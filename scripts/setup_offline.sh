#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then echo "Python 3.11+ is required." >&2; exit 1; fi
"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lite.txt
set -a; . ./.env.offline; set +a
python -m app.ingest
python scripts/verify_project.py
printf '\nOffline setup complete. Run: ./scripts/run_offline.sh\n'
