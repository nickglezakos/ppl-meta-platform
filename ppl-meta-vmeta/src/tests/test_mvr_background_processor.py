"""
Unit Tests for MVR Background Processor

Tests background processing including retry logic, task tracking,
statistics, and integration hook functionality.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mvr_repository import MVRRepository
from services.mvr_service import MVRService
from services.mvr_matcher import MVRMatcher
from ml.mvr_processor import MVRProcessor
from background.mvr_background_processor import MVRBackgroundProcessor
from background.mvr_integration_hook import MVRIntegrationHook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMVRBackgroundProcessor:
    """Test suite for MVR Background Processor."""
    
    @pytest.fixture
    async def db_pool(self):
        """Create database connection pool."""
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "ppl_user"),
            password=os.getenv("DB_PASSWORD", "ppl_password"),
            database=os.getenv("DB_NAME", "ppl_meta"),
            min_size=2,
            max_size=10
        )
        yield pool
        await pool.close()
    
    @pytest.fixture
    async def repository(self, db_pool):
        """Create repository instance."""
        return MVRRepository(connection_pool=db_pool)
    
    @pytest.fixture
    def ml_processor(self):
        """Create ML processor instance."""
        return MVRProcessor()
    
    @pytest.fixture
    async def service(self, repository, ml_processor):
        """Create service instance."""
        return MVRService(
            repository=repository,
            ml_processor=ml_processor
        )
    
    @pytest.fixture
    async def matcher(self, repository, ml_processor):
        """Create matcher instance."""
        return MVRMatcher(
            repository=repository,
            ml_processor=ml_processor
        )
    
    @pytest.fixture
    async def background_processor(self, service, matcher):
        """Create background processor instance."""
        return MVRBackgroundProcessor(
            mvr_service=service,
            mvr_matcher=matcher,
            max_retries=3,
            retry_delay=1.0  # Shorter for testing
        )
    
    @pytest.fixture
    async def integration_hook(self, background_processor):
        """Create integration hook instance."""
        return MVRIntegrationHook(
            background_processor=background_processor
        )
    
    async def test_process_new_individual_mock(
        self,
        background_processor,
        service
    ):
        """Test processing new Individual with mocked service."""
        logger.info("Test: Process New Individual (Mock)")
        
        individual_uuid = uuid4()
        session_uuid = uuid4()
        
        # Mock the service methods
        with patch.object(
            service,
            'create_mvr_people_from_individual',
            new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = {
                "mvr_people_uuid": str(uuid4()),
                "featured_individual_uuid": str(individual_uuid),
                "quality_score": 0.85
            }
            
            # Trigger processing
            result = await background_processor.process_new_individual(
                individual_uuid=individual_uuid,
                session_uuid=session_uuid,
                auto_match=False  # Disable matching for this test
            )
            
            assert result["status"] == "processing"
            assert result["task_id"] == str(individual_uuid)
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Check status
            status = await background_processor.get_task_status(
                individual_uuid
            )
            assert status["status"] in ["completed", "processing"]
            
            logger.info(f"✅ Processing status: {status['status']}")
    
    async def test_get_statistics(self, background_processor):
        """Test getting background processing statistics."""
        logger.info("Test: Get Statistics")
        
        stats = await background_processor.get_statistics()
        
        assert "pending" in stats
        assert "completed" in stats
        assert "failed" in stats
        assert "success_rate_percent" in stats
        assert "average_processing_time_seconds" in stats
        assert "merged_count" in stats
        assert "unique_individuals_count" in stats
        
        logger.info(f"✅ Statistics: {stats}")
    
    async def test_get_all_pending_tasks(self, background_processor):
        """Test getting all pending tasks."""
        logger.info("Test: Get All Pending Tasks")
        
        pending = await background_processor.get_all_pending_tasks()
        
        assert "pending_count" in pending
        assert "task_ids" in pending
        assert pending["pending_count"] == len(pending["task_ids"])
        
        logger.info(f"✅ Pending tasks: {pending['pending_count']}")
    
    async def test_cleanup_old_tasks(self, background_processor):
        """Test cleaning up old tasks."""
        logger.info("Test: Cleanup Old Tasks")
        
        # Cleanup tasks older than 1 hour
        cleaned = await background_processor.cleanup_old_tasks(
            max_age_hours=1
        )
        
        assert cleaned >= 0
        logger.info(f"✅ Cleaned up {cleaned} old tasks")
    
    async def test_integration_hook_enable_disable(self, integration_hook):
        """Test enabling and disabling integration hook."""
        logger.info("Test: Integration Hook Enable/Disable")
        
        # Initially enabled
        assert integration_hook.is_enabled() is True
        
        # Disable
        integration_hook.disable()
        assert integration_hook.is_enabled() is False
        
        # Enable
        integration_hook.enable()
        assert integration_hook.is_enabled() is True
        
        logger.info("✅ Enable/disable working correctly")
    
    async def test_integration_hook_on_individual_created_mock(
        self,
        integration_hook,
        background_processor,
        service
    ):
        """Test on_individual_created hook with mocked service."""
        logger.info("Test: On Individual Created Hook (Mock)")
        
        individual_uuid = uuid4()
        session_uuid = uuid4()
        
        # Mock the service
        with patch.object(
            service,
            'create_mvr_people_from_individual',
            new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = {
                "mvr_people_uuid": str(uuid4()),
                "featured_individual_uuid": str(individual_uuid),
                "quality_score": 0.85
            }
            
            # Trigger hook
            await integration_hook.on_individual_created(
                individual_uuid=individual_uuid,
                session_uuid=session_uuid,
                auto_match=False
            )
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Check task was created
            pending = await background_processor.get_all_pending_tasks()
            stats = await background_processor.get_statistics()
            
            # Task should be either pending or completed
            total_tasks = pending["pending_count"] + stats["completed"]
            assert total_tasks > 0
            
            logger.info("✅ Hook triggered processing successfully")
    
    async def test_integration_hook_disabled(
        self,
        integration_hook,
        background_processor
    ):
        """Test hook behavior when disabled."""
        logger.info("Test: Integration Hook Disabled")
        
        # Disable hook
        integration_hook.disable()
        
        individual_uuid = uuid4()
        
        # Get initial stats
        initial_stats = await background_processor.get_statistics()
        initial_total = (
            initial_stats["pending"] + 
            initial_stats["completed"] + 
            initial_stats["failed"]
        )
        
        # Try to trigger (should be ignored)
        await integration_hook.on_individual_created(
            individual_uuid=individual_uuid,
            auto_match=False
        )
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Check stats haven't changed
        final_stats = await background_processor.get_statistics()
        final_total = (
            final_stats["pending"] + 
            final_stats["completed"] + 
            final_stats["failed"]
        )
        
        assert final_total == initial_total
        
        # Re-enable
        integration_hook.enable()
        
        logger.info("✅ Hook correctly ignored when disabled")


async def run_all_tests():
    """Run all background processor tests."""
    logger.info("=" * 70)
    logger.info("MVR Background Processor Test Suite")
    logger.info("=" * 70)
    
    test_instance = TestMVRBackgroundProcessor()
    
    # Create fixtures
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "ppl_user"),
        password=os.getenv("DB_PASSWORD", "ppl_password"),
        database=os.getenv("DB_NAME", "ppl_meta"),
        min_size=2,
        max_size=10
    )
    
    repository = MVRRepository(connection_pool=pool)
    ml_processor = MVRProcessor()
    service = MVRService(repository=repository, ml_processor=ml_processor)
    matcher = MVRMatcher(repository=repository, ml_processor=ml_processor)
    
    background_processor = MVRBackgroundProcessor(
        mvr_service=service,
        mvr_matcher=matcher,
        max_retries=3,
        retry_delay=1.0
    )
    
    integration_hook = MVRIntegrationHook(
        background_processor=background_processor
    )
    
    try:
        # Run tests
        await test_instance.test_process_new_individual_mock(
            background_processor,
            service
        )
        await test_instance.test_get_statistics(background_processor)
        await test_instance.test_get_all_pending_tasks(background_processor)
        await test_instance.test_cleanup_old_tasks(background_processor)
        await test_instance.test_integration_hook_enable_disable(
            integration_hook
        )
        await test_instance.test_integration_hook_on_individual_created_mock(
            integration_hook,
            background_processor,
            service
        )
        await test_instance.test_integration_hook_disabled(
            integration_hook,
            background_processor
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ All Background Processor tests passed!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise
    
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
