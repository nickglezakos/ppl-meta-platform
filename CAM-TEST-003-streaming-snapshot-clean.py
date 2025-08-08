#!/usr/bin/env python3
"""
CAM-TEST-003: Video Streaming and Snapshot Capture Testing
=========================================================

This test validates the video streaming and snapshot capture capabilities.
"""

import base64
import json
import os
import time
from typing import Dict, List, Optional

import requests


class StreamingTestSuite:
    """Video streaming and snapshot capture test suite."""

    def __init__(self):
        self.base_url = "http://localhost:8005"
        self.node_url = "http://localhost:8001"
        self.auth_token = None
        self.detected_cameras = []
        self.connected_cameras = []
        self.test_results = []
        self.snapshots_dir = "/tmp/cam_test_snapshots"

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

    def authenticate_user(self) -> bool:
        """Step 1: Authenticate with Node service."""
        print("🔐 Step 1: User Authentication")

        try:
            response = requests.post(
                f"{self.node_url}/api/v1/users/login",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="username=fresh.user@example.com&password=NewPassword234!",
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")

                self.log_test(
                    "Node Authentication",
                    True,
                    f"Token obtained: {self.auth_token[:20]}...",
                )
                return True
            else:
                self.log_test(
                    "Node Authentication",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except (requests.RequestException, ValueError, KeyError) as e:
            self.log_test("Node Authentication", False, f"Exception: {e}")
            return False

    def detect_and_connect_camera(self) -> bool:
        """Step 2: Detect cameras and connect to first one."""
        print("\n📷 Step 2: Camera Detection and Connection")

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            # Detect cameras
            response = requests.post(
                f"{self.base_url}/api/v1/cameras/detect",
                headers=headers,
                params={"save_to_db": True},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self.detected_cameras = data.get("cameras", [])
                detected_count = data.get("detected_count", 0)

                self.log_test(
                    "Camera Detection",
                    True,
                    f"Detected {detected_count} cameras",
                )

                if detected_count == 0:
                    self.log_test("Camera Detection", False, "No cameras found")
                    return False

                # Connect to first camera
                device_id = self.detected_cameras[0].get("device_id")
                if not device_id:
                    self.log_test("Camera Connection", False, "No device_id found")
                    return False

                response = requests.post(
                    f"{self.base_url}/api/v1/cameras/{device_id}/connect",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    self.connected_cameras.append(device_id)
                    self.log_test(
                        "Camera Connection",
                        True,
                        f"Connected to {device_id}",
                    )
                    return True
                else:
                    self.log_test(
                        "Camera Connection",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                    )
                    return False
            else:
                self.log_test(
                    "Camera Detection",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except (requests.RequestException, ValueError, KeyError) as e:
            self.log_test("Camera Detection/Connection", False, f"Exception: {e}")
            return False

    def test_video_streaming(self) -> bool:
        """Step 3: Test video streaming operations."""
        print("\n🎥 Step 3: Video Streaming Operations")

        if not self.connected_cameras:
            self.log_test("Video Streaming", False, "No cameras connected")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            device_id = self.connected_cameras[0]

            # Start streaming
            print(f"    Starting stream for {device_id}...")
            response = requests.post(
                f"{self.base_url}/api/v1/streaming/{device_id}/start",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                stream_data = response.json()
                self.log_test(
                    "Start Video Stream",
                    True,
                    f"Stream started for {device_id}",
                )

                print(f"    Stream URL: {stream_data.get('stream_url', 'N/A')}")

                # Wait for stream to stabilize
                time.sleep(3)

                # Test video stream data retrieval
                print("    Testing video stream data retrieval...")
                try:
                    stream_response = requests.get(
                        f"{self.base_url}/api/v1/streaming/{device_id}/video",
                        headers=headers,
                        timeout=5,
                        stream=True,
                    )

                    if stream_response.status_code == 200:
                        # Read a small amount of stream data
                        data_chunk = stream_response.raw.read(1024)
                        if len(data_chunk) > 0:
                            self.log_test(
                                "Video Stream Data",
                                True,
                                f"Retrieved {len(data_chunk)} bytes of stream data",
                            )
                        else:
                            self.log_test(
                                "Video Stream Data",
                                False,
                                "No stream data received",
                            )
                    else:
                        self.log_test(
                            "Video Stream Data",
                            False,
                            f"HTTP {stream_response.status_code}",
                        )
                except (requests.RequestException, ValueError) as stream_e:
                    self.log_test(
                        "Video Stream Data",
                        False,
                        f"Stream data error: {stream_e}",
                    )

                # Stop streaming
                print(f"    Stopping stream for {device_id}...")
                time.sleep(2)
                response = requests.post(
                    f"{self.base_url}/api/v1/streaming/{device_id}/stop",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    self.log_test(
                        "Stop Video Stream",
                        True,
                        f"Stream stopped for {device_id}",
                    )
                    return True
                else:
                    self.log_test(
                        "Stop Video Stream",
                        False,
                        f"HTTP {response.status_code}: {response.text}",
                    )
                    return False
            else:
                self.log_test(
                    "Start Video Stream",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except (requests.RequestException, ValueError, KeyError) as e:
            self.log_test("Video Streaming", False, f"Exception: {e}")
            return False

    def test_snapshot_capture(self) -> bool:
        """Step 4: Test snapshot capture."""
        print("\n📸 Step 4: Snapshot Capture Testing")

        if not self.connected_cameras:
            self.log_test("Snapshot Capture", False, "No cameras connected")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            device_id = self.connected_cameras[0]

            # Create snapshots directory
            os.makedirs(self.snapshots_dir, exist_ok=True)

            # Capture snapshot
            print(f"    Capturing snapshot from {device_id}...")
            response = requests.get(
                f"{self.base_url}/api/v1/streaming/{device_id}/snapshot",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                snapshot_data = response.json()

                # Extract image data
                image_data = snapshot_data.get("data", "")
                if image_data.startswith("data:image/jpeg;base64,"):
                    # Remove data URL prefix
                    base64_data = image_data.replace("data:image/jpeg;base64,", "")

                    # Decode and save image
                    image_bytes = base64.b64decode(base64_data)
                    timestamp = int(time.time())
                    filename = f"snapshot_{device_id}_{timestamp}.jpg"
                    filepath = os.path.join(self.snapshots_dir, filename)

                    with open(filepath, "wb") as f:
                        f.write(image_bytes)

                    # Verify file was created
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        self.log_test(
                            "Snapshot Capture",
                            True,
                            f"Saved {filename} ({file_size} bytes)",
                        )

                        # Log snapshot details
                        size_info = snapshot_data.get("size", {})
                        print(
                            f"    Resolution: {size_info.get('width', 'N/A')}x{size_info.get('height', 'N/A')}"
                        )
                        print(f"    Format: {snapshot_data.get('format', 'N/A')}")
                        print(f"    File: {filepath}")

                        return True
                    else:
                        self.log_test(
                            "Snapshot Capture",
                            False,
                            "File not created successfully",
                        )
                        return False
                else:
                    self.log_test(
                        "Snapshot Capture",
                        False,
                        "Invalid image data format",
                    )
                    return False
            else:
                self.log_test(
                    "Snapshot Capture",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except (requests.RequestException, ValueError, KeyError, OSError) as e:
            self.log_test("Snapshot Capture", False, f"Exception: {e}")
            return False

    def cleanup_resources(self) -> bool:
        """Step 5: Cleanup resources and disconnect cameras."""
        print("\n🧹 Step 5: Resource Cleanup")

        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}

            for device_id in self.connected_cameras:
                response = requests.post(
                    f"{self.base_url}/api/v1/cameras/{device_id}/disconnect",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    self.log_test(
                        "Camera Disconnect",
                        True,
                        f"Disconnected {device_id}",
                    )
                else:
                    self.log_test(
                        "Camera Disconnect",
                        False,
                        f"Failed to disconnect {device_id}",
                    )

            # Verify no active connections
            response = requests.get(
                f"{self.base_url}/api/v1/cameras/active",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                active_data = response.json()
                active_count = active_data.get("active_count", 0)

                if active_count == 0:
                    self.log_test(
                        "Cleanup Verification",
                        True,
                        "No active connections remaining",
                    )
                    return True
                else:
                    self.log_test(
                        "Cleanup Verification",
                        False,
                        f"{active_count} connections still active",
                    )
                    return False
            else:
                self.log_test(
                    "Cleanup Verification",
                    False,
                    "Could not verify cleanup",
                )
                return False

        except (requests.RequestException, ValueError, KeyError) as e:
            self.log_test("Resource Cleanup", False, f"Exception: {e}")
            return False

    def run_tests(self) -> Dict:
        """Run all streaming and snapshot tests."""
        print("🎥 Starting CAM-TEST-003: Video Streaming and Snapshot Capture Test")
        print("=" * 70)

        start_time = time.time()

        # Test sequence
        tests = [
            ("Authentication", self.authenticate_user),
            ("Camera Setup", self.detect_and_connect_camera),
            ("Video Streaming", self.test_video_streaming),
            ("Snapshot Capture", self.test_snapshot_capture),
            ("Resource Cleanup", self.cleanup_resources),
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            try:
                success = test_func()
                if success:
                    passed_tests += 1
            except (requests.RequestException, ValueError, KeyError, OSError) as e:
                self.log_test(test_name, False, f"Test exception: {e}")

        # Summary
        duration = time.time() - start_time
        success_rate = (passed_tests / total_tests) * 100

        print("\n" + "=" * 70)
        print("🎉 CAM-TEST-003 Video Streaming and Snapshot Test COMPLETED!")
        print("=" * 70)
        print("✅ Test Results Summary:")
        print(f"• Total Tests: {total_tests}")
        print(f"• Passed: {passed_tests}")
        print(f"• Failed: {total_tests - passed_tests}")
        print(f"• Success Rate: {success_rate:.1f}%")
        print(f"• Duration: {duration:.1f} seconds")

        if os.path.exists(self.snapshots_dir):
            snapshot_files = os.listdir(self.snapshots_dir)
            if snapshot_files:
                print(f"• Captured Snapshots: {len(snapshot_files)}")
                print(f"• Snapshots Location: {self.snapshots_dir}")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "duration": duration,
            "test_results": self.test_results,
        }


def main():
    """Main test execution."""
    suite = StreamingTestSuite()
    results = suite.run_tests()

    # Exit with appropriate code
    if results["passed_tests"] == results["total_tests"]:
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
