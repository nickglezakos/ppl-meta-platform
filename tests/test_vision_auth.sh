#!/bin/bash
# Quick test for Vision service authentication

echo "Testing Vision service with internal service token..."
echo ""

INTERNAL_TOKEN="ppl-meta-internal-service-secret-key-change-in-production"
TEST_VIDEO_UUID="d5fc47ef-ec7c-48fc-a53a-ab3a0ae8e6fb"

echo "Calling Vision service bulk-process endpoint..."
response=$(curl -s -w "\n%{http_code}" \
  "http://localhost:8003/faces/media/$TEST_VIDEO_UUID/bulk-process?force_process=true&frame_interval=10" \
  -X POST \
  -H "Authorization: Bearer $INTERNAL_TOKEN" \
  -H "X-Service-Name: test-script" \
  -H "Content-Type: application/json")

http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | sed '$d')

echo "HTTP Status: $http_code"
echo ""

if [ "$http_code" = "200" ]; then
    echo "✅ SUCCESS! Vision service accepted internal service token"
    echo ""
    echo "Response:"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
else
    echo "❌ FAILED with status $http_code"
    echo ""
    echo "Response:"
    echo "$body"
fi

echo ""
echo "Now testing full Enhanced Logic V2 flow..."
echo ""

./test_service_auth.sh
