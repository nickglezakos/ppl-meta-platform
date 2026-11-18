#!/usr/bin/env bash
# Lab debug hotfix for MVR soft-archive (NOT a release).
# Applies schema 055 + docker-cp Python paths into running containers.
# Frontend archive icon still requires Stage 2 frontend image pull.
#
# Usage: ./artifacts/lab-hotfix-mvr-archive.sh [eyenet@HOST]
set -euo pipefail

LAB="${1:-eyenet@192.168.9.13}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_TMP=/tmp/eyenet-hotfix-mvr-archive

echo "==> Lab: $LAB"
ssh -o ConnectTimeout=15 "$LAB" "rm -rf $REMOTE_TMP && mkdir -p \
  $REMOTE_TMP/sql \
  $REMOTE_TMP/vmeta/database \
  $REMOTE_TMP/vmeta/services \
  $REMOTE_TMP/vmeta/models \
  $REMOTE_TMP/vmeta/api_models \
  $REMOTE_TMP/vmeta/routes \
  $REMOTE_TMP/vmeta/ig_routes \
  $REMOTE_TMP/gateway \
  $REMOTE_TMP/presence/api \
  $REMOTE_TMP/presence/models \
  $REMOTE_TMP/presence/services"

scp "$REPO/deployment/windows-installer/schema/pack/055_add_mvr_people_archive.sql" \
  "$LAB:$REMOTE_TMP/sql/"
scp "$REPO/ppl-meta-vmeta/src/database/mvr_repository.py" \
  "$LAB:$REMOTE_TMP/vmeta/database/"
scp "$REPO/ppl-meta-vmeta/src/services/individual_groups_manager.py" \
  "$LAB:$REMOTE_TMP/vmeta/services/"
scp "$REPO/ppl-meta-vmeta/src/models/individual_group.py" \
  "$LAB:$REMOTE_TMP/vmeta/models/"
scp "$REPO/ppl-meta-vmeta/src/api/models/mvr_people.py" \
  "$LAB:$REMOTE_TMP/vmeta/api_models/"
scp "$REPO/ppl-meta-vmeta/src/api/routes/mvr_people.py" \
  "$LAB:$REMOTE_TMP/vmeta/routes/"
scp "$REPO/ppl-meta-vmeta/src/api/routes/individual_groups.py" \
  "$LAB:$REMOTE_TMP/vmeta/ig_routes/"
scp "$REPO/ppl-meta-gateway/src/api/v1/router.py" \
  "$LAB:$REMOTE_TMP/gateway/"
scp "$REPO/ppl-meta-presence/src/api/presence_routes.py" \
  "$LAB:$REMOTE_TMP/presence/api/"
scp "$REPO/ppl-meta-presence/src/models/presence_models.py" \
  "$LAB:$REMOTE_TMP/presence/models/"
scp "$REPO/ppl-meta-presence/src/services/presence_service.py" \
  "$LAB:$REMOTE_TMP/presence/services/"

ssh "$LAB" bash -s <<'EOF'
set -euo pipefail
REMOTE_TMP=/tmp/eyenet-hotfix-mvr-archive

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

PLATFORM_DIR=""
for d in "$HOME/eyenet-platform" /home/eyenet/eyenet-platform /opt/eyenet-platform; do
  if [[ -d "$d" ]]; then PLATFORM_DIR="$d"; break; fi
done
if [[ -n "$PLATFORM_DIR" && -f "$PLATFORM_DIR/.env" ]]; then
  set -a; . "$PLATFORM_DIR/.env"; set +a
fi
POSTGRES_USER="${POSTGRES_USER:-pplmeta}"
POSTGRES_DB="${POSTGRES_DB:-ppl_db}"

echo "==> Apply SQL 055_add_mvr_people_archive"
docker exec -i "$POSTGRES" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$REMOTE_TMP/sql/055_add_mvr_people_archive.sql"

# Discover Python package roots inside containers
VMETA_ROOT=$(docker exec "$VMETA" sh -c 'python -c "import database,os; print(os.path.dirname(database.__file__))"')
VMETA_SRC=$(dirname "$VMETA_ROOT")
GATEWAY_ROUTER=$(docker exec "$GATEWAY" sh -c 'python -c "import api.v1.router as r, os; print(r.__file__)"')
PRESENCE_API=$(docker exec "$PRESENCE" sh -c 'python -c "import api.presence_routes as r, os; print(os.path.dirname(r.__file__))"')
PRESENCE_SRC=$(dirname "$PRESENCE_API")

echo "VMETA_SRC=$VMETA_SRC"
echo "GATEWAY_ROUTER=$GATEWAY_ROUTER"
echo "PRESENCE_SRC=$PRESENCE_SRC"

docker cp "$REMOTE_TMP/vmeta/database/mvr_repository.py" "$VMETA:$VMETA_SRC/database/mvr_repository.py"
docker cp "$REMOTE_TMP/vmeta/services/individual_groups_manager.py" "$VMETA:$VMETA_SRC/services/individual_groups_manager.py"
docker cp "$REMOTE_TMP/vmeta/models/individual_group.py" "$VMETA:$VMETA_SRC/models/individual_group.py"
docker cp "$REMOTE_TMP/vmeta/api_models/mvr_people.py" "$VMETA:$VMETA_SRC/api/models/mvr_people.py"
docker cp "$REMOTE_TMP/vmeta/routes/mvr_people.py" "$VMETA:$VMETA_SRC/api/routes/mvr_people.py"
docker cp "$REMOTE_TMP/vmeta/ig_routes/individual_groups.py" "$VMETA:$VMETA_SRC/api/routes/individual_groups.py"
docker cp "$REMOTE_TMP/gateway/router.py" "$GATEWAY:$GATEWAY_ROUTER"
docker cp "$REMOTE_TMP/presence/api/presence_routes.py" "$PRESENCE:$PRESENCE_SRC/api/presence_routes.py"
docker cp "$REMOTE_TMP/presence/models/presence_models.py" "$PRESENCE:$PRESENCE_SRC/models/presence_models.py"
docker cp "$REMOTE_TMP/presence/services/presence_service.py" "$PRESENCE:$PRESENCE_SRC/services/presence_service.py"

docker restart "$VMETA" "$GATEWAY" "$PRESENCE"
echo "==> Hotfix applied (API/schema). Frontend archive icon still needs Stage 2 frontend image."
EOF
