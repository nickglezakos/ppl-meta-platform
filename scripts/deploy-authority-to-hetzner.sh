#!/usr/bin/env bash
# Deploy ppl-meta-authority to Hetzner via rsync + remote docker build + container recreate.
#
# Automates the manual flow documented in docs/notes.txt:
#   1) rsync local source to the Hetzner host
#   2) docker build on the remote host
#   3) recreate the authority container (migrations run on startup)
#
# Usage:
#   ./scripts/deploy-authority-to-hetzner.sh [version]
#   ./scripts/deploy-authority-to-hetzner.sh --version 2.25.77
#   ./scripts/deploy-authority-to-hetzner.sh --sync-only
#   ./scripts/deploy-authority-to-hetzner.sh --build-only --version 2.25.77
#   ./scripts/deploy-authority-to-hetzner.sh --deploy-only --version 2.25.77
#
# Environment overrides:
#   HETZNER_SSH_HOST            SSH config alias or user@host (default: hetzner)
#   HETZNER_REMOTE_SOURCE_DIR   Remote source directory
#   HETZNER_REMOTE_ENV_FILE     Remote env file passed to docker run
#   AUTHORITY_CONTAINER_NAME    Docker container name (default: ppl-meta-authority)
#   AUTHORITY_DOCKER_NETWORK    Docker network (default: ppl-meta-authority_default)
#   AUTHORITY_IMAGE_NAME        Image name without tag (default: ppl-meta-authority)
#   AUTHORITY_HEALTH_URL        Optional URL for post-deploy health check

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

HETZNER_SSH_HOST="${HETZNER_SSH_HOST:-hetzner}"
HETZNER_REMOTE_SOURCE_DIR="${HETZNER_REMOTE_SOURCE_DIR:-/home/deploy/apps/ppl-meta-authority/source}"
HETZNER_REMOTE_ENV_FILE="${HETZNER_REMOTE_ENV_FILE:-/home/deploy/apps/ppl-meta-authority/cicd/env/authority.env}"
AUTHORITY_CONTAINER_NAME="${AUTHORITY_CONTAINER_NAME:-ppl-meta-authority}"
AUTHORITY_DOCKER_NETWORK="${AUTHORITY_DOCKER_NETWORK:-ppl-meta-authority_default}"
AUTHORITY_IMAGE_NAME="${AUTHORITY_IMAGE_NAME:-ppl-meta-authority}"
AUTHORITY_HEALTH_URL="${AUTHORITY_HEALTH_URL:-}"

SOURCE_DIR="${AUTHORITY_SOURCE_DIR:-$REPO_ROOT/autonomous/ppl-meta-authority}"

SYNC_ONLY=false
BUILD_ONLY=false
DEPLOY_ONLY=false
DRY_RUN=false
VERSION=""

usage() {
  sed -n '3,24p' "$0" | sed 's/^# \{0,1\}//'
}

log() {
  printf '[deploy-authority] %s\n' "$1"
}

die() {
  printf '[deploy-authority] ERROR: %s\n' "$1" >&2
  exit 1
}

read_version_file() {
  if [[ -f "$REPO_ROOT/VERSION" ]]; then
    tr -d '[:space:]' < "$REPO_ROOT/VERSION"
  else
    echo ""
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      [[ $# -ge 2 ]] || die "--version requires a value"
      VERSION="$2"
      shift 2
      ;;
    --host)
      [[ $# -ge 2 ]] || die "--host requires a value"
      HETZNER_SSH_HOST="$2"
      shift 2
      ;;
    --sync-only)
      SYNC_ONLY=true
      shift
      ;;
    --build-only)
      BUILD_ONLY=true
      shift
      ;;
    --deploy-only)
      DEPLOY_ONLY=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      die "Unknown option: $1"
      ;;
    *)
      if [[ -z "$VERSION" ]]; then
        VERSION="$1"
      else
        die "Unexpected argument: $1"
      fi
      shift
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  VERSION="$(read_version_file)"
fi

if $SYNC_ONLY && { $BUILD_ONLY || $DEPLOY_ONLY; }; then
  die "Use only one of --sync-only, --build-only, or --deploy-only"
fi

if ! $SYNC_ONLY; then
  [[ -n "$VERSION" ]] || die "Version is required. Pass it as an argument, --version, or set VERSION in the repo root."
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  die "Authority source directory not found: $SOURCE_DIR"
fi

run_cmd() {
  if $DRY_RUN; then
    printf '+ %s\n' "$*"
  else
    "$@"
  fi
}

remote_cmd() {
  local remote_command="$1"
  if $DRY_RUN; then
    printf '+ ssh %q %q\n' "$HETZNER_SSH_HOST" "$remote_command"
  else
    ssh "$HETZNER_SSH_HOST" "$remote_command"
  fi
}

image_ref="${AUTHORITY_IMAGE_NAME}:${VERSION}"

log "Hetzner host: $HETZNER_SSH_HOST"
log "Source dir:   $SOURCE_DIR"
log "Remote dir:   $HETZNER_REMOTE_SOURCE_DIR"
if [[ -n "$VERSION" ]]; then
  log "Image tag:    $image_ref"
fi

if ! $BUILD_ONLY && ! $DEPLOY_ONLY; then
  log "Step 1/3: Syncing source to Hetzner..."
  run_cmd rsync -avz --delete \
    --exclude '.venv' --exclude '.git' --exclude '.env' --exclude 'data' --exclude 'headscale' \
    "$SOURCE_DIR/" \
    "$HETZNER_SSH_HOST:$HETZNER_REMOTE_SOURCE_DIR/"
fi

if $SYNC_ONLY; then
  log "Sync complete."
  exit 0
fi

if ! $DEPLOY_ONLY; then
  log "Step 2/3: Building Docker image on Hetzner..."
  remote_cmd "cd '$HETZNER_REMOTE_SOURCE_DIR' && docker build -t '$image_ref' ."
fi

if $BUILD_ONLY; then
  log "Build complete."
  exit 0
fi

log "Step 3/3: Recreating authority container..."
remote_cmd "docker rm -f '$AUTHORITY_CONTAINER_NAME' 2>/dev/null || true"
remote_cmd "docker run -d \
  --name '$AUTHORITY_CONTAINER_NAME' \
  --network '$AUTHORITY_DOCKER_NETWORK' \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8000:8000 \
  --env-file '$HETZNER_REMOTE_ENV_FILE' \
  '$image_ref'"

if [[ -n "$AUTHORITY_HEALTH_URL" ]]; then
  log "Running health check: $AUTHORITY_HEALTH_URL"
  if $DRY_RUN; then
    printf '+ curl -fsS \"%s\"\n' "$AUTHORITY_HEALTH_URL"
  else
    sleep 3
    if curl -fsS "$AUTHORITY_HEALTH_URL" >/dev/null; then
      log "Health check passed."
    else
      die "Health check failed for $AUTHORITY_HEALTH_URL"
    fi
  fi
fi

log "Deployment complete."
log "Container: $AUTHORITY_CONTAINER_NAME"
log "Image:     $image_ref"
