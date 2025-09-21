#!/usr/bin/env python3
"""
Test script to simulate a recording_completed event and verify automatic face detection workflow.
"""

import asyncio
import json
import logging
from datetime import datetime

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8002"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU4MzgwMjA1fQ.lZ_aU-7j2kbkyxtB5emQicWQgB3GcFxp-f6KQSnEqtg"


async def test_recording_completed_event():
    """Test automatic face detection workflow triggered by recording completion."""

    # Simulate a recording_completed event payload
    event_payload = {
        "event_type": "recording_completed",
        "camera_device_id": "mobile_TKQ1.221114.001",
        "recording_session_id": f"test_session_{int(datetime.now().timestamp())}",
        "user_id": "7",
        "video_file_path": "/tmp/test_recording.mp4",
        "recording_duration_seconds": 30.5,
        "file_size_bytes": 1024000,
        "timestamp": datetime.now().isoformat(),
        "metadata": {"resolution": "1920x1080", "frame_rate": 30, "codec": "h264"},
    }

    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Send recording completion event to orchestrator
            logger.info(
                f"🎬 Sending recording_completed event for camera: {event_payload['camera_device_id']}"
            )

            async with session.post(
                f"{ORCHESTRATOR_URL}/workflows/camera/events",
                json=event_payload,
                headers=headers,
            ) as response:

                if response.status == 200:
                    response_data = await response.json()
                    logger.info("✅ Recording completion event processed successfully")
                    logger.info(f"📋 Response: {json.dumps(response_data, indent=2)}")

                    # Get workflow ID if available
                    workflow_id = response_data.get("workflow_id")
                    if workflow_id:
                        await check_workflow_status(session, workflow_id, headers)

                    return True
                else:
                    logger.error(f"❌ Failed to process event: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error: {error_text}")
                    return False

    except Exception as e:
        logger.error(f"❌ Exception during test: {e}")
        return False


async def check_workflow_status(session, workflow_id, headers):
    """Check the status of the face detection workflow."""
    try:
        logger.info(f"🔍 Checking workflow status: {workflow_id}")

        async with session.get(
            f"{ORCHESTRATOR_URL}/workflows/{workflow_id}", headers=headers
        ) as response:

            if response.status == 200:
                workflow_data = await response.json()
                logger.info("📊 Workflow Status:")
                logger.info(f"   Status: {workflow_data.get('status')}")
                logger.info(f"   Media Count: {workflow_data.get('total_media_count')}")
                logger.info(
                    f"   Processed: {workflow_data.get('processed_media_count')}"
                )
                logger.info(f"   Failed: {workflow_data.get('failed_media_count')}")

                # Check method lifecycles
                lifecycles = workflow_data.get("method_lifecycles", [])
                for lifecycle in lifecycles:
                    logger.info(
                        f"   Method: {lifecycle.get('method')} - Status: {lifecycle.get('status')}"
                    )

            else:
                logger.warning(f"⚠️ Could not get workflow status: {response.status}")

    except Exception as e:
        logger.warning(f"⚠️ Error checking workflow status: {e}")


async def test_camera_settings():
    """Verify camera settings are configured correctly."""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8005/api/v1/cameras/mobile_TKQ1.221114.001/settings",
                headers=headers,
            ) as response:

                if response.status == 200:
                    settings = await response.json()
                    logger.info("📷 Camera Settings:")
                    logger.info(
                        f"   Auto Face Detection: {settings.get('auto_face_detection')}"
                    )
                    logger.info(
                        f"   Store in Memory: {settings.get('store_faces_in_memory')}"
                    )
                    logger.info(
                        f"   Persist After Recording: {settings.get('persist_after_recording')}"
                    )

                    if settings.get("auto_face_detection"):
                        logger.info(
                            "✅ Camera is configured for automatic face detection"
                        )
                        return True
                    else:
                        logger.warning("⚠️ Auto face detection is not enabled")
                        return False
                else:
                    logger.error(f"❌ Could not get camera settings: {response.status}")
                    return False

    except Exception as e:
        logger.error(f"❌ Error checking camera settings: {e}")
        return False


async def main():
    """Run the complete test suite."""
    logger.info("🧪 Starting automatic face detection workflow test")
    logger.info("=" * 60)

    # Skip camera settings check (requires service auth)
    # Test the automatic face detection workflow directly
    logger.info("1️⃣ Simulating recording completion event...")
    event_ok = await test_recording_completed_event()

    if event_ok:
        logger.info("\n✅ Test completed successfully!")
        logger.info("🎯 Workflow should now be processing")
    else:
        logger.error("\n❌ Test failed")


if __name__ == "__main__":
    asyncio.run(main())
