"""
Event Router and Dispatcher

This module implements the EventRouter which acts as the central hub for
routing events from subscribers to the appropriate handlers (BatchEventHandler).

The router provides:
- Asynchronous event queue with backpressure handling
- Worker pool for concurrent event processing
- Event filtering by type and collection
- Retry logic with exponential backoff
- Dead letter queue for failed events
- Comprehensive statistics and monitoring

Architecture:
    EventSubscriber → EventRouter → BatchEventHandler → BatchMonitor
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any, List
from uuid import UUID

from ..models.events import (
    EventRouterConfig,
    EventType,
    FaceDetectionCompletedEvent,
    WebSocketEvent
)


logger = logging.getLogger(__name__)


class EventRouter:
    """
    Routes events from subscribers to appropriate handlers.
    
    Manages:
    - Event queue with configurable size
    - Worker pool for concurrent processing
    - Event filtering and validation
    - Retry logic for failed events
    - Dead letter queue for permanently failed events
    - Statistics tracking
    """
    
    def __init__(
        self,
        config: EventRouterConfig,
        event_handler: Callable[[Dict[str, Any]], Any],
        collection_filter: Optional[List[UUID]] = None
    ):
        """
        Initialize event router.
        
        Args:
            config: Router configuration
            event_handler: Async callable to handle events
            collection_filter: Optional list of collection UUIDs to filter events
        """
        self.config = config
        self.event_handler = event_handler
        self.collection_filter = collection_filter
        
        # Event queue
        self.event_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.max_queue_size
        )
        
        # Dead letter queue for failed events
        self.dead_letter_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.dead_letter_queue_max_size
        )
        
        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Statistics
        self.stats = {
            "events_received": 0,
            "events_processed": 0,
            "events_failed": 0,
            "events_filtered": 0,
            "events_in_dead_letter": 0,
            "current_queue_size": 0,
            "peak_queue_size": 0,
            "started_at": None,
            "last_event_at": None
        }
        
        logger.info(
            f"EventRouter initialized: {config.worker_count} workers, "
            f"queue size {config.max_queue_size}, "
            f"retry max {config.retry_max_attempts}"
        )
    
    async def start(self) -> None:
        """Start the event router and worker pool."""
        if self.running:
            logger.warning("EventRouter already running")
            return
        
        self.running = True
        self.stats["started_at"] = datetime.now(timezone.utc)
        
        # Start worker tasks
        for i in range(self.config.worker_count):
            worker = asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"EventRouter-Worker-{i}"
            )
            self.workers.append(worker)
        
        logger.info(
            f"EventRouter started with {self.config.worker_count} workers"
        )
    
    async def stop(self) -> None:
        """Stop the event router gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping EventRouter...")
        self.running = False
        
        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        # Process remaining events in queue (with timeout)
        try:
            remaining = self.event_queue.qsize()
            if remaining > 0:
                logger.info(f"Processing {remaining} remaining events...")
                await asyncio.wait_for(
                    self._drain_queue(),
                    timeout=30.0
                )
        except asyncio.TimeoutError:
            logger.warning("Timeout draining event queue, some events may be lost")
        
        logger.info("EventRouter stopped")
    
    async def route_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Route an event to the queue for processing.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if event was queued, False if rejected
        """
        if not self.running:
            logger.warning("EventRouter not running, event rejected")
            return False
        
        self.stats["events_received"] += 1
        self.stats["last_event_at"] = datetime.now(timezone.utc)
        
        # Filter event
        if not self._should_process_event(event_data):
            self.stats["events_filtered"] += 1
            logger.debug(f"Event filtered: {event_data.get('event_type')}")
            return False
        
        # Try to add to queue (non-blocking)
        try:
            self.event_queue.put_nowait(event_data)
            
            # Update queue statistics
            current_size = self.event_queue.qsize()
            self.stats["current_queue_size"] = current_size
            if current_size > self.stats["peak_queue_size"]:
                self.stats["peak_queue_size"] = current_size
            
            return True
            
        except asyncio.QueueFull:
            logger.error(
                f"Event queue full ({self.config.max_queue_size}), "
                "event rejected - backpressure activated"
            )
            return False
    
    def _should_process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Determine if an event should be processed.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if event should be processed
        """
        # Check event type
        event_type = event_data.get("event_type")
        if not event_type:
            logger.warning("Event missing event_type field")
            return False
        
        # Currently we only process face_detection_completed events
        if event_type != EventType.FACE_DETECTION_COMPLETED:
            logger.debug(f"Ignoring event type: {event_type}")
            return False
        
        # Check collection filter
        if self.collection_filter:
            payload = event_data.get("payload", {})
            collection_id = payload.get("collection_id")
            
            if not collection_id:
                logger.warning("Event missing collection_id in payload")
                return False
            
            # Convert to UUID if string
            if isinstance(collection_id, str):
                try:
                    collection_id = UUID(collection_id)
                except ValueError:
                    logger.warning(f"Invalid collection_id UUID: {collection_id}")
                    return False
            
            if collection_id not in self.collection_filter:
                logger.debug(
                    f"Event collection {collection_id} not in filter, ignoring"
                )
                return False
        
        return True
    
    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop to process events from the queue.
        
        Args:
            worker_id: Worker identifier for logging
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get event from queue with timeout
                event_data = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Update queue size stat
                self.stats["current_queue_size"] = self.event_queue.qsize()
                
                # Process event with retry logic
                success = await self._process_event_with_retry(
                    event_data,
                    worker_id
                )
                
                if success:
                    self.stats["events_processed"] += 1
                else:
                    self.stats["events_failed"] += 1
                    # Add to dead letter queue
                    await self._add_to_dead_letter_queue(event_data)
                
                # Mark task as done
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                # No events in queue, continue
                continue
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} unexpected error: {e}",
                    exc_info=True
                )
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_event_with_retry(
        self,
        event_data: Dict[str, Any],
        worker_id: int
    ) -> bool:
        """
        Process event with retry logic.
        
        Args:
            event_data: Event data dictionary
            worker_id: Worker identifier for logging
            
        Returns:
            True if event processed successfully
        """
        for attempt in range(self.config.retry_max_attempts):
            try:
                # Call event handler
                await self.event_handler(event_data)
                
                if attempt > 0:
                    logger.info(
                        f"Worker {worker_id}: Event processed successfully "
                        f"on retry {attempt}"
                    )
                
                return True
                
            except Exception as e:
                logger.error(
                    f"Worker {worker_id}: Event processing failed "
                    f"(attempt {attempt + 1}/{self.config.retry_max_attempts}): {e}"
                )
                
                if attempt < self.config.retry_max_attempts - 1:
                    # Calculate backoff delay
                    delay = self.config.retry_initial_delay * (
                        self.config.retry_backoff_multiplier ** attempt
                    )
                    delay = min(delay, self.config.retry_max_delay)
                    
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(
            f"Worker {worker_id}: Event processing failed after "
            f"{self.config.retry_max_attempts} attempts, moving to dead letter queue"
        )
        return False
    
    async def _add_to_dead_letter_queue(self, event_data: Dict[str, Any]) -> None:
        """
        Add failed event to dead letter queue.
        
        Args:
            event_data: Event data dictionary
        """
        try:
            # Add metadata about failure
            dead_letter_event = {
                **event_data,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "retry_attempts": self.config.retry_max_attempts
            }
            
            self.dead_letter_queue.put_nowait(dead_letter_event)
            self.stats["events_in_dead_letter"] = self.dead_letter_queue.qsize()
            
            logger.warning(
                f"Event added to dead letter queue "
                f"(size: {self.dead_letter_queue.qsize()})"
            )
            
        except asyncio.QueueFull:
            logger.error(
                "Dead letter queue full, event will be lost! "
                "Consider processing dead letter queue."
            )
    
    async def _drain_queue(self) -> None:
        """Process all remaining events in queue."""
        while not self.event_queue.empty():
            try:
                event_data = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=0.1
                )
                await self._process_event_with_retry(event_data, worker_id=-1)
                self.event_queue.task_done()
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Error draining queue: {e}")
                break
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get router statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()
        stats["current_queue_size"] = self.event_queue.qsize()
        stats["dead_letter_queue_size"] = self.dead_letter_queue.qsize()
        stats["worker_count"] = len(self.workers)
        stats["running"] = self.running
        
        # Calculate uptime
        if stats["started_at"]:
            uptime = datetime.now(timezone.utc) - stats["started_at"]
            stats["uptime_seconds"] = uptime.total_seconds()
        else:
            stats["uptime_seconds"] = 0
        
        # Calculate processing rate
        if stats["uptime_seconds"] > 0:
            stats["events_per_second"] = (
                stats["events_processed"] / stats["uptime_seconds"]
            )
        else:
            stats["events_per_second"] = 0
        
        return stats
    
    async def get_dead_letter_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve events from dead letter queue without removing them.
        
        Args:
            limit: Maximum number of events to retrieve
            
        Returns:
            List of failed event data
        """
        events = []
        temp_queue = asyncio.Queue()
        
        try:
            # Extract events
            for _ in range(min(limit, self.dead_letter_queue.qsize())):
                event = await asyncio.wait_for(
                    self.dead_letter_queue.get(),
                    timeout=0.1
                )
                events.append(event)
                await temp_queue.put(event)
            
            # Put events back
            while not temp_queue.empty():
                event = await temp_queue.get()
                await self.dead_letter_queue.put(event)
            
            return events
            
        except asyncio.TimeoutError:
            return events
    
    async def clear_dead_letter_queue(self) -> int:
        """
        Clear all events from dead letter queue.
        
        Returns:
            Number of events cleared
        """
        count = 0
        while not self.dead_letter_queue.empty():
            try:
                await asyncio.wait_for(
                    self.dead_letter_queue.get(),
                    timeout=0.1
                )
                count += 1
            except asyncio.TimeoutError:
                break
        
        self.stats["events_in_dead_letter"] = 0
        logger.info(f"Cleared {count} events from dead letter queue")
        return count
    
    def is_healthy(self) -> bool:
        """
        Check if router is healthy.
        
        Returns:
            True if router is healthy
        """
        if not self.running:
            return False
        
        # Check if queue is near capacity
        queue_size = self.event_queue.qsize()
        if queue_size >= self.config.max_queue_size * 0.9:
            logger.warning(
                f"Event queue near capacity: {queue_size}/{self.config.max_queue_size}"
            )
            return False
        
        # Check dead letter queue
        dead_letter_size = self.dead_letter_queue.qsize()
        if dead_letter_size >= self.config.dead_letter_queue_max_size * 0.5:
            logger.warning(
                f"Dead letter queue accumulating: {dead_letter_size}/"
                f"{self.config.dead_letter_queue_max_size}"
            )
            return False
        
        # Check if workers are alive
        alive_workers = sum(1 for w in self.workers if not w.done())
        if alive_workers < self.config.worker_count:
            logger.error(
                f"Some workers died: {alive_workers}/{self.config.worker_count}"
            )
            return False
        
        return True
