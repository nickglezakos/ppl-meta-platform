"""
Event Subscription Integration Example

Demonstrates how to set up the complete event subscription pipeline using
the high-level SubscriptionManager.

This shows the full data flow:
Orchestrator/Vision → Subscriber → Router → Handler → Monitor → Batch Trigger

Two approaches are demonstrated:
1. Simple: Using the integration helper (recommended)
2. Manual: Setting up all components individually (for advanced use)
"""

import asyncio
import logging
from typing import List
from uuid import UUID

from src.services.integration import create_subscription_pipeline
from src.services.batch_repository import BatchProcessingRepository
from src.core.database import DatabaseManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def simple_setup_example(
    collection_ids: List[UUID],
    orchestrator_url: str = "http://localhost:8002",
    vision_service_url: str = "http://localhost:8003"
):
    """
    Simple setup using the integration helper (RECOMMENDED).
    
    This is the easiest way to get started.
    
    Args:
        collection_ids: List of collection UUIDs to monitor
        orchestrator_url: Orchestrator service URL
        vision_service_url: Vision service URL
        
    Returns:
        SubscriptionManager instance
    """
    logger.info("Setting up pipeline using integration helper...")
    
    # 1. Initialize database and repository
    db_manager = DatabaseManager()
    await db_manager.connect()
    repository = BatchProcessingRepository(db_manager.get_session())
    
    # 2. Create complete pipeline with one function call
    manager = await create_subscription_pipeline(
        repository=repository,
        collection_ids=collection_ids,
        orchestrator_url=orchestrator_url,
        vision_service_url=vision_service_url,
        enable_websocket=True,
        enable_polling=True,
        auto_failover=True
    )
    
    logger.info("Pipeline setup complete!")
    return manager


async def setup_event_pipeline(
    collection_ids: List[UUID],
    orchestrator_url: str = "http://localhost:8002",
    vision_service_url: str = "http://localhost:8003"
) -> tuple:
    """
    Set up the complete event processing pipeline.
    
    Args:
        collection_ids: List of collection UUIDs to monitor
        orchestrator_url: Orchestrator service URL
        vision_service_url: Vision service URL
        
    Returns:
        Tuple of (router, websocket_subscriber, polling_subscriber, handler, monitor)
    """
    logger.info("Setting up event processing pipeline...")
    
    # 1. Initialize database and repository
    db_manager = DatabaseManager()
    await db_manager.connect()
    repository = BatchProcessingRepository(db_manager.get_session())
    
    # 2. Create batch monitor
    batch_monitor = BatchMonitor(repository=repository)
    logger.info("✓ Batch monitor created")
    
    # 3. Create batch event handler
    batch_event_handler = BatchEventHandler(
        batch_monitor=batch_monitor,
        enable_video_completion=True,
        enable_recording_stop=True
    )
    logger.info("✓ Batch event handler created")
    
    # 4. Create event router with custom config
    router_config = EventRouterConfig(
        max_queue_size=1000,
        worker_count=3,
        retry_max_attempts=3,
        retry_initial_delay=1.0,
        retry_max_delay=30.0,
        retry_backoff_multiplier=2.0,
        dead_letter_queue_max_size=500
    )
    
    event_router = await create_event_router(
        batch_event_handler=batch_event_handler,
        router_config=router_config,
        collection_filter=collection_ids
    )
    logger.info("✓ Event router created")
    
    # 5. Create WebSocket subscriber (primary)
    websocket_config = SubscriptionConfig(
        orchestrator_url=orchestrator_url,
        event_endpoint="/api/v1/events/subscribe",
        event_types=["face_detection_completed"],
        collections=collection_ids,
        reconnect_initial_delay=5.0,
        reconnect_max_delay=60.0,
        reconnect_backoff_multiplier=2.0,
        heartbeat_interval_seconds=30.0,
        heartbeat_timeout_seconds=10.0,
        event_queue_max_size=100
    )
    
    websocket_subscriber = WebSocketEventSubscriber(
        config=websocket_config,
        on_event=event_router.route_event
    )
    logger.info("✓ WebSocket subscriber created")
    
    # 6. Create Polling subscriber (fallback)
    polling_config = PollingConfig(
        vision_service_url=vision_service_url,
        polling_interval_seconds=30.0,
        lookback_minutes=5,
        deduplication_window_minutes=60
    )
    
    polling_subscriber = PollingEventSubscriber(
        config=polling_config,
        on_event=event_router.route_event,
        collection_filter=collection_ids
    )
    logger.info("✓ Polling subscriber created")
    
    logger.info("Event processing pipeline setup complete!")
    
    return (
        event_router,
        websocket_subscriber,
        polling_subscriber,
        batch_event_handler,
        batch_monitor
    )


async def start_event_pipeline(
    router: EventRouter,
    websocket_subscriber: WebSocketEventSubscriber,
    polling_subscriber: PollingEventSubscriber
) -> None:
    """
    Start all components of the event pipeline.
    
    Args:
        router: Event router
        websocket_subscriber: WebSocket subscriber
        polling_subscriber: Polling subscriber
    """
    logger.info("Starting event processing pipeline...")
    
    # Start router first
    await router.start()
    logger.info("✓ Event router started")
    
    # Start WebSocket subscriber (primary)
    await websocket_subscriber.start()
    logger.info("✓ WebSocket subscriber started")
    
    # Start polling subscriber (fallback)
    await polling_subscriber.start()
    logger.info("✓ Polling subscriber started")
    
    logger.info("All components running!")


async def stop_event_pipeline(
    router: EventRouter,
    websocket_subscriber: WebSocketEventSubscriber,
    polling_subscriber: PollingEventSubscriber
) -> None:
    """
    Stop all components gracefully.
    
    Args:
        router: Event router
        websocket_subscriber: WebSocket subscriber
        polling_subscriber: Polling subscriber
    """
    logger.info("Stopping event processing pipeline...")
    
    # Stop subscribers first
    await websocket_subscriber.stop()
    logger.info("✓ WebSocket subscriber stopped")
    
    await polling_subscriber.stop()
    logger.info("✓ Polling subscriber stopped")
    
    # Stop router last (to process remaining events)
    await router.stop()
    logger.info("✓ Event router stopped")
    
    logger.info("Pipeline shutdown complete!")


async def print_statistics(
    router: EventRouter,
    websocket_subscriber: WebSocketEventSubscriber,
    polling_subscriber: PollingEventSubscriber,
    batch_monitor: BatchMonitor
) -> None:
    """
    Print statistics for all components.
    
    Args:
        router: Event router
        websocket_subscriber: WebSocket subscriber
        polling_subscriber: Polling subscriber
        batch_monitor: Batch monitor
    """
    print("\n" + "="*60)
    print("EVENT PIPELINE STATISTICS")
    print("="*60)
    
    # Router stats
    router_stats = router.get_statistics()
    print(f"\n📊 Event Router:")
    print(f"  Events Received:  {router_stats['events_received']}")
    print(f"  Events Processed: {router_stats['events_processed']}")
    print(f"  Events Failed:    {router_stats['events_failed']}")
    print(f"  Events Filtered:  {router_stats['events_filtered']}")
    print(f"  Queue Size:       {router_stats['current_queue_size']}")
    print(f"  Dead Letter:      {router_stats['dead_letter_queue_size']}")
    print(f"  Events/sec:       {router_stats['events_per_second']:.2f}")
    print(f"  Uptime:           {router_stats['uptime_seconds']:.1f}s")
    
    # WebSocket stats
    ws_state = websocket_subscriber.get_state()
    ws_stats = websocket_subscriber.get_statistics()
    print(f"\n🌐 WebSocket Subscriber:")
    print(f"  Status:           {ws_state.status.value}")
    print(f"  Events Received:  {ws_state.events_received}")
    print(f"  Events Processed: {ws_state.events_processed}")
    print(f"  Events Failed:    {ws_state.events_failed}")
    print(f"  Reconnections:    {ws_state.reconnect_attempts}")
    print(f"  Uptime:           {ws_stats.get('uptime_seconds', 0):.1f}s")
    print(f"  Healthy:          {'✓' if ws_stats.get('healthy', False) else '✗'}")
    
    # Polling stats
    poll_state = polling_subscriber.get_state()
    poll_stats = polling_subscriber.get_statistics()
    print(f"\n📡 Polling Subscriber:")
    print(f"  Status:           {poll_state.status.value}")
    print(f"  Events Received:  {poll_state.events_received}")
    print(f"  Events Processed: {poll_state.events_processed}")
    print(f"  Events Failed:    {poll_state.events_failed}")
    print(f"  Uptime:           {poll_stats.get('uptime_seconds', 0):.1f}s")
    print(f"  Healthy:          {'✓' if poll_stats.get('healthy', False) else '✗'}")
    
    # Batch monitor stats
    monitor_stats = batch_monitor.get_statistics()
    print(f"\n📦 Batch Monitor:")
    print(f"  Videos Received:  {monitor_stats['videos_received']}")
    print(f"  Batches Triggered: {monitor_stats['batches_triggered']}")
    print(f"  Active Batches:   {monitor_stats['active_batches']}")
    print(f"  Videos Pending:   {monitor_stats['videos_pending']}")
    
    print("\n" + "="*60 + "\n")


async def main():
    """
    Example main function demonstrating the event pipeline.
    
    Uses the simple integration helper for easy setup.
    """
    # Example collection IDs to monitor
    collection_ids = [
        UUID("12345678-1234-5678-1234-567812345678"),
        UUID("87654321-4321-8765-4321-876543218765")
    ]
    
    try:
        # Setup pipeline using simple helper
        manager = await simple_setup_example(
            collection_ids=collection_ids,
            orchestrator_url="http://localhost:8002",
            vision_service_url="http://localhost:8003"
        )
        
        # Start pipeline
        await manager.start()
        logger.info("Pipeline running... Press Ctrl+C to stop")
        
        # Print statistics every 30 seconds
        try:
            while True:
                await asyncio.sleep(30)
                print_manager_statistics(manager)
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
        
        # Stop pipeline
        await manager.stop()
        
        # Final statistics
        print_manager_statistics(manager)
        
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)


def print_manager_statistics(manager):
    """Print statistics from SubscriptionManager."""
    status = manager.get_status()
    
    print("\n" + "="*60)
    print("EVENT PIPELINE STATISTICS")
    print("="*60)
    
    # Overall status
    print(f"\n📊 Overall Status:")
    print(f"  Running:          {'✓' if status['running'] else '✗'}")
    print(f"  Healthy:          {'✓' if manager.is_healthy() else '✗'}")
    print(f"  Failover Active:  {'✓' if status['failover_active'] else '✗'}")
    
    # Component status
    if 'websocket' in status['components']:
        ws = status['components']['websocket']
        print(f"\n🌐 WebSocket Subscriber:")
        print(f"  Status:           {ws['status']}")
        print(f"  Healthy:          {'✓' if ws['healthy'] else '✗'}")
        print(f"  Events Processed: {ws['events_processed']}")
        print(f"  Events Failed:    {ws['events_failed']}")
    
    if 'polling' in status['components']:
        poll = status['components']['polling']
        print(f"\n📡 Polling Subscriber:")
        print(f"  Status:           {poll['status']}")
        print(f"  Healthy:          {'✓' if poll['healthy'] else '✗'}")
        print(f"  Events Processed: {poll['events_processed']}")
        print(f"  Events Failed:    {poll['events_failed']}")
    
    if 'router' in status['components']:
        router = status['components']['router']
        print(f"\n📊 Event Router:")
        print(f"  Events Processed: {router['events_processed']}")
        print(f"  Events Failed:    {router['events_failed']}")
        print(f"  Queue Size:       {router['queue_size']}")
        print(f"  Dead Letter:      {router['dead_letter_size']}")
    
    if 'batch_monitor' in status['components']:
        batch = status['components']['batch_monitor']
        print(f"\n📦 Batch Monitor:")
        print(f"  Batches Triggered: {batch['batches_triggered']}")
        print(f"  Active Batches:   {batch['active_batches']}")
        print(f"  Videos Pending:   {batch['videos_pending']}")
    
    # Statistics
    stats = status['statistics']
    if 'uptime_seconds' in stats:
        print(f"\n⏱️  Uptime: {stats['uptime_seconds']:.1f}s")
    print(f"  Total Events:     {stats['total_events_processed']}")
    print(f"  Failover Count:   {stats['failover_activations']}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
