"""
Event Models and Types
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Models for event subscription, WebSocket events, and event handling.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, validator


# =============================================
# EVENT TYPE ENUMS
# =============================================

class EventType(str, Enum):
    """Event types for batch processing."""
    
    FACE_DETECTION_COMPLETED = "face_detection_completed"
    VIDEO_COMPLETED = "video_completed"
    RECORDING_STOPPED = "recording_stopped"
    BATCH_TRIGGERED = "batch_triggered"
    BATCH_COMPLETED = "batch_completed"
    BATCH_FAILED = "batch_failed"


class EventSource(str, Enum):
    """Source system for events."""
    
    ORCHESTRATOR = "orchestrator"
    VISION = "vision"
    CAMERA = "camera"
    MEDIA = "media"
    VMETA = "vmeta"


class SubscriptionStatus(str, Enum):
    """Status of event subscription."""
    
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    STOPPED = "stopped"


# =============================================
# EVENT PAYLOAD MODELS
# =============================================

class FaceDetectionCompletedEvent(BaseModel):
    """
    Event payload for face detection completion.
    Published by Orchestrator when face detection finishes.
    """
    
    # Session identification
    session_uuid: UUID = Field(description="Face detection session UUID")
    session_type: str = Field(description="Session type (e.g., 'batch_mode')")
    
    # Video reference
    video_uuid: UUID = Field(description="Video that was processed")
    collection_id: str = Field(description="Collection identifier")
    
    # Session metadata
    video_start_time: datetime = Field(description="Video start timestamp")
    video_end_time: datetime = Field(description="Video end timestamp")
    
    # Results summary
    faces_detected: int = Field(ge=0, description="Number of faces detected")
    individuals_created: int = Field(ge=0, description="Individuals created")
    individuals_cached: int = Field(ge=0, description="Individuals from cache")
    
    # Processing metadata
    processing_started_at: datetime = Field(description="When processing started")
    processing_completed_at: datetime = Field(description="When processing completed")
    processing_time_seconds: float = Field(ge=0, description="Processing duration")
    
    # Cache performance
    cache_hit_rate: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Cache hit rate percentage"
    )
    
    # Completion metadata
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('video_end_time')
    def end_after_start(cls, v, values):
        """Ensure video end is after start."""
        if 'video_start_time' in values and v <= values['video_start_time']:
            raise ValueError('video_end_time must be after video_start_time')
        return v
    
    class Config:
        from_attributes = True


class WebSocketEvent(BaseModel):
    """
    Generic WebSocket event wrapper.
    Used for all events received via WebSocket connection.
    """
    
    # Event metadata
    event_id: str = Field(description="Unique event identifier")
    event_type: str = Field(description="Type of event")
    event_source: str = Field(description="Source system")
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event payload (flexible structure)
    payload: Dict[str, Any] = Field(description="Event data")
    
    # Routing metadata
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for request tracing"
    )
    
    class Config:
        from_attributes = True


# =============================================
# SUBSCRIPTION MODELS
# =============================================

class SubscriptionConfig(BaseModel):
    """Configuration for event subscription."""
    
    # Connection settings
    orchestrator_url: str = Field(
        "http://localhost:8002",
        description="Orchestrator service base URL"
    )
    event_endpoint: str = Field(
        "/api/v1/events/subscribe",
        description="WebSocket subscription endpoint"
    )
    
    # Subscription filters
    event_types: List[EventType] = Field(
        default_factory=lambda: [EventType.FACE_DETECTION_COMPLETED],
        description="Event types to subscribe to"
    )
    collections: Optional[List[str]] = Field(
        None,
        description="Filter by collection IDs (None = all)"
    )
    
    # Connection management
    reconnect_enabled: bool = Field(True, description="Auto-reconnect on disconnect")
    reconnect_interval_seconds: int = Field(
        5,
        ge=1,
        description="Initial reconnect interval"
    )
    max_reconnect_interval_seconds: int = Field(
        60,
        ge=1,
        description="Maximum reconnect interval"
    )
    reconnect_backoff_multiplier: float = Field(
        2.0,
        ge=1.0,
        description="Backoff multiplier for reconnect attempts"
    )
    
    # Heartbeat settings
    heartbeat_enabled: bool = Field(True, description="Send heartbeat pings")
    heartbeat_interval_seconds: int = Field(
        30,
        ge=5,
        description="Heartbeat ping interval"
    )
    heartbeat_timeout_seconds: int = Field(
        10,
        ge=1,
        description="Heartbeat response timeout"
    )
    
    # Buffer settings
    event_queue_max_size: int = Field(
        1000,
        ge=10,
        description="Maximum events in queue"
    )
    
    class Config:
        from_attributes = True


class PollingConfig(BaseModel):
    """Configuration for polling-based event subscription."""
    
    # Vision Service settings
    vision_service_url: str = Field(
        "http://localhost:8003",
        description="Vision service base URL"
    )
    sessions_endpoint: str = Field(
        "/api/v1/sessions",
        description="Sessions query endpoint"
    )
    
    # Polling settings
    polling_enabled: bool = Field(True, description="Enable polling fallback")
    polling_interval_seconds: int = Field(
        30,
        ge=5,
        description="Polling interval"
    )
    lookback_minutes: int = Field(
        5,
        ge=1,
        description="How far back to look for completed sessions"
    )
    
    # Deduplication
    deduplication_enabled: bool = Field(
        True,
        description="Prevent duplicate event processing"
    )
    deduplication_window_minutes: int = Field(
        60,
        ge=5,
        description="Time window for deduplication cache"
    )
    
    class Config:
        from_attributes = True


class SubscriptionState(BaseModel):
    """Current state of event subscription."""
    
    # Connection status
    status: SubscriptionStatus = Field(
        SubscriptionStatus.DISCONNECTED,
        description="Current subscription status"
    )
    subscriber_type: Literal["websocket", "polling"] = Field(
        description="Type of subscriber"
    )
    
    # Connection metadata
    connected_at: Optional[datetime] = Field(
        None,
        description="When connection was established"
    )
    disconnected_at: Optional[datetime] = Field(
        None,
        description="When connection was lost"
    )
    last_event_at: Optional[datetime] = Field(
        None,
        description="When last event was received"
    )
    
    # Reconnection tracking
    reconnect_attempts: int = Field(0, ge=0, description="Reconnection attempts")
    next_reconnect_at: Optional[datetime] = Field(
        None,
        description="Next reconnection attempt time"
    )
    
    # Statistics
    events_received: int = Field(0, ge=0, description="Total events received")
    events_processed: int = Field(0, ge=0, description="Total events processed")
    events_failed: int = Field(0, ge=0, description="Total events failed")
    
    # Health
    last_heartbeat_at: Optional[datetime] = Field(
        None,
        description="Last heartbeat sent"
    )
    last_heartbeat_response_at: Optional[datetime] = Field(
        None,
        description="Last heartbeat response received"
    )
    
    # Error tracking
    last_error: Optional[str] = Field(None, description="Last error message")
    last_error_at: Optional[datetime] = Field(None, description="Last error time")
    
    class Config:
        from_attributes = True


# =============================================
# EVENT ROUTING MODELS
# =============================================

class EventRouterConfig(BaseModel):
    """Configuration for event routing."""
    
    # Queue settings
    max_queue_size: int = Field(
        1000,
        ge=10,
        description="Maximum events in router queue"
    )
    worker_count: int = Field(
        3,
        ge=1,
        le=10,
        description="Number of event processing workers"
    )
    
    # Processing settings
    batch_event_timeout_seconds: int = Field(
        30,
        ge=1,
        description="Timeout for batch event processing"
    )
    
    # Error handling  
    retry_max_attempts: int = Field(3, ge=0, description="Max retries per event")
    retry_initial_delay: float = Field(
        1.0,
        ge=0.1,
        description="Initial retry delay in seconds"
    )
    retry_max_delay: float = Field(
        30.0,
        ge=1.0,
        description="Maximum retry delay in seconds"
    )
    retry_backoff_multiplier: float = Field(
        2.0,
        ge=1.0,
        description="Backoff multiplier for retries"
    )
    
    # Dead letter queue
    dead_letter_enabled: bool = Field(
        True,
        description="Enable dead letter queue for failed events"
    )
    dead_letter_queue_max_size: int = Field(
        500,
        ge=10,
        description="Maximum events in dead letter queue"
    )
    
    class Config:
        from_attributes = True


class ProcessedEvent(BaseModel):
    """Record of processed event for deduplication."""
    
    event_id: str = Field(description="Event identifier")
    event_type: EventType = Field(description="Type of event")
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When event was processed"
    )
    
    # Event key for deduplication
    session_uuid: Optional[UUID] = Field(None, description="Session UUID")
    video_uuid: Optional[UUID] = Field(None, description="Video UUID")
    collection_id: Optional[str] = Field(None, description="Collection ID")
    
    # Processing result
    success: bool = Field(description="Whether processing succeeded")
    error_message: Optional[str] = Field(None, description="Error if failed")
    
    class Config:
        from_attributes = True


# =============================================
# HEALTH CHECK MODELS
# =============================================

class SubscriptionHealthCheck(BaseModel):
    """Health check response for event subscription."""
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="Overall health status"
    )
    
    # Subscriber states
    websocket_status: SubscriptionStatus = Field(
        description="WebSocket subscriber status"
    )
    polling_status: SubscriptionStatus = Field(
        description="Polling subscriber status"
    )
    
    # Active subscriber
    active_subscriber: Literal["websocket", "polling", "none"] = Field(
        description="Currently active subscriber"
    )
    
    # Event statistics
    total_events_received: int = Field(ge=0, description="Total events received")
    total_events_processed: int = Field(ge=0, description="Total events processed")
    total_events_failed: int = Field(ge=0, description="Total events failed")
    
    # Queue status
    event_queue_size: int = Field(ge=0, description="Events in queue")
    event_queue_max_size: int = Field(ge=0, description="Queue capacity")
    
    # Recent activity
    last_event_received_at: Optional[datetime] = Field(
        None,
        description="Last event received"
    )
    seconds_since_last_event: Optional[float] = Field(
        None,
        ge=0,
        description="Seconds since last event"
    )
    
    # Connection info
    connected_since: Optional[datetime] = Field(
        None,
        description="Connection established time"
    )
    uptime_seconds: Optional[float] = Field(
        None,
        ge=0,
        description="Connection uptime"
    )
    
    class Config:
        from_attributes = True
