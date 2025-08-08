#!/usr/bin/env python3
"""
CAM-TEST-002: Comprehensive Camera Lifecycle Management Testing
=============================================================

This test validates the complete camera management workflow including:
1. Authentication with Node service
2. Camera detection and database persistence
3. Camera connection management
4. Streaming operations
5. Recording operations
6. Camera disconnection and cleanup
7. Error handling and edge cases

Prerequisites:
- All PPL Meta services running (Node, Camera, Gateway, etc.)
- User credentials: fresh.user@example.com / NewPassword234!
- At least one camera available for testing
"""

import json
import time
from typing import Dict, List, Optional

import requests


class CameraTestSuite:
    """Comprehensive camera management test suite."""

    def __init__(self):
        self.base_url = "http://localhost:8005"
        self.node_url = "http://localhost:8001"
        self.auth_token = None
        self.detected_cameras = []
        self.connected_cameras = []
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    └─ {details}")

        self.test_results.append(
            {
                "test": test_name,
                "success": success,
                "details": details,
                "timestamp": time.time(),
            }
        )

    def authenticate(self) -> bool:
        """Step 1: Authenticate with Node service."""
        print("\n🔐 Step 1: Authentication")

        try:
            response = requests.post(
                f"{self.node_url}/api/v1/users/login",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="username=fresh.user@example.com&password=NewPassword234!",
            )

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.log_test(
                    "Node Service Authentication",
                    True,
                    f"Token obtained: {self.auth_token[:20]}...",
                )
                return True
            else:
                self.log_test(
                    "Node Service Authentication",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test("Node Service Authentication", False, f"Exception: {e}")
            return False

    def test_camera_detection(self) -> bool:
        """Step 2: Test camera detection and database persistence."""
        print("\n📹 Step 2: Camera Detection")

        if not self.auth_token:
            self.log_test("Camera Detection", False, "No authentication token")
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }

            # Test camera detection with database save
            response = requests.post(
                f"{self.base_url}/api/v1/cameras/detect",
                headers=headers,
                params={"save_to_db": True},
            )

            if response.status_code == 200:
                data = response.json()
                self.detected_cameras = data.get("cameras", [])
                detected_count = data.get("detected_count", 0)
                saved_count = data.get("saved_count", 0)

                self.log_test(
                    "Camera Detection",
                    True,
                    f"Detected {detected_count} cameras, saved {saved_count} to DB",
                )

                # Log camera details
                for camera in self.detected_cameras:
                    print(
                        f"    📷 {camera.get('name', 'Unknown')} ({camera.get('device_id', 'N/A')})"
                    )
                    print(f"        Type: {camera.get('camera_type', 'Unknown')}")
                    print(
                        f"        Resolution: {camera.get('resolution_width', 0)}x{camera.get('resolution_height', 0)}"
                    )
                    print(f"        Max FPS: {camera.get('max_fps', 0)}")

                return detected_count > 0
            else:
                self.log_test(
                    "Camera Detection",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test("Camera Detection", False, f"Exception: {e}")
            return False

    def test_camera_listing(self) -> bool:
        """Step 3: Test camera listing from database."""
        print("\n📋 Step 3: Camera Listing")

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            response = requests.get(f"{self.base_url}/api/v1/cameras/", headers=headers)

            if response.status_code == 200:
                cameras = response.json()
                self.log_test(
                    "Camera Listing",
                    True,
                    f"Retrieved {len(cameras)} cameras from database",
                )

                for camera in cameras:
                    print(
                        f"    📷 ID: {camera.get('id')} | {camera.get('name')} | Status: {camera.get('status')}"
                    )

                return len(cameras) > 0
            else:
                self.log_test(
                    "Camera Listing",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test("Camera Listing", False, f"Exception: {e}")
            return False

    def test_camera_connection(self) -> bool:
        """Step 4: Test camera connection."""
        print("\n🔌 Step 4: Camera Connection")

        if not self.detected_cameras:
            self.log_test("Camera Connection", False, "No cameras detected")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            camera = self.detected_cameras[0]  # Test with first detected camera
            device_id = camera.get("device_id")

            response = requests.post(
                f"{self.base_url}/api/v1/cameras/{device_id}/connect", headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                self.connected_cameras.append(device_id)
                self.log_test(
                    "Camera Connection",
                    True,
                    f"Connected to {device_id}: {data.get('message', 'Success')}",
                )
                return True
            else:
                self.log_test(
                    "Camera Connection",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test("Camera Connection", False, f"Exception: {e}")
            return False

    def test_camera_streaming(self) -> bool:
        """Step 5: Test camera streaming operations."""
        print("\n🎥 Step 5: Camera Streaming")

        if not self.connected_cameras:
            self.log_test("Camera Streaming", False, "No cameras connected")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            device_id = self.connected_cameras[0]

            # Start streaming
            response = requests.post(
                f"{self.base_url}/api/v1/cameras/{device_id}/stream/start",
                headers=headers,
            )

            if response.status_code == 200:
                self.log_test(
                    "Start Streaming", True, f"Started stream for {device_id}"
                )

                # Wait a moment
                time.sleep(2)

                # Stop streaming
                response = requests.post(
                    f"{self.base_url}/api/v1/cameras/{device_id}/stream/stop",
                    headers=headers,
                )

                if response.status_code == 200:
                    self.log_test(
                        "Stop Streaming", True, f"Stopped stream for {device_id}"
                    )
                    return True
                else:
                    self.log_test(
                        "Stop Streaming",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                    )
                    return False
            else:
                self.log_test(
                    "Start Streaming",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test("Camera Streaming", False, f"Exception: {e}")
            return False

    def test_camera_recording(self) -> bool:
        """Step 6: Test camera recording operations."""
        print("\n🎬 Step 6: Camera Recording")

        if not self.connected_cameras:
            self.log_test("Camera Recording", False, "No cameras connected")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            device_id = self.connected_cameras[0]

            # Start recording
            response = requests.post(
                f"{self.base_url}/api/v1/cameras/{device_id}/record/start",
                headers=headers,
            )

            if response.status_code == 200:
                self.log_test(
                    "Start Recording", True, f"Started recording for {device_id}"
                )

                # Record for a few seconds
                time.sleep(3)

                # Stop recording
                response = requests.post(
                    f"{self.base_url}/api/v1/cameras/{device_id}/record/stop",
                    headers=headers,
                )

                if response.status_code == 200:
                    self.log_test(
                        "Stop Recording", True, f"Stopped recording for {device_id}"
                    )
                    return True
                else:
                    self.log_test(
                        "Stop Recording",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                    )
                    return False
            else:
                self.log_test(
                    "Start Recording",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test("Camera Recording", False, f"Exception: {e}")
            return False

    def test_camera_disconnection(self) -> bool:
        """Step 7: Test camera disconnection."""
        print("\n🔌 Step 7: Camera Disconnection")

        success_count = 0

        for device_id in self.connected_cameras:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"}

                response = requests.post(
                    f"{self.base_url}/api/v1/cameras/{device_id}/disconnect",
                    headers=headers,
                )

                if response.status_code == 200:
                    self.log_test(
                        f"Disconnect {device_id}", True, "Successfully disconnected"
                    )
                    success_count += 1
                else:
                    self.log_test(
                        f"Disconnect {device_id}", False, f"HTTP {response.status_code}"
                    )

            except Exception as e:
                self.log_test(f"Disconnect {device_id}", False, f"Exception: {e}")

        return success_count == len(self.connected_cameras)

    def test_error_handling(self) -> bool:
        """Step 8: Test error handling scenarios."""
        print("\n🚫 Step 8: Error Handling")

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # Test invalid camera ID
            response = requests.post(
                f"{self.base_url}/api/v1/cameras/invalid_camera_id/connect",
                headers=headers,
            )

            if response.status_code in [400, 404]:
                self.log_test(
                    "Invalid Camera ID Handling",
                    True,
                    "Properly rejected invalid camera ID",
                )
            else:
                self.log_test(
                    "Invalid Camera ID Handling",
                    False,
                    f"Unexpected response: {response.status_code}",
                )

            # Test unauthorized access
            response = requests.get(f"{self.base_url}/api/v1/cameras/")

            if response.status_code == 401:
                self.log_test(
                    "Unauthorized Access Handling",
                    True,
                    "Properly rejected unauthorized request",
                )
                return True
            else:
                self.log_test(
                    "Unauthorized Access Handling",
                    False,
                    f"Unexpected response: {response.status_code}",
                )
                return False

        except Exception as e:
            self.log_test("Error Handling", False, f"Exception: {e}")
            return False

    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("📊 CAM-TEST-002 COMPREHENSIVE REPORT")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"📈 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success Rate: {(passed_tests/total_tests*100):.1f}%")

        print(f"\n📹 Camera Summary:")
        print(f"   Detected Cameras: {len(self.detected_cameras)}")
        print(f"   Connected Cameras: {len(self.connected_cameras)}")

        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")

        print(f"\n🎯 Overall Result: {'✅ PASS' if failed_tests == 0 else '❌ FAIL'}")

        # Save detailed report
        report = {
            "test_suite": "CAM-TEST-002",
            "timestamp": time.time(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests / total_tests * 100,
            },
            "cameras": {
                "detected": self.detected_cameras,
                "connected_count": len(self.connected_cameras),
            },
            "detailed_results": self.test_results,
        }

        with open(
            "/Users/nickgklezakos/Documents/ppl-meta-code/CAM-TEST-002-report.json", "w"
        ) as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Detailed report saved to: CAM-TEST-002-report.json")

    def run_comprehensive_test(self):
        """Execute the complete camera lifecycle test suite."""
        print("🚀 Starting CAM-TEST-002: Comprehensive Camera Lifecycle Management")
        print("=" * 70)

        # Execute test steps in sequence
        steps = [
            self.authenticate,
            self.test_camera_detection,
            self.test_camera_listing,
            self.test_camera_connection,
            self.test_camera_streaming,
            self.test_camera_recording,
            self.test_camera_disconnection,
            self.test_error_handling,
        ]

        for step in steps:
            if not step():
                print(
                    f"\n⚠️  Critical failure in {step.__name__}, continuing with remaining tests..."
                )
                # Continue with other tests even if one fails

        self.generate_report()


if __name__ == "__main__":
    test_suite = CameraTestSuite()
    test_suite.run_comprehensive_test()
