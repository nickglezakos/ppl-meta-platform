# Batch Processing Integration Guide

## Overview

This guide explains how to integrate the event subscription system with the BatchMonitor to enable continuous batch processing triggered by face detection events.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   SubscriptionManager                        │
│                                                              │
│  ┌──────────────┐       ┌──────────────┐                   │
│  │  WebSocket   │       │   Polling    │                   │
│  │  Subscriber  │       │  Subscriber  │                   │
│  │  (Primary)   │       │  (Fallback)  │                   │
│  └──────┬───────┘       └──────┬───────┘                   │
│         │                       │                            │
│         └───────────┬───────────┘                            │
│                     ▼                                        │
│            ┌────────────────┐                               │
│            │  Event Router  │                               │
│            │   (Queue +     │                               │
│            │   Workers)     │                               │
│            └────────┬───────┘                               │
│                     ▼                                        │
│          ┌──────────────────┐                               │
│          │ BatchEventHandler│                               │
│          └────────┬─────────┘                               │
│                   ▼                                          │
│          ┌──────────────────┐                               │
│          │  BatchMonitor    │                               │
│          │  (Batch Logic)   │                               │
│          └────────┬─────────┘                               │
└──────────────────│──────────────────────────────────────────┘
                   ▼
          ┌────────────────┐
          │  Database      │
          │  (Batch State) │
          └────────────────┘
```

## Quick Start

### Simple Setup (Recommended)

```python
from uuid import UUID
from src.services.integration import create_subscription_pipeline
from src.services.batch_repository import BatchProcessingRepository
from src.core.database import DatabaseManager

# Initialize database
db_manager = DatabaseManager()
await db_manager.connect()
repository = BatchProcessingRepository(db_manager.get_session())

# Create pipeline with one function call
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=[UUID("your-collection-id")],
    orchestrator_url="http://localhost:8002",
    vision_service_url="http://localhost:8003",
    enable_websocket=True,
    enable_polling=True,
    auto_failover=True
)

# Start pipeline
await manager.start()

# ... application runs ...

# Stop pipeline
await manager.stop()
```

### Configuration Options

#### WebSocket + Polling with Auto-Failover (Default)

Best for production - WebSocket provides real-time events, polling activates automatically if WebSocket fails.

```python
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=collection_ids,
    enable_websocket=True,
    enable_polling=True,
    auto_failover=True
)
```

#### WebSocket Only

Use when you have reliable WebSocket connectivity and don't need fallback.

```python
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=collection_ids,
    enable_websocket=True,
    enable_polling=False,
    auto_failover=False
)
```

#### Polling Only

Use when WebSocket is not available or you prefer polling.

```python
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=collection_ids,
    enable_websocket=False,
    enable_polling=True,
    auto_failover=False
)
```

#### Dual Mode (Both Always On)

Maximum reliability - both subscribers run simultaneously. Events are deduplicated.

```python
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=collection_ids,
    enable_websocket=True,
    enable_polling=True,
    auto_failover=False
)
```

## Event Flow

1. **Event Source**
   - Orchestrator emits `face_detection_completed` events via WebSocket
   - Vision Service exposes completed sessions via REST API (polled)

2. **Subscription**
   - WebSocketEventSubscriber connects to Orchestrator WebSocket
   - PollingEventSubscriber polls Vision Service every 30 seconds

3. **Routing**
   - Events are queued in EventRouter
   - Worker pool processes events concurrently (3 workers default)
   - Failed events are retried with exponential backoff

4. **Handling**
   - BatchEventHandler routes events by type
   - `face_detection_completed` → `handle_video_completion_event()`
   - `recording_stopped` → `handle_recording_stop_event()`

5. **Batch Processing**
   - BatchMonitor receives video completion events
   - Accumulates videos until threshold reached
   - Triggers batch processing when conditions met

6. **Batch Trigger Conditions**
   - **Video threshold**: 10 videos accumulated
   - **Time threshold**: 60 minutes since batch creation
   - **Recording stopped**: Manual trigger

## Monitoring and Health Checks

### Get Pipeline Status

```python
status = manager.get_status()

print(f"Running: {status['running']}")
print(f"Healthy: {manager.is_healthy()}")
print(f"Failover Active: {status['failover_active']}")

# Component status
websocket_status = status['components']['websocket']
polling_status = status['components']['polling']
router_status = status['components']['router']
batch_status = status['components']['batch_monitor']
```

### Health Monitoring

The SubscriptionManager automatically monitors health every 30 seconds:

- Checks WebSocket subscriber health
- Activates polling fallback if WebSocket fails
- Deactivates fallback when WebSocket recovers

### Manual Subscriber Restart

```python
# Restart WebSocket subscriber
await manager.restart_subscriber('websocket')

# Restart Polling subscriber
await manager.restart_subscriber('polling')
```

## Advanced Configuration

### Custom Configurations

```python
from src.models.events import (
    SubscriptionConfig,
    PollingConfig,
    EventRouterConfig
)

# Custom WebSocket configuration
websocket_config = SubscriptionConfig(
    orchestrator_url="http://localhost:8002",
    event_endpoint="/api/v1/events/subscribe",
    event_types=["face_detection_completed", "recording_stopped"],
    collections=collection_ids,
    reconnect_initial_delay=5.0,
    reconnect_max_delay=60.0,
    heartbeat_interval_seconds=30.0
)

# Custom Polling configuration
polling_config = PollingConfig(
    vision_service_url="http://localhost:8003",
    polling_interval_seconds=30.0,
    lookback_minutes=5,
    deduplication_window_minutes=60
)

# Custom Router configuration
router_config = EventRouterConfig(
    max_queue_size=1000,
    worker_count=3,
    retry_max_attempts=3,
    retry_initial_delay=1.0,
    retry_max_delay=30.0,
    dead_letter_queue_max_size=500
)

# Create pipeline with custom configs
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=collection_ids,
    websocket_config=websocket_config,
    polling_config=polling_config,
    router_config=router_config
)
```

## Error Handling

### Retry Logic

Events that fail processing are automatically retried:

- **Max attempts**: 3
- **Initial delay**: 1 second
- **Backoff multiplier**: 2.0x
- **Max delay**: 30 seconds

### Dead Letter Queue

Events that fail all retries are moved to the dead letter queue for investigation:

```python
# Get failed events
router_stats = manager.event_router.get_statistics()
dead_letter_count = router_stats['dead_letter_queue_size']

# Retrieve failed events
failed_events = await manager.event_router.get_dead_letter_events(limit=100)

# Clear dead letter queue
cleared_count = await manager.event_router.clear_dead_letter_queue()
```

### Backpressure

When the event queue reaches capacity, new events are rejected to prevent memory issues. Monitor queue size:

```python
router_stats = manager.event_router.get_statistics()
print(f"Queue: {router_stats['current_queue_size']}/{router_config.max_queue_size}")
```

## Production Deployment

### Recommended Settings

```python
# Production configuration
manager = await create_subscription_pipeline(
    repository=repository,
    collection_ids=collection_ids,
    orchestrator_url=os.getenv("ORCHESTRATOR_URL"),
    vision_service_url=os.getenv("VISION_SERVICE_URL"),
    enable_websocket=True,
    enable_polling=True,
    auto_failover=True,
    router_config=EventRouterConfig(
        max_queue_size=2000,  # Higher capacity
        worker_count=5,       # More workers
        retry_max_attempts=5  # More retries
    )
)
```

### Logging

Configure appropriate log levels:

```python
import logging

# Production: INFO level
logging.basicConfig(level=logging.INFO)

# Debug: DEBUG level for troubleshooting
logging.basicConfig(level=logging.DEBUG)
```

### Graceful Shutdown

```python
import signal

async def shutdown(manager):
    logger.info("Shutting down...")
    await manager.stop()
    logger.info("Shutdown complete")

# Handle SIGTERM/SIGINT
loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(
        sig,
        lambda: asyncio.create_task(shutdown(manager))
    )
```

## Troubleshooting

### WebSocket Connection Issues

1. Check Orchestrator service is running
2. Verify WebSocket endpoint URL
3. Check network connectivity
4. Review WebSocket subscriber logs

### Polling Not Working

1. Check Vision Service is running
2. Verify REST API endpoint
3. Check collection filter configuration
4. Review polling interval settings

### Events Not Processing

1. Check event router queue size
2. Review worker task status
3. Check dead letter queue for failed events
4. Verify BatchMonitor configuration

### High Memory Usage

1. Reduce event queue size
2. Reduce worker count
3. Increase processing speed
4. Check for event processing bottlenecks

## See Also

- [Event Subscription Integration Example](../examples/event_subscription_integration.py)
- [Batch Processing Pipeline Documentation](continuous-individuals-and-mvr-pipeline.md)
- [API Documentation](../api/)
