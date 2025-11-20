#!/bin/bash
# Test script for service-to-service authentication and Enhanced Logic V2
#
# This script tests the authentication fixes and verifies Enhanced Logic V2 works correctly.

set -e  # Exit on error

echo "=========================================="
echo "Service Authentication Test Script"
echo "=========================================="
echo ""

# Configuration
ORCHESTRATOR_URL="http://localhost:8002"
INTERNAL_TOKEN="ppl-meta-internal-service-secret-key-change-in-production"

# Test video UUID - use the most recent video from database
TEST_VIDEO_UUID="d5fc47ef-ec7c-48fc-a53a-ab3a0ae8e6fb"

echo "📋 Test Configuration:"
echo "   Orchestrator URL: $ORCHESTRATOR_URL"
echo "   Test Video UUID: $TEST_VIDEO_UUID"
echo ""

# Test 1: Enhanced Logic V2 without auth (should fail or return empty)
echo "=============================================="
echo "Test 1: Enhanced Logic V2 WITHOUT Auth Token"
echo "=============================================="
echo "Expected: Should work with internal token or return gracefully"
echo ""

response_no_auth=$(curl -s -w "\n%{http_code}" \
  "$ORCHESTRATOR_URL/api/v1/media/$TEST_VIDEO_UUID/faces/enhanced-v2" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json")

http_code=$(echo "$response_no_auth" | tail -n 1)
body=$(echo "$response_no_auth" | sed '$d')

echo "HTTP Status: $http_code"
echo "Response (first 200 chars): ${body:0:200}"
echo ""

# Test 2: Enhanced Logic V2 with service auth token
echo "================================================"
echo "Test 2: Enhanced Logic V2 WITH Service Auth"
echo "================================================"
echo "Expected: Should succeed and create face_detection_session"
echo ""

response_with_auth=$(curl -s -w "\n%{http_code}" \
  "$ORCHESTRATOR_URL/api/v1/media/$TEST_VIDEO_UUID/faces/enhanced-v2" \
  -H "Authorization: Bearer $INTERNAL_TOKEN" \
  -H "X-Service-Name: test-script" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json")

http_code=$(echo "$response_with_auth" | tail -n 1)
body=$(echo "$response_with_auth" | sed '$d')

echo "HTTP Status: $http_code"
echo "Response:"
echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
echo ""

# Test 3: Check if face_detection_session was created
if [ "$http_code" = "200" ]; then
    echo "✅ Enhanced Logic V2 request succeeded!"
    echo ""
    
    session_uuid=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_uuid', ''))" 2>/dev/null || echo "")
    
    if [ -n "$session_uuid" ]; then
        echo "📊 Checking database for session: $session_uuid"
        echo ""
        
        # Check face_detection_sessions table
        psql -d ppl_vision_db -c "
            SELECT session_uuid, media_uuid, session_type, 
                   total_faces_detected, processing_status, created_at 
            FROM face_detection_sessions 
            WHERE session_uuid = '$session_uuid';" || true
        
        echo ""
        
        # Check person_objects table
        echo "📊 Checking person_objects created:"
        psql -d ppl_vision_db -c "
            SELECT COUNT(*) as person_object_count, 
                   MAX(created_at) as latest_created 
            FROM person_objects 
            WHERE media_id = '$TEST_VIDEO_UUID';" || true
        
        echo ""
    fi
else
    echo "❌ Enhanced Logic V2 request failed with status: $http_code"
    echo ""
fi

# Test 4: Verify overall database state
echo "=========================================="
echo "Test 4: Overall Database State"
echo "=========================================="
echo ""

echo "📊 Recent face_detection_sessions (last 5):"
psql -d ppl_vision_db -c "
    SELECT session_uuid, media_uuid, total_faces_detected, 
           processing_status, created_at 
    FROM face_detection_sessions 
    ORDER BY created_at DESC 
    LIMIT 5;" || true

echo ""

echo "📊 Recent person_objects count:"
psql -d ppl_vision_db -c "
    SELECT COUNT(*) as total_person_objects 
    FROM person_objects 
    WHERE created_at >= NOW() - INTERVAL '1 hour';" || true

echo ""

echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "- Test 1 checked Enhanced Logic V2 without auth"
echo "- Test 2 checked Enhanced Logic V2 with service token"
echo "- Test 3 verified face_detection_session creation"
echo "- Test 4 showed overall database state"
echo ""
echo "Next steps:"
echo "1. If tests passed: Re-enable auto-triggers in Media and Camera services"
echo "2. If tests failed: Check service logs and fix authentication issues"
echo "3. Upload a new video and verify full pipeline works"
echo ""
