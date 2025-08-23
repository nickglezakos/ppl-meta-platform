#!/bin/bash

# Linux-Only Multi-Architecture Docker Build and Push Script
# Builds for AMD64 (Intel/AMD) and ARM64 (Raspberry Pi, ARM servers)
# Optimized for Windows Docker Desktop (Linux containers), Linux VMs, and Raspberry Pi

set -e

echo "🐧 PPL Meta Mini Beta083 - Linux Multi-Architecture Build"
echo "========================================================"
echo ""
echo "🎯 Target Platforms:"
echo "   • linux/amd64 (Windows Docker Desktop, Intel Linux)"
echo "   • linux/arm64 (Raspberry Pi, ARM Linux, Apple Silicon)"
echo ""

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Docker Buildx not available. Please install Docker Desktop or enable buildx."
    exit 1
fi

# Create and use buildx builder if not exists
BUILDER_NAME="ppl-meta-linux-multiarch"
if ! docker buildx inspect $BUILDER_NAME > /dev/null 2>&1; then
    echo "🔧 Creating Linux multi-architecture builder..."
    docker buildx create --name $BUILDER_NAME --platform linux/amd64,linux/arm64 --use
else
    echo "✅ Using existing builder: $BUILDER_NAME"
    docker buildx use $BUILDER_NAME
fi

# Ensure builder is running
echo "🚀 Starting builder..."
docker buildx inspect --bootstrap

echo ""
echo "🏷️  Building Linux multi-architecture image with DeepFace..."
echo "📦 Including: Cython + Dlib + DeepFace for age detection"
echo ""

# Build and push for Linux platforms only
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag nickglezakos/ppl-meta-mini-beta083:latest \
    --tag nickglezakos/ppl-meta-mini-beta083:linux-multiarch \
    --push \
    -f Dockerfile.cython.dlib \
    .

echo ""
echo "🎉 Linux multi-architecture build complete!"
echo ""
echo "✅ Available platforms:"
echo "   • linux/amd64 (Windows Docker Desktop, Intel Linux)"
echo "   • linux/arm64 (Raspberry Pi, ARM Linux, Apple Silicon)"
echo ""
echo "🔄 Test commands:"
echo "   Windows Docker Desktop: docker run -d --name test-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo "   Raspberry Pi:           docker run -d --name test-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo "   Linux VM:               docker run -d --name test-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo ""
echo "🧪 Age detection test:"
echo "   curl -X POST http://localhost:8004/api/v1/analyze-faces \\"
echo "        -F 'file=@your-image.jpg' \\"
echo "        -F 'include_age=true'"
echo ""
echo "🌐 Docker Hub: https://hub.docker.com/r/nickglezakos/ppl-meta-mini-beta083"
