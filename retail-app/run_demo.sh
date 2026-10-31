#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
npm --prefix app run build
exec .venv/bin/python -m uvicorn retail.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8001}"
