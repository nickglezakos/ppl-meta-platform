#!/bin/bash

# Linux-Only Docker Build and Push Script
# Optimized for Windows WSL, Linux VMs, and Raspberry Pi
# Targets: linux/amd64 and linux/arm64

set -e

echo "🐧 PPL Meta Mini Beta083 - Linux-Only Multi-Architecture Build"
echo "=============================================================="
echo ""
echo "🎯 Target Platforms:"
echo "   • linux/amd64 (Windows WSL, Intel Linux, VMs)"
echo "   • linux/arm64 (Raspberry Pi, ARM Linux)"
echo ""

# Check if buildx is available
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Docker Buildx not available. Please install Docker Desktop or enable buildx."
    exit 1
fi

# Create and use buildx builder if not exists
BUILDER_NAME="ppl-meta-linux-builder"
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
echo "🏷️  Building Linux multi-architecture image..."
echo "Building for:"
echo "   • linux/amd64 - Windows WSL, Intel Linux, VMs"
echo "   • linux/arm64 - Raspberry Pi, ARM64 Linux"
echo ""

# Build and push for Linux platforms only
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag nickglezakos/ppl-meta-mini-beta083:latest \
    --tag nickglezakos/ppl-meta-mini-beta083:linux \
    --push \
    -f Dockerfile.cython.dlib \
    .

echo ""
echo "🎉 Linux multi-architecture build complete!"
echo ""
echo "✅ Available platforms:"
echo "   • linux/amd64 (Windows WSL, Intel Linux, VMs)"
echo "   • linux/arm64 (Raspberry Pi, ARM64 Linux)"
echo ""
echo "🔄 Test commands for different environments:"
echo ""
echo "Windows WSL:"
echo "   docker run -d --name ppl-mini-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo ""
echo "Linux VM:"
echo "   docker run -d --name ppl-mini-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo ""
echo "Raspberry Pi:"
echo "   docker run -d --name ppl-mini-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo ""
echo "🌐 Docker Hub: https://hub.docker.com/r/nickglezakos/ppl-meta-mini-beta083"
echo ""
echo "📝 Note: This image is Linux-only and will NOT run on native Windows Docker Desktop"
echo "    Use Windows WSL2 or Linux VMs for Windows compatibility"
