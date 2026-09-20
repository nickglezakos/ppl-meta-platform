#!/bin/bash
# Verify that all Windows installer platform images exist on GHCR for a release tag.
# Tag presence only — for digest coherence see verify_release_manifest.sh (Mode D).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=platform_release_images.sh
source "$SCRIPT_DIR/platform_release_images.sh"

RELEASE_TAG="${1:-$(tr -d '[:space:]' < "$SCRIPT_DIR/../VERSION")}"
REGISTRY="${REGISTRY:-$PLATFORM_REGISTRY_DEFAULT}"

echo "Verifying platform release ${RELEASE_TAG} at ${REGISTRY}"
echo

missing=0
for image in "${PLATFORM_IMAGE_NAMES[@]}"; do
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

echo "PASSED: all ${#PLATFORM_IMAGE_NAMES[@]} images present for ${RELEASE_TAG}"
echo "Tip: ./scripts/stage2_finalize_manifest.sh  # write+verify digest release-manifest.yml"
