#!/usr/bin/env python3
"""
Find and delete duplicate camera by name
"""
import json

import requests

# Configuration
CAMERAS_SERVICE_URL = "http://localhost:8005"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3Mjc3NjU0fQ.ezfRHyLjV8qKrIjUOJ1iufArV0WvFtdvHFZbFq4ss8w"


def get_auth_headers():
    return {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json",
    }


def get_all_cameras():
    """Get all cameras"""
    try:
        response = requests.get(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/",
            headers=get_auth_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get cameras: {response.status_code}")
            print(f"Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting cameras: {e}")
        return []


def delete_camera(camera_id):
    """Delete a camera by ID"""
    try:
        response = requests.delete(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/{camera_id}",
            headers=get_auth_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            print(f"✅ Successfully deleted camera {camera_id}")
            return True
        else:
            print(f"❌ Failed to delete camera {camera_id}: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error deleting camera {camera_id}: {e}")
        return False


def main():
    print("🔍 Searching for 'Mobile Camera TKQ1' duplicate...")

    cameras = get_all_cameras()
    if not cameras:
        print("❌ No cameras found")
        return

    print(f"\n📋 All cameras ({len(cameras)}):")
    target_camera = None

    for camera in cameras:
        print(
            f"  ID {camera['id']}: {camera['name']} - {camera['device_id']} ({camera['camera_type']})"
        )

        # Look for the camera named "Mobile Camera TKQ1"
        if "Mobile Camera" in camera["name"] and "TKQ1" in camera["name"]:
            target_camera = camera
            print(f"  ⚠️  FOUND TARGET: This is the duplicate to delete!")

    if target_camera:
        print(f"\n🎯 Found duplicate camera to delete:")
        print(f"   ID: {target_camera['id']}")
        print(f"   Name: {target_camera['name']}")
        print(f"   Device ID: {target_camera['device_id']}")

        confirm = input(
            f"\n❓ Delete camera ID {target_camera['id']} '{target_camera['name']}'? (y/N): "
        )
        if confirm.lower() == "y":
            if delete_camera(target_camera["id"]):
                print(f"✅ Successfully deleted duplicate camera!")
            else:
                print(f"❌ Failed to delete camera")
        else:
            print("❌ Deletion cancelled")
    else:
        print("\n✅ No camera named 'Mobile Camera TKQ1' found in the API response")
        print("💡 The duplicate might only be visible in the frontend cache")


if __name__ == "__main__":
    main()
