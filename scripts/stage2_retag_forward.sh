#!/usr/bin/env bash
# Mode D — retag-forward: point TO_TAG at the same digests as FROM_TAG (no rebuild).
#
# Use on a platform pin bump when only some services changed:
#   1. Rebuild changed services at TO_TAG (stage2_one.sh)
#   2. Retag the rest FROM_TAG → TO_TAG
#   3. write_release_manifest.sh + verify
#
# Usage (on build host, logged into GHCR):
#   FROM_TAG=2.25.81 TO_TAG=2.25.82 ./scripts/stage2_retag_forward.sh
#   FROM_TAG=2.25.81 TO_TAG=2.25.82 ./scripts/stage2_retag_forward.sh node media gateway
#   FROM_TAG=2.25.81 TO_TAG=2.25.82 EXCLUDE="cameras frontend" ./scripts/stage2_retag_forward.sh
#
# Requires: docker buildx (imagetools create).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=platform_release_images.sh
source "$ROOT/scripts/platform_release_images.sh"

REGISTRY="${REGISTRY:-$PLATFORM_REGISTRY_DEFAULT}"
FROM_TAG="${FROM_TAG:-}"
TO_TAG="${TO_TAG:-$(tr -d '[:space:]' < "$ROOT/VERSION")}"
EXCLUDE="${EXCLUDE:-}"

if [[ -z "$FROM_TAG" ]]; then
  echo "FROM_TAG is required (previous platform pin to copy digests from)." >&2
  echo "Example: FROM_TAG=2.25.81 TO_TAG=2.25.82 $0" >&2
  exit 2
fi

if [[ "$FROM_TAG" == "$TO_TAG" ]]; then
  echo "FROM_TAG and TO_TAG must differ (got ${FROM_TAG})." >&2
  exit 2
fi

if [[ $# -gt 0 ]]; then
  KEYS=("$@")
else
  KEYS=("${PLATFORM_SERVICE_KEYS[@]}")
fi

# Filter EXCLUDE (space-separated keys)
filtered=()
for key in "${KEYS[@]}"; do
  skip=0
  for ex in $EXCLUDE; do
    if [[ "$key" == "$ex" ]]; then skip=1; break; fi
  done
  if [[ "$skip" -eq 0 ]]; then
    filtered+=("$key")
  fi
done
KEYS=("${filtered[@]}")

if [[ ${#KEYS[@]} -eq 0 ]]; then
  echo "No services left to retag after EXCLUDE=${EXCLUDE}" >&2
  exit 2
fi

if ! docker buildx imagetools create --help >/dev/null 2>&1; then
  echo "docker buildx imagetools create is required for retag-forward." >&2
  exit 1
fi

echo "Retag-forward ${FROM_TAG} → ${TO_TAG} at ${REGISTRY}"
echo "Services: ${KEYS[*]}"
echo

for key in "${KEYS[@]}"; do
  image="$(platform_image_name_for_key "$key")"
  src="$(platform_image_ref "$REGISTRY" "$image" "$FROM_TAG")"
  dst="$(platform_image_ref "$REGISTRY" "$image" "$TO_TAG")"
  echo "======== retag ${key}: ${FROM_TAG} → ${TO_TAG} ========"
  if ! platform_resolve_digest "$src" >/dev/null; then
    echo "REPORT FAIL service=${key} reason=missing_source ref=${src}" >&2
    exit 1
  fi
  docker buildx imagetools create --tag "$dst" "$src"
  digest="$(platform_resolve_digest "$dst")"
  echo "REPORT OK service=${key} from=${FROM_TAG} to=${TO_TAG} digest=${digest} ref=${dst}"
done

echo "REPORT DONE retag-forward from=${FROM_TAG} to=${TO_TAG} services=${KEYS[*]}"
echo "Next: ./scripts/write_release_manifest.sh && ./scripts/verify_release_manifest.sh"
