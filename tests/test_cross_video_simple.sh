#!/bin/bash
# Simple Cross-Video Tracking Test
# No loops, just trigger and check once

set -e

echo "🔐 Authenticating..."
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Got token"
echo ""

echo "📹 Triggering cross-video tracking for 7 videos..."
RESPONSE=$(curl -s -X POST 'http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-11-20T11:09:00",
    "end_time": "2025-11-20T11:14:00",
    "video_uuids": [
      "6bc25594-fe00-49bc-b3ad-c382b6d580b0",
      "51e086d4-e352-4197-a6a6-8d4a96842c91",
      "4cc71fa5-a172-4160-8a4e-3bef97e7d73b",
      "3bc7eb19-f972-4546-8ec3-acbb01444079",
      "886f98e4-5d0b-4de0-81b0-a9587256f60b",
      "1609ade4-26cf-4848-98d2-9a9f926ecde0",
      "8a67e183-0203-42a2-bb25-774a97000471"
    ],
    "background_processing": true,
    "force_reprocess": false
  }')

echo "📊 Response:"
echo "$RESPONSE" | python3 -m json.tool

SESSION_UUID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('session_uuid', 'ERROR'))" 2>/dev/null || echo "ERROR")

if [ "$SESSION_UUID" != "ERROR" ]; then
    echo ""
    echo "✅ Session created: $SESSION_UUID"
    echo ""
    echo "To check status, run:"
    echo "  curl -s \"http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID\" -H \"Authorization: Bearer $TOKEN\" | python3 -m json.tool"
else
    echo "❌ Failed to create session"
fi
