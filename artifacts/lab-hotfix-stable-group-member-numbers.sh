#!/usr/bin/env bash
# Hotfix lab for:
#   1) Stable individual-group membership numbers (SQL 023 + vmeta)
#   2) Private-group member manage ACL (no link/delete without face media access)
#
# Symptom A: adding an MVR renumbers members so the newest becomes "Member 01".
# Symptom B: in a private group you can see your own member faces but not another
#            user's face, yet you can still link/delete that other member.
#
# Applies:
#   - SQL 023 into Postgres
#   - docker-cp vmeta manager/model/routes
#   - docker-cp gateway router (permissions proxy)
#   - docker-cp presence routes (link/unlink gate)
#   - restart vmeta + gateway + presence
#
# Note: Flutter UI hide of link/delete needs a frontend Stage 2 rebuild.
#       Until then APIs still return 403 so actions fail safely.
#
# Usage: ./artifacts/lab-hotfix-stable-group-member-numbers.sh [eyenet@HOST]
set -euo pipefail

LAB="${1:-eyenet@100.101.128.40}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_TMP=/tmp/eyenet-hotfix-stable-member-numbers

echo "==> Lab: $LAB"
ssh -o ConnectTimeout=15 "$LAB" "rm -rf $REMOTE_TMP && mkdir -p \
  $REMOTE_TMP/sql \
  $REMOTE_TMP/vmeta/services \
  $REMOTE_TMP/vmeta/models \
  $REMOTE_TMP/vmeta/routes \
  $REMOTE_TMP/gateway \
  $REMOTE_TMP/presence"

scp "$REPO/ppl-meta-vmeta/migrations/023_stable_group_member_numbers.sql" \
  "$LAB:$REMOTE_TMP/sql/"
scp "$REPO/ppl-meta-vmeta/src/services/individual_groups_manager.py" \
  "$LAB:$REMOTE_TMP/vmeta/services/"
scp "$REPO/ppl-meta-vmeta/src/models/individual_group.py" \
  "$LAB:$REMOTE_TMP/vmeta/models/"
scp "$REPO/ppl-meta-vmeta/src/api/routes/individual_groups.py" \
  "$LAB:$REMOTE_TMP/vmeta/routes/"
scp "$REPO/ppl-meta-gateway/src/api/v1/router.py" \
  "$LAB:$REMOTE_TMP/gateway/"
scp "$REPO/ppl-meta-presence/src/api/presence_routes.py" \
  "$LAB:$REMOTE_TMP/presence/"

ssh "$LAB" bash -s <<'EOF'
set -euo pipefail
REMOTE_TMP=/tmp/eyenet-hotfix-stable-member-numbers

POSTGRES=$(docker ps --format '{{.Names}}' | grep -E 'postgres|ppl-postgres' | head -1)
VMETA=$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-vmeta' | head -1)
GATEWAY=$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-gateway' | head -1)
PRESENCE=$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-presence' | head -1)
echo "POSTGRES=$POSTGRES"
echo "VMETA=$VMETA"
echo "GATEWAY=$GATEWAY"
echo "PRESENCE=$PRESENCE"
test -n "$POSTGRES"
test -n "$VMETA"
test -n "$GATEWAY"
test -n "$PRESENCE"

POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
POSTGRES_DB="${POSTGRES_DB:-ppl_db}"
if [[ -f "$HOME/eyenet-platform/.env" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$HOME/eyenet-platform/.env"; set +a
fi
if [[ -f "$HOME/eyenet-platform/.env.windows" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$HOME/eyenet-platform/.env.windows"; set +a
fi
POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
POSTGRES_DB="${POSTGRES_DB:-ppl_db}"

echo "==> Apply SQL 023_stable_group_member_numbers"
docker exec -i "$POSTGRES" \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < "$REMOTE_TMP/sql/023_stable_group_member_numbers.sql"

echo "==> Verify schema"
docker exec "$POSTGRES" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT column_name FROM information_schema.columns
   WHERE table_name='group_memberships' AND column_name='member_number';"
docker exec "$POSTGRES" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT to_regclass('public.group_member_number_reservations');"

BACKUP=/tmp/eyenet-hotfix-stable-member-numbers/backup
mkdir -p "$BACKUP/vmeta" "$BACKUP/gateway" "$BACKUP/presence"
docker cp "$VMETA:/app/src/services/individual_groups_manager.py" \
  "$BACKUP/vmeta/" 2>/dev/null || true
docker cp "$VMETA:/app/src/models/individual_group.py" \
  "$BACKUP/vmeta/" 2>/dev/null || true
docker cp "$VMETA:/app/src/api/routes/individual_groups.py" \
  "$BACKUP/vmeta/" 2>/dev/null || true
docker cp "$GATEWAY:/app/api/v1/router.py" \
  "$BACKUP/gateway/" 2>/dev/null || true
docker cp "$PRESENCE:/app/src/api/presence_routes.py" \
  "$BACKUP/presence/" 2>/dev/null || \
  docker cp "$PRESENCE:/app/api/presence_routes.py" \
  "$BACKUP/presence/" 2>/dev/null || true

echo "==> docker-cp vmeta"
docker cp "$REMOTE_TMP/vmeta/services/individual_groups_manager.py" \
  "$VMETA:/app/src/services/individual_groups_manager.py"
docker cp "$REMOTE_TMP/vmeta/models/individual_group.py" \
  "$VMETA:/app/src/models/individual_group.py"
docker cp "$REMOTE_TMP/vmeta/routes/individual_groups.py" \
  "$VMETA:/app/src/api/routes/individual_groups.py"

echo "==> docker-cp gateway"
docker cp "$REMOTE_TMP/gateway/router.py" "$GATEWAY:/app/api/v1/router.py"

echo "==> docker-cp presence"
if docker exec "$PRESENCE" test -f /app/src/api/presence_routes.py; then
  docker cp "$REMOTE_TMP/presence/presence_routes.py" \
    "$PRESENCE:/app/src/api/presence_routes.py"
elif docker exec "$PRESENCE" test -f /app/api/presence_routes.py; then
  docker cp "$REMOTE_TMP/presence/presence_routes.py" \
    "$PRESENCE:/app/api/presence_routes.py"
else
  echo "WARN: presence_routes.py path not found in container; skipping presence cp"
fi

echo "==> Verify patches"
docker exec "$VMETA" grep -n '_allocate_member_number\|can_manage_member\|user_can_manage_member' \
  /app/src/services/individual_groups_manager.py | head -10
docker exec "$VMETA" grep -n 'can_manage_member\|get_member_permissions' \
  /app/src/api/routes/individual_groups.py | head -10
docker exec "$GATEWAY" grep -n 'members/.*/permissions' /app/api/v1/router.py | head -5

echo "==> Restart vmeta gateway presence"
docker restart "$VMETA" "$GATEWAY" "$PRESENCE"
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 2
  gw=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:8080/health 2>/dev/null || echo 000)
  echo "try $i gateway_health=$gw"
  [[ "$gw" == "200" ]] && break
done
docker ps --filter name='vmeta|gateway|presence' --format '{{.Names}} {{.Status}}'
EOF

echo "==> Done."
echo "    Numbers should stay stable; private foreign members cannot be linked/deleted (API 403)."
echo "    Frontend icon hide needs Stage 2 frontend rebuild."
echo "    Tracker: docs/documentation/deployment/HOTFIXES_NOTES.md"
