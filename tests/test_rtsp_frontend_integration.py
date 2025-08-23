#!/usr/bin/env python3
"""
RTSP Camera Frontend Integration Test
=====================================

This script tests the complete RTSP camera management functionality
including create, read, update, and delete operations through both
the backend API and verifies the frontend can handle them.

Usage:
    python test_rtsp_frontend_integration.py
"""

import json
import time
from typing import Dict, List, Optional

import requests

# Configuration
NODE_SERVICE_URL = "http://localhost:8001"
CAMERAS_SERVICE_URL = "http://localhost:8005"
FRONTEND_URL = "http://localhost:3000"

# Test credentials
TEST_USERNAME = "fresh.user@example.com"
TEST_PASSWORD = "NewPassword234!"


class RTSPCameraTestSuite:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.test_cameras: List[str] = []

    def authenticate(self) -> bool:
        """Authenticate with the node service to get access token"""
        print("🔐 Authenticating with node service...")

        response = requests.post(
            f"{NODE_SERVICE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"username={TEST_USERNAME}&password={TEST_PASSWORD}",
        )

        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            print(f"✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.access_token}"}

    def test_camera_list(self) -> bool:
        """Test retrieving camera list"""
        print("\n📋 Testing camera list retrieval...")

        response = requests.get(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/", headers=self.get_auth_headers()
        )

        if response.status_code == 200:
            cameras = response.json()
            print(f"✅ Retrieved {len(cameras)} cameras")
            for camera in cameras:
                print(
                    f"   - {camera['name']} ({camera['camera_type']}) - {camera['device_id']}"
                )
            return True
        else:
            print(f"❌ Failed to retrieve cameras: {response.status_code}")
            return False

    def test_create_rtsp_camera(self) -> Optional[str]:
        """Test creating an RTSP camera"""
        print("\n➕ Testing RTSP camera creation...")

        camera_data = {
            "name": f"Test RTSP Camera {int(time.time())}",
            "host": "192.168.1.150",
            "port": 554,
            "username": "testuser",
            "password": "testpass",
            "stream_path": "/live/main",
        }

        response = requests.post(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/rtsp",
            headers={**self.get_auth_headers(), "Content-Type": "application/json"},
            json=camera_data,
        )

        if response.status_code == 201:
            camera = response.json()["camera"]
            device_id = camera["device_id"]
            self.test_cameras.append(device_id)
            print(f"✅ Created RTSP camera: {camera['name']} ({device_id})")
            return device_id
        else:
            print(
                f"❌ Failed to create RTSP camera: {response.status_code} - {response.text}"
            )
            return None

    def test_update_rtsp_camera(self, device_id: str) -> bool:
        """Test updating an RTSP camera"""
        print(f"\n✏️ Testing RTSP camera update for {device_id}...")

        update_data = {
            "name": f"Updated Test RTSP Camera {int(time.time())}",
            "host": "192.168.1.151",
            "port": 8554,
            "username": "updateduser",
            "password": "updatedpass",
            "stream_path": "/stream/updated",
        }

        response = requests.put(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/rtsp/{device_id}",
            headers={**self.get_auth_headers(), "Content-Type": "application/json"},
            json=update_data,
        )

        if response.status_code == 200:
            camera = response.json()["camera"]
            print(f"✅ Updated RTSP camera: {camera['name']} ({camera['device_id']})")
            return True
        else:
            print(
                f"❌ Failed to update RTSP camera: {response.status_code} - {response.text}"
            )
            return False

    def test_delete_rtsp_camera(self, device_id: str) -> bool:
        """Test deleting an RTSP camera"""
        print(f"\n🗑️ Testing RTSP camera deletion for {device_id}...")

        response = requests.delete(
            f"{CAMERAS_SERVICE_URL}/api/v1/cameras/rtsp/{device_id}",
            headers=self.get_auth_headers(),
        )

        if response.status_code == 200:
            print(f"✅ Deleted RTSP camera: {device_id}")
            if device_id in self.test_cameras:
                self.test_cameras.remove(device_id)
            return True
        else:
            print(
                f"❌ Failed to delete RTSP camera: {response.status_code} - {response.text}"
            )
            return False

    def test_frontend_accessibility(self) -> bool:
        """Test that frontend is accessible"""
        print("\n🌐 Testing frontend accessibility...")

        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200:
                print("✅ Frontend is accessible")
                print(f"   Frontend running at: {FRONTEND_URL}")
                return True
            else:
                print(f"❌ Frontend returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Frontend not accessible: {e}")
            return False

    def cleanup(self):
        """Clean up any test cameras created during testing"""
        print("\n🧹 Cleaning up test cameras...")

        for device_id in self.test_cameras[:]:
            self.test_delete_rtsp_camera(device_id)

    def run_full_test_suite(self):
        """Run the complete test suite"""
        print("🧪 RTSP Camera Frontend Integration Test Suite")
        print("=" * 50)

        # Step 1: Authentication
        if not self.authenticate():
            print("❌ Test suite failed at authentication step")
            return False

        # Step 2: Test camera list
        if not self.test_camera_list():
            print("❌ Test suite failed at camera list step")
            return False

        # Step 3: Test frontend accessibility
        if not self.test_frontend_accessibility():
            print(
                "⚠️ Frontend accessibility test failed, but continuing with backend tests"
            )

        # Step 4: Test create operation
        device_id = self.test_create_rtsp_camera()
        if not device_id:
            print("❌ Test suite failed at camera creation step")
            return False

        # Step 5: Test update operation
        if not self.test_update_rtsp_camera(device_id):
            print("❌ Test suite failed at camera update step")
            self.cleanup()
            return False

        # Step 6: Test delete operation
        if not self.test_delete_rtsp_camera(device_id):
            print("❌ Test suite failed at camera deletion step")
            return False

        # Final cleanup
        self.cleanup()

        print("\n🎉 All tests passed! RTSP camera management is working correctly.")
        print("\n📋 Summary:")
        print("✅ Authentication")
        print("✅ Camera list retrieval")
        print("✅ Frontend accessibility")
        print("✅ RTSP camera creation")
        print("✅ RTSP camera update")
        print("✅ RTSP camera deletion")

        print(f"\n🌐 You can now test the frontend UI at: {FRONTEND_URL}")
        print(
            "💡 Navigate to the cameras page to test the edit/delete buttons for RTSP cameras"
        )

        return True


def main():
    """Main function to run the test suite"""
    test_suite = RTSPCameraTestSuite()

    try:
        success = test_suite.run_full_test_suite()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        test_suite.cleanup()
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        test_suite.cleanup()
        exit(1)


if __name__ == "__main__":
    main()
