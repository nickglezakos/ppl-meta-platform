#!/usr/bin/env bash
set -euo pipefail

log() { printf "%s\n" "$*"; }
die() { printf "ERROR: %s\n" "$*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

need_cmd tailscale
need_cmd curl

TARGET_URL="${1:-${TARGET_URL:-}}"
if [ -z "$TARGET_URL" ]; then
  TARGET_URL="http://localhost:8080/health"
fi

log "🔍 VPN connection check"
log "Target: $TARGET_URL"

log "➡️  tailscale status"
tailscale status

log "➡️  tailscale ip"
tailscale ip -4 || true

log "➡️  HTTP check"
curl -fsS "$TARGET_URL" | head -c 400 || die "Failed to reach $TARGET_URL"
echo
log "✅ OK"
