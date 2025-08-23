#!/usr/bin/env python3
"""
Mobile Camera API Test Script
Tests all mobile camera endpoints with proper authentication
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import requests


class MobileCameraAPITester:
    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.jwt_token = self._generate_jwt_token()

    def _generate_jwt_token(self) -> str:
        """Generate JWT token using NODE_SERVICE_SECRET for testing"""
        # This is the same secret used in the running cameras service
        node_secret = "RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4"

        # Create payload similar to what Node service would send
        payload = {
            "sub": "7",  # User ID (using same as in logs)
            "exp": datetime.utcnow() + timedelta(hours=1),  # 1 hour expiry
            "iat": datetime.utcnow(),
        }

        # Generate token using NODE_SERVICE_SECRET
        token = jwt.encode(payload, node_secret, algorithm="HS256")
        print(f"✅ Generated JWT token for testing: {token[:50]}...")
        return str(token)  # Ensure it's returned as string

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        auth_required: bool = True,
    ) -> requests.Response:
        """Make HTTP request with authentication"""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()

        # Add authentication headers
        if auth_required and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            raise

    def _print_response(self, response: requests.Response, test_name: str):
        """Print formatted response details"""
        print(f"\n🔍 {test_name}")
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.url}")

        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response (text): {response.text[:500]}")

        if response.status_code >= 400:
            print(f"❌ Test failed with status {response.status_code}")
        else:
            print(f"✅ Test passed with status {response.status_code}")

    def test_health_check(self):
        """Test if the cameras service is running"""
        print("\n" + "=" * 60)
        print("🏥 HEALTH CHECK")
        print("=" * 60)

        response = self._make_request("GET", "/health/", auth_required=False)
        self._print_response(response, "Health Check")
        return response.status_code == 200

    def test_register_mobile_camera(self):
        """Test mobile camera registration"""
        print("\n" + "=" * 60)
        print("📱 MOBILE CAMERA REGISTRATION")
        print("=" * 60)

        registration_data = {
            "name": "Test Mobile Device",
            "device_id": "mobile_test_device_001",
            "ip_address": "192.168.1.100",
            "port": 8554,
            "device_model": "iPhone 15 Pro",
            "device_manufacturer": "Apple",
            "app_version": "1.0.0",
            "resolution_width": 1920,
            "resolution_height": 1080,
            "max_fps": 30,
            "supports_audio": True,
        }

        response = self._make_request(
            "POST", "/api/v1/cameras/mobile", data=registration_data
        )
        self._print_response(response, "Mobile Camera Registration")
        return response.status_code in [200, 201]

    def test_list_mobile_cameras(self):
        """Test listing mobile cameras"""
        print("\n" + "=" * 60)
        print("📋 LIST MOBILE CAMERAS")
        print("=" * 60)

        response = self._make_request("GET", "/api/v1/cameras/mobile")
        self._print_response(response, "List Mobile Cameras")
        return response.status_code == 200

    def test_mobile_camera_heartbeat(self):
        """Test mobile camera heartbeat"""
        print("\n" + "=" * 60)
        print("💓 MOBILE CAMERA HEARTBEAT")
        print("=" * 60)

        # Heartbeat data is optional, can be any Dict or None
        heartbeat_data = {
            "battery_level": 85,
            "signal_strength": -45,
            "app_status": "active",
        }

        response = self._make_request(
            "POST",
            "/api/v1/cameras/mobile/mobile_test_device_001/heartbeat",
            data=heartbeat_data,
        )
        self._print_response(response, "Mobile Camera Heartbeat")
        return response.status_code == 200

    def test_update_mobile_camera(self):
        """Test mobile camera update"""
        print("\n" + "=" * 60)
        print("🔄 UPDATE MOBILE CAMERA")
        print("=" * 60)

        update_data = {
            "status": "connected",
            "resolution_width": 3840,
            "resolution_height": 2160,
            "current_fps": 60,
            "battery_level": 75,
        }

        response = self._make_request(
            "PUT", "/api/v1/cameras/mobile/mobile_test_device_001", data=update_data
        )
        self._print_response(response, "Update Mobile Camera")
        return response.status_code == 200

    def test_get_mobile_camera_info(self):
        """Test getting mobile camera info"""
        print("\n" + "=" * 60)
        print("ℹ️  GET MOBILE CAMERA INFO")
        print("=" * 60)

        response = self._make_request(
            "GET", "/api/v1/cameras/mobile_test_device_001/info"
        )
        self._print_response(response, "Get Mobile Camera Info")
        return response.status_code == 200

    def test_unregister_mobile_camera(self):
        """Test mobile camera unregistration"""
        print("\n" + "=" * 60)
        print("🗑️  UNREGISTER MOBILE CAMERA")
        print("=" * 60)

        response = self._make_request(
            "DELETE", "/api/v1/cameras/mobile/mobile_test_device_001"
        )
        self._print_response(response, "Unregister Mobile Camera")
        return response.status_code in [200, 204]

    def run_all_tests(self):
        """Run all mobile camera API tests"""
        print("🚀 Starting Mobile Camera API Tests...")
        print(f"Base URL: {self.base_url}")
        print(f"JWT Token: {self.jwt_token[:50]}...")

        tests = [
            ("Health Check", self.test_health_check),
            ("Register Mobile Camera", self.test_register_mobile_camera),
            ("List Mobile Cameras", self.test_list_mobile_cameras),
            ("Mobile Camera Heartbeat", self.test_mobile_camera_heartbeat),
            ("Update Mobile Camera", self.test_update_mobile_camera),
            ("Get Mobile Camera Info", self.test_get_mobile_camera_info),
            ("Unregister Mobile Camera", self.test_unregister_mobile_camera),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                success = test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}: {test_name}")

        print(f"\n🎯 Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Mobile Camera API is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the logs above for details.")

        return passed == total


def main():
    """Main test runner"""
    print("🎯 PPL Meta Mobile Camera API Test Suite")
    print("=" * 60)

    # Test connectivity first
    tester = MobileCameraAPITester()

    # Run all tests
    success = tester.run_all_tests()

    exit_code = 0 if success else 1
    print(f"\n🏁 Exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    exit(main())
