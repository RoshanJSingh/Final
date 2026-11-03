#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/build_retail_data.py
npm --prefix app run build
exec .venv/bin/python -m uvicorn demo:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8001}"
