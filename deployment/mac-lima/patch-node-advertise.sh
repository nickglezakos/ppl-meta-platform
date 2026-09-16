#!/usr/bin/env bash
# Patch running ppl-meta-node container:
# - users.py: ADVERTISE_HOST for platform/services URLs
# - mesh_vpn_service.py: soft-fail if tailscale CLI missing (image-compatible)
set -euo pipefail

cd "${HOME}/eyenet-platform"
CID="$(docker compose -f docker-compose.yml -p pplmeta ps -aq ppl-meta-node)"
IMG="$(docker inspect -f '{{.Image}}' "$CID")"
REPO_USERS="/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py"

echo "CID=$CID"
echo "IMG=$IMG"

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

docker create --name node-extract "$IMG" >/dev/null
docker cp node-extract:/app/src/services/mesh_vpn_service.py "$TMP/mesh_vpn_service.py.origin"
docker rm node-extract >/dev/null

python3 - "$TMP/mesh_vpn_service.py.origin" <<'PY'
import sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text()
old = '''        path = shutil.which("tailscale")
        if not path:
            raise RuntimeError(
                "tailscale not found on PATH. Install with: brew install tailscale"
            )
        logger.info("Found tailscale at %s", path)
        return path'''
new = '''        path = shutil.which("tailscale")
        if not path:
            logger.warning(
                "tailscale not found on PATH — VPN status will report uninstalled"
            )
            return ""
        logger.info("Found tailscale at %s", path)
        return path'''
if old in text:
    p.write_text(text.replace(old, new))
    print("patched raise->softfail")
elif "VPN status will report uninstalled" in text:
    print("already softfail")
else:
    raise SystemExit("could not locate _find_tailscale raise pattern in image mesh_vpn_service.py")
PY

docker stop "$CID" || true
sleep 1
docker cp "$REPO_USERS" "$CID":/app/src/api/v1/users.py
docker cp "$TMP/mesh_vpn_service.py.origin" "$CID":/app/src/services/mesh_vpn_service.py
# Image hard-imports netifaces; workspace soft-imports — patch to avoid crash.
docker cp /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/multicast_discovery.py \
  "$CID":/app/src/services/multicast_discovery.py
# Workspace main: TrustedHost ADVERTISE_HOST + skip missing bootstrap users
docker cp /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/main.py \
  "$CID":/app/src/main.py
docker start "$CID"
sleep 3
# Drop host-only helper if a previous attempt copied it (harmless if absent)
docker exec "$CID" rm -f /app/src/services/vpn_login_server.py || true

for i in $(seq 1 40); do
  st="$(docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CID")"
  echo "  $i $st"
  case "$st" in
    running/healthy) break ;;
    exited/*|restarting/*)
      docker logs --tail=50 "$CID"
      exit 1
      ;;
  esac
  sleep 2
done

docker compose -f docker-compose.yml -p pplmeta exec -T ppl-meta-node printenv ADVERTISE_HOST
docker compose -f docker-compose.yml -p pplmeta exec -T ppl-meta-node \
  python -c 'import os; adv=(os.getenv("ADVERTISE_HOST") or "").strip().split(":")[0]; print("advertise_host=", adv); print("expected_register=", f"http://{adv}:8080/api/v1/cameras/mobile")'
