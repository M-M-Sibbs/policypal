"""API contract tests for /, /health, /chat and the source routes (LLM mocked)."""
from __future__ import annotations

from app import create_app

from .conftest import FakeGenerator, ProviderError, ProviderTimeout

ANSWERABLE = "How many unused PTO days can I carry over into next year?"


def test_health_reports_ready_index(client, index_meta):
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["index_ready"] is True
    assert body["chunks"] == index_meta["chunk_count"] > 0
    assert body["version"]


def test_health_when_index_missing(settings, tmp_path):
    app = create_app(settings.with_overrides(chroma_dir=tmp_path / "none"))
    body = app.test_client().get("/health").get_json()
    assert body["status"] == "ok" and body["index_ready"] is False and "detail" in body


def test_chat_returns_answer_citations_and_snippets(client):
    resp = client.post("/chat", json={"question": ANSWERABLE})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "answered" and body["refused"] is False
    assert body["request_id"].startswith("req-")
    assert "5" in body["answer"] and "[1]" in body["answer"]
    cite = body["citations"][0]
    for key in ("id", "chunk_id", "document_id", "title", "section", "snippet", "source_url", "document_version"):
        assert key in cite
    assert cite["document_id"] == "POL-02"
    assert len(cite["snippet"]) <= 300
    assert isinstance(body["latency_ms"], int) and body["corpus_version"]


def test_chat_accepts_langflow_input_value(client):
    resp = client.post("/chat", json={"input_value": ANSWERABLE, "session_id": "abc"})
    body = resp.get_json()
    assert resp.status_code == 200 and body["status"] == "answered" and body["session_id"] == "abc"


def test_out_of_scope_is_refused_without_calling_the_llm(make_client):
    fake = FakeGenerator("should never be used [1]")
    body = make_client(fake).post("/chat", json={"question": "What is the capital of France?"}).get_json()
    assert body["status"] == "out_of_scope" and body["refused"] is True
    assert body["answer"] == "I can only answer about our policies."
    assert body["citations"] == [] and fake.calls == []


def test_model_refusal_becomes_insufficient_evidence(make_client):
    body = make_client(FakeGenerator("INSUFFICIENT_EVIDENCE")).post("/chat", json={"question": ANSWERABLE}).get_json()
    assert body["status"] == "insufficient_evidence" and body["citations"] == [] and body["refused"]


def test_uncited_answer_is_retried_then_refused(make_client):
    fake = FakeGenerator("Probably ten days.", "Still no markers.")
    body = make_client(fake).post("/chat", json={"question": ANSWERABLE}).get_json()
    assert [c["retry"] for c in fake.calls] == [False, True]
    assert body["status"] == "insufficient_evidence" and body["citations"] == []


def test_uncited_answer_recovers_on_retry(make_client):
    fake = FakeGenerator("Probably ten days.", "Up to 5 days carry over [1].")
    body = make_client(fake).post("/chat", json={"question": ANSWERABLE}).get_json()
    assert body["status"] == "answered" and len(body["citations"]) == 1


def test_long_answer_is_capped(make_client):
    long_answer = " ".join("Employees can carry over five days [1]." for _ in range(80))
    body = make_client(FakeGenerator(long_answer)).post("/chat", json={"question": ANSWERABLE}).get_json()
    assert body["status"] == "answered" and body["truncated"] is True
    assert len(body["answer"].split()) <= 250


def test_invalid_requests_return_400(client):
    assert client.post("/chat", data="not json", content_type="application/json").status_code == 400
    assert client.post("/chat", json={}).status_code == 400
    assert client.post("/chat", json={"question": "   "}).status_code == 400
    resp = client.post("/chat", json={"question": "x" * 2001})
    assert resp.status_code == 400 and resp.get_json()["status"] == "invalid_request"
    assert client.post("/chat", json={"question": "hi", "files": ["a.pdf"]}).status_code == 400


def test_provider_failures_map_to_502_and_504(make_client):
    r502 = make_client(FakeGenerator(ProviderError("boom"))).post("/chat", json={"question": ANSWERABLE})
    assert r502.status_code == 502 and r502.get_json()["status"] == "provider_error"
    assert "boom" not in r502.get_data(as_text=True)  # no provider internals leaked
    r504 = make_client(FakeGenerator(ProviderTimeout("slow"))).post("/chat", json={"question": ANSWERABLE})
    assert r504.status_code == 504 and r504.get_json()["status"] == "provider_timeout"


def test_missing_index_returns_503(settings, tmp_path):
    app = create_app(settings.with_overrides(chroma_dir=tmp_path / "none"))
    resp = app.test_client().post("/chat", json={"question": ANSWERABLE})
    assert resp.status_code == 503 and resp.get_json()["status"] == "knowledge_base_unavailable"


def test_index_built_with_other_backend_is_rejected(settings, index_meta):
    app = create_app(settings.with_overrides(embed_backend="sentence-transformers"))
    assert app.test_client().get("/health").get_json()["index_ready"] is False


def test_sources_are_restricted_to_registered_documents(client):
    md = client.get("/sources/POL-02")
    assert md.status_code == 200 and 'id="carry-over"' in md.get_data(as_text=True)
    assert "Content-Security-Policy" in md.headers
    html = client.get("/sources/POL-05").get_data(as_text=True)
    assert "<script" not in html and 'id="home-office-stipend"' in html
    pdf = client.get("/docs/POL-06")
    assert pdf.status_code == 200 and pdf.mimetype == "application/pdf"
    assert client.get("/sources/POL-99").status_code == 404
    assert client.get("/sources/..%2Fapp").status_code == 404


def test_every_citation_link_resolves(client):
    for q in [ANSWERABLE, "What is the per diem for international travel?", "How many floating holidays do I get?"]:
        for cite in client.post("/chat", json={"question": q}).get_json()["citations"]:
            path = cite["source_url"].split("#")[0]
            assert client.get(path).status_code == 200


def test_policies_endpoint_and_index_page(client):
    body = client.get("/api/policies").get_json()
    assert len(body["policies"]) == 12 and body["examples"]
    assert client.get("/").status_code == 200


def test_unknown_route_and_wrong_method(client):
    assert client.get("/nope").status_code == 404
    assert client.get("/chat").status_code == 405
