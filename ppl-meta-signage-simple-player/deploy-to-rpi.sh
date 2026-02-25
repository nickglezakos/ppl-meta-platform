#!/bin/bash
#
# PPL Meta Signage - Raspberry Pi Deployment Script
#
# This script assists with deploying the signage application to a Raspberry Pi

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}PPL Meta Signage - RPi Deployment Script${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if rsync is available
if ! command -v rsync &> /dev/null; then
    echo -e "${RED}❌ rsync is required but not installed${NC}"
    echo "Install with: brew install rsync (macOS) or apt install rsync (Linux)"
    exit 1
fi

# Get RPi details
read -p "Raspberry Pi IP address: " RPI_IP
read -p "Raspberry Pi username [pi]: " RPI_USER
RPI_USER=${RPI_USER:-pi}

echo ""
echo -e "${BLUE}Testing connection to ${RPI_USER}@${RPI_IP}...${NC}"

# Test SSH connection
if ! ssh -o ConnectTimeout=5 "${RPI_USER}@${RPI_IP}" "echo 'Connection successful'" &>/dev/null; then
    echo -e "${RED}❌ Cannot connect to Raspberry Pi${NC}"
    echo ""
    echo "Make sure:"
    echo "  1. The Raspberry Pi is powered on and connected to network"
    echo "  2. SSH is enabled on the Pi"
    echo "  3. You can SSH to it: ssh ${RPI_USER}@${RPI_IP}"
    exit 1
fi

echo -e "${GREEN}✅ Connection successful${NC}"
echo ""

# Deployment directory on RPi
DEPLOY_DIR="/home/${RPI_USER}/ppl-meta-signage"

echo -e "${BLUE}📦 Preparing deployment...${NC}"
echo "   Local: $(pwd)/ppl-meta-signage-simple-player"
echo "   Remote: ${RPI_USER}@${RPI_IP}:${DEPLOY_DIR}"
echo ""

# Create deployment directory on RPi
echo -e "${BLUE}Creating deployment directory...${NC}"
ssh "${RPI_USER}@${RPI_IP}" "mkdir -p ${DEPLOY_DIR}"

# Build the application for Linux
echo ""
echo -e "${BLUE}🔨 Building application for Linux...${NC}"
cd ppl-meta-signage-simple-player
flutter build linux --release

if [ ! -d "build/linux/x64/release/bundle" ]; then
    echo -e "${RED}❌ Build failed - bundle directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build successful${NC}"
echo ""

# Sync files to RPi
echo -e "${BLUE}📤 Deploying to Raspberry Pi...${NC}"
echo ""

# Sync the built application
rsync -avz --progress \
    build/linux/x64/release/bundle/ \
    "${RPI_USER}@${RPI_IP}:${DEPLOY_DIR}/app/"

# Sync setup scripts
rsync -avz --progress \
    setup_console.py \
    start_signage.sh \
    "${RPI_USER}@${RPI_IP}:${DEPLOY_DIR}/"

# Make scripts executable on RPi
ssh "${RPI_USER}@${RPI_IP}" "chmod +x ${DEPLOY_DIR}/setup_console.py ${DEPLOY_DIR}/start_signage.sh"

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "1. SSH to your Raspberry Pi:"
echo -e "   ${YELLOW}ssh ${RPI_USER}@${RPI_IP}${NC}"
echo ""
echo "2. Navigate to the deployment directory:"
echo -e "   ${YELLOW}cd ${DEPLOY_DIR}${NC}"
echo ""
echo "3. Run the startup script (it will prompt for configuration):"
echo -e "   ${YELLOW}./start_signage.sh${NC}"
echo ""
echo "   OR configure manually first:"
echo -e "   ${YELLOW}./setup_console.py${NC}"
echo ""
echo "4. The application will:"
echo "   - Prompt for backend IP and port (first time)"
echo "   - Test the connection"
echo "   - Save configuration"
echo "   - Start the signage player"
echo ""
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Deployment directory on RPi: ${DEPLOY_DIR}"
echo ""
