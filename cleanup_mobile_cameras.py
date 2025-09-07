#!/usr/bin/env python3
"""
Clean up mobile camera data that might have incompatible structure.
"""

import json

import requests

# Authentication token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3MDIwMTM2fQ.NuGCB2Oslgy4VT6oKPi0BwVY-Zt_l55VezUd_eX9pcw"
BASE_URL = "http://localhost:8005"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def list_mobile_cameras():
    """List all mobile cameras."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/cameras/mobile", headers=headers)
        if response.status_code == 200:
            data = response.json()
            cameras = data.get("cameras", [])
            print(f"📋 Found {len(cameras)} mobile cameras:")
            for camera in cameras:
                print(
                    f"  • ID: {camera.get('id')}, Device: {camera.get('device_id')}, Name: {camera.get('name', 'Unknown')}"
                )
            return cameras
        else:
            print(
                f"❌ Failed to list cameras: {response.status_code} - {response.text}"
            )
            return []
    except Exception as e:
        print(f"❌ Error listing cameras: {e}")
        return []


def delete_camera(camera_id):
    """Delete a camera by ID."""
    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/cameras/{camera_id}", headers=headers
        )
        if response.status_code == 200:
            print(f"✅ Deleted camera ID {camera_id}")
            return True
        else:
            print(
                f"❌ Failed to delete camera {camera_id}: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error deleting camera {camera_id}: {e}")
        return False


def main():
    print("🧹 Mobile Camera Cleanup Tool")
    print("=" * 40)

    # List current mobile cameras
    cameras = list_mobile_cameras()

    if not cameras:
        print("✅ No mobile cameras found to clean up")
        return

    # Delete each mobile camera
    print("\n🗑️  Deleting mobile cameras...")
    for camera in cameras:
        camera_id = camera.get("id")
        if camera_id:
            delete_camera(camera_id)

    print("\n✅ Mobile camera cleanup complete!")
    print("Now you can register your mobile camera fresh without data conflicts.")


if __name__ == "__main__":
    main()
