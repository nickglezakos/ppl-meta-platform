#!/usr/bin/env bash
# Re-register platform services with discovery using compose DNS names.
# Discovery keeps an in-memory registry; recreating it (or a cold start before
# peers finish booting) leaves the Network page seeing only a partial list
# (often just the gateway, which self-registers).
#
# Health checks from *inside* the discovery container against ppl-meta-*:port
# work on WSL. Checking 127.0.0.1 from the WSL distro often misses published
# ports (localhostForwarding / NAT), which used to skip every service except
# whichever ones happened to answer on loopback.
# ADVERTISE_HOST rewriting still exposes the LAN IP to phones.
set -euo pipefail

DISCOVERY_URL="${DISCOVERY_URL:-http://127.0.0.1:8006}"
SERVICES=(
  "ppl-meta-discovery:8006"
  "ppl-meta-gateway:8080"
  "ppl-meta-node:8001"
  "ppl-meta-cameras:8005"
  "ppl-meta-communications:8009"
  "ppl-meta-models:8013"
  "ppl-meta-presence:8011"
  "ppl-meta-media:8000"
  "ppl-meta-orchestrator:8002"
  "ppl-meta-vision:8003"
  "ppl-meta-vmeta:8008"
)

discovery_cid() {
  docker ps -q --filter "name=ppl-meta-discovery" --filter "status=running" | head -1
}

register_from_inside_discovery() {
  local cid="$1"
  echo "Registering via discovery container ${cid} (compose DNS health checks)..."
  docker exec -i "$cid" python - "$RELEASE_TAG" <<'PY'
import json, sys, urllib.error, urllib.request

version = sys.argv[1] if len(sys.argv) > 1 else "2.25.83"
pairs = [
    ("ppl-meta-discovery", 8006),
    ("ppl-meta-gateway", 8080),
    ("ppl-meta-node", 8001),
    ("ppl-meta-cameras", 8005),
    ("ppl-meta-communications", 8009),
    ("ppl-meta-models", 8013),
    ("ppl-meta-presence", 8011),
    ("ppl-meta-media", 8000),
    ("ppl-meta-orchestrator", 8002),
    ("ppl-meta-vision", 8003),
    ("ppl-meta-vmeta", 8008),
]

def healthy(name, port):
    for path in ("/health", "/health/"):
        try:
            urllib.request.urlopen(f"http://{name}:{port}{path}", timeout=2)
            return True
        except Exception:
            continue
    return False

def register(name, port):
    body = json.dumps({
        "name": name,
        "service_type": "backend",
        "version": version,
        "host": name,
        "port": port,
        "health_endpoint": "/health",
        "capabilities": [],
        "metadata": {},
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8006/api/v1/services/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)

for name, port in pairs:
    if not healthy(name, port):
        print(f"skip {name} (compose DNS :{port} not ready)")
        continue
    try:
        register(name, port)
        print(f"registered {name} -> {name}:{port}")
    except Exception as exc:
        print(f"WARN: failed to register {name}: {exc}")
PY
}

echo "Waiting for discovery ..."
CID="$(discovery_cid || true)"
for _ in $(seq 1 60); do
  CID="$(discovery_cid || true)"
  if [[ -n "${CID}" ]]; then
    if docker exec "$CID" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8006/health', timeout=2)" >/dev/null 2>&1; then
      break
    fi
  fi
  if curl -sf --max-time 2 "${DISCOVERY_URL}/health" >/dev/null 2>&1 \
    || curl -sf --max-time 2 "${DISCOVERY_URL}/health/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

RELEASE_TAG="${RELEASE_TAG:-2.25.83}"
if [[ -n "${CID:-}" ]]; then
  register_from_inside_discovery "$CID"
else
  echo "Discovery container not found; falling back to ${DISCOVERY_URL} + 127.0.0.1 health checks"
  for pair in "${SERVICES[@]}"; do
    name="${pair%%:*}"
    port="${pair##*:}"
    if ! curl -sf --max-time 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1 \
      && ! curl -sf --max-time 2 "http://127.0.0.1:${port}/health/" >/dev/null 2>&1; then
      echo "skip ${name} (port ${port} not ready on 127.0.0.1)"
      continue
    fi
    body=$(printf '{"name":"%s","service_type":"backend","version":"%s","host":"%s","port":%s,"health_endpoint":"/health","capabilities":[],"metadata":{}}' \
      "$name" "$RELEASE_TAG" "$name" "$port")
    if curl -sf -X POST "${DISCOVERY_URL}/api/v1/services/register" \
      -H "Content-Type: application/json" \
      -d "$body" >/dev/null; then
      echo "registered ${name} -> ${name}:${port}"
    else
      echo "WARN: failed to register ${name}"
    fi
  done
fi

echo "Discovery directory:"
if [[ -n "${CID:-}" ]]; then
  docker exec "$CID" python -c '
import json, urllib.request
d=json.load(urllib.request.urlopen("http://127.0.0.1:8006/api/v1/services", timeout=5))
for s in sorted(d.get("services",[]), key=lambda x: x["name"]):
    print("  %-28s %s:%s  %s" % (s["name"], s["host"], s["port"], s["status"]))
print("total=%d healthy=%d" % (d.get("total_count", len(d.get("services",[]))), d.get("healthy_count", 0)))
'
else
  curl -sf "${DISCOVERY_URL}/api/v1/services" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for s in sorted(d.get("services",[]), key=lambda x: x["name"]):
    print("  %-28s %s:%s  %s" % (s["name"], s["host"], s["port"], s["status"]))
print("total=%d" % len(d.get("services",[])))
' || curl -sf "${DISCOVERY_URL}/api/v1/services" | head -c 500
fi
echo
