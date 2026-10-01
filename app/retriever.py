"""Query-time retrieval: embed -> top-k cosine from Chroma -> optional
cross-encoder re-rank -> keep top-n."""
from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .embeddings import passage_text
from .vectorstore import Hit, VectorStore


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder  # heavy import, deferred

        self.model_id = model_name
        self.model = CrossEncoder(model_name, device="cpu")

    def score(self, question: str, hits: list[Hit]) -> list[float]:
        pairs = [(question, passage_text(h.chunk.title, h.chunk.section, h.chunk.text)) for h in hits]
        return [float(s) for s in self.model.predict(pairs, show_progress_bar=False)]


@dataclass
class RetrievalResult:
    hits: list[Hit]  # final, ordered evidence passed to the generator
    candidates: list[Hit]  # raw top-k before re-ranking (for debugging/eval)
    best_similarity: float

    def above(self, threshold: float) -> bool:
        return bool(self.candidates) and self.best_similarity >= threshold


class Retriever:
    def __init__(self, settings: Settings, store: VectorStore, embedder, reranker=None):
        self.settings = settings
        self.store = store
        self.embedder = embedder
        self.reranker = reranker

    def retrieve(self, question: str) -> RetrievalResult:
        candidates = self.store.query(self.embedder.embed_query(question), self.settings.top_k)
        best = max((h.similarity for h in candidates), default=0.0)
        hits = list(candidates)
        if self.reranker is not None and hits:
            scores = self.reranker.score(question, hits)
            for hit, score in zip(hits, scores):
                hit.rerank_score = score
            hits.sort(key=lambda h: (-h.rerank_score, h.chunk.chunk_id))
        return RetrievalResult(hits=hits[: self.settings.top_n], candidates=candidates, best_similarity=best)
