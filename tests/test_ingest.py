"""Ingestion: parsing, cleaning, chunking and index building."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.chunking import chunk_document
from app.corpus import collect_corpus, corpus_version, file_digest, load_manifest, verify_committed
from app.ingest import build_chunks, run_ingest
from app.parsing import parse_document
from app.vectorstore import VectorStore

POLICIES = Path(__file__).resolve().parents[1] / "data" / "policies"


def test_manifest_meets_corpus_requirements(settings):
    manifest = load_manifest(settings)
    docs = manifest["documents"]
    assert 5 <= len(docs) <= 20
    assert {d["format"] for d in docs} == {"md", "txt", "html", "pdf"}
    assert 30 <= manifest["total_page_count"] <= 120
    assert len({d["document_id"] for d in docs}) == len(docs)


@pytest.mark.parametrize("path", sorted(POLICIES.iterdir()), ids=lambda p: p.name)
def test_every_policy_parses_with_metadata(path):
    doc = parse_document(path)
    assert doc.doc_id.startswith("POL-")
    assert doc.meta["version"] and doc.meta["effective_date"]
    assert len(doc.sections) >= 5
    assert all(s.text.strip() for s in doc.sections)


def test_html_cleaning_strips_navigation_and_scripts():
    doc = parse_document(POLICIES / "POL-05_remote_and_hybrid_work.html")
    text = " ".join(s.text for s in doc.sections)
    assert "Intranet home" not in text
    assert "console.log" not in text
    assert "intranetAnalytics" not in text
    assert "$500" in text


def test_pdf_keeps_real_pages_and_removes_running_headers():
    doc = parse_document(POLICIES / "POL-06_travel_and_expense.pdf")
    assert doc.page_count >= 3
    text = " ".join(s.text for s in doc.sections)
    assert "Acme Corp | POL-06" not in text
    assert "Page 2" not in text
    per_diem = next(s for s in doc.sections if s.heading == "Meals and Per Diem")
    assert per_diem.page_start is not None and per_diem.page_start >= 1
    assert "$110 per day" in per_diem.text


def test_chunks_respect_size_overlap_and_ids():
    doc = parse_document(POLICIES / "POL-02_paid_time_off.md")
    chunks = chunk_document(doc, chunk_tokens=40, chunk_overlap=10)
    assert all(len(c.text.split()) <= 40 for c in chunks)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    # a long section split into windows shares overlapping words
    multi = [c for c in chunks if c.chunk_id.endswith("-c01")]
    assert multi, "expected at least one section split into windows"
    first = next(c for c in chunks if c.chunk_id == multi[0].chunk_id.replace("-c01", "-c00"))
    assert first.text.split()[-10:] == multi[0].text.split()[:10]
    # same input -> same ids (stable)
    assert ids == [c.chunk_id for c in chunk_document(doc, chunk_tokens=40, chunk_overlap=10)]


def test_chunk_metadata_and_source_links(settings):
    docs = collect_corpus(settings)
    chunks = build_chunks(settings, docs, "test")
    pdf_chunks = [c for c in chunks if c.format == "pdf"]
    other = [c for c in chunks if c.format != "pdf"]
    assert all(c.source_url.startswith(f"/sources/{c.document_id}#page=") for c in pdf_chunks)
    assert all(c.page_start is None and c.source_url == f"/sources/{c.document_id}#{c.anchor}" for c in other)
    assert all(c.section and c.title and c.document_version for c in chunks)


def test_rebuild_is_idempotent_and_reuses_embeddings(settings, tmp_path):
    s = settings.with_overrides(chroma_dir=tmp_path / "idx")
    first = run_ingest(s, quiet=True)
    second = run_ingest(s, quiet=True)
    assert first["chunk_count"] == second["chunk_count"] == VectorStore(s.chroma_dir, s.collection_name).count()
    assert first["corpus_version"] == second["corpus_version"] == corpus_version(load_manifest(s)["documents"])
    assert first["embedded_chunks"] == first["chunk_count"] and second["embedded_chunks"] == 0
    meta = json.loads((s.chroma_dir / "index_meta.json").read_text())
    assert meta["embed_backend"] == "hash" and meta["seed"] == 42


def test_committed_corpus_version_is_stable(settings):
    # The evaluation results in eval/results/ were produced on this corpus version.
    assert corpus_version(load_manifest(settings)["documents"]) == "v1-2a44e4aa53"


def test_strict_mode_detects_changed_or_unlisted_files(settings, tmp_path):
    policies = tmp_path / "policies"
    shutil.copytree(settings.policy_dir, policies)
    s = settings.with_overrides(policy_dir=policies, chroma_dir=tmp_path / "idx")
    target = policies / "POL-02_paid_time_off.md"
    target.write_text(target.read_text(encoding="utf-8").replace("Up to 5", "Up to 7"), encoding="utf-8")
    with pytest.raises(ValueError, match="changed since the manifest"):
        run_ingest(s, quiet=True, strict=True)
    # non-strict mode simply indexes the edited file
    run_ingest(s, quiet=True)
    shutil.copy(settings.policy_dir / target.name, target)  # restore, then add an unlisted file
    (policies / "POL-13_parking.md").write_text("# Parking\n\nStaff park in Lot B.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not in data/manifest.json"):
        verify_committed(s)


def test_crlf_checkout_has_same_hash(tmp_path):
    src = POLICIES / "POL-02_paid_time_off.md"
    crlf = tmp_path / src.name
    crlf.write_bytes(src.read_bytes().replace(b"\n", b"\r\n"))
    assert file_digest(crlf) == file_digest(src)


def test_files_without_metadata_get_derived_metadata(tmp_path):
    md = tmp_path / "POL-13_parking_policy.md"
    md.write_text("# Parking Policy\n\n## Allocation\n\nEmployees park in Lot B.\n", encoding="utf-8")
    doc = parse_document(md)
    assert doc.meta["doc_id"] == "POL-13" and doc.meta["title"] == "Parking Policy"
    assert doc.meta["version"] == "1.0" and {"doc_id", "version"} <= doc.derived_keys
    txt = tmp_path / "travel notes.txt"
    txt.write_text("Travel Notes\n============\n\nBook trains early.\n", encoding="cp1252")
    doc = parse_document(txt)
    assert doc.meta["doc_id"] == "DOC-TRAVEL-NOTES" and "Book trains early." in doc.sections[0].text
    with pytest.raises(ValueError, match="no readable text"):
        empty = tmp_path / "empty.md"
        empty.write_text("---\ntitle: Empty\n---\n", encoding="utf-8")
        parse_document(empty)
