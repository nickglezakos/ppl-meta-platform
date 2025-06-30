#!/bin/bash
# Script to reorganize PPL Meta Platform structure properly
# This moves the gateway service out of the docs folder

echo "🔧 Reorganizing PPL Meta Platform Structure..."

# Check if we're in the right directory
if [ ! -d "docs/ppl-meta-geteway" ]; then
    echo "❌ Gateway service not found in docs/ppl-meta-geteway"
    echo "   This script should be run from the ppl-meta-node directory"
    exit 1
fi

# Create the proper structure
echo "📁 Creating proper directory structure..."

# Move up to the parent directory (ppl-meta-code)
cd ..

# Create the gateway service as a separate project
if [ -d "ppl-meta-node/docs/ppl-meta-geteway" ]; then
    echo "🚚 Moving gateway service to proper location..."
    mv ppl-meta-node/docs/ppl-meta-geteway ./ppl-meta-gateway
    echo "✅ Gateway service moved to ppl-meta-gateway/"
fi

# Create placeholders for other services if they don't exist
if [ ! -d "ppl-meta-media" ]; then
    echo "📁 Creating ppl-meta-media placeholder..."
    mkdir -p ppl-meta-media
    echo "# PPL Meta Media Service" > ppl-meta-media/README.md
fi

if [ ! -d "ppl-meta-orchestrator" ]; then
    echo "📁 Creating ppl-meta-orchestrator placeholder..."
    mkdir -p ppl-meta-orchestrator  
    echo "# PPL Meta Orchestrator Service" > ppl-meta-orchestrator/README.md
fi

# Create the ecosystem docker-compose file
echo "🐳 Creating ecosystem Docker Compose configuration..."

cat > docker-compose.ecosystem.yml << 'EOF'
# PPL Meta Platform - Complete Ecosystem
# This orchestrates all microservices in the platform

version: '3.8'

# Include the infrastructure from the node service
include:
  - path: ./ppl-meta-node/docker-compose.infrastructure.yml

services:
  # Override the gateway service to use the properly located code
  ppl-meta-gateway:
    build:
      context: ./ppl-meta-gateway
      dockerfile: Dockerfile
    container_name: ppl-meta-gateway
    ports:
      - "8080:8080"
    environment:
      - SERVICE_NAME=ppl-meta-gateway
      - SERVICE_VERSION=1.0.0
      - HOST=0.0.0.0
      - PORT=8080
      - DEBUG=false
      - SERVICE_DISCOVERY_ENABLED=true
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
    networks:
      - ppl-network
      - ppl-internal
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Add other services as you create them
  # ppl-meta-media:
  #   build: ./ppl-meta-media
  #   ports:
  #     - "8000:8000"
  #   networks:
  #     - ppl-network
  #     - ppl-internal

  # ppl-meta-orchestrator:
  #   build: ./ppl-meta-orchestrator
  #   ports:
  #     - "8002:8002"
  #   networks:
  #     - ppl-network
  #     - ppl-internal

networks:
  ppl-network:
    external: true
  ppl-internal:
    external: true
EOF

echo ""
echo "✅ Reorganization Complete!"
echo ""
echo "📊 New Structure:"
echo "ppl-meta-code/"
echo "├── ppl-meta-gateway/           # API Gateway (moved from docs)"
echo "├── ppl-meta-node/              # User Management"
echo "├── ppl-meta-media/             # Media Service (placeholder)"
echo "├── ppl-meta-orchestrator/      # Orchestrator (placeholder)"
echo "└── docker-compose.ecosystem.yml # Complete ecosystem"
echo ""
echo "🔧 Next Steps:"
echo "1. Move your other microservices to this level"
echo "2. Update the ecosystem docker-compose file"
echo "3. Run: docker-compose -f docker-compose.ecosystem.yml up -d"
echo ""
echo "⚠️  Note: Update any references to the old gateway location"
