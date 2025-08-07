#!/bin/bash

# PPL Meta Mini - Cython Docker Build Script (Clean Version)
set -e

echo "Building PPL Meta Mini with Cython compilation..."

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.cython.yml down 2>/dev/null || true

# Build image using docker-compose
echo "Building Docker image with Cython compilation..."
docker-compose -f docker-compose.cython.yml build

if [ $? -eq 0 ]; then
    echo "Docker image built successfully!"
    
    # Start the service
    echo "Starting Cython-optimized service..."
    docker-compose -f docker-compose.cython.yml up -d
    
    # Wait for startup
    echo "Waiting for service to start..."
    sleep 15
    
    # Test the service
    echo "Testing health endpoint..."
    curl -s http://localhost:8005/health | python3 -m json.tool 2>/dev/null || echo "Service not ready yet"
    
    # Show logs
    echo "Container logs:"
    docker-compose -f docker-compose.cython.yml logs --tail=20
    
    echo "Cython build complete! Service available at:"
    echo "   - Health: http://localhost:8005/health"
    echo "   - Docs: http://localhost:8005/docs"
    echo "   - Main: http://localhost:8005/"
    
    # Show image info
    echo "Image information:"
    docker images | grep ppl-meta-mini
else
    echo "Docker build failed!"
    exit 1
fi
