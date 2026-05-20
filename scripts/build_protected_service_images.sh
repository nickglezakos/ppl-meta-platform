#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
RELEASE_TAG="${RELEASE_TAG:-$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo latest)}"
MIN_FREE_GB="${MIN_FREE_GB:-12}"
SERVICES=("vision" "vmeta")

if [[ $# -gt 0 ]]; then
    SERVICES=("$@")
fi

check_free_space() {
    local free_kb
    free_kb=$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local required_kb=$((MIN_FREE_GB * 1024 * 1024))
    if (( free_kb < required_kb )); then
        echo "Not enough free disk space. Required: ${MIN_FREE_GB}GiB, available: $((free_kb / 1024 / 1024))GiB" >&2
        exit 1
    fi
}

cleanup_docker_cache() {
    docker builder prune -af >/dev/null 2>&1 || true
    docker image prune -f >/dev/null 2>&1 || true
}

build_service() {
    local service="$1"
    local service_dir
    local dockerfile
    local image_name

    case "$service" in
        vision)
            service_dir="$PROJECT_ROOT/ppl-meta-vision"
            dockerfile="$service_dir/docker/Dockerfile.protected"
            image_name="$REGISTRY/ppl-meta-vision-protected:$RELEASE_TAG"
            ;;
        vmeta)
            service_dir="$PROJECT_ROOT/ppl-meta-vmeta"
            dockerfile="$service_dir/docker/Dockerfile.protected"
            image_name="$REGISTRY/ppl-meta-vmeta-protected:$RELEASE_TAG"
            ;;
        *)
            echo "Unsupported service: $service" >&2
            exit 1
            ;;
    esac

    echo "Building $service as $image_name"
    check_free_space
    DOCKER_BUILDKIT=1 docker build \
        --file "$dockerfile" \
        --tag "$image_name" \
        "$service_dir"
    cleanup_docker_cache
}

echo "Building protected service images with low-disk cleanup"
echo "Registry: $REGISTRY"
echo "Release tag: $RELEASE_TAG"
echo "Minimum free space: ${MIN_FREE_GB}GiB"

cleanup_docker_cache

for service in "${SERVICES[@]}"; do
    build_service "$service"
done

echo "Completed protected image builds"