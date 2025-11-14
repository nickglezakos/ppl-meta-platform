"""
Unit Tests for Camera Event Integration
Tests the integration between Camera Service events and batch processing
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.camera_event_integration import CameraEventIntegration
from src.services.camera_event_subscriber import CameraEventSubscriber
from src.services.batch_monitor import BatchMonitor
from src.services.hybrid_batch_trigger import HybridBatchTrigger


@pytest.fixture
def mock_batch_monitor():
    """Create mock batch monitor."""
    monitor = MagicMock(spec=BatchMonitor)
    monitor.handle_recording_stop = AsyncMock()
    monitor.get_statistics = MagicMock(return_value={})
    return monitor


@pytest.fixture
def mock_hybrid_trigger():
    """Create mock hybrid trigger."""
    trigger = MagicMock(spec=HybridBatchTrigger)
    trigger.get_statistics = MagicMock(return_value={})
    return trigger


@pytest_asyncio.fixture
async def camera_integration(mock_batch_monitor, mock_hybrid_trigger):
    """Create camera event integration instance."""
    integration = CameraEventIntegration(
        batch_monitor=mock_batch_monitor,
        hybrid_trigger=mock_hybrid_trigger,
        orchestrator_url="http://localhost:8002",
        camera_service_url="http://localhost:8005",
        enable_websocket=False,  # Disable for unit tests
        enable_polling=False      # Disable for unit tests
    )
    yield integration
    await integration.stop()


class TestCameraEventIntegration:
    """Test camera event integration."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, camera_integration):
        """Test integration initialization."""
        assert camera_integration.batch_monitor is not None
        assert camera_integration.hybrid_trigger is not None
        assert camera_integration.subscriber is not None
        assert not camera_integration.is_running
    
    @pytest.mark.asyncio
    async def test_start_stop(self, camera_integration):
        """Test starting and stopping integration."""
        # Mock subscriber
        camera_integration.subscriber.start = AsyncMock()
        camera_integration.subscriber.stop = AsyncMock()
        
        # Start
        await camera_integration.start()
        assert camera_integration.is_running
        camera_integration.subscriber.start.assert_called_once()
        
        # Stop
        await camera_integration.stop()
        assert not camera_integration.is_running
        camera_integration.subscriber.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_recording_stopped(
        self,
        camera_integration,
        mock_batch_monitor
    ):
        """Test handling recording stopped event."""
        collection_id = "test-collection"
        session_id = str(uuid4())
        reason = "user_stopped"
        
        # Call handler
        await camera_integration._handle_recording_stopped(
            collection_id=collection_id,
            session_id=session_id,
            reason=reason
        )
        
        # Verify batch monitor was called
        mock_batch_monitor.handle_recording_stop.assert_called_once_with(
            collection_id=collection_id,
            recording_session_id=session_id,
            reason=reason
        )
    
    @pytest.mark.asyncio
    async def test_handle_recording_completed(self, camera_integration):
        """Test handling recording completed event."""
        collection_id = "test-collection"
        event_data = {
            "recording_session_id": str(uuid4()),
            "recording_duration_seconds": 120.5,
            "file_size_bytes": 1024000
        }
        
        # Should not raise exception
        await camera_integration._handle_recording_completed(
            collection_id=collection_id,
            event_data=event_data
        )
    
    @pytest.mark.asyncio
    async def test_error_handling_in_recording_stopped(
        self,
        camera_integration,
        mock_batch_monitor
    ):
        """Test error handling in recording stopped handler."""
        # Make batch monitor raise exception
        mock_batch_monitor.handle_recording_stop.side_effect = Exception(
            "Test error"
        )
        
        # Should not raise exception (error handled internally)
        await camera_integration._handle_recording_stopped(
            collection_id="test-collection",
            session_id=str(uuid4()),
            reason="user_stopped"
        )
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, camera_integration):
        """Test getting integration statistics."""
        # Mock subscriber statistics
        camera_integration.subscriber.get_statistics = MagicMock(
            return_value={"events_received": 10}
        )
        
        stats = camera_integration.get_statistics()
        
        assert "is_running" in stats
        assert "subscriber_stats" in stats
        assert "batch_monitor_stats" in stats
        assert "hybrid_trigger_enabled" in stats
        assert "hybrid_trigger_stats" in stats


class TestCameraEventSubscriber:
    """Test camera event subscriber."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test subscriber initialization."""
        subscriber = CameraEventSubscriber(
            orchestrator_url="http://localhost:8002",
            camera_service_url="http://localhost:8005",
            enable_websocket=False,
            enable_polling=False
        )
        
        assert not subscriber.is_running
        assert subscriber.on_recording_stopped is None
        assert subscriber.on_recording_completed is None
    
    @pytest.mark.asyncio
    async def test_set_handlers(self):
        """Test setting event handlers."""
        subscriber = CameraEventSubscriber(
            enable_websocket=False,
            enable_polling=False
        )
        
        recording_stopped_handler = AsyncMock()
        recording_completed_handler = AsyncMock()
        
        subscriber.set_recording_stopped_handler(recording_stopped_handler)
        subscriber.set_recording_completed_handler(recording_completed_handler)
        
        assert subscriber.on_recording_stopped == recording_stopped_handler
        assert subscriber.on_recording_completed == recording_completed_handler
    
    @pytest.mark.asyncio
    async def test_process_recording_stopped_event(self):
        """Test processing recording stopped event."""
        subscriber = CameraEventSubscriber(
            enable_websocket=False,
            enable_polling=False
        )
        
        handler = AsyncMock()
        subscriber.set_recording_stopped_handler(handler)
        
        event = {
            "event_type": "recording_stopped",
            "collection_id": "test-collection",
            "recording_session_id": str(uuid4()),
            "reason": "user_stopped"
        }
        
        await subscriber._process_event(event)
        
        # Verify handler was called
        handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_event_deduplication(self):
        """Test that duplicate events are filtered out."""
        subscriber = CameraEventSubscriber(
            enable_websocket=False,
            enable_polling=False
        )
        
        handler = AsyncMock()
        subscriber.set_recording_stopped_handler(handler)
        
        session_id = str(uuid4())
        event = {
            "event_type": "recording_stopped",
            "collection_id": "test-collection",
            "recording_session_id": session_id,
            "reason": "user_stopped"
        }
        
        # Process same event twice
        await subscriber._process_event(event)
        await subscriber._process_event(event)
        
        # Handler should only be called once
        assert handler.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting subscriber statistics."""
        subscriber = CameraEventSubscriber(
            enable_websocket=False,
            enable_polling=False
        )
        
        stats = subscriber.get_statistics()
        
        assert "is_running" in stats
        assert "events_received" in stats
        assert "events_processed" in stats
        assert "events_failed" in stats
        assert "handlers_registered" in stats


class TestEndToEndFlow:
    """Test end-to-end event flow."""
    
    @pytest.mark.asyncio
    async def test_recording_stop_to_batch_trigger(
        self,
        mock_batch_monitor,
        mock_hybrid_trigger
    ):
        """Test complete flow from recording stop to batch trigger."""
        # Setup integration
        integration = CameraEventIntegration(
            batch_monitor=mock_batch_monitor,
            hybrid_trigger=mock_hybrid_trigger,
            enable_websocket=False,
            enable_polling=False
        )
        
        # Simulate recording stop event
        collection_id = "test-collection"
        session_id = str(uuid4())
        
        # Manually trigger the event handler
        await integration._handle_recording_stopped(
            collection_id=collection_id,
            session_id=session_id,
            reason="user_stopped"
        )
        
        # Verify batch monitor was called
        mock_batch_monitor.handle_recording_stop.assert_called_once_with(
            collection_id=collection_id,
            recording_session_id=session_id,
            reason="user_stopped"
        )
        
        await integration.stop()
