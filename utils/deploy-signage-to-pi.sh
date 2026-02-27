#!/bin/bash

# Deploy Signage Player to Raspberry Pi
# This script saves the Docker image, transfers it to the Pi, and loads it

set -e

echo "🚀 Deploying Signage Player to Raspberry Pi..."

PI_HOST="pi@192.168.1.77"
IMAGE_NAME="ppl-meta-signage-player:arm64"
TAR_FILE="/tmp/signage-player-arm64.tar"

# Step 1: Save Docker image to tar file
echo "📦 Saving Docker image..."
docker save -o $TAR_FILE $IMAGE_NAME

# Step 2: Transfer to Pi
echo "📤 Transferring image to Pi (this may take a few minutes)..."
scp $TAR_FILE $PI_HOST:/tmp/

# Step 3: Load image on Pi
echo "📥 Loading image on Pi..."
ssh $PI_HOST "docker load -i /tmp/signage-player-arm64.tar"

# Step 4: Update docker-compose tag
echo "🔧 Updating docker-compose.yml..."
ssh $PI_HOST "cd ~/ppl-meta-deploy && sed -i 's/ppl-meta-signage-player:latest/ppl-meta-signage-player:arm64/' docker-compose.yml"

# Step 5: Start service
echo "▶️  Starting signage player..."
ssh $PI_HOST "cd ~/ppl-meta-deploy && docker compose up -d signage-player"

# Step 6: Check status
echo "✅ Checking service status..."
ssh $PI_HOST "cd ~/ppl-meta-deploy && docker compose ps signage-player"

# Step 7: Show logs
echo "📋 Recent logs:"
ssh $PI_HOST "cd ~/ppl-meta-deploy && docker compose logs --tail 20 signage-player"

# Cleanup
echo "🧹 Cleaning up..."
rm $TAR_FILE
ssh $PI_HOST "rm /tmp/signage-player-arm64.tar"

echo ""
echo "✅ Deployment complete!"
echo "Signage player is running on the Pi."
echo "It should auto-register with Discovery Service at 192.168.1.75:8003"
echo ""
echo "To view logs: ssh pi@192.168.1.77 'cd ~/ppl-meta-deploy && docker compose logs -f signage-player'"
echo "To stop: ssh pi@192.168.1.77 'cd ~/ppl-meta-deploy && docker compose stop signage-player'"
echo "To restart: ssh pi@192.168.1.77 'cd ~/ppl-meta-deploy && docker compose restart signage-player'"
