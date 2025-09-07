#!/usr/bin/env python3
"""
Test script to validate mobile camera streaming compatibility fixes

This script tests the backend readiness for mobile camera streaming
after implementing the Android camera compatibility fixes.
"""

import asyncio
import logging
from typing import Dict

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MobileCameraCompatibilityTester:
    """Test mobile camera streaming compatibility after fixes"""

    def __init__(self):
        self.base_url = "http://localhost:8005"  # Cameras service
        self.gateway_url = "http://localhost:8080"  # Gateway service
        self.test_results = {}

    async def test_cameras_service_health(self) -> bool:
        """Test cameras service health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Cameras service health: {data}")
                        return True
                    else:
                        logger.error(
                            f"❌ Cameras service health failed: {response.status}"
                        )
                        return False
        except Exception as e:
            logger.error(f"❌ Cameras service connection failed: {e}")
            return False

    async def test_mobile_camera_registration_endpoint(self) -> bool:
        """Test mobile camera registration endpoint"""
        try:
            # Test mobile camera registration
            mobile_camera_data = {
                "device_id": "test_mobile_compatibility_fix",
                "device_name": "Test Mobile Camera (Compatibility Fix)",
                "device_type": "mobile",
                "capabilities": {
                    "video": True,
                    "audio": True,
                    "streaming": True,
                    "yuv420_support": True,  # New capability
                    "resolution_fallback": True,  # New capability
                },
                "network_info": {
                    "ip_address": "192.168.1.100",
                    "port": 8080,
                    "protocol": "http",
                },
                "camera_specs": {
                    "supported_resolutions": ["640x480", "1280x720", "320x240"],
                    "preferred_format": "yuv420",
                    "fallback_formats": ["yuv420", "nv21"],
                },
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/cameras/mobile", json=mobile_camera_data
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        logger.info(f"✅ Mobile camera registration successful: {data}")
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Registration failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Mobile camera registration test failed: {e}")
            return False

    async def test_streaming_session_creation(self) -> bool:
        """Test streaming session creation for mobile camera"""
        try:
            session_data = {
                "camera_id": "test_mobile_compatibility_fix",
                "stream_config": {
                    "format": "yuv420",
                    "resolution": "640x480",
                    "fps": 30,
                    "bitrate": 1000000,
                    "fallback_resolutions": ["480x320", "320x240"],
                },
                "compatibility_mode": True,  # New flag for compatibility mode
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/streaming/sessions", json=session_data
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        logger.info(f"✅ Streaming session creation successful: {data}")

                        # Store session info for cleanup
                        self.test_results["session_id"] = data.get("session_id")
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Streaming session creation failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Streaming session creation test failed: {e}")
            return False

    async def test_gateway_mobile_camera_integration(self) -> bool:
        """Test gateway integration for mobile cameras"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test gateway health
                async with session.get(f"{self.gateway_url}/health") as response:
                    if response.status != 200:
                        logger.error(
                            f"❌ Gateway health check failed: {response.status}"
                        )
                        return False

                # Test mobile camera listing through gateway
                async with session.get(
                    f"{self.gateway_url}/api/v1/cameras"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        mobile_cameras = [
                            cam
                            for cam in data.get("cameras", [])
                            if cam.get("device_type") == "mobile"
                        ]
                        logger.info(
                            f"✅ Gateway mobile cameras listing: {len(mobile_cameras)} mobile cameras found"
                        )
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Gateway mobile cameras listing failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Gateway mobile camera integration test failed: {e}")
            return False

    async def cleanup_test_data(self):
        """Clean up test data"""
        try:
            # Clean up streaming session
            if "session_id" in self.test_results:
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        f"{self.base_url}/api/v1/streaming/sessions/{self.test_results['session_id']}"
                    ) as response:
                        if response.status in [200, 204]:
                            logger.info("✅ Test streaming session cleaned up")
                        else:
                            logger.warning(
                                f"⚠️ Failed to cleanup streaming session: {response.status}"
                            )

            # Clean up test camera
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/api/v1/cameras/test_mobile_compatibility_fix"
                ) as response:
                    if response.status in [200, 204]:
                        logger.info("✅ Test mobile camera cleaned up")
                    else:
                        logger.warning(
                            f"⚠️ Failed to cleanup test camera: {response.status}"
                        )

        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all compatibility tests"""
        logger.info("🧪 Starting Mobile Camera Compatibility Tests")
        logger.info("=" * 60)

        tests = [
            ("Cameras Service Health", self.test_cameras_service_health),
            (
                "Mobile Camera Registration",
                self.test_mobile_camera_registration_endpoint,
            ),
            ("Streaming Session Creation", self.test_streaming_session_creation),
            ("Gateway Integration", self.test_gateway_mobile_camera_integration),
        ]

        results = {}

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
        logger.info("=" * 60)
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
        else:
            logger.error("💥 Some tests FAILED. Check the logs above for details.")

        return results


async def main():
    """Main test execution"""
    tester = MobileCameraCompatibilityTester()
    results = await tester.run_all_tests()

    # Exit with error code if any tests failed
    if not all(results.values()):
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
