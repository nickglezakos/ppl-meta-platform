#!/bin/bash

# Multi-Architecture Docker Build and Push Script
# Builds for both AMD64 (Windows/Linux) and ARM64 (Apple Silicon)

set -e

echo "🏗️  PPL Meta Mini - Multi-Architecture Docker Build"
echo "=================================================="
echo ""

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Docker Buildx not available. Please install Docker Desktop or enable buildx."
    exit 1
fi

# Create and use buildx builder if not exists
BUILDER_NAME="ppl-meta-multiarch"
if ! docker buildx inspect $BUILDER_NAME > /dev/null 2>&1; then
    echo "🔧 Creating multi-architecture builder..."
    docker buildx create --name $BUILDER_NAME --platform linux/amd64,linux/arm64 --use
else
    echo "✅ Using existing builder: $BUILDER_NAME"
    docker buildx use $BUILDER_NAME
fi

# Ensure builder is running
echo "🚀 Starting builder..."
docker buildx inspect --bootstrap

echo ""
echo "🏷️  Building multi-architecture image..."
echo "Target platforms: linux/amd64 (Windows/Intel), linux/arm64 (Apple Silicon)"
echo ""

# Build and push for multiple platforms
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag nickglezakos/ppl-meta-mini-beta081:latest \
    --tag nickglezakos/ppl-meta-mini-beta081:multiarch \
    --push \
    -f Dockerfile.cython.dlib \
    .

echo ""
echo "🎉 Multi-architecture build complete!"
echo ""
echo "✅ Available platforms:"
echo "   • linux/amd64 (Windows, Intel Linux)"
echo "   • linux/arm64 (Apple Silicon, ARM Linux)"
echo ""
echo "🔄 Test on different platforms:"
echo "   Windows: docker run -d --name test-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta081:latest"
echo "   macOS:   docker run -d --name test-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta081:latest"
echo "   Linux:   docker run -d --name test-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta081:latest"
echo ""
echo "🌐 Docker Hub: https://hub.docker.com/r/nickglezakos/ppl-meta-mini-beta081"
