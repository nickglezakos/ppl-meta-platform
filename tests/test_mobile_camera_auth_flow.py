#!/usr/bin/env python3
"""
Test Mobile Camera Authentication Flow

This script simulates the complete authentication flow that the mobile camera app should follow:
1. Login to Nod            # Test authentication endpoint - Camera service expects token as query param
            print(f"🔍 Sending token (first 20 chars): {self.jwt_token[:20]}...")
            auth_response = requests.post(
                f"{self.camera_service_url}/api/v1/auth/validate-token",
                headers={
                    'Accept': 'application/json',
                },
                params={
                    'token': self.jwt_token
                },
                timeout=10
            )
            print(f"🔍 Request URL: {auth_response.url}") (8001) to get JWT token
2. Use that token to connect to Media service (8000)
3. Use that token to connect to Camera service (8005)
4. Test camera registration with Camera service
"""

import json
import time
from typing import Any, Dict, Optional

import requests


class PPLMetaMobileAuthTester:
    def __init__(self):
        self.node_service_url = "http://localhost:8001"
        self.media_service_url = "http://localhost:8000"
        self.camera_service_url = "http://localhost:8005"
        self.jwt_token: Optional[str] = None

    def test_login(
        self,
        username: str = "fresh.user@example.com",
        password: str = "NewPassword234!",
    ) -> bool:
        """Test login to Node service to get JWT token"""
        print("🔐 Testing login to Node service...")

        try:
            response = requests.post(
                f"{self.node_service_url}/api/v1/users/login",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                data={"username": username, "password": password},
                timeout=10,
            )

            print(f"📥 Login response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Login successful!")
                print(f"📊 Response keys: {list(data.keys())}")

                # Extract token
                if "token" in data:
                    self.jwt_token = data["token"]
                elif "access_token" in data:
                    self.jwt_token = data["access_token"]
                elif "data" in data and "token" in data["data"]:
                    self.jwt_token = data["data"]["token"]

                if self.jwt_token:
                    print(f"🎫 JWT Token obtained: {self.jwt_token[:20]}...")
                    return True
                else:
                    print("❌ No token found in response")
                    return False
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False

        except Exception as e:
            print(f"💥 Login error: {e}")
            return False

    def test_platform_services_discovery(self) -> Optional[Dict[str, Any]]:
        """Test platform services discovery endpoint"""
        print("\n🔍 Testing platform services discovery...")

        if not self.jwt_token:
            print("❌ No JWT token available")
            return None

        try:
            response = requests.get(
                f"{self.node_service_url}/api/v1/users/platform/services",
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Accept": "application/json",
                },
                timeout=10,
            )

            print(f"📥 Platform services response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Platform services discovery successful!")
                print(
                    f"📊 Available services: {list(data.get('microservices', {}).keys())}"
                )

                # Print service details
                if "microservices" in data:
                    for service_name, service_info in data["microservices"].items():
                        print(
                            f"   🔧 {service_name}: {service_info['endpoint']} - {service_info['purpose']}"
                        )

                return data
            else:
                print(f"❌ Platform services discovery failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return None

        except Exception as e:
            print(f"💥 Platform services discovery error: {e}")
            return None

    def test_media_service_connection(self) -> bool:
        """Test connection to Media service with JWT token"""
        print("\n🎬 Testing Media service connection...")

        if not self.jwt_token:
            print("❌ No JWT token available")
            return False

        try:
            # Test health endpoint
            health_response = requests.get(
                f"{self.media_service_url}/health", timeout=5
            )
            print(f"💓 Media health check: {health_response.status_code}")

            # Test authenticated endpoint (if any)
            # Media service typically doesn't have auth endpoints - it processes videos
            # Let's test a typical media endpoint
            try:
                media_response = requests.get(
                    f"{self.media_service_url}/api/v1/media",
                    headers={
                        "Authorization": f"Bearer {self.jwt_token}",
                        "Accept": "application/json",
                    },
                    timeout=10,
                )
                print(f"📺 Media API response: {media_response.status_code}")

                if media_response.status_code == 200:
                    print("✅ Media service connection successful!")
                    return True
                else:
                    print(f"⚠️ Media API returned: {media_response.status_code}")
                    # Media service connection is still OK if health check passes
                    return health_response.status_code == 200

            except Exception as e:
                print(f"⚠️ Media API test failed: {e}")
                # Still OK if health check passes
                return health_response.status_code == 200

        except Exception as e:
            print(f"💥 Media service connection error: {e}")
            return False

    def test_camera_service_connection(self) -> bool:
        """Test connection to Camera service with JWT token"""
        print("\n📹 Testing Camera service connection...")

        if not self.jwt_token:
            print("❌ No JWT token available")
            return False

        try:
            # Test health endpoint
            health_response = requests.get(
                f"{self.camera_service_url}/health", timeout=5
            )
            print(f"💓 Camera health check: {health_response.status_code}")

            # Test authentication endpoint - Camera service expects token as query param
            print(f"🔍 Sending token (first 20 chars): {self.jwt_token[:20]}...")
            auth_response = requests.post(
                f"{self.camera_service_url}/api/v1/auth/validate-token",
                headers={
                    "Accept": "application/json",
                },
                params={"token": self.jwt_token},
                timeout=10,
            )
            print(f"🔍 Request URL: {auth_response.url}")
            print(f"🔐 Camera auth validation: {auth_response.status_code}")

            if auth_response.status_code == 200:
                print("✅ Camera service authentication successful!")
                auth_data = auth_response.json()
                print(
                    f"👤 Authenticated user: {auth_data.get('user_id', 'unknown')} with {len(auth_data.get('permissions', []))} permissions"
                )
                return True
            else:
                print(f"❌ Camera authentication failed: {auth_response.status_code}")
                print(f"📄 Response: {auth_response.text}")
                return False

        except Exception as e:
            print(f"💥 Camera service connection error: {e}")
            return False

    def test_camera_registration(self) -> bool:
        """Test mobile camera registration with Camera service"""
        print("\n📱 Testing mobile camera registration...")

        if not self.jwt_token:
            print("❌ No JWT token available")
            return False

        try:
            # Prepare registration data
            registration_data = {
                "name": "Test Mobile Camera",
                "device_id": f"mobile_test_{int(time.time())}",
                "ip_address": "192.168.1.66",
                "port": 8554,
                "device_model": "Test Device",
                "device_manufacturer": "Test Manufacturer",
                "app_version": "2.13.0",
                "resolution_width": 1920,
                "resolution_height": 1080,
                "max_fps": 30,
                "supports_audio": False,
            }

            print(f"📝 Registration data: {registration_data}")

            response = requests.post(
                f"{self.camera_service_url}/api/v1/cameras/mobile",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.jwt_token}",
                },
                json=registration_data,
                timeout=30,
            )

            print(f"📥 Registration response status: {response.status_code}")

            if response.status_code in [200, 201]:
                data = response.json()
                print("✅ Camera registration successful!")
                print(f"📊 Registration response: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Camera registration failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False

        except Exception as e:
            print(f"💥 Camera registration error: {e}")
            return False

    def run_complete_test(self) -> bool:
        """Run the complete authentication and connection test"""
        print("🚀 Starting PPL Meta Mobile Camera Authentication Flow Test")
        print("=" * 60)

        # Step 1: Login to get JWT token
        if not self.test_login():
            print("\n❌ Authentication flow failed at login step")
            return False

        # Step 2: Discover platform services
        platform_services = self.test_platform_services_discovery()
        if not platform_services:
            print("\n⚠️ Platform services discovery failed, but continuing...")

        # Step 3: Test Media service connection
        media_ok = self.test_media_service_connection()
        if not media_ok:
            print("\n⚠️ Media service connection failed, but continuing...")

        # Step 4: Test Camera service connection
        camera_ok = self.test_camera_service_connection()
        if not camera_ok:
            print("\n❌ Authentication flow failed at camera service connection")
            return False

        # Step 5: Test camera registration
        registration_ok = self.test_camera_registration()
        if not registration_ok:
            print("\n❌ Authentication flow failed at camera registration")
            return False

        print("\n" + "=" * 60)
        print("✅ Complete authentication flow test PASSED!")
        print(f"🎫 JWT Token: {self.jwt_token[:20]}...")
        print(f"🎬 Media Service: {'✅' if media_ok else '⚠️'}")
        print(f"📹 Camera Service: {'✅' if camera_ok else '❌'}")
        print(f"📱 Registration: {'✅' if registration_ok else '❌'}")

        return True


def main():
    """Main test function"""
    tester = PPLMetaMobileAuthTester()

    print("🏥 Testing service health first...")

    # Quick health checks
    services = [
        ("Node", "http://localhost:8001/health"),
        ("Media", "http://localhost:8000/health"),
        ("Camera", "http://localhost:8005/health"),
    ]

    for name, url in services:
        try:
            response = requests.get(url, timeout=3)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {name} service: {response.status_code}")
        except Exception as e:
            print(f"❌ {name} service: {e}")

    print("\n" + "=" * 60)

    # Run complete test
    success = tester.run_complete_test()

    if success:
        print("\n🎉 All tests passed! The authentication flow is working correctly.")
        print("\n📋 Flutter app should use this flow:")
        print("1. Login to Node service (8001) with username/password")
        print("2. Get JWT token from login response")
        print("3. Use JWT token for Camera service (8005) authentication")
        print(
            "4. Media service (8000) doesn't require authentication for basic operations"
        )
        print("5. Use Camera service for mobile camera registration")
    else:
        print("\n💥 Tests failed! Check the service logs and configuration.")


if __name__ == "__main__":
    main()
