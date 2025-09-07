#!/usr/bin/env python3
"""
Test Mobile Camera Streaming Fixes

This script tests the two main fixes implemented:
1. Mobile app sending frames to backend
2. Frontend connecting to correct streaming URLs

Expected flow:
1. Mobile app captures frames -> sends to backend cameras service
2. Frontend discovers mobile camera -> connects to backend streaming endpoint
3. End-to-end video streaming works
"""

import json
import sys
import time

import requests


def test_backend_services():
    """Test that all backend services are running"""
    print("🔍 Testing Backend Services...")

    services = [
        ("Node Service", "http://localhost:8001/api/v1/health"),
        ("Cameras Service", "http://localhost:8005/health"),
        ("Gateway Service", "http://localhost:8080/health"),
        ("Discovery Service", "http://localhost:8006/health"),
    ]

    all_healthy = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"✅ {name}: Healthy")
            else:
                print(f"❌ {name}: Error {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"❌ {name}: Not responding - {e}")
            all_healthy = False

    return all_healthy


def test_mobile_camera_registration():
    """Test if mobile camera is registered in cameras service"""
    print("\n🔍 Testing Mobile Camera Registration...")

    try:
        response = requests.get("http://localhost:8005/api/v1/cameras", timeout=5)
        if response.status_code == 200:
            cameras = response.json()
            mobile_cameras = [
                cam for cam in cameras if cam.get("camera_type") == "mobile"
            ]

            if mobile_cameras:
                print(f"✅ Found {len(mobile_cameras)} mobile camera(s) registered")
                for cam in mobile_cameras:
                    print(
                        f"   📱 {cam.get('name', 'Unknown')} - {cam.get('device_id', 'Unknown ID')}"
                    )
                    print(f"      Status: {cam.get('status', 'Unknown')}")
                    if "ip_address" in cam:
                        print(f"      IP: {cam['ip_address']}")
                return True
            else:
                print("❌ No mobile cameras found registered")
                return False
        else:
            print(f"❌ Failed to get cameras list: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking camera registration: {e}")
        return False


def test_streaming_endpoints():
    """Test mobile camera streaming endpoints"""
    print("\n🔍 Testing Mobile Camera Streaming Endpoints...")

    # Get mobile cameras
    try:
        response = requests.get("http://localhost:8005/api/v1/cameras", timeout=5)
        if response.status_code != 200:
            print("❌ Cannot get cameras list")
            return False

        cameras = response.json()
        mobile_cameras = [cam for cam in cameras if cam.get("camera_type") == "mobile"]

        if not mobile_cameras:
            print("❌ No mobile cameras to test")
            return False

        # Test streaming endpoint for each mobile camera
        for camera in mobile_cameras:
            device_id = camera.get("device_id")
            if not device_id:
                continue

            streaming_url = f"http://localhost:8005/api/v1/streaming/{device_id}/video"
            print(f"🎥 Testing stream for {camera.get('name', device_id)}")
            print(f"   URL: {streaming_url}")

            try:
                # Test if endpoint exists (should get some response, even if no frames)
                response = requests.get(streaming_url, timeout=3, stream=True)
                print(f"   Status: {response.status_code}")
                print(
                    f"   Content-Type: {response.headers.get('content-type', 'Not set')}"
                )

                if response.status_code == 200:
                    # Check if it's MJPEG stream
                    content_type = response.headers.get("content-type", "")
                    if "multipart/x-mixed-replace" in content_type:
                        print("   ✅ MJPEG stream endpoint working")
                    else:
                        print(f"   ⚠️ Unexpected content type: {content_type}")
                elif response.status_code == 404:
                    print("   ❌ Camera not connected/streaming")
                else:
                    print(f"   ⚠️ Unexpected status: {response.status_code}")

            except Exception as e:
                print(f"   ❌ Error accessing stream: {e}")

        return True

    except Exception as e:
        print(f"❌ Error testing streaming endpoints: {e}")
        return False


def test_frame_transmission():
    """Test if mobile app is sending frames to backend"""
    print("\n🔍 Testing Frame Transmission...")
    print("📱 Check mobile app logs for:")
    print("   - 'Received frame: WxH' messages (camera capture working)")
    print("   - Frame transmission to backend (should see HTTP requests)")
    print("   - No 'Frames: 0' messages in streaming duration logs")
    print("\n💡 Mobile app should show frames being sent to backend at:")
    print("   http://192.168.69.107:8005/api/v1/streaming/mobile_{device_id}/frame")
    print("\n⚠️  If you see 'Received frame' but no backend transmission:")
    print("   - Check CameraService.setStreamingService() connection")
    print("   - Verify MobileStreamingService.sendFrameToBackend() is called")
    print("   - Check mobile app authentication with backend")


def main():
    print("🧪 Mobile Camera Streaming Fixes Test")
    print("=" * 50)

    # Test 1: Backend services
    if not test_backend_services():
        print("\n❌ Backend services not ready. Please start all services first.")
        sys.exit(1)

    # Test 2: Mobile camera registration
    mobile_registered = test_mobile_camera_registration()

    # Test 3: Streaming endpoints
    test_streaming_endpoints()

    # Test 4: Frame transmission guidance
    test_frame_transmission()

    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    if mobile_registered:
        print("✅ Mobile camera is registered - good start!")
        print("📱 Check mobile app logs to see if frames are being sent to backend")
        print("🌐 Check frontend to see if it can display the mobile camera stream")
        print("\n🔍 If mobile app shows 'Received frame' but frontend shows no video:")
        print("   1. Verify mobile app is sending frames with new fixes")
        print("   2. Check if frontend is using correct streaming URL")
        print("   3. Test the stream URL manually in browser")
    else:
        print("❌ Mobile camera not registered yet")
        print("📱 Ensure mobile app is running and authenticated")
        print("🔐 Check mobile app authentication with backend services")

    print("\n💡 The fixes implemented:")
    print("   1. ✅ CameraService now sends frames to MobileStreamingService")
    print("   2. ✅ Frontend URL logic updated for mobile cameras")
    print("   3. 🎯 Mobile app should now transmit frames to backend!")


if __name__ == "__main__":
    main()
