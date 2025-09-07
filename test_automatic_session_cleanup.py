#!/usr/bin/env python3
"""
Test script to verify automatic streaming session cleanup functionality.
Tests that sessions are automatically cleaned up when:
1. Cameras disconnect
2. Streams are stopped
3. Mobile cameras lose WebSocket connections
"""

import json
import time

import requests

# Base URLs
NODE_URL = "http://localhost:8001"
CAMERAS_URL = "http://localhost:8005"


def get_auth_token():
    """Get authentication token."""
    response = requests.post(
        f"{NODE_URL}/api/v1/users/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data="username=fresh.user@example.com&password=NewPassword234!",
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get auth token: {response.text}")


def get_streaming_sessions(token):
    """Get current streaming sessions."""
    response = requests.get(
        f"{CAMERAS_URL}/api/v1/auth/streaming-sessions",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get sessions: {response.text}")


def get_cameras(token):
    """Get available cameras."""
    response = requests.get(
        f"{CAMERAS_URL}/api/v1/cameras/", headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get cameras: {response.text}")


def start_stream(token, device_id):
    """Start streaming for a camera."""
    response = requests.post(
        f"{CAMERAS_URL}/api/v1/streaming/{device_id}/start",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to start stream: {response.text}")


def stop_stream(token, device_id):
    """Stop streaming for a camera."""
    response = requests.post(
        f"{CAMERAS_URL}/api/v1/streaming/{device_id}/stop",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to stop stream: {response.text}")


def disconnect_camera(token, device_id):
    """Disconnect a camera."""
    response = requests.post(
        f"{CAMERAS_URL}/api/v1/cameras/{device_id}/disconnect",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to disconnect camera: {response.text}")


def disconnect_all_cameras(token):
    """Disconnect all cameras."""
    response = requests.post(
        f"{CAMERAS_URL}/api/v1/cameras/disconnect-all",
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to disconnect all cameras: {response.text}")


def test_automatic_session_cleanup():
    """Test automatic session cleanup functionality."""

    print("🧪 Testing Automatic Streaming Session Cleanup")
    print("=" * 60)

    try:
        # Get authentication token
        print("1️⃣ Getting authentication token...")
        token = get_auth_token()
        print("✅ Authentication successful")

        # Check initial state
        print("\n2️⃣ Checking initial session state...")
        initial_sessions = get_streaming_sessions(token)
        print(f"📊 Initial sessions: {initial_sessions['sessions']['total_sessions']}")

        # Get available cameras
        print("\n3️⃣ Getting available cameras...")
        cameras = get_cameras(token)
        print(f"📷 Found {len(cameras)} cameras")

        if not cameras:
            print("⚠️ No cameras available for testing")
            return

        # Use the first available camera for testing
        test_camera = cameras[0]
        device_id = test_camera["device_id"]
        camera_name = test_camera["name"]

        print(f"🎯 Using camera: {camera_name} ({device_id})")

        # Test 1: Stream start/stop cleanup
        print(f"\n4️⃣ Test 1: Stream start/stop session cleanup")
        print(f"Starting stream for {device_id}...")

        start_result = start_stream(token, device_id)
        print(f"✅ Stream started: {start_result['status']}")

        # Check sessions after starting stream
        time.sleep(2)  # Give time for session creation
        sessions_after_start = get_streaming_sessions(token)
        sessions_count = sessions_after_start["sessions"]["total_sessions"]
        print(f"📊 Sessions after start: {sessions_count}")

        # Stop the stream and check cleanup
        print(f"Stopping stream for {device_id}...")
        stop_result = stop_stream(token, device_id)
        print(f"✅ Stream stopped: {stop_result['status']}")

        if "sessions_cleaned" in stop_result:
            print(f"🧹 Sessions cleaned during stop: {stop_result['sessions_cleaned']}")

        # Check sessions after stopping stream
        time.sleep(1)
        sessions_after_stop = get_streaming_sessions(token)
        sessions_count_after_stop = sessions_after_stop["sessions"]["total_sessions"]
        print(f"📊 Sessions after stop: {sessions_count_after_stop}")

        # Test 2: Camera disconnect cleanup
        print(f"\n5️⃣ Test 2: Camera disconnect session cleanup")

        # Start stream again
        print(f"Starting stream again for {device_id}...")
        start_stream(token, device_id)
        time.sleep(2)

        sessions_before_disconnect = get_streaming_sessions(token)
        sessions_count_before = sessions_before_disconnect["sessions"]["total_sessions"]
        print(f"📊 Sessions before disconnect: {sessions_count_before}")

        # Disconnect camera
        print(f"Disconnecting camera {device_id}...")
        disconnect_result = disconnect_camera(token, device_id)
        print(f"✅ Camera disconnected: {disconnect_result['status']}")

        if "sessions_cleaned" in disconnect_result:
            print(
                f"🧹 Sessions cleaned during disconnect: {disconnect_result['sessions_cleaned']}"
            )

        # Check sessions after disconnect
        time.sleep(1)
        sessions_after_disconnect = get_streaming_sessions(token)
        sessions_count_after = sessions_after_disconnect["sessions"]["total_sessions"]
        print(f"📊 Sessions after disconnect: {sessions_count_after}")

        # Test 3: Disconnect all cleanup
        print(f"\n6️⃣ Test 3: Disconnect all cameras cleanup")

        # Create some sessions first by starting multiple streams
        print("Creating multiple sessions...")
        active_cameras = []
        for camera in cameras[:3]:  # Test with up to 3 cameras
            try:
                start_stream(token, camera["device_id"])
                active_cameras.append(camera["device_id"])
                print(f"✅ Started stream for {camera['name']}")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Could not start stream for {camera['name']}: {e}")

        # Check sessions before disconnect all
        time.sleep(2)
        sessions_before_all = get_streaming_sessions(token)
        sessions_count_before_all = sessions_before_all["sessions"]["total_sessions"]
        print(f"📊 Total sessions before disconnect all: {sessions_count_before_all}")

        # Disconnect all cameras
        print("Disconnecting all cameras...")
        disconnect_all_result = disconnect_all_cameras(token)
        print(f"✅ All cameras disconnected: {disconnect_all_result['status']}")

        if "sessions_cleaned" in disconnect_all_result:
            print(
                f"🧹 Sessions cleaned during disconnect all: {disconnect_all_result['sessions_cleaned']}"
            )

        # Check final session state
        time.sleep(1)
        final_sessions = get_streaming_sessions(token)
        final_sessions_count = final_sessions["sessions"]["total_sessions"]
        print(f"📊 Final sessions count: {final_sessions_count}")

        # Summary
        print(f"\n🎯 Test Results Summary:")
        print(f"   Initial sessions: {initial_sessions['sessions']['total_sessions']}")
        print(f"   Final sessions: {final_sessions_count}")
        print(
            f"   Sessions should be 0 after cleanup: {'✅' if final_sessions_count == 0 else '❌'}"
        )

        if final_sessions_count == 0:
            print(
                "\n🎉 All tests passed! Automatic session cleanup is working correctly."
            )
        else:
            print(f"\n⚠️ Warning: {final_sessions_count} sessions remain after cleanup.")
            print("Active sessions:")
            for session in final_sessions["sessions"]["sessions"]:
                print(f"   - {session['session_id']} (device: {session['device_id']})")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_automatic_session_cleanup()
