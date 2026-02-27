#!/bin/bash

# Test script for workflow settings endpoints (direct to cameras service)

echo "🧪 Testing Camera Workflow Settings Endpoints (Direct)"
echo "======================================================="

# Test GET workflow settings
echo ""
echo "1️⃣ Getting workflow settings for usb_camera_0..."
GET_RESPONSE=$(curl -s -X GET http://localhost:8005/api/v1/cameras/usb_camera_0/workflow-settings)

echo "Response:"
echo $GET_RESPONSE | jq '.'

if echo $GET_RESPONSE | jq -e '.device_id' > /dev/null 2>&1; then
  echo "✅ GET request successful"
else
  echo "❌ GET request failed"
  exit 1
fi

# Test PATCH workflow settings
echo ""
echo "2️⃣ Updating workflow settings..."
PATCH_RESPONSE=$(curl -s -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/workflow-settings?auto_face_detection=true&confidence_threshold=0.8&enable_performance_optimization=true&show_performance_indicators=true&mvr_quality_threshold=0.25" \
  -H "Content-Type: application/json")

echo "Response:"
echo $PATCH_RESPONSE | jq '.'

# Verify the update
echo ""
echo "3️⃣ Verifying the update..."
VERIFY_RESPONSE=$(curl -s -X GET http://localhost:8005/api/v1/cameras/usb_camera_0/workflow-settings)

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

# Test with detection methods as a list
echo ""
echo "4️⃣ Testing with multiple detection methods..."
METHODS_RESPONSE=$(curl -s -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/workflow-settings" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_face_detection": true,
    "detection_methods": ["opencv", "dlib", "mtcnn"],
    "confidence_threshold": 0.75
  }')

echo "Response:"
echo $METHODS_RESPONSE | jq '.'

echo ""
echo "======================================================="
echo "🏁 Testing complete"
