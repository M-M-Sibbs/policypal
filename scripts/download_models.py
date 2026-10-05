"""Download the configured embedding (and re-ranking) models into the local
cache so the first request does not wait for a download. Used by the Dockerfile.

    python scripts/download_models.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402
from app.embeddings import build_embedder  # noqa: E402


def main() -> int:
    s = load_settings()
    if s.embed_backend == "hash":
        print("EMBED_BACKEND=hash: nothing to download")
        return 0
    embedder = build_embedder(s.embed_backend, s.embed_model)
    embedder.embed_documents(["warm-up"])  # ONNX downloads its model on first use
    print(f"cached {embedder.model_id}")
    if s.rerank:
        from app.retriever import CrossEncoderReranker

        CrossEncoderReranker(s.rerank_model)
        print(f"cached {s.rerank_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
