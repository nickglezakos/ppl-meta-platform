#!/usr/bin/env python3
"""
Test Simple Direct Streaming
Test the reverted simple streaming setup for Flutter frontend integration.
"""

import requests
import time

def test_simple_streaming():
    print("🧪 Testing Simple Direct Streaming Setup")
    print("=" * 50)
    
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

    # Step 4: Test direct streaming endpoint (as Flutter would use it)
    print("\n4️⃣ Testing direct streaming endpoint...")
    
    # Test the simple direct URL format
    stream_url = f"http://localhost:8005/api/v1/streaming/{camera_id}/video"
    print(f"🎥 Direct Stream URL: {stream_url}")

    try:
        # Just test the headers, don't download the stream
        stream_response = requests.get(
            stream_url, 
            headers=headers,
            timeout=5, 
            stream=True
        )
        stream_response.raise_for_status()

        print("✅ Direct streaming endpoint accessible!")
        print(f"   Status: {stream_response.status_code}")
        print(f"   Content-Type: {stream_response.headers.get('content-type')}")
        
        # Verify it's MJPEG
        content_type = stream_response.headers.get("content-type", "")
        if "multipart/x-mixed-replace" in content_type:
            print("✅ Correct MJPEG content type detected")
        else:
            print(f"⚠️ Unexpected content type: {content_type}")

        # Close the stream immediately to not consume resources
        stream_response.close()

    except Exception as e:
        print(f"❌ Direct streaming endpoint test failed: {e}")
        return False

    print("\n🎉 Simple Direct Streaming Test PASSED!")
    print("\n📋 Summary:")
    print("✅ Authentication working")
    print("✅ Camera detection working") 
    print("✅ Stream start working")
    print("✅ Direct streaming endpoint accessible")
    print(f"\n🎥 Flutter should now use: {stream_url}")
    print("   No sessions, no complex routing - just direct MJPEG!")
    
    return True

if __name__ == "__main__":
    success = test_simple_streaming()
    if success:
        print("\n🚀 Ready for Flutter testing!")
        print("   Navigate to http://localhost:3000/cameras")
        print("   Camera streams should now display correctly!")
    else:
        print("\n❌ Simple streaming setup needs fixes")