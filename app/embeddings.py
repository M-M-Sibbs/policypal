"""Embedding backends.

* SentenceTransformerEmbedder - BAAI/bge-small-en-v1.5 (384-dim, local, free).
  This is the default for real use and deployment.
* HashEmbedder - a deterministic feature-hashing bag-of-words model with no
  model download. It lets CI and the offline test suite build a real Chroma
  index without network access. It is a lexical baseline, not a semantic
  model, and is labelled as such in every result it produces.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

import numpy as np

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

STOPWORDS = frozenset(
    """a an and are as at be been but by can could do does did for from had has have
    how i if in into is it its may me might must my no not of on or our shall should so
    than that the their them then there these they this those to up us was we were what
    when where which who whom why will with would you your yours about any all also each
    get got per""".split()
)
TOKEN_RE = re.compile(r"[a-z0-9$%]+(?:[.'][a-z0-9]+)*")


def _stem(token: str) -> str:
    if len(token) > 4 and token.endswith(("ies", "ied")):
        return token[:-3] + "y"
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def content_tokens(text: str) -> list[str]:
    """Lower-cased, stop-word-free, lightly stemmed tokens (shared with the
    extractive generator and the lexical evaluation proxy)."""
    return [_stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class HashEmbedder:
    name = "hash"

    def __init__(self, dim: int = 2048):
        self.dim = dim
        self.model_id = f"hash-bow-{dim}"

    @staticmethod
    @lru_cache(maxsize=65536)
    def _bucket(feature: str, dim: int) -> tuple[int, float]:
        digest = hashlib.md5(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] & 1 else -1.0
        return index, sign

    def _embed(self, text: str) -> list[float]:
        tokens = content_tokens(text)
        features: dict[str, float] = {}
        for tok in tokens:
            features[tok] = features.get(tok, 0.0) + 1.0
        for a, b in zip(tokens, tokens[1:]):
            key = f"{a}_{b}"
            features[key] = features.get(key, 0.0) + 0.5
        vec = np.zeros(self.dim, dtype=np.float64)
        for feature, count in features.items():
            idx, sign = self._bucket(feature, self.dim)
            vec[idx] += sign * (1.0 + math.log(count))
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist() if norm else vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class SentenceTransformerEmbedder:
    name = "sentence-transformers"

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer  # heavy import, deferred
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "sentence-transformers is not installed. Install torch (CPU) and requirements.txt, "
                "or set EMBED_BACKEND=hash for the offline embedder."
            ) from exc

        self.model_id = model_name
        self.model = SentenceTransformer(model_name, device="cpu")
        self.query_prefix = BGE_QUERY_PREFIX if "bge" in model_name.lower() else ""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode([self.query_prefix + text], normalize_embeddings=True, show_progress_bar=False)
        return vector[0].tolist()


def build_embedder(backend: str, model_name: str):
    if backend == "hash":
        return HashEmbedder()
    if backend == "sentence-transformers":
        return SentenceTransformerEmbedder(model_name)
    raise ValueError(f"unknown EMBED_BACKEND {backend!r}")


def passage_text(title: str, section: str, text: str) -> str:
    """What we embed for a chunk: its text plus where it lives, so a chunk whose
    body never repeats the topic (e.g. 'Carry-over') is still findable."""
    return f"{title} - {section}\n{text}"
