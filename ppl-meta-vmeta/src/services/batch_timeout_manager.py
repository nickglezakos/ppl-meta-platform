"""
Batch Timeout Manager
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Background service for monitoring batch timeouts and triggering partial
batch processing when batches reach their timeout threshold.

This service runs as a background task, periodically checking for batches
that have reached their timeout and coordinating with the batch monitor
to trigger processing.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from ..models.batch_processing import BatchProcessingState
from ..database.batch_repository import BatchProcessingRepository
from .batch_monitor import BatchMonitor

logger = logging.getLogger(__name__)


class BatchTimeoutManager:
    """
    Background service for monitoring batch timeouts.
    
    Responsibilities:
    - Run periodic checks for timeout batches
    - Coordinate with batch monitor to trigger processing
    - Handle graceful shutdown
    - Track timeout statistics
    """
    
    def __init__(
        self,
        repository: BatchProcessingRepository,
        batch_monitor: BatchMonitor,
        check_interval_seconds: int = 30,
        enabled: bool = True
    ):
        """
        Initialize timeout manager.
        
        Args:
            repository: Database repository
            batch_monitor: Batch monitor service
            check_interval_seconds: How often to check for timeouts
            enabled: Whether timeout checking is enabled
        """
        self.repository = repository
        self.batch_monitor = batch_monitor
        self.check_interval = check_interval_seconds
        self.enabled = enabled
        
        # Background task
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._stats = {
            'checks_performed': 0,
            'timeouts_found': 0,
            'timeouts_triggered': 0,
            'timeouts_failed': 0,
            'last_check_at': None
        }
        
        logger.info(
            f"BatchTimeoutManager initialized "
            f"(interval: {check_interval_seconds}s, enabled: {enabled})"
        )
    
    async def start(self):
        """Start the timeout monitoring background task."""
        if not self.enabled:
            logger.info("Timeout manager disabled, not starting")
            return
        
        if self._running:
            logger.warning("Timeout manager already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_monitoring_loop())
        
        logger.info("Timeout manager started")
    
    async def stop(self, timeout: float = 10.0):
        """
        Stop the timeout monitoring background task.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self._running:
            return
        
        logger.info("Stopping timeout manager...")
        
        self._running = False
        self._shutdown_event.set()
        
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("Timeout manager did not stop gracefully")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Timeout manager stopped")
    
    async def _run_monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Timeout monitoring loop started")
        
        try:
            while self._running:
                try:
                    # Check for timeout batches
                    await self._check_timeouts()
                    
                    # Wait for next check or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.check_interval
                        )
                        # Shutdown event was set
                        break
                    except asyncio.TimeoutError:
                        # Normal timeout, continue loop
                        pass
                
                except Exception as e:
                    logger.error(f"Error in timeout monitoring loop: {e}")
                    # Brief pause before retry
                    await asyncio.sleep(5)
        
        finally:
            logger.info("Timeout monitoring loop ended")
    
    async def _check_timeouts(self):
        """Check for and handle timeout batches."""
        try:
            # Get batches that have reached timeout
            timeout_batches = await self.repository.get_timeout_batches()
            
            self._stats['checks_performed'] += 1
            self._stats['last_check_at'] = datetime.utcnow()
            
            if not timeout_batches:
                logger.debug("No timeout batches found")
                return
            
            logger.info(f"Found {len(timeout_batches)} timeout batches")
            self._stats['timeouts_found'] += len(timeout_batches)
            
            # Process each timeout batch
            for batch in timeout_batches:
                await self._handle_timeout_batch(batch)
        
        except Exception as e:
            logger.error(f"Failed to check timeouts: {e}")
    
    async def _handle_timeout_batch(self, batch: BatchProcessingState):
        """
        Handle a single timeout batch.
        
        Args:
            batch: Batch that has reached timeout
        """
        try:
            logger.info(
                f"Processing timeout for batch {batch.batch_uuid} "
                f"(collection: {batch.collection_id}, "
                f"videos: {batch.video_count})"
            )
            
            # Delegate to batch monitor
            response = await self.batch_monitor.handle_batch_timeout(
                batch.batch_uuid
            )
            
            if response:
                self._stats['timeouts_triggered'] += 1
                logger.info(
                    f"Triggered timeout batch {batch.batch_uuid} "
                    f"({batch.video_count} videos)"
                )
            else:
                logger.debug(
                    f"Batch {batch.batch_uuid} not triggered "
                    "(below minimum or disabled)"
                )
        
        except Exception as e:
            logger.error(f"Failed to handle timeout batch {batch.batch_uuid}: {e}")
            self._stats['timeouts_failed'] += 1
    
    async def check_now(self) -> int:
        """
        Manually trigger an immediate timeout check.
        
        Returns:
            Number of batches that timed out
        """
        logger.info("Manual timeout check triggered")
        
        timeout_batches = await self.repository.get_timeout_batches()
        
        if not timeout_batches:
            return 0
        
        count = 0
        for batch in timeout_batches:
            try:
                response = await self.batch_monitor.handle_batch_timeout(
                    batch.batch_uuid
                )
                if response:
                    count += 1
            except Exception as e:
                logger.error(f"Failed to process timeout: {e}")
        
        return count
    
    def get_statistics(self) -> dict:
        """
        Get timeout manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            'running': self._running,
            'enabled': self.enabled,
            'check_interval': self.check_interval
        }
    
    def is_running(self) -> bool:
        """
        Check if timeout manager is running.
        
        Returns:
            True if running
        """
        return self._running
    
    async def get_upcoming_timeouts(
        self,
        within_minutes: int = 30
    ) -> List[BatchProcessingState]:
        """
        Get batches that will timeout within specified minutes.
        
        Args:
            within_minutes: Look ahead window in minutes
            
        Returns:
            List of batches approaching timeout
        """
        try:
            cutoff = datetime.utcnow() + timedelta(minutes=within_minutes)
            
            # This would require a custom query
            # For now, get all timeout batches and filter
            timeout_batches = await self.repository.get_timeout_batches()
            
            upcoming = [
                batch for batch in timeout_batches
                if batch.timeout_at and batch.timeout_at <= cutoff
            ]
            
            return upcoming
        
        except Exception as e:
            logger.error(f"Failed to get upcoming timeouts: {e}")
            return []


class PollingFallbackManager:
    """
    Polling-based fallback for event-driven batch monitoring.
    
    Used when event system is unavailable or unreliable.
    Periodically polls database for completed videos and triggers
    batch processing.
    """
    
    def __init__(
        self,
        batch_monitor: BatchMonitor,
        poll_interval_seconds: int = 60,
        enabled: bool = False
    ):
        """
        Initialize polling fallback manager.
        
        Args:
            batch_monitor: Batch monitor service
            poll_interval_seconds: Polling interval
            enabled: Whether polling is enabled
        """
        self.batch_monitor = batch_monitor
        self.poll_interval = poll_interval_seconds
        self.enabled = enabled
        
        # Background task
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._stats = {
            'polls_performed': 0,
            'videos_discovered': 0,
            'polls_failed': 0,
            'last_poll_at': None
        }
        
        logger.info(
            f"PollingFallbackManager initialized "
            f"(interval: {poll_interval_seconds}s, enabled: {enabled})"
        )
    
    async def start(self):
        """Start the polling background task."""
        if not self.enabled:
            logger.info("Polling fallback disabled, not starting")
            return
        
        if self._running:
            logger.warning("Polling fallback already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_polling_loop())
        
        logger.info("Polling fallback started")
    
    async def stop(self, timeout: float = 10.0):
        """
        Stop the polling background task.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self._running:
            return
        
        logger.info("Stopping polling fallback...")
        
        self._running = False
        self._shutdown_event.set()
        
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("Polling fallback did not stop gracefully")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Polling fallback stopped")
    
    async def _run_polling_loop(self):
        """Main polling loop."""
        logger.info("Polling loop started")
        
        try:
            while self._running:
                try:
                    # Poll for new videos
                    await self._poll_for_videos()
                    
                    # Wait for next poll or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.poll_interval
                        )
                        # Shutdown event was set
                        break
                    except asyncio.TimeoutError:
                        # Normal timeout, continue loop
                        pass
                
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    self._stats['polls_failed'] += 1
                    await asyncio.sleep(5)
        
        finally:
            logger.info("Polling loop ended")
    
    async def _poll_for_videos(self):
        """
        Poll for completed videos.
        
        Note: This is a placeholder. Actual implementation would query
        the video/face detection service for completed videos.
        """
        try:
            self._stats['polls_performed'] += 1
            self._stats['last_poll_at'] = datetime.utcnow()
            
            # TODO: Implement actual polling logic
            # This would involve:
            # 1. Query face detection service for completed sessions
            # 2. Check which videos haven't been added to batches
            # 3. Create VideoCompletionEvent for each
            # 4. Call batch_monitor.handle_video_completion()
            
            logger.debug("Polling for completed videos (not implemented)")
        
        except Exception as e:
            logger.error(f"Failed to poll for videos: {e}")
            self._stats['polls_failed'] += 1
    
    def get_statistics(self) -> dict:
        """
        Get polling manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            'running': self._running,
            'enabled': self.enabled,
            'poll_interval': self.poll_interval
        }
    
    def is_running(self) -> bool:
        """
        Check if polling manager is running.
        
        Returns:
            True if running
        """
        return self._running
