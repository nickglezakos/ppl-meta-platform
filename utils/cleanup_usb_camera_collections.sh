#!/bin/bash
#
# Clean up duplicate usb_camera_0 collections - keep only the specified one
#

MEDIA_SERVICE_URL="http://localhost:8000"
KEEP_UUID="76241fb0-fc86-4859-b442-f7f2979a5c53"  # usb_camera_0 Collection to keep

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
echo "🔍 Fetching all collections..."

# Get all collections (not excluding camera collections)
RESPONSE=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" \
    "$MEDIA_SERVICE_URL/api/v1/media/collections?limit=5000")

echo "📋 Processing collections..."

# Parse and filter collections
echo "$RESPONSE" | python3 -c "
import sys, json

keep_uuid = '$KEEP_UUID'

data = json.load(sys.stdin)

# Filter for usb_camera_0 collections
usb_collections = [
    c for c in data 
    if 'usb_camera_0' in c.get('name', '').lower()
]

print(f'TOTAL: {len(usb_collections)}')

# Find the one to keep
keep_coll = next((c for c in usb_collections if c.get('uuid') == keep_uuid), None)

if keep_coll:
    print(f\"KEEP: {keep_coll['uuid']}|{keep_coll['name']}|{keep_coll.get('created_at', 'N/A')}\")
else:
    print(f'WARNING: Keep UUID {keep_uuid} not found!')

# List all others for deletion
for coll in usb_collections:
    if coll.get('uuid') != keep_uuid:
        print(f\"DELETE: {coll['uuid']}|{coll['name']}|{coll.get('created_at', 'N/A')}\")
" > /tmp/collection_parsing.txt

# Read the parsed results
COLLECTIONS=$(cat /tmp/collection_parsing.txt)

# Parse the output
TOTAL=$(echo "$COLLECTIONS" | grep "^TOTAL:" | cut -d: -f2 | tr -d ' ')
KEEP_LINE=$(echo "$COLLECTIONS" | grep "^KEEP:")
DELETE_LINES=$(echo "$COLLECTIONS" | grep "^DELETE:")

if [ -z "$TOTAL" ] || [ "$TOTAL" = "0" ]; then
    echo "❌ No usb_camera_0 collections found"
    exit 1
fi

echo "📋 Found $TOTAL usb_camera_0 collections"
echo ""

if [ -n "$KEEP_LINE" ]; then
    KEEP_UUID_FOUND=$(echo "$KEEP_LINE" | cut -d'|' -f1 | cut -d: -f2 | tr -d ' ')
    KEEP_NAME=$(echo "$KEEP_LINE" | cut -d'|' -f2)
    KEEP_DATE=$(echo "$KEEP_LINE" | cut -d'|' -f3)
    
    echo "📌 Keeping collection:"
    echo "   Name: $KEEP_NAME"
    echo "   UUID: $KEEP_UUID_FOUND"
    echo "   Created: $KEEP_DATE"
else
    echo "⚠️  Warning: The collection to keep (UUID: $KEEP_UUID) was not found!"
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

# Process each DELETE line
while IFS= read -r line; do
    # Skip empty lines
    [ -z "$line" ] && continue
    
    # Extract UUID (first field after "DELETE: ")
    UUID=$(echo "$line" | cut -d'|' -f1 | cut -d':' -f2 | tr -d ' ')
    # Extract name (second field)
    NAME=$(echo "$line" | cut -d'|' -f2)
    
    echo "🗑️  Deleting: $NAME (UUID: $UUID)"
    
    HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null \
        -X DELETE \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        "$MEDIA_SERVICE_URL/api/v1/media/collections/$UUID")
    
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
        echo "   ✅ Deleted successfully"
        DELETED=$((DELETED + 1))
    elif [ "$HTTP_CODE" = "401" ]; then
        echo "   ⏳ Token expired - refreshing..."
        LOGIN_RESPONSE=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
          -H 'Content-Type: application/x-www-form-urlencoded' \
          -d 'username=fresh.user@example.com&password=NewPassword234!')
        AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
        if [ -z "$AUTH_TOKEN" ]; then
            echo "   ❌ Failed to refresh auth token!"
            FAILED=$((FAILED + 1))
            continue
        fi
        echo "   ✅ Token refreshed, retrying deletion..."
        sleep 2
        # Retry with new token
        HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null \
            -X DELETE \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            "$MEDIA_SERVICE_URL/api/v1/media/collections/$UUID")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
            echo "   ✅ Deleted successfully (after token refresh)"
            DELETED=$((DELETED + 1))
        else
            echo "   ❌ Failed after retry (HTTP $HTTP_CODE)"
            FAILED=$((FAILED + 1))
        fi
    elif [ "$HTTP_CODE" = "429" ]; then
        echo "   ⏳ Rate limited - waiting 5 seconds..."
        sleep 5
        # Retry once
        HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null \
            -X DELETE \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            "$MEDIA_SERVICE_URL/api/v1/media/collections/$UUID")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
            echo "   ✅ Deleted successfully (after rate limit)"
            DELETED=$((DELETED + 1))
        else
            echo "   ❌ Failed after retry (HTTP $HTTP_CODE)"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "   ❌ Failed (HTTP $HTTP_CODE)"
        FAILED=$((FAILED + 1))
    fi
    
    # Delay between deletions to avoid rate limiting (200ms = 5 per second)
    sleep 0.2
done <<< "$DELETE_LINES"

echo ""
echo "✅ Cleanup complete!"
echo "   Deleted: $DELETED"
echo "   Failed: $FAILED"
echo "   Kept: 1 (UUID: $KEEP_UUID)"
