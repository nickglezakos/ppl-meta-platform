"""
Batch Processing Prometheus Metrics

Metrics collection for continuous individuals and MVR pipeline monitoring.

Author: PPL Meta Platform
Date: November 13, 2025
Version: 1.0.0
"""

import logging
from typing import Dict, Optional
from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)


# ============================================================================
# Batch Processing Metrics
# ============================================================================

# Counter: Total batches processed
batch_processing_total = Counter(
    'batch_processing_total',
    'Total number of batches processed',
    ['collection_id', 'status', 'is_partial', 'trigger_reason']
)

# Gauge: Current batch size (videos in accumulating batch)
batch_current_size = Gauge(
    'batch_current_size',
    'Current number of videos in accumulating batch',
    ['collection_id']
)

# Histogram: Batch processing duration
batch_processing_duration_seconds = Histogram(
    'batch_processing_duration_seconds',
    'Time to process batch (seconds)',
    ['collection_id', 'is_partial'],
    buckets=[10, 30, 60, 120, 300, 600]  # 10s to 10min
)

# Counter: Individuals created
individuals_created_total = Counter(
    'individuals_created_total',
    'Total individuals created',
    ['collection_id', 'source']  # source: new, cached
)

# Counter: MVR people created
mvr_people_created_total = Counter(
    'mvr_people_created_total',
    'Total MVR people created',
    ['collection_id', 'source']  # source: new, cached
)

# Gauge: Cache hit rate (percentage)
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Percentage of cache hits',
    ['collection_id', 'cache_level']  # level: individual, mvr
)

# Counter: Partial batches triggered
partial_batches_total = Counter(
    'partial_batches_total',
    'Total partial batches triggered',
    ['collection_id', 'trigger_reason']  # recording_stopped, timeout_reached
)

# Gauge: Incomplete batches waiting
incomplete_batches_waiting = Gauge(
    'incomplete_batches_waiting',
    'Number of batches waiting for more videos',
    ['collection_id']
)

# Gauge: Active timeout tasks
timeout_tasks_active = Gauge(
    'timeout_tasks_active',
    'Number of active timeout monitoring tasks',
    ['collection_id']
)

# Histogram: Partial batch size distribution
partial_batch_size = Histogram(
    'partial_batch_size',
    'Distribution of partial batch sizes',
    ['collection_id'],
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
)

# Counter: Batch failures
batch_failures_total = Counter(
    'batch_failures_total',
    'Total batch processing failures',
    ['collection_id', 'error_type']
)

# Histogram: Batch trigger latency (time from last video to trigger)
batch_trigger_latency_seconds = Histogram(
    'batch_trigger_latency_seconds',
    'Time from last video added to batch trigger (seconds)',
    ['collection_id', 'trigger_reason'],
    buckets=[0.1, 0.5, 1, 5, 10, 60, 600]  # 100ms to 10min
)

# Gauge: Worker pool status
worker_pool_active = Gauge(
    'worker_pool_active',
    'Number of active workers processing batches'
)

worker_pool_idle = Gauge(
    'worker_pool_idle',
    'Number of idle workers available'
)

worker_pool_queue_size = Gauge(
    'worker_pool_queue_size',
    'Number of batches waiting in queue'
)


# ============================================================================
# Camera Event Integration Metrics
# ============================================================================

# Counter: Camera events received
camera_events_received_total = Counter(
    'camera_events_received_total',
    'Total camera events received',
    ['event_type', 'transport']  # transport: websocket, polling
)

# Counter: Camera events processed
camera_events_processed_total = Counter(
    'camera_events_processed_total',
    'Total camera events processed successfully',
    ['event_type']
)

# Counter: Camera events failed
camera_events_failed_total = Counter(
    'camera_events_failed_total',
    'Total camera events that failed processing',
    ['event_type', 'error_type']
)

# Gauge: WebSocket connection status
camera_websocket_connected = Gauge(
    'camera_websocket_connected',
    'Camera event WebSocket connection status (1=connected, 0=disconnected)'
)

# Counter: WebSocket reconnections
camera_websocket_reconnections_total = Counter(
    'camera_websocket_reconnections_total',
    'Total WebSocket reconnection attempts'
)

# Histogram: Event processing latency
camera_event_processing_latency_seconds = Histogram(
    'camera_event_processing_latency_seconds',
    'Time to process camera event (seconds)',
    ['event_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]  # 1ms to 1s
)


# ============================================================================
# Vision Service Integration Metrics
# ============================================================================

# Counter: Vision events received
vision_events_received_total = Counter(
    'vision_events_received_total',
    'Total vision service events received',
    ['event_type']
)

# Counter: Vision events processed
vision_events_processed_total = Counter(
    'vision_events_processed_total',
    'Total vision service events processed',
    ['event_type']
)


# ============================================================================
# Pipeline Execution Metrics
# ============================================================================

# Histogram: Individual creation time
individual_creation_duration_seconds = Histogram(
    'individual_creation_duration_seconds',
    'Time to create individual via Orchestrator (seconds)',
    ['collection_id', 'cached'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# Histogram: MVR creation time
mvr_creation_duration_seconds = Histogram(
    'mvr_creation_duration_seconds',
    'Time to create MVR person (seconds)',
    ['collection_id', 'cached'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

# Histogram: Merge operation time
merge_operation_duration_seconds = Histogram(
    'merge_operation_duration_seconds',
    'Time to run merge algorithm (seconds)',
    ['collection_id'],
    buckets=[1, 5, 10, 30, 60, 120]
)

# Counter: Cache operations
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_level', 'result']  
    # operation: get, set, hit, miss
    # cache_level: individual, mvr
    # result: success, failure
)


# ============================================================================
# Database Metrics
# ============================================================================

# Histogram: Database query duration
database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query execution time (seconds)',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]
)

# Counter: Database operations
database_operations_total = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'table', 'status']
)


# ============================================================================
# Service Info
# ============================================================================

service_info = Info(
    'batch_processing_service',
    'Batch processing service information'
)

# Set service info
service_info.info({
    'version': '1.0.0',
    'service': 'vmeta',
    'component': 'batch_processing',
    'description': 'Continuous individuals and MVR pipeline'
})


# ============================================================================
# Metrics Helper Functions
# ============================================================================

def record_batch_started(
    collection_id: str,
    video_count: int,
    is_partial: bool,
    trigger_reason: str
):
    """Record batch processing start."""
    batch_processing_total.labels(
        collection_id=collection_id,
        status='started',
        is_partial=str(is_partial),
        trigger_reason=trigger_reason
    ).inc()
    
    if is_partial:
        partial_batches_total.labels(
            collection_id=collection_id,
            trigger_reason=trigger_reason
        ).inc()
        
        partial_batch_size.labels(
            collection_id=collection_id
        ).observe(video_count)


def record_batch_completed(
    collection_id: str,
    video_count: int,
    is_partial: bool,
    trigger_reason: str,
    duration_seconds: float,
    individuals_created: int,
    individuals_cached: int,
    mvr_created: int,
    mvr_cached: int
):
    """Record batch processing completion."""
    batch_processing_total.labels(
        collection_id=collection_id,
        status='completed',
        is_partial=str(is_partial),
        trigger_reason=trigger_reason
    ).inc()
    
    batch_processing_duration_seconds.labels(
        collection_id=collection_id,
        is_partial=str(is_partial)
    ).observe(duration_seconds)
    
    # Record individuals
    if individuals_created > 0:
        individuals_created_total.labels(
            collection_id=collection_id,
            source='new'
        ).inc(individuals_created)
    
    if individuals_cached > 0:
        individuals_created_total.labels(
            collection_id=collection_id,
            source='cached'
        ).inc(individuals_cached)
    
    # Record MVR people
    if mvr_created > 0:
        mvr_people_created_total.labels(
            collection_id=collection_id,
            source='new'
        ).inc(mvr_created)
    
    if mvr_cached > 0:
        mvr_people_created_total.labels(
            collection_id=collection_id,
            source='cached'
        ).inc(mvr_cached)
    
    # Calculate cache hit rates
    total_individuals = individuals_created + individuals_cached
    if total_individuals > 0:
        individual_cache_rate = (individuals_cached / total_individuals) * 100
        cache_hit_rate.labels(
            collection_id=collection_id,
            cache_level='individual'
        ).set(individual_cache_rate)
    
    total_mvr = mvr_created + mvr_cached
    if total_mvr > 0:
        mvr_cache_rate = (mvr_cached / total_mvr) * 100
        cache_hit_rate.labels(
            collection_id=collection_id,
            cache_level='mvr'
        ).set(mvr_cache_rate)


def record_batch_failed(
    collection_id: str,
    is_partial: bool,
    trigger_reason: str,
    error_type: str
):
    """Record batch processing failure."""
    batch_processing_total.labels(
        collection_id=collection_id,
        status='failed',
        is_partial=str(is_partial),
        trigger_reason=trigger_reason
    ).inc()
    
    batch_failures_total.labels(
        collection_id=collection_id,
        error_type=error_type
    ).inc()


def update_batch_size(collection_id: str, video_count: int):
    """Update current batch size gauge."""
    batch_current_size.labels(
        collection_id=collection_id
    ).set(video_count)


def update_incomplete_batches(collection_id: str, count: int):
    """Update incomplete batches gauge."""
    incomplete_batches_waiting.labels(
        collection_id=collection_id
    ).set(count)


def update_timeout_tasks(collection_id: str, count: int):
    """Update active timeout tasks gauge."""
    timeout_tasks_active.labels(
        collection_id=collection_id
    ).set(count)


def update_worker_pool_status(
    active_workers: int,
    idle_workers: int,
    queue_size: int
):
    """Update worker pool status gauges."""
    worker_pool_active.set(active_workers)
    worker_pool_idle.set(idle_workers)
    worker_pool_queue_size.set(queue_size)


def record_camera_event_received(event_type: str, transport: str):
    """Record camera event received."""
    camera_events_received_total.labels(
        event_type=event_type,
        transport=transport
    ).inc()


def record_camera_event_processed(event_type: str, duration_seconds: float):
    """Record camera event processed."""
    camera_events_processed_total.labels(
        event_type=event_type
    ).inc()
    
    camera_event_processing_latency_seconds.labels(
        event_type=event_type
    ).observe(duration_seconds)


def record_camera_event_failed(event_type: str, error_type: str):
    """Record camera event failed."""
    camera_events_failed_total.labels(
        event_type=event_type,
        error_type=error_type
    ).inc()


def update_websocket_status(connected: bool):
    """Update WebSocket connection status."""
    camera_websocket_connected.set(1 if connected else 0)


def record_websocket_reconnection():
    """Record WebSocket reconnection attempt."""
    camera_websocket_reconnections_total.inc()


def record_vision_event_received(event_type: str):
    """Record vision service event received."""
    vision_events_received_total.labels(
        event_type=event_type
    ).inc()


def record_vision_event_processed(event_type: str):
    """Record vision service event processed."""
    vision_events_processed_total.labels(
        event_type=event_type
    ).inc()


def record_individual_creation(
    collection_id: str,
    cached: bool,
    duration_seconds: float
):
    """Record individual creation."""
    individual_creation_duration_seconds.labels(
        collection_id=collection_id,
        cached=str(cached)
    ).observe(duration_seconds)


def record_mvr_creation(
    collection_id: str,
    cached: bool,
    duration_seconds: float
):
    """Record MVR person creation."""
    mvr_creation_duration_seconds.labels(
        collection_id=collection_id,
        cached=str(cached)
    ).observe(duration_seconds)


def record_merge_operation(collection_id: str, duration_seconds: float):
    """Record merge operation."""
    merge_operation_duration_seconds.labels(
        collection_id=collection_id
    ).observe(duration_seconds)


def record_cache_operation(
    operation: str,
    cache_level: str,
    result: str
):
    """Record cache operation."""
    cache_operations_total.labels(
        operation=operation,
        cache_level=cache_level,
        result=result
    ).inc()


def record_database_query(
    operation: str,
    table: str,
    duration_seconds: float,
    status: str = 'success'
):
    """Record database query."""
    database_query_duration_seconds.labels(
        operation=operation,
        table=table
    ).observe(duration_seconds)
    
    database_operations_total.labels(
        operation=operation,
        table=table,
        status=status
    ).inc()


def record_batch_trigger_latency(
    collection_id: str,
    trigger_reason: str,
    latency_seconds: float
):
    """Record time from last video to batch trigger."""
    batch_trigger_latency_seconds.labels(
        collection_id=collection_id,
        trigger_reason=trigger_reason
    ).observe(latency_seconds)


# ============================================================================
# Metrics Export
# ============================================================================

def get_metrics_summary() -> Dict[str, any]:
    """
    Get summary of current metrics.
    
    Returns dict with key metrics for monitoring dashboard.
    """
    # This would aggregate metrics from Prometheus
    # For now, return placeholder
    return {
        "batch_processing": {
            "total_batches_24h": 0,
            "avg_processing_time_seconds": 0,
            "cache_hit_rate_percent": 0
        },
        "worker_pool": {
            "active": 0,
            "idle": 0,
            "queue_size": 0
        },
        "camera_events": {
            "events_received_24h": 0,
            "websocket_connected": False
        }
    }


logger.info("Batch processing metrics initialized")
