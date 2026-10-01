"""Ingestion: parsing, cleaning, chunking and index building."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.chunking import chunk_document
from app.ingest import build_chunks, corpus_version, load_manifest, run_ingest
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
    chunks = build_chunks(settings, load_manifest(settings))
    pdf_chunks = [c for c in chunks if c.format == "pdf"]
    other = [c for c in chunks if c.format != "pdf"]
    assert all(c.source_url.startswith(f"/sources/{c.document_id}#page=") for c in pdf_chunks)
    assert all(c.page_start is None and c.source_url == f"/sources/{c.document_id}#{c.anchor}" for c in other)
    assert all(c.section and c.title and c.document_version for c in chunks)


def test_rebuild_is_idempotent(settings, tmp_path):
    s = settings.with_overrides(chroma_dir=tmp_path / "idx")
    first = run_ingest(s, quiet=True)
    second = run_ingest(s, quiet=True)
    assert first["chunk_count"] == second["chunk_count"] == VectorStore(s.chroma_dir, s.collection_name).count()
    assert first["corpus_version"] == second["corpus_version"] == corpus_version(load_manifest(s))
    meta = json.loads((s.chroma_dir / "index_meta.json").read_text())
    assert meta["embed_backend"] == "hash" and meta["seed"] == 42


def test_changed_file_is_detected(settings, tmp_path):
    manifest = load_manifest(settings)
    manifest["documents"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="changed since the manifest"):
        build_chunks(settings, manifest)
