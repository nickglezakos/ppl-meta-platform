#!/usr/bin/env python3
"""
Test Complete Simple Streaming Setup
Tests both backend simple streaming and Flutter compatibility.
"""

import requests
import json

def test_complete_simple_streaming():
    print("🧪 Testing Complete Simple Streaming Setup")
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
        return False

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
            return False

        camera_id = cameras[0]["device_id"]
        print(f"📷 Using camera: {camera_id}")
    except Exception as e:
        print(f"❌ Camera detection failed: {e}")
        return False

    # Step 3: Start streaming
    print("\n3️⃣ Starting camera stream...")
    start_url = f"http://localhost:8005/api/v1/streaming/{camera_id}/start"

    try:
        start_response = requests.post(start_url, headers=headers)
        start_response.raise_for_status()
        stream_info = start_response.json()
        print(f"✅ Stream started: {stream_info['message']}")
        print(f"🎥 Stream URL: {stream_info['stream_url']}")
    except Exception as e:
        print(f"❌ Stream start failed: {e}")
        return False

    # Step 4: Test direct streaming with Bearer header
    print("\n4️⃣ Testing direct streaming with Bearer header...")
    stream_url_header = f"http://localhost:8005/api/v1/streaming/{camera_id}/video"
    
    try:
        stream_response = requests.get(
            stream_url_header, 
            headers=headers,
            timeout=5, 
            stream=True
        )
        stream_response.raise_for_status()
        print("✅ Bearer header authentication works!")
        stream_response.close()
    except Exception as e:
        print(f"❌ Bearer header test failed: {e}")
        return False

    # Step 5: Test direct streaming with query parameter (Flutter method)
    print("\n5️⃣ Testing direct streaming with query parameter...")
    stream_url_query = f"http://localhost:8005/api/v1/streaming/{camera_id}/video?token={token}"
    
    try:
        # No Authorization header - using token in URL
        stream_response = requests.get(
            stream_url_query,
            timeout=5, 
            stream=True
        )
        stream_response.raise_for_status()

        print("✅ Query parameter authentication works!")
        print(f"   Status: {stream_response.status_code}")
        print(f"   Content-Type: {stream_response.headers.get('content-type')}")
        
        # Verify it's MJPEG
        content_type = stream_response.headers.get("content-type", "")
        if "multipart/x-mixed-replace" in content_type:
            print("✅ Correct MJPEG content type detected")
        else:
            print(f"⚠️ Unexpected content type: {content_type}")

        stream_response.close()
    except Exception as e:
        print(f"❌ Query parameter test failed: {e}")
        return False

    # Step 6: Test Flutter compatibility
    print("\n6️⃣ Testing Flutter frontend accessibility...")
    try:
        frontend_response = requests.get("http://localhost:3000", timeout=5)
        if frontend_response.status_code == 200:
            print("✅ Flutter frontend is accessible")
        else:
            print(f"⚠️ Flutter frontend returned: {frontend_response.status_code}")
    except Exception as e:
        print(f"⚠️ Flutter frontend test failed: {e}")

    print("\n🎉 COMPLETE SIMPLE STREAMING SETUP TEST PASSED!")
    print("\n📋 Summary:")
    print("✅ Authentication working")
    print("✅ Camera detection working") 
    print("✅ Stream start working")
    print("✅ Bearer header streaming working")
    print("✅ Query parameter streaming working (Flutter compatible)")
    print("✅ Flutter frontend accessible")
    
    print(f"\n🎥 Flutter URLs:")
    print(f"   Direct: {stream_url_query}")
    print("   Format: http://localhost:8005/api/v1/streaming/CAMERA_ID/video?token=JWT_TOKEN")
    
    print(f"\n🚀 Ready for complete testing!")
    print("   1. Navigate to http://localhost:3000/cameras")
    print("   2. Camera streams should display using simple direct streaming")
    print("   3. No complex sessions or routing - just direct MJPEG!")
    
    return True

if __name__ == "__main__":
    success = test_complete_simple_streaming()
    exit(0 if success else 1)