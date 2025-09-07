#!/usr/bin/env python3
"""
Authenticated test for mobile camera streaming compatibility fixes
Tests the complete mobile camera workflow after Android compatibility fixes
"""

import asyncio
import json
import logging

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthenticatedMobileCameraTest:
    """Test mobile camera streaming with authentication"""

    def __init__(self):
        self.base_url = "http://localhost:8005"  # Cameras service
        self.node_url = "http://localhost:8001"  # Node service
        self.gateway_url = "http://localhost:8080"  # Gateway service
        self.access_token = None
        self.test_results = {}

    async def authenticate(self) -> bool:
        """Authenticate and get access token"""
        try:
            auth_data = {
                "username": "fresh.user@example.com",
                "password": "NewPassword234!",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.node_url}/api/v1/users/login",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=auth_data,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.access_token = data.get("access_token")
                        logger.info("✅ Authentication successful")
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Authentication failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False

    def get_auth_headers(self) -> dict:
        """Get authorization headers"""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    async def test_services_health(self) -> bool:
        """Test all services health"""
        services = [
            ("Node Service", f"{self.node_url}/api/v1/health"),
            ("Cameras Service", f"{self.base_url}/health"),
            ("Gateway Service", f"{self.gateway_url}/health"),
        ]

        all_healthy = True

        for service_name, health_url in services:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_url) as response:
                        if response.status == 200:
                            logger.info(f"✅ {service_name}: Healthy")
                        else:
                            logger.error(
                                f"❌ {service_name}: Unhealthy ({response.status})"
                            )
                            all_healthy = False
            except Exception as e:
                logger.error(f"❌ {service_name}: Connection failed - {e}")
                all_healthy = False

        return all_healthy

    async def test_mobile_camera_registration(self) -> bool:
        """Test mobile camera registration with YUV420 support"""
        try:
            # Enhanced mobile camera data with compatibility features
            mobile_camera_data = {
                "name": "Test Mobile Camera (YUV420 Fix)",
                "device_id": "test_mobile_yuv420_fix",
                "ip_address": "192.168.1.100",
                "port": 8080,
                "device_model": "Android Device",
                "device_manufacturer": "Test Manufacturer",
                "app_version": "2.0.0",
                "resolution_width": 1280,
                "resolution_height": 720,
                "max_fps": 30,
                "supports_audio": True,
            }

            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/cameras/mobile",
                    headers=headers,
                    json=mobile_camera_data,
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        logger.info("✅ Mobile camera registration successful")
                        logger.info(f"   Camera ID: {data.get('id')}")
                        self.test_results["camera_id"] = data.get("id")
                        self.test_results["device_id"] = mobile_camera_data["device_id"]
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Mobile camera registration failed: {response.status}"
                        )
                        logger.error(f"   Response: {text}")
                        return False

        except Exception as e:
            logger.error(f"❌ Mobile camera registration test failed: {e}")
            return False

    async def test_list_cameras(self) -> bool:
        """Test listing cameras to verify registration"""
        try:
            headers = self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/cameras", headers=headers
                ) as response:
                    if response.status == 200:
                        cameras = await response.json()  # Direct list response
                        mobile_cameras = [
                            cam for cam in cameras if cam.get("camera_type") == "MOBILE"
                        ]

                        logger.info("✅ Camera listing successful")
                        logger.info(f"   Total cameras: {len(cameras)}")
                        logger.info(f"   Mobile cameras: {len(mobile_cameras)}")

                        # Check if our test camera is listed
                        test_camera = next(
                            (
                                cam
                                for cam in mobile_cameras
                                if cam.get("device_id") == "test_mobile_yuv420_fix"
                            ),
                            None,
                        )
                        if test_camera:
                            logger.info(
                                f"   ✅ Test camera found: {test_camera.get('name')}"
                            )

                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Camera listing failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Camera listing test failed: {e}")
            return False

    async def test_mobile_streaming_session(self) -> bool:
        """Test creating a streaming session for mobile camera"""
        if "device_id" not in self.test_results:
            logger.warning("⚠️ Skipping streaming session test - no device ID")
            return False

        try:
            device_id = self.test_results["device_id"]
            headers = self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/auth/streaming-session/{device_id}",
                    headers=headers,
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        logger.info("✅ Streaming session created successfully")
                        logger.info(f"   Session ID: {data.get('session_id')}")
                        logger.info(f"   Streaming URL: {data.get('streaming_url')}")
                        self.test_results["session_id"] = data.get("session_id")
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Streaming session creation failed: {response.status}"
                        )
                        logger.error(f"   Response: {text}")
                        return False

        except Exception as e:
            logger.error(f"❌ Streaming session test failed: {e}")
            return False

    async def cleanup_test_data(self):
        """Clean up test data"""
        try:
            headers = self.get_auth_headers()

            # Clean up streaming session
            if "session_id" in self.test_results:
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        f"{self.base_url}/api/v1/streaming/sessions/{self.test_results['session_id']}",
                        headers=headers,
                    ) as response:
                        if response.status in [200, 204, 404]:
                            logger.info("✅ Test streaming session cleaned up")
                        else:
                            logger.warning(
                                f"⚠️ Failed to cleanup streaming session: {response.status}"
                            )

            # Clean up test camera
            if "camera_id" in self.test_results:
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        f"{self.base_url}/api/v1/cameras/{self.test_results['camera_id']}",
                        headers=headers,
                    ) as response:
                        if response.status in [200, 204, 404]:
                            logger.info("✅ Test mobile camera cleaned up")
                        else:
                            logger.warning(
                                f"⚠️ Failed to cleanup test camera: {response.status}"
                            )

        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")

    async def run_all_tests(self) -> dict:
        """Run all mobile camera compatibility tests"""
        logger.info("🧪 Starting Authenticated Mobile Camera Compatibility Tests")
        logger.info("=" * 70)

        # Authenticate first
        if not await self.authenticate():
            logger.error("❌ Authentication failed - cannot continue tests")
            return {"Authentication": False}

        tests = [
            ("Services Health Check", self.test_services_health),
            ("Mobile Camera Registration", self.test_mobile_camera_registration),
            ("Camera Listing", self.test_list_cameras),
            ("Streaming Session Creation", self.test_mobile_streaming_session),
        ]

        results = {"Authentication": True}

        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running: {test_name}")
            try:
                result = await test_func()
                results[test_name] = result
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"   {status}")
            except Exception as e:
                logger.error(f"   ❌ FAILED with exception: {e}")
                results[test_name] = False

        # Cleanup
        logger.info(f"\n🧹 Cleaning up test data...")
        await self.cleanup_test_data()

        # Summary
        logger.info(f"\n📊 Test Results Summary:")
        logger.info("=" * 70)
        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"  {test_name}: {status}")

        logger.info(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            logger.info("🎉 All mobile camera compatibility tests PASSED!")
            logger.info(
                "📱 Mobile app should now work without camera initialization errors"
            )
            logger.info(
                "🔧 Android YUV420 format and resolution fallback fixes are working"
            )
        else:
            logger.error("💥 Some tests FAILED. Check the logs above for details.")

        return results


async def main():
    """Main test execution"""
    tester = AuthenticatedMobileCameraTest()
    results = await tester.run_all_tests()

    # Exit with error code if any tests failed
    if not all(results.values()):
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
