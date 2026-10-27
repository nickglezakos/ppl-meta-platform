#!/bin/bash
# Mac / host local-Python overrides only.
# Sourced by VS Code local Python tasks — never by Docker Compose / lab installers.
# Labs keep compose DNS (ppl-meta-media, ppl-meta-cameras, …).

if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_PATH="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    SCRIPT_PATH="${(%):-%N}"
else
    SCRIPT_PATH="$0"
fi

SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_PATH" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Inter-service URLs for processes on the host (no Compose DNS).
export MEDIA_SERVICE_URL="http://127.0.0.1:8000"
export CAMERAS_SERVICE_URL="http://127.0.0.1:8005"
# Orchestrator reads CAMERA_SERVICE_URL (singular); keep both in sync for local Python.
export CAMERA_SERVICE_URL="${CAMERA_SERVICE_URL:-http://127.0.0.1:8005}"
export NODE_SERVICE_URL="${NODE_SERVICE_URL:-http://127.0.0.1:8001/api/v1}"
export GATEWAY_SERVICE_URL="${GATEWAY_SERVICE_URL:-http://127.0.0.1:8080}"
export COMMUNICATIONS_SERVICE_URL="${COMMUNICATIONS_SERVICE_URL:-http://127.0.0.1:8009/api/v1}"
export DISCOVERY_SERVICE_URL="${DISCOVERY_SERVICE_URL:-http://127.0.0.1:8006}"
export VISION_SERVICE_URL="${VISION_SERVICE_URL:-http://127.0.0.1:8003}"
export VMETA_SERVICE_URL="${VMETA_SERVICE_URL:-http://127.0.0.1:8008}"
export VMETA_URL="${VMETA_URL:-http://127.0.0.1:8008}"
export MODELS_SERVICE_URL="${MODELS_SERVICE_URL:-http://127.0.0.1:8013}"
export ORCHESTRATOR_SERVICE_URL="${ORCHESTRATOR_SERVICE_URL:-http://127.0.0.1:8002}"
export PRESENCE_SERVICE_URL="${PRESENCE_SERVICE_URL:-http://127.0.0.1:8011}"

# Instant-detection Celery defaults Redis host to Compose DNS ("redis") when unset.
export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

# Keep media on its existing on-disk library (ppl-meta-media/media).
# Forcing a separate .local root made new uploads miss the DB/UI path used by
# historical files under media/<user>/...
export STORAGE_PATH="${STORAGE_PATH:-${PROJECT_ROOT}/ppl-meta-media/media}"
export UPLOAD_DIR="${UPLOAD_DIR:-$STORAGE_PATH}"
mkdir -p "$STORAGE_PATH"
