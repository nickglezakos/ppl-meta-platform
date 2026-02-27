#!/bin/bash

# Test script for workflow settings endpoints

echo "🧪 Testing Camera Workflow Settings Endpoints"
echo "=============================================="

# Get auth token
echo ""
echo "1️⃣ Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/users/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=fresh.user@example.com&password=NewPassword234!')

TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Authentication failed"
  echo "Response: $AUTH_RESPONSE"
  exit 1
fi

echo "✅ Authentication successful"
echo "Token: ${TOKEN:0:50}..."

# Test GET workflow settings
echo ""
echo "2️⃣ Getting workflow settings for usb_camera_0..."
GET_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/cameras/usb_camera_0/workflow-settings \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo $GET_RESPONSE | jq '.'

# Test PATCH workflow settings
echo ""
echo "3️⃣ Updating workflow settings..."
PATCH_RESPONSE=$(curl -s -X PATCH http://localhost:8080/api/v1/cameras/usb_camera_0/workflow-settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_face_detection": true,
    "detection_methods": ["opencv", "dlib", "mtcnn"],
    "confidence_threshold": 0.8,
    "enable_performance_optimization": true,
    "show_performance_indicators": true,
    "mvr_quality_threshold": 0.25
  }')

echo "Response:"
echo $PATCH_RESPONSE | jq '.'

# Verify the update
echo ""
echo "4️⃣ Verifying the update..."
VERIFY_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/cameras/usb_camera_0/workflow-settings \
  -H "Authorization: Bearer $TOKEN")

echo "Updated settings:"
echo $VERIFY_RESPONSE | jq '.'

# Check key values
AUTO_FACE=$(echo $VERIFY_RESPONSE | jq -r '.auto_face_detection')
CONFIDENCE=$(echo $VERIFY_RESPONSE | jq -r '.confidence_threshold')
MVR_QUALITY=$(echo $VERIFY_RESPONSE | jq -r '.mvr_quality_threshold')

echo ""
echo "📊 Verification Results:"
echo "  - Auto Face Detection: $AUTO_FACE (expected: true)"
echo "  - Confidence Threshold: $CONFIDENCE (expected: 0.8)"
echo "  - MVR Quality Threshold: $MVR_QUALITY (expected: 0.25)"

if [ "$AUTO_FACE" = "true" ] && [ "$CONFIDENCE" = "0.8" ] && [ "$MVR_QUALITY" = "0.25" ]; then
  echo ""
  echo "✅ All tests passed!"
else
  echo ""
  echo "⚠️  Some values don't match expected results"
fi

echo ""
echo "=============================================="
echo "🏁 Testing complete"
