#!/bin/bash

echo "Testing Workflow Settings Fixes"
echo "================================="

# Authenticate
echo ""
echo "1. Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=fresh.user@example.com&password=NewPassword234!')

TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "Authentication failed"
  echo "Response: $AUTH_RESPONSE"
  exit 1
fi

echo "Authentication successful"

# Get settings
echo ""
echo "2. Getting workflow settings..."
GET_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/cameras/usb_camera_0/workflow-settings -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo $GET_RESPONSE | jq '.'

# Update settings
echo ""
echo "3. Updating workflow settings..."
PATCH_RESPONSE=$(curl -s -X PATCH http://localhost:8080/api/v1/cameras/usb_camera_0/workflow-settings -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"auto_face_detection": true, "detection_methods": ["opencv", "dlib"], "confidence_threshold": 0.75, "mvr_quality_threshold": 0.25}')

echo "Response:"
echo $PATCH_RESPONSE | jq '.'

# Verify
echo ""
echo "4. Verifying settings persisted..."
VERIFY_RESPONSE=$(curl -s -X GET http://localhost:8080/api/v1/cameras/usb_camera_0/workflow-settings -H "Authorization: Bearer $TOKEN")

echo "Final settings:"
echo $VERIFY_RESPONSE | jq '.'

AUTO_FACE=$(echo $VERIFY_RESPONSE | jq -r '.auto_face_detection')
METHODS=$(echo $VERIFY_RESPONSE | jq -r '.detection_methods | length')

if [ "$AUTO_FACE" = "true" ] && [ "$METHODS" = "2" ]; then
  echo ""
  echo "All tests passed!"
else
  echo ""
  echo "Some values don't match"
fi

echo ""
echo "Testing complete"
