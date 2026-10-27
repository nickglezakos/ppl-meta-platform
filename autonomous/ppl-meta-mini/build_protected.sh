#!/bin/bash
# Build the protected PPL Meta Mini image (Cython .so, proprietary .py stripped).
set -euo pipefail

PPL_VERSION="${PPL_VERSION:-2.19.19}"
IMAGE_NAME="${IMAGE_NAME:-nickglezakos/ppl-meta-mini-protected}"
BASE_IMAGE="${BASE_IMAGE:-python:3.11-slim}"
TAG_SUFFIX="${1:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ ! -f Dockerfile.protected ]]; then
    echo "Dockerfile.protected not found in ${SCRIPT_DIR}" >&2
    exit 1
fi

IMAGE_TAG="${IMAGE_NAME}:${TAG_SUFFIX}"

echo "[INFO] Building ${IMAGE_TAG} (BASE_IMAGE=${BASE_IMAGE}, PPL_VERSION=${PPL_VERSION})"

docker build \
    --build-arg BASE_IMAGE="${BASE_IMAGE}" \
    --build-arg PPL_VERSION="${PPL_VERSION}" \
    -f Dockerfile.protected \
    -t "${IMAGE_TAG}" \
    -t "${IMAGE_NAME}:v${PPL_VERSION}" \
    .

echo "[SUCCESS] Built ${IMAGE_TAG}"
echo "Run example:"
echo "  docker run -d --name ppl-meta-mini -p 8004:8004 ${IMAGE_TAG}"
