#!/usr/bin/env bash
# Make EyeNet platform container packages public on GHCR so installs need no pull login.
#
# Requires: gh auth with read:packages + write:packages (or admin on the packages).
# Usage:
#   ./scripts/make_platform_ghcr_public.sh
#   ./scripts/make_platform_ghcr_public.sh 2.25.80   # tag unused; visibility is per-package

set -euo pipefail

OWNER="${GHCR_OWNER:-nickglezakos}"
# Nested image names under ghcr.io/<owner>/ppl-meta-platform/<image>
PACKAGES=(
  ppl-meta-platform/ppl-meta-node
  ppl-meta-platform/ppl-meta-media
  ppl-meta-platform/ppl-meta-gateway
  ppl-meta-platform/ppl-meta-orchestrator
  ppl-meta-platform/ppl-meta-discovery
  ppl-meta-platform/ppl-meta-communications
  ppl-meta-platform/ppl-meta-frontend
  ppl-meta-platform/ppl-meta-vision-protected
  ppl-meta-platform/ppl-meta-vmeta-protected
  ppl-meta-platform/ppl-meta-cameras
  ppl-meta-platform/ppl-meta-presence
  ppl-meta-platform/ppl-meta-models
)

ok=0
fail=0
for pkg in "${PACKAGES[@]}"; do
  encoded="${pkg//'/'/%2F}"
  echo "Setting public: ghcr.io/${OWNER}/${pkg}"
  if gh api --method PUT \
    -H "Accept: application/vnd.github+json" \
    "/user/packages/container/${encoded}/visibility" \
    -f visibility=public >/dev/null 2>&1; then
    echo "  OK"
    ok=$((ok + 1))
  else
    # Fallback: some accounts use the packages API with PATCH on visibility endpoint variants
    if gh api --method PATCH \
      -H "Accept: application/vnd.github+json" \
      "/user/packages/container/${encoded}" \
      -f visibility=public >/dev/null 2>&1; then
      echo "  OK (patch)"
      ok=$((ok + 1))
    else
      echo "  FAIL — set manually: https://github.com/users/${OWNER}/packages/container/${encoded}/settings"
      fail=$((fail + 1))
    fi
  fi
done

echo
echo "Public: ${ok}  Failed: ${fail}"
if (( fail > 0 )); then
  echo "If API fails with 403, refresh scopes: gh auth refresh -h github.com -s read:packages,write:packages,repo"
  echo "Or in GitHub UI: Package settings → Change visibility → Public"
  exit 1
fi
