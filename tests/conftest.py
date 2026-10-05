"""Shared fixtures. Everything here runs offline: the index is built with the
deterministic hash embedder and the LLM is replaced by fakes, so the suite
needs no API key, no model download and no network."""
from __future__ import annotations

import pytest

from app import create_app
from app.config import load_settings
from app.generator import ExtractiveGenerator, ProviderError, ProviderTimeout
from app.ingest import run_ingest
from app.rag import RagPipeline


@pytest.fixture(scope="session")
def settings(tmp_path_factory):
    base = load_settings()
    return base.with_overrides(
        chroma_dir=tmp_path_factory.mktemp("chroma"),
        upload_dir=tmp_path_factory.mktemp("uploads"),
        admin_token="",
        embed_backend="hash",
        embed_model="hash",
        rerank=False,
        score_threshold=0.12,
        llm_provider="extractive",
        llm_api_key="",
    )


@pytest.fixture(scope="session")
def index_meta(settings):
    return run_ingest(settings, quiet=True)


class FakeGenerator:
    """Returns scripted outputs in order; records calls."""

    label = last_label = "fake:test"

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate(self, question, hits, retry=False):
        self.calls.append({"question": question, "retry": retry, "n_hits": len(hits)})
        out = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def make_client(settings, index_meta):
    def factory(generator=None, **overrides):
        s = settings.with_overrides(**overrides) if overrides else settings
        gen = generator or ExtractiveGenerator()
        app = create_app(s, pipeline_factory=lambda: RagPipeline.from_settings(s, generator=gen))
        app.config["TESTING"] = True
        return app.test_client()

    return factory


@pytest.fixture
def client(make_client):
    return make_client()


__all__ = ["FakeGenerator", "ProviderError", "ProviderTimeout"]
