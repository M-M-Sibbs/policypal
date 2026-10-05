#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .venv/bin/activate ]; then echo "Run ./scripts/setup_offline.sh first." >&2; exit 1; fi
. .venv/bin/activate
set -a; . ./.env.offline; set +a
if [ ! -f storage/chroma-offline/index_meta.json ]; then python -m app.ingest; fi
exec python -m flask --app app run --host 127.0.0.1 --port "${PORT:-5000}"
