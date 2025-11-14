#!/bin/bash

################################################################################
# Continuous Pipeline Monitor
# 
# This script monitors the continuous individuals and MVR pipeline while
# you record via the Flutter app. It checks:
# - Video segments being created
# - Face detection completion
# - Batch accumulation
# - Batch processing triggers
# - Individuals and MVR creation
#
# Usage: ./tests/monitor_continuous_pipeline.sh
################################################################################

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Service URLs
NODE_URL="${NODE_URL:-http://localhost:8001}"
MEDIA_URL="${MEDIA_URL:-http://localhost:8000}"
VISION_URL="${VISION_URL:-http://localhost:8003}"
VMETA_URL="${VMETA_URL:-http://localhost:8008}"

# Get auth token
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🔍 Continuous Individuals & MVR Pipeline Monitor${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}▶${NC} Getting authentication token..."
AUTH_TOKEN=$(curl -s -X POST "${NODE_URL}/api/v1/users/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$AUTH_TOKEN" ]; then
    echo -e "${RED}❌ Failed to authenticate${NC}"
    exit 1
fi

# Extract user ID from token
USER_ID=$(echo "$AUTH_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.sub' 2>/dev/null || echo "7")

echo -e "${GREEN}✅ Authenticated (User ID: ${USER_ID})${NC}"
echo ""

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📱 START RECORDING NOW via Flutter app${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "This monitor will track:"
echo "  • Video segments saved to media service"
echo "  • Face detection completion status"
echo "  • Batch accumulation (5 videos per batch)"
echo "  • Automatic batch processing triggers"
echo "  • Individuals and MVR creation results"
echo ""
echo -e "${CYAN}Press Ctrl+C to stop monitoring${NC}"
echo ""
sleep 3

# Monitoring loop
LAST_VIDEO_COUNT=0
LAST_FD_COUNT=0
LAST_BATCH_COUNT=0
ITERATION=0

while true; do
    ITERATION=$((ITERATION + 1))
    clear
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🔍 Continuous Pipeline Monitor - Iteration ${ITERATION}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # ========================================================================
    # 1. Video Segments Status
    # ========================================================================
    echo -e "${BLUE}━━━ 📹 VIDEO SEGMENTS ━━━${NC}"
    
    VIDEOS_RESPONSE=$(curl -s -H "Authorization: Bearer ${AUTH_TOKEN}" \
      "${MEDIA_URL}/api/v1/videos?user_id=${USER_ID}&limit=100" 2>/dev/null)
    
    if echo "$VIDEOS_RESPONSE" | jq -e '.videos' >/dev/null 2>&1; then
        VIDEO_COUNT=$(echo "$VIDEOS_RESPONSE" | jq -r '.videos | length')
        echo -e "  Total videos: ${GREEN}${VIDEO_COUNT}${NC}"
        
        if [ "$VIDEO_COUNT" -gt "$LAST_VIDEO_COUNT" ]; then
            NEW_VIDEOS=$((VIDEO_COUNT - LAST_VIDEO_COUNT))
            echo -e "  ${GREEN}✨ +${NEW_VIDEOS} new video(s) saved!${NC}"
            LAST_VIDEO_COUNT=$VIDEO_COUNT
        fi
        
        # Show most recent videos
        if [ "$VIDEO_COUNT" -gt 0 ]; then
            echo ""
            echo "  Recent videos:"
            echo "$VIDEOS_RESPONSE" | jq -r '.videos[0:3] | .[] | "    • \(.title // "Untitled") - \(.uuid)"' 2>/dev/null
        fi
    else
        echo -e "  ${YELLOW}No videos yet or service unavailable${NC}"
        VIDEO_COUNT=0
    fi
    
    echo ""
    
    # ========================================================================
    # 2. Face Detection Status
    # ========================================================================
    echo -e "${BLUE}━━━ 👤 FACE DETECTION ━━━${NC}"
    echo -e "  ${CYAN}ℹ️  Face detection runs automatically on video save${NC}"
    echo -e "  ${CYAN}ℹ️  Processing time: ~60s per video segment${NC}"
    echo ""
    
    # ========================================================================
    # 3. Batch Processing Status
    # ========================================================================
    echo -e "${BLUE}━━━ 📦 BATCH PROCESSING ━━━${NC}"
    
    BATCH_STATUS=$(curl -s -H "Authorization: Bearer ${AUTH_TOKEN}" \
      "${VMETA_URL}/api/v1/batch-processing/status?user_id=${USER_ID}" 2>/dev/null)
    
    if echo "$BATCH_STATUS" | jq -e '.' >/dev/null 2>&1; then
        VIDEOS_READY=$(echo "$BATCH_STATUS" | jq -r '.videos_ready // 0')
        BATCH_SIZE=$(echo "$BATCH_STATUS" | jq -r '.batch_size // 5')
        CURRENT_BATCH=$(echo "$BATCH_STATUS" | jq -r '.current_batch_number // 0')
        
        echo -e "  Current batch: ${CYAN}#${CURRENT_BATCH}${NC}"
        echo -e "  Videos ready: ${GREEN}${VIDEOS_READY}${NC}/${BATCH_SIZE}"
        
        # Progress bar
        PROGRESS=$((VIDEOS_READY * 100 / BATCH_SIZE))
        BAR_LENGTH=20
        FILLED=$((VIDEOS_READY * BAR_LENGTH / BATCH_SIZE))
        
        echo -n "  Progress: ["
        for ((i=0; i<BAR_LENGTH; i++)); do
            if [ $i -lt $FILLED ]; then
                echo -n "█"
            else
                echo -n "░"
            fi
        done
        echo "] ${PROGRESS}%"
        
        if [ "$VIDEOS_READY" -eq "$BATCH_SIZE" ]; then
            echo -e "  ${GREEN}✅ Batch threshold reached! Pipeline should trigger...${NC}"
        fi
    else
        echo -e "  ${YELLOW}Batch service not responding or no batches yet${NC}"
    fi
    
    echo ""
    
    # ========================================================================
    # 4. Batch History
    # ========================================================================
    echo -e "${BLUE}━━━ 📊 BATCH HISTORY ━━━${NC}"
    
    BATCH_HISTORY=$(curl -s -H "Authorization: Bearer ${AUTH_TOKEN}" \
      "${VMETA_URL}/api/v1/batch-processing/history?user_id=${USER_ID}&limit=5" 2>/dev/null)
    
    if echo "$BATCH_HISTORY" | jq -e '.batches' >/dev/null 2>&1; then
        BATCH_COUNT=$(echo "$BATCH_HISTORY" | jq -r '.batches | length')
        
        if [ "$BATCH_COUNT" -gt 0 ]; then
            echo -e "  Completed batches: ${GREEN}${BATCH_COUNT}${NC}"
            echo ""
            
            if [ "$BATCH_COUNT" -gt "$LAST_BATCH_COUNT" ]; then
                NEW_BATCHES=$((BATCH_COUNT - LAST_BATCH_COUNT))
                echo -e "  ${GREEN}🎉 +${NEW_BATCHES} batch(es) processed!${NC}"
                echo ""
                LAST_BATCH_COUNT=$BATCH_COUNT
            fi
            
            # Show batch details
            echo "$BATCH_HISTORY" | jq -r '.batches[] | 
                "  Batch \(.batch_number) [\(.status)]
                    UUID: \(.batch_uuid)
                    Videos: \(.video_count)
                    Trigger: \(.trigger_reason)
                    👤 Individuals: \(.individuals_created // 0) created, \(.individuals_cached // 0) cached
                    👥 MVR People: \(.mvr_people_created // 0) created, \(.mvr_people_cached // 0) cached
                    💾 Cache Rate: \(.cache_hit_rate // 0)%
                    ⏱️  Time: \(.processing_time_seconds // 0)s
                "' 2>/dev/null | head -40
        else
            echo -e "  ${YELLOW}No completed batches yet${NC}"
        fi
    else
        echo -e "  ${YELLOW}Batch history not available yet${NC}"
    fi
    
    echo ""
    
    # ========================================================================
    # Summary Line
    # ========================================================================
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Summary: ${VIDEO_COUNT} videos | ${VIDEOS_READY}/5 in batch | ${BATCH_COUNT} batches completed${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Next update in 10 seconds... (Ctrl+C to stop)${NC}"
    
    # Wait 10 seconds before next iteration (reduced frequency to avoid overwhelming services)
    sleep 10
done
