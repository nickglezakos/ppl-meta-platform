#!/bin/bash
# Build and Deploy Signage Docker Image to Raspberry Pi
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}PPL Meta Signage - Docker Build & Deploy${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Configuration
IMAGE_NAME="ppl-meta-signage-player"
IMAGE_TAG="arm64"
RPI_IP="${1:-192.168.1.77}"
RPI_USER="${2:-pi}"

if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <RPI_IP> [RPI_USER]${NC}"
    echo -e "${YELLOW}Using default: $0 $RPI_IP $RPI_USER${NC}"
    echo ""
fi

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Image: $IMAGE_NAME:$IMAGE_TAG"
echo "  Target: $RPI_USER@$RPI_IP"
echo ""

# Step 1: Build Docker image for ARM64
echo -e "${BLUE}🔨 Building Docker image for ARM64...${NC}"
cd ppl-meta-signage-simple-player

# Create or use existing builder
if ! docker buildx inspect signage-builder >/dev/null 2>&1; then
    echo "Creating new buildx builder..."
    docker buildx create --name signage-builder --use
else
    echo "Using existing buildx builder..."
    docker buildx use signage-builder
fi

docker buildx build \
    --platform linux/arm64 \
    -t $IMAGE_NAME:$IMAGE_TAG \
    --load \
    .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built successfully${NC}"
echo ""

# Step 2: Save image to tar
echo -e "${BLUE}📦 Saving Docker image to tar...${NC}"
docker save $IMAGE_NAME:$IMAGE_TAG | gzip > /tmp/signage-player.tar.gz

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to save Docker image${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image saved to /tmp/signage-player.tar.gz${NC}"
echo ""

# Step 3: Transfer to Raspberry Pi
echo -e "${BLUE}📤 Transferring image to Raspberry Pi...${NC}"
scp /tmp/signage-player.tar.gz $RPI_USER@$RPI_IP:/tmp/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to transfer image${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image transferred successfully${NC}"
echo ""

# Step 4: Load image on Raspberry Pi
echo -e "${BLUE}📥 Loading image on Raspberry Pi...${NC}"
ssh $RPI_USER@$RPI_IP "docker load < /tmp/signage-player.tar.gz && rm /tmp/signage-player.tar.gz"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to load image on RPi${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image loaded on RPi${NC}"
echo ""

# Step 5: Restart container
echo -e "${BLUE}🔄 Restarting signage container...${NC}"
ssh $RPI_USER@$RPI_IP "cd ~/ppl-meta-deploy && docker compose down && docker compose up -d"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to restart container${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Container restarted successfully${NC}"
echo ""

# Cleanup
rm /tmp/signage-player.tar.gz

# Step 6: Check status
echo -e "${BLUE}📊 Checking container status...${NC}"
echo ""
ssh $RPI_USER@$RPI_IP "docker ps | grep signage-player"
echo ""

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Check logs: ssh $RPI_USER@$RPI_IP 'docker logs -f signage-player'"
echo "  2. The configuration at ~/.local/share/signage_simple_player/ will be used"
echo "  3. App should auto-connect to backend at 192.168.1.70"
echo ""
