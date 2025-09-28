#!/usr/bin/env python3
"""
🎯 PPL Thread Workflow Test with REAL Face Data
==============================================

This script tests the complete automatic PPL Thread workflow using REAL media IDs
that have existing face detection data in the PostgreSQL database.

Key Findings from Analysis:
- PostgreSQL database: ppl_vision_db
- Table: face_detections
- Top media with faces: 87eff63e-9a5a-4c5e-b1e8-0f033cff5658 (190 faces)
"""

import json
import time
from pathlib import Path

import requests

# Configuration
VISION_SERVICE_URL = "http://localhost:8003"
ORCHESTRATOR_URL = "http://localhost:8002"

# Real media IDs with confirmed face data (from PostgreSQL query)
REAL_MEDIA_IDS = [
    ("87eff63e-9a5a-4c5e-b1e8-0f033cff5658", 190),  # 190 faces
    ("f7dfeab9-01d6-46dc-af3c-bbd74e9af560", 52),  # 52 faces
    ("436b948c-e828-4d36-a08e-a1a0ff3508f2", 35),  # 35 faces
    ("3dce7d1e-a539-47bc-b2d0-a4ba3b391e3f", 26),  # 26 faces
    ("94299a9b-5fa8-41a0-aeba-dd10c5413576", 24),  # 24 faces
]


def get_auth_token():
    """Get authentication token for API calls."""
    try:
        # Read cached token
        token_file = Path("auth_token.json")
        if token_file.exists():
            with open(token_file, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("access_token")
    except Exception as e:
        print(f"Warning: Could not read auth token: {e}")

    return None


def test_face_data_retrieval(auth_token):
    """Test retrieving face data for real media IDs."""
    print("🔍 Testing Face Data Retrieval from Vision Service")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    successful_media = []

    for media_id, expected_faces in REAL_MEDIA_IDS:
        print(f"\n📹 Testing Media: {media_id}")
        print(f"   Expected faces: {expected_faces}")

        try:
            # Test Vision Service face retrieval (what Flutter uses)
            response = requests.get(
                f"{VISION_SERVICE_URL}/faces/media/{media_id}",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                total_faces = data.get("total_faces", 0)
                has_stored_faces = data.get("has_stored_faces", False)

                print(f"   ✅ Vision Service Response:")
                print(f"      Total faces: {total_faces}")
                print(f"      Has stored faces: {has_stored_faces}")
                print(f"      Matches expected: {total_faces == expected_faces}")

                if has_stored_faces and total_faces > 0:
                    successful_media.append((media_id, total_faces))

            elif response.status_code == 401:
                print(f"   ❌ Authentication required: {response.status_code}")
                break
            else:
                print(f"   ❌ Vision Service error: {response.status_code}")
                print(f"      Response: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Connection error: {e}")

    return successful_media


def test_ppl_thread_workflow(auth_token, media_id, face_count):
    """Test PPL Thread workflow for a specific media ID."""
    print(f"\n🎯 Testing PPL Thread Workflow for Media: {media_id}")
    print(f"   Face count: {face_count}")

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Step 1: Check if PPL Thread data already exists
    print("   1️⃣ Checking existing PPL Thread data...")
    try:
        response = requests.get(
            f"{ORCHESTRATOR_URL}/person-objects/{media_id}", headers=headers, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            total_persons = data.get("total_persons", 0)
            status = data.get("status", "unknown")

            print(f"      ✅ Existing PPL Thread data found:")
            print(f"         Total persons: {total_persons}")
            print(f"         Status: {status}")

            if total_persons > 0:
                print(
                    f"      🎉 SUCCESS: PPL Thread workflow has processed this media!"
                )
                print(f"         {face_count} faces → {total_persons} persons")
                return True
            else:
                print(f"      ⚠️  PPL Thread data exists but no persons found")

        elif response.status_code == 404:
            print(
                f"      ℹ️  No existing PPL Thread data - this is normal for unprocessed media"
            )
        else:
            print(f"      ❌ Orchestrator error: {response.status_code}")
            print(f"         Response: {response.text[:200]}")

    except Exception as e:
        print(f"      ❌ Orchestrator connection error: {e}")

    # Step 2: Trigger PPL Thread workflow manually
    print("   2️⃣ Triggering PPL Thread workflow...")
    try:
        response = requests.post(
            f"{VISION_SERVICE_URL}/api/v1/person-objects/auto-trigger",
            json={"media_id": media_id},
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            total_persons = result.get("total_persons", 0)

            print(f"      ✅ PPL Thread workflow completed:")
            print(f"         Total persons: {total_persons}")
            print(f"         Conversion: {face_count} faces → {total_persons} persons")

            return True

        else:
            print(f"      ❌ PPL Thread trigger failed: {response.status_code}")
            print(f"         Response: {response.text[:200]}")

    except Exception as e:
        print(f"      ❌ PPL Thread trigger error: {e}")

    return False


def test_flutter_integration(auth_token, media_id):
    """Test the exact API calls Flutter makes."""
    print(f"\n📱 Testing Flutter Integration for Media: {media_id}")

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    # Step 1: Face count (what Flutter's face widget does)
    print("   1️⃣ Testing face count retrieval...")
    try:
        response = requests.get(
            f"{VISION_SERVICE_URL}/faces/media/{media_id}", headers=headers, timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            face_count = data.get("total_faces", 0)
            print(f"      ✅ Flutter face count: {face_count}")
        else:
            print(f"      ❌ Flutter face count failed: {response.status_code}")
            face_count = 0

    except Exception as e:
        print(f"      ❌ Flutter face count error: {e}")
        face_count = 0

    # Step 2: Person count (what Flutter's person widget does)
    print("   2️⃣ Testing person count retrieval...")
    try:
        response = requests.get(
            f"{ORCHESTRATOR_URL}/person-objects/{media_id}", headers=headers, timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            person_count = data.get("total_persons", 0)
            print(f"      ✅ Flutter person count: {person_count}")
        else:
            print(f"      ❌ Flutter person count: 0 (no data)")
            person_count = 0

    except Exception as e:
        print(f"      ❌ Flutter person count error: {e}")
        person_count = 0

    # Summary
    if face_count > 0 and person_count > 0:
        print(f"      🎉 FLUTTER INTEGRATION SUCCESS!")
        print(f"         Face widget shows: {face_count} faces")
        print(f"         Person widget shows: {person_count} persons")
        return True
    elif face_count > 0 and person_count == 0:
        print(f"      ⚠️  FLUTTER SHOWS: {face_count} faces, 0 persons")
        print(
            f"         This means PPL Thread workflow hasn't processed this media yet"
        )
        print(f"         The automatic workflow integration should fix this!")
        return False
    else:
        print(f"      ❌ FLUTTER INTEGRATION ISSUE")
        return False


def main():
    """Run comprehensive PPL Thread workflow test with real data."""
    print("🎯 PPL Thread Workflow Test with REAL Face Data")
    print("=" * 60)
    print()
    print("📋 Testing Plan:")
    print("1. Authenticate with platform")
    print("2. Test face data retrieval for real media IDs")
    print("3. Test PPL Thread workflow processing")
    print("4. Validate Flutter integration")
    print("5. Test automatic workflow integration")
    print()

    # Step 1: Authentication
    auth_token = get_auth_token()
    if not auth_token:
        print("❌ No authentication token found!")
        print(
            "   Please run: curl -X POST 'http://localhost:8001/api/v1/users/login' \\"
        )
        print("     -H 'Content-Type: application/x-www-form-urlencoded' \\")
        print("     -d 'username=fresh.user@example.com&password=NewPassword234!'")
        return

    print(f"✅ Authentication token loaded")
    print()

    # Step 2: Test face data retrieval
    successful_media = test_face_data_retrieval(auth_token)

    if not successful_media:
        print("\n❌ No media with face data could be retrieved!")
        print("   This suggests an authentication or API issue.")
        return

    print(f"\n✅ Found {len(successful_media)} media IDs with accessible face data")
    print()

    # Step 3: Test PPL Thread workflow with top media
    test_media_id, test_face_count = successful_media[0]  # Use media with most faces

    workflow_success = test_ppl_thread_workflow(
        auth_token, test_media_id, test_face_count
    )

    # Step 4: Test Flutter integration
    flutter_success = test_flutter_integration(auth_token, test_media_id)

    # Step 5: Final summary
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)

    print(f"✅ Face data retrieval: {len(successful_media)}/5 media IDs accessible")
    print(
        f"{'✅' if workflow_success else '❌'} PPL Thread workflow: {'Working' if workflow_success else 'Needs attention'}"
    )
    print(
        f"{'✅' if flutter_success else '⚠️'} Flutter integration: {'Complete' if flutter_success else 'Faces only - needs PPL Thread'}"
    )

    if workflow_success and flutter_success:
        print("\n🎉 FULL INTEGRATION SUCCESS!")
        print("   • Face detection data: ✅ Available")
        print("   • PPL Thread workflows: ✅ Processing faces → persons")
        print("   • Flutter integration: ✅ Shows both face and person counts")
        print("   • Automatic workflows: ✅ Ready to test")
    elif len(successful_media) > 0:
        print("\n⚠️  PARTIAL SUCCESS - Ready for automatic workflow integration")
        print("   • Face detection data: ✅ Available")
        print("   • PPL Thread workflows: 🔄 Can be triggered")
        print("   • Flutter integration: ✅ Shows face counts, ready for person counts")
        print("   • Next step: Test automatic PPL Thread trigger after face detection")
    else:
        print("\n❌ INTEGRATION ISSUES DETECTED")
        print("   Please check authentication and service connectivity")

    print(f"\n📋 Test media ID for further testing: {test_media_id}")
    print(f"   Face count: {test_face_count}")
    print(f"   Use this media ID to test the automatic workflow integration!")


if __name__ == "__main__":
    main()
