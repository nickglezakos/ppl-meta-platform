#!/usr/bin/env bash
# Re-register platform services with discovery using compose DNS names.
# Discovery keeps an in-memory registry; recreating it (or a cold start before
# peers finish booting) leaves mobile clients seeing only a partial/unhealthy list.
# Health checks from inside the discovery container work reliably against
# ppl-meta-*:port. ADVERTISE_HOST rewriting still exposes the LAN IP to phones.
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

echo "Waiting for discovery at ${DISCOVERY_URL}/health ..."
for _ in $(seq 1 60); do
  if curl -sf "${DISCOVERY_URL}/health" >/dev/null 2>&1 \
    || curl -sf "${DISCOVERY_URL}/health/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

for pair in "${SERVICES[@]}"; do
  name="${pair%%:*}"
  port="${pair##*:}"
  # Skip if the published port is not up yet (best-effort).
  if ! curl -sf --max-time 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1 \
    && ! curl -sf --max-time 2 "http://127.0.0.1:${port}/health/" >/dev/null 2>&1; then
    echo "skip ${name} (port ${port} not ready)"
    continue
  fi
  body=$(printf '{"name":"%s","service_type":"backend","version":"2.25.82","host":"%s","port":%s,"health_endpoint":"/health","capabilities":[],"metadata":{}}' \
    "$name" "$name" "$port")
  if curl -sf -X POST "${DISCOVERY_URL}/api/v1/services/register" \
    -H "Content-Type: application/json" \
    -d "$body" >/dev/null; then
    echo "registered ${name} -> ${name}:${port}"
  else
    echo "WARN: failed to register ${name}"
  fi
done

echo "Discovery directory:"
curl -sf "${DISCOVERY_URL}/api/v1/services" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for s in sorted(d.get("services",[]), key=lambda x: x["name"]):
    print("  %-28s %s:%s  %s" % (s["name"], s["host"], s["port"], s["status"]))
print("total=%d" % len(d.get("services",[])))
' || curl -sf "${DISCOVERY_URL}/api/v1/services" | head -c 500
echo
