"""PolicyPal - a RAG assistant for company policy questions.

`app` below is the WSGI application used by `gunicorn app:app` and `flask run`.
Creating it is cheap: models and the vector index load lazily on the first
/chat request, or in a background thread when PRELOAD_PIPELINE=1.
"""
from __future__ import annotations

import logging
import os
import threading

from flask import Flask, jsonify, request

from .config import Settings, load_settings
from .rag import PipelineHolder


def create_app(settings: Settings | None = None, pipeline_factory=None) -> Flask:
    settings = settings or load_settings()
    flask_app = Flask(__name__, static_folder=None)
    flask_app.config["SETTINGS"] = settings
    flask_app.config["PIPELINE"] = PipelineHolder(settings, pipeline_factory)
    flask_app.config["JSON_SORT_KEYS"] = False
    flask_app.json.sort_keys = False

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")

    from .routes import bp

    flask_app.register_blueprint(bp)

    @flask_app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return resp

    @flask_app.errorhandler(404)
    def not_found(_err):
        return jsonify({"status": "not_found", "message": "Not found."}), 404

    @flask_app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify({"status": "method_not_allowed", "message": f"{request.method} is not allowed here."}), 405

    @flask_app.errorhandler(Exception)
    def unexpected(err):
        from werkzeug.exceptions import HTTPException

        if isinstance(err, HTTPException):
            return jsonify({"status": "error", "message": err.description}), err.code
        logging.getLogger("policypal").exception("unhandled error")
        return jsonify({"status": "internal_error", "message": "Something went wrong. Please retry."}), 500

    if os.getenv("PRELOAD_PIPELINE", "0") == "1":
        holder = flask_app.config["PIPELINE"]

        def warm():
            try:
                holder.get()
                logging.getLogger("policypal").info("pipeline preloaded")
            except Exception as exc:  # reported later via /health and /chat
                logging.getLogger("policypal").warning("pipeline preload failed: %s", exc)

        threading.Thread(target=warm, daemon=True).start()

    return flask_app


app = create_app()
