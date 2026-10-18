#!/usr/bin/env bash
# Hotfix eyenet-demo: HubSpot ↔ Presence CRM (Settings UI + import + grant outbound).
# Presence: docker-cp hubspot_crm.py + models/service/routes from local repo.
# Frontend: Flutter web build + docker-cp.
#
# Usage:
#   ./artifacts/lab-hotfix-hubspot-crm.sh [eyenet@HOST]
#   SKIP_FLUTTER_BUILD=1 ./artifacts/lab-hotfix-hubspot-crm.sh
#
# Debug only — not a Stage 2/3 release.
set -euo pipefail

LAB="${1:-eyenet@100.101.128.40}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_TMP=/tmp/eyenet-hotfix-hubspot-crm
SKIP_FLUTTER_BUILD="${SKIP_FLUTTER_BUILD:-0}"

echo "==> Lab: $LAB"
echo "==> Repo: $REPO"

# --- Frontend web build (Mac) ---
if [[ "$SKIP_FLUTTER_BUILD" != "1" ]]; then
  echo "==> Flutter web build"
  (
    cd "$REPO/ppl-meta-frontend"
    flutter pub get
    flutter build web --release
  )
else
  echo "==> SKIP_FLUTTER_BUILD=1 — using existing build/web"
fi
test -f "$REPO/ppl-meta-frontend/build/web/main.dart.js"
grep -q "HubSpot CRM" "$REPO/ppl-meta-frontend/build/web/main.dart.js" \
  || { echo "ERROR: 'HubSpot CRM' not found in main.dart.js — rebuild frontend"; exit 1; }
grep -q "crm/hubspot" "$REPO/ppl-meta-frontend/build/web/main.dart.js" \
  || { echo "ERROR: 'crm/hubspot' not found in main.dart.js — rebuild frontend"; exit 1; }

# --- Stage files on lab ---
ssh -o ConnectTimeout=15 "$LAB" "rm -rf $REMOTE_TMP && mkdir -p $REMOTE_TMP/frontend $REMOTE_TMP/presence"

scp \
  "$REPO/ppl-meta-presence/src/services/hubspot_crm.py" \
  "$REPO/ppl-meta-presence/src/models/presence_models.py" \
  "$REPO/ppl-meta-presence/src/services/presence_service.py" \
  "$REPO/ppl-meta-presence/src/api/presence_routes.py" \
  "$LAB:$REMOTE_TMP/presence/"

rsync -az \
  "$REPO/ppl-meta-frontend/build/web/main.dart.js" \
  "$REPO/ppl-meta-frontend/build/web/flutter_service_worker.js" \
  "$REPO/ppl-meta-frontend/build/web/version.json" \
  "$REPO/ppl-meta-frontend/build/web/flutter.js" \
  "$REPO/ppl-meta-frontend/build/web/flutter_bootstrap.js" \
  "$REPO/ppl-meta-frontend/build/web/index.html" \
  "$LAB:$REMOTE_TMP/frontend/"

# --- Apply inside containers ---
ssh -o ConnectTimeout=20 "$LAB" bash -s <<'EOF'
set -euo pipefail
REMOTE_TMP=/tmp/eyenet-hotfix-hubspot-crm

PRES=$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-presence' | head -1)
FE=$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-frontend' | head -1)
echo "PRES=$PRES"
echo "FE=$FE"
test -n "$PRES"
test -n "$FE"

echo "==> Backup presence files"
docker exec "$PRES" mkdir -p /tmp/hotfix-backup-hubspot-crm
docker exec "$PRES" cp -a /app/src/services/presence_service.py /tmp/hotfix-backup-hubspot-crm/ || true
docker exec "$PRES" cp -a /app/src/api/presence_routes.py /tmp/hotfix-backup-hubspot-crm/ || true
docker exec "$PRES" cp -a /app/src/models/presence_models.py /tmp/hotfix-backup-hubspot-crm/ || true
docker exec "$PRES" sh -c 'test -f /app/src/services/hubspot_crm.py && cp -a /app/src/services/hubspot_crm.py /tmp/hotfix-backup-hubspot-crm/ || true'

echo "==> docker cp presence HubSpot sources"
docker cp "$REMOTE_TMP/presence/hubspot_crm.py" "$PRES:/app/src/services/hubspot_crm.py"
docker cp "$REMOTE_TMP/presence/presence_models.py" "$PRES:/app/src/models/presence_models.py"
docker cp "$REMOTE_TMP/presence/presence_service.py" "$PRES:/app/src/services/presence_service.py"
docker cp "$REMOTE_TMP/presence/presence_routes.py" "$PRES:/app/src/api/presence_routes.py"

echo "==> Verify presence markers"
docker exec "$PRES" grep -n 'crm_hubspot\|HubSpotCrmConfig\|_notify_hubspot_grant' /app/src/services/presence_service.py | head -15
docker exec "$PRES" grep -n 'crm/hubspot\|UpdateHubSpotCrmConfigRequest' /app/src/api/presence_routes.py | head -15
docker exec "$PRES" grep -n 'class HubSpotCrmConfig\|hubspot_posted' /app/src/models/presence_models.py | head -10
docker exec "$PRES" test -f /app/src/services/hubspot_crm.py

echo "==> Import check"
docker exec -i "$PRES" python - <<'PY'
import sys
sys.path.insert(0, '/app/src')
from services.hubspot_crm import map_hubspot_contact, grant_note_body
from models.presence_models import HubSpotCrmConfig, HubSpotCrmConfigPublic
c = map_hubspot_contact({"id": "1", "properties": {"firstname": "A", "lastname": "B", "email": "a@b.c"}})
assert c and c.contact_id == "1" and c.display_name == "A B"
assert "session_uuid=x" in grant_note_body(session_uuid="x", grant_type="check_in", assurance_level="low", person_name="N", occurred_at=None)
pub = HubSpotCrmConfigPublic(token_configured=True)
assert "access_token" not in pub.model_dump()
print("import_ok", HubSpotCrmConfig().enabled)
PY

echo "==> Restart presence"
docker restart "$PRES"
for i in $(seq 1 25); do
  sleep 2
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 3 -L http://127.0.0.1:8011/health || echo 000)
  echo "try $i presence health=$code"
  [[ "$code" == "200" || "$code" == "307" ]] && break
done

echo "==> Probe HubSpot routes (expect 401/403 without auth, not 404/500)"
for path in \
  /api/v1/presence/installations/current/crm/hubspot \
  /api/v1/presence/installations/current/crm/hubspot/test \
  /api/v1/presence/installations/current/crm/hubspot/sync
do
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 -X GET "http://127.0.0.1:8011${path}" 2>/dev/null || echo 000)
  # test/sync are POST; GET may 405 — still proves route exists
  if [[ "$path" == *"/test" || "$path" == *"/sync" ]]; then
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 -X POST "http://127.0.0.1:8011${path}" || echo 000)
  fi
  echo "presence ${path} -> $code"
  [[ "$code" == "401" || "$code" == "403" || "$code" == "200" || "$code" == "405" || "$code" == "422" ]] \
    || { echo "WARN: unexpected status $code for $path"; }
done

echo "==> openapi hubspot paths"
curl -sS http://127.0.0.1:8011/openapi.json | python3 -c '
import json,sys
d=json.load(sys.stdin)
paths=[p for p in d.get("paths",{}) if "hubspot" in p]
print("hubspot routes:", paths)
assert any("/crm/hubspot" in p for p in paths), "missing hubspot routes"
'

echo "==> gateway probe (optional)"
curl -sS -o /dev/null -w "gateway_hubspot=%{http_code}\n" --max-time 5 \
  http://127.0.0.1:8080/api/v1/presence/installations/current/crm/hubspot || true

echo "==> Backup + docker cp frontend"
docker exec "$FE" mkdir -p /tmp/hotfix-backup-hubspot-crm
docker exec "$FE" cp -a /usr/share/nginx/html/main.dart.js /tmp/hotfix-backup-hubspot-crm/ || true

docker cp "$REMOTE_TMP/frontend/main.dart.js" "$FE:/usr/share/nginx/html/main.dart.js"
docker cp "$REMOTE_TMP/frontend/flutter_service_worker.js" "$FE:/usr/share/nginx/html/flutter_service_worker.js"
docker cp "$REMOTE_TMP/frontend/version.json" "$FE:/usr/share/nginx/html/version.json"
docker cp "$REMOTE_TMP/frontend/flutter.js" "$FE:/usr/share/nginx/html/flutter.js"
docker cp "$REMOTE_TMP/frontend/flutter_bootstrap.js" "$FE:/usr/share/nginx/html/flutter_bootstrap.js"
docker cp "$REMOTE_TMP/frontend/index.html" "$FE:/usr/share/nginx/html/index.html"

docker exec "$FE" grep -o 'HubSpot CRM' /usr/share/nginx/html/main.dart.js | head -3
docker exec "$FE" nginx -s reload || docker restart "$FE"

sleep 2
ui=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:3000/ || echo 000)
echo "ui=$ui"
test "$ui" = "200"

docker ps --filter name=presence --format '{{.Names}} {{.Image}} {{.Status}}'
docker ps --filter name=frontend --format '{{.Names}} {{.Image}} {{.Status}}'
EOF

echo ""
echo "==> Hotfix applied on $LAB"
echo "    UI: http://100.101.128.40:3000/ (hard-refresh)"
echo "    Presence → Settings → HubSpot CRM"
