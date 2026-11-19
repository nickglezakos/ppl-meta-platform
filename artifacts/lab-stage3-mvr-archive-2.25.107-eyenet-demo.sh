#!/usr/bin/env bash
# Stage 3 on eyenet-demo: MVR soft-archive (2.25.107).
# Run ON the demo box as user eyenet (copy-paste or: bash this-file.sh).
#
# Pulls: frontend, vmeta-protected, gateway, presence @ :2.25.107
# Schema: apply/verify (includes 055_add_mvr_people_archive / is_archived gates)
set -euo pipefail

RELEASE_TAG="${RELEASE_TAG:-2.25.107}"
INSTALL="${INSTALL:-$HOME/eyenet-platform}"
REPO="${REPO:-$HOME/ppl-meta-platform}"

echo "==> Stage 3 eyenet-demo → ${RELEASE_TAG}"
hostname
ip -4 -br addr || true
cd "$INSTALL"
echo "PWD=$(pwd)"

COMPOSE=""
for f in docker-compose.windows-installer.yml docker-compose.yml compose.yml; do
  if [[ -f "$f" ]]; then COMPOSE="$f"; break; fi
done
test -n "$COMPOSE" || { echo "FATAL: no compose file in $INSTALL"; exit 1; }
echo "COMPOSE=$COMPOSE"

PROJECT="${COMPOSE_PROJECT_NAME:-}"
if [[ -z "$PROJECT" ]] && grep -q '^COMPOSE_PROJECT_NAME=' .env 2>/dev/null; then
  PROJECT=$(grep '^COMPOSE_PROJECT_NAME=' .env | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
PROJECT="${PROJECT:-pplmeta}"
echo "PROJECT=$PROJECT"

# Refresh schema pack + compose from monorepo tip (needs git access to origin/main).
if [[ -d "$REPO/.git" ]]; then
  echo "==> Sync $REPO to origin/main"
  git -C "$REPO" fetch origin
  git -C "$REPO" reset --hard origin/main
  if [[ -d "$REPO/deployment/windows-installer/schema" ]]; then
    mkdir -p "$INSTALL/schema"
    rsync -a "$REPO/deployment/windows-installer/schema/" "$INSTALL/schema/" 2>/dev/null \
      || cp -a "$REPO/deployment/windows-installer/schema/." "$INSTALL/schema/"
  fi
fi

if [[ -f .env ]]; then
  if grep -q '^RELEASE_TAG=' .env; then
    sed -i.bak -e "s/^RELEASE_TAG=.*/RELEASE_TAG=${RELEASE_TAG}/" .env
  else
    echo "RELEASE_TAG=${RELEASE_TAG}" >> .env
  fi
fi
grep -E '^(RELEASE_TAG|ADVERTISE_HOST|REGISTRY)=' .env || true

echo "==> Pull archive services @ ${RELEASE_TAG}"
# Service names differ slightly by compose file; pull by image where needed.
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env pull \
  ppl-meta-frontend ppl-meta-gateway ppl-meta-presence ppl-meta-vmeta \
  2>/dev/null || true
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env pull \
  ppl-meta-frontend ppl-meta-gateway ppl-meta-presence ppl-meta-vmeta-protected \
  2>/dev/null || true

# Force-recreate the four; then bring whole stack up on the pin.
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env up -d --force-recreate \
  ppl-meta-frontend ppl-meta-gateway ppl-meta-presence ppl-meta-vmeta \
  2>/dev/null || true
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env up -d --force-recreate \
  ppl-meta-frontend ppl-meta-gateway ppl-meta-presence ppl-meta-vmeta-protected \
  2>/dev/null || true

# Also pull remaining services to the pin (Mode D retags may not all be published yet).
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env pull || true
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file .env up -d

sleep 12

echo "==> Schema apply + verify"
APPLY=""
VERIFY=""
if [[ -x "$INSTALL/schema/apply.sh" ]]; then
  APPLY="$INSTALL/schema/apply.sh"
  VERIFY="$INSTALL/schema/verify.sh"
elif [[ -x "$REPO/deployment/windows-installer/schema/apply.sh" ]]; then
  APPLY="$REPO/deployment/windows-installer/schema/apply.sh"
  VERIFY="$REPO/deployment/windows-installer/schema/verify.sh"
fi
test -n "$APPLY" || { echo "FATAL: schema/apply.sh not found"; exit 1; }
bash "$APPLY"
bash "$VERIFY"

if [[ -x "$INSTALL/reregister-discovery-services.sh" ]]; then
  bash "$INSTALL/reregister-discovery-services.sh" || true
elif [[ -x "$REPO/deployment/windows-installer/reregister-discovery-services.sh" ]]; then
  bash "$REPO/deployment/windows-installer/reregister-discovery-services.sh" || true
fi

echo "==> Digests (expect tag ${RELEASE_TAG})"
for name in frontend gateway presence vmeta; do
  cid=$(docker ps --format '{{.Names}}' | grep -E "ppl-meta-${name}" | head -1 || true)
  if [[ -n "$cid" ]]; then
    docker inspect "$cid" --format '{{.Name}} {{.Config.Image}} {{index .RepoDigests 0}}' 2>/dev/null \
      || docker inspect "$cid" --format '{{.Name}} {{.Config.Image}}'
  else
    echo "MISSING container matching ppl-meta-${name}"
  fi
done

echo "==> Frontend archive UI string smoke"
FE=$(docker ps --format '{{.Names}}' | grep -E 'ppl-meta-frontend' | head -1 || true)
if [[ -n "$FE" ]]; then
  docker exec "$FE" sh -c 'grep -R -l "Show archived\|archive_outlined\|Archive this person" /usr/share/nginx/html 2>/dev/null | head -5' \
    || docker exec "$FE" sh -c 'grep -R -l "Show archived\|Archive this person" /app 2>/dev/null | head -5' \
    || echo "(string grep inconclusive — hard-refresh browser)"
fi

echo "==> Local health"
for url in http://127.0.0.1:3000/ http://127.0.0.1:8080/health; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url" || echo 000)
  echo "$url -> $code"
done

echo "REPORT OK stage3 tag=${RELEASE_TAG} host=$(hostname)"
echo "Hard-refresh UI (Ctrl+Shift+R). Archive icon is on People & Groups member avatars."
