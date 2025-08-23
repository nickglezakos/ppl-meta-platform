#!/bin/bash
# CAM-TEST-001: Complete Cross-Service Authentication Integration Test
# Tests the integration between Node service authentication and Camera service access.

echo "🎯 CAM-TEST-001: COMPLETE CROSS-SERVICE AUTHENTICATION TEST"
echo "=============================================================="
echo

echo "📋 Test Specification:"
echo "• Step 1: Authenticate with Node service to get JWT token"
echo "• Step 2: Use Node JWT token to access Camera detection endpoint"
echo "• Step 3: Verify camera detection results and cross-service authentication"
echo

# Step 1: Node Service Authentication
echo "🔍 Step 1: Node Service Authentication"
echo "======================================="

JWT_RESPONSE=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!')

echo "Node Auth Response:"
echo "$JWT_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(json.dumps(data, indent=2))
    if 'access_token' in data:
        print('\\n✅ SUCCESS: Node authentication successful')
        print(f'   Token: {data[\"access_token\"][:40]}...')
        # Export token for next step
        with open('/tmp/jwt_token.txt', 'w') as f:
            f.write(data['access_token'])
    else:
        print('\\n❌ FAILED: No access_token in response')
        sys.exit(1)
except Exception as e:
    print(f'❌ ERROR: Failed to parse JSON - {e}')
    sys.exit(1)
" || exit 1

# Get the token
JWT_TOKEN=$(cat /tmp/jwt_token.txt)

echo
echo "🎥 Step 2: Camera Detection with Cross-Service JWT"
echo "=================================================="

CAMERA_RESPONSE=$(curl -s -X POST 'http://localhost:8005/api/v1/cameras/detect' \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H 'Content-Type: application/json' \
  -w "HTTP_STATUS:%{http_code}")

# Extract response and status
HTTP_STATUS=$(echo "$CAMERA_RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
RESPONSE_BODY=$(echo "$CAMERA_RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "Camera Detection HTTP Status: $HTTP_STATUS"
echo "Camera Detection Response:"
echo "$RESPONSE_BODY" | python3 -c "
import sys, json
try:
    data = sys.stdin.read().strip()
    if data:
        parsed = json.loads(data)
        print(json.dumps(parsed, indent=2))
    else:
        print('(empty response)')
except:
    print(data if data else '(no response)')
"

echo
echo "🎯 Step 3: Test Results Summary"
echo "==============================="

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ SUCCESS: Cross-service authentication working!"
    echo "✅ SUCCESS: Camera detection endpoint accessible with Node JWT"
    echo "✅ SUCCESS: CAM-TEST-001 PASSED"
    echo
    echo "🏆 INTEGRATION TEST RESULT: SUCCESSFUL"
    echo "   Node Service JWT tokens are accepted by Camera service"
    echo "   Cross-service authentication is working correctly"
else
    echo "❌ FAILED: Camera detection returned HTTP $HTTP_STATUS"
    echo "❌ FAILED: CAM-TEST-001 NEEDS INVESTIGATION"
    echo
    echo "🔍 DEBUGGING INFO:"
    echo "   Check camera service logs for authentication errors"
    echo "   Verify JWT token format and permissions"
fi

# Cleanup
rm -f /tmp/jwt_token.txt
