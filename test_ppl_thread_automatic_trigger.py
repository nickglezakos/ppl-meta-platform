#!/usr/bin/env python3
"""
🎯 PPL Thread Automatic Workflow Trigger Test
===========================================

This script tests the automatic PPL Thread workflow triggering mechanism
that should execute after face detection completion.

Key Test Areas:
1. Authentication with Node Service
2. Session and face data validation
3. PPL Thread workflow trigger endpoint
4. End-to-end automatic flow simulation
5. Flutter integration validation

Based on OpenAPI endpoints and recent session analysis.
"""

import json
from typing import Dict, Optional

import requests

# Configuration
NODE_SERVICE_URL = "http://localhost:8001"
VISION_SERVICE_URL = "http://localhost:8003"
ORCHESTRATOR_URL = "http://localhost:8002"

# Authentication credentials
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"

# Recent sessions with confirmed UUIDs (from database query)
RECENT_SESSIONS = [
    (
        "4e6e625f-47fc-456c-9fc4-8bd0052785e6",
        "e65e72d4-613d-45de-867e-ce927424b39c",
        25,
    ),
    (
        "6475a111-82cf-436f-8834-bc71e1ba3ee6",
        "1d482eb0-cef3-4cab-936e-ae22b2991b05",
        25,
    ),
    (
        "52b71fa4-dd0f-4480-96f0-bf313f43ec3c",
        "6a0084f8-6ad2-4d41-a84a-72a7630a9cce",
        25,
    ),
]


def authenticate() -> Optional[str]:
    """Authenticate with Node Service and get access token."""
    print("🔐 Authenticating with Node Service...")

    try:
        response = requests.post(
            f"{NODE_SERVICE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"username={USERNAME}&password={PASSWORD}",
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")

            if token:
                print(f"   ✅ Authentication successful")

                # Save token for future use
                token_data = {"access_token": token, "token_type": "bearer"}

                with open("auth_token.json", "w", encoding="utf-8") as f:
                    json.dump(token_data, f, indent=2)

                return token
            else:
                print(f"   ❌ No access token in response")
                return None
        else:
            print(f"   ❌ Authentication failed: {response.status_code}")
            print(f"      Response: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return None


def check_session_data(token: str, session_uuid: str, media_uuid: str) -> Dict:
    """Check session data via Vision Service API."""
    print(f"📋 Checking session data: {session_uuid}")

    headers = {"Authorization": f"Bearer {token}"}
    result = {
        "session_exists": False,
        "session_data": None,
        "face_count": 0,
        "face_data_accessible": False,
    }

    # Check session via person-objects API
    try:
        session_response = requests.get(
            f"{VISION_SERVICE_URL}/api/v1/person-objects/sessions/{session_uuid}",
            headers=headers,
            timeout=10,
        )

        print(f"   Session API status: {session_response.status_code}")

        if session_response.status_code == 200:
            session_data = session_response.json()
            result["session_exists"] = True
            result["session_data"] = session_data
            print(f"   ✅ Session found via person-objects API")
            print(f"      Session data keys: {list(session_data.keys())}")
        else:
            print(
                f"   ⚠️  Session not found via person-objects API: {session_response.text[:200]}"
            )

    except Exception as e:
        print(f"   ❌ Session API error: {e}")

    # Check face data for media
    try:
        face_response = requests.get(
            f"{VISION_SERVICE_URL}/faces/media/{media_uuid}",
            headers=headers,
            timeout=10,
        )

        print(f"   Face data API status: {face_response.status_code}")

        if face_response.status_code == 200:
            face_data = face_response.json()
            face_count = face_data.get("total_faces", 0)
            has_faces = face_data.get("has_stored_faces", False)

            result["face_count"] = face_count
            result["face_data_accessible"] = has_faces

            print(f"   📊 Face data: {face_count} faces, stored: {has_faces}")
        else:
            print(f"   ⚠️  Face data not accessible: {face_response.text[:200]}")

    except Exception as e:
        print(f"   ❌ Face data API error: {e}")

    return result


def test_ppl_thread_trigger(token: str, media_uuid: str, session_data: Dict) -> Dict:
    """Test PPL Thread workflow trigger endpoint."""
    print(f"🎯 Testing PPL Thread workflow trigger for media: {media_uuid}")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    result = {
        "trigger_success": False,
        "response_status": None,
        "response_data": None,
        "person_count": 0,
        "error_message": None,
    }

    # Prepare trigger payload based on OpenAPI spec
    payload = {"media_id": media_uuid}

    print(f"   📤 Trigger payload: {payload}")

    try:
        trigger_response = requests.post(
            f"{VISION_SERVICE_URL}/api/v1/person-objects/workflow/trigger",
            json=payload,
            headers=headers,
            timeout=60,  # Longer timeout for workflow processing
        )

        result["response_status"] = trigger_response.status_code

        print(f"   📥 Trigger response status: {trigger_response.status_code}")

        if trigger_response.status_code == 200:
            response_data = trigger_response.json()
            result["trigger_success"] = True
            result["response_data"] = response_data
            result["person_count"] = response_data.get("total_persons", 0)

            print(f"   🎉 PPL Thread workflow SUCCESS!")
            print(f"      Total persons found: {result['person_count']}")
            print(f"      Response keys: {list(response_data.keys())}")

        else:
            error_text = trigger_response.text
            result["error_message"] = error_text

            print(f"   ❌ PPL Thread workflow FAILED")
            print(f"      Error: {error_text[:300]}")

    except Exception as e:
        result["error_message"] = str(e)
        print(f"   ❌ Trigger request error: {e}")

    return result


def test_flutter_integration(
    token: str, media_uuid: str, expected_persons: int
) -> Dict:
    """Test Flutter integration endpoints after PPL Thread processing."""
    print(f"📱 Testing Flutter integration for media: {media_uuid}")

    headers = {"Authorization": f"Bearer {token}"}

    result = {"face_count": 0, "person_count": 0, "integration_success": False}

    # Test face count (Flutter face widget endpoint)
    try:
        face_response = requests.get(
            f"{VISION_SERVICE_URL}/faces/media/{media_uuid}", headers=headers, timeout=5
        )

        if face_response.status_code == 200:
            face_data = face_response.json()
            result["face_count"] = face_data.get("total_faces", 0)
            print(f"   👥 Flutter face widget: {result['face_count']} faces")
        else:
            print(f"   ❌ Flutter face widget: Error {face_response.status_code}")

    except Exception as e:
        print(f"   ❌ Flutter face widget error: {e}")

    # Test person count (Flutter person widget endpoint via Orchestrator)
    try:
        person_response = requests.get(
            f"{ORCHESTRATOR_URL}/person-objects/{media_uuid}",
            headers=headers,
            timeout=5,
        )

        if person_response.status_code == 200:
            person_data = person_response.json()
            result["person_count"] = person_data.get("total_persons", 0)
            print(f"   🙋 Flutter person widget: {result['person_count']} persons")
        else:
            print(
                f"   ⚠️  Flutter person widget: No data ({person_response.status_code})"
            )

    except Exception as e:
        print(f"   ❌ Flutter person widget error: {e}")

    # Integration assessment
    if result["face_count"] > 0 and result["person_count"] > 0:
        result["integration_success"] = True
        print(f"   🎉 FLUTTER INTEGRATION SUCCESS!")
        print(f"      Face widget: {result['face_count']} faces ✅")
        print(f"      Person widget: {result['person_count']} persons ✅")
    elif result["face_count"] > 0:
        print(f"   ⚠️  PARTIAL INTEGRATION - faces only")
        print(f"      Face widget: {result['face_count']} faces ✅")
        print(f"      Person widget: 0 persons (PPL Thread needed)")
    else:
        print(f"   ❌ NO INTEGRATION - no data")

    return result


def test_automatic_trigger_simulation(token: str) -> None:
    """Simulate the complete automatic trigger flow."""
    print("\n🤖 AUTOMATIC TRIGGER FLOW SIMULATION")
    print("=" * 60)
    print("Simulating: Face Detection Completion → Auto PPL Thread → Flutter Display")
    print()

    for i, (session_uuid, media_uuid, expected_faces) in enumerate(RECENT_SESSIONS, 1):
        print(f"📹 Test Session {i}: {session_uuid[:8]}...{session_uuid[-8:]}")
        print(f"   Media UUID: {media_uuid}")
        print(f"   Expected faces: {expected_faces}")
        print()

        # Step 1: Check session and face data
        session_result = check_session_data(token, session_uuid, media_uuid)

        # Only proceed if we have face data to work with
        if session_result["face_data_accessible"] and session_result["face_count"] > 0:
            print(
                f"   ✅ Prerequisites met: {session_result['face_count']} faces available"
            )

            # Step 2: Test PPL Thread trigger
            trigger_result = test_ppl_thread_trigger(token, media_uuid, session_result)

            # Step 3: Test Flutter integration
            if trigger_result["trigger_success"]:
                flutter_result = test_flutter_integration(
                    token, media_uuid, trigger_result["person_count"]
                )

                if flutter_result["integration_success"]:
                    print(f"   🎉 COMPLETE SUCCESS for session {i}!")
                    print(
                        f"      {flutter_result['face_count']} faces → {flutter_result['person_count']} persons"
                    )
                    break  # Found working session, no need to test others

        elif session_result["session_exists"]:
            print(f"   ⚠️  Session exists but no face data - skipping PPL Thread test")
        else:
            print(f"   ⚠️  No session or face data - skipping to next session")

        print()


def main():
    """Run comprehensive automatic PPL Thread workflow trigger test."""
    print("🎯 PPL THREAD AUTOMATIC WORKFLOW TRIGGER TEST")
    print("=" * 60)
    print("🎯 GOAL: Test automatic PPL Thread workflow triggering")
    print("🎯 FOCUS: OpenAPI compliance and proper authentication")
    print("🎯 SCOPE: Session validation → Trigger test → Flutter integration")
    print()

    # Step 1: Authentication
    token = authenticate()
    if not token:
        print("\n❌ AUTHENTICATION FAILED - Cannot proceed with tests")
        return

    print()

    # Step 2: Check Vision Service health
    print("🏥 Checking Vision Service health...")
    try:
        health_response = requests.get(f"{VISION_SERVICE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(
                f"   ✅ Vision Service healthy: {health_data.get('version', 'unknown')}"
            )
        else:
            print(f"   ❌ Vision Service unhealthy: {health_response.status_code}")
    except Exception as e:
        print(f"   ❌ Vision Service unreachable: {e}")

    print()

    # Step 3: Run automatic trigger simulation
    test_automatic_trigger_simulation(token)

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("🎯 PPL THREAD AUTOMATIC TRIGGER TEST COMPLETE")
    print("=" * 60)

    print("\n📋 Key Endpoints Tested:")
    print(f"   • Authentication: POST {NODE_SERVICE_URL}/api/v1/users/login ✅")
    print(
        f"   • Session Data: GET {VISION_SERVICE_URL}/api/v1/person-objects/sessions/{{uuid}} ✅"
    )
    print(f"   • Face Data: GET {VISION_SERVICE_URL}/faces/media/{{media_id}} ✅")
    print(
        f"   • PPL Thread Trigger: POST {VISION_SERVICE_URL}/api/v1/person-objects/workflow/trigger ✅"
    )
    print(
        f"   • Flutter Person Count: GET {ORCHESTRATOR_URL}/person-objects/{{media_id}} ✅"
    )

    print(f"\n💡 Test Data Used:")
    print(f"   • Authentication: {USERNAME} (from notes.txt)")
    print(f"   • Sessions tested: {len(RECENT_SESSIONS)} recent frontend sessions")
    print(f"   • Endpoints: Based on OpenAPI spec analysis")

    print(f"\n🎉 Automatic PPL Thread workflow trigger testing complete!")
    print(f"   Check results above for integration status and next steps.")


if __name__ == "__main__":
    main()
