"""
Subscription Manager

Coordinates event subscribers (WebSocket + Polling) with the EventRouter
and BatchMonitor to provide a complete event processing pipeline.

This manager handles:
- Lifecycle management for all components
- Automatic failover from WebSocket to Polling
- Health monitoring and recovery
- Graceful shutdown with proper cleanup

Architecture:
    SubscriptionManager
    ├── WebSocketEventSubscriber (primary)
    ├── PollingEventSubscriber (fallback)
    ├── EventRouter
    ├── BatchEventHandler
    └── BatchMonitor
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from ..models.events import (
    SubscriptionConfig,
    PollingConfig,
    EventRouterConfig,
    SubscriptionStatus
)
from .event_subscriber import EventSubscriber
from .websocket_subscriber import WebSocketEventSubscriber
from .polling_subscriber import PollingEventSubscriber
from .event_router import EventRouter
from .event_router_factory import create_event_router
from .batch_event_handler import BatchEventHandler
from .batch_monitor import BatchMonitor


logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages the complete event subscription and processing pipeline.
    
    Coordinates:
    - WebSocket subscriber (primary real-time events)
    - Polling subscriber (fallback for reliability)
    - Event router (queuing and dispatch)
    - Batch event handler (event routing)
    - Batch monitor (batch processing logic)
    """
    
    def __init__(
        self,
        batch_monitor: BatchMonitor,
        websocket_config: SubscriptionConfig,
        polling_config: PollingConfig,
        router_config: Optional[EventRouterConfig] = None,
        collection_filter: Optional[List[UUID]] = None,
        enable_websocket: bool = True,
        enable_polling: bool = True,
        auto_failover: bool = True
    ):
        """
        Initialize subscription manager.
        
        Args:
            batch_monitor: Batch monitor instance
            websocket_config: WebSocket subscription configuration
            polling_config: Polling subscription configuration
            router_config: Event router configuration (optional)
            collection_filter: Filter events by collection IDs
            enable_websocket: Enable WebSocket subscriber
            enable_polling: Enable polling subscriber
            auto_failover: Enable automatic failover to polling
        """
        self.batch_monitor = batch_monitor
        self.collection_filter = collection_filter
        self.enable_websocket = enable_websocket
        self.enable_polling = enable_polling
        self.auto_failover = auto_failover
        
        # Configurations
        self.websocket_config = websocket_config
        self.polling_config = polling_config
        self.router_config = router_config or EventRouterConfig()
        
        # Components (initialized in setup)
        self.event_router: Optional[EventRouter] = None
        self.batch_event_handler: Optional[BatchEventHandler] = None
        self.websocket_subscriber: Optional[WebSocketEventSubscriber] = None
        self.polling_subscriber: Optional[PollingEventSubscriber] = None
        
        # State
        self.running = False
        self.started_at: Optional[datetime] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.failover_active = False
        
        # Statistics
        self.stats = {
            "started_at": None,
            "websocket_failures": 0,
            "failover_activations": 0,
            "health_checks_performed": 0,
            "total_events_processed": 0
        }
        
        logger.info(
            f"SubscriptionManager initialized "
            f"(websocket: {enable_websocket}, "
            f"polling: {enable_polling}, "
            f"auto_failover: {auto_failover})"
        )
    
    async def setup(self) -> None:
        """
        Set up all components of the pipeline.
        
        Must be called before start().
        """
        logger.info("Setting up subscription pipeline...")
        
        # 1. Create batch event handler
        self.batch_event_handler = BatchEventHandler(
            batch_monitor=self.batch_monitor,
            enable_video_completion=True,
            enable_recording_stop=True
        )
        logger.info("✓ Batch event handler created")
        
        # 2. Create event router
        self.event_router = await create_event_router(
            batch_event_handler=self.batch_event_handler,
            router_config=self.router_config,
            collection_filter=self.collection_filter
        )
        logger.info("✓ Event router created")
        
        # 3. Create WebSocket subscriber (if enabled)
        if self.enable_websocket:
            self.websocket_subscriber = WebSocketEventSubscriber(
                config=self.websocket_config,
                on_event=self.event_router.route_event
            )
            logger.info("✓ WebSocket subscriber created")
        
        # 4. Create Polling subscriber (if enabled)
        if self.enable_polling:
            self.polling_subscriber = PollingEventSubscriber(
                config=self.polling_config,
                on_event=self.event_router.route_event,
                collection_filter=self.collection_filter
            )
            logger.info("✓ Polling subscriber created")
        
        logger.info("Subscription pipeline setup complete!")
    
    async def start(self) -> None:
        """
        Start all components of the pipeline.
        
        Starts in order:
        1. Event router
        2. WebSocket subscriber (primary)
        3. Polling subscriber (fallback, if WebSocket fails or disabled)
        4. Health monitoring
        """
        if self.running:
            logger.warning("SubscriptionManager already running")
            return
        
        if not self.event_router:
            raise RuntimeError(
                "Pipeline not set up. Call setup() before start()"
            )
        
        logger.info("Starting subscription pipeline...")
        
        self.running = True
        self.started_at = datetime.now(timezone.utc)
        self.stats["started_at"] = self.started_at
        
        # 1. Start event router
        await self.event_router.start()
        logger.info("✓ Event router started")
        
        # 2. Start WebSocket subscriber (primary)
        if self.enable_websocket and self.websocket_subscriber:
            try:
                await self.websocket_subscriber.start()
                logger.info("✓ WebSocket subscriber started")
            except Exception as e:
                logger.error(
                    f"Failed to start WebSocket subscriber: {e}",
                    exc_info=True
                )
                self.stats["websocket_failures"] += 1
                
                # Activate polling as fallback
                if self.auto_failover and self.enable_polling:
                    logger.info("Activating polling fallback...")
                    await self._activate_polling_fallback()
        
        # 3. Start polling subscriber if:
        #    - WebSocket disabled, OR
        #    - Failover already active, OR
        #    - Both enabled (dual mode)
        should_start_polling = (
            not self.enable_websocket or
            self.failover_active or
            (self.enable_websocket and self.enable_polling)
        )
        
        if should_start_polling and self.polling_subscriber:
            await self.polling_subscriber.start()
            logger.info("✓ Polling subscriber started")
        
        # 4. Start health monitoring
        if self.auto_failover:
            self.health_check_task = asyncio.create_task(
                self._health_monitor_loop(),
                name="SubscriptionManager-HealthMonitor"
            )
            logger.info("✓ Health monitoring started")
        
        logger.info("Subscription pipeline fully operational!")
    
    async def stop(self) -> None:
        """
        Stop all components gracefully.
        
        Stops in reverse order of startup.
        """
        if not self.running:
            return
        
        logger.info("Stopping subscription pipeline...")
        
        self.running = False
        
        # 1. Stop health monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Health monitoring stopped")
        
        # 2. Stop subscribers
        if self.websocket_subscriber:
            await self.websocket_subscriber.stop()
            logger.info("✓ WebSocket subscriber stopped")
        
        if self.polling_subscriber:
            await self.polling_subscriber.stop()
            logger.info("✓ Polling subscriber stopped")
        
        # 3. Stop event router (last, to process remaining events)
        if self.event_router:
            await self.event_router.stop()
            logger.info("✓ Event router stopped")
        
        logger.info("Subscription pipeline stopped!")
    
    async def _health_monitor_loop(self) -> None:
        """
        Periodically check health of subscribers and activate failover.
        
        Runs every 30 seconds to monitor WebSocket health.
        """
        logger.info("Health monitoring loop started")
        
        while self.running:
            try:
                await asyncio.sleep(30)
                
                self.stats["health_checks_performed"] += 1
                
                # Check WebSocket health
                if self.websocket_subscriber and self.enable_websocket:
                    ws_healthy = self.websocket_subscriber.is_healthy()
                    
                    if not ws_healthy and not self.failover_active:
                        logger.warning(
                            "WebSocket subscriber unhealthy, "
                            "activating polling fallback"
                        )
                        await self._activate_polling_fallback()
                    
                    elif ws_healthy and self.failover_active:
                        logger.info(
                            "WebSocket subscriber recovered, "
                            "deactivating polling fallback"
                        )
                        await self._deactivate_polling_fallback()
                
            except asyncio.CancelledError:
                logger.info("Health monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Health monitoring error: {e}",
                    exc_info=True
                )
    
    async def _activate_polling_fallback(self) -> None:
        """
        Activate polling subscriber as fallback.
        """
        if not self.enable_polling or not self.polling_subscriber:
            logger.warning(
                "Cannot activate polling fallback - polling disabled"
            )
            return
        
        if self.failover_active:
            logger.debug("Polling fallback already active")
            return
        
        logger.info("Activating polling fallback...")
        
        try:
            # Start polling subscriber if not already running
            polling_state = self.polling_subscriber.get_state()
            if polling_state.status != SubscriptionStatus.CONNECTED:
                await self.polling_subscriber.start()
            
            self.failover_active = True
            self.stats["failover_activations"] += 1
            
            logger.info("✓ Polling fallback activated")
            
        except Exception as e:
            logger.error(
                f"Failed to activate polling fallback: {e}",
                exc_info=True
            )
    
    async def _deactivate_polling_fallback(self) -> None:
        """
        Deactivate polling fallback when WebSocket recovers.
        
        Only deactivates if both WebSocket and Polling are enabled
        (dual mode). If only polling is enabled, keeps it running.
        """
        if not self.failover_active:
            return
        
        # Only deactivate if we're in dual mode
        # (both WebSocket and Polling enabled)
        if not (self.enable_websocket and self.enable_polling):
            logger.debug(
                "Not in dual mode, keeping polling subscriber active"
            )
            return
        
        logger.info("Deactivating polling fallback...")
        
        try:
            # Stop polling subscriber
            if self.polling_subscriber:
                await self.polling_subscriber.stop()
            
            self.failover_active = False
            
            logger.info("✓ Polling fallback deactivated")
            
        except Exception as e:
            logger.error(
                f"Failed to deactivate polling fallback: {e}",
                exc_info=True
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the pipeline.
        
        Returns:
            Dictionary with status of all components
        """
        status = {
            "running": self.running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "failover_active": self.failover_active,
            "components": {}
        }
        
        # WebSocket subscriber status
        if self.websocket_subscriber:
            ws_state = self.websocket_subscriber.get_state()
            status["components"]["websocket"] = {
                "enabled": self.enable_websocket,
                "status": ws_state.status.value,
                "healthy": self.websocket_subscriber.is_healthy(),
                "events_processed": ws_state.events_processed,
                "events_failed": ws_state.events_failed
            }
        
        # Polling subscriber status
        if self.polling_subscriber:
            poll_state = self.polling_subscriber.get_state()
            status["components"]["polling"] = {
                "enabled": self.enable_polling,
                "status": poll_state.status.value,
                "healthy": self.polling_subscriber.is_healthy(),
                "events_processed": poll_state.events_processed,
                "events_failed": poll_state.events_failed
            }
        
        # Event router status
        if self.event_router:
            router_stats = self.event_router.get_statistics()
            status["components"]["router"] = {
                "running": router_stats["running"],
                "healthy": self.event_router.is_healthy(),
                "events_processed": router_stats["events_processed"],
                "events_failed": router_stats["events_failed"],
                "queue_size": router_stats["current_queue_size"],
                "dead_letter_size": router_stats.get("dead_letter_queue_size", 0)
            }
        
        # Batch monitor status
        if self.batch_monitor:
            monitor_stats = self.batch_monitor.get_statistics()
            status["components"]["batch_monitor"] = {
                "batches_triggered": monitor_stats["batches_triggered"],
                "active_batches": monitor_stats["active_batches"],
                "videos_pending": monitor_stats["videos_pending"]
            }
        
        # Overall statistics
        status["statistics"] = self.stats.copy()
        
        # Calculate total events
        total_events = 0
        if self.event_router:
            router_stats = self.event_router.get_statistics()
            total_events = router_stats.get("events_processed", 0)
        status["statistics"]["total_events_processed"] = total_events
        
        # Calculate uptime
        if self.started_at:
            uptime = datetime.now(timezone.utc) - self.started_at
            status["statistics"]["uptime_seconds"] = uptime.total_seconds()
        
        return status
    
    def is_healthy(self) -> bool:
        """
        Check overall health of the pipeline.
        
        Returns:
            True if pipeline is healthy
        """
        if not self.running:
            return False
        
        # Check router health
        if self.event_router and not self.event_router.is_healthy():
            logger.warning("Event router unhealthy")
            return False
        
        # Check if at least one subscriber is healthy
        websocket_healthy = (
            self.websocket_subscriber and
            self.websocket_subscriber.is_healthy()
        ) if self.enable_websocket else False
        
        polling_healthy = (
            self.polling_subscriber and
            self.polling_subscriber.is_healthy()
        ) if self.enable_polling else False
        
        if not (websocket_healthy or polling_healthy):
            logger.warning("No healthy subscribers")
            return False
        
        return True
    
    async def restart_subscriber(
        self,
        subscriber_type: str
    ) -> bool:
        """
        Manually restart a specific subscriber.
        
        Args:
            subscriber_type: "websocket" or "polling"
            
        Returns:
            True if restart successful
        """
        logger.info(f"Restarting {subscriber_type} subscriber...")
        
        try:
            if subscriber_type == "websocket" and self.websocket_subscriber:
                await self.websocket_subscriber.stop()
                await asyncio.sleep(2)
                await self.websocket_subscriber.start()
                logger.info("✓ WebSocket subscriber restarted")
                return True
            
            elif subscriber_type == "polling" and self.polling_subscriber:
                await self.polling_subscriber.stop()
                await asyncio.sleep(2)
                await self.polling_subscriber.start()
                logger.info("✓ Polling subscriber restarted")
                return True
            
            else:
                logger.warning(
                    f"Unknown or disabled subscriber type: {subscriber_type}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Failed to restart {subscriber_type} subscriber: {e}",
                exc_info=True
            )
            return False
