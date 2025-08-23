#!/bin/bash

# PPL Meta Mini Beta085 Build Script
# Official build script for the production beta085 image

set -e

echo "🚀 Building PPL Meta Mini Beta085 with TensorFlow + DeepFace..."

# Build the Docker image
docker build \
    -f Dockerfile.tensorflow \
    -t nickglezakos/ppl-meta-mini-beta085:latest \
    --platform linux/amd64 \
    .

echo "✅ Build completed successfully!"
echo "📦 Image: nickglezakos/ppl-meta-mini-beta085:latest"
echo ""
echo "🔧 To run the container:"
echo "docker run -d --name ppl-meta-mini -p 8004:8004 nickglezakos/ppl-meta-mini-beta085:latest"
echo ""
echo "🌐 To push to Docker Hub:"
echo "docker push nickglezakos/ppl-meta-mini-beta085:latest"
echo ""
echo "💾 To save as tar file:"
echo "docker save nickglezakos/ppl-meta-mini-beta085:latest -o ppl-meta-mini-beta085.tar"
