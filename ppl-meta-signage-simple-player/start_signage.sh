#!/bin/bash
# PPL Meta Signage - Startup Script with Auto-Configuration Check
# 
# This script should be used to start the signage application.
# It automatically checks for configuration and prompts for setup if needed.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_TOOL="${SCRIPT_DIR}/setup_console.py"
APP_DIR="${SCRIPT_DIR}"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}PPL Meta Signage - Startup${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is required but not installed${NC}"
    exit 1
fi

# Check if requests library is available
if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing required Python dependencies...${NC}"
    pip3 install requests --user || {
        echo -e "${RED}❌ Failed to install requests library${NC}"
        echo -e "${YELLOW}Please install manually: pip3 install requests${NC}"
        exit 1
    }
fi

# Check current configuration
echo -e "${BLUE}🔍 Checking configuration...${NC}"
if python3 "${SETUP_TOOL}" --show 2>/dev/null; then
    # Configuration exists
    echo ""
    echo -e "${GREEN}✅ Configuration found${NC}"
    echo ""
    
    # Test connection
    echo -e "${BLUE}🔍 Testing backend connection...${NC}"
    if python3 "${SETUP_TOOL}" --test; then
        echo ""
        echo -e "${GREEN}✅ Backend connection successful${NC}"
        echo ""
    else
        echo ""
        echo -e "${YELLOW}⚠️  Cannot connect to backend${NC}"
        echo ""
        echo "Options:"
        echo "  1. Check if backend services are running"
        echo "  2. Reconfigure backend settings"
        echo ""
        
        read -p "Reconfigure now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "${SETUP_TOOL}"
            if [ $? -ne 0 ]; then
                echo -e "${RED}❌ Configuration failed${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}⚠️  Proceeding with existing configuration...${NC}"
        fi
    fi
else
    # No configuration found
    echo ""
    echo -e "${YELLOW}⚠️  No configuration found${NC}"
    echo ""
    echo "This appears to be the first time running the signage application."
    echo "You need to configure the backend connection settings."
    echo ""
    
    read -p "Run configuration setup now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        python3 "${SETUP_TOOL}"
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Configuration failed${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Cannot start without configuration${NC}"
        echo ""
        echo "Run setup manually:"
        echo "  python3 ${SETUP_TOOL}"
        exit 1
    fi
fi

# Start the Flutter application
echo ""
echo -e "${GREEN}🚀 Starting PPL Meta Signage Application...${NC}"
echo ""

# Check if we're running on Linux (RPi)
if [ "$(uname)" == "Linux" ]; then
    # Linux/RPi - use the built executable
    if [ -f "${APP_DIR}/build/linux/x64/release/bundle/signage_simple_player" ]; then
        cd "${APP_DIR}/build/linux/x64/release/bundle"
        ./signage_simple_player
    elif [ -f "${APP_DIR}/signage_simple_player" ]; then
        cd "${APP_DIR}"
        ./signage_simple_player
    else
        echo -e "${YELLOW}⚠️  Built executable not found. Building application...${NC}"
        cd "${APP_DIR}"
        flutter build linux --release
        cd "${APP_DIR}/build/linux/x64/release/bundle"
        ./signage_simple_player
    fi
elif [ "$(uname)" == "Darwin" ]; then
    # macOS - use flutter run
    cd "${APP_DIR}"
    flutter run -d macos --release
else
    echo -e "${RED}❌ Unsupported platform: $(uname)${NC}"
    exit 1
fi
