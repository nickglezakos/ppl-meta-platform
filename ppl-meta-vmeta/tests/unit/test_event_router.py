"""
Unit Tests for EventRouter

Tests event routing, queue management, retry logic, and error handling.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from src.models.events import EventRouterConfig, EventType
from src.services.event_router import EventRouter


@pytest.fixture
def mock_event_handler():
    """Mock event handler function."""
    handler = AsyncMock()
    handler.return_value = None
    return handler


@pytest.fixture
def event_router_config():
    """Create event router configuration."""
    return EventRouterConfig(
        max_queue_size=10,
        worker_count=2,
        retry_max_attempts=3,
        retry_initial_delay=0.1,
        retry_max_delay=1.0,
        retry_backoff_multiplier=2.0,
        dead_letter_queue_max_size=10
    )


@pytest_asyncio.fixture
async def event_router(mock_event_handler, event_router_config):
    """Create event router instance."""
    router = EventRouter(
        config=event_router_config,
        event_handler=mock_event_handler,
        collection_filter=None
    )
    
    yield router
    
    # Cleanup
    if router.running:
        await router.stop()


@pytest.fixture
def sample_event():
    """Create sample event data."""
    return {
        "event_type": EventType.FACE_DETECTION_COMPLETED,
        "event_source": "orchestrator",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "session_uuid": str(uuid4()),
            "video_uuid": str(uuid4()),
            "collection_id": str(uuid4()),
            "faces_detected": 5,
            "individuals_created": 2,
            "individuals_cached": 3
        }
    }


class TestEventRouterBasics:
    """Test basic EventRouter functionality."""
    
    @pytest.mark.asyncio
    async def test_router_initialization(
        self, 
        event_router_config, 
        mock_event_handler
    ):
        """Test router initialization."""
        router = EventRouter(
            config=event_router_config,
            event_handler=mock_event_handler,
            collection_filter=None
        )
        
        assert not router.running
        assert router.event_handler == mock_event_handler
        assert len(router.workers) == 0
        
        # Check statistics initialized
        stats = router.get_statistics()
        assert stats["events_received"] == 0
        assert stats["events_processed"] == 0
        assert stats["events_failed"] == 0
    
    @pytest.mark.asyncio
    async def test_router_start_stop(self, event_router):
        """Test router start and stop."""
        # Start router
        await event_router.start()
        
        assert event_router.running
        assert len(event_router.workers) == 2  # worker_count from config
        
        # Stop router
        await event_router.stop()
        
        assert not event_router.running
        assert len(event_router.workers) == 0


class TestEventRouting:
    """Test event routing functionality."""
    
    @pytest.mark.asyncio
    async def test_route_event_success(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test successful event routing."""
        await event_router.start()
        
        # Route event
        result = await event_router.route_event(sample_event)
        assert result is True
        assert event_router.stats["events_received"] == 1
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Verify handler was called
        mock_event_handler.assert_called_once_with(sample_event)
        assert event_router.stats["events_processed"] == 1
    
    @pytest.mark.asyncio
    async def test_route_event_not_running(self, event_router, sample_event):
        """Test routing event when router not running."""
        result = await event_router.route_event(sample_event)
        
        assert result is False
        assert event_router.stats["events_received"] == 1
    
    @pytest.mark.asyncio
    async def test_route_multiple_events(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test routing multiple events."""
        await event_router.start()
        
        # Route multiple events
        for i in range(5):
            event = sample_event.copy()
            event["payload"]["session_uuid"] = str(uuid4())
            result = await event_router.route_event(event)
            assert result is True
        
        assert event_router.stats["events_received"] == 5
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        assert mock_event_handler.call_count == 5
        assert event_router.stats["events_processed"] == 5


class TestEventFiltering:
    """Test event filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_filter_by_event_type(self, event_router):
        """Test filtering by event type."""
        await event_router.start()
        
        # Valid event type
        valid_event = {
            "event_type": EventType.FACE_DETECTION_COMPLETED,
            "payload": {"collection_id": str(uuid4())}
        }
        result = await event_router.route_event(valid_event)
        assert result is True
        
        # Invalid event type
        invalid_event = {
            "event_type": "invalid_type",
            "payload": {}
        }
        result = await event_router.route_event(invalid_event)
        assert result is False
        assert event_router.stats["events_filtered"] == 1
    
    @pytest.mark.asyncio
    async def test_filter_by_collection(
        self,
        router_config,
        mock_event_handler
    ):
        """Test filtering by collection ID."""
        collection_id = uuid4()
        router = EventRouter(
            config=router_config,
            event_handler=mock_event_handler,
            collection_filter=[collection_id]
        )
        await router.start()
        
        # Event with matching collection
        matching_event = {
            "event_type": EventType.FACE_DETECTION_COMPLETED,
            "payload": {"collection_id": str(collection_id)}
        }
        result = await router.route_event(matching_event)
        assert result is True
        
        # Event with non-matching collection
        non_matching_event = {
            "event_type": EventType.FACE_DETECTION_COMPLETED,
            "payload": {"collection_id": str(uuid4())}
        }
        result = await router.route_event(non_matching_event)
        assert result is False
        assert router.stats["events_filtered"] == 1
        
        await router.stop()
    
    @pytest.mark.asyncio
    async def test_filter_missing_event_type(self, event_router):
        """Test filtering event without event_type."""
        await event_router.start()
        
        event = {"payload": {}}
        result = await event_router.route_event(event)
        
        assert result is False
        assert event_router.stats["events_filtered"] == 1


class TestRetryLogic:
    """Test retry logic for failed events."""
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test retry logic when handler fails."""
        # Make handler fail twice, then succeed
        mock_event_handler.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            None
        ]
        
        await event_router.start()
        await event_router.route_event(sample_event)
        
        # Wait for retries
        await asyncio.sleep(0.5)
        
        # Should be called 3 times (initial + 2 retries)
        assert mock_event_handler.call_count == 3
        assert event_router.stats["events_processed"] == 1
        assert event_router.stats["events_failed"] == 0
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test when all retries are exhausted."""
        # Make handler always fail
        mock_event_handler.side_effect = Exception("Always fails")
        
        await event_router.start()
        await event_router.route_event(sample_event)
        
        # Wait for all retries
        await asyncio.sleep(1.0)
        
        # Should be called 3 times (max attempts)
        assert mock_event_handler.call_count == 3
        assert event_router.stats["events_failed"] == 1
        assert event_router.stats["events_in_dead_letter"] == 1


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""
    
    @pytest.mark.asyncio
    async def test_add_to_dead_letter_queue(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test adding failed events to dead letter queue."""
        mock_event_handler.side_effect = Exception("Always fails")
        
        await event_router.start()
        await event_router.route_event(sample_event)
        
        # Wait for retries and DLQ
        await asyncio.sleep(1.0)
        
        stats = event_router.get_statistics()
        assert stats["dead_letter_queue_size"] == 1
    
    @pytest.mark.asyncio
    async def test_get_dead_letter_events(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test retrieving events from dead letter queue."""
        mock_event_handler.side_effect = Exception("Always fails")
        
        await event_router.start()
        await event_router.route_event(sample_event)
        
        # Wait for DLQ
        await asyncio.sleep(1.0)
        
        # Get dead letter events
        dead_events = await event_router.get_dead_letter_events(limit=10)
        
        assert len(dead_events) == 1
        assert dead_events[0]["event_type"] == EventType.FACE_DETECTION_COMPLETED
        assert "failed_at" in dead_events[0]
    
    @pytest.mark.asyncio
    async def test_clear_dead_letter_queue(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test clearing dead letter queue."""
        mock_event_handler.side_effect = Exception("Always fails")
        
        await event_router.start()
        await event_router.route_event(sample_event)
        
        # Wait for DLQ
        await asyncio.sleep(1.0)
        
        # Clear DLQ
        cleared = await event_router.clear_dead_letter_queue()
        
        assert cleared == 1
        assert event_router.stats["events_in_dead_letter"] == 0


class TestBackpressure:
    """Test backpressure handling."""
    
    @pytest.mark.asyncio
    async def test_queue_full_rejection(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test event rejection when queue is full."""
        # Make handler slow to fill queue
        mock_event_handler.side_effect = lambda x: asyncio.sleep(1.0)
        
        await event_router.start()
        
        # Fill queue beyond capacity
        results = []
        for i in range(15):
            event = sample_event.copy()
            event["payload"]["session_uuid"] = str(uuid4())
            result = await event_router.route_event(event)
            results.append(result)
        
        # Some events should be rejected
        assert False in results
        assert event_router.stats["events_received"] == 15


class TestStatistics:
    """Test statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test getting router statistics."""
        await event_router.start()
        await event_router.route_event(sample_event)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        stats = event_router.get_statistics()
        
        assert stats["running"] is True
        assert stats["events_received"] == 1
        assert stats["events_processed"] == 1
        assert stats["events_failed"] == 0
        assert stats["worker_count"] == 2
        assert "uptime_seconds" in stats
        assert "events_per_second" in stats


class TestHealthChecks:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_running(self, event_router):
        """Test health check when router is healthy."""
        await event_router.start()
        
        assert event_router.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_stopped(self, event_router):
        """Test health check when router is stopped."""
        assert event_router.is_healthy() is False
    
    @pytest.mark.asyncio
    async def test_is_healthy_queue_near_capacity(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test health check when queue is near capacity."""
        # Make handler slow to fill queue
        mock_event_handler.side_effect = lambda x: asyncio.sleep(1.0)
        
        await event_router.start()
        
        # Fill queue to 90%
        for i in range(9):
            event = sample_event.copy()
            await event_router.route_event(event)
        
        # Should be unhealthy due to queue capacity
        assert event_router.is_healthy() is False


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""
    
    @pytest.mark.asyncio
    async def test_drain_queue_on_shutdown(
        self,
        event_router,
        sample_event,
        mock_event_handler
    ):
        """Test that remaining events are processed on shutdown."""
        await event_router.start()
        
        # Add multiple events
        for i in range(3):
            event = sample_event.copy()
            event["payload"]["session_uuid"] = str(uuid4())
            await event_router.route_event(event)
        
        # Stop immediately
        await event_router.stop()
        
        # All events should be processed
        assert mock_event_handler.call_count == 3
