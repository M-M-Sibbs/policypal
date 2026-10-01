"""Download the embedding and re-ranking models into the Hugging Face cache so
the first request (and offline runs) don't wait for a download.

    python scripts/download_models.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402


def main() -> int:
    s = load_settings()
    if s.embed_backend != "sentence-transformers":
        print(f"EMBED_BACKEND={s.embed_backend}: nothing to download")
        return 0
    from sentence_transformers import CrossEncoder, SentenceTransformer

    SentenceTransformer(s.embed_model, device="cpu")
    print(f"cached {s.embed_model}")
    if s.rerank:
        CrossEncoder(s.rerank_model, device="cpu")
        print(f"cached {s.rerank_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
