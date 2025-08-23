#!/bin/bash

# Simplified Linux Docker Build for Beta083
# Single platform build to avoid buildx issues

set -e

echo "🐧 PPL Meta Mini Beta083 - Simplified Linux Build"
echo "==============================================="
echo ""

# Check current platform
PLATFORM=$(uname -m)
echo "🏗️  Building for current platform: $PLATFORM"

if [[ "$PLATFORM" == "arm64" || "$PLATFORM" == "aarch64" ]]; then
    TARGET_PLATFORM="linux/arm64"
    echo "📱 Detected ARM64 - Building for ARM64 (Raspberry Pi compatible)"
else
    TARGET_PLATFORM="linux/amd64"
    echo "💻 Detected AMD64 - Building for Intel/AMD (Windows Docker Desktop compatible)"
fi

echo ""
echo "🏷️  Building single-platform image..."

# Build for current platform only
docker build \
    --tag nickglezakos/ppl-meta-mini-beta083:latest \
    --tag nickglezakos/ppl-meta-mini-beta083:$(uname -m) \
    -f Dockerfile.cython.dlib \
    .

echo ""
echo "📤 Pushing to Docker Hub..."

docker push nickglezakos/ppl-meta-mini-beta083:latest
docker push nickglezakos/ppl-meta-mini-beta083:$(uname -m)

echo ""
echo "🎉 Single-platform build complete!"
echo ""
echo "✅ Built for: $TARGET_PLATFORM"
echo ""
echo "🔄 Test command:"
echo "   docker run -d --name test-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest"
echo ""
echo "🧪 Age detection test:"
echo "   curl -X POST http://localhost:8004/api/v1/analyze-faces \\"
echo "        -F 'file=@your-image.jpg' \\"
echo "        -F 'include_age=true'"
echo ""
echo "🌐 Docker Hub: https://hub.docker.com/r/nickglezakos/ppl-meta-mini-beta083"
echo ""
echo "📝 Note: This is a single-platform build. For multi-arch, run on both ARM64 and AMD64 machines."
