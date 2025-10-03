#!/usr/bin/env python3
"""
Test script for the Vi    # Step 2: Test duplicate prevention with force_process=false (default)
    print()
    print("2️⃣ Testing duplicate prevention (force_process=false)")
    try:
        # FIXED: Use query parameters, not JSON body
        prevention_url = f"http://localhost:8003/faces/media/{media_id}/bulk-process?frame_interval=15&max_frames=10&force_process=false&create_session=false"

        start_time = time.time()
        prevention_response = requests.post(
            prevention_url,
            headers=headers,
            timeout=30,
        )cate prevention fix.

This script tests the FIXED duplicate prevention logic in the Vision Service
bulk-process endpoint to ensure it properly prevents duplicate face storage.
"""

import json
import sys
import time

import requests


def test_duplicate_prevention_fix():
    """Test the fixed duplicate prevention logic."""

    print("🧪 TESTING VISION SERVICE DUPLICATE PREVENTION FIX")
    print("=" * 60)

    # Configuration
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU5MDg4MDA1fQ.Q0ZLtkGGDk0uDy0CE4uPzhO7tBZfJr2yXM-j-UQYrIY"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    media_id = "0f840231-70f9-4949-bb9a-94d328fe9839"  # Known media with duplicates

    print(f"📋 Test Configuration:")
    print(f"   Media ID: {media_id}")
    print(f"   Expected: Duplicate prevention should work correctly")
    print()

    # Step 1: Check current face count in database
    print("1️⃣ Checking current face count in database")
    try:
        face_response = requests.get(
            f"http://localhost:8003/faces/media/{media_id}", headers=headers, timeout=10
        )

        if face_response.status_code == 200:
            face_data = face_response.json()
            current_count = face_data.get("total_faces", 0)
            print(f"   ✅ Current face count: {current_count} faces")
        else:
            print(f"   ❌ Failed to get face count: {face_response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error getting face count: {e}")
        return False

    # Step 2: Test duplicate prevention with force_process=false (default)
    print()
    print("2️⃣ Testing duplicate prevention (force_process=false)")
    try:
        bulk_process_data = {
            "frame_interval": 15,
            "max_frames": 10,
            "force_process": False,  # This should trigger duplicate prevention
            "create_session": False,
        }

        start_time = time.time()
        prevention_response = requests.post(
            f"http://localhost:8003/faces/media/{media_id}/bulk-process",
            headers=headers,
            json=bulk_process_data,
            timeout=30,
        )
        response_time = time.time() - start_time

        if prevention_response.status_code == 200:
            prevention_data = prevention_response.json()

            if prevention_data.get("duplicate_prevention") and prevention_data.get(
                "skipped_processing"
            ):
                print(f"   ✅ DUPLICATE PREVENTION SUCCESS!")
                print(f"   📋 Response: {prevention_data.get('message', 'No message')}")
                print(f"   ⚡ Response time: {response_time:.2f}s (fast = good)")
                print(f"   🛡️ Prevented duplicate processing as expected")

                # Verify existing results structure
                existing_results = prevention_data.get("existing_results", {})
                total_faces = existing_results.get("total_faces", 0)
                print(f"   📊 Reported existing faces: {total_faces}")

                if total_faces == current_count:
                    print(f"   ✅ Count matches database query result")
                else:
                    print(
                        f"   ⚠️ Count mismatch: API reports {total_faces}, DB has {current_count}"
                    )

            else:
                print(f"   ❌ DUPLICATE PREVENTION FAILED!")
                print(
                    f"   📋 duplicate_prevention: {prevention_data.get('duplicate_prevention')}"
                )
                print(
                    f"   📋 skipped_processing: {prevention_data.get('skipped_processing')}"
                )
                print(f"   🚨 This indicates the fix didn't work properly")
                return False

        else:
            print(f"   ❌ HTTP Error: {prevention_response.status_code}")
            print(f"   📋 Response: {prevention_response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error testing duplicate prevention: {e}")
        return False

    # Step 3: Test force processing override
    print()
    print("3️⃣ Testing force processing override (force_process=true)")
    try:
        # FIXED: force_process is a query parameter, not JSON body parameter
        force_url = f"http://localhost:8003/faces/media/{media_id}/bulk-process?frame_interval=15&max_frames=3&force_process=true&create_session=false"

        start_time = time.time()
        force_response = requests.post(
            force_url,
            headers=headers,
            timeout=30,
        )
        response_time = time.time() - start_time

        if force_response.status_code == 200:
            force_data = force_response.json()

            if not force_data.get("duplicate_prevention"):
                print(f"   ✅ FORCE PROCESSING SUCCESS!")
                print(
                    f"   📋 Processed {force_data.get('total_faces_detected', 0)} faces"
                )
                print(f"   ⚡ Processing time: {response_time:.2f}s")
                print(f"   🔧 Override worked as expected")
            else:
                print(f"   ❌ FORCE PROCESSING FAILED!")
                print(
                    f"   📋 duplicate_prevention still active: {force_data.get('duplicate_prevention')}"
                )
                return False

        else:
            print(f"   ❌ HTTP Error: {force_response.status_code}")
            print(f"   📋 Response: {force_response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error testing force processing: {e}")
        return False

    # Step 4: Verify duplicate prevention still works after force processing
    print()
    print("4️⃣ Re-testing duplicate prevention after force processing")
    try:
        # FIXED: Use query parameters, not JSON body
        retest_url = f"http://localhost:8003/faces/media/{media_id}/bulk-process?force_process=false&create_session=false"
        retest_response = requests.post(
            retest_url,
            headers=headers,
            timeout=30,
        )

        if retest_response.status_code == 200:
            retest_data = retest_response.json()

            if retest_data.get("duplicate_prevention") and retest_data.get(
                "skipped_processing"
            ):
                print(f"   ✅ DUPLICATE PREVENTION STILL WORKING!")
                print(f"   📋 Successfully prevented processing again")

                # Check if face count increased from force processing
                new_existing_results = retest_data.get("existing_results", {})
                new_total_faces = new_existing_results.get("total_faces", 0)

                if new_total_faces > current_count:
                    print(
                        f"   📊 Face count increased from {current_count} to {new_total_faces}"
                    )
                    print(
                        f"   ✅ This confirms force processing worked and duplicate prevention detected the new faces"
                    )
                else:
                    print(f"   📊 Face count unchanged: {new_total_faces}")
                    print(
                        f"   ⚠️ Force processing may not have added faces (this could be normal)"
                    )

            else:
                print(f"   ❌ DUPLICATE PREVENTION BROKEN after force processing!")
                return False

        else:
            print(f"   ❌ HTTP Error: {retest_response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Error re-testing duplicate prevention: {e}")
        return False

    print()
    print("🎉 ALL TESTS PASSED!")
    print("✅ Duplicate prevention fix is working correctly")
    print("✅ Force processing override works")
    print("✅ Duplicate prevention persists after force processing")

    return True


def test_flutter_deduplication_impact():
    """Test if the backend fix reduces the need for Flutter deduplication."""

    print()
    print("🎯 TESTING FLUTTER DEDUPLICATION IMPACT")
    print("=" * 50)

    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU5MDg4MDA1fQ.Q0ZLtkGGDk0uDy0CE4uPzhO7tBZfJr2yXM-j-UQYrIY"
    headers = {"Authorization": f"Bearer {token}"}

    print("📋 Testing face count consistency across services...")

    # Test multiple media IDs to check for duplicate patterns
    test_media_ids = [
        "0f840231-70f9-4949-bb9a-94d328fe9839",  # Known problematic media
        # Add other media IDs if available
    ]

    for media_id in test_media_ids:
        print(f"   Testing media: {media_id}")

        try:
            # Get face count from Vision Service
            vision_response = requests.get(
                f"http://localhost:8003/faces/media/{media_id}",
                headers=headers,
                timeout=5,
            )

            if vision_response.status_code == 200:
                vision_data = vision_response.json()
                vision_count = vision_data.get("total_faces", 0)

                print(f"      Vision Service: {vision_count} faces")

                # If we see systematic 2x duplication, that's the old pattern
                # If we see single counts, that means our fix is working
                if vision_count % 2 == 0:
                    print(
                        f"      ⚠️ Even number ({vision_count}) - could indicate 2x duplication pattern"
                    )
                    print(
                        f"      🔍 Check if this represents actual faces or systematic doubles"
                    )
                else:
                    print(
                        f"      ✅ Odd number ({vision_count}) - likely represents actual faces"
                    )

            else:
                print(f"      ❌ Vision Service error: {vision_response.status_code}")

        except Exception as e:
            print(f"      ❌ Error testing {media_id}: {e}")

    print()
    print("💡 INTERPRETATION GUIDE:")
    print("   - If face counts are now odd numbers → Fix likely working")
    print("   - If face counts still show 2x pattern → Need more investigation")
    print("   - Flutter deduplication should show 0 duplicates removed when fix works")


if __name__ == "__main__":
    print("🔧 VISION SERVICE DUPLICATE PREVENTION FIX - TEST SUITE")
    print("=" * 65)
    print()

    # Run duplicate prevention tests
    success = test_duplicate_prevention_fix()

    if success:
        # Run Flutter impact tests
        test_flutter_deduplication_impact()

        print()
        print("🎯 SUMMARY")
        print("=" * 30)
        print("✅ Duplicate prevention fix appears to be working")
        print("📋 Next steps:")
        print("   1. Monitor Flutter logs for reduced deduplication")
        print("   2. Test with fresh video uploads")
        print("   3. Consider removing Flutter deduplication code")
        print()
        print("🚀 SUCCESS: Ready to deploy fix to production!")

    else:
        print()
        print("🚨 FAILURE: Duplicate prevention fix needs more work")
        print("❌ The backend fix is not working as expected")
        print("⚠️ Keep Flutter deduplication active until this is resolved")
        sys.exit(1)
