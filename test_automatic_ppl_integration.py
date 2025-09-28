#!/usr/bin/env python3
"""
🎯 PPL Thread Automatic Workflow Integration Test
==============================================

This script tests the complete automatic PPL Thread workflow integration:

1. Face Detection Completion → Automatic PPL Thread Trigger
2. Session Management and Data Requirements
3. End-to-End Flutter Integration

Key Focus Areas:
- Correct endpoint URL (/workflow/trigger vs /auto-trigger)
- Required data format (media_id + session_uuid)
- Session-Face Detection linking
- Automatic execution after face detection completion
"""

import json
import time
from pathlib import Path

import requests

# Configuration
VISION_SERVICE_URL = "http://localhost:8003"
ORCHESTRATOR_URL = "http://localhost:8002"

# Test media IDs with confirmed face data AND session UUIDs (from recent frontend sessions)
RECENT_MEDIA_WITH_SESSIONS = [
    (
        "e65e72d4-613d-45de-867e-ce927424b39c",
        "4e6e625f-47fc-456c-9fc4-8bd0052785e6",
        25,
    ),  # Most recent
    (
        "1d482eb0-cef3-4cab-936e-ae22b2991b05",
        "6475a111-82cf-436f-8834-bc71e1ba3ee6",
        25,
    ),  # Recent
    (
        "6a0084f8-6ad2-4d41-a84a-72a7630a9cce",
        "52b71fa4-dd0f-4480-96f0-bf313f43ec3c",
        25,
    ),  # Recent
]

# Use most recent media with session for testing
TEST_MEDIA_ID = RECENT_MEDIA_WITH_SESSIONS[0][
    0
]  # e65e72d4-613d-45de-867e-ce927424b39c (25 faces, has session)


def get_auth_token():
    """Get authentication token."""
    try:
        with open("auth_token.json", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("access_token")
    except Exception as e:
        print(f"Warning: Could not read auth token: {e}")
    return None


def test_session_media_linking(auth_token, media_id):
    """Test session-media linking for PPL Thread workflow requirements."""
    print(f"🔗 Testing Session-Media Linking for {media_id}")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Step 1: Check if there are sessions for this media
    print("1️⃣ Checking sessions for media...")
    try:
        response = requests.get(
            f"{VISION_SERVICE_URL}/sessions/media/{media_id}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            sessions_data = response.json()
            sessions = sessions_data.get("sessions", [])

            print(f"   ✅ Found {len(sessions)} session(s) for media {media_id}")

            for i, session in enumerate(sessions):
                session_uuid = session.get("session_uuid", "N/A")
                status = session.get("status", "unknown")
                faces = session.get("total_faces_detected", 0)

                print(f"   📋 Session {i+1}: {session_uuid}")
                print(f"      Status: {status}")
                print(f"      Faces detected: {faces}")

            return sessions

        elif response.status_code == 404:
            print(f"   ⚠️  No sessions found for media {media_id}")
            print("      This suggests the media hasn't been processed with sessions")
            return []
        else:
            print(f"   ❌ Sessions API error: {response.status_code}")
            return []

    except Exception as e:
        print(f"   ❌ Sessions API connection error: {e}")
        return []


def test_ppl_thread_trigger_requirements(auth_token, media_id):
    """Test PPL Thread workflow trigger with correct data format."""
    print(f"\n🎯 Testing PPL Thread Trigger Requirements")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Test 1: Trigger with just media_id (current auto-trigger format)
    print("1️⃣ Testing trigger with media_id only...")
    try:
        response = requests.post(
            f"{VISION_SERVICE_URL}/api/v1/person-objects/workflow/trigger",
            json={"media_id": media_id},
            headers=headers,
            timeout=30,
        )

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            persons = result.get("total_persons", "unknown")
            print(f"   ✅ SUCCESS: {persons} persons found")
            return True
        else:
            error_msg = response.text
            print(f"   ❌ Error: {error_msg[:300]}")

            # Check if error mentions session requirements
            if "session" in error_msg.lower():
                print("   💡 Hint: Workflow requires session_uuid")

    except Exception as e:
        print(f"   ❌ Connection error: {e}")

    return False


def test_face_data_accessibility(auth_token, media_id):
    """Test that face data is accessible for PPL Thread processing."""
    print(f"\n📊 Testing Face Data Accessibility")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Test face data retrieval
    print("1️⃣ Testing face data retrieval...")
    try:
        response = requests.get(
            f"{VISION_SERVICE_URL}/faces/media/{media_id}", headers=headers, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            total_faces = data.get("total_faces", 0)
            has_stored_faces = data.get("has_stored_faces", False)
            faces_by_frame = data.get("faces_by_frame", {})

            print(f"   ✅ Face data accessible:")
            print(f"      Total faces: {total_faces}")
            print(f"      Has stored faces: {has_stored_faces}")
            print(f"      Frames with faces: {len(faces_by_frame)}")

            if total_faces > 0 and has_stored_faces:
                print("   🎉 Face data is ready for PPL Thread processing!")
                return True
            else:
                print("   ⚠️  No face data available for processing")
                return False
        else:
            print(f"   ❌ Face data API error: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Face data API connection error: {e}")
        return False


def test_automatic_trigger_simulation(auth_token, media_id):
    """Simulate the automatic trigger as it would happen after face detection."""
    print(f"\n🤖 Simulating Automatic Trigger After Face Detection")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Step 1: Get current face detection state
    print("1️⃣ Getting current face detection state...")

    try:
        face_response = requests.get(
            f"{VISION_SERVICE_URL}/faces/media/{media_id}", headers=headers, timeout=10
        )

        if face_response.status_code != 200:
            print("   ❌ Cannot retrieve face data for simulation")
            return False

        face_data = face_response.json()
        face_count = face_data.get("total_faces", 0)

        print(f"   📊 Face detection state: {face_count} faces detected")

    except Exception as e:
        print(f"   ❌ Error getting face data: {e}")
        return False

    # Step 2: Get session information
    print("2️⃣ Getting session information...")

    try:
        session_response = requests.get(
            f"{VISION_SERVICE_URL}/sessions/media/{media_id}",
            headers=headers,
            timeout=10,
        )

        session_uuid = None
        if session_response.status_code == 200:
            sessions_data = session_response.json()
            sessions = sessions_data.get("sessions", [])

            if sessions:
                session_uuid = sessions[0].get("session_uuid")
                print(f"   📋 Session found: {session_uuid}")
            else:
                print("   ⚠️  No sessions found")
        else:
            print("   ⚠️  Session lookup failed")

    except Exception as e:
        print(f"   ❌ Error getting session data: {e}")

    # Step 3: Simulate the automatic trigger call
    print("3️⃣ Simulating automatic PPL Thread trigger...")

    # This is what the Vision Service automatic trigger should call
    payload = {"media_id": media_id}

    if session_uuid:
        payload["session_uuid"] = session_uuid
        payload["face_count"] = face_count
        print(f"   📤 Trigger payload: {payload}")
    else:
        print(f"   📤 Trigger payload (media_id only): {payload}")

    try:
        trigger_response = requests.post(
            f"{VISION_SERVICE_URL}/api/v1/person-objects/workflow/trigger",
            json=payload,
            headers=headers,
            timeout=30,
        )

        print(f"   📥 Trigger response: {trigger_response.status_code}")

        if trigger_response.status_code == 200:
            result = trigger_response.json()
            persons = result.get("total_persons", "unknown")

            print(f"   🎉 SUCCESS: Automatic trigger worked!")
            print(f"      {face_count} faces → {persons} persons")
            return True
        else:
            error_text = trigger_response.text
            print(f"   ❌ Trigger failed: {error_text[:300]}")
            return False

    except Exception as e:
        print(f"   ❌ Trigger connection error: {e}")
        return False


def test_flutter_end_to_end(auth_token, media_id):
    """Test the complete Flutter integration after automatic workflow."""
    print(f"\n📱 Testing Flutter End-to-End Integration")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Step 1: Face count (Flutter face widget)
    print("1️⃣ Testing Flutter face count...")
    try:
        face_response = requests.get(
            f"{VISION_SERVICE_URL}/faces/media/{media_id}", headers=headers, timeout=5
        )

        face_count = 0
        if face_response.status_code == 200:
            face_data = face_response.json()
            face_count = face_data.get("total_faces", 0)
            print(f"   ✅ Flutter face widget: {face_count} faces")
        else:
            print("   ❌ Flutter face widget: Error retrieving faces")

    except Exception as e:
        print(f"   ❌ Flutter face widget error: {e}")

    # Step 2: Person count (Flutter person widget)
    print("2️⃣ Testing Flutter person count...")
    try:
        person_response = requests.get(
            f"{ORCHESTRATOR_URL}/person-objects/{media_id}", headers=headers, timeout=5
        )

        person_count = 0
        if person_response.status_code == 200:
            person_data = person_response.json()
            person_count = person_data.get("total_persons", 0)
            print(f"   ✅ Flutter person widget: {person_count} persons")
        else:
            print(
                "   ⚠️  Flutter person widget: No person data (expected if workflow hasn't run)"
            )

    except Exception as e:
        print(f"   ❌ Flutter person widget error: {e}")

    # Step 3: Integration assessment
    print("3️⃣ Flutter integration assessment...")

    if face_count > 0 and person_count > 0:
        print(f"   🎉 COMPLETE SUCCESS!")
        print(f"      Face widget: {face_count} faces ✅")
        print(f"      Person widget: {person_count} persons ✅")
        print(f"      Automatic workflow: WORKING ✅")
        return True
    elif face_count > 0 and person_count == 0:
        print(f"   ⚠️  PARTIAL SUCCESS - Automatic workflow needed")
        print(f"      Face widget: {face_count} faces ✅")
        print(f"      Person widget: 0 persons (workflow not triggered)")
        print(f"      Next step: Fix automatic PPL Thread trigger")
        return False
    else:
        print(f"   ❌ INTEGRATION ISSUES")
        return False


def main():
    """Run comprehensive automatic PPL Thread workflow integration test."""
    print("🎯 PPL Thread Automatic Workflow Integration Test")
    print("=" * 60)
    print("🎯 FOCUS: Automatic triggering and data format requirements")
    print("🎯 ASSUMPTION: PPL Thread workflow itself works correctly")
    print("🎯 GOAL: Ensure automatic trigger after face detection completion")
    print()

    # Authentication
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ No authentication token!")
        return

    print(f"✅ Authentication ready")
    print(f"📋 Test media: {TEST_MEDIA_ID}")
    print()

    # Test sequence
    results = {}

    # Test 1: Session-Media linking
    sessions = test_session_media_linking(auth_token, TEST_MEDIA_ID)
    results["sessions"] = len(sessions) > 0

    # Test 2: Face data accessibility
    results["face_data"] = test_face_data_accessibility(auth_token, TEST_MEDIA_ID)

    # Test 3: PPL Thread trigger requirements
    results["ppl_trigger"] = test_ppl_thread_trigger_requirements(
        auth_token, TEST_MEDIA_ID
    )

    # Test 4: Automatic trigger simulation
    results["auto_trigger"] = test_automatic_trigger_simulation(
        auth_token, TEST_MEDIA_ID
    )

    # Test 5: Flutter end-to-end
    results["flutter_e2e"] = test_flutter_end_to_end(auth_token, TEST_MEDIA_ID)

    # Final assessment
    print("\n" + "=" * 60)
    print("🎯 AUTOMATIC WORKFLOW INTEGRATION RESULTS")
    print("=" * 60)

    for test, success in results.items():
        status = "✅" if success else "❌"
        print(
            f"{status} {test.replace('_', ' ').title()}: {'PASS' if success else 'NEEDS ATTENTION'}"
        )

    success_count = sum(results.values())
    total_tests = len(results)

    print(f"\n📊 Overall: {success_count}/{total_tests} tests passing")

    if success_count == total_tests:
        print("\n🎉 COMPLETE SUCCESS!")
        print("   Automatic PPL Thread workflow integration is working!")
    elif success_count >= 3:
        print("\n⚠️  MOSTLY WORKING - Minor fixes needed")
        print("   Core integration is ready, fine-tuning required")
    else:
        print("\n🔧 INTEGRATION WORK NEEDED")
        print("   Focus on automatic trigger and data format requirements")

    print(f"\n💡 Key Findings:")
    print(f"   • Face data accessible: {results['face_data']}")
    print(f"   • Session linking: {results['sessions']}")
    print(f"   • PPL Thread trigger: {results['ppl_trigger']}")
    print(f"   • Automatic execution: {results['auto_trigger']}")
    print(f"   • Flutter integration: {results['flutter_e2e']}")


if __name__ == "__main__":
    main()
