#!/bin/bash
# Verify that all Windows installer platform images exist on GHCR for a release tag.

set -euo pipefail

RELEASE_TAG="${1:-$(tr -d '[:space:]' < "$(dirname "$0")/../VERSION")}"
REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"

IMAGES=(
  ppl-meta-node
  ppl-meta-media
  ppl-meta-gateway
  ppl-meta-orchestrator
  ppl-meta-discovery
  ppl-meta-communications
  ppl-meta-frontend
  ppl-meta-vision-protected
  ppl-meta-vmeta-protected
)

echo "Verifying platform release ${RELEASE_TAG} at ${REGISTRY}"
echo

missing=0
for image in "${IMAGES[@]}"; do
  ref="${REGISTRY}/${image}:${RELEASE_TAG}"
  if docker manifest inspect "$ref" >/dev/null 2>&1; then
    echo "OK      ${ref}"
  else
    echo "MISSING ${ref}"
    missing=$((missing + 1))
  fi
done

echo
if (( missing > 0 )); then
  echo "FAILED: ${missing} image(s) missing for ${RELEASE_TAG}"
  exit 1
fi

echo "PASSED: all ${#IMAGES[@]} images present for ${RELEASE_TAG}"
