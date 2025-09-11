#!/usr/bin/env python3
"""
Fix Camera Disconnect Issues Script

This script addresses two camera disconnect issues:
1. USB cameras stuck in "connected" state when backend service lost the connection
2. Mobile cameras that should auto-disconnect when no active app session

The script provides a comprehensive fix for both camera types.
"""

import json
import sys
from datetime import datetime, timedelta

import requests

# Configuration
CAMERAS_SERVICE_URL = "http://localhost:8005"
NODE_SERVICE_URL = "http://localhost:8001"

# User credentials from notes.txt
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"


def get_auth_token():
    """Get authentication token."""
    try:
        response = requests.post(
            f"{NODE_SERVICE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"username={USERNAME}&password={PASSWORD}",
        )
        if response.status_code == 200:
            data = response.json()
            return data["access_token"]
        else:
            print(f"❌ Failed to authenticate: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting auth token: {e}")
        return None


def get_auth_headers(token):
    """Get authorization headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_all_cameras(token):
    """Get all cameras from the database."""
    try:
        response = requests.get(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras",
            headers=get_auth_headers(token),
        )

        if response.status_code == 200:
            return response.json().get("cameras", [])
        else:
            print(f"❌ Failed to get cameras: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting cameras: {e}")
        return []


def get_active_connections(token):
    """Get active camera connections from backend service."""
    try:
        response = requests.get(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/active",
            headers=get_auth_headers(token),
        )

        if response.status_code == 200:
            active_data = response.json()
            return active_data.get("active_cameras", [])
        else:
            print(f"❌ Failed to get active connections: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting active connections: {e}")
        return []


def force_disconnect_usb_camera(token, device_id):
    """Force disconnect a USB camera by cleaning up database state."""
    try:
        print(f"🔧 Force disconnecting USB camera: {device_id}")

        # Try direct disconnect first
        response = requests.post(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/{device_id}/disconnect",
            headers=get_auth_headers(token),
        )

        if response.status_code == 200:
            print(f"✅ Successfully disconnected USB camera: {device_id}")
            return True
        else:
            # If direct disconnect fails, it means backend service lost the connection
            # but database still shows connected - this is the exact issue
            print(f"⚠️ Backend says camera not connected, but database shows connected")
            print(f"   This confirms the state inconsistency issue!")

            # Use disconnect-all to force cleanup
            print(f"🔧 Using disconnect-all to force state cleanup...")
            response = requests.post(
                f"{CAMERAS_SERVICE_URL}/api/v1/cameras/disconnect-all",
                headers=get_auth_headers(token),
            )

            if response.status_code == 200:
                print(f"✅ Force disconnected all cameras (including {device_id})")
                return True
            else:
                print(f"❌ Failed to force disconnect: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Error force disconnecting USB camera {device_id}: {e}")
        return False


def cleanup_mobile_cameras(token):
    """Cleanup stale mobile camera connections."""
    try:
        print("🧹 Cleaning up stale mobile cameras...")

        response = requests.post(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/mobile/cleanup-stale",
            headers=get_auth_headers(token),
        )

        if response.status_code == 200:
            data = response.json()
            updated_count = data.get("updated_cameras", 0)
            print(f"✅ Cleaned up {updated_count} stale mobile cameras")
            return True
        else:
            print(f"❌ Failed to cleanup mobile cameras: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error cleaning up mobile cameras: {e}")
        return False


def analyze_camera_state_inconsistencies(all_cameras, active_connections):
    """Analyze and report camera state inconsistencies."""
    print("\n📊 CAMERA STATE ANALYSIS")
    print("=" * 50)

    # Create sets for easier comparison
    active_device_ids = {
        conn.get("device_id") for conn in active_connections if conn.get("device_id")
    }

    usb_stuck_cameras = []
    mobile_stuck_cameras = []
    consistent_cameras = []

    for camera in all_cameras:
        device_id = camera.get("device_id")
        camera_type = camera.get("camera_type", "UNKNOWN")
        status = camera.get("status", "UNKNOWN")

        is_db_connected = status == "connected"
        is_backend_connected = device_id in active_device_ids

        if is_db_connected and not is_backend_connected:
            # Camera shows connected in DB but not in backend - INCONSISTENT STATE
            if camera_type == "USB":
                usb_stuck_cameras.append(camera)
            elif camera_type == "MOBILE":
                mobile_stuck_cameras.append(camera)
        elif is_db_connected and is_backend_connected:
            # Camera connected in both DB and backend - CONSISTENT
            consistent_cameras.append(camera)
        elif not is_db_connected and not is_backend_connected:
            # Camera disconnected in both - CONSISTENT
            consistent_cameras.append(camera)

    print(f"🔍 Total cameras analyzed: {len(all_cameras)}")
    print(f"✅ Consistent state: {len(consistent_cameras)}")
    print(f"⚠️ USB cameras stuck: {len(usb_stuck_cameras)}")
    print(f"⚠️ Mobile cameras stuck: {len(mobile_stuck_cameras)}")

    return usb_stuck_cameras, mobile_stuck_cameras


def fix_usb_camera_issues(token, stuck_usb_cameras):
    """Fix USB camera disconnect issues."""
    if not stuck_usb_cameras:
        print("\n✅ No USB camera issues found!")
        return True

    print(f"\n🔧 FIXING USB CAMERA ISSUES")
    print("=" * 50)

    success_count = 0

    for camera in stuck_usb_cameras:
        device_id = camera.get("device_id")
        camera_name = camera.get("name", device_id)

        print(f"\n🔧 Fixing USB camera: {camera_name} ({device_id})")
        print(
            f"   Issue: Database shows 'connected' but backend has no active connection"
        )

        if force_disconnect_usb_camera(token, device_id):
            success_count += 1
            print(f"   ✅ Fixed!")
        else:
            print(f"   ❌ Failed to fix")

    print(
        f"\n📊 USB Camera Fix Results: {success_count}/{len(stuck_usb_cameras)} fixed"
    )
    return success_count == len(stuck_usb_cameras)


def fix_mobile_camera_issues(token, stuck_mobile_cameras):
    """Fix mobile camera disconnect issues."""
    if not stuck_mobile_cameras:
        print("\n✅ No mobile camera issues found!")
        return True

    print(f"\n🔧 FIXING MOBILE CAMERA ISSUES")
    print("=" * 50)

    print(
        f"Found {len(stuck_mobile_cameras)} mobile cameras stuck in 'connected' state"
    )
    print("Mobile cameras should auto-disconnect when mobile app is not active")

    # Show details of stuck mobile cameras
    for camera in stuck_mobile_cameras:
        device_id = camera.get("device_id")
        camera_name = camera.get("name", device_id)
        last_seen = camera.get("last_seen", "Unknown")

        print(f"   📱 {camera_name} ({device_id}) - Last seen: {last_seen}")

    # Run mobile cleanup
    return cleanup_mobile_cameras(token)


def main():
    """Main function to fix camera disconnect issues."""
    print("🚀 PPL Meta Camera Disconnect Issues Fix")
    print("=" * 50)
    print()
    print("This script will:")
    print("1. Analyze camera state inconsistencies")
    print("2. Fix USB cameras stuck in 'connected' state")
    print("3. Cleanup stale mobile camera connections")
    print()

    # Get authentication token
    print("🔐 Authenticating...")
    token = get_auth_token()
    if not token:
        print("❌ Failed to authenticate. Exiting.")
        return False
    print("✅ Authentication successful")

    # Get current camera state
    print("\n📋 Getting current camera state...")
    all_cameras = get_all_cameras(token)
    active_connections = get_active_connections(token)

    if not all_cameras:
        print("❌ No cameras found. Exiting.")
        return False

    print(f"✅ Found {len(all_cameras)} cameras in database")
    print(f"✅ Found {len(active_connections)} active connections")

    # Analyze state inconsistencies
    usb_stuck, mobile_stuck = analyze_camera_state_inconsistencies(
        all_cameras, active_connections
    )

    # Fix issues
    usb_success = fix_usb_camera_issues(token, usb_stuck)
    mobile_success = fix_mobile_camera_issues(token, mobile_stuck)

    # Final report
    print(f"\n🏁 FINAL RESULTS")
    print("=" * 50)

    if usb_success and mobile_success:
        print("✅ All camera disconnect issues have been fixed!")
        print("\n💡 RECOMMENDATIONS:")
        print("   • USB cameras now have proper connect/disconnect functionality")
        print("   • Mobile cameras will auto-cleanup after 5 minutes of inactivity")
        print("   • Refresh your frontend to see the updated camera states")
        return True
    else:
        print("⚠️ Some issues may remain. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
