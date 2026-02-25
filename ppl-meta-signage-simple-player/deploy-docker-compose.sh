#!/bin/bash

# Deploy Docker Compose with Auto-detected Backend IP
# Usage: ./deploy-docker-compose.sh <rpi_ip> [rpi_user]

set -e

RPI_IP="${1}"
RPI_USER="${2:-pi}"

if [ -z "$RPI_IP" ]; then
    echo "❌ Error: RPi IP address required"
    echo "Usage: $0 <rpi_ip> [rpi_user]"
    echo "Example: $0 192.168.1.77 pi"
    exit 1
fi

echo "🔍 Detecting backend IP address..."

# Get the IP address of this dev laptop on the local network (192.168.1.x)
BACKEND_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | grep "192.168.1" | awk '{print $2}' | head -n 1)

if [ -z "$BACKEND_IP" ]; then
    echo "⚠️  Could not auto-detect 192.168.1.x IP, trying alternative method..."
    BACKEND_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
fi

if [ -z "$BACKEND_IP" ]; then
    echo "❌ Error: Could not detect local IP address"
    echo "Please ensure you're connected to the local network (192.168.1.x)"
    exit 1
fi

echo "✅ Detected backend IP: $BACKEND_IP"
echo ""

# Create docker-compose.yml with detected IP
echo "📝 Creating docker-compose.yml..."

cat > /tmp/docker-compose.yml << EOF
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
    image: ppl-meta-signage-player:arm64
    container_name: signage-player
    restart: unless-stopped
    ports:
      - "8009:8009"
    environment:
      - DISPLAY=:0
      - GATEWAY_URL=http://${BACKEND_IP}:8080
      - DISCOVERY_URL=http://${BACKEND_IP}:8003
    volumes:
      - ./logs:/app/logs
      - /home/${RPI_USER}/.local/share/signage_simple_player:/root/.local/share/signage_simple_player
    network_mode: host
EOF

echo "✅ docker-compose.yml created with:"
echo "   GATEWAY_URL=http://${BACKEND_IP}:8080"
echo "   DISCOVERY_URL=http://${BACKEND_IP}:8003"
echo ""

# Test SSH connection
echo "🔗 Testing connection to RPi..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${RPI_USER}@${RPI_IP} "echo 'Connected'" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to ${RPI_USER}@${RPI_IP}"
    echo "Please check:"
    echo "  - RPi is powered on and connected to network"
    echo "  - SSH is enabled on the RPi"
    echo "  - IP address is correct"
    exit 1
fi
echo "✅ Connected to ${RPI_USER}@${RPI_IP}"
echo ""

# Backup existing docker-compose.yml
echo "💾 Backing up existing docker-compose.yml..."
ssh ${RPI_USER}@${RPI_IP} "cd ~/ppl-meta-deploy && cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"

# Copy new docker-compose.yml to RPi
echo "📤 Deploying docker-compose.yml to RPi..."
scp /tmp/docker-compose.yml ${RPI_USER}@${RPI_IP}:~/ppl-meta-deploy/docker-compose.yml

# Restart signage-player to apply changes
echo "🔄 Restarting signage-player..."
ssh ${RPI_USER}@${RPI_IP} "cd ~/ppl-meta-deploy && docker compose restart signage-player"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Checking signage-player logs..."
ssh ${RPI_USER}@${RPI_IP} "cd ~/ppl-meta-deploy && docker compose logs --tail 30 signage-player"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Signage should now connect to backend at:"
echo "   Gateway:   http://${BACKEND_IP}:8080"
echo "   Discovery: http://${BACKEND_IP}:8003"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
