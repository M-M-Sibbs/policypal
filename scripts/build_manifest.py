"""Build data/manifest.json from the policy files in data/policies/.

    python scripts/build_manifest.py

For PDFs, page_count is the real number of pages. For md/txt/html files, which
have no physical pages, page_count is a page-equivalent (words / 500, rounded
up) and is flagged with page_count_method so nobody mistakes it for a real
page number.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parsing import parse_document  # noqa: E402

POLICY_DIR = ROOT / "data" / "policies"
MANIFEST = ROOT / "data" / "manifest.json"
WORDS_PER_PAGE = 500


def main() -> int:
    docs = []
    total_pages = 0
    total_words = 0
    for path in sorted(POLICY_DIR.iterdir()):
        if path.suffix.lower() not in {".md", ".txt", ".html", ".pdf"}:
            continue
        parsed = parse_document(path)
        words = sum(len(re.findall(r"\S+", s.text)) for s in parsed.sections)
        if parsed.format == "pdf":
            pages = parsed.page_count
            method = "physical"
        else:
            pages = max(1, math.ceil(words / WORDS_PER_PAGE))
            method = f"estimated ({WORDS_PER_PAGE} words/page)"
        total_pages += pages
        total_words += words
        docs.append(
            {
                "document_id": parsed.meta["doc_id"],
                "title": parsed.meta["title"],
                "filename": path.name,
                "format": parsed.format,
                "version": parsed.meta["version"],
                "effective_date": parsed.meta["effective_date"],
                "category": parsed.meta.get("category", ""),
                "page_count": pages,
                "page_count_method": method,
                "word_count": words,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "provenance": "Original synthetic policy written for PolicyPal with AI assistance; fictional company Acme Corp.",
                "permission_status": "Owned by the project team; free to use, modify and commit.",
            }
        )
    manifest = {
        "corpus_name": "Acme Corp policies (synthetic)",
        "document_count": len(docs),
        "total_page_count": total_pages,
        "total_word_count": total_words,
        "documents": docs,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(ROOT)}: {len(docs)} documents, {total_pages} pages, {total_words} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
