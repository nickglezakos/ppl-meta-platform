#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
RELEASE_TAG="${RELEASE_TAG:-$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo latest)}"

SERVICES=("node" "media" "gateway" "orchestrator" "discovery" "communications" "frontend" "vision" "vmeta")
if [[ $# -gt 0 ]]; then
    SERVICES=("$@")
fi

echo "Pushing images to $REGISTRY with tag $RELEASE_TAG"

for service in "${SERVICES[@]}"; do
    case "$service" in
        node)
            docker push "$REGISTRY/ppl-meta-node:$RELEASE_TAG"
            ;;
        media)
            docker push "$REGISTRY/ppl-meta-media:$RELEASE_TAG"
            ;;
        gateway)
            docker push "$REGISTRY/ppl-meta-gateway:$RELEASE_TAG"
            ;;
        orchestrator)
            docker push "$REGISTRY/ppl-meta-orchestrator:$RELEASE_TAG"
            ;;
        discovery)
            docker push "$REGISTRY/ppl-meta-discovery:$RELEASE_TAG"
            ;;
        communications)
            docker push "$REGISTRY/ppl-meta-communications:$RELEASE_TAG"
            ;;
        frontend)
            docker push "$REGISTRY/ppl-meta-frontend:$RELEASE_TAG"
            ;;
        vision)
            docker push "$REGISTRY/ppl-meta-vision-protected:$RELEASE_TAG"
            ;;
        vmeta)
            docker push "$REGISTRY/ppl-meta-vmeta-protected:$RELEASE_TAG"
            ;;
        *)
            echo "Unsupported service: $service" >&2
            exit 1
            ;;
    esac
done

echo "All images pushed successfully"
