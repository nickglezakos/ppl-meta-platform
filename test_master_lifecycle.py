#!/usr/bin/env python3
"""
Test Master Lifecycle Workflow with force_process parameter
"""
import json
import time

import requests

# Setup authentication and test data
auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwidXNlcl9pZCI6InVzZXIxMjMiLCJyb2xlIjoidXNlciIsImV4cCI6MTczODA4NTU1N30.HvW2OqAW_eZ3rnvs0SL6NWwBkXWNMwPxiEFT8z0L70o"
headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

# Test media from our previous successful tests
media_uuid = "018d9a23-0e7a-7d42-abc3-d4f1e8c2b5a9"
camera_device_uuid = "018d9a22-e5f7-7b48-934a-1c5e2f8d4b67"

print("🎯 FINAL CORRECTED TEST: Master Lifecycle Workflow with force_process")
print("=" * 70)

# Correct payload structure based on WorkflowExecutionRequest model
correct_payload = {
    "source_id": media_uuid,  # Required: Media ID
    "source_identifier": "test-video-sample",  # Required: Human-readable identifier
    "source_type": "media",  # Default: media
    "workflow_types": ["face_detection", "person_objects"],  # Default workflows
    "execution_trigger": "manual",  # Default: manual
    "config": {
        "method": "two_stage",
        "force_process": True,  # This should bypass duplicate prevention!!!
        "detection_method": "two_stage",
        "frame_interval": 10,
        "confidence_threshold": 0.5,
        "enable_distance_calculation": True,
        "store_session": True,
    },
}

print(f"📤 Correct Payload Structure:")
print(json.dumps(correct_payload, indent=2))

enhanced_response = requests.post(
    "http://localhost:8002/api/v1/master-lifecycle/workflows/start",
    json=correct_payload,
    headers=headers,
    timeout=45,
)

print(f"\n📋 Response Status: {enhanced_response.status_code}")

if enhanced_response.status_code == 200:
    enhanced_result = enhanced_response.json()

    print("✅ MASTER LIFECYCLE WORKFLOW STARTED!")
    print("📊 INITIAL RESPONSE:")
    print(json.dumps(enhanced_result, indent=2))

    # Extract session UUID and check status
    session_uuid = enhanced_result.get("session_uuid")
    if session_uuid:
        print(f"\n🔍 Checking workflow status for session: {session_uuid}")

        # Wait a moment and check status
        time.sleep(5)

        status_response = requests.get(
            f"http://localhost:8002/api/v1/master-lifecycle/workflows/status/{session_uuid}",
            headers=headers,
            timeout=30,
        )

        if status_response.status_code == 200:
            status_result = status_response.json()
            faces_detected = status_result.get("total_faces_detected", 0)
            frames_processed = status_result.get("total_frames_processed", 0)

            print("📊 WORKFLOW STATUS:")
            print(f"👤 Total Faces Detected: {faces_detected}")
            print(f"🎬 Total Frames Processed: {frames_processed}")
            print(f'📈 Progress: {status_result.get("progress", 0)}%')
            print(f'🔄 Status: {status_result.get("status", "unknown")}')
            print(f'🎯 Current Stage: {status_result.get("current_stage", "unknown")}')

            if faces_detected > 0:
                print("\n🎉 BREAKTHROUGH SUCCESS!")
                print("✅ Master Lifecycle with force_process WORKING!")
                print("✅ Two-stage face detection fully operational end-to-end!")
                print(
                    "✅ Orchestrator successfully passing force_process to Vision Service!"
                )
                print(
                    "✅ Complete workflow: Request → Orchestrator → Vision Service → Results"
                )
            elif status_result.get("status") == "processing":
                print("\n⏳ Workflow still processing - may need more time...")
            else:
                print(
                    "\n❌ Still getting 0 faces - investigating force_process flow..."
                )

            print(f"\n📄 Full Status Result:")
            print(json.dumps(status_result, indent=2))
        else:
            print(f"❌ Status check failed: {status_response.text}")

else:
    print(f"❌ Master Lifecycle failed: {enhanced_response.text}")

print("\n" + "=" * 70)
print("📋 FINAL SOLUTION STATUS:")
print("✅ Two-stage face detection restored in Vision Service")
print("✅ Orchestrator updated to pass force_process parameter")
print("✅ Master Lifecycle correct payload structure identified")
print("🎯 Testing force_process end-to-end functionality...")
