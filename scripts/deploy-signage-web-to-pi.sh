#!/bin/bash
# Deploy Signage Player Web to Raspberry Pi

set -e

PI_HOST="pi@192.168.1.77"
IMAGE_NAME="ppl-meta-signage-player:web"
IMAGE_TAR="/tmp/signage-player-web.tar"

echo "🎬 Deploying Signage Player Web to Raspberry Pi..."
echo "=================================================="

# Wait for local build to complete
echo "⏳ Checking if Docker image exists locally..."
if ! docker image inspect $IMAGE_NAME >/dev/null 2>&1; then
    echo "❌ Image $IMAGE_NAME not found locally. Build it first with:"
    echo "   cd ppl-meta-signage-simple-player"
    echo "   docker buildx build --platform linux/arm64 -t $IMAGE_NAME -f Dockerfile.web . --load"
    exit 1
fi

echo "✅ Image found locally"

# Save image to tar
echo "📦 Saving Docker image to tar file..."
docker save $IMAGE_NAME -o $IMAGE_TAR
echo "✅ Image saved to $IMAGE_TAR"

# Transfer to Pi
echo "🚀 Transferring image to Pi (this may take a few minutes)..."
scp $IMAGE_TAR $PI_HOST:/tmp/
echo "✅ Image transferred"

# Load image on Pi
echo "📥 Loading image on Pi..."
ssh $PI_HOST "docker load -i /tmp/signage-player-web.tar && rm /tmp/signage-player-web.tar"
echo "✅ Image loaded on Pi"

# Update docker-compose.yml
echo "📝 Updating docker-compose.yml on Pi..."
ssh $PI_HOST "cd ~/ppl-meta-deploy && cat > docker-compose.yml" << 'EOF'
version: '3.8'

services:
  edge-camera:
    image: ppl-meta-edge-camera:latest
    container_name: edge-camera
    restart: unless-stopped
    ports:
      - "9001:9001"
    devices:
      - /dev/video0:/dev/video0
    privileged: true
    volumes:
      - ./logs:/app/logs
    network_mode: host

  signage-player:
    image: ppl-meta-signage-player:web
    container_name: signage-player
    restart: unless-stopped
    ports:
      - "8009:8009"
    environment:
      - GATEWAY_URL=http://192.168.1.75:8080
    volumes:
      - ./logs:/app/logs
    network_mode: host
EOF
echo "✅ docker-compose.yml updated"

# Start services
echo "🚀 Starting services on Pi..."
ssh $PI_HOST "cd ~/ppl-meta-deploy && docker compose up -d"
echo "✅ Services started"

# Check status
echo "📊 Checking service status..."
ssh $PI_HOST "cd ~/ppl-meta-deploy && docker compose ps"

# Clean up
echo "🧹 Cleaning up local tar file..."
rm $IMAGE_TAR
echo "✅ Cleanup complete"

echo ""
echo "=================================================="
echo "✨ Deployment complete!"
echo ""
echo "📱 Access signage player at: http://192.168.1.77:8009"
echo "📹 Edge camera at: http://192.168.1.77:9001"
echo ""
echo "View logs with:"
echo "  ssh $PI_HOST 'cd ~/ppl-meta-deploy && docker compose logs -f signage-player'"
echo "=================================================="
