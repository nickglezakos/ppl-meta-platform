"""
Integration Module

Provides high-level functions for setting up the complete event
subscription and batch processing pipeline with minimal configuration.

This module simplifies integration by providing:
- Single function to set up complete pipeline
- Sensible defaults for all configurations
- Easy customization options
"""

import logging
from typing import Optional, List
from uuid import UUID

from ..models.events import (
    SubscriptionConfig,
    PollingConfig,
    EventRouterConfig
)
from .subscription_manager import SubscriptionManager
from .batch_monitor import BatchMonitor
from .batch_repository import BatchProcessingRepository


logger = logging.getLogger(__name__)


async def create_subscription_pipeline(
    repository: BatchProcessingRepository,
    collection_ids: List[UUID],
    orchestrator_url: str = "http://localhost:8002",
    vision_service_url: str = "http://localhost:8003",
    enable_websocket: bool = True,
    enable_polling: bool = True,
    auto_failover: bool = True,
    websocket_config: Optional[SubscriptionConfig] = None,
    polling_config: Optional[PollingConfig] = None,
    router_config: Optional[EventRouterConfig] = None
) -> SubscriptionManager:
    """
    Create and set up complete event subscription pipeline.
    
    This is the main entry point for integrating the batch processing
    system with event subscriptions.
    
    Args:
        repository: BatchProcessingRepository instance
        collection_ids: List of collection UUIDs to monitor
        orchestrator_url: Orchestrator service URL
        vision_service_url: Vision service URL
        enable_websocket: Enable WebSocket subscriber (real-time)
        enable_polling: Enable polling subscriber (fallback)
        auto_failover: Enable automatic failover to polling
        websocket_config: Custom WebSocket config (optional)
        polling_config: Custom polling config (optional)
        router_config: Custom router config (optional)
        
    Returns:
        Configured SubscriptionManager instance
        
    Example:
        ```python
        # Create repository
        repository = BatchProcessingRepository(db_session)
        
        # Set up pipeline
        manager = await create_subscription_pipeline(
            repository=repository,
            collection_ids=[collection_uuid],
            orchestrator_url="http://localhost:8002",
            vision_service_url="http://localhost:8003"
        )
        
        # Start pipeline
        await manager.start()
        
        # ... run application ...
        
        # Stop pipeline
        await manager.stop()
        ```
    """
    logger.info("Creating subscription pipeline...")
    
    # 1. Create batch monitor
    batch_monitor = BatchMonitor(repository=repository)
    logger.info("✓ Batch monitor created")
    
    # 2. Create default configurations if not provided
    if websocket_config is None:
        websocket_config = SubscriptionConfig(
            orchestrator_url=orchestrator_url,
            event_endpoint="/api/v1/events/subscribe",
            event_types=["face_detection_completed", "recording_stopped"],
            collections=collection_ids,
            reconnect_initial_delay=5.0,
            reconnect_max_delay=60.0,
            reconnect_backoff_multiplier=2.0,
            heartbeat_interval_seconds=30.0,
            heartbeat_timeout_seconds=10.0,
            event_queue_max_size=100
        )
        logger.info("✓ Using default WebSocket configuration")
    
    if polling_config is None:
        polling_config = PollingConfig(
            vision_service_url=vision_service_url,
            polling_interval_seconds=30.0,
            lookback_minutes=5,
            deduplication_window_minutes=60
        )
        logger.info("✓ Using default polling configuration")
    
    if router_config is None:
        router_config = EventRouterConfig(
            max_queue_size=1000,
            worker_count=3,
            retry_max_attempts=3,
            retry_initial_delay=1.0,
            retry_max_delay=30.0,
            retry_backoff_multiplier=2.0,
            dead_letter_queue_max_size=500
        )
        logger.info("✓ Using default router configuration")
    
    # 3. Create subscription manager
    manager = SubscriptionManager(
        batch_monitor=batch_monitor,
        websocket_config=websocket_config,
        polling_config=polling_config,
        router_config=router_config,
        collection_filter=collection_ids,
        enable_websocket=enable_websocket,
        enable_polling=enable_polling,
        auto_failover=auto_failover
    )
    
    # 4. Set up all components
    await manager.setup()
    
    logger.info("✓ Subscription pipeline created and ready!")
    logger.info(
        f"  Collections: {len(collection_ids)}"
    )
    logger.info(
        f"  WebSocket: {'enabled' if enable_websocket else 'disabled'}"
    )
    logger.info(
        f"  Polling: {'enabled' if enable_polling else 'disabled'}"
    )
    logger.info(
        f"  Auto-failover: {'enabled' if auto_failover else 'disabled'}"
    )
    
    return manager


def create_websocket_only_pipeline(
    repository: BatchProcessingRepository,
    collection_ids: List[UUID],
    orchestrator_url: str = "http://localhost:8002"
):
    """
    Create pipeline with WebSocket subscriber only.
    
    Use when you want real-time events and don't need polling fallback.
    
    Args:
        repository: BatchProcessingRepository instance
        collection_ids: List of collection UUIDs to monitor
        orchestrator_url: Orchestrator service URL
        
    Returns:
        Configured SubscriptionManager instance
    """
    return create_subscription_pipeline(
        repository=repository,
        collection_ids=collection_ids,
        orchestrator_url=orchestrator_url,
        enable_websocket=True,
        enable_polling=False,
        auto_failover=False
    )


def create_polling_only_pipeline(
    repository: BatchProcessingRepository,
    collection_ids: List[UUID],
    vision_service_url: str = "http://localhost:8003"
):
    """
    Create pipeline with polling subscriber only.
    
    Use when WebSocket is not available or you prefer polling.
    
    Args:
        repository: BatchProcessingRepository instance
        collection_ids: List of collection UUIDs to monitor
        vision_service_url: Vision service URL
        
    Returns:
        Configured SubscriptionManager instance
    """
    return create_subscription_pipeline(
        repository=repository,
        collection_ids=collection_ids,
        vision_service_url=vision_service_url,
        enable_websocket=False,
        enable_polling=True,
        auto_failover=False
    )


def create_dual_mode_pipeline(
    repository: BatchProcessingRepository,
    collection_ids: List[UUID],
    orchestrator_url: str = "http://localhost:8002",
    vision_service_url: str = "http://localhost:8003"
):
    """
    Create pipeline with both WebSocket and Polling running simultaneously.
    
    Use for maximum reliability - both subscribers run at the same time.
    Events are deduplicated by the router.
    
    Args:
        repository: BatchProcessingRepository instance
        collection_ids: List of collection UUIDs to monitor
        orchestrator_url: Orchestrator service URL
        vision_service_url: Vision service URL
        
    Returns:
        Configured SubscriptionManager instance
    """
    return create_subscription_pipeline(
        repository=repository,
        collection_ids=collection_ids,
        orchestrator_url=orchestrator_url,
        vision_service_url=vision_service_url,
        enable_websocket=True,
        enable_polling=True,
        auto_failover=False  # Both always on, no failover needed
    )
