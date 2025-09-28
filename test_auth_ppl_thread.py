#!/usr/bin/env python3
"""
Test PPL Thread workflow with proper authentication.
"""
import asyncio
import json
import logging
from typing import Optional

import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_auth_token() -> str:
    """Get authentication token from Node Service."""
    login_data = {"username": "fresh.user@example.com", "password": "NewPassword234!"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8001/api/v1/users/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["access_token"]
            else:
                raise Exception(f"Login failed: {response.status}")


async def create_vision_session(media_id: str, auth_token: str) -> Optional[str]:
    """Create a Vision Service session with authentication."""
    session_data = {"media_uuid": media_id, "session_type": "streaming"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8003/sessions/start", json=session_data, headers=headers
        ) as response:
            data = await response.json()
            logger.info(f"Session creation response: {response.status}")
            logger.info(f"Session data: {json.dumps(data, indent=2)}")

            if response.status == 200 and data.get("success"):
                return data.get("session_uuid")
            return None


async def trigger_ppl_workflow(session_uuid: str, auth_token: str) -> bool:
    """Trigger PPL Thread workflow with session UUID."""
    workflow_data = {
        "session_uuid": session_uuid,
        "tolerance_percent": 20.0,
        "enable_quality_analysis": True,
        "enable_age_detection": True,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8003/api/v1/person-objects/workflows/start",
            json=workflow_data,
            headers=headers,
        ) as response:
            data = await response.json()
            logger.info(f"Workflow trigger response: {response.status}")
            logger.info(f"Workflow data: {json.dumps(data, indent=2)}")

            return response.status == 200


async def test_authenticated_ppl_workflow():
    """Test complete PPL Thread workflow with authentication."""
    logger.info("🔐 Testing PPL Thread workflow with authentication")
    logger.info("=" * 60)

    # Test media UUIDs with face detection data
    test_media_ids = [
        "291ae808-c9b8-4eec-b835-97f72a108308",  # 12 faces
        "6cb0a76c-70da-441d-9411-9f5ae579ee0c",  # 16 faces
    ]

    try:
        # Step 1: Get authentication token
        logger.info("🎫 Getting authentication token...")
        auth_token = await get_auth_token()
        logger.info("✅ Authentication successful")

        for media_id in test_media_ids:
            logger.info(f"\n📹 Testing media: {media_id}")
            logger.info("-" * 50)

            # Step 2: Create session
            logger.info("🔧 Creating Vision Service session...")
            session_uuid = await create_vision_session(media_id, auth_token)

            if session_uuid:
                logger.info(f"✅ Session created: {session_uuid}")

                # Step 3: Trigger PPL workflow
                logger.info("🎯 Triggering PPL Thread workflow...")
                success = await trigger_ppl_workflow(session_uuid, auth_token)

                if success:
                    logger.info("✅ PPL Thread workflow triggered successfully")
                else:
                    logger.error("❌ PPL Thread workflow trigger failed")
            else:
                logger.error("❌ Session creation failed")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_authenticated_ppl_workflow())
