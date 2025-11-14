"""
Event Subscriber Base Classes
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Abstract base classes for event subscription implementations.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable, Dict, Any

from ..models.events import (
    SubscriptionStatus,
    SubscriptionState,
    EventType,
    FaceDetectionCompletedEvent
)


logger = logging.getLogger(__name__)


class EventSubscriber(ABC):
    """
    Abstract base class for event subscribers.
    
    Defines the interface for all event subscription implementations
    (WebSocket, Polling, etc.).
    """
    
    def __init__(
        self,
        subscriber_type: str,
        on_event: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        """
        Initialize event subscriber.
        
        Args:
            subscriber_type: Type identifier ("websocket" or "polling")
            on_event: Async callback for event handling
        """
        self.subscriber_type = subscriber_type
        self.on_event = on_event
        
        # Connection state
        self.state = SubscriptionState(subscriber_type=subscriber_type)
        
        # Control flags
        self._running = False
        self._stop_requested = False
        
        # Background tasks
        self._main_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(f"[{self.subscriber_type.upper()}] Subscriber initialized")
    
    # =============================================
    # ABSTRACT METHODS (must be implemented)
    # =============================================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to event source.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from event source."""
        pass
    
    @abstractmethod
    async def _run_subscription(self) -> None:
        """
        Main subscription loop.
        
        This method should:
        1. Receive events from source
        2. Parse events
        3. Call on_event callback
        4. Handle errors and reconnection
        """
        pass
    
    # =============================================
    # LIFECYCLE MANAGEMENT
    # =============================================
    
    async def start(self) -> None:
        """Start event subscription."""
        if self._running:
            logger.warning(
                f"[{self.subscriber_type.upper()}] "
                f"Subscriber already running"
            )
            return
        
        logger.info(f"[{self.subscriber_type.upper()}] Starting subscriber...")
        
        self._running = True
        self._stop_requested = False
        
        # Update state
        self.state.status = SubscriptionStatus.CONNECTING
        
        # Start main subscription task
        self._main_task = asyncio.create_task(self._run_subscription())
        
        logger.info(f"[{self.subscriber_type.upper()}] Subscriber started")
    
    async def stop(self) -> None:
        """Stop event subscription gracefully."""
        if not self._running:
            logger.warning(
                f"[{self.subscriber_type.upper()}] "
                f"Subscriber not running"
            )
            return
        
        logger.info(f"[{self.subscriber_type.upper()}] Stopping subscriber...")
        
        self._stop_requested = True
        self._running = False
        
        # Cancel all background tasks
        await self._cancel_task(self._main_task, "main")
        await self._cancel_task(self._reconnect_task, "reconnect")
        await self._cancel_task(self._heartbeat_task, "heartbeat")
        
        # Disconnect
        await self.disconnect()
        
        # Update state
        self.state.status = SubscriptionStatus.STOPPED
        self.state.disconnected_at = datetime.utcnow()
        
        logger.info(f"[{self.subscriber_type.upper()}] Subscriber stopped")
    
    async def _cancel_task(
        self,
        task: Optional[asyncio.Task],
        task_name: str
    ) -> None:
        """Cancel a background task."""
        if task and not task.done():
            logger.debug(
                f"[{self.subscriber_type.upper()}] "
                f"Cancelling {task_name} task..."
            )
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(
                    f"[{self.subscriber_type.upper()}] "
                    f"{task_name.capitalize()} task cancelled"
                )
    
    # =============================================
    # STATE MANAGEMENT
    # =============================================
    
    def update_state(
        self,
        status: Optional[SubscriptionStatus] = None,
        **kwargs
    ) -> None:
        """
        Update subscription state.
        
        Args:
            status: New subscription status
            **kwargs: Additional state fields to update
        """
        if status:
            self.state.status = status
        
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def increment_event_counter(
        self,
        counter: str,
        amount: int = 1
    ) -> None:
        """
        Increment event counter.
        
        Args:
            counter: Counter name (events_received, events_processed, etc.)
            amount: Increment amount
        """
        if hasattr(self.state, counter):
            current = getattr(self.state, counter)
            setattr(self.state, counter, current + amount)
    
    def record_error(self, error: Exception) -> None:
        """
        Record error in state.
        
        Args:
            error: Exception that occurred
        """
        self.state.last_error = str(error)
        self.state.last_error_at = datetime.utcnow()
        logger.error(
            f"[{self.subscriber_type.upper()}] Error: {error}",
            exc_info=True
        )
    
    # =============================================
    # EVENT HANDLING
    # =============================================
    
    async def handle_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle received event.
        
        Args:
            event_data: Raw event data
        """
        try:
            # Update statistics
            self.increment_event_counter('events_received')
            self.state.last_event_at = datetime.utcnow()
            
            # Call event callback if provided
            if self.on_event:
                await self.on_event(event_data)
                self.increment_event_counter('events_processed')
            else:
                logger.warning(
                    f"[{self.subscriber_type.upper()}] "
                    f"No event handler configured"
                )
        
        except Exception as e:
            self.increment_event_counter('events_failed')
            self.record_error(e)
            logger.error(
                f"[{self.subscriber_type.upper()}] "
                f"Failed to handle event: {e}",
                exc_info=True
            )
    
    # =============================================
    # RECONNECTION LOGIC
    # =============================================
    
    async def schedule_reconnect(
        self,
        initial_delay: int = 5,
        max_delay: int = 60,
        backoff_multiplier: float = 2.0
    ) -> None:
        """
        Schedule reconnection with exponential backoff.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_multiplier: Backoff multiplier
        """
        # Calculate delay with exponential backoff
        delay = min(
            initial_delay * (backoff_multiplier ** self.state.reconnect_attempts),
            max_delay
        )
        
        self.state.next_reconnect_at = (
            datetime.utcnow() + timedelta(seconds=delay)
        )
        
        logger.info(
            f"[{self.subscriber_type.upper()}] "
            f"Reconnecting in {delay:.1f} seconds "
            f"(attempt {self.state.reconnect_attempts + 1})..."
        )
        
        # Wait for delay
        await asyncio.sleep(delay)
        
        # Attempt reconnection
        self.state.reconnect_attempts += 1
        success = await self.connect()
        
        if success:
            # Reset reconnect counter on success
            self.state.reconnect_attempts = 0
            self.state.next_reconnect_at = None
            logger.info(
                f"[{self.subscriber_type.upper()}] "
                f"Reconnection successful"
            )
        else:
            # Schedule another reconnect
            if not self._stop_requested:
                await self.schedule_reconnect(
                    initial_delay,
                    max_delay,
                    backoff_multiplier
                )
    
    # =============================================
    # HEALTH CHECK
    # =============================================
    
    def is_healthy(self) -> bool:
        """
        Check if subscriber is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        # Connected status
        if self.state.status != SubscriptionStatus.CONNECTED:
            return False
        
        # Recent events (within last 5 minutes)
        if self.state.last_event_at:
            time_since_event = (
                datetime.utcnow() - self.state.last_event_at
            ).total_seconds()
            if time_since_event > 300:  # 5 minutes
                logger.warning(
                    f"[{self.subscriber_type.upper()}] "
                    f"No events received in {time_since_event:.0f} seconds"
                )
                return False
        
        return True
    
    def get_state(self) -> SubscriptionState:
        """
        Get current subscription state.
        
        Returns:
            Current state snapshot
        """
        return self.state.model_copy(deep=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get subscription statistics.
        
        Returns:
            Statistics dictionary
        """
        uptime = None
        if self.state.connected_at:
            uptime = (
                datetime.utcnow() - self.state.connected_at
            ).total_seconds()
        
        time_since_event = None
        if self.state.last_event_at:
            time_since_event = (
                datetime.utcnow() - self.state.last_event_at
            ).total_seconds()
        
        return {
            'subscriber_type': self.subscriber_type,
            'status': self.state.status.value,
            'events_received': self.state.events_received,
            'events_processed': self.state.events_processed,
            'events_failed': self.state.events_failed,
            'uptime_seconds': uptime,
            'time_since_last_event_seconds': time_since_event,
            'reconnect_attempts': self.state.reconnect_attempts,
            'is_healthy': self.is_healthy()
        }
