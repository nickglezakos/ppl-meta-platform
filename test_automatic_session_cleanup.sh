#!/bin/bash

echo "🧪 Testing Automatic Streaming Session Cleanup"
echo "=" | tr ' ' '=' | head -c 60; echo

# Get authentication token
echo "1️⃣ Getting authentication token..."
AUTH_RESPONSE=$(curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' \
  -s)

TOKEN=$(echo $AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get authentication token"
    exit 1
fi

echo "✅ Authentication successful"

# Function to get streaming sessions
get_sessions() {
    curl -H "Authorization: Bearer $TOKEN" \
         -s http://localhost:8005/api/v1/auth/streaming-sessions | \
         python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Sessions: {data['sessions']['total_sessions']}\")"
}

# Function to get cameras
get_cameras() {
    curl -H "Authorization: Bearer $TOKEN" \
         -s http://localhost:8005/api/v1/cameras/ | \
         python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['device_id'] if data else 'NO_CAMERAS')"
}

echo ""
echo "2️⃣ Checking initial session state..."
get_sessions

echo ""
echo "3️⃣ Getting available cameras..."
DEVICE_ID=$(get_cameras)

if [ "$DEVICE_ID" = "NO_CAMERAS" ]; then
    echo "⚠️ No cameras available for testing"
    exit 1
fi

echo "🎯 Using camera: $DEVICE_ID"

echo ""
echo "4️⃣ Test 1: Stream start/stop session cleanup"
echo "Starting stream for $DEVICE_ID..."

# Start stream
START_RESPONSE=$(curl -H "Authorization: Bearer $TOKEN" \
     -X POST -s http://localhost:8005/api/v1/streaming/$DEVICE_ID/start)

echo "✅ Stream start response received"

# Check sessions after start
sleep 2
echo "📊 Sessions after stream start:"
get_sessions

echo ""
echo "Stopping stream for $DEVICE_ID..."

# Stop stream and check for cleanup
STOP_RESPONSE=$(curl -H "Authorization: Bearer $TOKEN" \
     -X POST -s http://localhost:8005/api/v1/streaming/$DEVICE_ID/stop)

echo "✅ Stream stop response:"
echo $STOP_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Status: {data.get('status', 'unknown')}\")
    if 'sessions_cleaned' in data:
        print(f\"🧹 Sessions cleaned during stop: {data['sessions_cleaned']}\")
    else:
        print('❌ No sessions_cleaned field in response')
except:
    print('❌ Error parsing response')
"

# Check sessions after stop
sleep 1
echo "📊 Sessions after stream stop:"
get_sessions

echo ""
echo "5️⃣ Test 2: Camera disconnect session cleanup"

# Start stream again
echo "Starting stream again for $DEVICE_ID..."
curl -H "Authorization: Bearer $TOKEN" \
     -X POST -s http://localhost:8005/api/v1/streaming/$DEVICE_ID/start > /dev/null

sleep 2
echo "📊 Sessions before disconnect:"
get_sessions

echo ""
echo "Disconnecting camera $DEVICE_ID..."

# Disconnect camera
DISCONNECT_RESPONSE=$(curl -H "Authorization: Bearer $TOKEN" \
     -X POST -s http://localhost:8005/api/v1/cameras/$DEVICE_ID/disconnect)

echo "✅ Camera disconnect response:"
echo $DISCONNECT_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Status: {data.get('status', 'unknown')}\")
    if 'sessions_cleaned' in data:
        print(f\"🧹 Sessions cleaned during disconnect: {data['sessions_cleaned']}\")
    else:
        print('❌ No sessions_cleaned field in response')
except:
    print('❌ Error parsing response')
"

# Check sessions after disconnect
sleep 1
echo "📊 Sessions after camera disconnect:"
get_sessions

echo ""
echo "6️⃣ Test 3: Disconnect all cameras cleanup"

# Start a few streams
echo "Creating multiple sessions..."
curl -H "Authorization: Bearer $TOKEN" \
     -X POST -s http://localhost:8005/api/v1/streaming/$DEVICE_ID/start > /dev/null

sleep 2
echo "📊 Sessions before disconnect all:"
get_sessions

echo ""
echo "Disconnecting all cameras..."

# Disconnect all
DISCONNECT_ALL_RESPONSE=$(curl -H "Authorization: Bearer $TOKEN" \
     -X POST -s http://localhost:8005/api/v1/cameras/disconnect-all)

echo "✅ Disconnect all response:"
echo $DISCONNECT_ALL_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Status: {data.get('status', 'unknown')}\")
    if 'sessions_cleaned' in data:
        print(f\"🧹 Sessions cleaned during disconnect all: {data['sessions_cleaned']}\")
    else:
        print('❌ No sessions_cleaned field in response')
except:
    print('❌ Error parsing response')
"

# Check final sessions
sleep 1
echo "📊 Final sessions count:"
FINAL_COUNT=$(curl -H "Authorization: Bearer $TOKEN" \
         -s http://localhost:8005/api/v1/auth/streaming-sessions | \
         python3 -c "import sys, json; data=json.load(sys.stdin); print(data['sessions']['total_sessions'])")

echo "Sessions: $FINAL_COUNT"

echo ""
echo "🎯 Test Results Summary:"
if [ "$FINAL_COUNT" = "0" ]; then
    echo "🎉 All tests passed! Automatic session cleanup is working correctly."
    echo "✅ Sessions properly cleaned up: 0 sessions remaining"
else
    echo "⚠️ Warning: $FINAL_COUNT sessions remain after cleanup."
    echo "This may indicate an issue with automatic cleanup."
fi
