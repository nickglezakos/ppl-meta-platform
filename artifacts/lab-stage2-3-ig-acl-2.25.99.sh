#!/usr/bin/env bash
# Stage 2 Mode D (2.25.99) + Stage 3 on lab-work-dual-64g
# for individual-group stable member numbers + private member manage ACL.
#
# Run from Mac (LAN/Tailscale to lab):
#   ./artifacts/lab-stage2-3-ig-acl-2.25.99.sh eyenet@192.168.9.13
#   ./artifacts/lab-stage2-3-ig-acl-2.25.99.sh eyenet@100.101.128.40
set -euo pipefail

LAB="${1:-eyenet@192.168.9.13}"
RELEASE_TAG=2.25.99
FROM_TAG=2.25.98
REBUILD="vmeta gateway presence frontend"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Lab: $LAB  pin: $RELEASE_TAG  rebuild: $REBUILD"
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
test "$(tr -d '[:space:]' < VERSION)" = "2.25.99"
echo "$REPO" > /tmp/eyenet-stage2-repo-path
REMOTE_PULL

echo "==> Stage 2 rebuild: $REBUILD"
ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=120 "$LAB" bash -s <<REMOTE_S2
set -euo pipefail
REPO=\$(cat /tmp/eyenet-stage2-repo-path)
cd "\$REPO"
export RELEASE_TAG=$RELEASE_TAG
export EXTRA_SHA_TAG=1
mkdir -p /tmp/eyenet-stage2
./scripts/check_installer_pins.sh
for s in $REBUILD; do
  echo "======== building \$s ========"
  EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh "\$s" 2>&1 | tee "/tmp/eyenet-stage2/\${s}.log"
  grep -E '^REPORT OK|^REPORT FAIL|^REPORT DONE' "/tmp/eyenet-stage2/\${s}.log" || true
  grep -q '^REPORT OK' "/tmp/eyenet-stage2/\${s}.log"
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
want = {
    'ppl-meta-vmeta-protected': None,
    'ppl-meta-gateway': None,
    'ppl-meta-presence': None,
    'ppl-meta-frontend': None,
}
for name in list(want):
    m = re.search(
        rf'{re.escape(name)}:\n\s+tag:\s*"2\.25\.99"\n\s+digest:\s*"sha256:([0-9a-f]{{12}})',
        manifest,
    )
    if m:
        want[name] = m.group(1)
vmeta = want['ppl-meta-vmeta-protected'] or '????????'
gateway = want['ppl-meta-gateway'] or '????????'
presence = want['ppl-meta-presence'] or '????????'
frontend = want['ppl-meta-frontend'] or '????????'
old = (
    '- GHCR images for **2.25.99** (Mode D): rebuild vmeta + gateway + presence + frontend; '
    'retag-forward the other eight from `2.25.98`. Stage 3 on `lab-work-dual-64g` after publish.'
)
new = (
    f'- GHCR images published for **2.25.99** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): '
    f'rebuilt vmeta-protected `{vmeta}…`, gateway `{gateway}…`, presence `{presence}…`, '
    f'frontend `{frontend}…`; retagged the other eight from `2.25.98`. '
    f'Manifest finalized 2026-10-13.'
)
if old in text:
    cl.write_text(text.replace(old, new, 1))
    print('CHANGELOG Notes updated')
else:
    print('CHANGELOG Notes line not found or already updated')
print('digests:', want)
PY
git add CHANGELOG.md

git commit -m "$(cat <<'EOF'
Stage 1: finalize 2.25.99 manifest after vmeta/gateway/presence/frontend publish.

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
echo "==> Verify member_number column"
POSTGRES=\$(docker ps --format '{{.Names}}' | grep -E 'postgres|ppl-postgres' | head -1 || true)
if [[ -n "\$POSTGRES" ]]; then
  docker exec "\$POSTGRES" psql -U "\${POSTGRES_USER:-pplmeta}" -d "\${POSTGRES_DB:-ppl_db}" -tAc \
    "SELECT column_name FROM information_schema.columns WHERE table_name='group_memberships' AND column_name='member_number';" || true
fi
for s in vmeta gateway presence frontend; do
  cid=\$(docker ps --format '{{.Names}}' | grep -E "ppl-meta-\${s}" | head -1 || true)
  if [[ -n "\$cid" ]]; then
    echo "---- \$cid ----"
    docker inspect "\$cid" --format 'Image={{.Config.Image}}'
  fi
done
grep '^RELEASE_TAG=' .env
REMOTE_S3

echo "==> Done. Hard-refresh UI and verify:"
echo "    - membership numbers stay stable on add"
echo "    - private foreign members: no link/delete icons"
echo "    Tracker: docs/documentation/deployment/HOTFIXES_NOTES.md → move to Completed"
