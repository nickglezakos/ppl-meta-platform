#!/usr/bin/env python3
"""
Test script to verify camera streaming endpoint accessibility
for Flutter frontend integration.
"""
import json

import requests


def test_streaming_endpoint():
    print("🧪 Testing Camera Streaming Endpoint for Flutter Frontend")
    print("=" * 60)

    # Step 1: Login to get token
    print("\n1️⃣ Getting authentication token...")
    login_url = "http://localhost:8001/api/v1/users/login"
    login_data = {"username": "fresh.user@example.com", "password": "NewPassword234!"}

    try:
        login_response = requests.post(
            login_url,
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login_response.raise_for_status()
        token = login_response.json()["access_token"]
        print(f"✅ Login successful, token: {token[:20]}...")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # Step 2: Detect cameras
    print("\n2️⃣ Detecting cameras...")
    detect_url = "http://localhost:8005/api/v1/cameras/detect?save_to_db=true"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        detect_response = requests.post(detect_url, headers=headers)
        detect_response.raise_for_status()
        cameras = detect_response.json()["cameras"]
        print(f"✅ Detected {len(cameras)} cameras")

        if not cameras:
            print("❌ No cameras detected")
            return

        camera_id = cameras[0]["device_id"]
        print(f"📷 Using camera: {camera_id}")
    except Exception as e:
        print(f"❌ Camera detection failed: {e}")
        return

    # Step 3: Connect to camera
    print("\n3️⃣ Connecting to camera...")
    connect_url = f"http://localhost:8005/api/v1/cameras/{camera_id}/connect"

    try:
        connect_response = requests.post(connect_url, headers=headers)
        connect_response.raise_for_status()
        print(f"✅ Camera connected: {connect_response.json()['message']}")
    except Exception as e:
        print(f"❌ Camera connection failed: {e}")
        return

    # Step 4: Test streaming endpoint (as Flutter would use it)
    print("\n4️⃣ Testing streaming endpoint...")

    # Test the corrected URL format
    stream_url = (
        f"http://localhost:8005/api/v1/streaming/{camera_id}/video?token={token}"
    )
    print(f"🎥 Stream URL: {stream_url}")

    try:
        # Just test the headers, don't download the stream
        stream_response = requests.get(stream_url, timeout=5, stream=True)
        stream_response.raise_for_status()

        print("✅ Streaming endpoint accessible!")
        print(f"   Status: {stream_response.status_code}")
        print(f"   Content-Type: {stream_response.headers.get('content-type')}")
        print(
            f"   Transfer-Encoding: {stream_response.headers.get('transfer-encoding')}"
        )

        # Verify it's MJPEG
        content_type = stream_response.headers.get("content-type", "")
        if "multipart/x-mixed-replace" in content_type:
            print("✅ Correct MJPEG content type detected")
        else:
            print(f"⚠️ Unexpected content type: {content_type}")

        # Close the stream immediately to not consume resources
        stream_response.close()

    except Exception as e:
        print(f"❌ Streaming endpoint test failed: {e}")
        return

    print("\n🎉 All tests passed! The streaming endpoint is working correctly.")
    print("   Flutter frontend should now be able to display the camera stream.")


if __name__ == "__main__":
    test_streaming_endpoint()
