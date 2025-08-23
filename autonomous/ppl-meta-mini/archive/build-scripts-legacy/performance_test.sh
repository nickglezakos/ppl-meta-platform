#!/bin/bash

# PPL Meta Mini - Performance Comparison Test
echo "PPL Meta Mini - Performance Comparison Test"
echo "==========================================="

# Test simple vs Cython performance
echo ""
echo "1. Testing Simple Python Build (port 8004)..."
if curl -s --connect-timeout 3 http://localhost:8004/health >/dev/null 2>&1; then
    echo "   Simple service is responding"
    echo "   Response time test (5 requests):"
    for i in {1..5}; do
        time_result=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8004/health)
        echo "   Request $i: ${time_result}s"
    done
else
    echo "   Simple service is NOT responding"
fi

echo ""
echo "2. Testing Cython Build (port 8005)..."
if curl -s --connect-timeout 3 http://localhost:8005/health >/dev/null 2>&1; then
    echo "   Cython service is responding"
    echo "   Response time test (5 requests):"
    for i in {1..5}; do
        time_result=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8005/health)
        echo "   Request $i: ${time_result}s"
    done
else
    echo "   Cython service is NOT responding"
fi

echo ""
echo "3. Image size comparison:"
docker images | grep ppl-meta-mini | awk '{printf "   %-40s %10s\n", $1":"$2, $7}'

echo ""
echo "4. Container resource usage:"
echo "   Simple container:"
docker stats --no-stream ppl-meta-mini-simple 2>/dev/null || echo "   Not running"
echo "   Cython container:"
docker stats --no-stream ppl-meta-mini-cython 2>/dev/null || echo "   Not running"

echo ""
echo "Performance comparison complete."
