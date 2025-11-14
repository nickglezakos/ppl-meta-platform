"""
Unit Tests for PollingEventSubscriber

Tests polling logic, deduplication, and Vision Service integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.events import (
    PollingConfig,
    SubscriptionStatus,
    EventType
)
from src.services.polling_subscriber import PollingEventSubscriber


@pytest.fixture
def polling_config():
    """Create test polling configuration."""
    return PollingConfig(
        vision_service_url="http://localhost:8003",
        polling_interval_seconds=1.0,
        lookback_minutes=5,
        deduplication_window_minutes=60
    )


@pytest.fixture
def mock_event_callback():
    """Create mock event callback."""
    callback = AsyncMock()
    callback.return_value = True
    return callback


@pytest.fixture
def collection_filter():
    """Create collection filter."""
    return [uuid4()]


@pytest.fixture
async def polling_subscriber(
    polling_config,
    mock_event_callback,
    collection_filter
):
    """Create polling subscriber instance."""
    subscriber = PollingEventSubscriber(
        config=polling_config,
        on_event=mock_event_callback,
        collection_filter=collection_filter
    )
    yield subscriber
    if subscriber.state.status != SubscriptionStatus.DISCONNECTED:
        await subscriber.stop()


@pytest.fixture
def sample_session():
    """Create sample Vision Service session."""
    return {
        "session_uuid": str(uuid4()),
        "video_uuid": str(uuid4()),
        "collection_id": str(uuid4()),
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
        "faces_detected": 5,
        "individuals_created": 2,
        "individuals_cached": 3,
        "processing_time_ms": 1500
    }


class TestPollingSubscriberBasics:
    """Test basic polling subscriber functionality."""
    
    @pytest.mark.asyncio
    async def test_subscriber_initialization(
        self,
        polling_config,
        mock_event_callback,
        collection_filter
    ):
        """Test subscriber initialization."""
        subscriber = PollingEventSubscriber(
            config=polling_config,
            on_event=mock_event_callback,
            collection_filter=collection_filter
        )
        
        assert subscriber.config == polling_config
        assert subscriber.on_event == mock_event_callback
        assert subscriber.collection_filter == collection_filter
        assert subscriber.state.status == SubscriptionStatus.DISCONNECTED
        assert len(subscriber._processed_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_get_state(self, polling_subscriber):
        """Test getting subscriber state."""
        state = polling_subscriber.get_state()
        
        assert state.status == SubscriptionStatus.DISCONNECTED
        assert state.events_received == 0
        assert state.events_processed == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, polling_subscriber):
        """Test getting subscriber statistics."""
        stats = polling_subscriber.get_statistics()
        
        assert "status" in stats
        assert "healthy" in stats
        assert "uptime_seconds" in stats


class TestConnection:
    """Test connection functionality."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self, polling_subscriber):
        """Test successful connection."""
        await polling_subscriber.connect()
        
        assert polling_subscriber.session is not None
        assert (
            polling_subscriber.state.status ==
            SubscriptionStatus.CONNECTED
        )
    
    @pytest.mark.asyncio
    async def test_disconnect(self, polling_subscriber):
        """Test disconnection."""
        await polling_subscriber.connect()
        await polling_subscriber.disconnect()
        
        assert polling_subscriber.session is None
        assert (
            polling_subscriber.state.status ==
            SubscriptionStatus.DISCONNECTED
        )


class TestPolling:
    """Test polling functionality."""
    
    @pytest.mark.asyncio
    async def test_poll_completed_sessions(
        self,
        polling_subscriber,
        sample_session
    ):
        """Test polling for completed sessions."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "sessions": [sample_session],
            "count": 1
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()
            
            polling_subscriber.session = mock_session
            
            sessions = await polling_subscriber._poll_completed_sessions()
            
            assert len(sessions) == 1
            assert sessions[0]["session_uuid"] == sample_session["session_uuid"]
    
    @pytest.mark.asyncio
    async def test_poll_empty_response(self, polling_subscriber):
        """Test polling with no completed sessions."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "sessions": [],
            "count": 0
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()
            
            polling_subscriber.session = mock_session
            
            sessions = await polling_subscriber._poll_completed_sessions()
            
            assert len(sessions) == 0
    
    @pytest.mark.asyncio
    async def test_poll_error_handling(self, polling_subscriber):
        """Test error handling during polling."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.get = AsyncMock(
                side_effect=Exception("Network error")
            )
            
            polling_subscriber.session = mock_session
            
            sessions = await polling_subscriber._poll_completed_sessions()
            
            # Should return empty list on error
            assert len(sessions) == 0
            assert polling_subscriber.state.events_failed == 1


class TestSessionProcessing:
    """Test session processing functionality."""
    
    @pytest.mark.asyncio
    async def test_process_session(
        self,
        polling_subscriber,
        sample_session,
        mock_event_callback
    ):
        """Test processing a single session."""
        await polling_subscriber._process_session(sample_session)
        
        # Callback should be called once
        mock_event_callback.assert_called_once()
        assert polling_subscriber.state.events_processed == 1
        
        # Session should be marked as processed
        assert sample_session["session_uuid"] in polling_subscriber._processed_sessions
    
    @pytest.mark.asyncio
    async def test_process_duplicate_session(
        self,
        polling_subscriber,
        sample_session,
        mock_event_callback
    ):
        """Test deduplication of already processed session."""
        # Process first time
        await polling_subscriber._process_session(sample_session)
        mock_event_callback.assert_called_once()
        
        # Process again
        mock_event_callback.reset_mock()
        await polling_subscriber._process_session(sample_session)
        
        # Should not call callback again
        mock_event_callback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_session_to_event_conversion(
        self,
        polling_subscriber,
        sample_session
    ):
        """Test converting session to event format."""
        event = polling_subscriber._session_to_event(sample_session)
        
        assert event["event_type"] == EventType.FACE_DETECTION_COMPLETED
        assert event["event_source"] == "vision_service"
        assert "timestamp" in event
        assert "payload" in event
        
        payload = event["payload"]
        assert payload["session_uuid"] == sample_session["session_uuid"]
        assert payload["video_uuid"] == sample_session["video_uuid"]
        assert payload["collection_id"] == sample_session["collection_id"]
        assert payload["faces_detected"] == sample_session["faces_detected"]


class TestDeduplication:
    """Test deduplication functionality."""
    
    @pytest.mark.asyncio
    async def test_deduplication_cache(
        self,
        polling_subscriber,
        sample_session,
        mock_event_callback
    ):
        """Test deduplication cache behavior."""
        session_uuid = sample_session["session_uuid"]
        
        # First processing
        await polling_subscriber._process_session(sample_session)
        assert session_uuid in polling_subscriber._processed_sessions
        assert mock_event_callback.call_count == 1
        
        # Second processing (duplicate)
        await polling_subscriber._process_session(sample_session)
        assert mock_event_callback.call_count == 1  # Not called again
    
    @pytest.mark.asyncio
    async def test_cleanup_deduplication_cache(self, polling_subscriber):
        """Test cleanup of old entries from deduplication cache."""
        # Add old entries
        for i in range(10):
            polling_subscriber._processed_sessions.add(f"old-session-{i}")
        
        initial_size = len(polling_subscriber._processed_sessions)
        
        # Cleanup
        polling_subscriber._cleanup_deduplication_cache()
        
        # Cache should be cleared
        assert len(polling_subscriber._processed_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_deduplication_window(
        self,
        polling_config,
        mock_event_callback,
        collection_filter
    ):
        """Test deduplication window configuration."""
        # Set short deduplication window
        polling_config.deduplication_window_minutes = 1
        
        subscriber = PollingEventSubscriber(
            config=polling_config,
            on_event=mock_event_callback,
            collection_filter=collection_filter
        )
        
        assert subscriber.config.deduplication_window_minutes == 1


class TestCollectionFiltering:
    """Test collection filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_filter_by_collection(
        self,
        polling_config,
        mock_event_callback
    ):
        """Test filtering sessions by collection ID."""
        collection_id = uuid4()
        subscriber = PollingEventSubscriber(
            config=polling_config,
            on_event=mock_event_callback,
            collection_filter=[collection_id]
        )
        
        # Matching session
        matching_session = {
            "session_uuid": str(uuid4()),
            "collection_id": str(collection_id),
            "status": "completed"
        }
        
        await subscriber._process_session(matching_session)
        mock_event_callback.assert_called_once()
        
        # Non-matching session
        mock_event_callback.reset_mock()
        non_matching_session = {
            "session_uuid": str(uuid4()),
            "collection_id": str(uuid4()),
            "status": "completed"
        }
        
        await subscriber._process_session(non_matching_session)
        mock_event_callback.assert_not_called()


class TestHealthChecks:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_connected(self, polling_subscriber):
        """Test health check when connected."""
        polling_subscriber.state.status = SubscriptionStatus.CONNECTED
        polling_subscriber.state.last_event_at = datetime.utcnow()
        
        assert polling_subscriber.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_disconnected(self, polling_subscriber):
        """Test health check when disconnected."""
        polling_subscriber.state.status = SubscriptionStatus.DISCONNECTED
        
        assert polling_subscriber.is_healthy() is False


class TestLifecycle:
    """Test subscriber lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, polling_subscriber):
        """Test starting and stopping subscriber."""
        await polling_subscriber.start()
        
        assert polling_subscriber.main_task is not None
        assert (
            polling_subscriber.state.status ==
            SubscriptionStatus.CONNECTED
        )
        
        await polling_subscriber.stop()
        
        assert polling_subscriber.main_task is None
        assert (
            polling_subscriber.state.status ==
            SubscriptionStatus.DISCONNECTED
        )
    
    @pytest.mark.asyncio
    async def test_polling_interval(self, polling_subscriber):
        """Test polling interval timing."""
        # Set short interval for testing
        polling_subscriber.config.polling_interval_seconds = 0.1
        
        with patch.object(
            polling_subscriber,
            '_poll_completed_sessions',
            new_callable=AsyncMock,
            return_value=[]
        ) as mock_poll:
            await polling_subscriber.start()
            
            # Wait for multiple polling cycles
            await asyncio.sleep(0.3)
            
            await polling_subscriber.stop()
            
            # Should have polled at least twice
            assert mock_poll.call_count >= 2


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_callback_error_handling(
        self,
        polling_subscriber,
        sample_session,
        mock_event_callback
    ):
        """Test handling callback errors."""
        # Make callback fail
        mock_event_callback.side_effect = Exception("Callback failed")
        
        await polling_subscriber._process_session(sample_session)
        
        # Should record failure
        assert polling_subscriber.state.events_failed == 1
    
    @pytest.mark.asyncio
    async def test_invalid_session_data(
        self,
        polling_subscriber,
        mock_event_callback
    ):
        """Test handling invalid session data."""
        invalid_session = {
            "session_uuid": "not-a-uuid",
            # Missing required fields
        }
        
        await polling_subscriber._process_session(invalid_session)
        
        # Should not crash, may record as failure
        mock_event_callback.assert_not_called()
