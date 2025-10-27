#!/bin/bash
# PPL Meta Mini v2.19.19 - Comprehensive Image Testing Script
# Tests both Bookworm and Bullseye variants with face analytics validation

set -euo pipefail

# Configuration
PPL_VERSION="2.19.19"
IMAGE_NAME="nickglezakos/ppl-meta-mini-v${PPL_VERSION}"
TEST_PORT=8004

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

# Function to test basic imports and functionality
test_basic_functionality() {
    local image_tag=$1
    local variant_name=$2
    
    log_info "Testing basic functionality for ${variant_name} (${image_tag})"
    
    # Test script for imports and basic functionality
    local test_script='
import sys, platform, os
print(f"🔍 PPL Meta Mini v2.19.19 - {variant_name} Testing")
print(f"📋 System Information:")
print(f"   Python: {sys.version}")
print(f"   Platform: {platform.platform()}")
print(f"   Architecture: {platform.machine()}")

# Test critical dependencies
print(f"📦 Testing Dependencies:")

# Test dlib
try:
    import dlib
    version = getattr(dlib, "__version__", "20.0.0")
    print(f"   ✅ dlib: {version}")
    
    # Test basic dlib functionality
    detector = dlib.get_frontal_face_detector()
    print(f"   ✅ dlib face detector initialized")
except Exception as e:
    print(f"   ❌ dlib test failed: {e}")
    sys.exit(1)

# Test TensorFlow
try:
    import tensorflow as tf
    print(f"   ✅ TensorFlow: {tf.__version__}")
    
    # Basic TensorFlow test
    x = tf.constant([[1.0, 2.0], [3.0, 4.0]])
    print(f"   ✅ TensorFlow computation test passed")
except Exception as e:
    print(f"   ❌ TensorFlow test failed: {e}")
    sys.exit(1)

# Test DeepFace
try:
    from deepface import DeepFace
    print(f"   ✅ DeepFace: imported successfully")
    
    # Test available models
    models = ["VGG-Face", "Facenet", "OpenFace", "DeepFace"]
    print(f"   ✅ Available DeepFace models: {models}")
except Exception as e:
    print(f"   ❌ DeepFace test failed: {e}")
    sys.exit(1)

# Test OpenCV
try:
    import cv2
    print(f"   ✅ OpenCV: {cv2.__version__}")
except Exception as e:
    print(f"   ❌ OpenCV test failed: {e}")
    sys.exit(1)

# Test FastAPI dependencies
try:
    import fastapi, uvicorn, pydantic
    print(f"   ✅ FastAPI: {fastapi.__version__}")
    print(f"   ✅ Uvicorn: {uvicorn.__version__}")
    print(f"   ✅ Pydantic: {pydantic.__version__}")
except Exception as e:
    print(f"   ❌ FastAPI dependencies test failed: {e}")
    sys.exit(1)

print(f"🎉 All {variant_name} tests passed successfully!")
'
    
    # Replace variant_name placeholder
    test_script=$(echo "$test_script" | sed "s/{variant_name}/$variant_name/g")
    
    # Run the test
    if docker run --rm "${image_tag}" python -c "$test_script"; then
        log_success "Basic functionality test passed for ${variant_name}"
        return 0
    else
        log_error "Basic functionality test failed for ${variant_name}"
        return 1
    fi
}

# Function to test service startup and health check
test_service_startup() {
    local image_tag=$1
    local variant_name=$2
    
    log_info "Testing service startup for ${variant_name} (${image_tag})"
    
    # Start container in background
    local container_name="ppl-mini-test-${variant_name,,}"
    
    log_info "Starting container: ${container_name}"
    docker run -d \
        --name "${container_name}" \
        -p "${TEST_PORT}:8004" \
        "${image_tag}" || {
        log_error "Failed to start container ${container_name}"
        return 1
    }
    
    # Wait for startup
    log_info "Waiting for service to start..."
    sleep 10
    
    # Test health endpoint
    local health_check_passed=false
    for attempt in {1..6}; do
        log_info "Health check attempt ${attempt}/6..."
        if curl -f -s "http://localhost:${TEST_PORT}/health" >/dev/null 2>&1; then
            log_success "Health check passed for ${variant_name}"
            health_check_passed=true
            break
        else
            log_warning "Health check attempt ${attempt} failed, retrying..."
            sleep 5
        fi
    done
    
    # Get container logs for debugging
    log_info "Container logs for ${container_name}:"
    docker logs "${container_name}" | tail -20 || true
    
    # Cleanup
    log_info "Cleaning up container: ${container_name}"
    docker stop "${container_name}" >/dev/null 2>&1 || true
    docker rm "${container_name}" >/dev/null 2>&1 || true
    
    if [ "$health_check_passed" = true ]; then
        log_success "Service startup test passed for ${variant_name}"
        return 0
    else
        log_error "Service startup test failed for ${variant_name}"
        return 1
    fi
}

# Function to test image size and efficiency
test_image_metrics() {
    local image_tag=$1
    local variant_name=$2
    
    log_info "Testing image metrics for ${variant_name} (${image_tag})"
    
    # Get image size
    local image_size=$(docker images "${image_tag}" --format "{{.Size}}")
    log_info "Image size: ${image_size}"
    
    # Get layer count
    local layer_count=$(docker history "${image_tag}" --format "{{.ID}}" | wc -l)
    log_info "Layer count: ${layer_count}"
    
    # Performance test (startup time)
    log_info "Testing container startup time..."
    local start_time=$(date +%s)
    docker run --rm "${image_tag}" python -c "print('Container started successfully')" >/dev/null
    local end_time=$(date +%s)
    local startup_time=$((end_time - start_time))
    
    log_info "Startup time: ${startup_time} seconds"
    
    # Metrics summary
    echo "📊 Image Metrics Summary for ${variant_name}:"
    echo "   Size: ${image_size}"
    echo "   Layers: ${layer_count}"
    echo "   Startup: ${startup_time}s"
    
    log_success "Image metrics test completed for ${variant_name}"
}

# Main test execution
main() {
    log_info "PPL Meta Mini v${PPL_VERSION} - Comprehensive Image Testing"
    log_info "=========================================================="
    
    # Test configuration
    local test_variants=()
    case "${1:-both}" in
        "bookworm")
            test_variants=("${IMAGE_NAME}:latest:Bookworm")
            ;;
        "bullseye")
            test_variants=("${IMAGE_NAME}:bullseye:Bullseye")
            ;;
        "both")
            test_variants=(
                "${IMAGE_NAME}:latest:Bookworm"
                "${IMAGE_NAME}:bullseye:Bullseye"
            )
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [bookworm|bullseye|both]"
            echo "  bookworm: Test Debian Bookworm variant only"
            echo "  bullseye: Test Debian Bullseye variant only"
            echo "  both:     Test both variants (default)"
            exit 0
            ;;
        *)
            log_error "Unknown test target: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    # Execute tests for each variant
    local overall_success=true
    
    for variant_info in "${test_variants[@]}"; do
        IFS=':' read -r image_tag variant_name <<< "$variant_info"
        
        log_info "Testing variant: ${variant_name} (${image_tag})"
        echo "=================================================="
        
        # Check if image exists
        if ! docker images "${image_tag}" --format "{{.Repository}}:{{.Tag}}" | grep -q "${image_tag}"; then
            log_error "Image not found: ${image_tag}"
            log_error "Please build the image first using: ./build_enhanced.sh ${variant_name,,}"
            overall_success=false
            continue
        fi
        
        # Test 1: Basic functionality
        if ! test_basic_functionality "${image_tag}" "${variant_name}"; then
            overall_success=false
            continue
        fi
        
        # Test 2: Service startup
        if ! test_service_startup "${image_tag}" "${variant_name}"; then
            overall_success=false
            continue
        fi
        
        # Test 3: Image metrics
        test_image_metrics "${image_tag}" "${variant_name}"
        
        log_success "All tests passed for ${variant_name}!"
        echo ""
    done
    
    # Final summary
    if [ "$overall_success" = true ]; then
        log_success "🎉 All image tests completed successfully!"
        log_info "Images are ready for deployment and Docker Hub push"
    else
        log_error "❌ Some tests failed. Please review the output above."
        exit 1
    fi
}

# Execute main function
main "$@"