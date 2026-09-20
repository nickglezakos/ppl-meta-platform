#!/usr/bin/env bash
# Build + push one (or more) Stage 2 services, then print a short status line.
# Survives SSH disconnect better when invoked per-service from the Mac, or inside tmux.
#
# Usage (on build host, from repo root):
#   RELEASE_TAG=2.25.82 ./scripts/stage2_one.sh cameras
#   RELEASE_TAG=2.25.82 ./scripts/stage2_one.sh cameras frontend
#   RELEASE_TAG=2.25.82 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras
#
# EXTRA_SHA_TAG=1 also tags/pushes :${RELEASE_TAG}-<shortsha> alongside :${RELEASE_TAG}.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 1 ]]; then
  echo "Usage: RELEASE_TAG=<ver> $0 <service> [service…]" >&2
  exit 2
fi

REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
RELEASE_TAG="${RELEASE_TAG:-$(tr -d '[:space:]' < VERSION)}"
export RELEASE_TAG
SHORT_SHA="$(git rev-parse --short HEAD)"
EXTRA_SHA_TAG="${EXTRA_SHA_TAG:-0}"

image_ref() {
  local key="$1"
  case "$key" in
    vision) echo "${REGISTRY}/ppl-meta-vision-protected:${RELEASE_TAG}" ;;
    vmeta) echo "${REGISTRY}/ppl-meta-vmeta-protected:${RELEASE_TAG}" ;;
    *) echo "${REGISTRY}/ppl-meta-${key}:${RELEASE_TAG}" ;;
  esac
}

for svc in "$@"; do
  echo "======== Stage 2 one: ${svc} @ ${RELEASE_TAG} (git ${SHORT_SHA}) ========"
  if [[ "$svc" == "frontend" ]]; then
    if [[ ! -d ppl-meta-frontend/build/web ]]; then
      echo "Building Flutter web assets…"
      (cd ppl-meta-frontend && flutter pub get && flutter build web --release)
    fi
  fi
  ./scripts/build_windows_installer_images.sh "$svc"
  ./scripts/push_protected_service_images.sh "$svc"
  REF="$(image_ref "$svc")"
  if [[ "$EXTRA_SHA_TAG" == "1" ]]; then
    SHA_REF="${REF%:*}:${RELEASE_TAG}-${SHORT_SHA}"
    docker tag "$REF" "$SHA_REF"
    docker push "$SHA_REF"
    echo "REPORT OK service=${svc} tag=${RELEASE_TAG} sha_tag=${RELEASE_TAG}-${SHORT_SHA} ref=${REF}"
  else
    echo "REPORT OK service=${svc} tag=${RELEASE_TAG} ref=${REF}"
  fi
done

echo "REPORT DONE services=$* RELEASE_TAG=${RELEASE_TAG} git=${SHORT_SHA}"
echo "When all intended services are published: ./scripts/stage2_finalize_manifest.sh"
