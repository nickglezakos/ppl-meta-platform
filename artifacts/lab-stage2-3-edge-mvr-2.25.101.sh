#!/usr/bin/env bash
# Stage 2 Mode D (2.25.101) one-service-at-a-time + Stage 3 on lab-work-dual-64g
# for edge Record/MVR: media frame auth, vision FPS contamination, cameras/FE Record≠ID.
#
# Run from Mac (LAN/Tailscale to lab):
#   ./artifacts/lab-stage2-3-edge-mvr-2.25.101.sh eyenet@192.168.9.13
#   ./artifacts/lab-stage2-3-edge-mvr-2.25.101.sh eyenet@100.101.128.40
set -euo pipefail

LAB="${1:-eyenet@192.168.9.13}"
RELEASE_TAG=2.25.101
FROM_TAG=2.25.100
REBUILD="media vision cameras frontend"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Lab: $LAB  pin: $RELEASE_TAG  rebuild (one-at-a-time): $REBUILD"
ssh -o ConnectTimeout=15 "$LAB" "hostname; hostname -I; free -h | head -2; df -h / | tail -1"

echo "==> Locate monorepo + pull main"
ssh "$LAB" bash -s <<'REMOTE_PULL'
set -euo pipefail
REPO=""
for d in "$HOME/ppl-meta-platform" "$HOME/ppl-meta-code"; do
  if [[ -d "$d/.git" && -f "$d/scripts/stage2_one.sh" ]]; then
    REPO="$d"
    break
  fi
done
if [[ -z "$REPO" ]]; then
  echo "No Stage 2 monorepo found under ~/ppl-meta-platform or ~/ppl-meta-code"
  exit 1
fi
echo "REPO=$REPO"
cd "$REPO"
git fetch origin
git checkout main
git reset --hard origin/main
git clean -fd -- deployment/windows-installer/schema/ 2>/dev/null || true
git rev-parse --short HEAD
test "$(tr -d '[:space:]' < VERSION)" = "2.25.101"
echo "$REPO" > /tmp/eyenet-stage2-repo-path
REMOTE_PULL

echo "==> Stage 2 rebuild one-at-a-time: $REBUILD"
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=120 "$LAB" bash -s <<REMOTE_S2
set -euo pipefail
REPO=\$(cat /tmp/eyenet-stage2-repo-path)
cd "\$REPO"
export RELEASE_TAG=$RELEASE_TAG
export EXTRA_SHA_TAG=1
mkdir -p /tmp/eyenet-stage2
./scripts/check_installer_pins.sh
for s in $REBUILD; do
  echo "======== building \$s $(date -Is) ========"
  EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh "\$s" 2>&1 | tee "/tmp/eyenet-stage2/\${s}.log"
  grep -E '^REPORT OK|^REPORT FAIL|^REPORT DONE' "/tmp/eyenet-stage2/\${s}.log" || true
  grep -q '^REPORT OK' "/tmp/eyenet-stage2/\${s}.log"
  echo "======== OK \$s $(date -Is) ========"
done
echo "======== retag-forward $FROM_TAG → $RELEASE_TAG (exclude rebuilt) ========"
FROM_TAG=$FROM_TAG TO_TAG=$RELEASE_TAG EXCLUDE="$REBUILD" ./scripts/stage2_retag_forward.sh 2>&1 | tee /tmp/eyenet-stage2/retag.log
echo "======== finalize manifest ========"
RELEASE_TAG=$RELEASE_TAG ./scripts/stage2_finalize_manifest.sh 2>&1 | tee /tmp/eyenet-stage2/finalize.log
echo "STAGE2_DONE"
REMOTE_S2

echo "==> Copy release-manifest.yml back to Mac"
REPO_REMOTE=$(ssh "$LAB" 'cat /tmp/eyenet-stage2-repo-path')
scp "$LAB:$REPO_REMOTE/deployment/windows-installer/release-manifest.yml" \
  "$ROOT/deployment/windows-installer/release-manifest.yml"

cd "$ROOT"
git add deployment/windows-installer/release-manifest.yml

python3 <<'PY'
from pathlib import Path
import re
manifest = Path('deployment/windows-installer/release-manifest.yml').read_text()
cl = Path('CHANGELOG.md')
text = cl.read_text()

def dig(name: str) -> str:
    m = re.search(
        rf'{re.escape(name)}:\n\s+tag:\s*"2\.25\.101"\n\s+digest:\s*"sha256:([0-9a-f]{{12}})',
        manifest,
    )
    return m.group(1) if m else '????????'

media = dig('ppl-meta-media')
vision = dig('ppl-meta-vision-protected') or dig('ppl-meta-vision')
cameras = dig('ppl-meta-cameras')
frontend = dig('ppl-meta-frontend')
old = (
    '- Affects `ppl-meta-media`, `ppl-meta-vision`, `ppl-meta-cameras`, `ppl-meta-frontend`. '
    'Mode D: rebuild those four; retag-forward the other eight from `2.25.100`.'
)
new = (
    f'- GHCR images published for **2.25.101** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): '
    f'rebuilt media `{media}…`, vision-protected `{vision}…`, cameras `{cameras}…`, '
    f'frontend `{frontend}…`; retagged the other eight from `2.25.100`. '
    f'Manifest finalized 2026-10-16.'
)
if old in text:
    cl.write_text(text.replace(old, new, 1))
    print('CHANGELOG Notes updated')
else:
    print('CHANGELOG Notes line not found or already updated')
print('digests:', media, vision, cameras, frontend)
PY
git add CHANGELOG.md

git commit -m "$(cat <<'EOF'
Stage 1: finalize 2.25.101 manifest after media/vision/cameras/frontend publish.

EOF
)" || echo "(manifest commit may already exist)"
git push origin HEAD

echo "==> Stage 3: upgrade Ubuntu install on lab"
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=60 "$LAB" bash -s <<REMOTE_S3
set -euo pipefail
INSTALL="\$HOME/eyenet-platform"
cd "\$INSTALL"
if [[ -f .env ]]; then
  sed -i.bak -e "s/^RELEASE_TAG=.*/RELEASE_TAG=$RELEASE_TAG/" .env
  grep '^RELEASE_TAG=' .env
fi
COMPOSE=docker-compose.yml
[[ -f docker-compose.windows-installer.yml ]] && COMPOSE=docker-compose.windows-installer.yml
SRC=\$(cat /tmp/eyenet-stage2-repo-path 2>/dev/null || true)
if [[ -n "\${SRC:-}" && -d "\$SRC/deployment/windows-installer" ]]; then
  cp "\$SRC/deployment/windows-installer/docker-compose.windows-installer.yml" "\$INSTALL/" 2>/dev/null || true
  rsync -a --delete "\$SRC/deployment/windows-installer/schema/" "\$INSTALL/schema/" 2>/dev/null || \
    cp -a "\$SRC/deployment/windows-installer/schema/." "\$INSTALL/schema/" 2>/dev/null || true
fi
docker compose -p pplmeta -f "\$COMPOSE" --env-file .env pull
docker compose -p pplmeta -f "\$COMPOSE" --env-file .env up -d --remove-orphans
if [[ -x ./schema/apply.sh ]]; then
  echo "==> schema/apply.sh"
  ./schema/apply.sh || true
elif [[ -n "\${SRC:-}" && -x "\$SRC/deployment/windows-installer/schema/apply.sh" ]]; then
  (cd "\$SRC/deployment/windows-installer" && bash schema/apply.sh) || true
fi
if [[ -x ./reregister-discovery-services.sh ]]; then
  RELEASE_TAG=$RELEASE_TAG ./reregister-discovery-services.sh || true
fi
sleep 8
echo "==> Health"
curl -sS -o /dev/null -w "ui:%{http_code}\\n" --max-time 10 http://127.0.0.1:3000/ || true
curl -sS -o /dev/null -w "gw:%{http_code}\\n" --max-time 10 http://127.0.0.1:8080/health || true
curl -sS -o /dev/null -w "media:%{http_code}\\n" --max-time 10 http://127.0.0.1:8000/health || true
echo "==> Image tags"
for name in media vision cameras frontend; do
  cid=\$(docker ps --format '{{.Names}}' | grep -E "ppl-meta-\${name}" | head -1 || true)
  if [[ -n "\$cid" ]]; then
    echo "---- \$cid ----"
    docker inspect "\$cid" --format 'Image={{.Config.Image}}'
  fi
done
grep '^RELEASE_TAG=' .env
REMOTE_S3

echo "==> Done Stage 2+3 for $RELEASE_TAG. Hard-refresh UI; re-test edge Record → Details/MVR."
