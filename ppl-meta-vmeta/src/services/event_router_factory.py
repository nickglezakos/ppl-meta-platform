"""
Event Router Factory

Factory functions for creating and configuring EventRouter instances
connected to BatchEventHandler and BatchMonitor.
"""

import logging
from typing import Optional, List
from uuid import UUID

from ..models.events import EventRouterConfig, EventType
from .event_router import EventRouter
from .batch_event_handler import BatchEventHandler


logger = logging.getLogger(__name__)


async def create_event_router(
    batch_event_handler: BatchEventHandler,
    router_config: Optional[EventRouterConfig] = None,
    collection_filter: Optional[List[UUID]] = None
) -> EventRouter:
    """
    Create and configure an EventRouter instance.
    
    Args:
        batch_event_handler: BatchEventHandler instance to route events to
        router_config: Optional router configuration (uses defaults if None)
        collection_filter: Optional list of collection UUIDs to filter events
        
    Returns:
        Configured EventRouter instance
    """
    # Use default config if not provided
    if router_config is None:
        router_config = EventRouterConfig()
        logger.info("Using default EventRouter configuration")
    
    # Create router with batch event handler
    router = EventRouter(
        config=router_config,
        event_handler=batch_event_handler.handle_event,
        collection_filter=collection_filter
    )
    
    logger.info(
        f"EventRouter created for collections: "
        f"{collection_filter if collection_filter else 'all'}"
    )
    
    return router


def create_default_router_config(
    worker_count: int = 3,
    max_queue_size: int = 1000,
    retry_max_attempts: int = 3
) -> EventRouterConfig:
    """
    Create EventRouterConfig with custom parameters.
    
    Args:
        worker_count: Number of worker tasks for processing events
        max_queue_size: Maximum size of event queue
        retry_max_attempts: Maximum retry attempts for failed events
        
    Returns:
        EventRouterConfig instance
    """
    return EventRouterConfig(
        max_queue_size=max_queue_size,
        worker_count=worker_count,
        retry_max_attempts=retry_max_attempts,
        retry_initial_delay=1.0,
        retry_max_delay=30.0,
        retry_backoff_multiplier=2.0,
        dead_letter_queue_max_size=500
    )
