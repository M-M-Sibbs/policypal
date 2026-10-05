"""Embedding backends.

Available backends:

* OnnxMiniLMEmbedder
  Uses Chroma's built-in ONNX MiniLM embedding model.
  This provides semantic embeddings without requiring PyTorch.
  Recommended for Windows environments where PyTorch DLLs are blocked.

* SentenceTransformerEmbedder
  Uses a SentenceTransformer model such as BAAI/bge-small-en-v1.5.
  Requires sentence-transformers + PyTorch.

* HashEmbedder
  Deterministic feature-hashing bag-of-words model with no model download.
  Used for CI/offline testing and as a lightweight lexical baseline.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
from functools import lru_cache

import numpy as np


BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

STOPWORDS = frozenset(
    """
    a an and are as at be been but by can could do does did for from had has have
    how i if in into is it its may me might must my no not of on or our shall should so
    than that the their them then there these they this those to up us was we were what
    when where which who whom why will with would you your yours about any all also each
    get got per
    """.split()
)

TOKEN_RE = re.compile(r"[a-z0-9$%]+(?:[.'][a-z0-9]+)*")


def _stem(token: str) -> str:
    """Very small stemmer used by the hash-based lexical embedder."""

    if len(token) > 4 and token.endswith(("ies", "ied")):
        return token[:-3] + "y"

    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]

    return token


def content_tokens(text: str) -> list[str]:
    """Return normalized lexical tokens.

    Shared by the hash embedder and lexical evaluation helpers.
    """

    return [
        _stem(token)
        for token in TOKEN_RE.findall(text.lower())
        if token not in STOPWORDS
    ]


# ============================================================
# HASH / OFFLINE EMBEDDER
# ============================================================

class HashEmbedder:
    """Deterministic lexical embedding backend.

    This backend requires no external model and no network access.
    It is useful for CI, offline testing, and fallback scenarios.

    It is NOT a semantic embedding model.
    """

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

        # Single-token features
        for token in tokens:
            features[token] = features.get(token, 0.0) + 1.0

        # Bigram features
        for left, right in zip(tokens, tokens[1:]):
            key = f"{left}_{right}"
            features[key] = features.get(key, 0.0) + 0.5

        vector = np.zeros(self.dim, dtype=np.float64)

        for feature, count in features.items():
            index, sign = self._bucket(feature, self.dim)
            vector[index] += sign * (1.0 + math.log(count))

        norm = np.linalg.norm(vector)

        if norm:
            return (vector / norm).tolist()

        return vector.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


# ============================================================
# ONNX SEMANTIC EMBEDDER
# ============================================================

class OnnxMiniLMEmbedder:
    """Semantic embedding backend using Chroma's ONNX MiniLM model.

    This backend uses ONNX Runtime instead of PyTorch.

    Advantages:
    - semantic retrieval
    - CPU compatible
    - no PyTorch DLL dependency
    - suitable for local Windows development
    - potentially lighter for deployment environments

    The underlying model is Chroma's ONNX MiniLM-L6-v2 embedding model.
    """

    name = "onnx"

    def __init__(self):
        try:
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        except ImportError as exc:
            raise RuntimeError(
                "Chroma ONNX embedding support is unavailable. "
                "Ensure chromadb and onnxruntime are installed."
            ) from exc

        self.model_id = "all-MiniLM-L6-v2-onnx"

        try:
            self.model = ONNXMiniLM_L6_V2()
        except Exception as exc:
            raise RuntimeError(
                "Unable to initialise the ONNX MiniLM embedding model."
            ) from exc

    @staticmethod
    def _to_python_vectors(vectors) -> list[list[float]]:
        """Convert NumPy / ONNX output into plain Python floats."""

        result: list[list[float]] = []

        for vector in vectors:
            result.append([float(value) for value in vector])

        return result

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            vectors = self.model(texts)
        except Exception as exc:
            raise RuntimeError(
                f"ONNX document embedding failed: {exc}"
            ) from exc

        return self._to_python_vectors(vectors)

    def embed_query(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed an empty query.")

        try:
            vectors = self.model([text])
        except Exception as exc:
            raise RuntimeError(
                f"ONNX query embedding failed: {exc}"
            ) from exc

        converted = self._to_python_vectors(vectors)

        if not converted:
            raise RuntimeError(
                "ONNX embedding model returned no query vector."
            )

        return converted[0]


# ============================================================
# SENTENCE TRANSFORMERS EMBEDDER
# ============================================================

class SentenceTransformerEmbedder:
    """Semantic embeddings using sentence-transformers.

    Requires PyTorch.

    This backend is retained because it may work on Linux/Render or on
    machines where PyTorch is permitted.
    """

    name = "sentence-transformers"

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "sentence-transformers / PyTorch could not be loaded. "
                "Use EMBED_BACKEND=onnx for semantic embeddings without "
                "PyTorch, or EMBED_BACKEND=hash for the offline backend."
            ) from exc

        self.model_id = model_name

        try:
            self.model = SentenceTransformer(
                model_name,
                device="cpu",
            )
        except Exception as exc:
            raise RuntimeError(
                f"Unable to initialise SentenceTransformer model "
                f"{model_name!r}: {exc}"
            ) from exc

        self.query_prefix = (
            BGE_QUERY_PREFIX
            if "bge" in model_name.lower()
            else ""
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed an empty query.")

        vector = self.model.encode(
            [self.query_prefix + text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return vector[0].tolist()


# ============================================================
# EMBEDDER FACTORY
# ============================================================

def build_embedder(
    backend: str,
    model_name: str,
):
    """Create the configured embedding backend."""

    normalized_backend = (backend or "").strip().lower()

    if normalized_backend == "hash":
        return HashEmbedder()

    if normalized_backend == "onnx":
        return OnnxMiniLMEmbedder()

    if normalized_backend == "sentence-transformers":
        return SentenceTransformerEmbedder(model_name)

    raise ValueError(
        f"Unknown EMBED_BACKEND {backend!r}. "
        "Expected one of: hash, onnx, sentence-transformers."
    )


_EMBEDDERS: dict[tuple[str, str], object] = {}
_EMBEDDERS_LOCK = threading.Lock()


def get_embedder(backend: str, model_name: str):
    """Process-wide cached embedder, so re-indexing after a policy update
    reuses the model the chat pipeline already loaded instead of loading a
    second copy (important on a 512 MB host)."""
    key = ((backend or "").strip().lower(), model_name)
    with _EMBEDDERS_LOCK:
        if key not in _EMBEDDERS:
            _EMBEDDERS[key] = build_embedder(backend, model_name)
        return _EMBEDDERS[key]


# ============================================================
# PASSAGE REPRESENTATION
# ============================================================

def passage_text(
    title: str,
    section: str,
    text: str,
) -> str:
    """Build the text representation stored in the vector index.

    Including title and section makes retrieval stronger when the chunk body
    itself does not explicitly repeat the policy topic.

    Example:

        Paid Time Off Policy - Carry-over
        Employees may carry over up to five unused PTO days...
    """

    title = (title or "").strip()
    section = (section or "").strip()
    text = (text or "").strip()

    return f"{title} - {section}\n{text}"