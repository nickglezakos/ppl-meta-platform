#!/usr/bin/env python3
"""
Test the Fixed Frame Extraction API Endpoint
"""

import time

import requests


def test_fixed_endpoint():
    """Test the fixed frame extraction endpoint."""

    print("🧪 Testing Fixed Frame Extraction API Endpoint")
    print("=" * 60)

    # Configuration
    BASE_URL = "http://localhost"
    VIDEO_UUID = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
    TEST_FRAMES = [50, 100, 150]

    print(f"📋 Test Configuration:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Video UUID: {VIDEO_UUID}")
    print(f"   Test frames: {TEST_FRAMES}")

    # Step 1: Authenticate (using the correct credentials and method)
    print(f"\n1️⃣ Authenticating...")
    try:
        # Use the EXACT authentication method from the working notebook
        auth_response = requests.post(
            f"{BASE_URL}/api/v1/users/login",
            data={"username": "fresh.user@example.com", "password": "NewPassword234!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            auth_token = auth_data.get("access_token")
            print(f"   ✅ Authentication successful")
        else:
            print(
                f"   ❌ Auth failed: {auth_response.status_code} - {auth_response.text}"
            )
            return False

    except Exception as e:
        print(f"   💥 Auth error: {e}")
        return False

    # Step 2: Test frame extraction
    print(f"\n2️⃣ Testing frame extraction...")

    headers = {"Authorization": f"Bearer {auth_token}"}
    successful_extractions = 0

    for frame_num in TEST_FRAMES:
        print(f"\n   📸 Testing frame {frame_num}...")

        try:
            # Test via nginx proxy
            response = requests.get(
                f"{BASE_URL}/api/v1/media/{VIDEO_UUID}/frame/{frame_num}",
                headers=headers,
                params={"format": "jpeg", "quality": 85, "size": "medium"},
                timeout=30,
            )

            print(f"      Status: {response.status_code}")

            if response.status_code == 200:
                frame_size = len(response.content)
                content_type = response.headers.get("content-type", "N/A")
                print(f"      ✅ SUCCESS!")
                print(f"      📊 Size: {frame_size:,} bytes ({frame_size/1024:.1f} KB)")
                print(f"      🖼️  Type: {content_type}")
                successful_extractions += 1

            elif response.status_code == 400:
                print(f"      ❌ Bad Request: {response.text}")
                print(f"      💡 This might be a file path issue")

            elif response.status_code == 404:
                print(f"      ❌ Not Found: {response.text}")
                print(f"      💡 Media might not exist or endpoint missing")

            else:
                print(f"      ❌ Failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"      💥 Request error: {e}")

    # Results
    print(f"\n🏁 Test Results:")
    print(f"   Successful extractions: {successful_extractions}/{len(TEST_FRAMES)}")

    if successful_extractions == len(TEST_FRAMES):
        print(f"   🎉 ALL TESTS PASSED! Frame extraction is working!")
        return True
    elif successful_extractions > 0:
        print(f"   ⚠️  PARTIAL SUCCESS - Some frames extracted")
        return True
    else:
        print(f"   ❌ ALL TESTS FAILED - Frame extraction not working")
        return False


if __name__ == "__main__":
    success = test_fixed_endpoint()
    print(
        f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}: Frame extraction test completed"
    )
