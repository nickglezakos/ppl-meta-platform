#!/usr/bin/env python3
"""
Test script to verify duplicate face detection prevention is working.

This script tests the duplicate prevention mechanism by:
1. Checking if there are existing face detections for a media file
2. Testing the Vision Service duplicate prevention endpoint
3. Testing the Media Service workflow duplicate prevention
"""

import asyncio
import json
import time

import requests

# Configuration
VISION_SERVICE_URL = "http://localhost:8003"
ORCHESTRATOR_URL = "http://localhost:8002"
GATEWAY_URL = "http://localhost:8080"
TEST_MEDIA_ID = (
    "656d4cca-9444-41d6-84df-1ee111789f2a"  # Our test media with known duplicates
)

# Test authentication token (replace with valid token)
AUTH_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU5MDgxODI2fQ.WaM5oX_-s7CXFbPGxd98FjAvR-6aCQgddhri8m1LFZw"
}


def test_vision_service_duplicate_prevention():
    """Test Vision Service duplicate prevention."""
    print("🔍 Testing Vision Service Duplicate Prevention")
    print("=" * 50)

    # First, check existing faces
    print(f"Checking existing faces for media: {TEST_MEDIA_ID}")
    response = requests.get(
        f"{VISION_SERVICE_URL}/faces/media/{TEST_MEDIA_ID}", headers=AUTH_HEADERS
    )

    if response.status_code == 200:
        data = response.json()
        face_count = data.get("total_faces", 0)
        has_stored = data.get("has_stored_faces", False)
        print(
            f"✅ Found {face_count} existing face detections (has_stored: {has_stored})"
        )

        if face_count > 0:
            print("🔄 Testing bulk processing with existing data (should be skipped)")

            # Test bulk processing (should be prevented)
            bulk_response = requests.post(
                f"{VISION_SERVICE_URL}/faces/media/{TEST_MEDIA_ID}/bulk-process",
                headers=AUTH_HEADERS,
                params={"force_process": False},  # Don't force processing
            )

            if bulk_response.status_code == 200:
                bulk_data = bulk_response.json()
                if bulk_data.get("skipped_processing", False):
                    print(
                        "✅ SUCCESS: Vision Service correctly prevented duplicate processing"
                    )
                    print(f"   - Message: {bulk_data.get('message', 'N/A')}")
                    print(
                        f"   - Duplicate Prevention: {bulk_data.get('duplicate_prevention', False)}"
                    )
                else:
                    print("❌ WARNING: Processing was not skipped as expected")
            else:
                print(
                    f"❌ ERROR: Bulk processing request failed: {bulk_response.status_code}"
                )
                print(f"   Response: {bulk_response.text}")
        else:
            print("ℹ️  No existing faces found - would proceed with normal processing")
    else:
        print(f"❌ ERROR: Failed to check existing faces: {response.status_code}")
        print(f"   Response: {response.text}")

    print()


def test_orchestrator_workflow_duplicate_prevention():
    """Test Orchestrator workflow duplicate prevention via Media Service."""
    print("🔍 Testing Orchestrator Workflow Duplicate Prevention")
    print("=" * 50)

    # Test starting a new workflow (should detect existing data)
    print(f"Starting face detection workflow for media: {TEST_MEDIA_ID}")

    workflow_payload = {"media_ids": [TEST_MEDIA_ID], "methods": ["two_stage"]}

    response = requests.post(
        f"{ORCHESTRATOR_URL}/workflows/face-detection/bulk-process",
        headers=AUTH_HEADERS,
        json=workflow_payload,
    )

    if response.status_code == 200:
        workflow_data = response.json()
        workflow_id = workflow_data.get("workflow_id")
        print(f"✅ Workflow started: {workflow_id}")

        # Monitor workflow progress (should complete quickly if duplicates prevented)
        print("🔄 Monitoring workflow progress...")
        max_checks = 10
        check_count = 0

        while check_count < max_checks:
            time.sleep(2)  # Wait 2 seconds between checks

            status_response = requests.get(
                f"{ORCHESTRATOR_URL}/workflows/face-detection/status/{workflow_id}",
                headers=AUTH_HEADERS,
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                workflow_status = status_data.get("status", "unknown")
                progress = status_data.get("progress", 0)

                print(f"   - Status: {workflow_status}, Progress: {progress}%")

                if workflow_status in ["completed", "failed"]:
                    if workflow_status == "completed":
                        print("✅ Workflow completed")

                        # Check if it was due to duplicate prevention
                        metadata = status_data.get("metadata", {})
                        if "duplicate_prevention" in str(metadata):
                            print(
                                "✅ SUCCESS: Duplicate prevention detected in workflow"
                            )
                        else:
                            print(
                                "ℹ️  Workflow completed normally (no duplicate prevention triggered)"
                            )
                    else:
                        print(
                            f"❌ Workflow failed: {status_data.get('error', 'Unknown error')}"
                        )
                    break
            else:
                print(
                    f"❌ Failed to get workflow status: {status_response.status_code}"
                )
                break

            check_count += 1

        if check_count >= max_checks:
            print("⏰ Workflow monitoring timed out")
    else:
        print(f"❌ ERROR: Failed to start workflow: {response.status_code}")
        print(f"   Response: {response.text}")

    print()


def check_current_duplicates():
    """Check current duplicate state in database."""
    print("🔍 Checking Current Duplicate Status")
    print("=" * 50)

    # Get person objects to see current state
    response = requests.get(
        f"{GATEWAY_URL}/api/v1/orchestrator/person-objects/{TEST_MEDIA_ID}",
        headers=AUTH_HEADERS,
    )

    if response.status_code == 200:
        data = response.json()
        total_faces = data.get("total_faces", 0)
        total_persons = data.get("total_persons", 0)

        print(f"Current state for media {TEST_MEDIA_ID}:")
        print(f"   - Total Faces: {total_faces}")
        print(f"   - Total Persons: {total_persons}")

        # If we still have duplicates, they should be exactly double what they should be
        if total_faces > 0:
            expected_faces = total_faces // 2  # Assuming exactly 2x duplicates
            print(f"   - Expected Faces (if duplicates removed): {expected_faces}")

            if total_faces % 2 == 0:
                print("ℹ️  Face count is even - consistent with 2x duplicate pattern")
            else:
                print("⚠️  Face count is odd - unexpected duplicate pattern")

    else:
        print(f"❌ Failed to get current person objects: {response.status_code}")
        print(f"   Response: {response.text}")

    print()


def main():
    """Run all duplicate prevention tests."""
    print("🚀 PPL Meta Platform - Duplicate Face Detection Prevention Test")
    print("=" * 70)
    print()

    # Check current state
    check_current_duplicates()

    # Test Vision Service duplicate prevention
    test_vision_service_duplicate_prevention()

    # Test Orchestrator workflow duplicate prevention
    test_orchestrator_workflow_duplicate_prevention()

    print("🏁 Duplicate Prevention Testing Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
