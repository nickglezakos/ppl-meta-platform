#!/usr/bin/env bash
# Hotfix: renumber individual-group memberships oldest-first.
#
# After 023, newest members were Member 01. Product rule is chronological:
# first join = Group Member 01, later joins get higher numbers.
#
# Applies SQL 024 only (vmeta already allocates MAX+1).
#
# Usage: ./artifacts/lab-hotfix-renumber-group-members-oldest-first.sh [eyenet@HOST]
set -euo pipefail

LAB="${1:-eyenet@100.101.128.40}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_TMP=/tmp/eyenet-hotfix-renumber-members-oldest-first
SQL="$REPO/ppl-meta-vmeta/migrations/024_renumber_group_members_oldest_first.sql"

echo "==> Lab: $LAB"
test -f "$SQL"
ssh -o ConnectTimeout=15 "$LAB" "rm -rf $REMOTE_TMP && mkdir -p $REMOTE_TMP/sql"
scp "$SQL" "$LAB:$REMOTE_TMP/sql/"

ssh "$LAB" bash -s <<'EOF'
set -euo pipefail
REMOTE_TMP=/tmp/eyenet-hotfix-renumber-members-oldest-first

POSTGRES=$(docker ps --format '{{.Names}}' | grep -E 'postgres|ppl-postgres' | head -1)
echo "POSTGRES=$POSTGRES"
test -n "$POSTGRES"

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

echo "==> Before (sample)"
docker exec "$POSTGRES" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT group_id, individual_id, member_number, added_at
   FROM group_memberships
   ORDER BY group_id, added_at ASC
   LIMIT 12;"

echo "==> Apply SQL 024_renumber_group_members_oldest_first"
docker exec -i "$POSTGRES" \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < "$REMOTE_TMP/sql/024_renumber_group_members_oldest_first.sql"

echo "==> After (sample)"
docker exec "$POSTGRES" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT group_id, individual_id, member_number, added_at
   FROM group_memberships
   ORDER BY group_id, added_at ASC
   LIMIT 12;"

echo "==> Check rank vs added_at (should be empty)"
docker exec "$POSTGRES" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "WITH ranked AS (
     SELECT id, member_number,
            ROW_NUMBER() OVER (
              PARTITION BY group_id
              ORDER BY added_at ASC, individual_id ASC
            ) AS expected
     FROM group_memberships
   )
   SELECT * FROM ranked WHERE member_number IS DISTINCT FROM expected;"
EOF

echo "==> Done. Refresh the group members screen; oldest should be Member 01."
