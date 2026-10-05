"""The policy corpus: committed policies plus runtime updates.

Two folders make up the corpus:

* ``data/policies/`` - the committed, version-controlled policies. Any
  md/txt/html/pdf file placed here is indexed on the next ingest.
* ``storage/uploads/`` (``POLICY_UPLOAD_DIR``) - policies added or replaced at
  runtime through the admin page/API. Each file has a ``.meta.json`` sidecar
  with its metadata. A document here replaces a committed document with the
  same ``doc_id``; ``_hidden.json`` lists committed documents that were removed.

Deleting the uploads folder (or "Reset to original" in the admin page)
returns the corpus exactly to the committed state.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT_DIR, Settings
from .parsing import SUPPORTED_SUFFIXES, ParsedDocument, parse_document

TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm"}
WORDS_PER_PAGE = 500
HIDDEN_FILE = "_hidden.json"
SIDECAR_SUFFIX = ".meta.json"
CORPUS_FILE = "corpus.json"  # effective manifest written next to the index
PROVENANCE = "Original synthetic policy written for PolicyPal with AI assistance; fictional company Acme Corp."
PERMISSION = "Owned by the project team; free to use, modify and commit."


def file_digest(path: Path) -> str:
    """SHA-256 of a policy file. Text files are hashed with LF line endings so
    a Windows checkout (CRLF) produces the same hash as Linux/CI."""
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


@dataclass
class CorpusDocument:
    doc: ParsedDocument
    path: Path
    origin: str  # "original" | "uploaded" | "replaced"
    sha256: str
    display_name: str = ""  # original file name of an upload

    def manifest_entry(self) -> dict:
        meta = self.doc.meta
        if self.doc.format == "pdf":
            pages, method = self.doc.page_count, "physical"
        else:
            pages = max(1, math.ceil(self.doc.word_count / WORDS_PER_PAGE))
            method = f"estimated ({WORDS_PER_PAGE} words/page)"
        return {
            "document_id": meta["doc_id"],
            "title": meta["title"],
            "filename": self.display_name or self.path.name,
            "format": self.doc.format,
            "version": meta["version"],
            "effective_date": meta["effective_date"],
            "category": meta.get("category", ""),
            "page_count": pages,
            "page_count_method": method,
            "word_count": self.doc.word_count,
            "sha256": self.sha256,
            "provenance": PROVENANCE if self.origin == "original" else "Uploaded through the PolicyPal admin page.",
            "permission_status": PERMISSION if self.origin == "original" else "Provided by the uploader.",
        }


def load_manifest(settings: Settings) -> dict:
    return json.loads(settings.manifest_path.read_text(encoding="utf-8"))


def corpus_version(entries: list[dict]) -> str:
    joined = "|".join(f"{d['document_id']}:{d['version']}:{d['sha256']}" for d in entries)
    return "v1-" + hashlib.sha256(joined.encode()).hexdigest()[:10]


def policy_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES and not p.name.startswith((".", "_"))
    )


def read_sidecar(path: Path) -> dict:
    sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
    if not sidecar.exists():
        return {}
    return json.loads(sidecar.read_text(encoding="utf-8"))


def hidden_ids(settings: Settings) -> set[str]:
    path = settings.upload_dir / HIDDEN_FILE
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def write_hidden_ids(settings: Settings, ids: set[str]) -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / HIDDEN_FILE).write_text(json.dumps(sorted(ids), indent=2) + "\n", encoding="utf-8")


def verify_committed(settings: Settings) -> None:
    """Strict check used by CI: every committed policy is listed in
    data/manifest.json with a matching hash, and nothing is unlisted."""
    manifest = load_manifest(settings)
    listed = {}
    for entry in manifest["documents"]:
        path = settings.policy_dir / entry["filename"]
        if not path.exists():
            raise FileNotFoundError(f"manifest lists missing file {entry['filename']}")
        if file_digest(path) != entry["sha256"]:
            raise ValueError(
                f"{entry['filename']} changed since the manifest was built; run `python scripts/build_manifest.py`"
            )
        listed[path.name] = entry
    unlisted = [p.name for p in policy_files(settings.policy_dir) if p.name not in listed]
    if unlisted:
        raise ValueError(f"policy files not in data/manifest.json: {unlisted}; run `python scripts/build_manifest.py`")


def committed_documents(settings: Settings) -> list[CorpusDocument]:
    docs, seen = [], {}
    for path in policy_files(settings.policy_dir):
        doc = parse_document(path)
        if doc.doc_id in seen:
            raise ValueError(f"duplicate doc_id {doc.doc_id} in {seen[doc.doc_id]} and {path.name}")
        seen[doc.doc_id] = path.name
        docs.append(CorpusDocument(doc, path, "original", file_digest(path)))
    return docs


def uploaded_documents(settings: Settings) -> list[CorpusDocument]:
    docs = []
    for path in policy_files(settings.upload_dir):
        sidecar = read_sidecar(path)
        doc = parse_document(path, overrides=sidecar)
        docs.append(CorpusDocument(doc, path, "uploaded", file_digest(path), sidecar.get("source_filename", "")))
    return docs


def collect_corpus(settings: Settings, strict: bool = False) -> list[CorpusDocument]:
    """Committed policies, minus hidden ones, with uploads replacing or adding."""
    if strict:
        verify_committed(settings)
    committed = {d.doc.doc_id: d for d in committed_documents(settings)}
    hidden = hidden_ids(settings)
    effective = {doc_id: d for doc_id, d in committed.items() if doc_id not in hidden}
    for upload in uploaded_documents(settings):
        if upload.doc.doc_id in committed:
            upload.origin = "replaced"
        effective[upload.doc.doc_id] = upload
    if not effective:
        raise ValueError("the corpus is empty: add at least one policy document")
    return [effective[k] for k in sorted(effective)]


def write_corpus_file(settings: Settings, docs: list[CorpusDocument], version: str) -> None:
    """Record what the current index contains; /sources and /api/policies read it."""
    entries = []
    for d in docs:
        entry = d.manifest_entry()
        entry["origin"] = d.origin
        try:
            entry["path"] = d.path.resolve().relative_to(ROOT_DIR).as_posix()
        except ValueError:
            entry["path"] = str(d.path.resolve())
        entries.append(entry)
    body = {"corpus_version": version, "document_count": len(entries), "documents": entries}
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    (settings.chroma_dir / CORPUS_FILE).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def read_corpus_file(settings: Settings) -> dict | None:
    path = settings.chroma_dir / CORPUS_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def entry_path(settings: Settings, entry: dict) -> Path:
    if entry.get("path"):
        p = Path(entry["path"])
        return p if p.is_absolute() else ROOT_DIR / p
    return settings.policy_dir / entry["filename"]
