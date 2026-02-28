#!/bin/bash

# Flutter Camera Registration Test Script
# Tests the correct authentication and camera registration flow

echo "🧪 Flutter Camera Registration Test"
echo "=================================="

# Step 1: Get authentication token
echo "🔑 Step 1: Getting authentication token..."
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])' 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get authentication token"
  exit 1
fi

echo "✅ Token obtained: ${TOKEN:0:20}..."

# Step 2: Test camera registration with CORRECT payload
echo ""
echo "📱 Step 2: Testing camera registration with CORRECT payload..."

# Generate unique device ID
DEVICE_ID="flutter_test_$(date +%s)"

# Test the CORRECT endpoint with CORRECT payload format
RESPONSE=$(curl -s -X POST 'http://localhost:8005/api/v1/cameras/mobile' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Flutter Test Camera '"$(date +%H:%M:%S)"'",
    "device_id": "'"$DEVICE_ID"'",
    "ip_address": "192.168.1.100",
    "port": 8554,
    "device_model": "Flutter Test Device",
    "device_manufacturer": "PPL Meta",
    "app_version": "1.0.0",
    "resolution_width": 1920,
    "resolution_height": 1080,
    "max_fps": 30,
    "supports_audio": true
  }')

echo "📥 Registration response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Check if registration was successful
if echo "$RESPONSE" | grep -q "Mobile camera registered successfully"; then
  echo ""
  echo "✅ SUCCESS: Camera registration working correctly!"
  echo "📋 Flutter developers should use:"
  echo "   - Endpoint: /api/v1/cameras/mobile"
  echo "   - Payload: MobileCameraCreate schema (see documentation)"
else
  echo ""
  echo "❌ FAILED: Camera registration not working"
  echo "🔍 Check service status and JWT permissions"
fi

echo ""
echo "📚 For complete implementation guide, see:"
echo "   docs/development/FLUTTER_AUTHENTICATION_FLOW.md"
