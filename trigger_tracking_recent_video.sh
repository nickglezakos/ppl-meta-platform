#!/bin/bash

echo "🔍 Triggering Cross-Video Tracking for Recent Recording"
echo "========================================================="

VIDEO_UUID="766e9609-0ce4-43f9-bd75-0bd8eefe4d41"

# Get auth token
echo ""
echo "1️⃣ Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!')

TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Authentication failed"
  echo "Response: $AUTH_RESPONSE"
  exit 1
fi

echo "✅ Authentication successful"

# Trigger cross-video tracking
echo ""
echo "2️⃣ Triggering cross-video tracking for video $VIDEO_UUID..."
TRACKING_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/v1/vmeta/cross-video-tracking/simple" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"video_uuids\": [\"$VIDEO_UUID\"],
    \"use_cache\": false,
    \"enable_mvr_creation\": true
  }")

echo ""
echo "Response:"
echo $TRACKING_RESPONSE | jq '.'

# Check session status
SESSION_UUID=$(echo $TRACKING_RESPONSE | jq -r '.session_uuid')

if [ "$SESSION_UUID" != "null" ] && [ -n "$SESSION_UUID" ]; then
  echo ""
  echo "3️⃣ Checking session status..."
  sleep 5
  
  STATUS_RESPONSE=$(curl -s -X GET "http://localhost:8080/api/v1/vmeta/cross-video-tracking/sessions/$SESSION_UUID" \
    -H "Authorization: Bearer $TOKEN")
  
  echo ""
  echo "Session Status:"
  echo $STATUS_RESPONSE | jq '.'
fi

echo ""
echo "========================================================="
echo "Done! Check the vmeta logs and database for results."
