#!/bin/bash
# PPL Meta Mini v2.19.19 - Enhanced Build Script
# Supports both Debian Bookworm and Bullseye with multi-architecture builds

set -euo pipefail

# Configuration
PPL_VERSION="2.19.19"
IMAGE_NAME="nickglezakos/ppl-meta-mini-v${PPL_VERSION}"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to build image
build_image() {
    local base_image=$1
    local tag_suffix=$2
    local image_tag="${IMAGE_NAME}:${tag_suffix}"
    
    log_info "Building ${image_tag} with base image: ${base_image}"
    
    # Build command
    docker build \
        --build-arg BASE_IMAGE="${base_image}" \
        --build-arg PPL_VERSION="${PPL_VERSION}" \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        -f Dockerfile.tensorflow \
        -t "${image_tag}" \
        .
    
    if [ $? -eq 0 ]; then
        log_success "Successfully built ${image_tag}"
        return 0
    else
        log_error "Failed to build ${image_tag}"
        return 1
    fi
}

# Function to test image
test_image() {
    local image_tag=$1
    
    log_info "Testing image: ${image_tag}"
    
    # Test basic functionality
    docker run --rm "${image_tag}" python -c "
import sys, platform
print(f'✅ PPL Meta Mini v${PPL_VERSION}')
print(f'✅ Python: {sys.version}')
print(f'✅ Platform: {platform.platform()}')

# Test critical dependencies
try:
    import dlib
    print(f'✅ dlib: {getattr(dlib, \"__version__\", \"20.0.0\")}')
except ImportError as e:
    print(f'❌ dlib import failed: {e}')
    sys.exit(1)

try:
    import tensorflow as tf
    print(f'✅ TensorFlow: {tf.__version__}')
except ImportError as e:
    print(f'❌ TensorFlow import failed: {e}')
    sys.exit(1)

try:
    from deepface import DeepFace
    print(f'✅ DeepFace: imported successfully')
except ImportError as e:
    print(f'❌ DeepFace import failed: {e}')
    sys.exit(1)

print('🎉 All tests passed!')
"
    
    if [ $? -eq 0 ]; then
        log_success "Image test passed: ${image_tag}"
        return 0
    else
        log_error "Image test failed: ${image_tag}"
        return 1
    fi
}

# Main execution
main() {
    log_info "PPL Meta Mini v${PPL_VERSION} - Enhanced Build Script"
    log_info "=================================================="
    
    # Check if we're in the right directory
    if [ ! -f "Dockerfile.tensorflow" ]; then
        log_error "Dockerfile.tensorflow not found. Please run from the ppl-meta-mini directory."
        exit 1
    fi
    
    # Build type selection
    case "${1:-bookworm}" in
        "bookworm")
            log_info "Building Debian Bookworm variant (default)"
            build_image "python:3.11-slim" "latest" && \
            docker tag "${IMAGE_NAME}:latest" "${IMAGE_NAME}:bookworm" && \
            test_image "${IMAGE_NAME}:latest"
            ;;
        "bullseye")
            log_info "Building Debian Bullseye variant"
            build_image "python:3.11-slim-bullseye" "bullseye" && \
            test_image "${IMAGE_NAME}:bullseye"
            ;;
        "both")
            log_info "Building both Bookworm and Bullseye variants"
            
            # Build Bookworm
            log_info "Building Bookworm variant..."
            build_image "python:3.11-slim" "latest" && \
            docker tag "${IMAGE_NAME}:latest" "${IMAGE_NAME}:bookworm" && \
            test_image "${IMAGE_NAME}:latest" || exit 1
            
            # Build Bullseye
            log_info "Building Bullseye variant..."
            build_image "python:3.11-slim-bullseye" "bullseye" && \
            test_image "${IMAGE_NAME}:bullseye" || exit 1
            
            log_success "Both variants built successfully!"
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [bookworm|bullseye|both]"
            echo "  bookworm: Build Debian Bookworm variant (default)"
            echo "  bullseye: Build Debian Bullseye variant"
            echo "  both:     Build both variants"
            exit 0
            ;;
        *)
            log_error "Unknown build type: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    log_info "Build completed! Available images:"
    docker images "${IMAGE_NAME}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

# Execute main function
main "$@"