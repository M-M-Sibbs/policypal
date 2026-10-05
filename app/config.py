"""Central configuration. Every tunable lives here and can be overridden by an
environment variable (see .env.example). Values are read once at import time;
tests build their own Settings objects instead of mutating globals."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field, replace
from pathlib import Path

try:  # optional: load a local .env during development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_VERSION = "1.0.0"

# Default relevance thresholds differ per embedding backend because cosine
# scores are on different scales. Override with SCORE_THRESHOLD after running
# scripts/calibrate_threshold.py for the backend you deploy.
DEFAULT_THRESHOLDS = {
    "sentence-transformers": 0.35,
    "onnx": 0.30,
    "hash": 0.12,
}


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def _env_int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(_env(name, str(default)))


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Paths
    policy_dir: Path = ROOT_DIR / "data" / "policies"
    manifest_path: Path = ROOT_DIR / "data" / "manifest.json"
    chroma_dir: Path = ROOT_DIR / "storage" / "chroma"
    frontend_dist: Path = ROOT_DIR / "frontend" / "dist"
    collection_name: str = "policies"
    upload_dir: Path = ROOT_DIR / "storage" / "uploads"  # runtime policy updates

    # Policy management (admin page / API). Disabled unless ADMIN_TOKEN is set.
    admin_token: str = ""
    max_upload_mb: int = 5
    max_uploaded_docs: int = 20

    # Reproducibility
    seed: int = 42

    # Chunking (tokens are approximated as whitespace-separated words)
    chunk_tokens: int = 500
    chunk_overlap: int = 75

    # Embeddings:
    # - "onnx" is the final tested semantic backend (Chroma MiniLM, no PyTorch)
    # - "sentence-transformers" remains supported for alternative environments
    # - "hash" is the deterministic offline/CI baseline
    embed_backend: str = "onnx"
    embed_model: str = "all-MiniLM-L6-v2-onnx"

    # Retrieval
    top_k: int = 8
    top_n: int = 4
    score_threshold: float = 0.30
    rerank: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Generation
    llm_provider: str = "groq"  # groq | openrouter | openai | extractive
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"
    llm_base_url: str = ""
    llm_fallback_provider: str = ""
    llm_fallback_api_key: str = ""
    llm_fallback_model: str = ""
    llm_timeout_s: float = 30.0
    llm_temperature: float = 0.0
    max_tokens: int = 300

    # Guardrails
    max_question_chars: int = 2000
    answer_word_target: int = 150
    max_answer_words: int = 250
    snippet_chars: int = 300

    extra: dict = field(default_factory=dict)

    def with_overrides(self, **kwargs) -> "Settings":
        return replace(self, **kwargs)


def load_settings() -> Settings:
    backend = _env("EMBED_BACKEND", "onnx").lower()
    threshold_default = DEFAULT_THRESHOLDS.get(backend, 0.30)

    default_model = {
        "onnx": "all-MiniLM-L6-v2-onnx",
        "sentence-transformers": "BAAI/bge-small-en-v1.5",
        "hash": "hash",
    }.get(backend, "all-MiniLM-L6-v2-onnx")

    return Settings(
        chroma_dir=Path(_env("CHROMA_DIR", str(ROOT_DIR / "storage" / "chroma"))),
        upload_dir=Path(_env("POLICY_UPLOAD_DIR", str(ROOT_DIR / "storage" / "uploads"))),
        admin_token=_env("ADMIN_TOKEN", ""),
        max_upload_mb=_env_int("MAX_UPLOAD_MB", 5),
        max_uploaded_docs=_env_int("MAX_UPLOADED_DOCS", 20),
        seed=_env_int("SEED", 42),
        chunk_tokens=_env_int("CHUNK_TOKENS", 500),
        chunk_overlap=_env_int("CHUNK_OVERLAP", 75),
        embed_backend=backend,
        embed_model=_env("EMBED_MODEL", default_model),
        top_k=_env_int("TOP_K", 8),
        top_n=_env_int("TOP_N", 4),
        score_threshold=_env_float("SCORE_THRESHOLD", threshold_default),
        rerank=_env_bool("RERANK", False),
        rerank_model=_env(
            "RERANK_MODEL",
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
        ),
        llm_provider=_env("LLM_PROVIDER", "groq").lower(),
        llm_api_key=_env("LLM_API_KEY", ""),
        llm_model=_env("LLM_MODEL", "openai/gpt-oss-20b"),
        llm_base_url=_env("LLM_BASE_URL", ""),
        llm_fallback_provider=_env("LLM_FALLBACK_PROVIDER", "").lower(),
        llm_fallback_api_key=_env("LLM_FALLBACK_API_KEY", ""),
        llm_fallback_model=_env("LLM_FALLBACK_MODEL", ""),
        llm_timeout_s=_env_float("LLM_TIMEOUT_S", 30.0),
        llm_temperature=_env_float("LLM_TEMPERATURE", 0.0),
        max_tokens=_env_int("MAX_TOKENS", 300),
        max_question_chars=_env_int("MAX_QUESTION_CHARS", 2000),
        answer_word_target=_env_int("ANSWER_WORD_TARGET", 150),
        max_answer_words=_env_int("MAX_ANSWER_WORDS", 250),
    )


def set_seeds(seed: int) -> None:
    """Fix every random source we use so ingestion and evaluation are repeatable."""
    random.seed(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))

    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:  # pragma: no cover
        pass

    # Seed torch only if the sentence-transformers backend has already loaded it.
    # Importing torch just to seed it is unnecessary for the ONNX configuration.
    import sys

    torch = sys.modules.get("torch")
    if torch is not None:
        torch.manual_seed(seed)
