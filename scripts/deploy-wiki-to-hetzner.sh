#!/usr/bin/env bash
# Rsync built EyeNet wiki static site to Hetzner. Independent of Authority deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL_DIR="${1:-$ROOT/artifacts/wiki-site}"
REMOTE_DIR="${WIKI_REMOTE_DIR:-/home/deploy/apps/ppl-meta-wiki/html}"
WIKI_BASE_URL="${WIKI_BASE_URL:-https://wiki.eyenet-vision.com}"

if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "Local build directory not found: $LOCAL_DIR" >&2
  echo "Run: python3 scripts/build_wiki_static.py --out $LOCAL_DIR" >&2
  exit 1
fi

if [[ ! -f "$LOCAL_DIR/index.html" ]]; then
  echo "Missing $LOCAL_DIR/index.html — build the site first." >&2
  exit 1
fi

: "${HETZNER_HOST:?Set HETZNER_HOST}"
: "${HETZNER_USER:?Set HETZNER_USER}"

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new)
if [[ -n "${HETZNER_SSH_KEY_PATH:-}" ]]; then
  SSH_OPTS+=(-i "$HETZNER_SSH_KEY_PATH")
fi

echo "Ensuring remote directory $REMOTE_DIR"
ssh "${SSH_OPTS[@]}" "$HETZNER_USER@$HETZNER_HOST" "mkdir -p '$REMOTE_DIR'"

echo "Rsync $LOCAL_DIR/ → $HETZNER_USER@$HETZNER_HOST:$REMOTE_DIR/"
# Protect large sideload packages: wiki APK/ZIP trees are gitignored and often
# absent from CI checkouts. --delete would wipe production downloads otherwise.
rsync -avz --delete \
  --filter='P owners-admins/downloads/' \
  --filter='P **/downloads/' \
  -e "ssh ${SSH_OPTS[*]}" \
  "$LOCAL_DIR/" \
  "$HETZNER_USER@$HETZNER_HOST:$REMOTE_DIR/"

echo "Smoke checks against $WIKI_BASE_URL"
for path in /distributors/ /owners-admins/; do
  code="$(curl -fsS -o /dev/null -w '%{http_code}' "$WIKI_BASE_URL$path" || true)"
  if [[ "$code" != "200" ]]; then
    echo "FAIL $WIKI_BASE_URL$path → HTTP $code" >&2
    exit 1
  fi
  echo "OK  $WIKI_BASE_URL$path → $code"
done

echo "Wiki deploy complete."
