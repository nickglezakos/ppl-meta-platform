#!/bin/sh
set -eu

AUTHORITY_BASE_URL="${AUTHORITY_BASE_URL:-}"
AUTHORITY_ADMIN_EMAIL="${AUTHORITY_ADMIN_EMAIL:-}"
AUTHORITY_ADMIN_PASSWORD="${AUTHORITY_ADMIN_PASSWORD:-}"
AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN="${AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN:-false}"
AUTHORITY_VERIFY_ME="${AUTHORITY_VERIFY_ME:-true}"

if [ -z "$AUTHORITY_BASE_URL" ]; then
  echo 'AUTHORITY_BASE_URL is required' >&2
  exit 1
fi

if [ -z "$AUTHORITY_ADMIN_EMAIL" ]; then
  echo 'AUTHORITY_ADMIN_EMAIL is required' >&2
  exit 1
fi

if [ -z "$AUTHORITY_ADMIN_PASSWORD" ]; then
  echo 'AUTHORITY_ADMIN_PASSWORD is required' >&2
  exit 1
fi

fetch_json() {
  curl --fail --silent --show-error \
    -H 'Content-Type: application/json' \
    "$@"
}

if [ "$AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN" = 'true' ]; then
  fetch_json -X POST "$AUTHORITY_BASE_URL/api/v1/auth/bootstrap-admin" >/dev/null
fi

SESSION_TOKEN="$(fetch_json -X POST "$AUTHORITY_BASE_URL/api/v1/auth/login" \
  -d "{\"email\":\"$AUTHORITY_ADMIN_EMAIL\",\"password\":\"$AUTHORITY_ADMIN_PASSWORD\"}" | sed -n 's/.*"session_token":"\([^"]*\)".*/\1/p')"

if [ -z "$SESSION_TOKEN" ]; then
  echo 'Failed to obtain session token from authority login response' >&2
  exit 1
fi

if [ "$AUTHORITY_VERIFY_ME" = 'true' ]; then
  curl --fail --silent --show-error \
    -H "Authorization: Bearer $SESSION_TOKEN" \
    "$AUTHORITY_BASE_URL/api/v1/auth/me" >/dev/null
fi

printf '%s\n' "$SESSION_TOKEN"