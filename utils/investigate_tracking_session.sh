#!/bin/bash

# Investigation Script: Tracking Session 843e7d29-36fc-4542-9fc5-194a7a1fbc11
# Date: November 16, 2025
# Purpose: Find the individual and MVR person created, trace back to videos

# Authenticate
echo "=== Authenticating ==="
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtained: ${TOKEN:0:30}..."
echo ""

# Our 8 video UUIDs from the recording
OUR_VIDEOS=(
  "8c77cf47-1db0-4b91-ab86-2f873307c52d"
  "52fa4969-cfe5-4252-9c87-10745b675c15"
  "cc62d890-cc0c-4738-ae37-ae06783de1d1"
  "5066a8c3-de30-46e7-9e5d-8d7352947181"
  "8135343f-c0cd-47a4-9ccb-a1441e355d95"
  "42b39201-e0dd-41d9-a195-cfa330df9f86"
  "9bbbff74-0286-470a-ad02-3b7b079d1f81"
  "011fb0dd-a27c-4c7c-a47d-2761361b8fd7"
)

echo "=== Investigation Report: Tracking Session 843e7d29 ==="
echo ""
echo "Session Details:"
echo "  UUID: 843e7d29-36fc-4542-9fc5-194a7a1fbc11"
echo "  Created: 2025-11-16 14:19:49"
echo "  Completed: 2025-11-16 14:19:49.199299 (0.17 seconds)"
echo "  Result: 1 individual, 1 MVR person"
echo "  Videos processed: 8"
echo ""

# Step 1: Search for MVR people created on Nov 16
echo "=== Step 1: Searching for MVR People on Nov 16, 2025 ==="
echo ""

curl -s -X POST "http://localhost:8008/api/v1/mvr-people/search/by-collection" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "usb_camera_0",
    "start_time": "2025-11-16T00:00:00",
    "end_time": "2025-11-16T23:59:59",
    "limit": 500
  }' > /tmp/mvr_search_results.json

python3 << 'EOF'
import json

# Load results
with open('/tmp/mvr_search_results.json') as f:
    data = json.load(f)

total = data.get('total_results', 0)
print(f"Total MVR people found: {total}")
print("")

# Our 8 video UUIDs
our_videos = {
    "8c77cf47-1db0-4b91-ab86-2f873307c52d": "segment_001",
    "52fa4969-cfe5-4252-9c87-10745b675c15": "segment_002",
    "cc62d890-cc0c-4738-ae37-ae06783de1d1": "segment_003",
    "5066a8c3-de30-46e7-9e5d-8d7352947181": "segment_004",
    "8135343f-c0cd-47a4-9ccb-a1441e355d95": "segment_005",
    "42b39201-e0dd-41d9-a195-cfa330df9f86": "segment_006",
    "9bbbff74-0286-470a-ad02-3b7b079d1f81": "segment_007",
    "011fb0dd-a27c-4c7c-a47d-2761361b8fd7": "segment_008"
}

if total == 0:
    print("❌ NO MVR PEOPLE FOUND!")
    print("")
    print("This confirms the issue:")
    print("  - Tracking session reported creating 1 MVR person")
    print("  - But the MVR person was NOT persisted to the database")
    print("  - Or the search endpoint is broken (doesn't actually filter by collection)")
    print("")
    print("The search endpoint query on line 1715-1738 of mvr_people.py:")
    print("  SELECT * FROM mvr_people WHERE created_at >= $1 AND created_at <= $2")
    print("  This query does NOT filter by collection at all!")
    print("  It only filters by created_at timestamp")
    print("")
    print("Recommendation: Search without collection filter to find ALL MVR people")
else:
    print(f"✓ Found {total} MVR people")
    print("")
    
    # Check each MVR person
    found_match = False
    for idx, mvr in enumerate(data.get('mvr_people', []), 1):
        mvr_uuid = mvr['mvr_people_uuid']
        individual_uuids = mvr['individual_uuids']
        appearances = mvr.get('appearances', [])
        
        # Check if any appearances match our videos
        matching_videos = []
        for app in appearances:
            video_uuid = app['video_uuid']
            if video_uuid in our_videos:
                matching_videos.append({
                    'uuid': video_uuid,
                    'name': our_videos[video_uuid],
                    'timestamp': f"{app['start_timestamp']} - {app['end_timestamp']}"
                })
        
        if matching_videos:
            found_match = True
            print(f"✅ MATCH FOUND! MVR Person #{idx}")
            print(f"   MVR UUID: {mvr_uuid}")
            print(f"   Individual UUIDs: {individual_uuids}")
            print(f"   Total Appearances: {mvr['total_appearances']} across {mvr['unique_videos']} videos")
            print(f"   Confidence: {mvr['confidence_score']}, Quality: {mvr['quality_score']}")
            print(f"   First Seen: {mvr['first_seen']}")
            print(f"   Last Seen: {mvr['last_seen']}")
            print(f"   Age: {mvr.get('estimated_age', 'N/A')}, Gender: {mvr.get('estimated_gender', 'N/A')}")
            print("")
            print(f"   Appearances in OUR 8 videos ({len(matching_videos)} videos):")
            for v in matching_videos:
                print(f"     - {v['name']} ({v['uuid'][:8]}) at {v['timestamp']}")
            print("")
        else:
            print(f"MVR Person #{idx}: {mvr_uuid} - Does NOT match our videos")
    
    if not found_match:
        print("")
        print("❌ NO MATCHES FOUND!")
        print("None of the MVR people have appearances in our 8 videos")

EOF

echo ""
echo "=== Step 2: Health Check - Total MVR People Count ==="
curl -s http://localhost:8008/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Total MVR people in database: {data['mvr_people']['statistics']['total_mvr_people']}\")"

echo ""
echo "=== Investigation Complete ==="
echo "Results saved to /tmp/mvr_search_results.json"
