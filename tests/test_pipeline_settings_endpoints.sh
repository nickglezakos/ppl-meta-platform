#!/bin/bash
# Test script for pipeline settings endpoints
# Run this after applying the database migration

BASE_URL="http://localhost:8005"
TOKEN="your-token-here"  # Replace with actual token

echo "🧪 Testing Pipeline Settings Endpoints"
echo "======================================"
echo ""

# Test 1: Get current pipeline settings
echo "📋 Test 1: GET /api/v1/cameras/usb_camera_0/pipeline-settings"
curl -X GET "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

# Test 2: Update pipeline settings - Both enabled (default)
echo "📋 Test 2: PATCH - Both pipelines enabled"
curl -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&instant_detection_interval_seconds=5&segment_duration_seconds=30" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

# Test 3: Update pipeline settings - Instant detection only
echo "📋 Test 3: PATCH - Instant detection only (no recording)"
curl -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=false&instant_detection_interval_seconds=10" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

# Test 4: Update pipeline settings - Recording only
echo "📋 Test 4: PATCH - Recording only (no instant detection)"
curl -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=false&recording_pipeline_enabled=true&segment_duration_seconds=60" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

# Test 5: Try to disable both (should fail)
echo "📋 Test 5: PATCH - Try to disable both (should fail with 400)"
curl -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=false&recording_pipeline_enabled=false" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

# Test 6: Try invalid interval (should fail)
echo "📋 Test 6: PATCH - Try invalid interval (should fail with 400)"
curl -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&instant_detection_interval_seconds=100" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

# Test 7: Restore default settings
echo "📋 Test 7: PATCH - Restore default settings"
curl -X PATCH "${BASE_URL}/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&instant_detection_interval_seconds=5&segment_duration_seconds=30" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" | jq '.'
echo ""
echo ""

echo "✅ Pipeline settings endpoint tests complete!"
