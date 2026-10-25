#!/usr/bin/env bash

set -euo pipefail

BACKEND_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$BACKEND_DIR"

if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

exec "$PYTHON_BIN" -m uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --reload \
    "$@"
