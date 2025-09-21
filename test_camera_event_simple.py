#!/usr/bin/env python3
"""
Simple test fo    try:
        async with aiohttp.ClientSession() as session:
            # Send camera event to orchestrator with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }

            async with session.post(
                "http://localhost:8002/workflows/camera/events",
                json=event_data,
                headers=headers
            ) as response: event -> face detection workflow
"""

import asyncio
import json
import logging

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_camera_event_workflow():
    """Test camera recording completion event triggering face detection"""

    # Authentication token
    auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU4Mzk0OTQ1fQ.nM4DRL4iHLobo7ShYy9wZ6YPMPVji0_cYapoSZZdvqE"

    # Create a realistic camera event - updated schema based on OpenAPI
    event_data = {
        "event_type": "recording_completed",
        "camera_device_id": "test_camera_123",
        "recording_session_id": "session_test_456",
        "video_file_path": "/tmp/test_video.mp4",
        "user_id": "7",
        "recording_duration_seconds": 30,
        "file_size_bytes": 1024000,
        "metadata": {"resolution": "1920x1080", "fps": 30, "format": "mp4"},
    }

    print("🎥 Testing Camera Event -> Face Detection Workflow")
    print("=" * 60)
    print(f"📊 Event data: {json.dumps(event_data, indent=2)}")

    try:
        async with aiohttp.ClientSession() as session:
            # Send camera event to orchestrator
            async with session.post(
                "http://localhost:8002/api/v1/orchestrator/events/camera",
                json=event_data,
                headers={"Content-Type": "application/json"},
            ) as response:

                print(f"\n📡 Response status: {response.status}")
                response_text = await response.text()
                print(f"📄 Response body: {response_text}")

                if response.status == 200:
                    try:
                        response_data = json.loads(response_text)
                        workflow_id = response_data.get("workflow_id")

                        if workflow_id:
                            print(f"✅ Workflow created successfully: {workflow_id}")
                            print(
                                f"🔄 Workflow status: {response_data.get('workflow_status', 'unknown')}"
                            )

                            # Wait a bit for processing to start
                            await asyncio.sleep(2)

                            # Check workflow status
                            await check_workflow_status(session, workflow_id)

                        else:
                            print("⚠️ No workflow ID in response")
                    except json.JSONDecodeError:
                        print("⚠️ Response is not valid JSON")

                elif response.status == 403:
                    print("❌ Authentication error - 403 Forbidden")
                    print(
                        "   This suggests the status check authentication fix is needed"
                    )
                else:
                    print(f"❌ Unexpected response status: {response.status}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def check_workflow_status(session, workflow_id):
    """Check workflow status to test authentication"""
    try:
        auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU4Mzk0OTQ1fQ.nM4DRL4iHLobo7ShYy9wZ6YPMPVji0_cYapoSZZdvqE"

        print(f"\n🔍 Checking workflow status for: {workflow_id}")

        headers = {"Authorization": f"Bearer {auth_token}"}

        async with session.get(
            f"http://localhost:8002/workflows/face-detection/status/{workflow_id}",
            headers=headers,
        ) as response:

            print(f"📊 Status check response: {response.status}")

            if response.status == 200:
                status_data = await response.json()
                print(
                    f"✅ Status check successful: {json.dumps(status_data, indent=2)}"
                )
            elif response.status == 403:
                print("❌ Status check failed with 403 Forbidden")
                print("   This indicates authentication is still not working")
            else:
                text = await response.text()
                print(f"⚠️ Status check returned {response.status}: {text}")

    except Exception as e:
        print(f"❌ Status check error: {e}")


if __name__ == "__main__":
    asyncio.run(test_camera_event_workflow())
