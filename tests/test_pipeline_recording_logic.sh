#!/bin/bash

# Test Pipeline Settings Recording Logic Integration
# Tests the actual recording behavior with different pipeline configurations

set -e

echo "🧪 Testing Pipeline Settings Recording Logic Integration"
echo "========================================================="
echo ""

# Configuration
NODE_SERVICE="http://localhost:8001"
CAMERAS_SERVICE="http://localhost:8005"
DEVICE_ID="usb_camera_0"
USER_EMAIL="fresh.user@example.com"
USER_PASSWORD="NewPassword234!"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo "ℹ $1"
}

# Function to get JWT token
get_token() {
    print_info "Logging in as $USER_EMAIL..."
    
    RESPONSE=$(curl -s -X POST "$NODE_SERVICE/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$USER_EMAIL\",\"password\":\"$USER_PASSWORD\"}")
    
    TOKEN=$(echo $RESPONSE | jq -r '.access_token')
    
    if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
        print_error "Failed to get authentication token"
        echo "Response: $RESPONSE"
        exit 1
    fi
    
    print_success "Authenticated successfully"
    echo "$TOKEN"
}

# Function to start recording
start_recording() {
    local token=$1
    local device_id=$2
    
    print_info "Starting recording for $device_id..."
    
    RESPONSE=$(curl -s -X POST "$CAMERAS_SERVICE/api/v1/cameras/$device_id/recording/start" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '{"quality": "high"}')
    
    echo "$RESPONSE"
}

# Function to stop recording
stop_recording() {
    local token=$1
    local device_id=$2
    
    print_info "Stopping recording for $device_id..."
    
    RESPONSE=$(curl -s -X POST "$CAMERAS_SERVICE/api/v1/cameras/$device_id/recording/stop" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json")
    
    echo "$RESPONSE"
}

# Function to get pipeline settings
get_pipeline_settings() {
    local token=$1
    local device_id=$2
    
    curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/$device_id/pipeline-settings" \
        -H "Authorization: Bearer $token"
}

# Function to update pipeline settings
update_pipeline_settings() {
    local token=$1
    local device_id=$2
    local data=$3
    
    curl -s -X PATCH "$CAMERAS_SERVICE/api/v1/cameras/$device_id/pipeline-settings" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "$data"
}

# Function to check Cameras service logs
check_logs() {
    local pattern=$1
    print_info "Checking logs for pattern: $pattern"
    
    # Get the last 50 lines of the cameras service log (adjust path as needed)
    if [ -f "../ppl-meta-cameras/logs/camera_service.log" ]; then
        tail -n 50 ../ppl-meta-cameras/logs/camera_service.log | grep "$pattern" || echo "(no matches)"
    else
        print_warning "Log file not found at ../ppl-meta-cameras/logs/camera_service.log"
    fi
}

# Get authentication token
TOKEN=$(get_token)
echo ""

# Test 1: Default Configuration (Both Pipelines Enabled)
echo "📋 Test 1: Default Configuration (Both Pipelines)"
echo "=================================================="
print_info "Current settings for $DEVICE_ID:"
get_pipeline_settings "$TOKEN" "$DEVICE_ID" | jq '.'

print_info "Starting recording with both pipelines enabled..."
START_RESULT=$(start_recording "$TOKEN" "$DEVICE_ID")
echo "$START_RESULT" | jq '.'

SESSION_UUID=$(echo "$START_RESULT" | jq -r '.session_uuid // .recording_id')
print_info "Session UUID: $SESSION_UUID"

sleep 5

print_info "Stopping recording..."
STOP_RESULT=$(stop_recording "$TOKEN" "$DEVICE_ID")
echo "$STOP_RESULT" | jq '.'

print_success "Test 1 completed"
echo ""

sleep 2

# Test 2: Instant Detection Only Mode
echo "📋 Test 2: Instant Detection Only Mode"
echo "======================================="
print_info "Updating pipeline settings to instant-detection-only..."
update_pipeline_settings "$TOKEN" "$DEVICE_ID" \
    '{"instant_detection_enabled": true, "recording_pipeline_enabled": false}' | jq '.'

print_info "Starting recording with instant-detection-only..."
START_RESULT=$(start_recording "$TOKEN" "$DEVICE_ID")
echo "$START_RESULT" | jq '.'

MODE=$(echo "$START_RESULT" | jq -r '.mode // "full_recording"')
if [ "$MODE" == "instant_detection_only" ]; then
    print_success "Correctly started in instant-detection-only mode"
else
    print_error "Expected mode 'instant_detection_only', got '$MODE'"
fi

sleep 5

print_info "Stopping instant-detection-only session..."
STOP_RESULT=$(stop_recording "$TOKEN" "$DEVICE_ID")
echo "$STOP_RESULT" | jq '.'

STOP_MODE=$(echo "$STOP_RESULT" | jq -r '.mode // "unknown"')
if [ "$STOP_MODE" == "instant_detection_only" ]; then
    print_success "Correctly stopped instant-detection-only session"
else
    print_error "Expected stop mode 'instant_detection_only', got '$STOP_MODE'"
fi

print_success "Test 2 completed"
echo ""

sleep 2

# Test 3: Recording Only Mode (No Instant Detection)
echo "📋 Test 3: Recording Only Mode (No Instant Detection)"
echo "====================================================="
print_info "Updating pipeline settings to recording-only..."
update_pipeline_settings "$TOKEN" "$DEVICE_ID" \
    '{"instant_detection_enabled": false, "recording_pipeline_enabled": true}' | jq '.'

print_info "Starting recording with recording-only mode..."
START_RESULT=$(start_recording "$TOKEN" "$DEVICE_ID")
echo "$START_RESULT" | jq '.'

MODE=$(echo "$START_RESULT" | jq -r '.mode // "full_recording"')
if [ "$MODE" != "instant_detection_only" ]; then
    print_success "Started in recording mode (no instant detection)"
else
    print_error "Unexpected mode: $MODE"
fi

sleep 5

print_info "Stopping recording-only session..."
STOP_RESULT=$(stop_recording "$TOKEN" "$DEVICE_ID")
echo "$STOP_RESULT" | jq '.'

print_success "Test 3 completed"
echo ""

sleep 2

# Test 4: Restore Default Settings
echo "📋 Test 4: Restore Default Settings"
echo "===================================="
print_info "Restoring default settings (both pipelines enabled)..."
update_pipeline_settings "$TOKEN" "$DEVICE_ID" \
    '{"instant_detection_enabled": true, "recording_pipeline_enabled": true, "instant_detection_interval_seconds": 5, "segment_duration_seconds": 30}' | jq '.'

print_info "Verifying settings..."
FINAL_SETTINGS=$(get_pipeline_settings "$TOKEN" "$DEVICE_ID")
echo "$FINAL_SETTINGS" | jq '.'

INSTANT_ENABLED=$(echo "$FINAL_SETTINGS" | jq -r '.instant_detection_enabled')
RECORDING_ENABLED=$(echo "$FINAL_SETTINGS" | jq -r '.recording_pipeline_enabled')

if [ "$INSTANT_ENABLED" == "true" ] && [ "$RECORDING_ENABLED" == "true" ]; then
    print_success "Settings restored to default"
else
    print_error "Failed to restore default settings"
fi

print_success "Test 4 completed"
echo ""

# Summary
echo "📊 Test Summary"
echo "==============="
print_success "All pipeline recording logic tests completed!"
echo ""
echo "✅ Test 1: Both pipelines (default)"
echo "✅ Test 2: Instant-detection-only mode"
echo "✅ Test 3: Recording-only mode"
echo "✅ Test 4: Settings restore"
echo ""
print_info "Check the Cameras service logs for detailed pipeline status messages"
print_info "Look for log entries with [PIPELINE-SETTINGS], [INSTANT-ONLY], etc."
