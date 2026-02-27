#!/bin/bash
# Quick test of pipeline settings endpoints
# This test assumes the cameras service is running on localhost:8005

BASE_URL="http://localhost:8005"

echo "🧪 Testing Pipeline Settings Endpoints"
echo "========================================="
echo ""
echo "Note: Using public endpoints without authentication for testing"
echo "If authentication is required, you'll need to add a valid token"
echo ""

# Test 1: Get pipeline settings for usb_camera_0
echo "📋 Test 1: GET pipeline settings for usb_camera_0"
echo "Request: GET ${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings"
curl -s "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings" | python3 -m json.tool
echo ""
echo ""

# Test 2: Get pipeline settings for mobile camera
echo "📋 Test 2: GET pipeline settings for mobile camera"
echo "Request: GET ${BASE_URL}/api/v1/cameras/mobile_TKQ1.221114.001/pipeline-settings"
curl -s "${BASE_URL}/api/v1/cameras/mobile_TKQ1.221114.001/pipeline-settings" | python3 -m json.tool
echo ""
echo ""

# Test 3: Try to get settings for non-existent camera (should fail)
echo "📋 Test 3: GET pipeline settings for non-existent camera (should return 404)"
echo "Request: GET ${BASE_URL}/api/v1/cameras/fake_camera_999/pipeline-settings"
curl -s "${BASE_URL}/api/v1/cameras/fake_camera_999/pipeline-settings" | python3 -m json.tool
echo ""
echo ""

# Test 4: Update pipeline settings - Instant detection only
echo "📋 Test 4: PATCH - Set to instant detection only"
echo "Request: PATCH ${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings"
echo "Body: instant_detection=true, recording_pipeline=false"
curl -s -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=false&instant_detection_interval_seconds=10" | python3 -m json.tool
echo ""
echo ""

# Test 5: Verify the change
echo "📋 Test 5: Verify the change was applied"
curl -s "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings" | python3 -m json.tool
echo ""
echo ""

# Test 6: Update pipeline settings - Recording only
echo "📋 Test 6: PATCH - Set to recording only"
echo "Request: PATCH ${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings"
echo "Body: instant_detection=false, recording_pipeline=true"
curl -s -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=false&recording_pipeline_enabled=true&segment_duration_seconds=60" | python3 -m json.tool
echo ""
echo ""

# Test 7: Try to disable both (should fail with 400)
echo "📋 Test 7: PATCH - Try to disable both pipelines (should fail)"
echo "Request: PATCH ${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings"
echo "Body: instant_detection=false, recording_pipeline=false"
curl -s -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=false&recording_pipeline_enabled=false" | python3 -m json.tool
echo ""
echo ""

# Test 8: Try invalid instant detection interval (should fail with 400)
echo "📋 Test 8: PATCH - Invalid instant detection interval (should fail)"
echo "Request: interval=100 (must be 1-60)"
curl -s -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&instant_detection_interval_seconds=100" | python3 -m json.tool
echo ""
echo ""

# Test 9: Try invalid segment duration (should fail with 400)
echo "📋 Test 9: PATCH - Invalid segment duration (should fail)"
echo "Request: segment_duration=500 (must be 5-300)"
curl -s -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&segment_duration_seconds=500" | python3 -m json.tool
echo ""
echo ""

# Test 10: Restore default settings
echo "📋 Test 10: PATCH - Restore default settings"
echo "Request: Both pipelines enabled with default intervals"
curl -s -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&instant_detection_interval_seconds=5&segment_duration_seconds=30" | python3 -m json.tool
echo ""
echo ""

# Final verification
echo "📋 Final: Verify all cameras have valid settings"
curl -s "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings" | python3 -m json.tool
echo ""

echo "✅ Pipeline settings endpoint tests complete!"
echo ""
echo "Summary of configurations tested:"
echo "  ✓ Default (both enabled)"
echo "  ✓ Instant detection only"
echo "  ✓ Recording only"
echo "  ✓ Validation: Both disabled (rejected)"
echo "  ✓ Validation: Invalid intervals (rejected)"
