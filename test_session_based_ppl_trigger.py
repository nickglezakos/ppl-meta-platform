#!/usr/bin/env python3
"""
🎯 Session-Based PPL Thread Workflow Trigger Test
=================================================

Test the automatic PPL Thread workflow using session-based media from the analysis document.
Focus on the sessions that should have proper session UUIDs and face data.
"""

import json

import requests

# Configuration
VISION_SERVICE_URL = "http://localhost:8003"
ORCHESTRATOR_URL = "http://localhost:8002"

# Session data from FLUTTER_FACE_COUNT_DATA_FLOW_ANALYSIS.md
SESSION_DATA = [
    {
        "session_uuid": "4e6e625f-47fc-456c-9fc4-8bd0052785e6",
        "media_uuid": "e65e72d4-613d-45de-867e-ce927424b39c",
        "expected_faces": 25,
    },
    {
        "session_uuid": "6475a111-82cf-436f-8834-bc71e1ba3ee6",
        "media_uuid": "1d482eb0-cef3-4cab-936e-ae22b2991b05",
        "expected_faces": 25,
    },
    {
        "session_uuid": "52b71fa4-dd0f-4480-96f0-bf313f43ec3c",
        "media_uuid": "6a0084f8-6ad2-4d41-a84a-72a7630a9cce",
        "expected_faces": 25,
    },
    {
        "session_uuid": "83fcd465-f7f7-4981-bda1-f7c75f3b4c12",
        "media_uuid": "87eff63e-9a5a-4c5e-b1e8-0f033cff5658",
        "expected_faces": 190,
    },
]


def get_auth_token():
    """Get authentication token from saved file."""
    try:
        with open("auth_token.json", "r") as f:
            data = json.load(f)
            return data.get("access_token")
    except Exception as e:
        print(f"❌ Failed to read auth token: {e}")
        return None


def test_session_ppl_workflow(session_data):
    """Test PPL Thread workflow with session-based approach."""
    token = get_auth_token()
    if not token:
        print("❌ No authentication token available")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print("🎯 Testing Session-Based PPL Thread Workflow")
    print("=" * 60)

    for i, session in enumerate(session_data, 1):
        session_uuid = session["session_uuid"]
        media_uuid = session["media_uuid"]
        expected_faces = session["expected_faces"]

        print(f"\n📹 Test {i}: Session {session_uuid[:8]}...")
        print(f"   Media: {media_uuid}")
        print(f"   Expected faces: {expected_faces}")

        # Test 1: Check face data availability
        print(f"\n🔍 Step 1: Check face data...")
        try:
            face_response = requests.get(
                f"{VISION_SERVICE_URL}/faces/media/{media_uuid}",
                headers=headers,
                timeout=10,
            )

            print(f"   Face API status: {face_response.status_code}")

            if face_response.status_code == 200:
                face_data = face_response.json()
                total_faces = face_data.get("total_faces", 0)
                has_stored = face_data.get("has_stored_faces", False)

                print(f"   ✅ Found {total_faces} faces, stored: {has_stored}")

                if total_faces > 0:
                    # Test 2: Trigger PPL Thread workflow with session info
                    print(f"\n🎯 Step 2: Trigger PPL Thread workflow...")

                    # Try with session UUID in payload
                    payload = {"media_id": media_uuid, "session_uuid": session_uuid}

                    print(f"   Payload: {payload}")

                    trigger_response = requests.post(
                        f"{VISION_SERVICE_URL}/api/v1/person-objects/workflow/trigger",
                        json=payload,
                        headers=headers,
                        timeout=60,
                    )

                    print(f"   Trigger status: {trigger_response.status_code}")

                    if trigger_response.status_code == 200:
                        result_data = trigger_response.json()
                        print(f"   🎉 SUCCESS! PPL Thread workflow completed")
                        print(
                            f"      Total persons: {result_data.get('total_persons', 0)}"
                        )

                        # Test 3: Verify Flutter can access person data
                        print(f"\n📱 Step 3: Test Flutter person count access...")

                        person_response = requests.get(
                            f"{ORCHESTRATOR_URL}/person-objects/{media_uuid}",
                            headers=headers,
                            timeout=5,
                        )

                        if person_response.status_code == 200:
                            person_data = person_response.json()
                            person_count = person_data.get("total_persons", 0)
                            print(f"   🎉 Flutter integration SUCCESS!")
                            print(f"      Face count: {total_faces}")
                            print(f"      Person count: {person_count}")

                            if person_count > 0:
                                print(f"\n🎊 COMPLETE SUCCESS FOR SESSION {i}!")
                                print(f"   Face Detection: {total_faces} faces ✅")
                                print(f"   PPL Thread: {person_count} persons ✅")
                                print(f"   Flutter Ready: Both widgets have data ✅")
                                return True
                        else:
                            print(
                                f"   ⚠️  Flutter person data not available: {person_response.status_code}"
                            )
                    else:
                        error_text = trigger_response.text
                        print(f"   ❌ PPL Thread trigger failed: {error_text}")
                else:
                    print(f"   ⚠️  No face data available for this media")
            else:
                print(f"   ❌ Face data not accessible: {face_response.status_code}")

        except Exception as e:
            print(f"   ❌ Error processing session: {e}")

        print(f"   → Moving to next session...")

    print(f"\n⚠️  No sessions produced complete success")
    return False


if __name__ == "__main__":
    print("🎯 SESSION-BASED PPL THREAD WORKFLOW TEST")
    print("🎯 Using session data from FLUTTER_FACE_COUNT_DATA_FLOW_ANALYSIS.md")
    print()

    success = test_session_ppl_workflow(SESSION_DATA)

    print(f"\n" + "=" * 60)
    if success:
        print("🎉 COMPLETE PPL THREAD INTEGRATION SUCCESS!")
        print("   Ready for automatic triggering in production")
    else:
        print("⚠️  PPL THREAD INTEGRATION NEEDS ATTENTION")
        print("   Check session data storage and API endpoints")
    print("=" * 60)
