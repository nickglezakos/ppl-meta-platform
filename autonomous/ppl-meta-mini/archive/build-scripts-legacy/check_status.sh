#!/bin/bash

# PPL Meta Mini - Simple Status Check (No Terminal Escapes)
echo "PPL Meta Mini Cython Build - Status Check"
echo "=========================================="

# Check if Cython container is running
echo ""
echo "1. Checking Cython container status..."
if docker ps | grep -q ppl-meta-mini-cython; then
    echo "   ✓ Cython container is running"
else
    echo "   ✗ Cython container is NOT running"
fi

# Check available images
echo ""
echo "2. Available Docker images:"
docker images | grep ppl-meta-mini

# Test Cython service
echo ""
echo "3. Testing Cython service (port 8005)..."
if curl -s --connect-timeout 3 http://localhost:8005/health >/dev/null 2>&1; then
    echo "   ✓ Cython service is responding"
    echo "   Health check result:"
    curl -s http://localhost:8005/health | python3 -m json.tool 2>/dev/null || echo "   Could not parse JSON"
else
    echo "   ✗ Cython service is NOT responding"
fi

# Test simple service if running
echo ""
echo "4. Testing simple service (port 8004)..."
if curl -s --connect-timeout 3 http://localhost:8004/health >/dev/null 2>&1; then
    echo "   ✓ Simple service is responding"
    echo "   Health check result:"
    curl -s http://localhost:8004/health | python3 -m json.tool 2>/dev/null || echo "   Could not parse JSON"
else
    echo "   ✗ Simple service is NOT responding"
fi

echo ""
echo "Status check complete."
