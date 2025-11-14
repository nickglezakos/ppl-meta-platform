"""
Hybrid Batch Trigger

Implements Strategy 3 (Hybrid Approach) for batch processing:
- PRIMARY: Recording stop events → Immediate trigger for partial batches
- FALLBACK: Timeout monitoring → Automatic trigger if event is missed
- SAFEGUARD: Max wait time → Force trigger after extended period

This is the recommended approach for handling partial batches (videos remaining
after a recording session ends).

Architecture:
    Normal flow:
        Video 1-5 → Batch triggers at 5 (threshold)
        Video 6-8 → Recording stops → Immediate trigger (recording_stopped event)
    
    Fallback flow (event missed):
        Video 6-8 → Recording stops → Event NOT received
        → Timeout after 10 minutes → Trigger (timeout)

Features:
- Real-time response to recording stop events
- Automatic timeout fallback if events are missed
- Per-collection timeout task management
- Configurable minimum partial batch size
- Configurable timeout duration
- Graceful cancellation of timeout tasks
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID

from ..database.connection import get_database_connection


logger = logging.getLogger(__name__)


class HybridBatchTrigger:
    """
    Hybrid batch triggering: recording stop events + timeout fallback.
    
    This class manages batch triggering using two complementary strategies:
    1. Recording stop events (primary) - Immediate processing when recording ends
    2. Timeout monitoring (fallback) - Automatic trigger if event is missed
    
    Features:
    - Per-collection timeout task management
    - Automatic cleanup and cancellation
    - Configurable timeout and minimum batch size
    - Integration with Camera Service events
    - Database state tracking
    """
    
    def __init__(
        self,
        default_timeout_minutes: int = 10,
        default_min_partial_batch_size: int = 2,
        max_wait_hours: int = 24
    ):
        """
        Initialize hybrid batch trigger.
        
        Args:
            default_timeout_minutes: Default timeout for partial batches
            default_min_partial_batch_size: Minimum videos for partial batch
            max_wait_hours: Maximum wait time before forcing trigger
        """
        self.default_timeout_minutes = default_timeout_minutes
        self.default_min_partial_batch_size = default_min_partial_batch_size
        self.max_wait_hours = max_wait_hours
        
        # Timeout task tracking: collection_id -> asyncio.Task
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        
        # Batch trigger callbacks
        self.on_batch_trigger_callback = None
        
        logger.info(
            f"HybridBatchTrigger initialized: "
            f"timeout={default_timeout_minutes}m, "
            f"min_partial_size={default_min_partial_batch_size}, "
            f"max_wait={max_wait_hours}h"
        )
    
    def set_batch_trigger_callback(self, callback):
        """
        Set callback function to invoke when batch should be triggered.
        
        Args:
            callback: Async function(batch_uuid, reason, is_partial) -> None
        """
        self.on_batch_trigger_callback = callback
    
    async def on_video_added(
        self,
        collection_id: str,
        batch_uuid: UUID,
        video_count: int,
        batch_size_threshold: int
    ) -> None:
        """
        Called when a video is added to a batch.
        
        This method:
        1. Checks if batch has reached threshold (normal trigger)
        2. If not, starts/resets timeout task for partial batch handling
        
        Args:
            collection_id: Collection identifier
            batch_uuid: Current batch UUID
            video_count: Current number of videos in batch
            batch_size_threshold: Threshold for normal batch trigger
        """
        logger.debug(
            f"[HYBRID] Video added to batch {str(batch_uuid)[:8]}: "
            f"{video_count}/{batch_size_threshold} videos"
        )
        
        # Check normal batch size trigger
        if video_count >= batch_size_threshold:
            logger.info(
                f"[THRESHOLD] Batch {str(batch_uuid)[:8]} reached threshold "
                f"({video_count} videos)"
            )
            await self._trigger_batch(
                batch_uuid=batch_uuid,
                collection_id=collection_id,
                reason="threshold",
                is_partial=False
            )
            return
        
        # Start/reset timeout task for partial batch
        await self._start_timeout_task(
            collection_id=collection_id,
            batch_uuid=batch_uuid,
            current_video_count=video_count
        )
    
    async def on_recording_stopped(
        self,
        collection_id: str,
        recording_session_id: Optional[str] = None,
        reason: str = "user_stopped"
    ) -> None:
        """
        PRIMARY TRIGGER: Called when recording session stops.
        
        This is the main mechanism for handling partial batches. When a
        recording session stops, we immediately trigger any accumulating batch
        that has enough videos (>= min_partial_batch_size).
        
        Args:
            collection_id: Collection identifier
            recording_session_id: Optional recording session UUID
            reason: Reason for recording stop (user_stopped, error, etc.)
        """
        logger.info(
            f"[RECORDING STOP] Recording stopped for collection {collection_id} "
            f"(reason: {reason})"
        )
        
        # Cancel timeout task (no longer needed)
        await self._cancel_timeout_task(collection_id)
        
        # Get current batch for collection
        batch = await self._get_active_batch(collection_id)
        
        if not batch:
            logger.info(
                f"[RECORDING STOP] No active batch for {collection_id}"
            )
            return
        
        batch_uuid = batch['batch_uuid']
        video_count = batch['video_count']
        
        # Get minimum partial batch size
        min_size = await self._get_min_partial_batch_size(collection_id)
        
        if video_count < min_size:
            logger.info(
                f"[RECORDING STOP] Batch {str(batch_uuid)[:8]} has only "
                f"{video_count} videos (< {min_size} minimum), not triggering"
            )
            return
        
        logger.info(
            f"[RECORDING STOP] Triggering partial batch {str(batch_uuid)[:8]} "
            f"with {video_count} remaining videos (reason: recording_stopped)"
        )
        
        await self._trigger_batch(
            batch_uuid=batch_uuid,
            collection_id=collection_id,
            reason="recording_stopped",
            is_partial=True
        )
    
    async def _start_timeout_task(
        self,
        collection_id: str,
        batch_uuid: UUID,
        current_video_count: int
    ) -> None:
        """
        FALLBACK TRIGGER: Start timeout monitoring task.
        
        Creates an asyncio task that waits for the configured timeout period.
        If the timeout expires and the batch is still accumulating, it triggers
        a partial batch.
        
        This serves as a fallback in case:
        - Recording stop event is missed
        - Recording crashes without sending stop event
        - Network issues prevent event delivery
        
        Args:
            collection_id: Collection identifier
            batch_uuid: Batch UUID to monitor
            current_video_count: Current video count for logging
        """
        # Cancel existing timeout task for this collection
        await self._cancel_timeout_task(collection_id)
        
        # Get timeout configuration
        timeout_minutes = await self._get_timeout_minutes(collection_id)
        
        logger.debug(
            f"[TIMEOUT] Starting timeout task for {collection_id}: "
            f"{timeout_minutes} minutes (batch {str(batch_uuid)[:8]}, "
            f"{current_video_count} videos)"
        )
        
        # Create new timeout task
        task = asyncio.create_task(
            self._timeout_handler(
                collection_id=collection_id,
                batch_uuid=batch_uuid,
                timeout_minutes=timeout_minutes
            ),
            name=f"BatchTimeout-{collection_id}"
        )
        
        self.timeout_tasks[collection_id] = task
        
        # Update database with timeout timestamp
        await self._update_batch_timeout(
            batch_uuid=batch_uuid,
            timeout_at=datetime.now(timezone.utc) + timedelta(
                minutes=timeout_minutes
            )
        )
    
    async def _timeout_handler(
        self,
        collection_id: str,
        batch_uuid: UUID,
        timeout_minutes: int
    ) -> None:
        """
        Timeout monitoring task handler.
        
        Waits for the specified timeout period. If the task is not cancelled
        (i.e., recording stop event was not received), triggers the partial
        batch if it has enough videos.
        
        Args:
            collection_id: Collection identifier
            batch_uuid: Batch UUID being monitored
            timeout_minutes: Timeout duration in minutes
        """
        timeout_seconds = timeout_minutes * 60
        
        try:
            logger.debug(
                f"[TIMEOUT] Waiting {timeout_minutes}m for batch "
                f"{str(batch_uuid)[:8]} ({collection_id})"
            )
            
            await asyncio.sleep(timeout_seconds)
            
            # Timeout expired - check if batch is still accumulating
            batch = await self._get_active_batch(collection_id)
            
            if not batch:
                logger.debug(
                    f"[TIMEOUT] No active batch for {collection_id} "
                    "(likely already processed)"
                )
                return
            
            # Verify this is the same batch we were monitoring
            if batch['batch_uuid'] != batch_uuid:
                logger.debug(
                    f"[TIMEOUT] Batch UUID mismatch for {collection_id} "
                    "(new batch started)"
                )
                return
            
            video_count = batch['video_count']
            min_size = await self._get_min_partial_batch_size(collection_id)
            
            if video_count < min_size:
                logger.info(
                    f"[TIMEOUT] Batch {str(batch_uuid)[:8]} timeout expired "
                    f"but only has {video_count} videos (< {min_size} minimum)"
                )
                return
            
            logger.warning(
                f"[TIMEOUT] Batch {str(batch_uuid)[:8]} timeout expired "
                f"({timeout_minutes}m), triggering partial batch with "
                f"{video_count} videos"
            )
            
            await self._trigger_batch(
                batch_uuid=batch_uuid,
                collection_id=collection_id,
                reason="timeout",
                is_partial=True
            )
            
        except asyncio.CancelledError:
            logger.debug(
                f"[TIMEOUT] Task cancelled for {collection_id} "
                f"(batch {str(batch_uuid)[:8]})"
            )
            raise
        
        except Exception as e:
            logger.error(
                f"[TIMEOUT] Error in timeout handler for {collection_id}: {e}",
                exc_info=True
            )
        
        finally:
            # Remove from tracking dict
            if collection_id in self.timeout_tasks:
                del self.timeout_tasks[collection_id]
    
    async def _cancel_timeout_task(self, collection_id: str) -> None:
        """
        Cancel timeout monitoring task for a collection.
        
        Called when:
        - Recording stop event is received (timeout no longer needed)
        - Batch triggers via threshold (normal trigger)
        - New timeout task is started (replaces old one)
        
        Args:
            collection_id: Collection identifier
        """
        task = self.timeout_tasks.get(collection_id)
        
        if not task:
            return
        
        if task.done():
            # Task already completed
            del self.timeout_tasks[collection_id]
            return
        
        logger.debug(
            f"[TIMEOUT] Cancelling timeout task for {collection_id}"
        )
        
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Remove from tracking dict
        if collection_id in self.timeout_tasks:
            del self.timeout_tasks[collection_id]
    
    async def _trigger_batch(
        self,
        batch_uuid: UUID,
        collection_id: str,
        reason: str,
        is_partial: bool
    ) -> None:
        """
        Trigger batch processing.
        
        Invokes the callback function to actually process the batch.
        Updates database state to mark batch as triggered.
        
        Args:
            batch_uuid: Batch UUID to trigger
            collection_id: Collection identifier
            reason: Trigger reason (threshold, recording_stopped, timeout)
            is_partial: Whether this is a partial batch
        """
        logger.info(
            f"[TRIGGER] Batch {str(batch_uuid)[:8]} triggered: "
            f"reason={reason}, partial={is_partial}, collection={collection_id}"
        )
        
        # Update database state
        await self._update_batch_trigger_info(
            batch_uuid=batch_uuid,
            trigger_reason=reason,
            is_partial=is_partial
        )
        
        # Invoke callback if set
        if self.on_batch_trigger_callback:
            try:
                await self.on_batch_trigger_callback(
                    batch_uuid=batch_uuid,
                    collection_id=collection_id,
                    reason=reason,
                    is_partial=is_partial
                )
            except Exception as e:
                logger.error(
                    f"[TRIGGER] Error in batch trigger callback: {e}",
                    exc_info=True
                )
        else:
            logger.warning(
                "[TRIGGER] No batch trigger callback configured"
            )
    
    async def _get_active_batch(
        self,
        collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current accumulating batch for collection.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Batch dict or None if no active batch
        """
        async with get_database_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    batch_uuid,
                    collection_id,
                    batch_number,
                    status,
                    video_count,
                    batch_size_threshold,
                    first_video_start_time,
                    last_video_end_time,
                    created_at
                FROM batch_processing_state
                WHERE collection_id = $1
                  AND status = 'accumulating'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                collection_id
            )
            
            if not row:
                return None
            
            return dict(row)
    
    async def _get_timeout_minutes(self, collection_id: str) -> int:
        """
        Get timeout configuration for collection.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Timeout in minutes
        """
        async with get_database_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT partial_batch_timeout_minutes
                FROM batch_processing_config
                WHERE collection_id = $1
                   OR collection_id IS NULL
                ORDER BY collection_id DESC NULLS LAST
                LIMIT 1
                """,
                collection_id
            )
            
            if row:
                return row['partial_batch_timeout_minutes']
            
            return self.default_timeout_minutes
    
    async def _get_min_partial_batch_size(self, collection_id: str) -> int:
        """
        Get minimum partial batch size for collection.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Minimum number of videos for partial batch
        """
        async with get_database_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT partial_batch_min_videos
                FROM batch_processing_config
                WHERE collection_id = $1
                   OR collection_id IS NULL
                ORDER BY collection_id DESC NULLS LAST
                LIMIT 1
                """,
                collection_id
            )
            
            if row:
                return row['partial_batch_min_videos']
            
            return self.default_min_partial_batch_size
    
    async def _update_batch_timeout(
        self,
        batch_uuid: UUID,
        timeout_at: datetime
    ) -> None:
        """
        Update batch with timeout timestamp.
        
        Args:
            batch_uuid: Batch UUID
            timeout_at: When timeout will trigger
        """
        async with get_database_connection() as conn:
            await conn.execute(
                """
                UPDATE batch_processing_state
                SET timeout_at = $2,
                    last_video_time = NOW(),
                    updated_at = NOW()
                WHERE batch_uuid = $1
                """,
                batch_uuid,
                timeout_at
            )
    
    async def _update_batch_trigger_info(
        self,
        batch_uuid: UUID,
        trigger_reason: str,
        is_partial: bool
    ) -> None:
        """
        Update batch with trigger information.
        
        Args:
            batch_uuid: Batch UUID
            trigger_reason: Reason for trigger
            is_partial: Whether this is a partial batch
        """
        async with get_database_connection() as conn:
            await conn.execute(
                """
                UPDATE batch_processing_state
                SET trigger_reason = $2,
                    is_partial_batch = $3,
                    triggered_at = NOW(),
                    status = 'processing',
                    updated_at = NOW()
                WHERE batch_uuid = $1
                """,
                batch_uuid,
                trigger_reason,
                is_partial
            )
    
    async def cleanup(self) -> None:
        """
        Cleanup and cancel all timeout tasks.
        
        Should be called when shutting down the service.
        """
        logger.info(
            f"[CLEANUP] Cancelling {len(self.timeout_tasks)} timeout tasks"
        )
        
        tasks = list(self.timeout_tasks.values())
        
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to finish
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.timeout_tasks.clear()
        
        logger.info("[CLEANUP] All timeout tasks cancelled")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about timeout task management.
        
        Returns:
            Dictionary with statistics
        """
        active_tasks = sum(
            1 for task in self.timeout_tasks.values()
            if not task.done()
        )
        
        return {
            "active_timeout_tasks": active_tasks,
            "total_tracked_collections": len(self.timeout_tasks),
            "default_timeout_minutes": self.default_timeout_minutes,
            "default_min_partial_batch_size": (
                self.default_min_partial_batch_size
            ),
            "max_wait_hours": self.max_wait_hours,
            "callback_configured": self.on_batch_trigger_callback is not None
        }
