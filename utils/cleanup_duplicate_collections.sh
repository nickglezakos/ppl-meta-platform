#!/bin/bash
#
# Clean up duplicate camera collections - keep only the oldest one
#

MEDIA_SERVICE_URL="http://localhost:8000"
CAMERA_ID="usb_camera_0"

echo "🔑 Getting fresh auth token..."
echo ""

# Login to get auth token
LOGIN_RESPONSE=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!')

# Extract access_token from JSON response
AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$AUTH_TOKEN" ]; then
    echo "❌ Failed to get auth token"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Auth token obtained"

echo ""
echo "🔍 Fetching all collections for $CAMERA_ID..."
echo "=" | tr '=' '=' | head -c 60; echo ""

# Get all collections
RESPONSE=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
    "$MEDIA_SERVICE_URL/api/v1/media/search?collection_id=$CAMERA_ID&page_size=5000&order_by=created_at&order=asc")

# Extract collection UUIDs and created_at dates
COLLECTIONS=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    
    # Extract unique collections
    seen = {}
    for item in items:
        coll = item.get('collection')
        if coll:
            uuid = coll.get('uuid')
            name = coll.get('name', '')
            created = coll.get('created_at', '')
            
            if '$CAMERA_ID' in name and uuid not in seen:
                seen[uuid] = {'uuid': uuid, 'name': name, 'created_at': created}
    
    # Sort by created_at
    collections = sorted(seen.values(), key=lambda x: x['created_at'])
    
    print(f'TOTAL: {len(collections)}')
    
    if collections:
        oldest = collections[0]
        print(f'KEEP: {oldest[\"uuid\"]}|{oldest[\"name\"]}|{oldest[\"created_at\"]}')
        
        for coll in collections[1:]:
            print(f'DELETE: {coll[\"uuid\"]}|{coll[\"name\"]}|{coll[\"created_at\"]}')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

# Parse the output
TOTAL=$(echo "$COLLECTIONS" | grep "^TOTAL:" | cut -d: -f2 | tr -d ' ')
KEEP_LINE=$(echo "$COLLECTIONS" | grep "^KEEP:")
DELETE_LINES=$(echo "$COLLECTIONS" | grep "^DELETE:")

if [ -z "$TOTAL" ] || [ "$TOTAL" = "0" ]; then
    echo "❌ No collections found"
    exit 1
fi

echo "📋 Found $TOTAL collections"
echo ""

if [ -n "$KEEP_LINE" ]; then
    KEEP_UUID=$(echo "$KEEP_LINE" | cut -d'|' -f1 | cut -d: -f2 | tr -d ' ')
    KEEP_NAME=$(echo "$KEEP_LINE" | cut -d'|' -f2)
    KEEP_DATE=$(echo "$KEEP_LINE" | cut -d'|' -f3)
    
    echo "📌 Keeping OLDEST collection:"
    echo "   Name: $KEEP_NAME"
    echo "   UUID: $KEEP_UUID"
    echo "   Created: $KEEP_DATE"
fi

DELETE_COUNT=$(echo "$DELETE_LINES" | wc -l | tr -d ' ')

if [ -z "$DELETE_LINES" ] || [ "$DELETE_COUNT" = "0" ]; then
    echo ""
    echo "✅ No duplicates to delete!"
    exit 0
fi

echo ""
echo "🗑️  Will delete $DELETE_COUNT duplicate collections"
echo ""
read -p "⚠️  Delete $DELETE_COUNT collections? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "🔄 Deleting duplicates..."

DELETED=0
FAILED=0

while IFS='|' read -r PREFIX UUID NAME CREATED; do
    if [ "$PREFIX" = "DELETE:" ]; then
        UUID=$(echo "$UUID" | tr -d ' ')
        echo "🗑️  Deleting: $NAME (UUID: $UUID)"
        
        HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null \
            -X DELETE \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            "$MEDIA_SERVICE_URL/api/v1/media/collections/$UUID")
        
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
            echo "   ✅ Deleted successfully"
            DELETED=$((DELETED + 1))
        else
            echo "   ❌ Failed (HTTP $HTTP_CODE)"
            FAILED=$((FAILED + 1))
        fi
    fi
done <<< "$DELETE_LINES"

echo ""
echo "✅ Cleanup complete!"
echo "   Deleted: $DELETED"
echo "   Failed: $FAILED"
echo "   Kept: 1 (oldest)"
