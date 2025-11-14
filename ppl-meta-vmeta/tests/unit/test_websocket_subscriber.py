"""
Unit Tests for WebSocketEventSubscriber

Tests WebSocket connection, reconnection, heartbeat, and event handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4
import aiohttp

from src.models.events import (
    SubscriptionConfig,
    SubscriptionStatus,
    EventType
)
from src.services.websocket_subscriber import WebSocketEventSubscriber


@pytest.fixture
def subscription_config():
    """Create test subscription configuration."""
    return SubscriptionConfig(
        orchestrator_url="http://localhost:8002",
        event_endpoint="/api/v1/events/subscribe",
        event_types=["face_detection_completed"],
        collections=[uuid4()],
        reconnect_initial_delay=0.1,
        reconnect_max_delay=1.0,
        reconnect_backoff_multiplier=2.0,
        heartbeat_interval_seconds=1.0,
        heartbeat_timeout_seconds=0.5,
        event_queue_max_size=10
    )


@pytest.fixture
def mock_event_callback():
    """Create mock event callback."""
    callback = AsyncMock()
    callback.return_value = True
    return callback


@pytest.fixture
async def websocket_subscriber(subscription_config, mock_event_callback):
    """Create WebSocket subscriber instance."""
    subscriber = WebSocketEventSubscriber(
        config=subscription_config,
        on_event=mock_event_callback
    )
    yield subscriber
    if subscriber.state.status != SubscriptionStatus.DISCONNECTED:
        await subscriber.stop()


@pytest.fixture
def sample_websocket_message():
    """Create sample WebSocket message."""
    return {
        "event_type": EventType.FACE_DETECTION_COMPLETED,
        "event_source": "orchestrator",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "session_uuid": str(uuid4()),
            "video_uuid": str(uuid4()),
            "collection_id": str(uuid4()),
            "faces_detected": 5
        }
    }


class TestWebSocketSubscriberBasics:
    """Test basic WebSocket subscriber functionality."""
    
    @pytest.mark.asyncio
    async def test_subscriber_initialization(
        self,
        subscription_config,
        mock_event_callback
    ):
        """Test subscriber initialization."""
        subscriber = WebSocketEventSubscriber(
            config=subscription_config,
            on_event=mock_event_callback
        )
        
        assert subscriber.config == subscription_config
        assert subscriber.on_event == mock_event_callback
        assert subscriber.state.status == SubscriptionStatus.DISCONNECTED
        assert subscriber.state.events_received == 0
    
    @pytest.mark.asyncio
    async def test_get_state(self, websocket_subscriber):
        """Test getting subscriber state."""
        state = websocket_subscriber.get_state()
        
        assert state.status == SubscriptionStatus.DISCONNECTED
        assert state.events_received == 0
        assert state.events_processed == 0
        assert state.events_failed == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, websocket_subscriber):
        """Test getting subscriber statistics."""
        stats = websocket_subscriber.get_statistics()
        
        assert "status" in stats
        assert "healthy" in stats
        assert "uptime_seconds" in stats


class TestWebSocketConnection:
    """Test WebSocket connection functionality."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self, websocket_subscriber):
        """Test successful WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.receive = AsyncMock()
        mock_ws.receive.return_value.type = aiohttp.WSMsgType.TEXT
        mock_ws.receive.return_value.json.return_value = {
            "type": "subscribed"
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.ws_connect = AsyncMock(return_value=mock_ws)
            
            await websocket_subscriber.connect()
            
            assert websocket_subscriber.ws is not None
            assert websocket_subscriber.session is not None
    
    @pytest.mark.asyncio
    async def test_disconnect(self, websocket_subscriber):
        """Test WebSocket disconnection."""
        # Mock connection
        websocket_subscriber.ws = AsyncMock()
        websocket_subscriber.session = AsyncMock()
        
        await websocket_subscriber.disconnect()
        
        assert websocket_subscriber.ws is None
        assert websocket_subscriber.session is None
        assert (
            websocket_subscriber.state.status ==
            SubscriptionStatus.DISCONNECTED
        )
    
    @pytest.mark.asyncio
    async def test_connection_failure(self, websocket_subscriber):
        """Test handling connection failure."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            mock_session.ws_connect = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            
            with pytest.raises(Exception):
                await websocket_subscriber.connect()


class TestMessageHandling:
    """Test WebSocket message handling."""
    
    @pytest.mark.asyncio
    async def test_handle_text_message(
        self,
        websocket_subscriber,
        sample_websocket_message,
        mock_event_callback
    ):
        """Test handling TEXT message."""
        import json
        
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.json.return_value = sample_websocket_message
        
        await websocket_subscriber._handle_message(mock_msg)
        
        # Callback should be called
        mock_event_callback.assert_called_once()
        assert websocket_subscriber.state.events_received == 1
    
    @pytest.mark.asyncio
    async def test_handle_closed_message(self, websocket_subscriber):
        """Test handling CLOSED message."""
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.CLOSED
        
        await websocket_subscriber._handle_message(mock_msg)
        
        # Should trigger reconnection
        assert (
            websocket_subscriber.state.status ==
            SubscriptionStatus.RECONNECTING
        )
    
    @pytest.mark.asyncio
    async def test_handle_error_message(self, websocket_subscriber):
        """Test handling ERROR message."""
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.ERROR
        
        await websocket_subscriber._handle_message(mock_msg)
        
        assert websocket_subscriber.state.events_failed == 1
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, websocket_subscriber):
        """Test handling PING message."""
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.PING
        
        # Should not raise exception
        await websocket_subscriber._handle_message(mock_msg)
    
    @pytest.mark.asyncio
    async def test_handle_pong_message(self, websocket_subscriber):
        """Test handling PONG message."""
        websocket_subscriber.waiting_for_pong = True
        
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.PONG
        
        await websocket_subscriber._handle_message(mock_msg)
        
        assert websocket_subscriber.waiting_for_pong is False
    
    @pytest.mark.asyncio
    async def test_handle_invalid_json(
        self,
        websocket_subscriber,
        mock_event_callback
    ):
        """Test handling message with invalid JSON."""
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.json.side_effect = ValueError("Invalid JSON")
        
        await websocket_subscriber._handle_message(mock_msg)
        
        # Should not call callback
        mock_event_callback.assert_not_called()
        assert websocket_subscriber.state.events_failed == 1


class TestEventFiltering:
    """Test event filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_filter_by_event_type(
        self,
        subscription_config,
        mock_event_callback
    ):
        """Test filtering by event type."""
        # Only subscribe to face_detection_completed
        subscription_config.event_types = ["face_detection_completed"]
        
        subscriber = WebSocketEventSubscriber(
            config=subscription_config,
            on_event=mock_event_callback
        )
        
        # Matching event
        matching_msg = {
            "event_type": "face_detection_completed",
            "payload": {}
        }
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.json.return_value = matching_msg
        
        await subscriber._handle_message(mock_msg)
        mock_event_callback.assert_called_once()
        
        # Non-matching event
        mock_event_callback.reset_mock()
        non_matching_msg = {
            "event_type": "other_event",
            "payload": {}
        }
        mock_msg.json.return_value = non_matching_msg
        
        await subscriber._handle_message(mock_msg)
        mock_event_callback.assert_not_called()


class TestHeartbeat:
    """Test heartbeat functionality."""
    
    @pytest.mark.asyncio
    async def test_heartbeat_start(self, websocket_subscriber):
        """Test starting heartbeat."""
        websocket_subscriber.ws = AsyncMock()
        
        await websocket_subscriber._start_heartbeat()
        
        assert websocket_subscriber.heartbeat_task is not None
    
    @pytest.mark.asyncio
    async def test_heartbeat_loop(self, websocket_subscriber):
        """Test heartbeat loop."""
        websocket_subscriber.ws = AsyncMock()
        websocket_subscriber.ws.ping = AsyncMock()
        
        # Run heartbeat for a short time
        websocket_subscriber._start_heartbeat()
        await asyncio.sleep(0.2)
        
        # Should have sent at least one ping
        # (heartbeat interval is 1.0s in fixture)
        websocket_subscriber.ws.ping.assert_called()
    
    @pytest.mark.asyncio
    async def test_heartbeat_timeout(self, websocket_subscriber):
        """Test heartbeat timeout detection."""
        websocket_subscriber.waiting_for_pong = True
        websocket_subscriber.state.last_pong_at = None
        
        result = await websocket_subscriber._wait_for_pong()
        
        assert result is False


class TestReconnection:
    """Test reconnection functionality."""
    
    @pytest.mark.asyncio
    async def test_schedule_reconnect(self, websocket_subscriber):
        """Test scheduling reconnection."""
        websocket_subscriber.schedule_reconnect()
        
        assert (
            websocket_subscriber.state.status ==
            SubscriptionStatus.RECONNECTING
        )
        assert websocket_subscriber.state.reconnect_attempts == 1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, websocket_subscriber):
        """Test exponential backoff on reconnection."""
        # First attempt
        websocket_subscriber.state.reconnect_attempts = 0
        delay1 = websocket_subscriber._calculate_backoff_delay()
        
        # Second attempt
        websocket_subscriber.state.reconnect_attempts = 1
        delay2 = websocket_subscriber._calculate_backoff_delay()
        
        # Third attempt
        websocket_subscriber.state.reconnect_attempts = 2
        delay3 = websocket_subscriber._calculate_backoff_delay()
        
        # Delays should increase exponentially
        assert delay2 > delay1
        assert delay3 > delay2


class TestHealthChecks:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_connected(self, websocket_subscriber):
        """Test health check when connected."""
        websocket_subscriber.state.status = SubscriptionStatus.CONNECTED
        websocket_subscriber.state.last_event_at = datetime.utcnow()
        
        assert websocket_subscriber.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_disconnected(self, websocket_subscriber):
        """Test health check when disconnected."""
        websocket_subscriber.state.status = SubscriptionStatus.DISCONNECTED
        
        assert websocket_subscriber.is_healthy() is False
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_reconnecting(self, websocket_subscriber):
        """Test health check when reconnecting."""
        websocket_subscriber.state.status = SubscriptionStatus.RECONNECTING
        
        assert websocket_subscriber.is_healthy() is False


class TestLifecycle:
    """Test subscriber lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, websocket_subscriber):
        """Test starting and stopping subscriber."""
        with patch.object(
            websocket_subscriber,
            'connect',
            new_callable=AsyncMock
        ):
            await websocket_subscriber.start()
            
            assert websocket_subscriber.main_task is not None
            
            await websocket_subscriber.stop()
            
            assert websocket_subscriber.main_task is None
            assert (
                websocket_subscriber.state.status ==
                SubscriptionStatus.DISCONNECTED
            )
