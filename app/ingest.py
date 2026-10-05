"""Ingestion: corpus -> parse -> clean -> chunk -> embed -> Chroma.

    python -m app.ingest              # index data/policies (+ any runtime uploads)
    python -m app.ingest --strict     # CI: also require data/manifest.json to match
    EMBED_BACKEND=hash python -m app.ingest   # offline, no model download

The build is deterministic: files are processed in sorted order, the seed is
fixed, and the collection is rebuilt from scratch each time. Embeddings of
chunks whose text did not change are reused from the previous index, so
re-indexing after a single policy update only embeds that policy.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .chunking import Chunk, chunk_document
from .config import Settings, load_settings, set_seeds
from .corpus import (
    CorpusDocument,
    collect_corpus,
    corpus_version,
    load_manifest,  # noqa: F401  (re-exported for scripts and tests)
    write_corpus_file,
)
from .embeddings import get_embedder, passage_text
from .vectorstore import existing_embeddings, read_index_meta, write_index


def build_chunks(settings: Settings, docs: list[CorpusDocument], version: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for item in docs:
        for chunk in chunk_document(item.doc, settings.chunk_tokens, settings.chunk_overlap):
            chunk.corpus_version = version
            chunks.append(chunk)
    ids = [c.chunk_id for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk ids")
    return chunks


def _reusable(settings: Settings, embedder) -> dict[str, tuple[str, list[float]]]:
    """Previous embeddings, only if they came from the same model."""
    meta = read_index_meta(settings.chroma_dir)
    if not meta or meta.get("embed_backend") != settings.embed_backend or meta.get("embed_model") != embedder.model_id:
        return {}
    try:
        return existing_embeddings(settings.chroma_dir, settings.collection_name)
    except Exception:  # unreadable index: just embed everything again
        return {}


def run_ingest(settings: Settings, embedder=None, quiet: bool = False, strict: bool = False, reuse: bool = True) -> dict:
    set_seeds(settings.seed)
    started = time.perf_counter()
    docs = collect_corpus(settings, strict=strict)
    entries = [d.manifest_entry() for d in docs]
    version = corpus_version(entries)
    chunks = build_chunks(settings, docs, version)
    embedder = embedder or get_embedder(settings.embed_backend, settings.embed_model)

    texts = [passage_text(c.title, c.section, c.text) for c in chunks]
    previous = _reusable(settings, embedder) if reuse else {}
    embeddings: list[list[float] | None] = []
    todo = []
    for i, (chunk, text) in enumerate(zip(chunks, texts)):
        old = previous.get(chunk.chunk_id)
        if old is not None and old[0] == chunk.text:
            embeddings.append(old[1])
        else:
            embeddings.append(None)
            todo.append(i)
    if todo:
        fresh = embedder.embed_documents([texts[i] for i in todo])
        for i, vector in zip(todo, fresh):
            embeddings[i] = vector

    meta = {
        "corpus_version": version,
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "embedded_chunks": len(todo),
        "reused_chunks": len(chunks) - len(todo),
        "embed_backend": settings.embed_backend,
        "embed_model": embedder.model_id,
        "chunk_tokens": settings.chunk_tokens,
        "chunk_overlap": settings.chunk_overlap,
        "seed": settings.seed,
        "uploaded_documents": sum(d.origin != "original" for d in docs),
        "build_seconds": round(time.perf_counter() - started, 2),
    }
    write_index(settings.chroma_dir, settings.collection_name, chunks, embeddings, meta)
    write_corpus_file(settings, docs, version)
    if not quiet:
        print(
            f"Indexed {meta['chunk_count']} chunks from {meta['document_count']} documents "
            f"into {settings.chroma_dir} ({meta['embed_backend']}: {meta['embed_model']}, "
            f"corpus {meta['corpus_version']}, embedded {meta['embedded_chunks']}, "
            f"reused {meta['reused_chunks']}, {meta['build_seconds']}s)"
        )
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PolicyPal vector index")
    parser.add_argument("--chunk-tokens", type=int)
    parser.add_argument("--chunk-overlap", type=int)
    parser.add_argument("--chroma-dir", type=Path)
    parser.add_argument("--strict", action="store_true", help="require data/manifest.json to match data/policies (CI)")
    parser.add_argument("--no-reuse", action="store_true", help="re-embed every chunk")
    args = parser.parse_args(argv)
    settings = load_settings()
    overrides = {}
    if args.chunk_tokens:
        overrides["chunk_tokens"] = args.chunk_tokens
    if args.chunk_overlap is not None:
        overrides["chunk_overlap"] = args.chunk_overlap
    if args.chroma_dir:
        overrides["chroma_dir"] = args.chroma_dir
    run_ingest(settings.with_overrides(**overrides), strict=args.strict, reuse=not args.no_reuse)
    return 0


if __name__ == "__main__":
    sys.exit(main())
