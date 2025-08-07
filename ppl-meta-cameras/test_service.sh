#!/bin/bash

# PPL Meta Cameras Microservice Test Script

echo "🎥 Testing PPL Meta Cameras Microservice"
echo "========================================"

# Configuration
HOST="localhost"
PORT="8005"
BASE_URL="http://${HOST}:${PORT}"

echo ""
echo "1️⃣ Testing Health Endpoints..."

# Basic health check
echo "   • Basic health check:"
curl -s "${BASE_URL}/health/" | python3 -c "import sys, json; print('✅ Health check passed' if json.load(sys.stdin).get('status') == 'healthy' else '❌ Health check failed')" 2>/dev/null || echo "❌ Service not responding"

# Readiness check
echo "   • Readiness check:"
curl -s "${BASE_URL}/health/ready" | python3 -c "import sys, json; print('✅ Service ready' if json.load(sys.stdin).get('status') == 'ready' else '❌ Service not ready')" 2>/dev/null || echo "❌ Readiness check failed"

echo ""
echo "2️⃣ Testing Authentication..."

# Get demo token
echo "   • Creating demo token:"
TOKEN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/demo-token?role=administrator")
TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "✅ Demo token created successfully"
else
    echo "❌ Failed to create demo token"
    exit 1
fi

echo ""
echo "3️⃣ Testing Camera Detection..."

# Detect cameras
echo "   • Detecting cameras:"
DETECT_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" -X POST "${BASE_URL}/api/v1/cameras/detect")
CAMERA_COUNT=$(echo "$DETECT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('detected_count', 0))" 2>/dev/null)

echo "   Detected $CAMERA_COUNT cameras"

echo ""
echo "4️⃣ Testing Camera Listing..."

# List cameras
echo "   • Listing cameras:"
LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/api/v1/cameras/")
LISTED_COUNT=$(echo "$LIST_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)

echo "   Listed $LISTED_COUNT cameras from database"

echo ""
echo "5️⃣ Testing Active Connections..."

# List active connections
echo "   • Checking active connections:"
ACTIVE_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/api/v1/cameras/active")
ACTIVE_COUNT=$(echo "$ACTIVE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('active_count', 0))" 2>/dev/null)

echo "   Active connections: $ACTIVE_COUNT"

echo ""
echo "6️⃣ Testing API Documentation..."

# Check docs endpoint
echo "   • API documentation:"
curl -s "${BASE_URL}/docs" | grep -q "PPL Meta Cameras" && echo "✅ API docs available at ${BASE_URL}/docs" || echo "❌ API docs not accessible"

echo ""
echo "🎉 Test Summary"
echo "=============="
echo "Service URL: ${BASE_URL}"
echo "API Docs: ${BASE_URL}/docs"
echo "Health: ${BASE_URL}/health/"
echo ""
echo "Demo Token (24h): $TOKEN"
echo ""
echo "Example Usage:"
echo "curl -H 'Authorization: Bearer $TOKEN' '${BASE_URL}/api/v1/cameras/'"
echo ""
echo "✅ PPL Meta Cameras microservice test completed!"
