"""Build data/manifest.json from the policy files in data/policies/.

    python scripts/build_manifest.py

Run this after adding, editing or removing a committed policy; CI checks that
the committed manifest matches the folder (python -m app.ingest --strict).

For PDFs, page_count is the real number of pages. For md/txt/html files, which
have no physical pages, page_count is a page-equivalent (words / 500, rounded
up) and is flagged with page_count_method so nobody mistakes it for a real
page number. Text files are hashed with LF line endings, so the manifest is
the same on Windows and Linux checkouts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.corpus import committed_documents  # noqa: E402


def main() -> int:
    settings = load_settings()
    entries = [d.manifest_entry() for d in committed_documents(settings)]
    entries.sort(key=lambda e: e["filename"])
    manifest = {
        "corpus_name": "Acme Corp policies (synthetic)",
        "document_count": len(entries),
        "total_page_count": sum(e["page_count"] for e in entries),
        "total_word_count": sum(e["word_count"] for e in entries),
        "documents": entries,
    }
    settings.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {settings.manifest_path.relative_to(ROOT)}: {len(entries)} documents, "
        f"{manifest['total_page_count']} pages, {manifest['total_word_count']} words"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
