#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
RELEASE_TAG="${RELEASE_TAG:-$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo latest)}"
PLATFORM="${PLATFORM:-linux/amd64}"
MIN_FREE_GB="${MIN_FREE_GB:-12}"
SERVICES=(node media gateway orchestrator discovery communications frontend vision vmeta)

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

resolve_service() {
    local service="$1"

    case "$service" in
        node)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-node"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-node:$RELEASE_TAG"
            ;;
        media)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-media"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-media:$RELEASE_TAG"
            ;;
        gateway)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-gateway"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-gateway:$RELEASE_TAG"
            ;;
        orchestrator)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-orchestrator"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-orchestrator:$RELEASE_TAG"
            ;;
        discovery)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-discovery"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-discovery:$RELEASE_TAG"
            ;;
        communications)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-communications"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-communications:$RELEASE_TAG"
            ;;
        frontend)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-frontend"
            DOCKERFILE="$SERVICE_DIR/Dockerfile"
            IMAGE_NAME="$REGISTRY/ppl-meta-frontend:$RELEASE_TAG"
            if [[ ! -d "$SERVICE_DIR/build/web" ]]; then
                echo "Frontend build artifacts missing at $SERVICE_DIR/build/web. Run 'flutter build web --release' first." >&2
                exit 1
            fi
            ;;
        vision)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-vision"
            DOCKERFILE="$SERVICE_DIR/docker/Dockerfile.protected"
            IMAGE_NAME="$REGISTRY/ppl-meta-vision-protected:$RELEASE_TAG"
            ;;
        vmeta)
            SERVICE_DIR="$PROJECT_ROOT/ppl-meta-vmeta"
            DOCKERFILE="$SERVICE_DIR/docker/Dockerfile.protected"
            IMAGE_NAME="$REGISTRY/ppl-meta-vmeta-protected:$RELEASE_TAG"
            ;;
        *)
            echo "Unsupported service: $service" >&2
            exit 1
            ;;
    esac

    if [[ ! -f "$DOCKERFILE" ]]; then
        echo "Dockerfile not found for $service: $DOCKERFILE" >&2
        exit 1
    fi
}

build_service() {
    local service="$1"

    resolve_service "$service"

    echo "Building $service as $IMAGE_NAME for platform $PLATFORM"
    check_free_space
    DOCKER_BUILDKIT=1 docker build \
        --platform "$PLATFORM" \
        --file "$DOCKERFILE" \
        --tag "$IMAGE_NAME" \
        "$SERVICE_DIR"
    cleanup_docker_cache
}

echo "Building Windows installer images with low-disk cleanup"
echo "Registry: $REGISTRY"
echo "Release tag: $RELEASE_TAG"
echo "Platform: $PLATFORM"
echo "Minimum free space: ${MIN_FREE_GB}GiB"

cleanup_docker_cache

for service in "${SERVICES[@]}"; do
    build_service "$service"
done

echo "Completed Windows installer image builds"