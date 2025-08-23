#!/bin/bash
# CAM-TEST-002: Comprehensive Camera Lifecycle Management and Connection Testing
# Author: PPL Meta Platform Team
# Date: August 8, 2025

echo "🧪 Starting CAM-TEST-002: Comprehensive Camera Lifecycle Management Test..."
echo "========================================================================"
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
NODE_SERVICE="http://localhost:8001"
CAMERAS_SERVICE="http://localhost:8005"
TEST_USER="fresh.user@example.com"
TEST_PASSWORD="NewPassword234!"

echo -e "${BLUE}📋 Test Configuration:${NC}"
echo "• Node Service: $NODE_SERVICE"
echo "• Cameras Service: $CAMERAS_SERVICE"
echo "• Test User: $TEST_USER"
echo

# Step 1: Authentication Setup
echo -e "${BLUE}Step 1: Authentication Setup${NC}"
echo "Authenticating user and obtaining JWT token..."

AUTH_RESPONSE=$(curl -s -X POST "$NODE_SERVICE/api/v1/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$TEST_USER&password=$TEST_PASSWORD")

if [[ $? -eq 0 ]] && [[ $AUTH_RESPONSE == *"access_token"* ]]; then
    JWT_TOKEN=$(echo $AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
    if [[ -n "$JWT_TOKEN" ]]; then
        echo -e "${GREEN}✅ Authentication successful${NC}"
        echo "Token obtained: ${JWT_TOKEN:0:20}..."
    else
        echo -e "${RED}❌ Failed to extract JWT token${NC}"
        echo "Response: $AUTH_RESPONSE"
        exit 1
    fi
else
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi
echo

# Step 2: Camera Detection Methods Testing
echo -e "${BLUE}Step 2: Camera Detection Methods Testing${NC}"
echo "Testing camera detection endpoint..."

DETECTION_RESPONSE=$(curl -s -X POST "$CAMERAS_SERVICE/api/v1/cameras/detect" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if [[ $? -eq 0 ]] && [[ $DETECTION_RESPONSE == *"status"* ]]; then
    echo -e "${GREEN}✅ Camera detection completed${NC}"
    echo "Detection Response:"
    echo "$DETECTION_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DETECTION_RESPONSE"
    
    # Extract camera count
    CAMERA_COUNT=$(echo $DETECTION_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'cameras_detected' in data:
        print(len(data['cameras_detected']))
    elif 'total_cameras' in data:
        print(data['total_cameras'])
    else:
        print('0')
except:
    print('0')
" 2>/dev/null)
    
    echo -e "${YELLOW}📊 Detected cameras: $CAMERA_COUNT${NC}"
else
    echo -e "${RED}❌ Camera detection failed${NC}"
    echo "Response: $DETECTION_RESPONSE"
fi
echo

# Step 3: List All Available Cameras
echo -e "${BLUE}Step 3: List All Available Cameras${NC}"
echo "Retrieving all detected cameras from database..."

AVAILABLE_CAMERAS=$(curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/" \
  -H "Authorization: Bearer $JWT_TOKEN")

if [[ $? -eq 0 ]] && [[ $AVAILABLE_CAMERAS == *"status"* ]]; then
    echo -e "${GREEN}✅ Camera list retrieved${NC}"
    echo "Available Cameras:"
    echo "$AVAILABLE_CAMERAS" | python3 -m json.tool 2>/dev/null || echo "$AVAILABLE_CAMERAS"
else
    echo -e "${RED}❌ Failed to retrieve camera list${NC}"
    echo "Response: $AVAILABLE_CAMERAS"
fi
echo

# Step 4: Connect to First Detected Camera
echo -e "${BLUE}Step 4: Connect to First Detected Camera${NC}"
echo "Attempting to connect to first detected camera..."

# Try to connect to usb_camera_0 (most common)
CONNECT_RESPONSE=$(curl -s -X POST "$CAMERAS_SERVICE/api/v1/cameras/usb_camera_0/connect" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Connection attempt completed${NC}"
    echo "Connection Response:"
    echo "$CONNECT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CONNECT_RESPONSE"
    
    # Check if connection was successful
    if [[ $CONNECT_RESPONSE == *"success"* ]] || [[ $CONNECT_RESPONSE == *"CONNECTED"* ]]; then
        CAMERA_CONNECTED=true
        echo -e "${GREEN}📷 Camera connection successful${NC}"
    else
        CAMERA_CONNECTED=false
        echo -e "${YELLOW}⚠️ Camera connection may have failed or no camera available${NC}"
    fi
else
    echo -e "${RED}❌ Connection request failed${NC}"
    CAMERA_CONNECTED=false
fi
echo

# Step 5: List Active Camera Connections
echo -e "${BLUE}Step 5: List Active Camera Connections${NC}"
echo "Checking active camera connections..."

ACTIVE_CAMERAS=$(curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/active" \
  -H "Authorization: Bearer $JWT_TOKEN")

if [[ $? -eq 0 ]] && [[ $ACTIVE_CAMERAS == *"active_connections"* ]]; then
    echo -e "${GREEN}✅ Active connections retrieved${NC}"
    echo "Active Cameras:"
    echo "$ACTIVE_CAMERAS" | python3 -m json.tool 2>/dev/null || echo "$ACTIVE_CAMERAS"
    
    # Extract active count
    ACTIVE_COUNT=$(echo $ACTIVE_CAMERAS | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'total_active' in data:
        print(data['total_active'])
    elif 'active_connections' in data:
        print(len(data['active_connections']))
    else:
        print('0')
except:
    print('0')
" 2>/dev/null)
    
    echo -e "${YELLOW}📊 Active connections: $ACTIVE_COUNT${NC}"
else
    echo -e "${RED}❌ Failed to retrieve active connections${NC}"
    echo "Response: $ACTIVE_CAMERAS"
fi
echo

# Step 6: Test Camera Information Retrieval
echo -e "${BLUE}Step 6: Test Camera Information Retrieval${NC}"
echo "Getting detailed camera information..."

CAMERA_INFO=$(curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/usb_camera_0/info" \
  -H "Authorization: Bearer $JWT_TOKEN")

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Camera info request completed${NC}"
    echo "Camera Information:"
    echo "$CAMERA_INFO" | python3 -m json.tool 2>/dev/null || echo "$CAMERA_INFO"
else
    echo -e "${RED}❌ Failed to retrieve camera information${NC}"
fi
echo

# Step 7: Disconnect Individual Camera
echo -e "${BLUE}Step 7: Disconnect Individual Camera${NC}"
echo "Disconnecting specific camera..."

DISCONNECT_RESPONSE=$(curl -s -X POST "$CAMERAS_SERVICE/api/v1/cameras/usb_camera_0/disconnect" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Disconnect attempt completed${NC}"
    echo "Disconnect Response:"
    echo "$DISCONNECT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DISCONNECT_RESPONSE"
else
    echo -e "${RED}❌ Disconnect request failed${NC}"
fi
echo

# Step 8: Verify Active Connections After Disconnect
echo -e "${BLUE}Step 8: Verify Active Connections After Disconnect${NC}"
echo "Checking active connections after disconnect..."

FINAL_ACTIVE=$(curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/active" \
  -H "Authorization: Bearer $JWT_TOKEN")

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Final active connections retrieved${NC}"
    echo "Final Active Cameras:"
    echo "$FINAL_ACTIVE" | python3 -m json.tool 2>/dev/null || echo "$FINAL_ACTIVE"
    
    # Extract final active count
    FINAL_ACTIVE_COUNT=$(echo $FINAL_ACTIVE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'total_active' in data:
        print(data['total_active'])
    elif 'active_connections' in data:
        print(len(data['active_connections']))
    else:
        print('0')
except:
    print('0')
" 2>/dev/null)
    
    echo -e "${YELLOW}📊 Final active connections: $FINAL_ACTIVE_COUNT${NC}"
else
    echo -e "${RED}❌ Failed to retrieve final active connections${NC}"
fi
echo

# Step 9: Test Bulk Disconnect (Admin Function)
echo -e "${BLUE}Step 9: Test Bulk Disconnect (Admin Function)${NC}"
echo "Testing disconnect-all functionality..."

BULK_DISCONNECT=$(curl -s -X POST "$CAMERAS_SERVICE/api/v1/cameras/disconnect-all" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json")

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Bulk disconnect completed${NC}"
    echo "Bulk Disconnect Response:"
    echo "$BULK_DISCONNECT" | python3 -m json.tool 2>/dev/null || echo "$BULK_DISCONNECT"
else
    echo -e "${RED}❌ Bulk disconnect failed${NC}"
fi
echo

# Step 10: Final State Verification
echo -e "${BLUE}Step 10: Final State Verification${NC}"
echo "Verifying final system state..."

# Check final active connections
FINAL_STATE_ACTIVE=$(curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/active" \
  -H "Authorization: Bearer $JWT_TOKEN")

# Check available cameras
FINAL_STATE_AVAILABLE=$(curl -s -X GET "$CAMERAS_SERVICE/api/v1/cameras/" \
  -H "Authorization: Bearer $JWT_TOKEN")

echo -e "${GREEN}✅ Final state verification completed${NC}"
echo
echo "Final Active Connections:"
echo "$FINAL_STATE_ACTIVE" | python3 -m json.tool 2>/dev/null || echo "$FINAL_STATE_ACTIVE"
echo
echo "Final Available Cameras:"
echo "$FINAL_STATE_AVAILABLE" | python3 -m json.tool 2>/dev/null || echo "$FINAL_STATE_AVAILABLE"
echo

# Test Summary
echo -e "${BLUE}========================================================================"
echo "🎉 CAM-TEST-002 Comprehensive Camera Lifecycle Test COMPLETED!"
echo "========================================================================${NC}"
echo
echo -e "${GREEN}✅ Test Results Summary:${NC}"
echo "• Authentication: Successful"
echo "• Camera Detection: Tested"
echo "• Available Camera Listing: Tested"
echo "• Camera Connection: Attempted"
echo "• Active Connection Monitoring: Tested"
echo "• Camera Information Retrieval: Tested"
echo "• Individual Disconnect: Tested"
echo "• Bulk Disconnect: Tested"
echo "• Final State Verification: Completed"
echo
echo -e "${YELLOW}📋 Test completed at: $(date)${NC}"
echo -e "${BLUE}🔍 Review the responses above to validate camera management functionality${NC}"
echo

exit 0
