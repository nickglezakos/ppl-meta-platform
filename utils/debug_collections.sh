#!/bin/bash
#
# Debug version - shows what's being parsed
#

MEDIA_SERVICE_URL="http://localhost:8000"
KEEP_UUID="76241fb0-fc86-4859-b442-f7f2979a5c53"

echo "🔑 Getting fresh auth token..."
LOGIN_RESPONSE=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!')

AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$AUTH_TOKEN" ]; then
    echo "❌ Failed to get auth token"
    exit 1
fi

echo "✅ Auth token obtained"
echo ""
echo "🔍 Fetching all collections..."

RESPONSE=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
    "$MEDIA_SERVICE_URL/api/v1/media/collections?limit=5000")

echo "📋 DEBUG: Saving response to /tmp/collections_response.json"
echo "$RESPONSE" > /tmp/collections_response.json

echo "📋 DEBUG: First 500 chars of response:"
echo "$RESPONSE" | head -c 500
echo ""
echo ""

echo "📋 Processing collections with Python..."

# Parse collections
python3 << 'PYEOF'
import json

keep_uuid = '76241fb0-fc86-4859-b442-f7f2979a5c53'

with open('/tmp/collections_response.json', 'r') as f:
    data = json.load(f)

print(f"DEBUG: Total collections in response: {len(data)}")
print(f"DEBUG: Type of data: {type(data)}")

if isinstance(data, list):
    print("DEBUG: Data is a list")
    usb_collections = [
        c for c in data 
        if 'usb_camera_0' in c.get('name', '').lower()
    ]
elif isinstance(data, dict):
    print("DEBUG: Data is a dict")
    print(f"DEBUG: Dict keys: {list(data.keys())[:5]}")
    # Maybe it's wrapped in a response object?
    if 'collections' in data:
        usb_collections = [
            c for c in data['collections']
            if 'usb_camera_0' in c.get('name', '').lower()
        ]
    elif 'items' in data:
        usb_collections = [
            c for c in data['items']
            if 'usb_camera_0' in c.get('name', '').lower()
        ]
    else:
        # Assume top-level is already collections
        usb_collections = [
            c for c in data.values()
            if isinstance(c, dict) and 'usb_camera_0' in c.get('name', '').lower()
        ]
else:
    print(f"DEBUG: Unexpected data type: {type(data)}")
    usb_collections = []

print(f"DEBUG: Found {len(usb_collections)} usb_camera_0 collections")

if usb_collections:
    print("\nDEBUG: First 3 collections:")
    for i, coll in enumerate(usb_collections[:3]):
        print(f"  {i+1}. UUID: {coll.get('uuid')}, Name: {coll.get('name')}")

# Now output in the format the script expects
print(f"\nTOTAL: {len(usb_collections)}")

keep_coll = next((c for c in usb_collections if c.get('uuid') == keep_uuid), None)

if keep_coll:
    print(f"KEEP: {keep_coll['uuid']}|{keep_coll['name']}|{keep_coll.get('created_at', 'N/A')}")
else:
    print(f"WARNING: Keep UUID {keep_uuid} not found!")

for coll in usb_collections:
    if coll.get('uuid') != keep_uuid:
        print(f"DELETE: {coll['uuid']}|{coll['name']}|{coll.get('created_at', 'N/A')}")
PYEOF
