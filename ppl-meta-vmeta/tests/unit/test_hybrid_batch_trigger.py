"""
Unit tests for Hybrid Batch Trigger

Tests the hybrid approach for partial batch handling:
- Primary: Recording stop events → Immediate trigger
- Fallback: Timeout monitoring → Automatic trigger
- Integration with BatchMonitor
- Timeout task management
- Edge cases and error handling
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from src.services.hybrid_batch_trigger import HybridBatchTrigger


@pytest.fixture
def trigger_config():
    """Configuration for hybrid batch trigger."""
    return {
        "default_timeout_minutes": 10,
        "default_min_partial_batch_size": 2,
        "max_wait_hours": 24
    }


@pytest_asyncio.fixture
async def hybrid_trigger(trigger_config):
    """Create and cleanup hybrid batch trigger."""
    trigger = HybridBatchTrigger(**trigger_config)
    yield trigger
    await trigger.cleanup()


@pytest.fixture
def mock_batch_data():
    """Mock batch data from database."""
    return {
        "batch_uuid": uuid4(),
        "collection_id": "test-collection",
        "batch_number": 1,
        "status": "accumulating",
        "video_count": 3,
        "batch_size_threshold": 5,
        "first_video_start_time": datetime.now(timezone.utc),
        "last_video_end_time": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def mock_config_data():
    """Mock configuration data."""
    return {
        "partial_batch_timeout_minutes": 10,
        "partial_batch_min_videos": 2
    }


# =============================================================================
# Initialization Tests
# =============================================================================

class TestHybridTriggerInitialization:
    """Test hybrid trigger initialization."""
    
    def test_initialization(self, trigger_config):
        """Test basic initialization."""
        trigger = HybridBatchTrigger(**trigger_config)
        
        assert trigger.default_timeout_minutes == 10
        assert trigger.default_min_partial_batch_size == 2
        assert trigger.max_wait_hours == 24
        assert len(trigger.timeout_tasks) == 0
        assert trigger.on_batch_trigger_callback is None
    
    def test_set_callback(self, hybrid_trigger):
        """Test setting batch trigger callback."""
        callback = AsyncMock()
        hybrid_trigger.set_batch_trigger_callback(callback)
        
        assert hybrid_trigger.on_batch_trigger_callback == callback
    
    def test_get_statistics_initial(self, hybrid_trigger):
        """Test statistics at initialization."""
        stats = hybrid_trigger.get_statistics()
        
        assert stats["active_timeout_tasks"] == 0
        assert stats["total_tracked_collections"] == 0
        assert stats["default_timeout_minutes"] == 10
        assert stats["callback_configured"] is False


# =============================================================================
# Video Added Tests (Normal Threshold Trigger)
# =============================================================================

class TestVideoAddedThresholdTrigger:
    """Test batch triggering when threshold is reached."""
    
    @pytest.mark.asyncio
    async def test_threshold_trigger(self, hybrid_trigger):
        """Test triggering when batch reaches threshold."""
        batch_uuid = uuid4()
        collection_id = "test-collection"
        
        # Set callback to track trigger
        trigger_called = {"called": False, "args": {}}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
            trigger_called["args"] = kwargs
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_active_batch',
            return_value=None
        ), patch.object(
            hybrid_trigger,
            '_update_batch_trigger_info',
            return_value=None
        ):
            # Video added reaches threshold (5/5)
            await hybrid_trigger.on_video_added(
                collection_id=collection_id,
                batch_uuid=batch_uuid,
                video_count=5,
                batch_size_threshold=5
            )
        
        # Verify batch was triggered
        assert trigger_called["called"]
        assert trigger_called["args"]["batch_uuid"] == batch_uuid
        assert trigger_called["args"]["reason"] == "threshold"
        assert trigger_called["args"]["is_partial"] is False
        
        # Verify no timeout task was created
        assert len(hybrid_trigger.timeout_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_no_trigger_below_threshold(self, hybrid_trigger):
        """Test no trigger when below threshold."""
        batch_uuid = uuid4()
        collection_id = "test-collection"
        
        # Set callback to track trigger
        trigger_called = {"called": False}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_start_timeout_task',
            return_value=None
        ) as mock_start_timeout:
            # Video added below threshold (3/5)
            await hybrid_trigger.on_video_added(
                collection_id=collection_id,
                batch_uuid=batch_uuid,
                video_count=3,
                batch_size_threshold=5
            )
        
        # Verify batch was NOT triggered
        assert not trigger_called["called"]
        
        # Verify timeout task was started
        mock_start_timeout.assert_called_once()


# =============================================================================
# Recording Stop Tests (Primary Trigger)
# =============================================================================

class TestRecordingStopTrigger:
    """Test recording stop event triggering."""
    
    @pytest.mark.asyncio
    async def test_recording_stop_triggers_partial_batch(
        self,
        hybrid_trigger,
        mock_batch_data,
        mock_config_data
    ):
        """Test immediate trigger on recording stop."""
        collection_id = "test-collection"
        
        # Set callback to track trigger
        trigger_called = {"called": False, "args": {}}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
            trigger_called["args"] = kwargs
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_cancel_timeout_task',
            return_value=None
        ) as mock_cancel, \
        patch.object(
            hybrid_trigger,
            '_get_active_batch',
            return_value=mock_batch_data
        ), \
        patch.object(
            hybrid_trigger,
            '_get_min_partial_batch_size',
            return_value=mock_config_data['partial_batch_min_videos']
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_trigger_info',
            return_value=None
        ):
            # Recording stops
            await hybrid_trigger.on_recording_stopped(
                collection_id=collection_id,
                recording_session_id="session-123",
                reason="user_stopped"
            )
        
        # Verify timeout was cancelled
        mock_cancel.assert_called_once_with(collection_id)
        
        # Verify batch was triggered
        assert trigger_called["called"]
        assert trigger_called["args"]["reason"] == "recording_stopped"
        assert trigger_called["args"]["is_partial"] is True
    
    @pytest.mark.asyncio
    async def test_recording_stop_no_active_batch(self, hybrid_trigger):
        """Test recording stop with no active batch."""
        collection_id = "test-collection"
        
        # Set callback
        trigger_called = {"called": False}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock no active batch
        with patch.object(
            hybrid_trigger,
            '_cancel_timeout_task',
            return_value=None
        ), \
        patch.object(
            hybrid_trigger,
            '_get_active_batch',
            return_value=None
        ):
            await hybrid_trigger.on_recording_stopped(
                collection_id=collection_id
            )
        
        # Verify batch was NOT triggered
        assert not trigger_called["called"]
    
    @pytest.mark.asyncio
    async def test_recording_stop_below_minimum(
        self,
        hybrid_trigger,
        mock_batch_data
    ):
        """Test recording stop with batch below minimum size."""
        collection_id = "test-collection"
        
        # Set batch to only 1 video (below minimum of 2)
        mock_batch_data['video_count'] = 1
        
        # Set callback
        trigger_called = {"called": False}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_cancel_timeout_task',
            return_value=None
        ), \
        patch.object(
            hybrid_trigger,
            '_get_active_batch',
            return_value=mock_batch_data
        ), \
        patch.object(
            hybrid_trigger,
            '_get_min_partial_batch_size',
            return_value=2
        ):
            await hybrid_trigger.on_recording_stopped(
                collection_id=collection_id
            )
        
        # Verify batch was NOT triggered (below minimum)
        assert not trigger_called["called"]


# =============================================================================
# Timeout Tests (Fallback Trigger)
# =============================================================================

class TestTimeoutFallback:
    """Test timeout monitoring fallback."""
    
    @pytest.mark.asyncio
    async def test_timeout_triggers_partial_batch(
        self,
        hybrid_trigger,
        mock_batch_data,
        mock_config_data
    ):
        """Test timeout fallback triggers partial batch."""
        collection_id = "test-collection"
        batch_uuid = mock_batch_data['batch_uuid']
        
        # Set callback
        trigger_called = {"called": False, "args": {}}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
            trigger_called["args"] = kwargs
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_active_batch',
            return_value=mock_batch_data
        ), \
        patch.object(
            hybrid_trigger,
            '_get_min_partial_batch_size',
            return_value=mock_config_data['partial_batch_min_videos']
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_trigger_info',
            return_value=None
        ):
            # Manually invoke timeout handler with very short timeout
            await hybrid_trigger._timeout_handler(
                collection_id=collection_id,
                batch_uuid=batch_uuid,
                timeout_minutes=0.001  # Very short for testing
            )
        
        # Verify batch was triggered via timeout
        assert trigger_called["called"]
        assert trigger_called["args"]["reason"] == "timeout"
        assert trigger_called["args"]["is_partial"] is True
    
    @pytest.mark.asyncio
    async def test_timeout_cancelled(self, hybrid_trigger):
        """Test timeout task cancellation."""
        collection_id = "test-collection"
        batch_uuid = uuid4()
        
        # Mock database calls for starting timeout
        with patch.object(
            hybrid_trigger,
            '_get_timeout_minutes',
            return_value=1
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_timeout',
            return_value=None
        ):
            # Start timeout task
            await hybrid_trigger._start_timeout_task(
                collection_id=collection_id,
                batch_uuid=batch_uuid,
                current_video_count=3
            )
        
        # Verify task was created
        assert collection_id in hybrid_trigger.timeout_tasks
        task = hybrid_trigger.timeout_tasks[collection_id]
        assert not task.done()
        
        # Cancel task
        await hybrid_trigger._cancel_timeout_task(collection_id)
        
        # Verify task was cancelled
        assert collection_id not in hybrid_trigger.timeout_tasks
    
    @pytest.mark.asyncio
    async def test_timeout_no_trigger_below_minimum(
        self,
        hybrid_trigger,
        mock_batch_data
    ):
        """Test timeout doesn't trigger if below minimum."""
        collection_id = "test-collection"
        batch_uuid = mock_batch_data['batch_uuid']
        
        # Set batch to only 1 video
        mock_batch_data['video_count'] = 1
        
        # Set callback
        trigger_called = {"called": False}
        
        async def mock_callback(**kwargs):
            trigger_called["called"] = True
        
        hybrid_trigger.set_batch_trigger_callback(mock_callback)
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_active_batch',
            return_value=mock_batch_data
        ), \
        patch.object(
            hybrid_trigger,
            '_get_min_partial_batch_size',
            return_value=2
        ):
            # Invoke timeout handler
            await hybrid_trigger._timeout_handler(
                collection_id=collection_id,
                batch_uuid=batch_uuid,
                timeout_minutes=0.001
            )
        
        # Verify batch was NOT triggered (below minimum)
        assert not trigger_called["called"]


# =============================================================================
# Concurrent Collections Tests
# =============================================================================

class TestConcurrentCollections:
    """Test handling multiple collections concurrently."""
    
    @pytest.mark.asyncio
    async def test_multiple_collections_independent_timeouts(
        self,
        hybrid_trigger
    ):
        """Test multiple collections have independent timeout tasks."""
        collection_ids = ["collection-1", "collection-2", "collection-3"]
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_timeout_minutes',
            return_value=1
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_timeout',
            return_value=None
        ):
            # Start timeout tasks for all collections
            for collection_id in collection_ids:
                await hybrid_trigger._start_timeout_task(
                    collection_id=collection_id,
                    batch_uuid=uuid4(),
                    current_video_count=3
                )
        
        # Verify all tasks created
        assert len(hybrid_trigger.timeout_tasks) == 3
        for collection_id in collection_ids:
            assert collection_id in hybrid_trigger.timeout_tasks
            assert not hybrid_trigger.timeout_tasks[collection_id].done()
    
    @pytest.mark.asyncio
    async def test_cancel_one_collection_doesnt_affect_others(
        self,
        hybrid_trigger
    ):
        """Test cancelling one collection doesn't affect others."""
        collection_ids = ["collection-1", "collection-2", "collection-3"]
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_timeout_minutes',
            return_value=1
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_timeout',
            return_value=None
        ):
            # Start timeout tasks
            for collection_id in collection_ids:
                await hybrid_trigger._start_timeout_task(
                    collection_id=collection_id,
                    batch_uuid=uuid4(),
                    current_video_count=3
                )
        
        # Cancel one collection
        await hybrid_trigger._cancel_timeout_task("collection-2")
        
        # Verify only one was cancelled
        assert len(hybrid_trigger.timeout_tasks) == 2
        assert "collection-1" in hybrid_trigger.timeout_tasks
        assert "collection-2" not in hybrid_trigger.timeout_tasks
        assert "collection-3" in hybrid_trigger.timeout_tasks


# =============================================================================
# Cleanup Tests
# =============================================================================

class TestCleanup:
    """Test cleanup and shutdown."""
    
    @pytest.mark.asyncio
    async def test_cleanup_cancels_all_tasks(self, hybrid_trigger):
        """Test cleanup cancels all timeout tasks."""
        collection_ids = ["collection-1", "collection-2", "collection-3"]
        
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_timeout_minutes',
            return_value=10
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_timeout',
            return_value=None
        ):
            # Start multiple timeout tasks
            for collection_id in collection_ids:
                await hybrid_trigger._start_timeout_task(
                    collection_id=collection_id,
                    batch_uuid=uuid4(),
                    current_video_count=3
                )
        
        # Verify tasks created
        assert len(hybrid_trigger.timeout_tasks) == 3
        
        # Cleanup
        await hybrid_trigger.cleanup()
        
        # Verify all tasks cancelled
        assert len(hybrid_trigger.timeout_tasks) == 0


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test statistics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_statistics_with_active_tasks(self, hybrid_trigger):
        """Test statistics reporting active tasks."""
        # Mock database calls
        with patch.object(
            hybrid_trigger,
            '_get_timeout_minutes',
            return_value=10
        ), \
        patch.object(
            hybrid_trigger,
            '_update_batch_timeout',
            return_value=None
        ):
            # Start some timeout tasks
            await hybrid_trigger._start_timeout_task(
                collection_id="collection-1",
                batch_uuid=uuid4(),
                current_video_count=3
            )
            await hybrid_trigger._start_timeout_task(
                collection_id="collection-2",
                batch_uuid=uuid4(),
                current_video_count=4
            )
        
        stats = hybrid_trigger.get_statistics()
        
        assert stats["active_timeout_tasks"] == 2
        assert stats["total_tracked_collections"] == 2
    
    def test_statistics_with_callback(self, hybrid_trigger):
        """Test statistics shows callback configured."""
        callback = AsyncMock()
        hybrid_trigger.set_batch_trigger_callback(callback)
        
        stats = hybrid_trigger.get_statistics()
        
        assert stats["callback_configured"] is True
