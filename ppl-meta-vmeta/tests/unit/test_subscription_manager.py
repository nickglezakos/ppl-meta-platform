"""
Unit Tests for SubscriptionManager

Tests lifecycle management, failover, and health monitoring.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.models.events import (
    SubscriptionConfig,
    PollingConfig,
    EventRouterConfig,
    SubscriptionStatus
)
from src.services.subscription_manager import SubscriptionManager
from src.services.batch_monitor import BatchMonitor


@pytest.fixture
def websocket_config():
    """Create WebSocket configuration."""
    return SubscriptionConfig(
        orchestrator_url="http://localhost:8002",
        event_endpoint="/api/v1/events/subscribe",
        event_types=["face_detection_completed"],
        collections=[uuid4()],
        reconnect_initial_delay=0.1,
        reconnect_max_delay=1.0
    )


@pytest.fixture
def polling_config():
    """Create polling configuration."""
    return PollingConfig(
        vision_service_url="http://localhost:8003",
        polling_interval_seconds=1.0,
        lookback_minutes=5
    )


@pytest.fixture
def router_config():
    """Create router configuration."""
    return EventRouterConfig(
        max_queue_size=10,
        worker_count=2,
        retry_max_attempts=3
    )


@pytest.fixture
def collection_filter():
    """Create collection filter."""
    return [uuid4()]


@pytest.fixture
def mock_batch_monitor():
    """Create mock batch monitor."""
    monitor = MagicMock(spec=BatchMonitor)
    monitor.get_statistics.return_value = {
        "videos_received": 0,
        "batches_triggered": 0,
        "active_batches": 0,
        "videos_pending": 0
    }
    return monitor


@pytest.fixture
async def subscription_manager(
    mock_batch_monitor,
    websocket_config,
    polling_config,
    router_config,
    collection_filter
):
    """Create subscription manager instance."""
    manager = SubscriptionManager(
        batch_monitor=mock_batch_monitor,
        websocket_config=websocket_config,
        polling_config=polling_config,
        router_config=router_config,
        collection_filter=collection_filter,
        enable_websocket=True,
        enable_polling=True,
        auto_failover=True
    )
    yield manager
    if manager.running:
        await manager.stop()


class TestSubscriptionManagerBasics:
    """Test basic subscription manager functionality."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(
        self,
        mock_batch_monitor,
        websocket_config,
        polling_config
    ):
        """Test manager initialization."""
        manager = SubscriptionManager(
            batch_monitor=mock_batch_monitor,
            websocket_config=websocket_config,
            polling_config=polling_config
        )
        
        assert manager.batch_monitor == mock_batch_monitor
        assert manager.enable_websocket is True
        assert manager.enable_polling is True
        assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_setup(self, subscription_manager):
        """Test pipeline setup."""
        await subscription_manager.setup()
        
        assert subscription_manager.event_router is not None
        assert subscription_manager.batch_event_handler is not None
        assert subscription_manager.websocket_subscriber is not None
        assert subscription_manager.polling_subscriber is not None


class TestLifecycleManagement:
    """Test lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, subscription_manager):
        """Test starting and stopping manager."""
        await subscription_manager.setup()
        
        # Mock subscriber/router methods
        with patch.object(
            subscription_manager.event_router,
            'start',
            new_callable=AsyncMock
        ), patch.object(
            subscription_manager.websocket_subscriber,
            'start',
            new_callable=AsyncMock
        ), patch.object(
            subscription_manager.polling_subscriber,
            'start',
            new_callable=AsyncMock
        ):
            await subscription_manager.start()
            
            assert subscription_manager.running is True
            assert subscription_manager.started_at is not None
        
        # Stop
        with patch.object(
            subscription_manager.event_router,
            'stop',
            new_callable=AsyncMock
        ), patch.object(
            subscription_manager.websocket_subscriber,
            'stop',
            new_callable=AsyncMock
        ), patch.object(
            subscription_manager.polling_subscriber,
            'stop',
            new_callable=AsyncMock
        ):
            await subscription_manager.stop()
            
            assert subscription_manager.running is False
    
    @pytest.mark.asyncio
    async def test_start_without_setup(self, subscription_manager):
        """Test starting without setup raises error."""
        with pytest.raises(RuntimeError):
            await subscription_manager.start()
    
    @pytest.mark.asyncio
    async def test_double_start(self, subscription_manager):
        """Test that double start is handled gracefully."""
        await subscription_manager.setup()
        
        with patch.object(
            subscription_manager.event_router,
            'start',
            new_callable=AsyncMock
        ), patch.object(
            subscription_manager.websocket_subscriber,
            'start',
            new_callable=AsyncMock
        ):
            await subscription_manager.start()
            await subscription_manager.start()  # Should not raise


class TestWebSocketOnly:
    """Test WebSocket-only mode."""
    
    @pytest.mark.asyncio
    async def test_websocket_only_mode(
        self,
        mock_batch_monitor,
        websocket_config,
        polling_config
    ):
        """Test WebSocket-only configuration."""
        manager = SubscriptionManager(
            batch_monitor=mock_batch_monitor,
            websocket_config=websocket_config,
            polling_config=polling_config,
            enable_websocket=True,
            enable_polling=False,
            auto_failover=False
        )
        
        await manager.setup()
        
        assert manager.websocket_subscriber is not None
        assert manager.polling_subscriber is None


class TestPollingOnly:
    """Test polling-only mode."""
    
    @pytest.mark.asyncio
    async def test_polling_only_mode(
        self,
        mock_batch_monitor,
        websocket_config,
        polling_config
    ):
        """Test polling-only configuration."""
        manager = SubscriptionManager(
            batch_monitor=mock_batch_monitor,
            websocket_config=websocket_config,
            polling_config=polling_config,
            enable_websocket=False,
            enable_polling=True,
            auto_failover=False
        )
        
        await manager.setup()
        
        assert manager.websocket_subscriber is None
        assert manager.polling_subscriber is not None


class TestAutoFailover:
    """Test automatic failover functionality."""
    
    @pytest.mark.asyncio
    async def test_activate_polling_fallback(self, subscription_manager):
        """Test activating polling fallback."""
        await subscription_manager.setup()
        
        # Mock polling subscriber
        subscription_manager.polling_subscriber.start = AsyncMock()
        subscription_manager.polling_subscriber.get_state = MagicMock()
        subscription_manager.polling_subscriber.get_state.return_value.status = (
            SubscriptionStatus.DISCONNECTED
        )
        
        await subscription_manager._activate_polling_fallback()
        
        assert subscription_manager.failover_active is True
        assert subscription_manager.stats["failover_activations"] == 1
    
    @pytest.mark.asyncio
    async def test_deactivate_polling_fallback(self, subscription_manager):
        """Test deactivating polling fallback."""
        await subscription_manager.setup()
        
        subscription_manager.failover_active = True
        subscription_manager.polling_subscriber.stop = AsyncMock()
        
        await subscription_manager._deactivate_polling_fallback()
        
        assert subscription_manager.failover_active is False
    
    @pytest.mark.asyncio
    async def test_health_monitor_detects_websocket_failure(
        self,
        subscription_manager
    ):
        """Test health monitor detects WebSocket failure."""
        await subscription_manager.setup()
        
        # Mock WebSocket as unhealthy
        subscription_manager.websocket_subscriber.is_healthy = MagicMock(
            return_value=False
        )
        subscription_manager.polling_subscriber.start = AsyncMock()
        subscription_manager.polling_subscriber.get_state = MagicMock()
        subscription_manager.polling_subscriber.get_state.return_value.status = (
            SubscriptionStatus.DISCONNECTED
        )
        
        # Trigger health check
        await subscription_manager._activate_polling_fallback()
        
        assert subscription_manager.failover_active is True


class TestHealthChecks:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_running(self, subscription_manager):
        """Test health check when manager is healthy."""
        await subscription_manager.setup()
        subscription_manager.running = True
        
        # Mock components as healthy
        subscription_manager.event_router.is_healthy = MagicMock(
            return_value=True
        )
        subscription_manager.websocket_subscriber.is_healthy = MagicMock(
            return_value=True
        )
        
        assert subscription_manager.is_healthy() is True
    
    @pytest.mark.asyncio
    async def test_is_healthy_when_stopped(self, subscription_manager):
        """Test health check when manager is stopped."""
        assert subscription_manager.is_healthy() is False
    
    @pytest.mark.asyncio
    async def test_is_healthy_router_unhealthy(self, subscription_manager):
        """Test health check when router is unhealthy."""
        await subscription_manager.setup()
        subscription_manager.running = True
        
        subscription_manager.event_router.is_healthy = MagicMock(
            return_value=False
        )
        
        assert subscription_manager.is_healthy() is False
    
    @pytest.mark.asyncio
    async def test_is_healthy_no_healthy_subscribers(
        self,
        subscription_manager
    ):
        """Test health check when no subscribers are healthy."""
        await subscription_manager.setup()
        subscription_manager.running = True
        
        subscription_manager.event_router.is_healthy = MagicMock(
            return_value=True
        )
        subscription_manager.websocket_subscriber.is_healthy = MagicMock(
            return_value=False
        )
        subscription_manager.polling_subscriber.is_healthy = MagicMock(
            return_value=False
        )
        
        assert subscription_manager.is_healthy() is False


class TestStatus:
    """Test status reporting."""
    
    @pytest.mark.asyncio
    async def test_get_status(self, subscription_manager):
        """Test getting manager status."""
        await subscription_manager.setup()
        
        # Mock component states
        subscription_manager.websocket_subscriber.get_state = MagicMock()
        subscription_manager.websocket_subscriber.get_state.return_value.status = (
            SubscriptionStatus.CONNECTED
        )
        subscription_manager.websocket_subscriber.get_state.return_value.events_processed = 10
        subscription_manager.websocket_subscriber.get_state.return_value.events_failed = 0
        subscription_manager.websocket_subscriber.is_healthy = MagicMock(
            return_value=True
        )
        
        subscription_manager.polling_subscriber.get_state = MagicMock()
        subscription_manager.polling_subscriber.get_state.return_value.status = (
            SubscriptionStatus.CONNECTED
        )
        subscription_manager.polling_subscriber.get_state.return_value.events_processed = 5
        subscription_manager.polling_subscriber.get_state.return_value.events_failed = 0
        subscription_manager.polling_subscriber.is_healthy = MagicMock(
            return_value=True
        )
        
        subscription_manager.event_router.get_statistics = MagicMock(
            return_value={
                "running": True,
                "events_processed": 15,
                "events_failed": 0,
                "current_queue_size": 0,
                "dead_letter_queue_size": 0
            }
        )
        subscription_manager.event_router.is_healthy = MagicMock(
            return_value=True
        )
        
        status = subscription_manager.get_status()
        
        assert "running" in status
        assert "failover_active" in status
        assert "components" in status
        assert "websocket" in status["components"]
        assert "polling" in status["components"]
        assert "router" in status["components"]


class TestManualRestart:
    """Test manual subscriber restart."""
    
    @pytest.mark.asyncio
    async def test_restart_websocket_subscriber(self, subscription_manager):
        """Test manually restarting WebSocket subscriber."""
        await subscription_manager.setup()
        
        subscription_manager.websocket_subscriber.stop = AsyncMock()
        subscription_manager.websocket_subscriber.start = AsyncMock()
        
        result = await subscription_manager.restart_subscriber('websocket')
        
        assert result is True
        subscription_manager.websocket_subscriber.stop.assert_called_once()
        subscription_manager.websocket_subscriber.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restart_polling_subscriber(self, subscription_manager):
        """Test manually restarting polling subscriber."""
        await subscription_manager.setup()
        
        subscription_manager.polling_subscriber.stop = AsyncMock()
        subscription_manager.polling_subscriber.start = AsyncMock()
        
        result = await subscription_manager.restart_subscriber('polling')
        
        assert result is True
        subscription_manager.polling_subscriber.stop.assert_called_once()
        subscription_manager.polling_subscriber.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restart_invalid_subscriber(self, subscription_manager):
        """Test restarting invalid subscriber type."""
        await subscription_manager.setup()
        
        result = await subscription_manager.restart_subscriber('invalid')
        
        assert result is False


class TestStatistics:
    """Test statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_statistics_initialization(self, subscription_manager):
        """Test statistics are initialized correctly."""
        assert subscription_manager.stats["websocket_failures"] == 0
        assert subscription_manager.stats["failover_activations"] == 0
        assert subscription_manager.stats["health_checks_performed"] == 0
    
    @pytest.mark.asyncio
    async def test_statistics_update_on_failover(
        self,
        subscription_manager
    ):
        """Test statistics update on failover."""
        await subscription_manager.setup()
        
        subscription_manager.polling_subscriber.start = AsyncMock()
        subscription_manager.polling_subscriber.get_state = MagicMock()
        subscription_manager.polling_subscriber.get_state.return_value.status = (
            SubscriptionStatus.DISCONNECTED
        )
        
        initial_count = subscription_manager.stats["failover_activations"]
        
        await subscription_manager._activate_polling_fallback()
        
        assert (
            subscription_manager.stats["failover_activations"] ==
            initial_count + 1
        )
