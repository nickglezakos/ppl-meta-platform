#!/usr/bin/env python3
"""
Script to manually register a mobile camera for testing frontend streaming
"""
import json

import requests

# Configuration
BASE_URL = "http://localhost:8005"
NODE_URL = "http://localhost:8001"


def get_auth_token():
    """Get authentication token"""
    login_data = {"username": "fresh.user@example.com", "password": "NewPassword234!"}

    response = requests.post(
        f"{NODE_URL}/api/v1/users/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Failed to get auth token: {response.status_code}")
        return None


def register_mobile_camera(token):
    """Register a mobile camera"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    camera_data = {
        "name": "Mobile Camera TKQ1",
        "device_id": "mobile_TKQ1.221114.001",
        "camera_type": "MOBILE",
        "status": "connected",
        "resolution": "720x480",
        "max_fps": 30,
        "supports_streaming": True,
        "supports_recording": False,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/cameras", json=camera_data, headers=headers
    )

    print(f"Camera registration response: {response.status_code}")
    if response.content:
        try:
            print(f"Response body: {response.json()}")
        except:
            print(f"Raw response: {response.text}")

    return response.status_code == 200 or response.status_code == 201


def test_streaming(token):
    """Test streaming endpoints"""
    headers = {"Authorization": f"Bearer {token}"}

    # Test direct streaming
    response = requests.head(
        f"{BASE_URL}/api/v1/streaming/mobile_TKQ1.221114.001/video", headers=headers
    )
    print(f"Direct streaming test: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")

    # Test session creation
    response = requests.post(
        f"{BASE_URL}/api/v1/streaming/mobile/mobile_TKQ1.221114.001/streaming-session",
        headers=headers,
    )
    print(f"Session creation test: {response.status_code}")
    if response.status_code == 200:
        session_data = response.json()
        print(f"Session data: {session_data}")

        # Test session URL
        session_id = session_data.get("session_id")
        if session_id:
            session_response = requests.head(
                f"{BASE_URL}/api/v1/streaming/mobile_TKQ1.221114.001/video-session/{session_id}"
            )
            print(f"Session URL test: {session_response.status_code}")
            print(
                f"Session Content-Type: {session_response.headers.get('content-type')}"
            )


def main():
    print("🎥 Mobile Camera Registration and Test Script")
    print("=" * 50)

    # Get authentication token
    print("1. Getting authentication token...")
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    print("✅ Got authentication token")

    # Register mobile camera
    print("\n2. Registering mobile camera...")
    if register_mobile_camera(token):
        print("✅ Mobile camera registered successfully")
    else:
        print("⚠️ Camera registration had issues, but continuing...")

    # Test streaming
    print("\n3. Testing streaming endpoints...")
    test_streaming(token)

    print("\n🎉 Test complete! Check frontend at http://localhost:3000")


if __name__ == "__main__":
    main()
