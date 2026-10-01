"""Offline ingestion: manifest -> parse -> clean -> chunk -> embed -> Chroma.

    python -m app.ingest            # uses settings from the environment / .env
    EMBED_BACKEND=hash python -m app.ingest   # offline, no model download

The build is deterministic: files are processed in sorted order, the seed is
fixed, and the index is rebuilt from scratch each time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from .chunking import Chunk, chunk_document
from .config import Settings, load_settings, set_seeds
from .embeddings import build_embedder, passage_text
from .parsing import SUPPORTED_SUFFIXES, parse_document
from .vectorstore import write_index


def load_manifest(settings: Settings) -> dict:
    return json.loads(settings.manifest_path.read_text(encoding="utf-8"))


def corpus_version(manifest: dict) -> str:
    joined = "|".join(f"{d['document_id']}:{d['version']}:{d['sha256']}" for d in manifest["documents"])
    return "v1-" + hashlib.sha256(joined.encode()).hexdigest()[:10]


def verify_manifest(settings: Settings, manifest: dict) -> list[Path]:
    """Every file listed must exist with the recorded hash, and every policy
    file on disk must be listed: the index never contains unregistered docs."""
    paths = []
    listed = set()
    for doc in manifest["documents"]:
        path = settings.policy_dir / doc["filename"]
        if not path.exists():
            raise FileNotFoundError(f"manifest lists missing file {doc['filename']}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != doc["sha256"]:
            raise ValueError(
                f"{doc['filename']} changed since the manifest was built; run `python scripts/build_manifest.py`"
            )
        listed.add(path.name)
        paths.append(path)
    unlisted = [
        p.name for p in settings.policy_dir.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES and p.name not in listed
    ]
    if unlisted:
        raise ValueError(f"policy files not in manifest: {unlisted}")
    return sorted(paths)


def build_chunks(settings: Settings, manifest: dict) -> list[Chunk]:
    version = corpus_version(manifest)
    by_file = {d["filename"]: d for d in manifest["documents"]}
    chunks: list[Chunk] = []
    for path in verify_manifest(settings, manifest):
        doc = parse_document(path)
        expected = by_file[path.name]["document_id"]
        if doc.doc_id != expected:
            raise ValueError(f"{path.name}: doc_id {doc.doc_id} does not match manifest {expected}")
        for chunk in chunk_document(doc, settings.chunk_tokens, settings.chunk_overlap):
            chunk.corpus_version = version
            chunks.append(chunk)
    ids = [c.chunk_id for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk ids")
    return chunks


def run_ingest(settings: Settings, embedder=None, quiet: bool = False) -> dict:
    set_seeds(settings.seed)
    started = time.perf_counter()
    manifest = load_manifest(settings)
    chunks = build_chunks(settings, manifest)
    embedder = embedder or build_embedder(settings.embed_backend, settings.embed_model)
    embeddings = embedder.embed_documents([passage_text(c.title, c.section, c.text) for c in chunks])
    meta = {
        "corpus_version": corpus_version(manifest),
        "document_count": len(manifest["documents"]),
        "chunk_count": len(chunks),
        "embed_backend": settings.embed_backend,
        "embed_model": embedder.model_id,
        "chunk_tokens": settings.chunk_tokens,
        "chunk_overlap": settings.chunk_overlap,
        "seed": settings.seed,
        "build_seconds": round(time.perf_counter() - started, 2),
    }
    write_index(settings.chroma_dir, settings.collection_name, chunks, embeddings, meta)
    if not quiet:
        print(
            f"Indexed {meta['chunk_count']} chunks from {meta['document_count']} documents "
            f"into {settings.chroma_dir} ({meta['embed_backend']}: {meta['embed_model']}, "
            f"corpus {meta['corpus_version']}, {meta['build_seconds']}s)"
        )
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PolicyPal vector index")
    parser.add_argument("--chunk-tokens", type=int)
    parser.add_argument("--chunk-overlap", type=int)
    parser.add_argument("--chroma-dir", type=Path)
    args = parser.parse_args(argv)
    settings = load_settings()
    overrides = {}
    if args.chunk_tokens:
        overrides["chunk_tokens"] = args.chunk_tokens
    if args.chunk_overlap is not None:
        overrides["chunk_overlap"] = args.chunk_overlap
    if args.chroma_dir:
        overrides["chroma_dir"] = args.chroma_dir
    run_ingest(settings.with_overrides(**overrides))
    return 0


if __name__ == "__main__":
    sys.exit(main())
