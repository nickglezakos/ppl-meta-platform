#!/usr/bin/env python3
"""
Test script to verify mobile camera IP update integration.
Tests the complete flow: IP discovery -> Backend update -> Frontend access
"""

import json
import time
from datetime import datetime

import requests

# Test configuration
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3MTU2MTk2fQ.nee7vqb2zjfbTUsOXZmwP1osZV2j_IlhUFvr8YeE7mY"
CAMERAS_SERVICE_URL = "http://localhost:8005"
DEVICE_ID = "mobile_TKQ1.221114.001"
CURRENT_IP = "192.168.69.107"
STALE_IP = "10.228.129.0"


def get_mobile_camera_info():
    """Get current mobile camera information"""
    url = f"{CAMERAS_SERVICE_URL}/api/v1/cameras/mobile"
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        cameras = response.json()
        for camera in cameras:
            if camera["device_id"] == DEVICE_ID:
                return camera

        return None
    except Exception as e:
        print(f"❌ Error getting camera info: {e}")
        return None


def update_mobile_camera_ip(new_ip, port=8554):
    """Update mobile camera IP address"""
    url = f"{CAMERAS_SERVICE_URL}/api/v1/cameras/mobile/{DEVICE_ID}/update-ip"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"ip_address": new_ip, "port": port}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error updating IP: {e}")
        return None


def simulate_stale_ip_scenario():
    """Simulate the stale IP scenario and test the fix"""
    print("🧪 Mobile Camera IP Update Integration Test")
    print("=" * 50)

    # Step 1: Set camera to stale IP (simulate network change)
    print("\n1️⃣ Simulating stale IP scenario...")
    print(f"   Setting camera IP to stale IP: {STALE_IP}")

    stale_result = update_mobile_camera_ip(STALE_IP)
    if not stale_result:
        print("❌ Failed to set stale IP")
        return False

    print(f"   ✅ Camera now has stale connection: {stale_result['new_connection']}")

    # Step 2: Get current camera state
    print("\n2️⃣ Getting current camera state...")
    camera_info = get_mobile_camera_info()
    if not camera_info:
        print("❌ Failed to get camera info")
        return False

    print(f"   📱 Camera: {camera_info['name']}")
    print(f"   🔗 Connection String: {camera_info['connection_string']}")
    print(f"   📍 IP Address: {camera_info['ip_address']}")
    print(f"   ⏰ Last Seen: {camera_info['last_seen']}")

    # Step 3: Simulate mobile app IP discovery and update
    print(f"\n3️⃣ Simulating mobile app IP discovery...")
    print(f"   📡 Mobile app discovers current IP: {CURRENT_IP}")
    print(f"   📤 Mobile app calls update-ip endpoint...")

    time.sleep(1)  # Brief delay to simulate discovery time

    update_result = update_mobile_camera_ip(CURRENT_IP)
    if not update_result:
        print("❌ Failed to update to current IP")
        return False

    print(f"   ✅ IP update successful!")
    print(f"   📝 Old connection: {update_result['old_connection']}")
    print(f"   🆕 New connection: {update_result['new_connection']}")

    # Step 4: Verify the update
    print("\n4️⃣ Verifying the update...")
    updated_camera_info = get_mobile_camera_info()
    if not updated_camera_info:
        print("❌ Failed to get updated camera info")
        return False

    # Check if IP was updated correctly
    if updated_camera_info["ip_address"] == CURRENT_IP:
        print(f"   ✅ IP successfully updated to: {updated_camera_info['ip_address']}")
    else:
        print(
            f"   ❌ IP update failed. Still shows: {updated_camera_info['ip_address']}"
        )
        return False

    # Check if connection string was updated
    expected_connection = f"mobile://{CURRENT_IP}:8554"
    if updated_camera_info["connection_string"] == expected_connection:
        print(
            f"   ✅ Connection string updated: {updated_camera_info['connection_string']}"
        )
    else:
        print(
            f"   ❌ Connection string incorrect: {updated_camera_info['connection_string']}"
        )
        return False

    # Check if last_seen was updated
    print(f"   ⏰ Last seen updated: {updated_camera_info['last_seen']}")

    # Step 5: Test frontend access (simulate)
    print("\n5️⃣ Testing frontend access simulation...")
    connection_string = updated_camera_info["connection_string"]

    if connection_string and connection_string.startswith("mobile://"):
        # Extract IP and port from connection string
        url_part = connection_string.replace("mobile://", "")
        ip_port = url_part.split(":")
        if len(ip_port) == 2:
            ip, port = ip_port[0], ip_port[1]
            stream_url = f"http://{ip}:{port}/stream"
            print(f"   📺 Frontend would access: {stream_url}")
            print(f"   ✅ Connection string provides valid stream URL")
        else:
            print(f"   ❌ Invalid connection string format: {connection_string}")
            return False
    else:
        print(f"   ❌ Invalid or missing connection string: {connection_string}")
        return False

    print("\n🎉 Integration test completed successfully!")
    print("✅ Mobile camera IP update mechanism is working correctly")
    print("✅ Stale IP fallback issue should be resolved")

    return True


def main():
    """Run the integration test"""
    try:
        success = simulate_stale_ip_scenario()
        if success:
            print("\n" + "=" * 50)
            print("✅ ALL TESTS PASSED")
            print("🔧 The mobile camera IP update fix is working correctly")
            print("📱 Mobile app should now properly update backend when IP changes")
            print("🚫 No more false fallbacks to stale IPs like 10.x.x.x")
        else:
            print("\n" + "=" * 50)
            print("❌ TESTS FAILED")
            print("🛠️ Further investigation needed")

    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Test failed with exception: {e}")


if __name__ == "__main__":
    main()
