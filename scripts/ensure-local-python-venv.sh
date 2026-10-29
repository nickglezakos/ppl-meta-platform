#!/bin/bash
# Ensure a service local venv can import FastAPI (and optionally install requirements).
# Usage: ensure-local-python-venv.sh <service-dir>
# Exits non-zero if the venv cannot be repaired.

set -euo pipefail

SERVICE_DIR="${1:-}"
if [ -z "$SERVICE_DIR" ] || [ ! -d "$SERVICE_DIR" ]; then
    echo "Usage: $0 <service-dir>" >&2
    exit 1
fi

SERVICE_DIR="$(cd "$SERVICE_DIR" && pwd)"
VENV_PY="$SERVICE_DIR/venv/bin/python"
REQ_FILE="$SERVICE_DIR/requirements.txt"

if [ ! -x "$VENV_PY" ]; then
    echo "❌ Missing venv python: $VENV_PY" >&2
    echo "   Create it with: python3.11 -m venv \"$SERVICE_DIR/venv\" && \"$SERVICE_DIR/venv/bin/pip\" install -r \"$REQ_FILE\"" >&2
    exit 1
fi

if "$VENV_PY" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
    exit 0
fi

echo "⚠️  $SERVICE_DIR venv is missing FastAPI/uvicorn — repairing from requirements.txt..."
if [ ! -f "$REQ_FILE" ]; then
    echo "❌ No requirements.txt at $REQ_FILE" >&2
    exit 1
fi

"$SERVICE_DIR/venv/bin/pip" install -r "$REQ_FILE"
if ! "$VENV_PY" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
    echo "❌ venv still cannot import fastapi/uvicorn after install" >&2
    exit 1
fi

echo "✅ $SERVICE_DIR venv repaired"
