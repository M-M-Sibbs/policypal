"""The online RAG pipeline: validate -> retrieve -> assess evidence ->
generate -> validate citations -> enforce length -> respond."""
from __future__ import annotations

import threading
import time

from .citations import build_citations, normalise_markers
from .config import Settings, set_seeds
from .embeddings import build_embedder
from .generator import build_generator
from .guardrails import (
    REFUSAL_INSUFFICIENT,
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_UNCITED,
    enforce_word_cap,
    is_refusal,
)
from .retriever import CrossEncoderReranker, Retriever
from .vectorstore import VectorStore, read_index_meta


class IndexUnavailable(RuntimeError):
    """The vector index is missing or was built with incompatible settings."""


def check_index(settings: Settings) -> tuple[bool, str, dict | None]:
    meta = read_index_meta(settings.chroma_dir)
    if meta is None:
        return False, "Index not built. Run `python -m app.ingest`.", None
    if meta.get("embed_backend") != settings.embed_backend:
        return (
            False,
            f"Index was built with EMBED_BACKEND={meta.get('embed_backend')} but the app is configured for "
            f"{settings.embed_backend}. Rebuild the index.",
            meta,
        )
    if settings.embed_backend == "sentence-transformers" and meta.get("embed_model") != settings.embed_model:
        return False, f"Index was built with {meta.get('embed_model')}; rebuild for {settings.embed_model}.", meta
    return True, "ok", meta


class RagPipeline:
    def __init__(self, settings: Settings, retriever: Retriever, generator, index_meta: dict):
        self.settings = settings
        self.retriever = retriever
        self.generator = generator
        self.index_meta = index_meta

    @classmethod
    def from_settings(cls, settings: Settings, generator=None, embedder=None, reranker=None) -> "RagPipeline":
        set_seeds(settings.seed)
        ok, reason, meta = check_index(settings)
        if not ok:
            raise IndexUnavailable(reason)
        try:
            store = VectorStore(settings.chroma_dir, settings.collection_name)
        except Exception as exc:  # corrupt or unreadable index
            raise IndexUnavailable(f"Index could not be opened: {type(exc).__name__}") from exc
        try:
            embedder = embedder or build_embedder(settings.embed_backend, settings.embed_model)
            if reranker is None and settings.rerank:
                reranker = CrossEncoderReranker(settings.rerank_model)
        except Exception as exc:  # missing package, failed model download, out of memory
            raise IndexUnavailable(f"Retrieval models could not be loaded: {exc}") from exc
        set_seeds(settings.seed)  # again, now that torch may be loaded
        retriever = Retriever(settings, store, embedder, reranker)
        return cls(settings, retriever, generator or build_generator(settings), meta)

    def _refusal(self, status: str, message: str, retrieval, started: float) -> dict:
        return self._payload(status, message, [], retrieval, started, refused=True)

    def _payload(self, status, answer, citations, retrieval, started, refused=False, truncated=False) -> dict:
        return {
            "status": status,
            "answer": answer,
            "refused": refused,
            "citations": citations,
            "corpus_version": self.index_meta.get("corpus_version"),
            "provider": getattr(self.generator, "last_label", getattr(self.generator, "label", "unknown")),
            "truncated": truncated,
            "retrieval": {
                "best_similarity": round(retrieval.best_similarity, 4) if retrieval else None,
                "threshold": self.settings.score_threshold,
                "reranked": self.retriever.reranker is not None,
                "chunks": [
                    {
                        "chunk_id": h.chunk.chunk_id,
                        "similarity": round(h.similarity, 4),
                        "rerank_score": None if h.rerank_score is None else round(h.rerank_score, 4),
                    }
                    for h in (retrieval.hits if retrieval else [])
                ],
            },
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }

    def answer(self, question: str) -> dict:
        started = time.perf_counter()
        retrieval = self.retriever.retrieve(question)

        # Guardrail 1: nothing in the corpus is close enough -> refuse before calling the LLM.
        if not retrieval.above(self.settings.score_threshold):
            return self._refusal("out_of_scope", REFUSAL_OUT_OF_SCOPE, retrieval, started)

        hits = retrieval.hits
        result = None
        for attempt in range(2):  # Guardrail 3: citations required; retry once
            raw = self.generator.generate(question, hits, retry=attempt == 1)
            if is_refusal(raw):
                return self._refusal("insufficient_evidence", REFUSAL_INSUFFICIENT, retrieval, started)
            # Guardrail 2: verify the length cap after generation
            capped, truncated = enforce_word_cap(normalise_markers(raw), self.settings.max_answer_words)
            result = build_citations(capped, hits, self.settings.snippet_chars)
            if result.citations:
                return self._payload("answered", result.answer, result.citations, retrieval, started, truncated=truncated)
        return self._refusal("insufficient_evidence", REFUSAL_UNCITED, retrieval, started)


class PipelineHolder:
    """Loads the pipeline lazily (models are slow to load) and lets /health
    report readiness without triggering a load."""

    def __init__(self, settings: Settings, factory=None):
        self.settings = settings
        self._factory = factory or (lambda: RagPipeline.from_settings(settings))
        self._pipeline: RagPipeline | None = None
        self._lock = threading.Lock()
        self.load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self._pipeline is not None

    def get(self) -> RagPipeline:
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    try:
                        self._pipeline = self._factory()
                        self.load_error = None
                    except IndexUnavailable as exc:
                        self.load_error = str(exc)
                        raise
        return self._pipeline

    def reset(self) -> None:
        with self._lock:
            self._pipeline = None
