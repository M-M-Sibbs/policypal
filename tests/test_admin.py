"""Policy updates through the admin API: add, replace, remove, reset, auth."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app import create_app
from app.generator import ExtractiveGenerator
from app.ingest import run_ingest
from app.rag import RagPipeline

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "policy-updates"
TOKEN = "test-admin-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def admin_env(settings, tmp_path):
    """A private index and upload folder per test, so updates never leak."""
    s = settings.with_overrides(chroma_dir=tmp_path / "chroma", upload_dir=tmp_path / "uploads", admin_token=TOKEN)
    run_ingest(s, quiet=True)
    app = create_app(s, pipeline_factory=lambda: RagPipeline.from_settings(s, generator=ExtractiveGenerator()))
    app.config["TESTING"] = True
    return app.test_client(), s


def upload(client, path: Path, **form):
    data = {"file": (io.BytesIO(path.read_bytes()), path.name), **form}
    return client.post("/api/admin/policies", data=data, headers=AUTH, content_type="multipart/form-data")


def ask(client, question: str) -> dict:
    return client.post("/chat", json={"question": question}).get_json()


def test_admin_disabled_without_token(client):
    assert client.get("/api/admin/status").get_json()["enabled"] is False
    resp = client.get("/api/admin/policies", headers=AUTH)
    assert resp.status_code == 403 and resp.get_json()["status"] == "admin_disabled"


def test_wrong_or_missing_token_is_rejected(admin_env):
    client, _ = admin_env
    assert client.get("/api/admin/status").get_json()["enabled"] is True
    assert client.get("/api/admin/policies").status_code == 401
    assert client.get("/api/admin/policies", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/admin/reset").status_code == 401
    assert client.get("/api/admin/policies", headers={"X-Admin-Token": TOKEN}).status_code == 200


def test_add_new_policy_is_answerable_and_cited(admin_env):
    client, _ = admin_env
    question = "How many spaces does the headquarters car park have?"
    assert ask(client, question)["status"] != "answered" or "120" not in ask(client, question)["answer"]

    resp = upload(client, EXAMPLES / "POL-13_parking_policy.md")
    body = resp.get_json()
    assert resp.status_code == 201 and body["status"] == "added"
    assert body["document"]["doc_id"] == "POL-13" and body["index"]["document_count"] == 13
    # only the new policy was embedded; everything else was reused
    assert 0 < body["index"]["embedded_chunks"] < body["index"]["chunk_count"]

    answer = ask(client, question)
    assert answer["status"] == "answered" and "120" in answer["answer"]
    assert answer["citations"][0]["document_id"] == "POL-13"
    assert client.get(answer["citations"][0]["source_url"].split("#")[0]).status_code == 200

    listed = {p["document_id"]: p for p in client.get("/api/policies").get_json()["policies"]}
    assert listed["POL-13"]["origin"] == "uploaded"
    assert client.get("/health").get_json()["documents"] == 13


def test_replacing_a_policy_bumps_version_and_changes_answer(admin_env):
    client, _ = admin_env
    question = "How many unused PTO days can I carry over into the next year?"
    before = ask(client, question)
    assert "5" in before["answer"] and before["citations"][0]["document_version"] == "1.0"

    body = upload(client, EXAMPLES / "POL-02_paid_time_off_update.md").get_json()
    assert body["status"] == "replaced" and body["previous_version"] == "1.0"
    assert body["document"]["version"] == "1.1" and "version" in body["derived_metadata"]

    after = ask(client, question)
    assert "8 unused days" in after["answer"]
    assert after["citations"][0]["document_id"] == "POL-02" and after["citations"][0]["document_version"] == "1.1"
    assert after["corpus_version"] != before["corpus_version"]
    page = client.get("/sources/POL-02").get_data(as_text=True)
    assert "Up to 8 unused days" in page and "version 1.1" in page

    # uploading again keeps bumping; removing the upload reverts to the original
    assert upload(client, EXAMPLES / "POL-02_paid_time_off_update.md").get_json()["document"]["version"] == "1.2"
    reverted = client.delete("/api/admin/policies/POL-02", headers=AUTH).get_json()
    assert reverted["status"] == "reverted"
    assert "5" in ask(client, question)["answer"]


def test_explicit_form_metadata_wins(admin_env, tmp_path):
    client, _ = admin_env
    plain = tmp_path / "canteen rules.txt"
    plain.write_text("Canteen Rules\n\nThe staff canteen opens at 07:30 and closes at 15:00.\n", encoding="utf-8")
    body = upload(client, plain, doc_id="pol-20", title="Canteen", version="3.0", effective_date="2026-12-01").get_json()
    assert body["document"] == {
        "doc_id": "POL-20", "title": "Canteen", "version": "3.0", "effective_date": "2026-12-01", "category": "General",
    }
    answer = ask(client, "What time does the staff canteen open?")
    assert "07:30" in answer["answer"] and answer["citations"][0]["title"] == "Canteen"


def test_remove_original_policy_then_reset(admin_env):
    client, _ = admin_env
    question = "What is the per diem for international travel?"
    assert ask(client, question)["citations"][0]["document_id"] == "POL-06"

    body = client.delete("/api/admin/policies/POL-06", headers=AUTH).get_json()
    assert body["status"] == "removed" and body["index"]["document_count"] == 11
    after = ask(client, question)
    assert all(c["document_id"] != "POL-06" for c in after["citations"])
    assert client.get("/sources/POL-06").status_code == 404

    upload(client, EXAMPLES / "POL-13_parking_policy.md")
    reset = client.post("/api/admin/reset", headers=AUTH).get_json()
    assert reset["status"] == "reset" and reset["index"]["document_count"] == 12
    assert reset["index"]["corpus_version"] == "v1-2a44e4aa53"
    assert ask(client, question)["citations"][0]["document_id"] == "POL-06"


def test_invalid_uploads_are_rejected_without_changing_the_index(admin_env, tmp_path):
    client, s = admin_env
    before = client.get("/health").get_json()["corpus_version"]

    exe = tmp_path / "virus.exe"
    exe.write_bytes(b"MZ")
    assert upload(client, exe).status_code == 400

    empty = tmp_path / "empty.md"
    empty.write_text("---\ntitle: Empty\n---\n", encoding="utf-8")
    resp = upload(client, empty)
    assert resp.status_code == 422 and "no readable text" in resp.get_json()["message"]

    bad_pdf = tmp_path / "broken.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4 not really a pdf")
    assert upload(client, bad_pdf).status_code == 422

    good = tmp_path / "rules.md"
    good.write_text("# Rules\n\nBe kind.\n", encoding="utf-8")
    assert upload(client, good, effective_date="31/12/2026").status_code == 422
    assert upload(client, good, doc_id="bad id!").status_code == 422

    assert client.post("/api/admin/policies", data={}, headers=AUTH).status_code == 400
    assert client.get("/health").get_json()["corpus_version"] == before
    assert not list(s.upload_dir.glob("*")) if s.upload_dir.exists() else True


def test_upload_size_limit(settings, tmp_path):
    s = settings.with_overrides(chroma_dir=tmp_path / "c", upload_dir=tmp_path / "u", admin_token=TOKEN, max_upload_mb=1)
    client = create_app(s).test_client()
    data = {"file": (io.BytesIO(b"x" * (2 * 1024 * 1024)), "big.md")}
    resp = client.post("/api/admin/policies", data=data, headers=AUTH, content_type="multipart/form-data")
    assert resp.status_code == 413 and resp.get_json()["status"] == "file_too_large"


def test_cannot_remove_unknown_policy(admin_env):
    client, _ = admin_env
    assert client.delete("/api/admin/policies/POL-99", headers=AUTH).status_code == 404


def test_reindex_picks_up_files_added_to_the_policy_folder(settings, tmp_path):
    import shutil

    policies = tmp_path / "policies"
    shutil.copytree(settings.policy_dir, policies)
    s = settings.with_overrides(
        policy_dir=policies, chroma_dir=tmp_path / "c", upload_dir=tmp_path / "u", admin_token=TOKEN
    )
    run_ingest(s, quiet=True)
    app = create_app(s, pipeline_factory=lambda: RagPipeline.from_settings(s, generator=ExtractiveGenerator()))
    client = app.test_client()
    shutil.copy(EXAMPLES / "POL-13_parking_policy.md", policies / "POL-13_parking_policy.md")
    body = client.post("/api/admin/reindex", headers=AUTH).get_json()
    assert body["index"]["document_count"] == 13
    assert "120" in ask(client, "How many spaces does the headquarters car park have?")["answer"]


def test_template_and_admin_page(admin_env):
    client, _ = admin_env
    template = client.get("/api/admin/template")
    assert template.status_code == 200 and b"doc_id: POL-13" in template.data
    assert client.get("/admin").status_code == 200


def test_bump_version():
    from app.admin import bump_version

    assert bump_version("1.0") == "1.1"
    assert bump_version("1.9") == "1.10"
    assert bump_version("2") == "2.1"
    assert bump_version("v3") == "v3.1"


def test_chat_waits_for_reindex_to_finish():
    import threading
    import time

    from app.rag import ReadWriteLock

    lock, events = ReadWriteLock(), []

    def writer():
        with lock.write():
            events.append("write-start")
            time.sleep(0.2)
            events.append("write-end")

    def reader():
        time.sleep(0.05)  # arrives while the writer holds the lock
        with lock.read():
            events.append("read")

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert events == ["write-start", "write-end", "read"]
