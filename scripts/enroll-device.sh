#!/usr/bin/env bash
set -euo pipefail

log() { printf "%s\n" "$*"; }
warn() { printf "WARN: %s\n" "$*" >&2; }
die() { printf "ERROR: %s\n" "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

json_get() {
  # Usage: json_get '<json>' 'path.to.key'
  local json="$1"
  local path="$2"
  if command -v jq >/dev/null 2>&1; then
    # shellcheck disable=SC2001
    jq -r ".${path} // empty" <<<"$json"
  else
  python - "$path" <<'PY' <<<"$json"
import json, sys

doc = json.loads(sys.stdin.read() or "{}")
path = sys.argv[1].split(".")

cur = doc
for p in path:
  if isinstance(cur, dict) and p in cur:
    cur = cur[p]
  else:
    cur = ""
    break

if cur is None:
  cur = ""

if isinstance(cur, str):
  print(cur)
else:
  print(json.dumps(cur))
PY
  fi
}

json_get_array() {
  # Usage: json_get_array '<json>' 'path.to.array'
  local json="$1"
  local path="$2"
  if command -v jq >/dev/null 2>&1; then
    jq -c ".${path} // []" <<<"$json"
  else
  python - "$path" <<'PY' <<<"$json"
import json, sys

doc = json.loads(sys.stdin.read() or "{}")
path = sys.argv[1].split(".")

cur = doc
for p in path:
  if isinstance(cur, dict) and p in cur:
    cur = cur[p]
  else:
    cur = []
    break

if cur is None:
  cur = []

print(json.dumps(cur))
PY
  fi
}

to_json_string_array() {
  # Input: comma-separated string OR repeated args.
  # Output: JSON array of strings.
  if [ "$#" -gt 1 ]; then
    if command -v jq >/dev/null 2>&1; then
      printf '%s\n' "$@" | jq -R . | jq -s .
    else
      printf '%s\n' "$@" | python - <<'PY'
import json, sys
print(json.dumps([l.strip() for l in sys.stdin.readlines() if l.strip()]))
PY
    fi
    return 0
  fi

  local raw="${1:-}"
  if [ -z "${raw//[[:space:]]/}" ]; then
    echo '[]'
    return 0
  fi

  if command -v jq >/dev/null 2>&1; then
    # Split CSV, trim whitespace around entries, drop empties.
    jq -c -n --arg raw "$raw" '$raw | split(",") | map(gsub("^\\s+|\\s+$"; "")) | map(select(length>0))'
  else
    python - <<'PY' <<<"$raw"
import json, sys
raw = sys.stdin.read()
parts = [p.strip() for p in raw.split(',')]
parts = [p for p in parts if p]
print(json.dumps(parts))
PY
  fi
}

need_cmd curl

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
USERNAME="${USERNAME:-}"
PASSWORD="${PASSWORD:-}"

DEVICE_TYPE="${DEVICE_TYPE:-camera}"
DEVICE_NAME="${DEVICE_NAME:-}"
TAGS_CSV="${TAGS:-tag:${DEVICE_TYPE}}"

log "🔐 PPL Meta Headscale enrollment"
log "Gateway: $GATEWAY_URL"

if [ -z "$USERNAME" ]; then
  read -r -p "Gateway username/email: " USERNAME
fi
if [ -z "$PASSWORD" ]; then
  read -r -s -p "Gateway password: " PASSWORD
  echo
fi
if [ -z "$DEVICE_NAME" ]; then
  read -r -p "Device name (hostname): " DEVICE_NAME
fi

log "➡️  Logging in to gateway..."
LOGIN_JSON=$(curl -fsS -X POST "${GATEWAY_URL%/}/api/v1/users/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=${USERNAME}" \
  --data-urlencode "password=${PASSWORD}") || die "Login failed"

TOKEN=$(json_get "$LOGIN_JSON" "access_token")
if [ -z "$TOKEN" ]; then
  die "Login response did not include access_token"
fi

TAGS_JSON=$(to_json_string_array "$TAGS_CSV")

log "➡️  Requesting device enrollment key..."
ENROLL_JSON=$(curl -fsS -X POST "${GATEWAY_URL%/}/api/v1/vpn/devices/enroll" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{\"device_type\":\"${DEVICE_TYPE}\",\"device_name\":\"${DEVICE_NAME}\",\"tags\":${TAGS_JSON}}") \
  || die "Enroll request failed"

AUTH_KEY=$(json_get "$ENROLL_JSON" "auth_key")
LOGIN_SERVER=$(json_get "$ENROLL_JSON" "instructions.headscale_url")

if [ -z "$AUTH_KEY" ]; then
  die "Enroll response did not include auth_key"
fi
if [ -z "$LOGIN_SERVER" ]; then
  warn "No instructions.headscale_url returned; falling back to HEADSCALE_URL env"
  LOGIN_SERVER="${HEADSCALE_URL:-}"
fi
if [ -z "$LOGIN_SERVER" ]; then
  die "Headscale login server URL not set (instructions.headscale_url missing and HEADSCALE_URL not set)"
fi

log "✅ Got auth key from gateway"

if ! command -v tailscale >/dev/null 2>&1; then
  case "$(uname -s)" in
    Linux)
      warn "tailscale CLI not found. You can install it with: curl -fsSL https://tailscale.com/install.sh | sh"
      ;;
    Darwin)
      warn "tailscale CLI not found. Install Tailscale for macOS (app + CLI) from https://tailscale.com/download"
      ;;
    *)
      warn "tailscale CLI not found. Install it from https://tailscale.com/download"
      ;;
  esac
  die "tailscale is required on the device"
fi

UP_CMD=(tailscale up --login-server "$LOGIN_SERVER" --auth-key "$AUTH_KEY" --hostname "$DEVICE_NAME" --accept-dns=true)

log "➡️  Bringing up Tailscale against Headscale..."
if [ "$(id -u)" -eq 0 ]; then
  "${UP_CMD[@]}" >/dev/null
else
  if command -v sudo >/dev/null 2>&1; then
    sudo "${UP_CMD[@]}" >/dev/null
  else
    die "Need root privileges to run tailscale up (sudo not available)"
  fi
fi

log "✅ tailscale up completed"

if tailscale ip -4 >/dev/null 2>&1; then
  VPN_IP=$(tailscale ip -4 | head -n 1 || true)
  if [ -n "$VPN_IP" ]; then
    log "📍 VPN IPv4: $VPN_IP"
  fi
fi

log "🔎 Quick status:"
tailscale status || true

log "✅ Enrollment done"
