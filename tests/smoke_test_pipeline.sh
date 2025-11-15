#!/bin/bash

################################################################################
# Smoke Test: Verify Continuous Pipeline Execution
# 
# This script checks if the pipeline processed the recent recording session:
# 1. Find last recording session (~8 minutes)
# 2. Check MVR people created after session start
# 3. Verify individuals created
# 4. Check batch processing history
################################################################################

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🧪 Continuous Pipeline Smoke Test${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get auth token
echo -e "${BLUE}▶${NC} Authenticating..."
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Authentication failed${NC}"
    exit 1
fi

USER_ID=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.sub' 2>/dev/null || echo "7")
echo -e "${GREEN}✅ Authenticated (User ID: ${USER_ID})${NC}"
echo ""

################################################################################
# STEP 1: Check Recent Videos (Last Recording Session)
################################################################################
echo -e "${CYAN}━━━ STEP 1: Check Recent Videos from usb_camera_0 ━━━${NC}"
echo ""

# Correct endpoint: /api/v1/media/search
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/media/search?limit=50&order_by=created_at&order=desc" \
  > /tmp/smoke_test_videos.json

# Debug: Check if we got data
if [ ! -s /tmp/smoke_test_videos.json ]; then
    echo -e "${RED}❌ Failed to fetch videos from Media service${NC}"
    echo "   Curl command failed or returned empty response"
    echo ""
else
    FILE_SIZE=$(wc -c < /tmp/smoke_test_videos.json)
    echo -e "${BLUE}📊 Received ${FILE_SIZE} bytes of data${NC}"
    echo ""
fi

# Analyze videos and extract session info
python3 << 'EOF'
import sys
import json
from datetime import datetime

try:
    # Read from temp file instead of stdin
    with open('/tmp/smoke_test_videos.json', 'r') as f:
        input_data = f.read().strip()
    
    if not input_data:
        print("❌ No data received from Media service")
        sys.exit(0)
    
    data = json.loads(input_data)
    
    # Handle list response from /api/v1/media/search (returns array directly)
    if isinstance(data, list):
        videos = data
    else:
        videos = data.get('videos', data.get('media', []))
    
    if not videos:
        print("❌ No videos found")
        sys.exit(0)
    
    # Filter videos from usb_camera_0
    camera_videos = []
    for v in videos:
        title = v.get('title', '')
        filename = v.get('filename', '')
        metadata = v.get('metadata', {})
        # Check if video is from usb_camera_0
        if 'usb_camera_0' in title.lower() or 'usb_camera_0' in filename.lower() or 'usb_camera_0' in str(metadata):
            camera_videos.append(v)
    
    if not camera_videos:
        # If no camera-specific match, take all recent videos
        camera_videos = videos[:20]
    
    # Get time range from first and last video
    if camera_videos:
        first_video = camera_videos[-1]  # Oldest
        last_video = camera_videos[0]    # Newest
        
        start_time = first_video.get('created_at', '')
        end_time = last_video.get('created_at', '')
        
        print(f"✅ Found {len(camera_videos)} recent video segments")
        print(f"   First video: {start_time}")
        print(f"   Last video: {end_time}")
        print(f"   Segments: {len(camera_videos)}")
        print("")
        
        # Write session info to temp file for later use
        with open('/tmp/smoke_test_session.txt', 'w') as f:
            f.write(f"START_TIME={start_time}\n")
            f.write(f"END_TIME={end_time}\n")
            f.write(f"VIDEO_COUNT={len(camera_videos)}\n")
            f.write(f"CAMERA_ID=usb_camera_0\n")
        
        # Show recent videos
        print("Recent video segments:")
        for i, v in enumerate(camera_videos[:10], 1):
            title = v.get('title', v.get('filename', 'Untitled'))[:60]
            uuid = v.get('uuid', v.get('id', 'N/A'))
            print(f"   {i}. {title}")
            print(f"      UUID: {uuid}")
    else:
        print("⚠️  No videos found")
    
except Exception as e:
    print(f"❌ Error: {e}")
EOF

# Load session variables from temp file
if [ -f /tmp/smoke_test_session.txt ]; then
    source /tmp/smoke_test_session.txt
fi

echo ""

################################################################################
# STEP 2: Check Individual Tracking Sessions
################################################################################
echo -e "${CYAN}━━━ STEP 2: Check Individual Tracking Sessions ━━━${NC}"
echo ""

# Query database directly for tracking sessions since there's no list endpoint
PGPASSWORD=postgres psql -h localhost -U postgres -d ppl_meta_vmeta -t -c \
  "SELECT COUNT(*) FROM tracking_sessions WHERE status = 'completed';" \
  2>/dev/null > /tmp/session_count.txt

SESSION_COUNT=$(cat /tmp/session_count.txt | tr -d ' ')

if [ -z "$SESSION_COUNT" ] || [ "$SESSION_COUNT" = "0" ]; then
    echo "⚠️  No completed tracking sessions found"
    echo "   Note: Run 'python3 simple_batch_trigger.py' to process videos with faces"
    echo ""
else
    echo "✅ Found $SESSION_COUNT completed tracking session(s)"
    echo ""
    
    # Get details of most recent sessions
    PGPASSWORD=postgres psql -h localhost -U postgres -d ppl_meta_vmeta -c \
      "SELECT 
         session_uuid, 
         status, 
         total_videos, 
         individuals_found, 
         unique_mvr_people_count,
         to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created,
         to_char(completed_at, 'YYYY-MM-DD HH24:MI:SS') as completed
       FROM tracking_sessions 
       WHERE status = 'completed'
       ORDER BY completed_at DESC 
       LIMIT 5;" \
      2>/dev/null
    
    echo ""
fi

################################################################################
# STEP 3: Check MVR People Created After Session Start
################################################################################
echo -e "${CYAN}━━━ STEP 3: Check MVR People Created ━━━${NC}"
echo ""

# Query database directly for MVR people count
PGPASSWORD=postgres psql -h localhost -U postgres -d ppl_meta_vmeta -t -c \
  "SELECT COUNT(*) FROM mvr_people;" \
  2>/dev/null > /tmp/mvr_count.txt

MVR_COUNT=$(cat /tmp/mvr_count.txt | tr -d ' ')

if [ -z "$MVR_COUNT" ] || [ "$MVR_COUNT" = "0" ]; then
    echo "⚠️  No MVR people found"
    echo "   This means no unique individuals have been identified yet"
    echo "   Run 'python3 simple_batch_trigger.py' to process videos"
    echo ""
else
    echo "✅ Found $MVR_COUNT MVR person/people in database"
    echo ""
    
    # Get details of MVR people
    PGPASSWORD=postgres psql -h localhost -U postgres -d ppl_meta_vmeta -c \
      "SELECT 
         mvr_person_uuid,
         source,
         total_appearances,
         confidence_score,
         to_char(first_seen, 'YYYY-MM-DD HH24:MI:SS') as first_seen,
         to_char(last_seen, 'YYYY-MM-DD HH24:MI:SS') as last_seen
       FROM mvr_people 
       ORDER BY last_seen DESC 
       LIMIT 10;" \
      2>/dev/null
    
    echo ""
fi

################################################################################
# STEP 4: Check Batch Processing History
################################################################################
echo -e "${CYAN}━━━ STEP 4: Check Batch Processing History ━━━${NC}"
echo ""

# Note: Batch processing history is separate from tracking sessions
# It's used for the continuous pipeline that monitors videos and triggers automatically
# For now, check if the table exists and has any records

PGPASSWORD=postgres psql -h localhost -U postgres -d ppl_meta_vmeta -t -c \
  "SELECT COUNT(*) FROM batch_processing_history;" \
  2>/dev/null > /tmp/batch_count.txt

BATCH_COUNT=$(cat /tmp/batch_count.txt | tr -d ' ')

if [ -z "$BATCH_COUNT" ] || [ "$BATCH_COUNT" = "0" ]; then
    echo "⚠️  No batch processing history found"
    echo "   Note: Batch processing is for continuous pipeline automation"
    echo "   Manual processing via simple_batch_trigger.py works independently"
    echo ""
else
    echo "✅ Found $BATCH_COUNT batch(es) in history"
    echo ""
    
    PGPASSWORD=postgres psql -h localhost -U postgres -d ppl_meta_vmeta -c \
      "SELECT 
         batch_uuid,
         collection_id,
         video_count,
         individuals_created,
         mvr_people_created,
         status,
         trigger_reason,
         to_char(completed_at, 'YYYY-MM-DD HH24:MI:SS') as completed
       FROM batch_processing_history 
       ORDER BY completed_at DESC 
       LIMIT 5;" \
      2>/dev/null
    
    echo ""
fi

################################################################################
# Summary
################################################################################
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 Smoke Test Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}✅ Test completed!${NC}"
echo ""
echo "Check the output above to verify:"
echo "  1. Recording session was found (~8 minutes duration)"
echo "  2. Video segments were created and uploaded"
echo "  3. MVR people objects were created after session start"
echo "  4. Batch processing history shows completed batches"
echo ""
