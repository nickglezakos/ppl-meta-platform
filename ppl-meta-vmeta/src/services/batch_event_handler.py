"""
Batch Event Handler
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Event handler for subscribing to face detection completion and recording
stop events, routing them to the batch monitor for processing.

This module acts as the bridge between the event system and batch monitoring,
handling event deserialization, validation, and routing.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime
from uuid import UUID

from ..models.batch_processing import (
    VideoCompletionEvent,
    RecordingStopEvent,
    BatchTriggerResponse
)
from ..models.events import EventType
from .batch_monitor import BatchMonitor

logger = logging.getLogger(__name__)


class BatchEventHandler:
    """
    Event handler for batch processing events.
    
    Subscribes to:
    - Face detection completion events
    - Recording stop events
    
    Routes events to BatchMonitor for processing.
    """
    
    def __init__(
        self,
        batch_monitor: BatchMonitor,
        enable_video_completion: bool = True,
        enable_recording_stop: bool = True
    ):
        """
        Initialize event handler.
        
        Args:
            batch_monitor: Batch monitor service
            enable_video_completion: Enable video completion event handling
            enable_recording_stop: Enable recording stop event handling
        """
        self.batch_monitor = batch_monitor
        self.enable_video_completion = enable_video_completion
        self.enable_recording_stop = enable_recording_stop
        
        # Event subscriptions (populated by register_subscriptions)
        self._subscriptions = []
        
        # Statistics
        self._stats = {
            'video_completion_events': 0,
            'recording_stop_events': 0,
            'events_failed': 0,
            'batches_triggered': 0
        }
        
        logger.info(
            "BatchEventHandler initialized "
            f"(video_completion: {enable_video_completion}, "
            f"recording_stop: {enable_recording_stop})"
        )
    
    async def handle_event(self, event_data: Dict[str, Any]) -> None:
        """
        Generic event handler that routes events based on type.
        
        Used by EventRouter to dispatch events.
        
        Args:
            event_data: Raw event data dictionary with 'event_type' field
        """
        event_type = event_data.get("event_type")
        
        if not event_type:
            logger.warning("Event missing event_type field")
            self._stats['events_failed'] += 1
            return
        
        # Route based on event type
        if event_type == EventType.FACE_DETECTION_COMPLETED:
            await self.handle_video_completion_event(event_data)
        elif event_type == EventType.RECORDING_STOPPED:
            await self.handle_recording_stop_event(event_data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            self._stats['events_failed'] += 1
    
    async def handle_video_completion_event(
        self,
        event_data: Dict[str, Any]
    ) -> Optional[BatchTriggerResponse]:
        """
        Handle video completion event.
        
        Args:
            event_data: Raw event data dictionary
            
        Returns:
            BatchTriggerResponse if batch was triggered, None otherwise
        """
        if not self.enable_video_completion:
            logger.debug("Video completion events disabled")
            return None
        
        try:
            # Parse event data
            event = self._parse_video_completion_event(event_data)
            
            if not event:
                logger.warning("Failed to parse video completion event")
                self._stats['events_failed'] += 1
                return None
            
            logger.debug(
                f"Received video completion: {event.video_uuid} "
                f"for collection {event.collection_id}"
            )
            
            # Route to batch monitor
            response = await self.batch_monitor.handle_video_completion(event)
            
            self._stats['video_completion_events'] += 1
            
            if response:
                self._stats['batches_triggered'] += 1
                logger.info(
                    f"Batch {response.batch_uuid} triggered "
                    f"(reason: {response.trigger_reason.value})"
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle video completion event: {e}")
            self._stats['events_failed'] += 1
            return None
    
    async def handle_recording_stop_event(
        self,
        event_data: Dict[str, Any]
    ) -> Optional[BatchTriggerResponse]:
        """
        Handle recording stop event.
        
        Args:
            event_data: Raw event data dictionary
            
        Returns:
            BatchTriggerResponse if batch was triggered, None otherwise
        """
        if not self.enable_recording_stop:
            logger.debug("Recording stop events disabled")
            return None
        
        try:
            # Parse event data
            event = self._parse_recording_stop_event(event_data)
            
            if not event:
                logger.warning("Failed to parse recording stop event")
                self._stats['events_failed'] += 1
                return None
            
            logger.debug(
                f"Received recording stop for collection {event.collection_id}"
            )
            
            # Route to batch monitor
            response = await self.batch_monitor.handle_recording_stop(event)
            
            self._stats['recording_stop_events'] += 1
            
            if response:
                self._stats['batches_triggered'] += 1
                logger.info(
                    f"Batch {response.batch_uuid} triggered "
                    f"by recording stop"
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle recording stop event: {e}")
            self._stats['events_failed'] += 1
            return None
    
    def _parse_video_completion_event(
        self,
        event_data: Dict[str, Any]
    ) -> Optional[VideoCompletionEvent]:
        """
        Parse raw event data into VideoCompletionEvent.
        
        Args:
            event_data: Raw event dictionary
            
        Returns:
            VideoCompletionEvent or None if parsing fails
        """
        try:
            # Handle different event formats
            # Format 1: Direct event data
            if 'video_uuid' in event_data:
                return VideoCompletionEvent(
                    video_uuid=UUID(str(event_data['video_uuid'])),
                    collection_id=event_data['collection_id'],
                    video_start_time=self._parse_datetime(
                        event_data['video_start_time']
                    ),
                    video_end_time=self._parse_datetime(
                        event_data['video_end_time']
                    ),
                    face_detection_session_uuid=self._parse_uuid(
                        event_data.get('face_detection_session_uuid')
                    )
                )
            
            # Format 2: Nested event payload
            if 'payload' in event_data:
                payload = event_data['payload']
                return VideoCompletionEvent(
                    video_uuid=UUID(str(payload['video_uuid'])),
                    collection_id=payload['collection_id'],
                    video_start_time=self._parse_datetime(
                        payload['video_start_time']
                    ),
                    video_end_time=self._parse_datetime(
                        payload['video_end_time']
                    ),
                    face_detection_session_uuid=self._parse_uuid(
                        payload.get('face_detection_session_uuid')
                    )
                )
            
            # Format 3: Event with data field
            if 'data' in event_data:
                data = event_data['data']
                return VideoCompletionEvent(
                    video_uuid=UUID(str(data['video_uuid'])),
                    collection_id=data['collection_id'],
                    video_start_time=self._parse_datetime(
                        data['video_start_time']
                    ),
                    video_end_time=self._parse_datetime(
                        data['video_end_time']
                    ),
                    face_detection_session_uuid=self._parse_uuid(
                        data.get('face_detection_session_uuid')
                    )
                )
            
            logger.warning(f"Unknown event format: {list(event_data.keys())}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse video completion event: {e}")
            return None
    
    def _parse_recording_stop_event(
        self,
        event_data: Dict[str, Any]
    ) -> Optional[RecordingStopEvent]:
        """
        Parse raw event data into RecordingStopEvent.
        
        Args:
            event_data: Raw event dictionary
            
        Returns:
            RecordingStopEvent or None if parsing fails
        """
        try:
            # Handle different event formats
            if 'collection_id' in event_data:
                return RecordingStopEvent(
                    collection_id=event_data['collection_id'],
                    stopped_at=self._parse_datetime(
                        event_data.get('stopped_at', datetime.utcnow())
                    ),
                    reason=event_data.get('reason')
                )
            
            if 'payload' in event_data:
                payload = event_data['payload']
                return RecordingStopEvent(
                    collection_id=payload['collection_id'],
                    stopped_at=self._parse_datetime(
                        payload.get('stopped_at', datetime.utcnow())
                    ),
                    reason=payload.get('reason')
                )
            
            if 'data' in event_data:
                data = event_data['data']
                return RecordingStopEvent(
                    collection_id=data['collection_id'],
                    stopped_at=self._parse_datetime(
                        data.get('stopped_at', datetime.utcnow())
                    ),
                    reason=data.get('reason')
                )
            
            logger.warning(f"Unknown event format: {list(event_data.keys())}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse recording stop event: {e}")
            return None
    
    def _parse_datetime(self, value: Any) -> datetime:
        """
        Parse datetime from various formats.
        
        Args:
            value: Datetime value (str, datetime, int timestamp)
            
        Returns:
            Parsed datetime
        """
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                pass
            
            # Try timestamp
            try:
                return datetime.fromtimestamp(float(value))
            except:
                pass
        
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        
        # Default to now
        return datetime.utcnow()
    
    def _parse_uuid(self, value: Any) -> Optional[UUID]:
        """
        Parse UUID from various formats.
        
        Args:
            value: UUID value (str, UUID, None)
            
        Returns:
            Parsed UUID or None
        """
        if value is None:
            return None
        
        if isinstance(value, UUID):
            return value
        
        try:
            return UUID(str(value))
        except:
            return None
    
    def register_subscriptions(
        self,
        event_bus: Any  # Type depends on event system implementation
    ):
        """
        Register event subscriptions with event bus.
        
        Args:
            event_bus: Event bus to subscribe to
        """
        # Video completion events
        if self.enable_video_completion:
            subscription = event_bus.subscribe(
                event_type='face_detection.completed',
                handler=self.handle_video_completion_event
            )
            self._subscriptions.append(subscription)
            logger.info("Subscribed to face_detection.completed events")
        
        # Recording stop events
        if self.enable_recording_stop:
            subscription = event_bus.subscribe(
                event_type='camera.recording_stopped',
                handler=self.handle_recording_stop_event
            )
            self._subscriptions.append(subscription)
            logger.info("Subscribed to camera.recording_stopped events")
    
    def unregister_subscriptions(self):
        """Unregister all event subscriptions."""
        for subscription in self._subscriptions:
            try:
                subscription.unsubscribe()
            except Exception as e:
                logger.warning(f"Failed to unsubscribe: {e}")
        
        self._subscriptions.clear()
        logger.info("Unregistered all event subscriptions")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get event handling statistics.
        
        Returns:
            Statistics dictionary
        """
        return self._stats.copy()
    
    async def test_video_completion(
        self,
        video_uuid: UUID,
        collection_id: str,
        video_start_time: Optional[datetime] = None,
        video_end_time: Optional[datetime] = None
    ) -> Optional[BatchTriggerResponse]:
        """
        Test video completion event handling.
        
        Helper method for testing without actual events.
        
        Args:
            video_uuid: Video identifier
            collection_id: Collection identifier
            video_start_time: Video start time (defaults to 1 hour ago)
            video_end_time: Video end time (defaults to now)
            
        Returns:
            BatchTriggerResponse if batch triggered
        """
        if not video_start_time:
            video_start_time = datetime.utcnow() - timedelta(hours=1)
        
        if not video_end_time:
            video_end_time = datetime.utcnow()
        
        event = VideoCompletionEvent(
            video_uuid=video_uuid,
            collection_id=collection_id,
            video_start_time=video_start_time,
            video_end_time=video_end_time
        )
        
        return await self.batch_monitor.handle_video_completion(event)
    
    async def test_recording_stop(
        self,
        collection_id: str,
        reason: Optional[str] = None
    ) -> Optional[BatchTriggerResponse]:
        """
        Test recording stop event handling.
        
        Helper method for testing without actual events.
        
        Args:
            collection_id: Collection identifier
            reason: Stop reason
            
        Returns:
            BatchTriggerResponse if batch triggered
        """
        event = RecordingStopEvent(
            collection_id=collection_id,
            stopped_at=datetime.utcnow(),
            reason=reason or "Test stop"
        )
        
        return await self.batch_monitor.handle_recording_stop(event)


# Import at end to avoid circular dependency
from datetime import timedelta
