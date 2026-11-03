#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/retail-app"
if [[ ! -x .venv/bin/python || ! -d app/node_modules ]]; then
  echo 'Install dependencies first; see README.md in the repository root.'
  exit 1
fi
exec bash run_demo.sh
