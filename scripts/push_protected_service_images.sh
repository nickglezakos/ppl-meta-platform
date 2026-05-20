#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="${REGISTRY:-ghcr.io/nickglezakos/ppl-meta-platform}"
RELEASE_TAG="${RELEASE_TAG:-$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo latest)}"

SERVICES=("vision" "vmeta")
if [[ $# -gt 0 ]]; then
    SERVICES=("$@")
fi

for service in "${SERVICES[@]}"; do
    case "$service" in
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

echo "Protected images pushed successfully"