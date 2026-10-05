"""Persistent Chroma vector store plus the metadata that describes how the
index was built (embedding model, chunking settings, corpus version)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .chunking import Chunk

META_FILE = "index_meta.json"


@dataclass
class Hit:
    chunk: Chunk
    similarity: float  # cosine similarity in [-1, 1]
    rerank_score: float | None = None


def _client(path: Path):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path), settings=ChromaSettings(anonymized_telemetry=False))


def read_index_meta(chroma_dir: Path) -> dict | None:
    meta_path = chroma_dir / META_FILE
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def existing_embeddings(chroma_dir: Path, collection_name: str) -> dict[str, tuple[str, list[float]]]:
    """chunk_id -> (text, embedding) from the current index, for reuse when
    re-indexing after an update. Empty if there is no index yet."""
    if read_index_meta(chroma_dir) is None:
        return {}
    client = _client(chroma_dir)
    collection = client.get_collection(collection_name, embedding_function=None)
    res = collection.get(include=["documents", "embeddings"])
    return {
        cid: (doc, [float(x) for x in emb])
        for cid, doc, emb in zip(res["ids"], res["documents"], res["embeddings"])
    }


def write_index(chroma_dir: Path, collection_name: str, chunks: list[Chunk], embeddings: list[list[float]], meta: dict) -> None:
    """Rebuild idempotently: drop the collection, then add every chunk.
    Rebuilding from scratch (instead of upserting) guarantees that removed or
    renamed chunks cannot linger."""
    meta_path = chroma_dir / META_FILE
    if meta_path.exists():
        meta_path.unlink()  # index is "not ready" until the rebuild completes
    client = _client(chroma_dir)
    if collection_name in {c.name if hasattr(c, "name") else c for c in client.list_collections()}:
        client.delete_collection(collection_name)
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )
    batch = 256
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        collection.add(
            ids=[c.chunk_id for c in part],
            documents=[c.text for c in part],
            metadatas=[c.metadata() for c in part],
            embeddings=embeddings[i : i + batch],
        )
    (chroma_dir / META_FILE).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


class VectorStore:
    def __init__(self, chroma_dir: Path, collection_name: str):
        self.chroma_dir = chroma_dir
        self.meta = read_index_meta(chroma_dir)
        if self.meta is None:
            raise FileNotFoundError(f"no index found in {chroma_dir}; run `python -m app.ingest`")
        self._client = _client(chroma_dir)
        self.collection = self._client.get_collection(collection_name, embedding_function=None)

    def count(self) -> int:
        return self.collection.count()

    def query(self, embedding: list[float], k: int) -> list[Hit]:
        res = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(k, max(1, self.count())),
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append(Hit(chunk=Chunk.from_metadata(meta, doc), similarity=1.0 - float(dist)))
        # deterministic order: similarity desc, then chunk id
        hits.sort(key=lambda h: (-round(h.similarity, 6), h.chunk.chunk_id))
        return hits

    def get_all(self) -> list[Chunk]:
        res = self.collection.get(include=["documents", "metadatas"])
        chunks = [Chunk.from_metadata(m, d) for d, m in zip(res["documents"], res["metadatas"])]
        return sorted(chunks, key=lambda c: c.chunk_id)
