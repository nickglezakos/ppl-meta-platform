#!/usr/bin/env bash
# Stage 3: upgrade existing lab stack to GHCR 2.25.97 (in-place, keep volumes/DB).
# Usage: ./artifacts/lab-stage3-2.25.97.sh eyenet@192.168.9.13
set -euo pipefail

LAB="${1:-eyenet@192.168.9.13}"
RELEASE_TAG=2.25.97

echo "==> Stage 3 in-place upgrade $LAB → $RELEASE_TAG"
ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 "$LAB" bash -s <<EOF
set -euo pipefail
INSTALL="\$HOME/eyenet-platform"
REPO="\$HOME/ppl-meta-platform"
cd "\$INSTALL"
echo "PWD=\$(pwd)"
ls -la docker-compose*.yml .env 2>/dev/null | head -20
grep -E '^(RELEASE_TAG|ADVERTISE_HOST|REGISTRY|COMPOSE_PROJECT_NAME)=' .env || true

COMPOSE=""
for f in docker-compose.windows-installer.yml docker-compose.yml compose.yml; do
  if [[ -f "\$f" ]]; then COMPOSE="\$f"; break; fi
done
if [[ -z "\$COMPOSE" ]]; then
  echo "FATAL: no compose file in \$INSTALL"
  exit 1
fi
echo "COMPOSE=\$COMPOSE"

PROJECT="\${COMPOSE_PROJECT_NAME:-}"
if [[ -z "\$PROJECT" ]] && grep -q '^COMPOSE_PROJECT_NAME=' .env 2>/dev/null; then
  PROJECT=\$(grep '^COMPOSE_PROJECT_NAME=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
if [[ -z "\$PROJECT" ]]; then
  SAMPLE=\$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-media|ppl-postgres' | head -1 || true)
  if [[ "\$SAMPLE" == *-ppl-meta-* ]]; then
    PROJECT="\${SAMPLE%%-ppl-meta-*}"
  elif [[ "\$SAMPLE" == pplmeta-* ]]; then
    PROJECT=pplmeta
  else
    PROJECT=pplmeta
  fi
fi
echo "PROJECT=\$PROJECT"

if [[ -d "\$REPO/.git" ]]; then
  git -C "\$REPO" fetch origin
  git -C "\$REPO" reset --hard origin/main
  if [[ -f "\$REPO/deployment/windows-installer/docker-compose.windows-installer.yml" ]]; then
    cp "\$REPO/deployment/windows-installer/docker-compose.windows-installer.yml" "\$INSTALL/\$COMPOSE" || true
  fi
  if [[ -d "\$REPO/deployment/windows-installer/schema" ]]; then
    mkdir -p "\$INSTALL/schema"
    rsync -a "\$REPO/deployment/windows-installer/schema/" "\$INSTALL/schema/" || \
      cp -a "\$REPO/deployment/windows-installer/schema/." "\$INSTALL/schema/"
  fi
fi

if [[ -f .env ]]; then
  if grep -q '^RELEASE_TAG=' .env; then
    sed -i.bak -e "s/^RELEASE_TAG=.*/RELEASE_TAG=$RELEASE_TAG/" .env
  else
    echo "RELEASE_TAG=$RELEASE_TAG" >> .env
  fi
fi
grep -E '^(RELEASE_TAG|ADVERTISE_HOST)=' .env

echo "==> Pull + recreate existing project (volumes preserved)"
docker compose -p "\$PROJECT" -f "\$COMPOSE" --env-file .env pull
docker compose -p "\$PROJECT" -f "\$COMPOSE" --env-file .env up -d --force-recreate

echo "==> Schema apply/verify + discovery reregister"
if [[ -x schema/apply.sh ]]; then bash schema/apply.sh || true; fi
if [[ -x schema/verify.sh ]]; then bash schema/verify.sh || true; fi
if [[ -x reregister-discovery-services.sh ]]; then
  bash reregister-discovery-services.sh || true
elif [[ -x "\$REPO/deployment/windows-installer/reregister-discovery-services.sh" ]]; then
  bash "\$REPO/deployment/windows-installer/reregister-discovery-services.sh" || true
fi

echo "==> Running image digests (vision / orchestrator)"
for name in ppl-meta-vision-protected ppl-meta-orchestrator; do
  cid=\$(docker ps --filter "name=\$name" --format '{{.ID}}' | head -1 || true)
  if [[ -n "\$cid" ]]; then
    docker inspect "\$cid" --format "{{.Name}} {{.Config.Image}} {{.Image}}"
  fi
done
echo "REPORT OK stage3 tag=$RELEASE_TAG"
EOF
