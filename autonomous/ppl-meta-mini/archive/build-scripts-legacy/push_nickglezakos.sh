#!/bin/bash

# PPL Meta Mini - Docker Hub Push for nickglezakos
echo "🚀 Docker Hub Push Setup for nickglezakos"
echo "=========================================="
echo

# Configuration
DOCKER_HUB_USERNAME="nickglezakos"
REPOSITORY_NAME="ppl-meta-mini-cython-dlib"
LOCAL_IMAGE="ppl-meta-mini-cython-dlib:latest"
DOCKER_HUB_IMAGE="${DOCKER_HUB_USERNAME}/${REPOSITORY_NAME}:latest"

echo "📋 Configuration:"
echo "  Local image: ${LOCAL_IMAGE}"
echo "  Docker Hub image: ${DOCKER_HUB_IMAGE}"
echo

# Check if local image exists
echo "🔍 Checking local image..."
if docker images | grep -q "ppl-meta-mini-cython-dlib.*latest"; then
    echo "✅ Local image found!"
    docker images ppl-meta-mini-cython-dlib:latest
else
    echo "❌ Local image not found!"
    exit 1
fi

echo
echo "🏷️  Tagging image for Docker Hub..."
docker tag "${LOCAL_IMAGE}" "${DOCKER_HUB_IMAGE}"

if [[ $? -eq 0 ]]; then
    echo "✅ Successfully tagged as: ${DOCKER_HUB_IMAGE}"
else
    echo "❌ Failed to tag image!"
    exit 1
fi

echo
echo "📋 Tagged images:"
docker images | grep "${REPOSITORY_NAME}"

echo
echo "⬆️  Ready to push! Run this command:"
echo "   docker push ${DOCKER_HUB_IMAGE}"
echo
echo "🌐 After pushing, the image will be available at:"
echo "   https://hub.docker.com/r/${DOCKER_HUB_USERNAME}/${REPOSITORY_NAME}"
echo
echo "🔄 Others can pull it with:"
echo "   docker pull ${DOCKER_HUB_IMAGE}"

# Ask if user wants to push now
echo
read -p "🚀 Push to Docker Hub now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⬆️  Pushing to Docker Hub..."
    echo "This may take several minutes (image is ~2.75GB)..."
    
    docker push "${DOCKER_HUB_IMAGE}"
    
    if [[ $? -eq 0 ]]; then
        echo
        echo "🎉 Successfully pushed to Docker Hub!"
        echo "🌐 Available at: https://hub.docker.com/r/${DOCKER_HUB_USERNAME}/${REPOSITORY_NAME}"
    else
        echo
        echo "❌ Push failed. Make sure:"
        echo "  1. You're logged in: docker login"
        echo "  2. Repository exists on Docker Hub"
        echo "  3. You have push permissions"
    fi
else
    echo "⏸️  Tagged but not pushed. You can push later with:"
    echo "   docker push ${DOCKER_HUB_IMAGE}"
fi
