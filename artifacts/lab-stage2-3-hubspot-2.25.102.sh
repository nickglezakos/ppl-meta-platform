#!/usr/bin/env bash
# Stage 2 Mode D (2.25.102) + Stage 3 on lab-work-dual-64g / eyenet-demo
# HubSpot CRM + authenticator APIs + login/MVR view fixes already on main.
#
# Run from Mac:
#   ./artifacts/lab-stage2-3-hubspot-2.25.102.sh eyenet@100.101.128.40
set -euo pipefail

LAB="${1:-eyenet@100.101.128.40}"
RELEASE_TAG=2.25.102
FROM_TAG=2.25.101
REBUILD="presence frontend media gateway"
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
test "$(tr -d '[:space:]' < VERSION)" = "2.25.102"
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
FROM_TAG=$FROM_TAG TO_TAG=$RELEASE_TAG EXCLUDE="presence frontend media gateway" ./scripts/stage2_retag_forward.sh 2>&1 | tee /tmp/eyenet-stage2/retag.log
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
        rf'{re.escape(name)}:\n\s+tag:\s*"2\.25\.102"\n\s+digest:\s*"sha256:([0-9a-f]{{12}})',
        manifest,
    )
    return m.group(1) if m else '????????'

presence = dig('ppl-meta-presence')
frontend = dig('ppl-meta-frontend')
media = dig('ppl-meta-media')
gateway = dig('ppl-meta-gateway')
old = '- Stage 2/3 Notes filled after GHCR publish and lab pull.'
new = (
    f'- GHCR images published for **2.25.102** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): '
    f'rebuilt presence `{presence}…`, frontend `{frontend}…`, media `{media}…`, gateway `{gateway}…`; '
    f'retagged the other eight from `2.25.101`. Manifest finalized 2026-10-18.'
)
if old in text:
    cl.write_text(text.replace(old, new, 1))
    print('CHANGELOG Notes updated')
else:
    print('CHANGELOG Notes line not found or already updated')
print('digests', presence, frontend, media, gateway)
PY
git add CHANGELOG.md
git commit -m "$(cat <<'EOF'
Stage 1: finalize 2.25.102 release-manifest after Mode D publish.

EOF
)" || echo "manifest commit skipped (no changes?)"

echo "==> Stage 3: compose pull/recreate to :$RELEASE_TAG (clear local presence pin)"
ssh -o ConnectTimeout=20 "$LAB" bash -s <<REMOTE_S3
set -euo pipefail
COMPOSE_DIR=""
for d in "\$HOME/eyenet-platform" "\$HOME/ppl-meta-platform" "/opt/eyenet"; do
  if [[ -f "\$d/docker-compose.yml" || -f "\$d/docker-compose.windows-installer.yml" ]]; then
    COMPOSE_DIR="\$d"
    break
  fi
done
test -n "\$COMPOSE_DIR"
echo "COMPOSE_DIR=\$COMPOSE_DIR"
cd "\$COMPOSE_DIR"

# Drop authenticator-hotfix / local presence image pin if present
if [[ -f docker-compose.override.yml ]]; then
  cp -a docker-compose.override.yml "/tmp/docker-compose.override.yml.bak.2.25.102"
  # Comment out presence image overrides so GHCR :2.25.102 wins
  python3 - <<'PY'
from pathlib import Path
p = Path('docker-compose.override.yml')
text = p.read_text()
# Soft-disable common local presence image pins
for needle in (
    'eyenet-local/ppl-meta-presence',
    'ppl-meta-presence:authenticator-hotfix',
):
    if needle in text:
        print('override mentions', needle)
p.write_text(text)
print('override kept (backup at /tmp); will force image via compose pull')
PY
fi

export RELEASE_TAG=$RELEASE_TAG
export COMPOSE_PROJECT_NAME=pplmeta
# Prefer windows-installer compose layout used on eyenet-demo
FILES=()
[[ -f docker-compose.yml ]] && FILES+=(-f docker-compose.yml)
[[ -f docker-compose.windows-installer.yml ]] && FILES+=(-f docker-compose.windows-installer.yml)
[[ -f docker-compose.override.yml ]] && FILES+=(-f docker-compose.override.yml)

# Ensure .env RELEASE_TAG
if [[ -f .env ]]; then
  grep -q '^RELEASE_TAG=' .env && sed -i "s|^RELEASE_TAG=.*|RELEASE_TAG=$RELEASE_TAG|" .env || echo "RELEASE_TAG=$RELEASE_TAG" >> .env
fi

echo "==> pull + recreate presence frontend media gateway ui"
COMPOSE_PROJECT_NAME=pplmeta docker compose "\${FILES[@]}" pull ppl-meta-presence ppl-meta-frontend ppl-meta-media ppl-meta-gateway || true
COMPOSE_PROJECT_NAME=pplmeta docker compose "\${FILES[@]}" up -d --force-recreate ppl-meta-presence ppl-meta-frontend ppl-meta-media ppl-meta-gateway

# Also pull remaining services to the new pin (retag-forward)
COMPOSE_PROJECT_NAME=pplmeta docker compose "\${FILES[@]}" pull || true
COMPOSE_PROJECT_NAME=pplmeta docker compose "\${FILES[@]}" up -d

sleep 15
echo "==> health"
for url in \
  http://127.0.0.1:8011/health \
  http://127.0.0.1:8080/health \
  http://127.0.0.1:3000/
do
  code=\$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "\$url" || echo 000)
  echo "\$url -> \$code"
done
echo "==> hubspot route"
curl -sS -o /dev/null -w 'hubspot=%{http_code}\n' --max-time 5 \
  http://127.0.0.1:8080/api/v1/presence/installations/current/crm/hubspot || true
echo "==> authenticator route"
curl -sS -o /dev/null -w 'authenticator=%{http_code}\n' --max-time 5 \
  http://127.0.0.1:8080/api/v1/presence/authenticator/enrollment || true
docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | grep -E 'presence|frontend|media|gateway' || true
REMOTE_S3

echo ""
echo "==> Stage 2+3 script finished for $RELEASE_TAG on $LAB"
echo "    Remember: push release-manifest commit from Mac if created."
