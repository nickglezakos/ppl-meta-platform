#!/bin/zsh

set -euo pipefail

TOKEN="${PRESENCE_RESET_TOKEN:-}"
BASE_URL="${PRESENCE_RESET_BASE_URL:-http://localhost}"
INSTALLATION_UUID="${PRESENCE_RESET_INSTALLATION_UUID:-local-installation}"

if [[ -z "$TOKEN" ]]; then
  echo "Set PRESENCE_RESET_TOKEN before running reset_presence_reservations.sh"
  exit 1
fi

curl -s \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"installation_uuid\":\"$INSTALLATION_UUID\"}" \
  "$BASE_URL/api/presence/installations/current/reset-reservations" | python3 -m json.tool