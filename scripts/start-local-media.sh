#!/bin/bash
# Reliable local Media service start for IDE tasks / host Python mode.
# Always binds :8000, loads host runtime URLs, and repairs a broken venv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MEDIA_DIR="$PROJECT_ROOT/ppl-meta-media"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

cd "$MEDIA_DIR"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/load-local-python-runtime-env.sh"
"$SCRIPT_DIR/ensure-local-python-venv.sh" "$MEDIA_DIR"

# Override mistaken PORT=8002 (orchestrator) values in local .env files.
export PORT=8000
export VISION_SERVICE_URL="${VISION_SERVICE_URL:-http://127.0.0.1:8003}"

media_healthy() {
    curl -sf --connect-timeout 1 "http://127.0.0.1:8000/health" 2>/dev/null | grep -q '"status"[[:space:]]*:[[:space:]]*"healthy"'
}

# If Media is already healthy, stay attached so IDE background tasks don't flap.
if media_healthy; then
    echo "Media already healthy on http://127.0.0.1:8000 — watching existing process"
    EXISTING_PID="$(lsof -ti tcp:8000 2>/dev/null | head -1 || true)"
    if [ -n "${EXISTING_PID:-}" ]; then
        echo "$EXISTING_PID" > "$PID_DIR/ppl-meta-media.pid"
        while kill -0 "$EXISTING_PID" 2>/dev/null && media_healthy; do
            sleep 5
        done
        echo "Existing Media process ended; restarting..."
    fi
fi

# Free a stale / unhealthy listener so restarts don't silently fail.
if lsof -ti tcp:8000 >/dev/null 2>&1; then
    echo "Freeing port 8000 before Media start..."
    lsof -ti tcp:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo "Starting Media on http://127.0.0.1:8000 ..."
exec "$MEDIA_DIR/venv/bin/python" -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
