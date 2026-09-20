#!/usr/bin/env bash
# After Stage 2 (Modes A–D): confirm GHCR tags exist, write release manifest, verify digests.
#
# Usage (on Mac or builder with docker login + network to GHCR):
#   RELEASE_TAG=2.25.82 ./scripts/stage2_finalize_manifest.sh
#   RELEASE_TAG=2.25.82 ./scripts/stage2_finalize_manifest.sh --allow-partial
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ALLOW_PARTIAL=0
for arg in "$@"; do
  case "$arg" in
    --allow-partial) ALLOW_PARTIAL=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

RELEASE_TAG="${RELEASE_TAG:-$(tr -d '[:space:]' < VERSION)}"
export RELEASE_TAG

echo "======== Stage 2 finalize: verify tags ========"
./scripts/verify_platform_release.sh "$RELEASE_TAG"

echo
echo "======== Stage 2 finalize: write release manifest ========"
if [[ "$ALLOW_PARTIAL" -eq 1 ]]; then
  ./scripts/write_release_manifest.sh --allow-partial
else
  ./scripts/write_release_manifest.sh
fi

echo
echo "======== Stage 2 finalize: verify release manifest ========"
./scripts/verify_release_manifest.sh

echo
echo "REPORT OK finalize RELEASE_TAG=${RELEASE_TAG} manifest=deployment/windows-installer/release-manifest.yml"
echo "Stage 1 next: commit release-manifest.yml (+ CHANGELOG Notes) and push."
