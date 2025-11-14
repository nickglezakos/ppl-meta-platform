"""
Batch Monitor Service
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Core service for monitoring batch accumulation, handling video completion
events, managing state transitions, and triggering batch processing.

This service is the heart of the continuous individuals pipeline, responsible for:
- Tracking video completion events
- Accumulating videos into batches
- Managing partial batch timeouts
- Triggering batch processing when thresholds are met
- Coordinating with event handlers and timeout managers

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable, Awaitable
from uuid import UUID, uuid4

from ..models.batch_processing import (
    BatchProcessingState,
    BatchProcessingConfig,
    BatchVideoAssignment,
    VideoCompletionEvent,
    RecordingStopEvent,
    BatchStatus,
    TriggerReason,
    BatchTriggerResponse
)
from ..database.batch_repository import BatchProcessingRepository
from .batch_config import BatchConfigService

logger = logging.getLogger(__name__)


class BatchMonitorError(Exception):
    """Custom exception for batch monitor operations."""
    pass


class BatchMonitor:
    """
    Service for monitoring and managing batch accumulation.
    
    Responsibilities:
    - Track video completions and add to active batches
    - Create new batches when needed
    - Monitor batch size and trigger processing
    - Handle partial batch scenarios
    - Manage batch state transitions
    - Coordinate timeout tracking
    """
    
    def __init__(
        self,
        repository: BatchProcessingRepository,
        config_service: BatchConfigService,
        batch_processor_callback: Optional[Callable[[UUID], Awaitable[None]]] = None
    ):
        """
        Initialize batch monitor.
        
        Args:
            repository: Database repository for batch operations
            config_service: Configuration service
            batch_processor_callback: Async callback to trigger batch processing
        """
        self.repository = repository
        self.config_service = config_service
        self.batch_processor_callback = batch_processor_callback
        
        # Hybrid trigger integration (set via set_hybrid_trigger)
        self.hybrid_trigger = None
        
        # In-memory tracking for active batches
        self._active_batches: Dict[str, UUID] = {}  # collection_id -> batch_uuid
        self._batch_locks: Dict[str, asyncio.Lock] = {}  # collection_id -> lock
        
        # Statistics
        self._stats = {
            'videos_processed': 0,
            'batches_created': 0,
            'batches_triggered': 0,
            'partial_batches': 0,
            'full_batches': 0
        }
        
        logger.info("BatchMonitor initialized")
    
    def set_hybrid_trigger(self, hybrid_trigger):
        """
        Set hybrid batch trigger for partial batch handling.
        
        Args:
            hybrid_trigger: HybridBatchTrigger instance
        """
        self.hybrid_trigger = hybrid_trigger
        logger.info("HybridBatchTrigger integration enabled")
    
    def _get_collection_lock(self, collection_id: str) -> asyncio.Lock:
        """Get or create lock for collection."""
        if collection_id not in self._batch_locks:
            self._batch_locks[collection_id] = asyncio.Lock()
        return self._batch_locks[collection_id]
    
    async def handle_video_completion(
        self,
        event: VideoCompletionEvent
    ) -> Optional[BatchTriggerResponse]:
        """
        Handle video completion event.
        
        This is the main entry point for batch accumulation.
        
        Args:
            event: Video completion event details
            
        Returns:
            BatchTriggerResponse if batch was triggered, None otherwise
            
        Raises:
            BatchMonitorError: If processing fails
        """
        collection_id = event.collection_id
        lock = self._get_collection_lock(collection_id)
        
        async with lock:
            try:
                logger.info(
                    f"Processing video completion: {event.video_uuid} "
                    f"for collection {collection_id}"
                )
                
                # Get or create active batch
                batch = await self._get_or_create_batch(collection_id)
                
                # Add video to batch
                await self._add_video_to_batch(batch, event)
                
                # Update batch state
                batch = await self._update_batch_after_video(batch)
                
                # Notify hybrid trigger (if configured)
                if self.hybrid_trigger:
                    await self.hybrid_trigger.on_video_added(
                        collection_id=collection_id,
                        batch_uuid=batch.batch_uuid,
                        video_count=batch.video_count,
                        batch_size_threshold=batch.batch_size_threshold
                    )
                
                # Check if batch should be triggered
                if await self._should_trigger_batch(batch):
                    return await self._trigger_batch_processing(
                        batch,
                        TriggerReason.BATCH_SIZE_REACHED
                    )
                
                # Update timeout if needed (legacy, hybrid trigger handles this)
                await self._update_batch_timeout(batch)
                
                self._stats['videos_processed'] += 1
                
                return None
                
            except Exception as e:
                logger.error(f"Failed to handle video completion: {e}")
                raise BatchMonitorError(f"Video completion handling failed: {e}")
    
    async def handle_recording_stop(
        self,
        event: RecordingStopEvent
    ) -> Optional[BatchTriggerResponse]:
        """
        Handle recording stop event for partial batch processing.
        
        Delegates to HybridBatchTrigger if configured, otherwise falls back
        to legacy behavior.
        
        Args:
            event: Recording stop event details
            
        Returns:
            BatchTriggerResponse if batch was triggered, None otherwise
        """
        collection_id = event.collection_id
        
        # Delegate to hybrid trigger if configured
        if self.hybrid_trigger:
            await self.hybrid_trigger.on_recording_stopped(
                collection_id=collection_id,
                recording_session_id=event.recording_session_uuid,
                reason=event.reason
            )
            return None
        
        # Legacy fallback behavior
        lock = self._get_collection_lock(collection_id)
        
        async with lock:
            try:
                logger.info(
                    f"Processing recording stop for collection {collection_id}"
                )
                
                # Get active batch
                batch = await self.repository.get_active_batch(collection_id)
                
                if not batch:
                    logger.debug(f"No active batch for {collection_id}")
                    return None
                
                # Get configuration
                config = await self.config_service.get_collection_config(
                    collection_id
                )
                
                # Check if recording stop event is enabled
                if not config.enable_recording_stop_event:
                    logger.debug("Recording stop event disabled")
                    return None
                
                # Check if batch meets minimum for partial processing
                if batch.video_count < config.partial_batch_min_videos:
                    logger.info(
                        f"Batch has {batch.video_count} videos, "
                        f"minimum is {config.partial_batch_min_videos}"
                    )
                    return None
                
                # Apply delay if configured
                if config.recording_stop_trigger_delay_seconds > 0:
                    await asyncio.sleep(
                        config.recording_stop_trigger_delay_seconds
                    )
                
                # Trigger partial batch processing
                return await self._trigger_batch_processing(
                    batch,
                    TriggerReason.RECORDING_STOPPED,
                    is_partial=True
                )
                
            except Exception as e:
                logger.error(f"Failed to handle recording stop: {e}")
                raise BatchMonitorError(f"Recording stop handling failed: {e}")
    
    async def handle_batch_timeout(
        self,
        batch_uuid: UUID
    ) -> Optional[BatchTriggerResponse]:
        """
        Handle batch timeout for partial batch processing.
        
        Called by timeout manager when batch reaches timeout.
        
        Args:
            batch_uuid: Batch that timed out
            
        Returns:
            BatchTriggerResponse if batch was triggered, None otherwise
        """
        try:
            # Get batch
            batch = await self.repository.get_batch(batch_uuid)
            
            if not batch:
                logger.warning(f"Batch {batch_uuid} not found for timeout")
                return None
            
            if batch.status != BatchStatus.ACCUMULATING:
                logger.debug(f"Batch {batch_uuid} is not accumulating")
                return None
            
            collection_id = batch.collection_id
            lock = self._get_collection_lock(collection_id)
            
            async with lock:
                # Get configuration
                config = await self.config_service.get_collection_config(
                    collection_id
                )
                
                # Check if timeout fallback is enabled
                if not config.enable_timeout_fallback:
                    logger.debug("Timeout fallback disabled")
                    return None
                
                # Check if batch meets minimum
                if batch.video_count < config.partial_batch_min_videos:
                    logger.info(
                        f"Batch {batch_uuid} has {batch.video_count} videos, "
                        f"marking as incomplete"
                    )
                    await self.repository.update_batch(
                        batch_uuid,
                        status=BatchStatus.INCOMPLETE
                    )
                    return None
                
                # Trigger partial batch processing
                logger.info(f"Triggering timeout for batch {batch_uuid}")
                return await self._trigger_batch_processing(
                    batch,
                    TriggerReason.TIMEOUT_REACHED,
                    is_partial=True
                )
                
        except Exception as e:
            logger.error(f"Failed to handle batch timeout: {e}")
            raise BatchMonitorError(f"Batch timeout handling failed: {e}")
    
    async def _get_or_create_batch(
        self,
        collection_id: str
    ) -> BatchProcessingState:
        """
        Get active batch or create new one.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Active or newly created batch
        """
        # Try to get from cache
        cached_batch_uuid = self._active_batches.get(collection_id)
        if cached_batch_uuid:
            batch = await self.repository.get_batch(cached_batch_uuid)
            if batch and batch.status == BatchStatus.ACCUMULATING:
                return batch
            else:
                # Remove stale cache entry
                del self._active_batches[collection_id]
        
        # Try to get from database
        batch = await self.repository.get_active_batch(collection_id)
        
        if batch:
            # Cache it
            self._active_batches[collection_id] = batch.batch_uuid
            return batch
        
        # Create new batch
        return await self._create_new_batch(collection_id)
    
    async def _create_new_batch(
        self,
        collection_id: str
    ) -> BatchProcessingState:
        """
        Create new batch for collection.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Newly created batch
        """
        # Get configuration
        config = await self.config_service.get_collection_config(collection_id)
        
        # Get next batch number
        batch_number = await self.repository.get_next_batch_number(collection_id)
        
        # Create batch
        batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id=collection_id,
            batch_number=batch_number,
            status=BatchStatus.ACCUMULATING,
            video_count=0,
            batch_size_threshold=config.batch_size_threshold,
            is_partial_batch=False,
            last_video_time=datetime.utcnow(),
            timeout_at=self.config_service.calculate_timeout(config)
        )
        
        batch = await self.repository.create_batch(batch)
        
        # Cache it
        self._active_batches[collection_id] = batch.batch_uuid
        self._stats['batches_created'] += 1
        
        logger.info(
            f"Created batch {batch.batch_uuid} (#{batch_number}) "
            f"for {collection_id}"
        )
        
        return batch
    
    async def _add_video_to_batch(
        self,
        batch: BatchProcessingState,
        event: VideoCompletionEvent
    ):
        """
        Add video to batch.
        
        Args:
            batch: Batch to add video to
            event: Video completion event
        """
        # Get next sequence number
        sequence = await self.repository.get_next_sequence_number(batch.batch_uuid)
        
        # Create assignment
        assignment = BatchVideoAssignment(
            batch_uuid=batch.batch_uuid,
            video_uuid=event.video_uuid,
            collection_id=event.collection_id,
            video_start_time=event.video_start_time,
            video_end_time=event.video_end_time,
            sequence_number=sequence,
            face_detection_session_uuid=event.face_detection_session_uuid
        )
        
        await self.repository.assign_video_to_batch(assignment)
        
        logger.debug(
            f"Added video {event.video_uuid} to batch {batch.batch_uuid} "
            f"(sequence {sequence})"
        )
    
    async def _update_batch_after_video(
        self,
        batch: BatchProcessingState
    ) -> BatchProcessingState:
        """
        Update batch state after adding video.
        
        Args:
            batch: Batch to update
            
        Returns:
            Updated batch
        """
        updates = {
            'video_count': batch.video_count + 1,
            'last_video_time': datetime.utcnow()
        }
        
        updated = await self.repository.update_batch(batch.batch_uuid, **updates)
        
        if not updated:
            raise BatchMonitorError(f"Failed to update batch {batch.batch_uuid}")
        
        return updated
    
    async def _should_trigger_batch(
        self,
        batch: BatchProcessingState
    ) -> bool:
        """
        Check if batch should be triggered for processing.
        
        Args:
            batch: Batch to check
            
        Returns:
            True if batch should be triggered
        """
        # Check if full batch size reached
        return batch.video_count >= batch.batch_size_threshold
    
    async def _update_batch_timeout(
        self,
        batch: BatchProcessingState
    ):
        """
        Update batch timeout after adding video.
        
        Args:
            batch: Batch to update
        """
        # Get configuration
        config = await self.config_service.get_collection_config(
            batch.collection_id
        )
        
        # Calculate new timeout
        new_timeout = self.config_service.calculate_timeout(
            config,
            batch.last_video_time
        )
        
        # Update if timeout enabled
        if config.enable_timeout_fallback:
            await self.repository.update_batch(
                batch.batch_uuid,
                timeout_at=new_timeout
            )
    
    async def _trigger_batch_processing(
        self,
        batch: BatchProcessingState,
        trigger_reason: TriggerReason,
        is_partial: bool = False
    ) -> BatchTriggerResponse:
        """
        Trigger batch processing.
        
        Args:
            batch: Batch to process
            trigger_reason: Reason for triggering
            is_partial: Whether this is a partial batch
            
        Returns:
            Trigger response
        """
        logger.info(
            f"Triggering batch {batch.batch_uuid} "
            f"(reason: {trigger_reason.value}, "
            f"videos: {batch.video_count}, "
            f"partial: {is_partial})"
        )
        
        # Update batch status
        updates = {
            'status': BatchStatus.PROCESSING,
            'trigger_reason': trigger_reason,
            'is_partial_batch': is_partial,
            'processing_started_at': datetime.utcnow()
        }
        
        await self.repository.update_batch(batch.batch_uuid, **updates)
        
        # Remove from active batches cache
        self._active_batches.pop(batch.collection_id, None)
        
        # Update statistics
        self._stats['batches_triggered'] += 1
        if is_partial:
            self._stats['partial_batches'] += 1
        else:
            self._stats['full_batches'] += 1
        
        # Call batch processor callback if provided
        if self.batch_processor_callback:
            try:
                # Call asynchronously without waiting
                asyncio.create_task(
                    self.batch_processor_callback(batch.batch_uuid)
                )
            except Exception as e:
                logger.error(f"Batch processor callback failed: {e}")
        
        # Return response
        return BatchTriggerResponse(
            batch_uuid=batch.batch_uuid,
            collection_id=batch.collection_id,
            trigger_reason=trigger_reason,
            video_count=batch.video_count,
            is_partial_batch=is_partial,
            triggered_at=datetime.utcnow()
        )
    
    async def get_active_batches(self) -> List[BatchProcessingState]:
        """
        Get all active (accumulating) batches.
        
        Returns:
            List of active batches
        """
        try:
            # Get from database
            batches = []
            for collection_id in self._active_batches.keys():
                batch = await self.repository.get_active_batch(collection_id)
                if batch:
                    batches.append(batch)
            
            return batches
            
        except Exception as e:
            logger.error(f"Failed to get active batches: {e}")
            return []
    
    async def get_batch_status(
        self,
        batch_uuid: UUID
    ) -> Optional[BatchProcessingState]:
        """
        Get current batch status.
        
        Args:
            batch_uuid: Batch identifier
            
        Returns:
            Batch state or None if not found
        """
        return await self.repository.get_batch(batch_uuid)
    
    async def force_trigger_batch(
        self,
        collection_id: str,
        reason: str = "Manual trigger"
    ) -> Optional[BatchTriggerResponse]:
        """
        Force trigger batch processing for collection.
        
        Admin/debug function to manually trigger processing.
        
        Args:
            collection_id: Collection identifier
            reason: Reason for manual trigger
            
        Returns:
            Trigger response or None if no active batch
        """
        lock = self._get_collection_lock(collection_id)
        
        async with lock:
            try:
                batch = await self.repository.get_active_batch(collection_id)
                
                if not batch:
                    logger.warning(f"No active batch for {collection_id}")
                    return None
                
                if batch.video_count == 0:
                    logger.warning(f"Batch {batch.batch_uuid} has no videos")
                    return None
                
                logger.info(
                    f"Force triggering batch {batch.batch_uuid} "
                    f"for {collection_id}: {reason}"
                )
                
                return await self._trigger_batch_processing(
                    batch,
                    TriggerReason.MANUAL_TRIGGER,
                    is_partial=batch.video_count < batch.batch_size_threshold
                )
                
            except Exception as e:
                logger.error(f"Failed to force trigger batch: {e}")
                raise BatchMonitorError(f"Force trigger failed: {e}")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get batch monitoring statistics.
        
        Returns:
            Statistics dictionary
        """
        return self._stats.copy()
    
    async def cleanup_stale_batches(self, max_age_hours: int = 48):
        """
        Clean up stale batches that are stuck in accumulating state.
        
        Args:
            max_age_hours: Maximum age before considering batch stale
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # This would require a new repository method
            # For now, just clear the cache
            stale_collections = []
            
            for collection_id, batch_uuid in self._active_batches.items():
                batch = await self.repository.get_batch(batch_uuid)
                if not batch or batch.created_at < cutoff:
                    stale_collections.append(collection_id)
            
            for collection_id in stale_collections:
                del self._active_batches[collection_id]
                logger.info(f"Cleaned up stale batch for {collection_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale batches: {e}")
