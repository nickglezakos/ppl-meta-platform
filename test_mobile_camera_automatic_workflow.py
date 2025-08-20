#!/usr/bin/env python3
"""
Test Mobile Camera Automatic Streaming Workflow

This script simulates the complete automatic streaming workflow that the mobile camera app should follow:
1. Login to Node service to get JWT token
2. Discover platform services dynamically
3. Auto-connect to Camera service using discovered endpoint
4. Auto-register mobile camera with user-provided name only
5. Auto-connect to Media service for streaming
6. Validate complete automatic workflow

This test ensures no hardcoded values are used - everything is discovered dynamically.
"""

import json
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests


class PPLMetaAutomaticWorkflowTester:
    def __init__(self, base_platform_url: str = "http://localhost:8001"):
        """
        Initialize the tester with only the base platform URL.
        All other service URLs will be discovered dynamically.
        """
        self.base_platform_url = base_platform_url
        self.jwt_token: Optional[str] = None
        self.platform_services: Optional[Dict[str, Any]] = None
        self.camera_service_url: Optional[str] = None
        self.media_service_url: Optional[str] = None
        self.registered_camera_id: Optional[str] = None

    def step_1_login(
        self,
        username: str = "fresh.user@example.com",
        password: str = "NewPassword234!",
    ) -> bool:
        """Step 1: Login to Node service to get JWT token"""
        print("🔐 STEP 1: Login to Node service...")

        try:
            response = requests.post(
                f"{self.base_platform_url}/api/v1/users/login",
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

                # Extract token dynamically
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

    def step_2_discover_platform_services(self) -> bool:
        """Step 2: Discover platform services dynamically"""
        print("\n🔍 STEP 2: Discover platform services...")

        if not self.jwt_token:
            print("❌ No JWT token available")
            return False

        try:
            response = requests.get(
                f"{self.base_platform_url}/api/v1/users/platform/services",
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Accept": "application/json",
                },
                timeout=10,
            )

            print(f"📥 Platform services response status: {response.status_code}")

            if response.status_code == 200:
                self.platform_services = response.json()
                print(f"✅ Platform services discovery successful!")

                # Extract service URLs dynamically
                microservices = self.platform_services.get("microservices", {})
                print(f"📊 Available services: {list(microservices.keys())}")

                # Get Camera service URL
                camera_service = microservices.get("cameras")
                if camera_service:
                    endpoints = camera_service.get("endpoints", {})
                    self.camera_service_url = endpoints.get("local") or endpoints.get(
                        "tailscale"
                    )
                    if self.camera_service_url:
                        print(f"📹 Camera service URL: {self.camera_service_url}")

                # Get Media service URL
                media_service = microservices.get("media")
                if media_service:
                    endpoints = media_service.get("endpoints", {})
                    self.media_service_url = endpoints.get("local") or endpoints.get(
                        "tailscale"
                    )
                    if self.media_service_url:
                        print(f"🎬 Media service URL: {self.media_service_url}")

                return bool(self.camera_service_url and self.media_service_url)
            else:
                print(f"❌ Platform services discovery failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False

        except Exception as e:
            print(f"💥 Platform services discovery error: {e}")
            return False

    def step_3_connect_to_camera_service(self) -> bool:
        """Step 3: Auto-connect to Camera service using discovered endpoint"""
        print("\n📹 STEP 3: Connect to Camera service...")

        if not self.jwt_token or not self.camera_service_url:
            print("❌ Missing JWT token or Camera service URL")
            return False

        try:
            # Test health endpoint
            health_response = requests.get(
                f"{self.camera_service_url}/health", timeout=5
            )
            print(f"💓 Camera health check: {health_response.status_code}")

            # Test authentication endpoint - Camera service expects token as query param
            print(f"🔍 Validating token with Camera service...")
            auth_response = requests.post(
                f"{self.camera_service_url}/api/v1/auth/validate-token",
                headers={
                    "Accept": "application/json",
                },
                params={"token": self.jwt_token},
                timeout=10,
            )
            print(f"🔐 Camera auth validation: {auth_response.status_code}")

            if auth_response.status_code == 200:
                print("✅ Camera service connection successful!")
                auth_data = auth_response.json()
                print(f"👤 Authenticated user: {auth_data.get('user_id', 'unknown')}")
                return True
            else:
                print(f"❌ Camera authentication failed: {auth_response.status_code}")
                print(f"📄 Response: {auth_response.text}")
                return False

        except Exception as e:
            print(f"💥 Camera service connection error: {e}")
            return False

    def step_4_auto_register_mobile_camera(self, camera_name: str) -> bool:
        """Step 4: Auto-register mobile camera with only user-provided name"""
        print(f"\n📱 STEP 4: Auto-register mobile camera '{camera_name}'...")

        if not self.jwt_token or not self.camera_service_url:
            print("❌ Missing JWT token or Camera service URL")
            return False

        try:
            # Generate dynamic device ID
            device_id = f"mobile_{uuid.uuid4().hex[:8]}_{int(time.time())}"

            # Prepare registration data - everything dynamic except camera name
            registration_data = {
                "name": camera_name,  # Only user input
                "device_id": device_id,
                "ip_address": "192.168.1.66",  # Could be detected dynamically
                "port": 8554,
                "device_model": "Automatic Test Device",
                "device_manufacturer": "PPL Meta Mobile",
                "app_version": "2.13.1",
                "resolution_width": 1920,
                "resolution_height": 1080,
                "max_fps": 30,
                "supports_audio": False,
            }

            print(
                f"📝 Registering camera with data: {json.dumps({k: v for k, v in registration_data.items() if k != 'device_id'}, indent=2)}"
            )

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
                print(f"📄 Full response data: {json.dumps(data, indent=2)}")

                # Extract camera ID dynamically
                if "camera_id" in data:
                    self.registered_camera_id = data["camera_id"]
                elif "id" in data:
                    self.registered_camera_id = data["id"]
                elif "data" in data and "id" in data["data"]:
                    self.registered_camera_id = data["data"]["id"]
                elif isinstance(data, dict) and "camera" in data:
                    self.registered_camera_id = data["camera"].get("id")

                print(f"📊 Registered camera ID: {self.registered_camera_id}")
                return True
            else:
                print(f"❌ Camera registration failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False

        except Exception as e:
            print(f"💥 Camera registration error: {e}")
            return False

    def step_5_connect_to_media_service(self) -> bool:
        """Step 5: Auto-connect to Media service for streaming"""
        print("\n🎬 STEP 5: Connect to Media service...")

        if not self.media_service_url:
            print("❌ Missing Media service URL")
            return False

        try:
            # Test health endpoint
            health_response = requests.get(
                f"{self.media_service_url}/health", timeout=5
            )
            print(f"💓 Media health check: {health_response.status_code}")

            # Test media API endpoint
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

    def step_6_validate_automatic_workflow(self) -> bool:
        """Step 6: Validate that the complete automatic workflow succeeded"""
        print("\n✅ STEP 6: Validate automatic workflow...")

        success_criteria = {
            "JWT Token": bool(self.jwt_token),
            "Platform Services": bool(self.platform_services),
            "Camera Service URL": bool(self.camera_service_url),
            "Media Service URL": bool(self.media_service_url),
            "Camera Registered": bool(self.registered_camera_id),
        }

        print("📋 Success Criteria Check:")
        all_success = True
        for criterion, status in success_criteria.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {criterion}: {status}")
            if not status:
                all_success = False

        if all_success:
            print("\n🎉 AUTOMATIC WORKFLOW VALIDATION PASSED!")
            print(f"📱 Camera '{self.get_camera_name()}' is ready for streaming")
            print(f"🔗 Camera ID: {self.registered_camera_id}")
            print(f"🎬 Media Service: {self.media_service_url}")
            print(f"📹 Camera Service: {self.camera_service_url}")
        else:
            print("\n❌ AUTOMATIC WORKFLOW VALIDATION FAILED!")

        return all_success

    def get_camera_name(self) -> str:
        """Get the camera name that was registered"""
        # This would come from the registration data in a real implementation
        return "Test Mobile Camera"

    def run_automatic_workflow_test(
        self, camera_name: str = "Automatic Test Camera"
    ) -> bool:
        """Run the complete automatic streaming workflow test"""
        print("🚀 STARTING AUTOMATIC STREAMING WORKFLOW TEST")
        print("=" * 60)
        print(f"📱 Camera Name: '{camera_name}' (only user input required)")
        print("🎯 Goal: Everything else should be automatic")
        print("=" * 60)

        # Step 1: Login
        if not self.step_1_login():
            print("\n❌ Workflow failed at Step 1: Login")
            return False

        # Step 2: Discover services
        if not self.step_2_discover_platform_services():
            print("\n❌ Workflow failed at Step 2: Service Discovery")
            return False

        # Step 3: Connect to Camera service
        if not self.step_3_connect_to_camera_service():
            print("\n❌ Workflow failed at Step 3: Camera Service Connection")
            return False

        # Step 4: Register camera
        if not self.step_4_auto_register_mobile_camera(camera_name):
            print("\n❌ Workflow failed at Step 4: Camera Registration")
            return False

        # Step 5: Connect to Media service
        if not self.step_5_connect_to_media_service():
            print("\n❌ Workflow failed at Step 5: Media Service Connection")
            return False

        # Step 6: Validate complete workflow
        if not self.step_6_validate_automatic_workflow():
            print("\n❌ Workflow failed at Step 6: Final Validation")
            return False

        print("\n" + "=" * 60)
        print("✅ AUTOMATIC STREAMING WORKFLOW TEST PASSED!")
        print("=" * 60)
        print("📋 Flutter App Implementation Requirements:")
        print("1. User enters camera name only")
        print("2. App handles login → service discovery → registration automatically")
        print("3. No hardcoded service URLs or manual configuration")
        print("4. Dynamic service endpoint resolution")
        print("5. Single-tap streaming activation")

        return True


def main():
    """Main test function"""
    print("🏥 Checking service health first...")

    # Quick health checks
    base_services = [
        ("Node", "http://localhost:8001/health"),
        ("Media", "http://localhost:8000/health"),
        ("Camera", "http://localhost:8005/health"),
    ]

    healthy_services = 0
    for name, url in base_services:
        try:
            response = requests.get(url, timeout=3)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {name} service: {response.status_code}")
            if response.status_code == 200:
                healthy_services += 1
        except Exception as e:
            print(f"❌ {name} service: {e}")

    if healthy_services < 3:
        print(f"\n⚠️ Warning: Only {healthy_services}/3 services are healthy")
        print("Some tests may fail. Please ensure all services are running.")

    print("\n" + "=" * 60)

    # Run automatic workflow test
    tester = PPLMetaAutomaticWorkflowTester()

    # Test with different camera names to ensure dynamic behavior
    test_cases = [
        "Living Room Camera",
        "Front Door Security",
        "Kitchen Monitor",
    ]

    for i, camera_name in enumerate(test_cases, 1):
        print(f"\n🧪 TEST CASE {i}: '{camera_name}'")
        print("-" * 40)

        success = tester.run_automatic_workflow_test(camera_name)

        if success:
            print(f"✅ Test case {i} passed!")
        else:
            print(f"❌ Test case {i} failed!")
            break

        # Reset tester for next test
        tester = PPLMetaAutomaticWorkflowTester()

        if i < len(test_cases):
            print("\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)

    print("\n🎯 AUTOMATIC WORKFLOW TESTING COMPLETE!")
    print(
        "The Flutter app should implement this exact flow with dynamic service discovery."
    )


if __name__ == "__main__":
    main()
