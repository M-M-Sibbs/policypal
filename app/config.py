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
DEFAULT_THRESHOLDS = {"sentence-transformers": 0.35, "hash": 0.12}


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

    # Reproducibility
    seed: int = 42

    # Chunking (tokens are approximated as whitespace-separated words)
    chunk_tokens: int = 500
    chunk_overlap: int = 75

    # Embeddings: "sentence-transformers" (default, BAAI/bge-small-en-v1.5) or
    # "hash" (dependency-free, deterministic; used in CI and offline runs).
    embed_backend: str = "sentence-transformers"
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # Retrieval
    top_k: int = 8
    top_n: int = 4
    score_threshold: float = 0.35
    rerank: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Generation
    llm_provider: str = "groq"  # groq | openrouter | openai | extractive
    llm_api_key: str = ""
    llm_model: str = "llama-3.1-8b-instant"
    llm_base_url: str = ""
    llm_fallback_provider: str = ""  # e.g. "openrouter"
    llm_fallback_api_key: str = ""
    llm_fallback_model: str = ""
    llm_timeout_s: float = 30.0
    llm_temperature: float = 0.0
    max_tokens: int = 300

    # Guardrails
    max_question_chars: int = 2000
    answer_word_target: int = 150  # asked of the model in the prompt
    max_answer_words: int = 250  # hard cap enforced after generation
    snippet_chars: int = 300

    extra: dict = field(default_factory=dict)

    def with_overrides(self, **kwargs) -> "Settings":
        return replace(self, **kwargs)


def load_settings() -> Settings:
    backend = _env("EMBED_BACKEND", "sentence-transformers").lower()
    threshold_default = DEFAULT_THRESHOLDS.get(backend, 0.35)
    return Settings(
        chroma_dir=Path(_env("CHROMA_DIR", str(ROOT_DIR / "storage" / "chroma"))),
        seed=_env_int("SEED", 42),
        chunk_tokens=_env_int("CHUNK_TOKENS", 500),
        chunk_overlap=_env_int("CHUNK_OVERLAP", 75),
        embed_backend=backend,
        embed_model=_env("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        top_k=_env_int("TOP_K", 8),
        top_n=_env_int("TOP_N", 4),
        score_threshold=_env_float("SCORE_THRESHOLD", threshold_default),
        rerank=_env_bool("RERANK", backend == "sentence-transformers"),
        rerank_model=_env("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        llm_provider=_env("LLM_PROVIDER", "groq").lower(),
        llm_api_key=_env("LLM_API_KEY", ""),
        llm_model=_env("LLM_MODEL", "llama-3.1-8b-instant"),
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
    try:  # torch is only present with the sentence-transformers backend
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass
