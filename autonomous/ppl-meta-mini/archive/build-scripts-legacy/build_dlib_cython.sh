#!/bin/bash

# PPL Meta Mini - Dlib + Cython Docker Image Builder
# This script builds the enhanced Docker image with dlib and Cython optimizations

set -e  # Exit on any error

echo "🚀 PPL Meta Mini - Dlib + Cython Docker Image Builder"
echo "======================================================="
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if required files exist
echo "📋 Checking required files..."
required_files=(
    "Dockerfile.cython.dlib"
    "requirements.cython.dlib.txt"
    "requirements.runtime.txt"
    "setup_cython_dlib.py"
    "src/main.py"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Error: Required file '$file' not found!"
        echo "Please ensure you're in the ppl-meta-mini directory and all files are present."
        exit 1
    fi
done

echo "✅ All required files found!"
echo

# Get system info
echo "💻 System Information:"
echo "  OS: $(uname -s)"
echo "  Architecture: $(uname -m)"
echo "  Docker Version: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
echo

# Start build
echo "🏗️  Starting Docker build..."
echo "⏱️  This will take 10-20 minutes depending on your system..."
echo "📦 Final image size will be approximately 850MB"
echo

# Build with progress
docker build \
    -f Dockerfile.cython.dlib \
    -t ppl-meta-mini-cython-dlib:latest \
    --progress=plain \
    .

# Verify build success
if [[ $? -eq 0 ]]; then
    echo
    echo "✅ Build completed successfully!"
    echo
    
    # Show image info
    echo "📊 Image Information:"
    docker images ppl-meta-mini-cython-dlib:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo
    
    # Test the image
    echo "🧪 Testing the built image..."
    
    # Stop any existing container
    docker stop ppl-meta-mini-dlib-test 2>/dev/null || true
    docker rm ppl-meta-mini-dlib-test 2>/dev/null || true
    
    # Start test container
    echo "Starting test container..."
    docker run -d \
        --name ppl-meta-mini-dlib-test \
        -p 8004:8004 \
        ppl-meta-mini-cython-dlib:latest
    
    # Wait for service to start
    echo "Waiting for service to start..."
    sleep 10
    
    # Test health endpoint
    if curl -s http://localhost:8004/health > /dev/null 2>&1; then
        echo "✅ Service is running and responding!"
        echo "🌐 Health check: http://localhost:8004/health"
        echo "📚 API docs: http://localhost:8004/docs"
    else
        echo "⚠️  Service started but health check failed. Check logs:"
        echo "   docker logs ppl-meta-mini-dlib-test"
    fi
    
    # Cleanup test container
    echo
    echo "🧹 Cleaning up test container..."
    docker stop ppl-meta-mini-dlib-test
    docker rm ppl-meta-mini-dlib-test
    
    echo
    echo "🎉 Success! Your dlib-enhanced Cython image is ready!"
    echo
    echo "📝 Next steps:"
    echo "  1. Run the container:"
    echo "     docker run -d --name ppl-meta-mini-dlib -p 8004:8004 ppl-meta-mini-cython-dlib:latest"
    echo
    echo "  2. Check health:"
    echo "     curl http://localhost:8004/health"
    echo
    echo "  3. View API docs:"
    echo "     open http://localhost:8004/docs"
    echo
    echo "📖 For complete documentation, see DLIB_CYTHON_USER_GUIDE.md"
    
else
    echo
    echo "❌ Build failed! Please check the error messages above."
    echo
    echo "🔍 Common solutions:"
    echo "  - Ensure Docker has enough memory (4GB recommended)"
    echo "  - Check internet connection for downloading dependencies"
    echo "  - Verify all required files are present"
    echo "  - Try building again (sometimes network issues cause temporary failures)"
    echo
    exit 1
fi
