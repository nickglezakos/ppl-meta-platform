#!/bin/bash

# PPL Meta Mini - Cython Docker Build Script
set -e

echo "🔧 Building PPL Meta Mini with Cython compilation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Stop any existing containers
echo -e "${BLUE}🛑 Stopping existing containers...${NC}"
docker-compose -f docker-compose.cython.yml down 2>/dev/null || true

# Build image using docker-compose
echo -e "${BLUE}📦 Building Docker image with Cython compilation...${NC}"
docker-compose -f docker-compose.cython.yml build

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
    
    # Start the service
    echo -e "${BLUE}� Starting Cython-optimized service...${NC}"
    docker-compose -f docker-compose.cython.yml up -d
    
    # Wait for startup
    echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
    sleep 15
    
    # Test the service
    echo -e "${BLUE}🏥 Testing health endpoint...${NC}"
    curl -s http://localhost:8005/health | python3 -m json.tool 2>/dev/null || echo "Service not ready yet"
    
    # Show logs
    echo -e "${BLUE}� Container logs:${NC}"
    docker-compose -f docker-compose.cython.yml logs --tail=20
    
    echo -e "${GREEN}✅ Cython build complete! Service available at:${NC}"
    echo "   - Health: http://localhost:8005/health"
    echo "   - Docs: http://localhost:8005/docs"
    echo "   - Main: http://localhost:8005/"
    
    # Show image info
    echo -e "${BLUE}📊 Image information:${NC}"
    docker images ppl-meta-mini-cython
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi
