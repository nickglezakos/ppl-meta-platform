#!/bin/bash

# Docker Image Optimization Script for PPL Meta Platform
# This script builds optimized Docker images and compares sizes

set -e

echo "🚀 PPL Meta Platform - Docker Image Optimization"
echo "=================================================="
echo "Building optimized Docker images with multi-stage builds and Alpine Linux..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to get image size
get_image_size() {
    local image_name=$1
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep "^$image_name" | head -1 | awk '{print $3}'
}

# Function to build and measure image
build_and_measure() {
    local service_name=$1
    local service_path=$2
    
    echo -e "${BLUE}🔨 Building $service_name...${NC}"
    
    # Build the optimized image
    if docker build -t "$service_name-optimized:latest" "$service_path"; then
        echo -e "${GREEN}✅ Successfully built $service_name-optimized${NC}"
        
        # Get sizes
        local old_size=$(get_image_size "$service_name")
        local new_size=$(get_image_size "$service_name-optimized")
        
        echo -e "${YELLOW}📊 Size comparison for $service_name:${NC}"
        echo -e "   Original: ${old_size:-'N/A'}"
        echo -e "   Optimized: $new_size"
        echo ""
    else
        echo -e "${RED}❌ Failed to build $service_name-optimized${NC}"
        echo ""
    fi
}

# Store original sizes
echo -e "${BLUE}📏 Checking current image sizes...${NC}"
docker images | grep ppl-meta
echo ""

# Build optimized images
echo -e "${BLUE}🔧 Building optimized images...${NC}"
echo ""

build_and_measure "ppl-meta-node" "./ppl-meta-node"
build_and_measure "ppl-meta-media" "./ppl-meta-media"
build_and_measure "ppl-meta-gateway" "./ppl-meta-gateway"
build_and_measure "ppl-meta-orchestrator" "./ppl-meta-orchestrator"

echo -e "${GREEN}🎉 Docker optimization complete!${NC}"
echo ""
echo -e "${BLUE}📊 Final size comparison:${NC}"
docker images | grep -E "(ppl-meta.*optimized|ppl-meta.*latest)" | sort

echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo "1. Test the optimized images with docker-compose"
echo "2. Update docker-compose files to use optimized images"
echo "3. Update CI/CD pipelines to use the new Dockerfiles"
echo ""
echo -e "${GREEN}✅ To use optimized images in docker-compose, tag them:${NC}"
echo "   docker tag ppl-meta-node-optimized:latest ppl-meta-node:latest"
echo "   docker tag ppl-meta-media-optimized:latest ppl-meta-media:latest"
echo "   docker tag ppl-meta-gateway-optimized:latest ppl-meta-gateway:latest"
echo "   docker tag ppl-meta-orchestrator-optimized:latest ppl-meta-orchestrator:latest"
