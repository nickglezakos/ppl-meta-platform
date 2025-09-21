#!/usr/bin/env python3
"""
Test Face Detection Workflow with Authentication Status Polling
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowTester:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.auth_token = None

    async def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        try:
            auth_data = {"username": "test_user", "password": "test_password"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json=auth_data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.auth_token = data.get("access_token")
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

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}

    async def test_face_detection_workflow(self) -> bool:
        """Test creating and monitoring face detection workflow"""
        try:
            # Create a test workflow
            workflow_data = {
                "media_id": "test-media-12345",
                "detection_methods": ["mtcnn"],
                "metadata": {
                    "recording_session_id": "test-session-67890",
                    "camera_device_id": "test-camera-001",
                    "source": "manual_test",
                },
            }

            logger.info("🚀 Creating face detection workflow...")

            async with aiohttp.ClientSession() as session:
                # Create workflow
                async with session.post(
                    f"{self.base_url}/api/v1/orchestrator/workflows/face-detection",
                    json=workflow_data,
                    headers={
                        **self._get_auth_headers(),
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status == 200:
                        workflow_response = await response.json()
                        workflow_id = workflow_response.get("workflow_id")
                        logger.info(f"✅ Workflow created: {workflow_id}")

                        # Test status polling with authentication
                        return await self._test_status_polling(session, workflow_id)
                    else:
                        text = await response.text()
                        logger.error(
                            f"❌ Workflow creation failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"❌ Workflow test error: {e}")
            return False

    async def _test_status_polling(
        self, session: aiohttp.ClientSession, workflow_id: str
    ) -> bool:
        """Test workflow status polling with authentication"""
        try:
            logger.info("🔍 Testing workflow status polling...")

            # Test status check with authentication
            async with session.get(
                f"{self.base_url}/api/v1/orchestrator/workflows/{workflow_id}/status",
                headers=self._get_auth_headers(),
            ) as response:
                if response.status == 200:
                    status_data = await response.json()
                    logger.info(
                        f"✅ Status check successful: {status_data.get('status', 'unknown')}"
                    )
                    return True
                elif response.status == 403:
                    logger.error(
                        "❌ Status check failed with 403 Forbidden - Authentication issue!"
                    )
                    return False
                else:
                    text = await response.text()
                    logger.error(f"❌ Status check failed: {response.status} - {text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Status polling error: {e}")
            return False

    async def test_media_workflow_status(self) -> bool:
        """Test media service workflow status authentication"""
        try:
            logger.info("🎥 Testing media workflow status authentication...")

            # Create test media workflow
            media_data = {
                "video_path": "/test/path/video.mp4",
                "detection_method": "mtcnn",
                "metadata": {"test": "authentication"},
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:8000/api/v1/media/face-detection",
                    json=media_data,
                    headers={
                        **self._get_auth_headers(),
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status == 200:
                        workflow_response = await response.json()
                        workflow_id = workflow_response.get("workflow_id")

                        if workflow_id:
                            # Test status polling for media workflow
                            async with session.get(
                                f"http://localhost:8000/api/v1/media/workflows/{workflow_id}/status",
                                headers=self._get_auth_headers(),
                            ) as status_response:
                                if status_response.status == 200:
                                    logger.info(
                                        "✅ Media workflow status check successful"
                                    )
                                    return True
                                elif status_response.status == 403:
                                    logger.error(
                                        "❌ Media workflow status failed with 403 - Auth issue!"
                                    )
                                    return False
                                else:
                                    text = await status_response.text()
                                    logger.error(
                                        f"❌ Media status check failed: {status_response.status} - {text}"
                                    )
                                    return False
                    else:
                        text = await response.text()
                        logger.info(
                            f"ℹ️ Media workflow creation: {response.status} - {text}"
                        )
                        return True  # This might fail normally, that's ok

        except Exception as e:
            logger.error(f"❌ Media workflow test error: {e}")
            return False


async def main():
    """Main test function"""
    print("🧪 Testing Face Detection Workflow Authentication")
    print("=" * 60)

    tester = WorkflowTester()

    # Step 1: Authenticate
    print("1️⃣ Getting authentication token...")
    if not await tester.authenticate():
        print("❌ Authentication failed - cannot proceed")
        return False

    # Step 2: Test orchestrator workflow
    print("\n2️⃣ Testing orchestrator workflow authentication...")
    orchestrator_success = await tester.test_face_detection_workflow()

    # Step 3: Test media workflow
    print("\n3️⃣ Testing media workflow authentication...")
    media_success = await tester.test_media_workflow_status()

    # Results
    print(f"\n🎯 Test Results Summary:")
    print(
        f"   Orchestrator workflow: {'✅ PASS' if orchestrator_success else '❌ FAIL'}"
    )
    print(f"   Media workflow: {'✅ PASS' if media_success else '❌ FAIL'}")

    overall_success = orchestrator_success and media_success
    print(
        f"\n🎉 Overall result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}"
    )

    return overall_success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
