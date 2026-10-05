"""HTTP routes: the chat UI at /, POST /chat, GET /health, policy sources."""
from __future__ import annotations

import logging
import time
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory

from .config import APP_VERSION
from .generator import ProviderError, ProviderTimeout
from .guardrails import InvalidQuestion, validate_question
from .rag import IndexUnavailable, check_index
from .sources import is_valid_doc_id, load_registry, resolve_source

log = logging.getLogger("policypal")
bp = Blueprint("policypal", __name__)

EXAMPLE_QUESTIONS = [
    "How many unused PTO days can I carry over into next year?",
    "What is the per diem for international travel?",
    "How quickly must I report a security incident?",
    "Can I use my personal laptop when working from home?",
    "How long is primary caregiver parental leave?",
    "What is the annual learning budget?",
]


def _request_id() -> str:
    return "req-" + uuid.uuid4().hex[:12]


def _error(status_code: int, status: str, message: str, request_id: str):
    return jsonify({"request_id": request_id, "status": status, "refused": False, "message": message}), status_code


@bp.get("/health")
def health():
    settings = current_app.config["SETTINGS"]
    ok, reason, meta = check_index(settings)
    holder = current_app.config["PIPELINE"]
    body = {
        "status": "ok",
        "index_ready": ok,
        "index_loaded": holder.loaded,
        "chunks": (meta or {}).get("chunk_count", 0),
        "documents": (meta or {}).get("document_count", 0),
        "corpus_version": (meta or {}).get("corpus_version"),
        "embed_backend": settings.embed_backend,
        "llm_provider": settings.llm_provider,
        "version": APP_VERSION,
    }
    if not ok:
        body["detail"] = reason
    elif holder.load_error:
        body["detail"] = holder.load_error
    return jsonify(body)


@bp.post("/chat")
def chat():
    request_id = _request_id()
    settings = current_app.config["SETTINGS"]
    started = time.perf_counter()

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error(400, "invalid_request", "Send a JSON body like {\"question\": \"...\"}.", request_id)
    # "input_value" is accepted so a Langflow ChatInput message can be forwarded as-is.
    raw_question = data.get("question", data.get("input_value"))
    if data.get("files"):
        return _error(400, "invalid_request", "File attachments are not supported; ask a text question.", request_id)
    try:
        question = validate_question(raw_question, settings.max_question_chars)
    except InvalidQuestion as exc:
        return _error(400, "invalid_request", str(exc), request_id)

    holder = current_app.config["PIPELINE"]
    try:
        with holder.index_lock.read():  # waits while a policy update re-indexes
            pipeline = holder.get()
            result = pipeline.answer(question)
    except IndexUnavailable:
        return _error(503, "knowledge_base_unavailable", "The policy knowledge base is not available yet. Please try again shortly.", request_id)
    except ProviderTimeout:
        log.warning("%s provider timeout", request_id)
        return _error(504, "provider_timeout", "The answer service took too long to respond. Please retry.", request_id)
    except ProviderError as exc:
        log.warning("%s provider error: %s", request_id, exc)
        return _error(502, "provider_error", "The answer service is unavailable. Please retry.", request_id)

    result["request_id"] = request_id
    if isinstance(data.get("session_id"), str):
        result["session_id"] = data["session_id"][:128]
    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    log.info(
        "%s status=%s citations=%d latency_ms=%d q_chars=%d",
        request_id, result["status"], len(result["citations"]), result["latency_ms"], len(question),
    )
    return jsonify(result)


@bp.get("/api/policies")
def policies():
    settings = current_app.config["SETTINGS"]
    docs = [
        {
            "document_id": d["document_id"],
            "title": d["title"],
            "category": d.get("category", ""),
            "format": d["format"],
            "version": d["version"],
            "effective_date": d["effective_date"],
            "origin": d.get("origin", "original"),
            "source_url": f"/sources/{d['document_id']}",
        }
        for d in load_registry(settings).values()
    ]
    return jsonify({"policies": docs, "examples": EXAMPLE_QUESTIONS, "max_question_chars": settings.max_question_chars})


@bp.get("/sources/<doc_id>")
@bp.get("/docs/<doc_id>")
def source(doc_id: str):
    settings = current_app.config["SETTINGS"]
    if not is_valid_doc_id(doc_id):
        return jsonify({"status": "not_found", "message": "Unknown policy document."}), 404
    resolved = resolve_source(settings, doc_id)
    if resolved is None:
        return jsonify({"status": "not_found", "message": "Unknown policy document."}), 404
    kind, value = resolved
    if kind == "pdf":
        resp = send_file(value, mimetype="application/pdf", download_name=value.name, as_attachment=False)
    else:
        resp = current_app.response_class(value, mimetype="text/html")
        resp.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'"
    return resp


# ---- Frontend (React build) ---------------------------------------------------

FALLBACK_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>PolicyPal</title></head>
<body style="font-family:system-ui;max-width:640px;margin:60px auto;padding:0 16px">
<h1>PolicyPal</h1><p>The chat interface has not been built yet. Run <code>npm --prefix frontend install</code>
and <code>npm --prefix frontend run build</code>, then reload. The API is available at <code>POST /chat</code>.</p>
</body></html>"""


@bp.get("/")
@bp.get("/admin")
def index():
    dist = current_app.config["SETTINGS"].frontend_dist
    if (dist / "index.html").exists():
        resp = send_from_directory(dist, "index.html")
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    return current_app.response_class(FALLBACK_PAGE, mimetype="text/html")


@bp.get("/assets/<path:filename>")
def assets(filename: str):
    dist = current_app.config["SETTINGS"].frontend_dist
    resp = send_from_directory(dist / "assets", filename)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


@bp.get("/favicon.svg")
def favicon():
    return send_from_directory(current_app.config["SETTINGS"].frontend_dist, "favicon.svg")
