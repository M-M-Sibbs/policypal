"""Policy management: add, replace, remove and re-index policies at runtime.

All endpoints live under /api/admin and require the ADMIN_TOKEN, sent as
`Authorization: Bearer <token>` (or `X-Admin-Token`). When ADMIN_TOKEN is not
set, policy management is disabled and every endpoint returns 403.

Uploaded files go to POLICY_UPLOAD_DIR (default storage/uploads), never into
the committed data/policies folder, so "reset" always restores the original
corpus. Every change re-indexes immediately; chat requests wait for the
re-index to finish (see PipelineHolder.index_lock).
"""
from __future__ import annotations

import hmac
import json
import logging
import re
import shutil
import tempfile
import time
from functools import wraps
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .config import Settings
from .corpus import (
    SIDECAR_SUFFIX,
    collect_corpus,
    committed_documents,
    hidden_ids,
    policy_files,
    read_corpus_file,
    write_hidden_ids,
)
from .parsing import METADATA_KEYS, SUPPORTED_SUFFIXES, parse_document
from .vectorstore import read_index_meta

log = logging.getLogger("policypal.admin")
admin_bp = Blueprint("policypal_admin", __name__, url_prefix="/api/admin")

TEMPLATE = """---
doc_id: POL-13
title: Parking Policy
version: "1.0"
effective_date: 2026-10-01
category: Workplace
---

# Parking Policy

One or two sentences saying what this policy covers and who it applies to.

## Eligibility

Write each rule as a clear, specific sentence. Concrete numbers, dates and
limits make answers easy to check, for example: "Employees may park in Lot B
from 07:00 to 19:00 on working days."

## Requesting a Permit

Use one `##` heading per topic. PolicyPal cites answers by section, so each
heading should describe the rule underneath it.
"""


class AdminError(Exception):
    def __init__(self, status_code: int, status: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.status = status
        self.message = message


def _settings() -> Settings:
    return current_app.config["SETTINGS"]


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _settings().admin_token
        if not token:
            return jsonify(
                {"status": "admin_disabled", "message": "Policy management is disabled. Set the ADMIN_TOKEN environment variable to enable it."}
            ), 403
        supplied = request.headers.get("X-Admin-Token", "")
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
        if not supplied or not hmac.compare_digest(supplied.encode(), token.encode()):
            return jsonify({"status": "unauthorized", "message": "The admin token is missing or incorrect."}), 401
        try:
            return view(*args, **kwargs)
        except AdminError as exc:
            return jsonify({"status": exc.status, "message": exc.message}), exc.status_code

    return wrapper


def bump_version(version: str) -> str:
    """1.0 -> 1.1, 2 -> 2.1, 1.9 -> 1.10; anything else gets '.1' appended."""
    m = re.fullmatch(r"(\d+)(?:\.(\d+))?", str(version).strip())
    if not m:
        return f"{version}.1"
    major, minor = m.group(1), m.group(2)
    return f"{major}.{int(minor) + 1}" if minor is not None else f"{major}.1"


def run_ingest(*args, **kwargs):
    # imported lazily so `python -m app.ingest` does not import itself twice
    from .ingest import run_ingest as _run

    return _run(*args, **kwargs)


def reindex(settings: Settings) -> dict:
    """Rebuild the index while holding the write lock, then reload the pipeline."""
    holder = current_app.config["PIPELINE"]
    with holder.index_lock.write():
        meta = run_ingest(settings, embedder=holder.embedder, quiet=True)
        holder.reset()
    log.info(
        "re-indexed: %s documents, %s chunks (%s embedded) in %ss",
        meta["document_count"], meta["chunk_count"], meta["embedded_chunks"], meta["build_seconds"],
    )
    return meta


def _index_summary(meta: dict) -> dict:
    keys = ("corpus_version", "document_count", "chunk_count", "embedded_chunks", "reused_chunks", "build_seconds")
    return {k: meta.get(k) for k in keys}


def _policy_rows(settings: Settings) -> list[dict]:
    corpus = read_corpus_file(settings) or {"documents": []}
    return [
        {
            "document_id": d["document_id"],
            "title": d["title"],
            "version": d["version"],
            "effective_date": d["effective_date"],
            "category": d.get("category", ""),
            "format": d["format"],
            "filename": d["filename"],
            "origin": d.get("origin", "original"),
            "word_count": d.get("word_count"),
            "source_url": f"/sources/{d['document_id']}",
        }
        for d in corpus["documents"]
    ]


def _uploaded_paths(settings: Settings, doc_id: str) -> list[Path]:
    paths = []
    for path in policy_files(settings.upload_dir):
        sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
        meta = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
        if meta.get("doc_id") == doc_id:
            paths.append(path)
    return paths


def _remove_upload(path: Path) -> None:
    path.unlink(missing_ok=True)
    path.with_name(path.name + SIDECAR_SUFFIX).unlink(missing_ok=True)


class _Snapshot:
    """Copy of the upload folder, restored if a change fails to index."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.backup = Path(tempfile.mkdtemp(prefix="policypal-uploads-"))
        if folder.exists():
            shutil.copytree(folder, self.backup, dirs_exist_ok=True)

    def restore(self) -> None:
        if self.folder.exists():
            shutil.rmtree(self.folder)
        shutil.copytree(self.backup, self.folder, dirs_exist_ok=True)

    def discard(self) -> None:
        shutil.rmtree(self.backup, ignore_errors=True)


def _apply_change(settings: Settings, change) -> dict:
    """Run a file change and re-index; roll the files back if indexing fails."""
    holder = current_app.config["PIPELINE"]
    snapshot = _Snapshot(settings.upload_dir)
    try:
        with holder.index_lock.write():
            result = change()
            try:
                collect_corpus(settings)  # validate before touching the index
                meta = run_ingest(settings, embedder=holder.embedder, quiet=True)
            except ValueError as exc:
                snapshot.restore()
                raise AdminError(422, "invalid_policy", str(exc)) from exc
            except Exception:
                snapshot.restore()
                run_ingest(settings, embedder=holder.embedder, quiet=True)
                raise
            finally:
                holder.reset()
        return {"result": result, "index": _index_summary(meta)}
    finally:
        snapshot.discard()


# ---- routes -------------------------------------------------------------------


@admin_bp.get("/status")
def status():
    """Public: lets the admin page know whether management is enabled."""
    s = _settings()
    return jsonify(
        {
            "enabled": bool(s.admin_token),
            "max_upload_mb": s.max_upload_mb,
            "allowed_types": sorted(SUPPORTED_SUFFIXES),
        }
    )


@admin_bp.get("/template")
def template():
    resp = current_app.response_class(TEMPLATE, mimetype="text/markdown")
    resp.headers["Content-Disposition"] = 'attachment; filename="POL-13_policy_template.md"'
    return resp


@admin_bp.get("/policies")
@require_admin
def list_policies():
    s = _settings()
    return jsonify(
        {
            "policies": _policy_rows(s),
            "hidden": sorted(hidden_ids(s)),
            "index": _index_summary(read_index_meta(s.chroma_dir) or {}),
        }
    )


@admin_bp.post("/policies")
@require_admin
def upload_policy():
    s = _settings()
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise AdminError(400, "invalid_request", "Choose a policy file to upload.")
    suffix = Path(upload.filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise AdminError(400, "invalid_request", f"Unsupported file type {suffix or '(none)'}. Use .md, .txt, .html or .pdf.")
    form = {k: (request.form.get(k) or "").strip() for k in METADATA_KEYS}

    # Parse in a scratch folder first so a bad file never reaches the corpus.
    scratch = Path(tempfile.mkdtemp(prefix="policypal-upload-"))
    try:
        name = secure_filename(upload.filename) or f"policy{suffix}"
        tmp_path = scratch / name
        upload.save(tmp_path)
        try:
            doc = parse_document(tmp_path, overrides=form)
        except Exception as exc:  # unreadable PDF, bad metadata, empty file …
            raise AdminError(422, "invalid_policy", f"Could not read this policy: {exc}") from exc

        current = {d["document_id"]: d for d in _policy_rows(s)}
        doc_id = doc.meta["doc_id"]
        previous = current.get(doc_id)  # replacing a policy that is in the index now
        if previous and "version" in doc.derived_keys and not form["version"]:
            doc.meta["version"] = bump_version(previous["version"])
        existing_uploads = _uploaded_paths(s, doc_id)
        if not existing_uploads and len(policy_files(s.upload_dir)) >= s.max_uploaded_docs:
            raise AdminError(409, "too_many_uploads", f"At most {s.max_uploaded_docs} uploaded policies are allowed. Reset or remove some first.")

        def change():
            s.upload_dir.mkdir(parents=True, exist_ok=True)
            for old in existing_uploads:
                _remove_upload(old)
            dest = s.upload_dir / f"{doc_id}__{int(time.time())}__{name}"
            shutil.copy(tmp_path, dest)
            meta = {k: doc.meta[k] for k in METADATA_KEYS if doc.meta.get(k)}
            sidecar = {**meta, "source_filename": name, "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            dest.with_name(dest.name + SIDECAR_SUFFIX).write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
            hidden = hidden_ids(s)
            if doc_id in hidden:
                write_hidden_ids(s, hidden - {doc_id})
            return meta

        out = _apply_change(s, change)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    meta = out["result"]
    action = "replaced" if previous else "added"
    log.info("policy %s %s (version %s)", doc_id, action, meta["version"])
    return jsonify(
        {
            "status": action,
            "message": (
                f"{doc_id} updated from version {previous['version']} to {meta['version']}."
                if previous
                else f"{doc_id} added as version {meta['version']}."
            ),
            "document": meta,
            "previous_version": previous["version"] if previous else None,
            "derived_metadata": sorted(doc.derived_keys - {k for k, v in form.items() if v}),
            "index": out["index"],
        }
    ), 201


@admin_bp.delete("/policies/<doc_id>")
@require_admin
def delete_policy(doc_id: str):
    s = _settings()
    doc_id = doc_id.upper()
    current = {d["document_id"]: d for d in _policy_rows(s)}
    if doc_id not in current:
        raise AdminError(404, "not_found", f"{doc_id} is not in the knowledge base.")
    if len(current) == 1:
        raise AdminError(409, "last_policy", "The knowledge base needs at least one policy.")
    committed = {d.doc.doc_id for d in committed_documents(s)}
    uploads = _uploaded_paths(s, doc_id)

    def change():
        for path in uploads:
            _remove_upload(path)
        if uploads and doc_id in committed:
            return "reverted"  # the original version comes back
        if doc_id in committed:
            write_hidden_ids(s, hidden_ids(s) | {doc_id})
        return "removed"

    out = _apply_change(s, change)
    message = (
        f"Upload removed; {doc_id} is back to its original version."
        if out["result"] == "reverted"
        else f"{doc_id} removed from the knowledge base."
    )
    return jsonify({"status": out["result"], "message": message, "index": out["index"]})


@admin_bp.post("/reset")
@require_admin
def reset():
    s = _settings()

    def change():
        if s.upload_dir.exists():
            shutil.rmtree(s.upload_dir)
        return "reset"

    out = _apply_change(s, change)
    return jsonify({"status": "reset", "message": "Knowledge base restored to the original policies.", "index": out["index"]})


@admin_bp.post("/reindex")
@require_admin
def reindex_now():
    s = _settings()
    try:
        meta = reindex(s)
    except ValueError as exc:
        raise AdminError(422, "invalid_policy", str(exc)) from exc
    return jsonify({"status": "reindexed", "message": "Index rebuilt.", "index": _index_summary(meta)})
