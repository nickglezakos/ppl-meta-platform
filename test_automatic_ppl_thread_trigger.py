#!/usr/bin/env python3
"""
PPL Meta Platform - Automatic PPL Thread Workflow Trigger Test
==============================================================

This test implements an event-driven mechanism to automatically trigger
the PPL Thread workflow when face detection completes, eliminating the
need for manual triggers or polling.

Event-Driven Architecture:
1. Listen for face detection workflow completion events
2. Extract session UUID from completed workflow
3. Automatically trigger PPL Thread workflow with session UUID
4. Verify complete end-to-end integration

Test Media: dce4c758-db32-4965-8741-f5c781d295a6 (61 faces detected)
Expected Result: Automatic person objects processing without manual intervention
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "http://localhost"
MEDIA_SERVICE_PORT = 8000
VISION_SERVICE_PORT = 8003
ORCHESTRATOR_PORT = 8080

# Test Configuration
TEST_MEDIA_ID = "dce4c758-db32-4965-8741-f5c781d295a6"
AUTH_TOKEN = None


class FaceDetectionWorkflowMonitor:
    """
    Event-driven monitor for face detection workflow completion.

    This class implements a WebSocket-like event system to detect when
    face detection workflows complete and automatically trigger PPL Thread.
    """

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        self.active_workflows = {}
        self.event_callbacks = {}

    async def register_workflow_event_listener(self, workflow_id: str, callback):
        """Register an event callback for workflow completion."""
        self.event_callbacks[workflow_id] = callback
        logger.info(
            f"📡 EVENT LISTENER: Registered callback for workflow {workflow_id}"
        )

    async def check_workflow_completion(self, workflow_id: str) -> Optional[Dict]:
        """Check if a workflow has completed and extract session data."""
        try:
            url = f"{BASE_URL}:{MEDIA_SERVICE_PORT}/api/v1/workflow/face-detection/status/{workflow_id}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                if status == "completed":
                    logger.info(f"✅ WORKFLOW COMPLETED: {workflow_id}")
                    logger.info(f"📊 Results: {data.get('results_summary', {})}")

                    # Extract session information for PPL Thread triggering
                    session_data = await self.extract_session_data(workflow_id)
                    return {
                        "workflow_id": workflow_id,
                        "status": status,
                        "results": data.get("results_summary", {}),
                        "session_data": session_data,
                    }
                elif status == "failed":
                    logger.error(
                        f"❌ WORKFLOW FAILED: {workflow_id} - {data.get('error_message')}"
                    )
                    return {
                        "workflow_id": workflow_id,
                        "status": "failed",
                        "error": data.get("error_message"),
                    }
                else:
                    logger.info(f"⏳ WORKFLOW STATUS: {workflow_id} - {status}")
                    return None
            else:
                logger.error(
                    f"❌ Failed to check workflow status: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"❌ Error checking workflow status: {e}")
            return None

    async def extract_session_data(self, workflow_id: str) -> Optional[Dict]:
        """Extract session UUID and media mapping from completed workflow."""
        try:
            # Check if a session was created for the media in this workflow
            url = f"{BASE_URL}:{VISION_SERVICE_PORT}/sessions/media/{TEST_MEDIA_ID}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                session_data = response.json()
                session_uuid = session_data.get("session_uuid")

                if session_uuid:
                    logger.info(
                        f"🔑 SESSION EXTRACTED: {session_uuid} for media {TEST_MEDIA_ID}"
                    )
                    return {
                        "session_uuid": session_uuid,
                        "media_id": TEST_MEDIA_ID,
                        "workflow_id": workflow_id,
                    }
                else:
                    logger.warning(f"⚠️ No session UUID found in response")
                    return None
            else:
                logger.warning(f"⚠️ No session found for media {TEST_MEDIA_ID}")
                return None

        except Exception as e:
            logger.error(f"❌ Error extracting session data: {e}")
            return None

    async def trigger_ppl_thread_workflow(self, session_data: Dict) -> bool:
        """Automatically trigger PPL Thread workflow using session UUID."""
        try:
            session_uuid = session_data.get("session_uuid")
            media_id = session_data.get("media_id")

            if not session_uuid:
                logger.error("❌ Cannot trigger PPL Thread: No session UUID available")
                return False

            logger.info(
                f"🚀 TRIGGERING PPL THREAD: session={session_uuid}, media={media_id}"
            )

            # Trigger PPL Thread workflow
            url = f"{BASE_URL}:{VISION_SERVICE_PORT}/api/v1/person-objects/workflow/trigger"
            payload = {
                "media_id": media_id,
                "session_uuid": session_uuid,
                "automatic_trigger": True,
                "triggered_by": "face_detection_completion_event",
            }

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                success = result.get("success", False)

                if success:
                    logger.info(
                        f"✅ PPL THREAD TRIGGERED: {result.get('merged_groups', 0)} persons from {result.get('original_groups', 0)} faces"
                    )
                    return True
                else:
                    logger.error(f"❌ PPL Thread trigger failed: {result}")
                    return False
            else:
                logger.error(
                    f"❌ PPL Thread trigger HTTP error: {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error triggering PPL Thread workflow: {e}")
            return False

    async def workflow_completion_event_handler(self, workflow_data: Dict):
        """Event handler for workflow completion - automatically triggers PPL Thread."""
        workflow_id = workflow_data.get("workflow_id")
        status = workflow_data.get("status")
        session_data = workflow_data.get("session_data")

        logger.info(
            f"🎯 EVENT TRIGGERED: Workflow {workflow_id} completed with status {status}"
        )

        if status == "completed" and session_data:
            # Automatically trigger PPL Thread workflow
            success = await self.trigger_ppl_thread_workflow(session_data)

            if success:
                logger.info(
                    f"🎉 AUTOMATIC TRIGGER SUCCESS: PPL Thread completed for {workflow_id}"
                )
                return True
            else:
                logger.error(
                    f"💥 AUTOMATIC TRIGGER FAILED: PPL Thread failed for {workflow_id}"
                )
                return False
        else:
            logger.warning(
                f"⚠️ Cannot trigger PPL Thread: status={status}, session_data={bool(session_data)}"
            )
            return False


class AutomaticPPLThreadTriggerTest:
    """
    Test class for automatic PPL Thread triggering using event-driven architecture.
    """

    def __init__(self):
        self.auth_token = None
        self.monitor = None

    async def authenticate(self) -> bool:
        """Authenticate and get JWT token."""
        try:
            url = f"{BASE_URL}:8001/api/v1/users/login"
            data = {"username": "fresh.user@example.com", "password": "NewPassword234!"}
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = requests.post(url, data=data, headers=headers)

            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data.get("access_token")
                logger.info("✅ AUTHENTICATION: Successfully obtained JWT token")

                # Initialize monitor with token
                self.monitor = FaceDetectionWorkflowMonitor(self.auth_token)
                return True
            else:
                logger.error(f"❌ AUTHENTICATION FAILED: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False

    async def verify_face_detection_status(self) -> Dict:
        """Verify current face detection status for test media."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            url = f"{BASE_URL}:{VISION_SERVICE_PORT}/faces/media/{TEST_MEDIA_ID}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                has_faces = data.get("has_stored_faces", False)
                total_faces = data.get("total_faces", 0)

                logger.info(
                    f"📊 FACE DETECTION STATUS: {total_faces} faces, stored={has_faces}"
                )
                return {"has_faces": has_faces, "total_faces": total_faces}
            else:
                logger.error(
                    f"❌ Failed to check face detection status: {response.status_code}"
                )
                return {"has_faces": False, "total_faces": 0}

        except Exception as e:
            logger.error(f"❌ Error checking face detection status: {e}")
            return {"has_faces": False, "total_faces": 0}

    async def verify_person_objects_status(self) -> Dict:
        """Verify current person objects status for test media."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            url = f"{BASE_URL}:{ORCHESTRATOR_PORT}/api/v1/orchestrator/person-objects/{TEST_MEDIA_ID}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                total_persons = data.get("total_persons", 0)
                total_faces = data.get("total_faces", 0)
                status = data.get("status", "unknown")

                logger.info(
                    f"👥 PERSON OBJECTS STATUS: {total_persons} persons, {total_faces} faces, status={status}"
                )
                return {
                    "total_persons": total_persons,
                    "total_faces": total_faces,
                    "status": status,
                }
            else:
                logger.error(
                    f"❌ Failed to check person objects status: {response.status_code}"
                )
                return {"total_persons": 0, "total_faces": 0, "status": "error"}

        except Exception as e:
            logger.error(f"❌ Error checking person objects status: {e}")
            return {"total_persons": 0, "total_faces": 0, "status": "error"}

    async def trigger_face_detection_workflow(self) -> Optional[str]:
        """Trigger face detection workflow and return workflow ID."""
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }
            url = f"{BASE_URL}:{MEDIA_SERVICE_PORT}/api/v1/workflow/face-detection/bulk-process"

            payload = {
                "media_ids": [TEST_MEDIA_ID],
                "method": "two_stage",
                "confidence_threshold": 0.5,
                "store_results": True,
                "workflow_metadata": {
                    "test_run": True,
                    "automatic_ppl_trigger_test": True,
                    "test_timestamp": datetime.now().isoformat(),
                },
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                workflow_id = data.get("workflow_id")
                status = data.get("status")

                logger.info(
                    f"🎬 FACE DETECTION WORKFLOW STARTED: {workflow_id}, status={status}"
                )
                return workflow_id
            else:
                logger.error(
                    f"❌ Failed to start face detection workflow: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"❌ Error starting face detection workflow: {e}")
            return None

    async def run_event_driven_test(self):
        """Run the complete event-driven test."""
        logger.info("🎯 STARTING EVENT-DRIVEN PPL THREAD TRIGGER TEST")
        logger.info("=" * 60)

        # Step 1: Authenticate
        logger.info("1️⃣ STEP 1: Authentication")
        if not await self.authenticate():
            logger.error("💥 TEST FAILED: Authentication failed")
            return False

        # Step 2: Verify initial status
        logger.info("\n2️⃣ STEP 2: Initial Status Verification")
        face_status = await self.verify_face_detection_status()
        person_status = await self.verify_person_objects_status()

        # Step 3: Start face detection workflow
        logger.info("\n3️⃣ STEP 3: Start Face Detection Workflow")
        workflow_id = await self.trigger_face_detection_workflow()

        if not workflow_id:
            logger.error("💥 TEST FAILED: Could not start face detection workflow")
            return False

        # Step 4: Register event listener for automatic PPL Thread triggering
        logger.info("\n4️⃣ STEP 4: Register Event-Driven PPL Thread Trigger")
        await self.monitor.register_workflow_event_listener(
            workflow_id, self.monitor.workflow_completion_event_handler
        )

        # Step 5: Monitor workflow with event-driven approach
        logger.info("\n5️⃣ STEP 5: Event-Driven Workflow Monitoring")
        max_wait_time = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # Check for workflow completion event
            workflow_result = await self.monitor.check_workflow_completion(workflow_id)

            if workflow_result:
                status = workflow_result.get("status")

                if status == "completed":
                    logger.info("🎉 EVENT DETECTED: Face detection workflow completed!")

                    # Trigger event handler (automatic PPL Thread trigger)
                    success = await self.monitor.workflow_completion_event_handler(
                        workflow_result
                    )

                    if success:
                        logger.info(
                            "✅ EVENT-DRIVEN SUCCESS: PPL Thread automatically triggered!"
                        )
                        break
                    else:
                        logger.error(
                            "💥 EVENT-DRIVEN FAILURE: PPL Thread trigger failed"
                        )
                        return False

                elif status == "failed":
                    logger.error("💥 TEST FAILED: Face detection workflow failed")
                    return False

            # Brief wait before next event check (not polling - event checking)
            await asyncio.sleep(1)
        else:
            logger.error("⏰ TEST TIMEOUT: Workflow did not complete within time limit")
            return False

        # Step 6: Verify final results
        logger.info("\n6️⃣ STEP 6: Final Results Verification")
        await asyncio.sleep(2)  # Allow PPL Thread to complete

        final_face_status = await self.verify_face_detection_status()
        final_person_status = await self.verify_person_objects_status()

        # Step 7: Test Results Summary
        logger.info("\n7️⃣ STEP 7: Test Results Summary")
        logger.info("=" * 60)

        success = (
            final_face_status.get("has_faces", False)
            and final_face_status.get("total_faces", 0) > 0
            and final_person_status.get("total_persons", 0) > 0
            and final_person_status.get("status") == "completed"
        )

        if success:
            logger.info("🎉 EVENT-DRIVEN TEST SUCCESS!")
            logger.info(
                f"   ✅ Face Detection: {final_face_status.get('total_faces', 0)} faces"
            )
            logger.info(
                f"   ✅ Person Objects: {final_person_status.get('total_persons', 0)} persons"
            )
            logger.info(f"   ✅ Status: {final_person_status.get('status')}")
            logger.info("   ✅ Automatic PPL Thread trigger working!")
        else:
            logger.error("💥 EVENT-DRIVEN TEST FAILED!")
            logger.error(f"   ❌ Face Detection: {final_face_status}")
            logger.error(f"   ❌ Person Objects: {final_person_status}")

        return success


async def main():
    """Main test execution."""
    test = AutomaticPPLThreadTriggerTest()

    try:
        success = await test.run_event_driven_test()

        if success:
            logger.info(
                "\n🎉 ALL TESTS PASSED: Event-driven PPL Thread trigger working!"
            )
            sys.exit(0)
        else:
            logger.error(
                "\n💥 TESTS FAILED: Event-driven PPL Thread trigger not working!"
            )
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Unexpected test error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
