#!/bin/sh
set -eu

AUTHORITY_BASE_URL="${AUTHORITY_BASE_URL:-}"
AUTHORITY_ADMIN_EMAIL="${AUTHORITY_ADMIN_EMAIL:-}"
AUTHORITY_ADMIN_PASSWORD="${AUTHORITY_ADMIN_PASSWORD:-}"
AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN="${AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN:-}"
AUTHORITY_TEST_APPLICATION_KEY="${AUTHORITY_TEST_APPLICATION_KEY:-}"
AUTHORITY_TEST_OWNER_EMAIL="${AUTHORITY_TEST_OWNER_EMAIL:-}"
AUTHORITY_TEST_INSTALLATION_UUID="${AUTHORITY_TEST_INSTALLATION_UUID:-}"

if [ -z "$AUTHORITY_BASE_URL" ]; then
  echo 'AUTHORITY_BASE_URL is required'
  exit 1
fi

fetch_json() {
  curl --fail --silent --show-error \
    -H 'Content-Type: application/json' \
    "$@"
}

wait_for_health() {
  attempt=1
  while [ "$attempt" -le 30 ]; do
    if fetch_json "$AUTHORITY_BASE_URL/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  fetch_json "$AUTHORITY_BASE_URL/health" >/dev/null
}

wait_for_admin_shell() {
  attempt=1
  while [ "$attempt" -le 30 ]; do
    if curl --fail --silent --show-error "$AUTHORITY_BASE_URL/admin" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  curl --fail --silent --show-error "$AUTHORITY_BASE_URL/admin" >/dev/null
}

echo 'Checking health endpoint...'
wait_for_health

echo 'Checking admin shell...'
wait_for_admin_shell

SESSION_TOKEN=''
if [ -n "$AUTHORITY_ADMIN_EMAIL" ] && [ -n "$AUTHORITY_ADMIN_PASSWORD" ]; then
  if [ "$AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN" = 'true' ]; then
    echo 'Bootstrapping initial admin...'
    fetch_json -X POST "$AUTHORITY_BASE_URL/api/v1/auth/bootstrap-admin" >/dev/null
  fi

  echo 'Checking authenticated login...'
  SESSION_TOKEN="$(fetch_json -X POST "$AUTHORITY_BASE_URL/api/v1/auth/login" \
    -d "{\"email\":\"$AUTHORITY_ADMIN_EMAIL\",\"password\":\"$AUTHORITY_ADMIN_PASSWORD\"}" | sed -n 's/.*"session_token":"\([^"]*\)".*/\1/p')"

  if [ -z "$SESSION_TOKEN" ]; then
    echo 'Failed to obtain session token from authority login response'
    exit 1
  fi

  curl --fail --silent --show-error \
    -H "Authorization: Bearer $SESSION_TOKEN" \
    "$AUTHORITY_BASE_URL/api/v1/auth/me" >/dev/null
fi

if [ -n "$AUTHORITY_TEST_APPLICATION_KEY" ] && [ -n "$AUTHORITY_TEST_OWNER_EMAIL" ] && [ -n "$AUTHORITY_TEST_INSTALLATION_UUID" ]; then
  echo 'Checking activation contract...'
  ACTIVATION_RESPONSE="$(fetch_json -X POST "$AUTHORITY_BASE_URL/api/v1/installations/activate" \
    -d "{\"application_key\":\"$AUTHORITY_TEST_APPLICATION_KEY\",\"installation_uuid\":\"$AUTHORITY_TEST_INSTALLATION_UUID\",\"owner_email\":\"$AUTHORITY_TEST_OWNER_EMAIL\"}")"

  echo "$ACTIVATION_RESPONSE" | grep '"approved":true' >/dev/null
  echo "$ACTIVATION_RESPONSE" | grep '"installation_uuid":"'$AUTHORITY_TEST_INSTALLATION_UUID'"' >/dev/null
fi

echo 'Authority deployment checks passed.'
