#!/usr/bin/env bash
# Run on Windows builder (WSL Ubuntu preferred) after repo + frontend web assets are present.
set -euo pipefail

TAG="${TAG:-2.25.80}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d ppl-meta-frontend/build/web ]]; then
  echo "Missing ppl-meta-frontend/build/web — copy from Mac first." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon not reachable. Start Docker Desktop and retry." >&2
  exit 1
fi

echo "Building + pushing platform images for ${TAG} (linux/amd64)"
RELEASE_TAG="$TAG" ./scripts/build_windows_installer_images.sh
RELEASE_TAG="$TAG" ./scripts/push_protected_service_images.sh
./scripts/verify_platform_release.sh "$TAG"
