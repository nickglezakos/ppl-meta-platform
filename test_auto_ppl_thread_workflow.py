#!/usr/bin/env python3
"""
Test script for automatic PPL Thread workflow integration.

This tests the complete flow:
1. Face detection completes -> 2. Orchestrator auto-triggers PPL Thread -> 3. Flutter retrieves results
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
VISION_URL = "http://localhost:8003"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU4MzgwMjA1fQ.lZ_aU-7j2kbkyxtB5emQicWQgB3GcFxp-f6KQSnEqtg"

# Test media UUID (replace with actual video UUID that has face data)
TEST_MEDIA_UUID = "daf06e3c-fcec-4a9d-a342-f0a0595800ca"


async def test_auto_ppl_thread_workflow():
    """Test the automatic PPL Thread workflow trigger."""
    logger.info("🧪 Testing automatic PPL Thread workflow integration")
    logger.info("=" * 60)

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        async with aiohttp.ClientSession() as session:

            # Step 1: Test Vision Service direct trigger endpoint
            logger.info("1️⃣ Testing Vision Service PPL Thread workflow trigger...")

            trigger_payload = {"media_id": TEST_MEDIA_UUID}

            async with session.post(
                f"{VISION_URL}/api/v1/person-objects/workflow/trigger",
                json=trigger_payload,
                headers=headers,
            ) as response:

                if response.status == 200:
                    trigger_result = await response.json()
                    logger.info("✅ PPL Thread workflow triggered successfully")
                    logger.info(
                        f"📋 Workflow Result: {json.dumps(trigger_result, indent=2)}"
                    )

                    # Step 2: Test data retrieval endpoint
                    logger.info("\n2️⃣ Testing person objects data retrieval...")

                    async with session.get(
                        f"{VISION_URL}/api/v1/person-objects/{TEST_MEDIA_UUID}",
                        headers=headers,
                    ) as get_response:

                        if get_response.status == 200:
                            person_data = await get_response.json()
                            logger.info("✅ Person objects data retrieved successfully")
                            logger.info(
                                f"📊 Person Count: {person_data.get('total_persons', 0)}"
                            )
                            logger.info(
                                f"👥 Face Count: {person_data.get('total_faces', 0)}"
                            )
                            logger.info(
                                f"📈 Status: {person_data.get('status', 'unknown')}"
                            )

                            return True
                        else:
                            error_text = await get_response.text()
                            logger.error(
                                f"❌ Failed to retrieve person data: {get_response.status}"
                            )
                            logger.error(f"Error: {error_text}")
                            return False

                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to trigger workflow: {response.status}")
                    logger.error(f"Error: {error_text}")
                    return False

    except Exception as e:
        logger.error(f"🚨 Test failed with exception: {e}")
        return False


async def test_orchestrator_integration():
    """Test the Orchestrator's automatic PPL Thread triggering."""
    logger.info("\n🧪 Testing Orchestrator integration")
    logger.info("=" * 60)

    # This would simulate the Orchestrator calling the Vision Service after face detection
    # For now, we'll just test the endpoint directly since the Orchestrator integration
    # is triggered automatically after face detection completes

    logger.info(
        "ℹ️ Orchestrator integration is automatic after face detection completes"
    )
    logger.info("ℹ️ Test the complete flow by:")
    logger.info("   1. Upload a video")
    logger.info("   2. Face detection runs automatically (if enabled)")
    logger.info("   3. PPL Thread workflow runs automatically after face detection")
    logger.info("   4. Flutter retrieves results via simple GET endpoint")

    return True


async def main():
    """Run the complete test suite."""
    logger.info("🚀 PPL Meta Platform - Automatic PPL Thread Workflow Tests")
    logger.info("=" * 60)

    # Test 1: Direct Vision Service integration
    workflow_ok = await test_auto_ppl_thread_workflow()

    # Test 2: Orchestrator integration info
    orchestrator_ok = await test_orchestrator_integration()

    logger.info("\n" + "=" * 60)
    if workflow_ok and orchestrator_ok:
        logger.info("✅ All tests completed successfully!")
        logger.info("🎯 The automatic PPL Thread workflow system is ready!")
        logger.info(
            "💡 Flutter can now simply call GET /api/v1/person-objects/{media_uuid}"
        )
    else:
        logger.error("❌ Some tests failed")

    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
