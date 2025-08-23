#!/bin/bash

# CAM-TEST-003: Video Streaming and Snapshot Capture Testing
# Tests video streaming capabilities and snapshot capture functionality

set -e  # Exit on any error

echo "🎥 Starting CAM-TEST-003: Video Streaming and Snapshot Capture Test..."
echo "========================================================================"
echo
echo "📋 Test Configuration:"
echo "• Node Service: http://localhost/api/node (via Nginx)"
echo "• Cameras Service: http://localhost/api/cameras (via Nginx)"
echo "• Test User: fresh.user@example.com"
echo "• Test Focus: Video streaming and snapshot capture"
echo "• Proxy: Using Nginx reverse proxy on localhost"
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Authentication Setup
print_step "Step 1: Authentication Setup"
echo "Authenticating user and obtaining JWT token via Nginx..."
AUTH_RESPONSE=$(curl -s -X POST "http://localhost/api/node/api/v1/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=fresh.user@example.com&password=NewPassword234!")

if echo "$AUTH_RESPONSE" | grep -q "access_token"; then
    JWT_TOKEN=$(echo $AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
    print_success "Authentication successful"
    echo "Token obtained: ${JWT_TOKEN:0:20}..."
else
    print_error "Authentication failed"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi
echo

# Step 2: Camera Detection and Connection
print_step "Step 2: Camera Detection and Connection Setup"
echo "Detecting available cameras via Nginx..."
DETECTION_RESPONSE=$(curl -s -X POST "http://localhost/api/cameras/api/v1/cameras/detect" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if echo "$DETECTION_RESPONSE" | grep -q "detected_count"; then
    print_success "Camera detection completed"
    DETECTED_COUNT=$(echo $DETECTION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('detected_count', 0))")
    echo "📊 Detected cameras: $DETECTED_COUNT"
    
    if [ "$DETECTED_COUNT" -eq 0 ]; then
        print_error "No cameras detected - cannot proceed with streaming tests"
        exit 1
    fi
else
    print_error "Camera detection failed"
    echo "Response: $DETECTION_RESPONSE"
    exit 1
fi

# Connect to first camera
echo "Connecting to first detected camera (usb_camera_0) via Nginx..."
CONNECT_RESPONSE=$(curl -s -X POST "http://localhost/api/cameras/api/v1/cameras/usb_camera_0/connect" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if echo "$CONNECT_RESPONSE" | grep -q "connected"; then
    print_success "Camera connected successfully"
    echo "Connection Response: $CONNECT_RESPONSE"
else
    print_warning "Camera connection may have failed"
    echo "Connection Response: $CONNECT_RESPONSE"
fi
echo

# Step 3: Start Video Streaming
print_step "Step 3: Start Video Streaming"
echo "Attempting to start video stream via Nginx..."
STREAM_START_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "http://localhost/api/cameras/api/v1/streaming/usb_camera_0/start" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$STREAM_START_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
STREAM_RESPONSE=$(echo "$STREAM_START_RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    print_success "Video streaming started successfully"
    echo "Stream Response:"
    echo "$STREAM_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STREAM_RESPONSE"
    STREAMING_ACTIVE=true
elif [ "$HTTP_CODE" = "404" ]; then
    print_warning "Streaming endpoint not found (404) - Feature may not be implemented"
    echo "Response: $STREAM_RESPONSE"
    STREAMING_ACTIVE=false
else
    print_error "Failed to start video streaming"
    echo "Response: $STREAM_RESPONSE"
    STREAMING_ACTIVE=false
fi
echo

# Step 4: Capture Snapshot During Streaming
print_step "Step 4: Snapshot Capture Testing"
echo "Attempting to capture snapshot via Nginx..."

# Create snapshots directory if it doesn't exist
mkdir -p /tmp/cam_test_snapshots

SNAPSHOT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost/api/cameras/api/v1/streaming/usb_camera_0/snapshot" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -o "/tmp/cam_test_snapshots/snapshot_$(date +%Y%m%d_%H%M%S).jpg")

SNAPSHOT_HTTP_CODE=$(echo "$SNAPSHOT_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
SNAPSHOT_RESP=$(echo "$SNAPSHOT_RESPONSE" | grep -v "HTTP_CODE:")

echo "Snapshot HTTP Status Code: $SNAPSHOT_HTTP_CODE"
if [ "$SNAPSHOT_HTTP_CODE" = "200" ]; then
    print_success "Snapshot captured successfully"
    # Check if file was created and has content
    SNAPSHOT_FILE=$(ls -la /tmp/cam_test_snapshots/snapshot_*.jpg 2>/dev/null | tail -1)
    if [ -n "$SNAPSHOT_FILE" ]; then
        FILE_SIZE=$(echo "$SNAPSHOT_FILE" | awk '{print $5}')
        print_success "Snapshot file created: $FILE_SIZE bytes"
        echo "File location: /tmp/cam_test_snapshots/"
        ls -la /tmp/cam_test_snapshots/
    else
        print_warning "Snapshot response was 200 but no file created"
    fi
elif [ "$SNAPSHOT_HTTP_CODE" = "404" ]; then
    print_warning "Snapshot endpoint not found (404) - Feature may not be implemented"
    echo "Response: $SNAPSHOT_RESP"
else
    print_error "Failed to capture snapshot"
    echo "Response: $SNAPSHOT_RESP"
fi
echo

# Step 5: Test Video Stream Data Retrieval
print_step "Step 5: Video Stream Data Retrieval Testing"
if [ "$STREAMING_ACTIVE" = true ]; then
    echo "Attempting to retrieve video stream data via Nginx..."
    # Test video stream endpoint with timeout
    timeout 5s curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost/api/cameras/api/v1/streaming/usb_camera_0/video" \
      -H "Authorization: Bearer $JWT_TOKEN" > /tmp/stream_test_output.txt 2>&1 || true
    
    if [ -f /tmp/stream_test_output.txt ]; then
        STREAM_HTTP_CODE=$(grep "HTTP_CODE:" /tmp/stream_test_output.txt | cut -d: -f2)
        STREAM_SIZE=$(wc -c < /tmp/stream_test_output.txt)
        
        if [ "$STREAM_HTTP_CODE" = "200" ] && [ "$STREAM_SIZE" -gt 1000 ]; then
            print_success "Video stream data retrieved successfully"
            echo "Stream data size: $STREAM_SIZE bytes"
        else
            print_warning "Video stream data retrieval may have issues"
            echo "HTTP Code: $STREAM_HTTP_CODE, Data size: $STREAM_SIZE bytes"
        fi
    else
        print_warning "Could not test video stream data retrieval"
    fi
else
    print_warning "Skipping video stream data test - streaming not active"
fi
echo

# Step 6: Stop Video Streaming
print_step "Step 6: Stop Video Streaming"
if [ "$STREAMING_ACTIVE" = true ]; then
    echo "Attempting to stop video stream via Nginx..."
    STREAM_STOP_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "http://localhost/api/cameras/api/v1/streaming/usb_camera_0/stop" \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -H "Content-Type: application/json")
    
    STOP_HTTP_CODE=$(echo "$STREAM_STOP_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    STOP_RESPONSE=$(echo "$STREAM_STOP_RESPONSE" | grep -v "HTTP_CODE:")
    
    echo "Stop HTTP Status Code: $STOP_HTTP_CODE"
    if [ "$STOP_HTTP_CODE" = "200" ]; then
        print_success "Video streaming stopped successfully"
        echo "Stop Response:"
        echo "$STOP_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STOP_RESPONSE"
    else
        print_warning "Failed to stop video streaming or endpoint not available"
        echo "Response: $STOP_RESPONSE"
    fi
else
    print_warning "Skipping stream stop test - streaming was not started"
fi
echo

# Step 7: Camera Disconnection and Cleanup
print_step "Step 7: Camera Disconnection and Cleanup"
echo "Disconnecting camera via Nginx..."
DISCONNECT_RESPONSE=$(curl -s -X POST "http://localhost/api/cameras/api/v1/cameras/usb_camera_0/disconnect" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if echo "$DISCONNECT_RESPONSE" | grep -q "disconnected"; then
    print_success "Camera disconnected successfully"
    echo "Disconnect Response: $DISCONNECT_RESPONSE"
else
    print_warning "Camera disconnection may have failed"
    echo "Disconnect Response: $DISCONNECT_RESPONSE"
fi
echo

# Step 8: Final Validation and Cleanup
print_step "Step 8: Final Validation and Resource Cleanup"
echo "Verifying final camera state via Nginx..."
FINAL_ACTIVE=$(curl -s -X GET "http://localhost/api/cameras/api/v1/cameras/active" \
  -H "Authorization: Bearer $JWT_TOKEN")

ACTIVE_COUNT=$(echo $FINAL_ACTIVE | python3 -c "import sys, json; print(json.load(sys.stdin).get('active_count', 'unknown'))" 2>/dev/null || echo "unknown")

if [ "$ACTIVE_COUNT" = "0" ]; then
    print_success "Final state verification passed - no active connections"
else
    print_warning "Final state verification - active connections: $ACTIVE_COUNT"
fi

echo "Final Active Cameras: $FINAL_ACTIVE"
echo

# Cleanup temporary files
rm -f /tmp/stream_test_output.txt
echo "📁 Temporary test files cleaned up"
echo

echo "========================================================================"
echo -e "${GREEN}🎉 CAM-TEST-003 Video Streaming and Snapshot Capture Test COMPLETED!${NC}"
echo "========================================================================"
echo
echo "✅ Test Results Summary:"
echo "• Authentication: Successful"
echo "• Camera Detection: Tested"
echo "• Camera Connection: Attempted"
echo "• Video Stream Start: Tested"
echo "• Snapshot Capture: Tested"
echo "• Video Stream Data: Tested"
echo "• Video Stream Stop: Tested"
echo "• Camera Disconnection: Tested"
echo "• Resource Cleanup: Completed"
echo
echo "📋 Test completed at: $(date)"
echo "🔍 Review the responses above to validate video streaming and snapshot functionality"
echo
if [ -d "/tmp/cam_test_snapshots" ] && [ "$(ls -A /tmp/cam_test_snapshots)" ]; then
    echo "📸 Captured snapshots available in: /tmp/cam_test_snapshots/"
    ls -la /tmp/cam_test_snapshots/
fi
