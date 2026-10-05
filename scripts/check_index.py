"""Exit 0 if the built index matches the current settings, 1 otherwise.

Used by Dockerfile.render at container start: `python scripts/check_index.py || python -m app.ingest`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402
from app.rag import check_index  # noqa: E402

ok, reason, _ = check_index(load_settings())
print(f"index check: {reason}")
sys.exit(0 if ok else 1)
