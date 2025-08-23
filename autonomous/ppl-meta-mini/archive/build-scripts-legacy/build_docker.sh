#!/bin/bash

# PPL Meta Mini - Docker Build Script for Nuitka
set -e

echo "🐳 Building PPL Meta Mini Docker Image with Nuitka"
echo "=================================================="

# Configuration
IMAGE_NAME="ppl-meta-mini"
IMAGE_TAG="nuitka-latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Build the Docker image
echo "🏗️  Building Docker image: ${FULL_IMAGE_NAME}"
docker build -f Dockerfile.nuitka -t "${FULL_IMAGE_NAME}" .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully: ${FULL_IMAGE_NAME}"
    
    # Show image size
    echo "📊 Image information:"
    docker images "${IMAGE_NAME}" | grep "${IMAGE_TAG}"
    
    echo ""
    echo "🚀 To run the container:"
    echo "docker run -d -p 8004:8004 --name ppl-meta-mini-nuitka ${FULL_IMAGE_NAME}"
    echo ""
    echo "🏥 To check health:"
    echo "curl http://localhost:8004/health"
    echo ""
    echo "📋 To view logs:"
    echo "docker logs ppl-meta-mini-nuitka"
    echo ""
    echo "🛑 To stop:"
    echo "docker stop ppl-meta-mini-nuitka && docker rm ppl-meta-mini-nuitka"
    
else
    echo "❌ Docker build failed!"
    exit 1
fi