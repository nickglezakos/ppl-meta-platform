#!/bin/bash

# PPL Meta Mini - Simple Python Docker Build Script
set -e

echo "🐍 Building PPL Meta Mini with simple Python image..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Build image
echo -e "${BLUE}📦 Building Docker image (simple Python)...${NC}"
docker build -f Dockerfile.simple -t ppl-meta-mini:simple .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
    
    # Show image info
    echo -e "${BLUE}📊 Image information:${NC}"
    docker images ppl-meta-mini:simple
    
    echo -e "${YELLOW}🚀 To run the container:${NC}"
    echo "docker run -p 8004:8004 ppl-meta-mini:simple"
    echo
    echo -e "${YELLOW}🚀 Or use docker-compose:${NC}"
    echo "docker-compose -f docker-compose.simple.yml up -d"
    echo
    echo -e "${YELLOW}🔍 To test the service:${NC}"
    echo "curl http://localhost:8004/health"
    echo
    echo -e "${BLUE}📋 Next steps for Cython optimization:${NC}"
    echo "1. Test this working image first"
    echo "2. Debug FastAPI + Cython compatibility issues"
    echo "3. Fix dlib compilation in Cython build"
    echo "4. Switch to Cython build once stable"
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi
