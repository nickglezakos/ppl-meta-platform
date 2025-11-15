#!/bin/bash
# Test VMeta startup state - check if there are pending videos BEFORE recording

echo "🔍 Testing VMeta startup state..."
echo "================================"

# Get auth token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Got auth token"
echo ""

# Check VMeta polling status
echo "📊 VMeta Polling Status:"
curl -s http://localhost:8008/api/v1/recording/status -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo ""
echo "📹 Videos in collection (last 20):"
curl -s "http://localhost:8000/api/v1/media/search?collection_id=usb_camera_0&page_size=20&order_by=created_at&order=desc" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Total: {len(data)} videos'); [print(f'  {v[\"created_at\"][:19]} | {v[\"uuid\"][:8]}') for v in data[:10]]"

echo ""
echo "✅ Test complete. Now start a recording and compare results."
