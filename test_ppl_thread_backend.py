#!/usr/bin/env python3
"""
Test script for automatic PPL Thread workflow integration.

This tests the complete backend flow:
1. Face detection completes -> 2. Orchestrator auto-triggers PPL Thread -> 3. Vision Service stores results
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
GATEWAY_URL = "http://localhost:8080"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU4OTE4MDk2fQ.z0AMMmO02xiihhbEfjrnfRYJvU5zYLGEacxF0dNYGQs"

# Test media UUIDs (real UUIDs that have stored face detection data)
TEST_MEDIA_UUIDS = [
    "291ae808-c9b8-4eec-b835-97f72a108308",  # Real UUID with 12 stored faces
    "6cb0a76c-70da-441d-9411-9f5ae579ee0c",  # Real UUID with 16 stored faces
]


async def test_orchestrator_service_health():
    """Test Orchestrator Service is running."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ORCHESTRATOR_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info("✅ Vision Service is healthy")
                    logger.info(
                        f"📋 Service Info: {health_data.get('service', 'Unknown')}"
                    )
                    return True
                else:
                    logger.error(
                        f"❌ Orchestrator Service unhealthy: {response.status}"
                    )
                    return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to Orchestrator Service: {e}")
        return False


async def get_auth_token() -> str:
    """Get authentication token."""
    login_response = requests.post(
        f"{NODE_BASE_URL}/api/v1/users/login",
        data={"username": "fresh.user@example.com", "password": "NewPassword234!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if login_response.status_code == 200:
        return login_response.json()["access_token"]
    else:
        raise Exception(f"Authentication failed: {login_response.status_code}")


def test_workflow_trigger(media_id: str, description: str) -> bool:
    """Test triggering PPL Thread workflow for media."""
    logger.info(f"🎯 Testing PPL Thread workflow for media: {media_id}")

    # Get authentication token
    auth_token = get_auth_token()

    # Trigger PPL Thread workflow with auth
    trigger_response = requests.post(
        f"{ORCHESTRATOR_BASE_URL}/person-objects/trigger",
        json={"media_id": media_id},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )

    logger.info(f"📡 Workflow trigger response: {trigger_response.status_code}")

    if trigger_response.status_code == 200:
        logger.info("✅ PPL Thread workflow triggered successfully")
        data = trigger_response.json()
        persons = data.get("person_count", 0)
        faces = data.get("face_count", 0)
        status = data.get("status", "unknown")
        logger.info(f"📊 Results: {persons} persons from {faces} faces")
        logger.info(f"📈 Status: {status}")
        return status == "success"
    else:
        logger.error(
            f"❌ Failed to trigger PPL Thread workflow: {trigger_response.status_code}"
        )
        try:
            error_data = trigger_response.json()
            logger.error(f"Error details: {error_data}")
        except:
            logger.error(f"Error text: {trigger_response.text}")
        return False


def test_person_data_retrieval(media_uuid: str) -> Dict:
    """Test retrieving person objects data for media."""
    logger.info(f"\n📊 Testing person data retrieval for media: {media_uuid}")

    async def fetch_data():
        # Get auth token
        auth_token = get_auth_token()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ORCHESTRATOR_BASE_URL}/person-objects/{media_uuid}",
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                logger.info(f"📡 Data retrieval response: {response.status}")

                if response.status == 200:
                    logger.info("✅ Person objects data retrieved successfully")
                    data = await response.json()

                    total_persons = data.get("person_count", 0)
                    total_faces = data.get("face_count", 0)
                    status = data.get("status", "unknown")

                    logger.info(
                        f"📊 Data: {total_persons} persons from {total_faces} faces"
                    )
                    logger.info(f"📈 Status: {status}")

                    if total_persons > 0:
                        logger.info(
                            f"🎉 SUCCESS: Found {total_persons} persons for media {media_uuid}"
                        )
                        return {
                            "success": True,
                            "person_count": total_persons,
                            "face_count": total_faces,
                            "status": status,
                        }
                    else:
                        logger.info(
                            f"ℹ️ No persons found yet for media {media_uuid} (status: {status})"
                        )
                        return {
                            "success": True,
                            "person_count": 0,
                            "face_count": total_faces,
                            "status": status,
                        }
                else:
                    logger.error(f"❌ Failed to retrieve data: {response.status}")
                    return {
                        "success": False,
                        "person_count": 0,
                        "face_count": 0,
                        "status": "error",
                    }

    return asyncio.run(fetch_data())


async def test_complete_workflow():
    """Test the complete workflow: trigger + retrieve."""
    logger.info("\n🧪 Testing Complete PPL Thread Workflow")
    logger.info("=" * 60)

    # Test health first
    if not await test_orchestrator_service_health():
        logger.error("❌ Cannot proceed - Vision Service is not available")
        return False

    success_count = 0
    total_tests = len(TEST_MEDIA_UUIDS)

    for media_uuid in TEST_MEDIA_UUIDS:
        logger.info(f"\n📹 Testing media UUID: {media_uuid}")
        logger.info("-" * 40)

        # Step 1: Trigger PPL Thread workflow
        trigger_result = await test_ppl_thread_workflow_trigger(media_uuid)

        # Step 2: Retrieve person data (regardless of trigger result)
        retrieval_result = await test_person_data_retrieval(media_uuid)

        # Evaluate results
        if trigger_result.get("success") and retrieval_result.get("success"):
            if retrieval_result.get("total_persons", 0) > 0:
                logger.info(f"🎉 COMPLETE SUCCESS for {media_uuid}!")
                success_count += 1
            else:
                logger.info(f"⚠️ PARTIAL SUCCESS for {media_uuid} (no persons found)")
        else:
            logger.error(f"❌ FAILED for {media_uuid}")

    logger.info("\n" + "=" * 60)
    logger.info("🎯 TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"📊 Successful workflows: {success_count}/{total_tests}")

    if success_count > 0:
        logger.info("✅ PPL Thread automatic workflow system is WORKING!")
        logger.info("🎯 Flutter can now use: GET /api/v1/person-objects/{media_uuid}")
        return True
    else:
        logger.error("❌ No successful workflows - check face detection data exists")
        return False


async def main():
    """Run the test suite."""
    logger.info("🚀 PPL Meta Platform - PPL Thread Workflow Backend Tests")
    logger.info("=" * 60)
    logger.info("Testing automatic PPL Thread workflow integration")
    logger.info("This verifies the backend can process person objects automatically")
    logger.info("=" * 60)

    success = await test_complete_workflow()

    logger.info("\n" + "=" * 60)
    if success:
        logger.info("🎉 BACKEND TESTS PASSED!")
        logger.info("🎯 Ready to integrate with Flutter person count widget")
        logger.info(
            "💡 Next: Update Flutter to use GET /api/v1/person-objects/{media_uuid}"
        )
    else:
        logger.error("❌ BACKEND TESTS FAILED")
        logger.error("🔧 Need to fix backend issues before Flutter integration")

    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
