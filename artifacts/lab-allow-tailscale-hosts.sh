#!/usr/bin/env bash
# Harden lab node TrustedHost for Tailscale + LAN.
#
# Keeps ADVERTISE_HOST on the LAN IP (so discovery URLs stay LAN-correct) and
# sets ALLOWED_HOSTS=LAN,TAILSCALE so direct :8001 login over VPN no longer
# returns HTTP 400 "Invalid host header".
#
# Usage:
#   ./artifacts/lab-allow-tailscale-hosts.sh [eyenet@HOST]
# Example:
#   ./artifacts/lab-allow-tailscale-hosts.sh eyenet@100.101.128.40
set -euo pipefail

LAB="${1:-eyenet@100.101.128.40}"

ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 "$LAB" bash -s <<'EOF'
set -euo pipefail
cd ~/eyenet-platform

TS_IP="$(tailscale ip -4 2>/dev/null | head -1 || true)"
LAN_IP="$(hostname -I | tr ' ' '\n' | grep -E '^(192\.|10\.)' | head -1 || true)"
if [[ -z "${LAN_IP:-}" ]]; then
  LAN_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
fi
if [[ -z "${LAN_IP:-}" ]]; then
  echo "ERROR: could not detect LAN IP" >&2
  exit 1
fi
if [[ -z "${TS_IP:-}" ]]; then
  echo "ERROR: could not detect Tailscale IPv4 (is tailscaled up?)" >&2
  exit 1
fi

ALLOW="${LAN_IP},${TS_IP}"
echo "LAN_IP=$LAN_IP TS_IP=$TS_IP ALLOWED_HOSTS=$ALLOW"

cp -a .env ".env.bak.$(date +%Y%m%d%H%M%S)"

if grep -q '^ADVERTISE_HOST=' .env; then
  sed -i -e "s/^ADVERTISE_HOST=.*/ADVERTISE_HOST=${LAN_IP}/" .env
else
  echo "ADVERTISE_HOST=${LAN_IP}" >> .env
fi

if grep -q '^ALLOWED_HOSTS=' .env; then
  sed -i -e "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=${ALLOW}/" .env
else
  echo "ALLOWED_HOSTS=${ALLOW}" >> .env
fi

echo "=== .env ==="
grep -E '^(ADVERTISE_HOST|ALLOWED_HOSTS|RELEASE_TAG)=' .env

COMPOSE=""
for f in docker-compose.windows-installer.yml docker-compose.yml; do
  [[ -f "$f" ]] && COMPOSE="$f" && break
done
PROJECT="$(docker ps --format '{{.Names}}' | grep ppl-meta-media | head -1 | sed 's/-ppl-meta-media.*//' || echo pplmeta)"
echo "COMPOSE=$COMPOSE PROJECT=$PROJECT"

# TrustedHostMiddleware allow-list is fixed at process start — must recreate.
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env up -d --force-recreate --no-deps \
  ppl-meta-node ppl-meta-discovery ppl-meta-gateway

for i in $(seq 1 30); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8001/health/ || echo 000)"
  [[ "$code" == "200" ]] && break
  sleep 2
done

if [[ -x ./reregister-discovery-services.sh ]]; then
  RELEASE_TAG="$(grep '^RELEASE_TAG=' .env | cut -d= -f2-)" ./reregister-discovery-services.sh || true
fi

NODE="$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-node' | head -1)"
echo "=== node env ==="
docker exec "$NODE" printenv ADVERTISE_HOST ALLOWED_HOSTS

echo "=== verify (must not say Invalid host header) ==="
curl -sS -w '\nLAN HTTP:%{http_code}\n' --max-time 5 -X POST "http://${LAN_IP}:8001/api/v1/users/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=probe@example.com&password=probe' | head -c 240 || true
echo
curl -sS -w '\nTS HTTP:%{http_code}\n' --max-time 5 -X POST "http://${TS_IP}:8001/api/v1/users/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=probe@example.com&password=probe' | head -c 240 || true
echo
echo "Expected: JSON detail Incorrect email/password (or 200 with real creds) — NOT Invalid host header"
EOF
