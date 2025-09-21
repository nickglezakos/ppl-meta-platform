#!/usr/bin/env python3
"""
Enable auto face detection for test camera
"""
import sys

import requests

# Add the orchestrator src directory to Python path
sys.path.insert(
    0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-orchestrator/src"
)

from service_auth import service_auth


def enable_auto_face_detection():
    """Enable auto face detection for the test camera"""
    camera_device_id = "mobile_TKQ1.221114.001"
    camera_service_url = "http://localhost:8005"

    # Generate service token
    try:
        service_token = service_auth.create_service_token("7", expires_hours=1)
        print(f"✅ Service token generated: {service_token[:20]}...")
    except Exception as e:
        print(f"❌ Failed to generate service token: {e}")
        return False

    # Get current camera settings
    print(f"🔍 Getting current settings for camera: {camera_device_id}")

    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }

    try:
        # Get camera settings
        response = requests.get(
            f"{camera_service_url}/api/v1/cameras/{camera_device_id}/settings",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            settings = response.json()
            print(
                f"✅ Current auto_face_detection: {settings.get('auto_face_detection', 'Not set')}"
            )

            # Update settings to enable auto face detection
            settings["auto_face_detection"] = True

            # Update the camera settings
            update_response = requests.put(
                f"{camera_service_url}/api/v1/cameras/{camera_device_id}/settings",
                json=settings,
                headers=headers,
                timeout=10,
            )

            if update_response.status_code == 200:
                print("✅ Successfully enabled auto face detection")
                return True
            else:
                print(f"❌ Failed to update settings: {update_response.status_code}")
                print(f"Response: {update_response.text}")
                return False

        else:
            print(f"❌ Failed to get camera settings: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error updating camera settings: {e}")
        return False


if __name__ == "__main__":
    print("🔧 PPL Meta - Enable Auto Face Detection")
    print("=" * 45)

    success = enable_auto_face_detection()
    if success:
        print("\n✅ Auto face detection enabled! You can now test the workflow.")
    else:
        print("\n❌ Failed to enable auto face detection.")

    sys.exit(0 if success else 1)
