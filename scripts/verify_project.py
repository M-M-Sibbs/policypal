"""Quick pre-submission check: required files exist and the committed corpus
matches data/manifest.json.

    python scripts/verify_project.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.corpus import file_digest  # noqa: E402

REQUIRED = [
    "app/__init__.py", "app/routes.py", "app/rag.py", "app/admin.py", "requirements.txt", "requirements-lite.txt",
    "data/manifest.json", ".github/workflows/ci.yml", "render.yaml", "Dockerfile.render",
    "README.md", "design-and-evaluation.md", "ai-tooling.md", "deployed.md", "eval/questions.jsonl",
]


def main() -> int:
    errors = [f"missing: {rel}" for rel in REQUIRED if not (ROOT / rel).exists()]
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    for d in manifest.get("documents", []):
        p = ROOT / "data/policies" / d["filename"]
        if not p.exists():
            errors.append(f"missing policy: {d['filename']}")
        elif file_digest(p) != d.get("sha256"):
            errors.append(f"hash mismatch: {d['filename']} (run python scripts/build_manifest.py)")
    dist = ROOT / "frontend/dist"
    if not (dist / "index.html").exists():
        print("note: frontend/dist not built yet (npm --prefix frontend ci && npm --prefix frontend run build)")
    count = len(manifest.get("documents", []))
    pages = sum(int(d.get("page_count") or 0) for d in manifest.get("documents", []))
    print(f"PolicyPal package check: {count} policy documents, {pages} manifest pages")
    if errors:
        print("FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS: required source, corpus, deployment and documentation files are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
