#!/bin/bash

# PPL Meta Mini - Docker Hub Push Script
# This script properly tags and pushes the dlib-enhanced Cython image to Docker Hub

set -e  # Exit on any error

echo "🚀 PPL Meta Mini - Docker Hub Push Script"
echo "=========================================="
echo

# Configuration - UPDATE THESE VALUES
DOCKER_HUB_USERNAME="your-dockerhub-username"  # Change this to your Docker Hub username
REPOSITORY_NAME="ppl-meta-mini-cython-dlib"
LOCAL_IMAGE_NAME="ppl-meta-mini-cython-dlib:latest"

# Derived values
DOCKER_HUB_REPO="${DOCKER_HUB_USERNAME}/${REPOSITORY_NAME}"
DOCKER_HUB_TAG="${DOCKER_HUB_REPO}:latest"

echo "📋 Configuration:"
echo "  Local image: ${LOCAL_IMAGE_NAME}"
echo "  Docker Hub repo: ${DOCKER_HUB_REPO}"
echo "  Final tag: ${DOCKER_HUB_TAG}"
echo

# Check if local image exists
if ! docker images | grep -q "ppl-meta-mini-cython-dlib.*latest"; then
    echo "❌ Error: Local image '${LOCAL_IMAGE_NAME}' not found!"
    echo "Please build the image first using:"
    echo "  docker build -f Dockerfile.cython.dlib -t ppl-meta-mini-cython-dlib:latest ."
    exit 1
fi

echo "✅ Local image found!"

# Check if user is logged in to Docker Hub
echo
echo "🔐 Checking Docker Hub authentication..."
if ! docker info | grep -q "Username:"; then
    echo "⚠️  You are not logged in to Docker Hub."
    echo "Please login first:"
    echo "  docker login"
    echo
    read -p "Do you want to login now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker login
    else
        echo "❌ Aborted. Please login and try again."
        exit 1
    fi
else
    echo "✅ Docker Hub authentication confirmed!"
fi

# Get image size info
echo
echo "📊 Image Information:"
docker images "${LOCAL_IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Tag the image for Docker Hub
echo
echo "🏷️  Tagging image for Docker Hub..."
docker tag "${LOCAL_IMAGE_NAME}" "${DOCKER_HUB_TAG}"

if [[ $? -eq 0 ]]; then
    echo "✅ Image tagged successfully as: ${DOCKER_HUB_TAG}"
else
    echo "❌ Failed to tag image!"
    exit 1
fi

# Show tagged images
echo
echo "📋 Tagged images:"
docker images | grep "${REPOSITORY_NAME}"

# Push to Docker Hub
echo
echo "⬆️  Pushing to Docker Hub..."
echo "This may take several minutes depending on your internet connection..."
echo "Image size: ~2.75GB"
echo

docker push "${DOCKER_HUB_TAG}"

if [[ $? -eq 0 ]]; then
    echo
    echo "🎉 Success! Image pushed to Docker Hub!"
    echo
    echo "📝 Your image is now available at:"
    echo "  https://hub.docker.com/r/${DOCKER_HUB_REPO}"
    echo
    echo "🔄 Others can now pull it with:"
    echo "  docker pull ${DOCKER_HUB_TAG}"
    echo
    echo "🧪 Test the pushed image:"
    echo "  docker run -d --name test-dlib -p 8004:8004 ${DOCKER_HUB_TAG}"
    
else
    echo
    echo "❌ Push failed! Common issues:"
    echo "  1. Repository doesn't exist on Docker Hub"
    echo "  2. No push permissions to repository"
    echo "  3. Network connection issues"
    echo "  4. Image size too large for account limits"
    echo
    echo "💡 Solutions:"
    echo "  - Create repository on Docker Hub first: https://hub.docker.com/"
    echo "  - Verify repository name matches your Docker Hub username"
    echo "  - Check your Docker Hub account limits"
    exit 1
fi

# Optional: Clean up local tagged image
echo
read -p "🧹 Remove local Docker Hub tag? (keeps original image) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi "${DOCKER_HUB_TAG}" 2>/dev/null || true
    echo "✅ Local Docker Hub tag removed"
fi

echo
echo "🎯 Next Steps:"
echo "  1. Update your documentation with the new Docker Hub repository"
echo "  2. Test pulling and running from Docker Hub"
echo "  3. Share the repository with your team"
