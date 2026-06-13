#!/bin/bash

set -euo pipefail

MODE="${1:-status}"

AUTHORITY_BASE_URL="${AUTHORITY_BASE_URL:-https://authority.eyenet-vision.com}"
GATEWAY_BASE_URL="${GATEWAY_BASE_URL:-http://localhost:8080}"
AUTHORITY_ADMIN_TOKEN="${AUTHORITY_ADMIN_TOKEN:-}"
AUTHORITY_ADMIN_EMAIL="${AUTHORITY_ADMIN_EMAIL:-}"
AUTHORITY_ADMIN_PASSWORD="${AUTHORITY_ADMIN_PASSWORD:-}"

INSTALLATION_UUID="${INSTALLATION_UUID:-tenant-a}"
APPLICATION_KEY="${APPLICATION_KEY:-lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f}"
CURRENT_DEV_OWNER_EMAIL="${CURRENT_DEV_OWNER_EMAIL:-nick.glezakos@gmail.com}"
PENDING_OWNER_EMAIL="${PENDING_OWNER_EMAIL:-bootstrap.owner@example.com}"
TENANT_NAME="${TENANT_NAME:-Tenant A}"
OFFLINE_GRACE_DAYS="${OFFLINE_GRACE_DAYS:-14}"

print_usage() {
  cat <<'EOF'
Usage:
  scripts/bootstrap-state.sh status
  scripts/bootstrap-state.sh pending
  scripts/bootstrap-state.sh restore

Environment variables:
  AUTHORITY_BASE_URL        Authority base URL. Default: https://authority.eyenet-vision.com
  GATEWAY_BASE_URL          Gateway base URL. Default: http://localhost:8080
  AUTHORITY_ADMIN_TOKEN     Optional explicit bearer token for pending and restore modes
  AUTHORITY_ADMIN_EMAIL     Optional login email used to obtain a session token
  AUTHORITY_ADMIN_PASSWORD  Optional login password used to obtain a session token
  INSTALLATION_UUID         Installation identifier value. Default: tenant-a
  APPLICATION_KEY           Default: lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f
  CURRENT_DEV_OWNER_EMAIL   Default: nick.glezakos@gmail.com
  PENDING_OWNER_EMAIL       Default: bootstrap.owner@example.com
  TENANT_NAME               Default: Tenant A
  OFFLINE_GRACE_DAYS        Default: 14

Examples:
  AUTHORITY_ADMIN_TOKEN=... scripts/bootstrap-state.sh pending
  AUTHORITY_ADMIN_EMAIL=... AUTHORITY_ADMIN_PASSWORD=... scripts/bootstrap-state.sh pending
  AUTHORITY_ADMIN_TOKEN=... scripts/bootstrap-state.sh restore
  AUTHORITY_ADMIN_EMAIL=... AUTHORITY_ADMIN_PASSWORD=... scripts/bootstrap-state.sh restore
  scripts/bootstrap-state.sh status
EOF
}

require_admin_token() {
  if [[ -n "$AUTHORITY_ADMIN_TOKEN" ]]; then
    return 0
  fi

  if [[ -z "$AUTHORITY_ADMIN_EMAIL" || -z "$AUTHORITY_ADMIN_PASSWORD" ]]; then
    echo "Set AUTHORITY_ADMIN_TOKEN or AUTHORITY_ADMIN_EMAIL and AUTHORITY_ADMIN_PASSWORD for this operation." >&2
    exit 1
  fi

  AUTHORITY_ADMIN_TOKEN="$({
    AUTHORITY_BASE_URL="$AUTHORITY_BASE_URL" \
    AUTHORITY_ADMIN_EMAIL="$AUTHORITY_ADMIN_EMAIL" \
    AUTHORITY_ADMIN_PASSWORD="$AUTHORITY_ADMIN_PASSWORD" \
    AUTHORITY_VERIFY_ME=true \
    sh "$(dirname "$0")/../autonomous/ppl-meta-authority/scripts/get_authority_session_token.sh"
  })"

  if [[ -z "$AUTHORITY_ADMIN_TOKEN" ]]; then
    echo "Failed to obtain AUTHORITY_ADMIN_TOKEN from Authority login." >&2
    exit 1
  fi
}

print_request_failure() {
  local label="$1"
  local url="$2"
  echo "$label unavailable at $url"
}

print_status() {
  echo
  echo "Authority installation by installation identifier:"
  if ! curl -fsS "$AUTHORITY_BASE_URL/api/v1/installations/$INSTALLATION_UUID"; then
    print_request_failure "Authority installation endpoint" "$AUTHORITY_BASE_URL/api/v1/installations/$INSTALLATION_UUID"
  fi
  echo
  echo
  echo "Node bootstrap status through gateway:"
  if ! curl -fsS "$GATEWAY_BASE_URL/api/v1/licensing/bootstrap/status"; then
    print_request_failure "Gateway bootstrap status endpoint" "$GATEWAY_BASE_URL/api/v1/licensing/bootstrap/status"
    return 1
  fi
  echo
}

upsert_installation() {
  local owner_email="$1"
  local notes="$2"

  require_admin_token

  curl -fsS -X POST "$AUTHORITY_BASE_URL/api/v1/admin/installations" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $AUTHORITY_ADMIN_TOKEN" \
    -d "{
      \"installation_uuid\": \"$INSTALLATION_UUID\",
      \"application_key\": \"$APPLICATION_KEY\",
      \"approved_owner_email\": \"$owner_email\",
      \"owner_enabled\": true,
      \"licence_status\": \"active\",
      \"offline_grace_days\": $OFFLINE_GRACE_DAYS,
      \"tenant_name\": \"$TENANT_NAME\",
      \"notes\": \"$notes\"
    }"
  echo
}

case "$MODE" in
  status)
    print_status
    ;;
  pending)
    upsert_installation "$PENDING_OWNER_EMAIL" "Temporary bootstrap pending state for development testing"
    echo
    echo "Bootstrap has been switched to pending in Authority."
    echo "Restart Node now so startup reconciliation refreshes the approved owner mapping."
    print_status
    ;;
  restore)
    upsert_installation "$CURRENT_DEV_OWNER_EMAIL" "Restored current development bootstrap-complete state"
    echo
    echo "Current development bootstrap state has been restored in Authority."
    echo "Restart Node now so startup reconciliation reassigns the approved owner locally."
    print_status
    ;;
  -h|--help|help)
    print_usage
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    print_usage
    exit 1
    ;;
esac