"""
Test Background Processing for MVR-People

This script demonstrates the background processing system for automatic
MVR-People creation and matching.
"""

import asyncio
import logging
from uuid import uuid4
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_background_processor():
    """Test MVR background processor with mock data."""
    
    logger.info("=" * 70)
    logger.info("MVR-People Background Processing Test")
    logger.info("=" * 70)
    
    # Import services
    from database.mvr_repository import MVRRepository
    from services.mvr_service import MVRService
    from services.mvr_matcher import MVRMatcher
    from ml.mvr_processor import MVRProcessor
    from background.mvr_background_processor import MVRBackgroundProcessor
    from background.mvr_integration_hook import MVRIntegrationHook
    import asyncpg
    import os
    
    # Database connection
    logger.info("\n📊 Connecting to database...")
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "ppl_user"),
        password=os.getenv("DB_PASSWORD", "ppl_password"),
        database=os.getenv("DB_NAME", "ppl_meta"),
        min_size=2,
        max_size=10
    )
    
    try:
        # Initialize services
        logger.info("🧬 Initializing MVR services...")
        mvr_repository = MVRRepository(connection_pool=pool)
        ml_processor = MVRProcessor()
        mvr_service = MVRService(
            repository=mvr_repository,
            ml_processor=ml_processor
        )
        mvr_matcher = MVRMatcher(
            repository=mvr_repository,
            ml_processor=ml_processor
        )
        
        # Initialize background processor
        background_processor = MVRBackgroundProcessor(
            mvr_service=mvr_service,
            mvr_matcher=mvr_matcher,
            max_retries=3,
            retry_delay=2.0  # Shorter for testing
        )
        
        integration_hook = MVRIntegrationHook(
            background_processor=background_processor
        )
        
        logger.info("✅ All services initialized")
        
        # Test 1: Trigger background processing
        logger.info("\n" + "=" * 70)
        logger.info("Test 1: Trigger Background Processing")
        logger.info("=" * 70)
        
        test_individual_uuid = uuid4()
        test_session_uuid = uuid4()
        
        logger.info(
            f"Triggering MVR creation for Individual: {test_individual_uuid}"
        )
        
        # This would normally be called from Individual creation
        await integration_hook.on_individual_created(
            individual_uuid=test_individual_uuid,
            session_uuid=test_session_uuid,
            auto_match=True
        )
        
        # Wait a bit for background processing
        logger.info("Waiting for background processing...")
        await asyncio.sleep(3)
        
        # Check status
        status = await background_processor.get_task_status(
            test_individual_uuid
        )
        logger.info(f"Task status: {status.get('status')}")
        
        # Test 2: Get statistics
        logger.info("\n" + "=" * 70)
        logger.info("Test 2: Background Processing Statistics")
        logger.info("=" * 70)
        
        stats = await background_processor.get_statistics()
        logger.info(f"Pending tasks: {stats['pending']}")
        logger.info(f"Completed tasks: {stats['completed']}")
        logger.info(f"Failed tasks: {stats['failed']}")
        logger.info(f"Success rate: {stats['success_rate_percent']}%")
        logger.info(
            f"Avg processing time: {stats['average_processing_time_seconds']}s"
        )
        logger.info(f"Merged count: {stats['merged_count']}")
        logger.info(
            f"Unique individuals: {stats['unique_individuals_count']}"
        )
        
        # Test 3: Enable/Disable hook
        logger.info("\n" + "=" * 70)
        logger.info("Test 3: Enable/Disable Integration Hook")
        logger.info("=" * 70)
        
        logger.info(f"Hook enabled: {integration_hook.is_enabled()}")
        
        integration_hook.disable()
        logger.info(f"Hook enabled after disable: {integration_hook.is_enabled()}")
        
        integration_hook.enable()
        logger.info(f"Hook enabled after enable: {integration_hook.is_enabled()}")
        
        # Test 4: Pending tasks
        logger.info("\n" + "=" * 70)
        logger.info("Test 4: Check Pending Tasks")
        logger.info("=" * 70)
        
        pending = await background_processor.get_all_pending_tasks()
        logger.info(f"Pending count: {pending['pending_count']}")
        logger.info(f"Task IDs: {pending['task_ids']}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ All tests completed successfully!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup
        logger.info("\n🧹 Cleaning up...")
        await pool.close()
        logger.info("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(test_background_processor())
