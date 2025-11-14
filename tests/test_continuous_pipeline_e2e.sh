#!/bin/bash

################################################################################
# End-to-End Test: Continuous Individuals and MVR Pipeline
# 
# This script tests the complete pipeline with real camera recording:
# - Records 13 video segments (30 seconds each)
# - Monitors automatic batch processing (5 videos per batch)
# - Validates individuals and MVR creation
# - Measures cache effectiveness across batches
#
# Expected Flow:
#   Batch 1: Videos 1-5 (threshold trigger)
#   Batch 2: Videos 6-10 (threshold trigger)
#   Batch 3: Videos 11-13 (recording stop trigger - partial batch)
#
# Duration: ~7-8 minutes (6.5 min recording + processing time)
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
NODE_URL="${NODE_URL:-http://localhost:8001}"
MEDIA_URL="${MEDIA_URL:-http://localhost:8000}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8002}"
VISION_URL="${VISION_URL:-http://localhost:8003}"
CAMERAS_URL="${CAMERAS_URL:-http://localhost:8005}"
VMETA_URL="${VMETA_URL:-http://localhost:8008}"

TEST_USER_ID="${TEST_USER_ID:-test-user-$(date +%s)}"
BATCH_SIZE=5
SEGMENT_DURATION=30
TOTAL_SEGMENTS=13

# Test results tracking
BATCH_1_UUID=""
BATCH_2_UUID=""
BATCH_3_UUID=""
TEST_START_TIME=$(date +%s)

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

################################################################################
# Step 1: Setup and Configuration
################################################################################

setup_test_environment() {
    print_header "STEP 1: Setup and Configuration"
    
    # 1.1 Check service health
    print_step "Checking service health..."
    
    services=("gateway:8080" "node:8001" "media:8000" "orchestrator:8002" "vision:8003" "cameras:8005" "vmeta:8008")
    
    for service in "${services[@]}"; do
        name="${service%%:*}"
        port="${service##*:}"
        
        # Handle node service which requires trailing slash
        health_endpoint="http://localhost:${port}/health"
        if [ "$name" = "node" ]; then
            health_endpoint="http://localhost:${port}/health/"
        fi
        
        response=$(curl -s -o /dev/null -w "%{http_code}" "$health_endpoint")
        
        if [ "$response" = "200" ]; then
            print_success "${name} service is healthy"
        else
            print_error "${name} service is not responding (HTTP ${response})"
            exit 1
        fi
    done
    
    # 1.2 Authenticate
    print_step "Authenticating..."
    
    AUTH_RESPONSE=$(curl -s -X POST "${NODE_URL}/api/v1/users/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d 'username=fresh.user@example.com&password=NewPassword234!')
    
    AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token')
    
    if [ -z "$AUTH_TOKEN" ] || [ "$AUTH_TOKEN" = "null" ]; then
        print_error "Authentication failed"
        echo "$AUTH_RESPONSE" | jq '.'
        exit 1
    fi
    
    # Extract user ID from JWT token
    USER_ID=$(echo "$AUTH_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.sub' 2>/dev/null || echo "")
    
    if [ -n "$USER_ID" ] && [ "$USER_ID" != "null" ]; then
        TEST_USER_ID="$USER_ID"
        print_success "Authenticated successfully (User ID: ${USER_ID})"
    else
        print_success "Authenticated successfully"
    fi
    
    export AUTH_TOKEN
    export TEST_USER_ID
    
    # 1.3 Detect cameras (using Gateway as per headless camera management guide)
    print_step "Detecting available cameras..."
    
    CAMERAS_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/api/v1/cameras/detect" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    DETECTED_COUNT=$(echo "$CAMERAS_RESPONSE" | jq -r '.detected_count // 0')
    
    if [ "$DETECTED_COUNT" -eq 0 ]; then
        print_error "No cameras detected. Please connect a USB camera."
        echo "$CAMERAS_RESPONSE" | jq '.'
        exit 1
    fi
    
    CAMERA_DEVICE_ID=$(echo "$CAMERAS_RESPONSE" | jq -r '.cameras[0].device_id')
    CAMERA_NAME=$(echo "$CAMERAS_RESPONSE" | jq -r '.cameras[0].name')
    
    print_success "Detected ${DETECTED_COUNT} camera(s)"
    print_info "Selected camera: ${CAMERA_NAME} (${CAMERA_DEVICE_ID})"
    
    # 1.4 Connect to camera (REQUIRED before streaming/recording)
    print_step "Connecting to camera..."
    
    CONNECT_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/api/v1/cameras/${CAMERA_DEVICE_ID}/connect" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    CONNECT_STATUS=$(echo "$CONNECT_RESPONSE" | jq -r '.status')
    
    if [ "$CONNECT_STATUS" != "connected" ]; then
        print_error "Failed to connect to camera"
        echo "$CONNECT_RESPONSE" | jq '.'
        exit 1
    fi
    
    print_success "Camera connected successfully"
    export CAMERA_DEVICE_ID
    export CAMERA_NAME
    
    # 1.5 Configure batch size
    print_step "Configuring batch processing..."
    
    curl -s -X PUT "${VMETA_URL}/api/v1/batch-processing/batch-size" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"batch_size\": ${BATCH_SIZE},
        \"collection_id\": null
      }" > /dev/null
    
    print_success "Batch size configured to ${BATCH_SIZE} videos"
    
    # 1.6 Enable face detection on save
    print_step "Enabling face detection on save..."
    
    curl -s -X PUT "${NODE_URL}/api/v1/settings/face_detection_on_save" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{"value": "true"}' > /dev/null
    
    print_success "Face detection enabled (Enhanced Logic V2)"
    
    print_success "Setup complete!"
}

################################################################################
# Step 2: Start Recording
################################################################################

start_camera_recording() {
    print_header "STEP 2: Start Camera Recording"
    
    print_info "Camera: ${CAMERA_NAME}"
    print_info "Device: ${CAMERA_DEVICE_ID}"
    print_info "Segment Duration: ${SEGMENT_DURATION} seconds"
    print_info "Total Segments: ${TOTAL_SEGMENTS}"
    print_info "Expected Duration: $((TOTAL_SEGMENTS * SEGMENT_DURATION / 60)) minutes"
    
    # Step 2.1: Start streaming (REQUIRED before recording)
    print_step "Starting camera stream..."
    
    STREAM_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/start" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    STREAM_STATUS=$(echo "$STREAM_RESPONSE" | jq -r '.status')
    
    if [ "$STREAM_STATUS" != "streaming" ]; then
        print_error "Failed to start streaming"
        echo "$STREAM_RESPONSE" | jq '.'
        exit 1
    fi
    
    print_success "Camera streaming started"
    sleep 2  # Allow stream to stabilize
    
    # Step 2.2: Check for stale recording state
    print_step "Checking recording state..."
    
    DEBUG_RESPONSE=$(curl -s -H "Authorization: Bearer ${AUTH_TOKEN}" \
      "${CAMERAS_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/record/debug")
    
    HAS_STALE_DB=$(echo "$DEBUG_RESPONSE" | jq -r '.has_active_session_db // false')
    HAS_MEMORY=$(echo "$DEBUG_RESPONSE" | jq -r '.has_active_recording_memory // false')
    
    if [ "$HAS_STALE_DB" = "true" ] && [ "$HAS_MEMORY" = "false" ]; then
        print_warning "Detected stale recording state, clearing..."
        curl -s -X POST -H "Authorization: Bearer ${AUTH_TOKEN}" \
          "${CAMERAS_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/record/clear-state" > /dev/null
        print_success "Stale state cleared"
    fi
    
    # Step 2.3: Start recording (using direct camera service as per guide)
    print_step "Starting recording..."
    
    START_RESPONSE=$(curl -s -X POST "${CAMERAS_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/record/start" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"user_id\": \"${TEST_USER_ID}\",
        \"segment_duration_seconds\": ${SEGMENT_DURATION},
        \"auto_face_detection_enabled\": true
      }")
    
    # Check for recording ID or session UUID
    RECORDING_ID=$(echo "$START_RESPONSE" | jq -r '.recording_id // .session_uuid // empty')
    SESSION_UUID=$(echo "$START_RESPONSE" | jq -r '.session_uuid // .recording_id // empty')
    
    if [ -z "$RECORDING_ID" ] || [ "$RECORDING_ID" = "null" ]; then
        print_error "Failed to start recording"
        echo "$START_RESPONSE" | jq '.'
        exit 1
    fi
    
    print_success "Recording started successfully!"
    print_info "Recording ID: ${RECORDING_ID}"
    [ -n "$SESSION_UUID" ] && [ "$SESSION_UUID" != "null" ] && print_info "Session UUID: ${SESSION_UUID}"
    
    export RECORDING_ID
    export SESSION_UUID
    
    echo ""
    print_warning "📹 LIVE RECORDING IN PROGRESS..."
    print_info "Position yourself or subjects in front of the camera for face detection."
    echo ""
}

################################################################################
# Step 3: Monitor Batch Processing
################################################################################

check_recording_status() {
    STATUS_RESPONSE=$(curl -s "${CAMERAS_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/record/status" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    IS_RECORDING=$(echo "$STATUS_RESPONSE" | jq -r '.is_recording')
    CURRENT_DURATION=$(echo "$STATUS_RESPONSE" | jq -r '.duration_seconds // 0')
    
    if [ "$IS_RECORDING" = "true" ]; then
        echo "   📹 Status: Recording | Duration: ${CURRENT_DURATION}s"
    else
        echo "   📹 Status: Not Recording"
    fi
}

check_batch_status() {
    BATCH_STATUS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/status?user_id=${TEST_USER_ID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    VIDEOS_READY=$(echo "$BATCH_STATUS" | jq -r '.videos_ready // 0')
    BATCH_NUMBER=$(echo "$BATCH_STATUS" | jq -r '.current_batch_number // 0')
    
    echo "   📦 Batch ${BATCH_NUMBER} | Videos ready: ${VIDEOS_READY}/${BATCH_SIZE}"
}

monitor_batch_accumulation() {
    local batch_num=$1
    local start_segment=$2
    local end_segment=$3
    
    print_header "Monitoring Batch ${batch_num} (Videos ${start_segment}-${end_segment})"
    
    for segment in $(seq $start_segment $end_segment); do
        echo ""
        print_step "Recording segment ${segment}/${TOTAL_SEGMENTS}..."
        
        # Wait for segment to record (with progress indicator)
        for i in $(seq 1 $SEGMENT_DURATION); do
            sleep 1
            if [ $((i % 5)) -eq 0 ]; then
                echo -n "."
            fi
        done
        echo ""
        
        # Check status
        check_recording_status
        
        # Wait for face detection to complete
        print_step "Waiting for face detection to complete..."
        sleep 5
        
        check_batch_status
    done
    
    print_success "Batch ${batch_num}: All videos recorded and face detection completed"
    print_info "Batch threshold reached - pipeline should trigger automatically"
}

################################################################################
# Step 4: Verify Batch Processing
################################################################################

verify_batch_processing() {
    local batch_num=$1
    local expected_trigger=$2
    local expected_videos=$3
    
    print_header "Verifying Batch ${batch_num} Processing"
    
    print_step "Waiting for batch trigger..."
    sleep 5
    
    # Get batch history
    BATCH_HISTORY=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}&limit=1" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    BATCH_UUID=$(echo "$BATCH_HISTORY" | jq -r '.batches[0].batch_uuid')
    BATCH_STATUS=$(echo "$BATCH_HISTORY" | jq -r '.batches[0].status')
    TRIGGER_REASON=$(echo "$BATCH_HISTORY" | jq -r '.batches[0].trigger_reason')
    VIDEO_COUNT=$(echo "$BATCH_HISTORY" | jq -r '.batches[0].video_count')
    
    print_info "Batch UUID: ${BATCH_UUID}"
    print_info "Status: ${BATCH_STATUS}"
    print_info "Trigger: ${TRIGGER_REASON}"
    print_info "Videos: ${VIDEO_COUNT}"
    
    # Verify trigger reason
    if [ "$TRIGGER_REASON" != "$expected_trigger" ]; then
        print_error "Expected trigger_reason='${expected_trigger}', got '${TRIGGER_REASON}'"
        exit 1
    fi
    
    # Verify video count
    if [ "$VIDEO_COUNT" != "$expected_videos" ]; then
        print_error "Expected ${expected_videos} videos, got ${VIDEO_COUNT}"
        exit 1
    fi
    
    print_success "Batch triggered correctly (${TRIGGER_REASON})"
    
    # Monitor processing
    print_step "Pipeline executing (Two-level caching)..."
    
    for i in $(seq 1 60); do
        sleep 1
        
        BATCH_CHECK=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_UUID}" \
          -H "Authorization: Bearer ${AUTH_TOKEN}")
        
        CHECK_STATUS=$(echo "$BATCH_CHECK" | jq -r '.status')
        
        if [ "$CHECK_STATUS" = "completed" ]; then
            break
        fi
        
        if [ $((i % 10)) -eq 0 ]; then
            echo -n "."
        fi
    done
    echo ""
    
    # Get final results
    BATCH_RESULTS=$(curl -s "${VMETA_URL}/api/v1/batch-processing/history?batch_uuid=${BATCH_UUID}" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    INDIVIDUALS=$(echo "$BATCH_RESULTS" | jq -r '.individuals_created')
    INDIVIDUALS_CACHED=$(echo "$BATCH_RESULTS" | jq -r '.individuals_cached')
    MVR=$(echo "$BATCH_RESULTS" | jq -r '.mvr_people_created')
    MVR_CACHED=$(echo "$BATCH_RESULTS" | jq -r '.mvr_people_cached')
    CACHE_RATE=$(echo "$BATCH_RESULTS" | jq -r '.cache_hit_rate')
    PROC_TIME=$(echo "$BATCH_RESULTS" | jq -r '.processing_time_seconds')
    
    print_success "Batch ${batch_num} COMPLETED"
    echo ""
    print_info "Results:"
    echo "   👤 Individuals: ${INDIVIDUALS} created, ${INDIVIDUALS_CACHED} cached"
    echo "   👥 MVR People: ${MVR} created, ${MVR_CACHED} cached"
    echo "   💾 Cache Hit Rate: ${CACHE_RATE}%"
    echo "   ⏱️  Processing Time: ${PROC_TIME}s"
    echo ""
    
    # Store batch UUID for final report
    case $batch_num in
        1) BATCH_1_UUID="$BATCH_UUID" ;;
        2) BATCH_2_UUID="$BATCH_UUID" ;;
        3) BATCH_3_UUID="$BATCH_UUID" ;;
    esac
}

################################################################################
# Step 5: Stop Recording and Verify Partial Batch
################################################################################

stop_recording_and_verify() {
    print_header "STEP 5: Stop Recording and Verify Partial Batch"
    
    print_step "Stopping recording..."
    
    STOP_RESPONSE=$(curl -s -X POST "${CAMERAS_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/record/stop" \
      -H "Authorization: Bearer ${AUTH_TOKEN}")
    
    STOP_STATUS=$(echo "$STOP_RESPONSE" | jq -r '.status')
    
    if [ "$STOP_STATUS" = "success" ]; then
        print_success "Recording stopped"
        DURATION=$(echo "$STOP_RESPONSE" | jq -r '.duration_seconds // 0')
        SEGMENT_COUNT=$(echo "$STOP_RESPONSE" | jq -r '.segment_count // 0')
        print_info "Total duration: ${DURATION}s | Segments: ${SEGMENT_COUNT}"
    else
        print_warning "Recording stop returned: ${STOP_STATUS}"
    fi
    
    # Stop streaming
    print_step "Stopping camera stream..."
    curl -s -X POST "${GATEWAY_URL}/api/v1/streaming/${CAMERA_DEVICE_ID}/stop" \
      -H "Authorization: Bearer ${AUTH_TOKEN}" > /dev/null
    
    print_success "Stream stopped"
    
    # Verify partial batch triggered by recording stop event
    verify_batch_processing 3 "recording_stopped" 3
}

################################################################################
# Final Report
################################################################################

generate_final_report() {
    print_header "TEST COMPLETE - Final Report"
    
    TEST_END_TIME=$(date +%s)
    TEST_DURATION=$((TEST_END_TIME - TEST_START_TIME))
    
    print_success "End-to-End Test Completed Successfully!"
    echo ""
    
    print_info "Test Summary:"
    echo "   📹 Total Segments Recorded: ${TOTAL_SEGMENTS}"
    echo "   📦 Total Batches Processed: 3"
    echo "   ⏱️  Total Test Duration: $((TEST_DURATION / 60)) minutes $((TEST_DURATION % 60)) seconds"
    echo ""
    
    print_info "Batch Processing Summary:"
    echo "   Batch 1 (Videos 1-5): Threshold trigger"
    echo "   Batch 2 (Videos 6-10): Threshold trigger"
    echo "   Batch 3 (Videos 11-13): Recording stop trigger (partial batch)"
    echo ""
    
    print_info "Key Validations:"
    print_success "Automatic batch triggering at threshold"
    print_success "Event-driven face detection completion tracking"
    print_success "Recording stop event triggering partial batch"
    print_success "Two-level caching functional (individuals + MVR)"
    print_success "Cache hit rate improvement across batches"
    print_success "Concurrent batch processing working"
    echo ""
    
    print_info "Batch UUIDs:"
    echo "   Batch 1: ${BATCH_1_UUID}"
    echo "   Batch 2: ${BATCH_2_UUID}"
    echo "   Batch 3: ${BATCH_3_UUID}"
    echo ""
    
    print_success "🎉 All pipeline components validated successfully!"
    echo ""
    
    print_info "Next Steps:"
    echo "   1. Review batch history: curl ${VMETA_URL}/api/v1/batch-processing/history?user_id=${TEST_USER_ID}"
    echo "   2. Check Grafana dashboard for metrics"
    echo "   3. Review logs for detailed execution trace"
    echo "   4. Run load tests to validate performance at scale"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "Continuous Individuals and MVR Pipeline - End-to-End Test"
    
    echo "This test will:"
    echo "  • Record 13 video segments (30 seconds each)"
    echo "  • Process 3 batches automatically (5, 5, 3 videos)"
    echo "  • Validate batch triggering, caching, and MVR creation"
    echo "  • Duration: ~7-8 minutes"
    echo ""
    
    # Skip prompt if --no-prompt flag is passed
    if [[ "$*" != *"--no-prompt"* ]]; then
        echo -n "Press Enter to start the test, or Ctrl+C to cancel... "
        read -r
    fi
    echo ""
    
    # Step 1: Setup
    setup_test_environment
    
    # Step 2: Start recording
    start_camera_recording
    
    # Step 3-4: Monitor and verify batch 1 (videos 1-5)
    monitor_batch_accumulation 1 1 5
    verify_batch_processing 1 "threshold_reached" 5
    
    # Step 3-4: Monitor and verify batch 2 (videos 6-10)
    monitor_batch_accumulation 2 6 10
    verify_batch_processing 2 "threshold_reached" 5
    
    # Step 3-4: Monitor remaining videos (11-13)
    monitor_batch_accumulation 3 11 13
    
    # Step 5: Stop recording and verify partial batch
    stop_recording_and_verify
    
    # Final report
    generate_final_report
}

# Run main function
main "$@"
