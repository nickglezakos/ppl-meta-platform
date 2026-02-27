#!/bin/bash

# Test Camera Recording Fix - Backend Timing Test
# Tests that recording start returns immediately (< 5s) with VMeta in background

echo "🧪 PPL Meta Camera Recording Fix - Testing Script"
echo "=================================================="
echo ""

# Get auth token
echo "1️⃣ Getting auth token..."
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Failed to get auth token. Is Node service running?"
  echo "   Start with: 🐍 Start Node Service (Local Python)"
  exit 1
fi

echo "✅ Got auth token: ${TOKEN:0:20}..."
echo ""

# Detect cameras
echo "2️⃣ Detecting cameras..."
curl -s -X POST "http://localhost:8005/api/v1/cameras/detect" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "✅ Camera detection complete"
echo ""

# Test USB camera if available
echo "3️⃣ Testing USB Camera Recording..."
echo "-----------------------------------"

# Connect USB camera
echo "   Connecting to usb_camera_0..."
CONNECT_RESPONSE=$(curl -s -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/connect" \
  -H "Authorization: Bearer $TOKEN")

if echo "$CONNECT_RESPONSE" | jq -e '.status == "connected"' > /dev/null 2>&1; then
  echo "   ✅ USB camera connected"
  
  # Start streaming
  echo "   Starting stream..."
  curl -s -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/start" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
  echo "   ✅ Stream started"
  
  # Start recording with timing
  echo "   Starting recording (measuring response time)..."
  START_TIME=$(date +%s)
  
  RECORDING_RESPONSE=$(curl -s -w "\n%{time_total}" -X POST \
    "http://localhost:8005/api/v1/streaming/usb_camera_0/record/start?enable_instant_detection=true" \
    -H "Authorization: Bearer $TOKEN")
  
  END_TIME=$(date +%s)
  RESPONSE_TIME=$(echo "$RECORDING_RESPONSE" | tail -1)
  RESPONSE_BODY=$(echo "$RECORDING_RESPONSE" | head -n -1)
  
  echo ""
  echo "   📊 Response time: ${RESPONSE_TIME}s"
  echo ""
  
  # Check if response is successful
  if echo "$RESPONSE_BODY" | jq -e '.status == "success"' > /dev/null 2>&1; then
    echo "   ✅ Recording started successfully"
    echo "   Session UUID: $(echo "$RESPONSE_BODY" | jq -r '.session_uuid')"
    
    # Verify response time
    if (( $(echo "$RESPONSE_TIME < 10" | bc -l) )); then
      echo "   ✅ Response time < 10s (GOOD - Backend returns immediately)"
    else
      echo "   ⚠️  Response time >= 10s (Backend may still be blocking)"
    fi
    
    # Wait a bit then stop recording
    echo ""
    echo "   Waiting 5 seconds before stopping..."
    sleep 5
    
    echo "   Stopping recording..."
    curl -s -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/record/stop" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    echo "   ✅ Recording stopped"
  else
    echo "   ❌ Recording failed to start"
    echo "   Response: $RESPONSE_BODY"
  fi
else
  echo "   ⚠️  USB camera not available (may not exist on this system)"
fi

echo ""
echo "4️⃣ Testing RTSP Camera Recording (if configured)..."
echo "---------------------------------------------------"

# Test RTSP camera if configured
RTSP_DEVICE_ID="rtsp_192.168.1.76_554"
echo "   Checking for RTSP camera: $RTSP_DEVICE_ID..."

# Try to connect
RTSP_CONNECT=$(curl -s -X POST "http://localhost:8005/api/v1/cameras/$RTSP_DEVICE_ID/connect" \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null)

if echo "$RTSP_CONNECT" | jq -e '.status == "connected"' > /dev/null 2>&1; then
  echo "   ✅ RTSP camera connected"
  
  # Start streaming
  echo "   Starting stream..."
  curl -s -X POST "http://localhost:8005/api/v1/streaming/$RTSP_DEVICE_ID/start" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
  echo "   ✅ Stream started"
  
  # Start recording with timing
  echo "   Starting recording (measuring response time)..."
  START_TIME=$(date +%s)
  
  RTSP_RECORDING=$(curl -s -w "\n%{time_total}" -X POST \
    "http://localhost:8005/api/v1/streaming/$RTSP_DEVICE_ID/record/start?enable_instant_detection=true" \
    -H "Authorization: Bearer $TOKEN")
  
  END_TIME=$(date +%s)
  RTSP_RESPONSE_TIME=$(echo "$RTSP_RECORDING" | tail -1)
  RTSP_RESPONSE_BODY=$(echo "$RTSP_RECORDING" | head -n -1)
  
  echo ""
  echo "   📊 Response time: ${RTSP_RESPONSE_TIME}s"
  echo ""
  
  # Check if response is successful
  if echo "$RTSP_RESPONSE_BODY" | jq -e '.status == "success"' > /dev/null 2>&1; then
    echo "   ✅ Recording started successfully"
    echo "   Session UUID: $(echo "$RTSP_RESPONSE_BODY" | jq -r '.session_uuid')"
    
    # Verify response time
    if (( $(echo "$RTSP_RESPONSE_TIME < 10" | bc -l) )); then
      echo "   ✅ Response time < 10s (GOOD - No UI freeze!)"
    else
      echo "   ⚠️  Response time >= 10s (May cause UI issues)"
    fi
    
    # Wait then stop
    echo ""
    echo "   Waiting 5 seconds before stopping..."
    sleep 5
    
    echo "   Stopping recording..."
    curl -s -X POST "http://localhost:8005/api/v1/streaming/$RTSP_DEVICE_ID/record/stop" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    echo "   ✅ Recording stopped"
  else
    echo "   ❌ Recording failed to start"
    echo "   Response: $RTSP_RESPONSE_BODY"
  fi
else
  echo "   ⚠️  RTSP camera not configured or not accessible"
  echo "      (Configure RTSP camera at 192.168.1.76:554 to test)"
fi

echo ""
echo "=================================================="
echo "✅ Testing complete!"
echo ""
echo "📋 Expected Results:"
echo "  • Response time < 10s (ideally < 5s)"
echo "  • Recording status: 'success'"
echo "  • Session UUID: valid UUID"
echo "  • No timeout errors"
echo ""
echo "🔍 Check backend logs for VMeta notification:"
echo "  grep 'VMETA-NOTIFY' ppl-meta-cameras/logs/ppl-meta-cameras.log"
echo ""
