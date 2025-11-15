"""
Batch Processing Repository
PPL Meta Platform - Continuous Individuals and MVR Pipeline

PostgreSQL repository for batch processing operations including CRUD
for batch state, video assignments, history, and configuration.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncpg

from models.batch_processing import (
    BatchProcessingState,
    BatchProcessingConfig,
    BatchVideoAssignment,
    BatchProcessingHistory,
    BatchStatus,
    TriggerReason,
    BatchVideoSummary,
    BatchStatistics
)

logger = logging.getLogger(__name__)


class BatchRepositoryError(Exception):
    """Custom exception for batch repository operations."""
    pass


class BatchProcessingRepository:
    """
    Repository for batch processing database operations.
    
    Provides CRUD operations for:
    - batch_processing_state
    - batch_video_assignments
    - batch_processing_history
    - batch_processing_config
    """
    
    def __init__(self, connection_pool: asyncpg.Pool):
        """
        Initialize repository with connection pool.
        
        Args:
            connection_pool: AsyncPG connection pool
        """
        self.pool = connection_pool
        logger.info("BatchProcessingRepository initialized")
    
    async def _execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def _fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def _fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    # =============================================
    # BATCH STATE OPERATIONS
    # =============================================
    
    async def create_batch(
        self,
        batch: BatchProcessingState
    ) -> BatchProcessingState:
        """
        Create new batch processing state.
        
        Args:
            batch: Batch state to create
            
        Returns:
            Created batch state
            
        Raises:
            BatchRepositoryError: If creation fails
        """
        try:
            query = """
                INSERT INTO batch_processing_state (
                    batch_uuid, collection_id, batch_number,
                    status, video_count, batch_size_threshold,
                    is_partial_batch, trigger_reason,
                    last_video_time, timeout_at,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW()
                )
                RETURNING *
            """
            
            row = await self._fetch_one(
                query,
                batch.batch_uuid,
                batch.collection_id,
                batch.batch_number,
                batch.status.value,
                batch.video_count,
                batch.batch_size_threshold,
                batch.is_partial_batch,
                batch.trigger_reason.value if batch.trigger_reason else None,
                batch.last_video_time,
                batch.timeout_at
            )
            
            if not row:
                raise BatchRepositoryError("Failed to create batch")
            
            logger.info(f"Created batch {batch.batch_uuid} for {batch.collection_id}")
            return BatchProcessingState(**row)
        
        except Exception as e:
            logger.error(f"Failed to create batch: {e}")
            raise BatchRepositoryError(f"Batch creation failed: {e}")
    
    async def get_batch(
        self,
        batch_uuid: UUID
    ) -> Optional[BatchProcessingState]:
        """
        Get batch by UUID.
        
        Args:
            batch_uuid: Batch identifier
            
        Returns:
            Batch state or None if not found
        """
        try:
            row = await self._fetch_one(
                "SELECT * FROM batch_processing_state WHERE batch_uuid = $1",
                batch_uuid
            )
            
            return BatchProcessingState(**row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get batch {batch_uuid}: {e}")
            raise BatchRepositoryError(f"Failed to get batch: {e}")
    
    async def get_active_batch(
        self,
        collection_id: str
    ) -> Optional[BatchProcessingState]:
        """
        Get active (accumulating) batch for collection.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Active batch or None if no active batch exists
        """
        try:
            row = await self._fetch_one(
                """
                SELECT * FROM batch_processing_state
                WHERE collection_id = $1 AND status = 'accumulating'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                collection_id
            )
            
            return BatchProcessingState(**row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get active batch for {collection_id}: {e}")
            raise BatchRepositoryError(f"Failed to get active batch: {e}")
    
    async def update_batch(
        self,
        batch_uuid: UUID,
        **updates
    ) -> Optional[BatchProcessingState]:
        """
        Update batch state.
        
        Args:
            batch_uuid: Batch to update
            **updates: Fields to update
            
        Returns:
            Updated batch state or None if not found
        """
        if not updates:
            return await self.get_batch(batch_uuid)
        
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_idx = 2  # $1 is batch_uuid
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ${param_idx}")
                # Convert enums to values
                if isinstance(value, (BatchStatus, TriggerReason)):
                    values.append(value.value)
                else:
                    values.append(value)
                param_idx += 1
            
            # Always update updated_at
            set_clauses.append(f"updated_at = NOW()")
            
            query = f"""
                UPDATE batch_processing_state
                SET {', '.join(set_clauses)}
                WHERE batch_uuid = $1
                RETURNING *
            """
            
            row = await self._fetch_one(query, batch_uuid, *values)
            
            if row:
                logger.debug(f"Updated batch {batch_uuid}")
                return BatchProcessingState(**row)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to update batch {batch_uuid}: {e}")
            raise BatchRepositoryError(f"Batch update failed: {e}")
    
    async def delete_batch(self, batch_uuid: UUID) -> bool:
        """
        Delete batch (CASCADE deletes video assignments).
        
        Args:
            batch_uuid: Batch to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self._execute(
                "DELETE FROM batch_processing_state WHERE batch_uuid = $1",
                batch_uuid
            )
            
            deleted = result.split()[1] == '1'
            if deleted:
                logger.info(f"Deleted batch {batch_uuid}")
            
            return deleted
        
        except Exception as e:
            logger.error(f"Failed to delete batch {batch_uuid}: {e}")
            raise BatchRepositoryError(f"Batch deletion failed: {e}")
    
    async def get_timeout_batches(self) -> List[BatchProcessingState]:
        """
        Get batches that have reached timeout.
        
        Returns:
            List of batches past their timeout
        """
        try:
            rows = await self._fetch_all(
                """
                SELECT * FROM batch_processing_state
                WHERE status = 'accumulating'
                  AND timeout_at IS NOT NULL
                  AND timeout_at <= NOW()
                ORDER BY timeout_at ASC
                """
            )
            
            return [BatchProcessingState(**row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get timeout batches: {e}")
            raise BatchRepositoryError(f"Failed to get timeout batches: {e}")
    
    async def get_next_batch_number(self, collection_id: str) -> int:
        """
        Get next batch number for collection.
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Next sequential batch number
        """
        try:
            row = await self._fetch_one(
                "SELECT get_next_batch_number($1) as batch_number",
                collection_id
            )
            
            return row['batch_number'] if row else 1
        
        except Exception as e:
            logger.error(f"Failed to get next batch number: {e}")
            raise BatchRepositoryError(f"Failed to get next batch number: {e}")
    
    # =============================================
    # VIDEO ASSIGNMENT OPERATIONS
    # =============================================
    
    async def assign_video_to_batch(
        self,
        assignment: BatchVideoAssignment
    ) -> BatchVideoAssignment:
        """
        Assign video to batch.
        
        Args:
            assignment: Video assignment details
            
        Returns:
            Created assignment
        """
        try:
            query = """
                INSERT INTO batch_video_assignments (
                    batch_uuid, video_uuid, collection_id,
                    video_start_time, video_end_time,
                    sequence_number, face_detection_session_uuid,
                    assigned_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, NOW()
                )
                RETURNING *
            """
            
            row = await self._fetch_one(
                query,
                assignment.batch_uuid,
                assignment.video_uuid,
                assignment.collection_id,
                assignment.video_start_time,
                assignment.video_end_time,
                assignment.sequence_number,
                assignment.face_detection_session_uuid
            )
            
            if not row:
                raise BatchRepositoryError("Failed to assign video")
            
            logger.debug(f"Assigned video {assignment.video_uuid} to batch {assignment.batch_uuid}")
            return BatchVideoAssignment(**row)
        
        except Exception as e:
            logger.error(f"Failed to assign video: {e}")
            raise BatchRepositoryError(f"Video assignment failed: {e}")
    
    async def get_batch_videos(
        self,
        batch_uuid: UUID
    ) -> List[BatchVideoAssignment]:
        """
        Get all videos assigned to batch.
        
        Args:
            batch_uuid: Batch identifier
            
        Returns:
            List of video assignments
        """
        try:
            rows = await self._fetch_all(
                """
                SELECT * FROM batch_video_assignments
                WHERE batch_uuid = $1
                ORDER BY sequence_number ASC
                """,
                batch_uuid
            )
            
            return [BatchVideoAssignment(**row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get batch videos: {e}")
            raise BatchRepositoryError(f"Failed to get batch videos: {e}")
    
    async def is_video_in_batch(
        self,
        video_uuid: UUID,
        batch_uuid: UUID
    ) -> bool:
        """
        Check if video is assigned to batch.
        
        Args:
            video_uuid: Video identifier
            batch_uuid: Batch identifier
            
        Returns:
            True if video is in batch
        """
        try:
            row = await self._fetch_one(
                "SELECT is_video_in_batch($1, $2) as exists",
                video_uuid,
                batch_uuid
            )
            
            return row['exists'] if row else False
        
        except Exception as e:
            logger.error(f"Failed to check video in batch: {e}")
            return False
    
    async def get_next_sequence_number(self, batch_uuid: UUID) -> int:
        """
        Get next sequence number for batch.
        
        Args:
            batch_uuid: Batch identifier
            
        Returns:
            Next sequence number
        """
        try:
            row = await self._fetch_one(
                "SELECT get_next_sequence_number($1) as seq",
                batch_uuid
            )
            
            return row['seq'] if row else 1
        
        except Exception as e:
            logger.error(f"Failed to get next sequence: {e}")
            return 1
    
    async def get_batch_video_summary(
        self,
        batch_uuid: UUID
    ) -> Optional[BatchVideoSummary]:
        """
        Get summary of videos in batch.
        
        Args:
            batch_uuid: Batch identifier
            
        Returns:
            Video summary or None
        """
        try:
            row = await self._fetch_one(
                """
                SELECT * FROM batch_video_summary
                WHERE batch_uuid = $1
                """,
                batch_uuid
            )
            
            return BatchVideoSummary(**row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get batch summary: {e}")
            return None
    
    # =============================================
    # HISTORY OPERATIONS
    # =============================================
    
    async def archive_batch(
        self,
        batch_uuid: UUID
    ) -> bool:
        """
        Archive completed batch to history.
        
        Args:
            batch_uuid: Batch to archive
            
        Returns:
            True if archived successfully
        """
        try:
            row = await self._fetch_one(
                "SELECT archive_batch_to_history($1) as success",
                batch_uuid
            )
            
            success = row['success'] if row else False
            if success:
                logger.info(f"Archived batch {batch_uuid} to history")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to archive batch: {e}")
            raise BatchRepositoryError(f"Batch archival failed: {e}")
    
    async def get_batch_history(
        self,
        collection_id: Optional[str] = None,
        limit: int = 100
    ) -> List[BatchProcessingHistory]:
        """
        Get batch processing history.
        
        Args:
            collection_id: Filter by collection (None for all)
            limit: Maximum number of records
            
        Returns:
            List of historical batch records
        """
        try:
            if collection_id:
                rows = await self._fetch_all(
                    """
                    SELECT * FROM batch_processing_history
                    WHERE collection_id = $1
                    ORDER BY processing_completed_at DESC
                    LIMIT $2
                    """,
                    collection_id,
                    limit
                )
            else:
                rows = await self._fetch_all(
                    """
                    SELECT * FROM batch_processing_history
                    ORDER BY processing_completed_at DESC
                    LIMIT $1
                    """,
                    limit
                )
            
            return [BatchProcessingHistory(**row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get batch history: {e}")
            raise BatchRepositoryError(f"Failed to get batch history: {e}")
    
    async def get_collection_stats(
        self,
        collection_id: str,
        limit: int = 10
    ) -> Optional[BatchStatistics]:
        """
        Get aggregated statistics for collection.
        
        Args:
            collection_id: Collection identifier
            limit: Number of recent batches to analyze
            
        Returns:
            Batch statistics or None
        """
        try:
            row = await self._fetch_one(
                "SELECT * FROM get_collection_batch_stats($1, $2)",
                collection_id,
                limit
            )
            
            return BatchStatistics(**row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return None
    
    # =============================================
    # CONFIGURATION OPERATIONS
    # =============================================
    
    async def get_config(
        self,
        collection_id: Optional[str] = None
    ) -> Optional[BatchProcessingConfig]:
        """
        Get batch processing configuration.
        
        Args:
            collection_id: Collection ID or None for global
            
        Returns:
            Configuration or None
        """
        try:
            if collection_id:
                row = await self._fetch_one(
                    """
                    SELECT * FROM batch_processing_config
                    WHERE collection_id = $1
                    """,
                    collection_id
                )
            else:
                row = await self._fetch_one(
                    """
                    SELECT * FROM batch_processing_config
                    WHERE collection_id IS NULL
                    """
                )
            
            return BatchProcessingConfig(**row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return None
    
    async def get_effective_config(
        self,
        collection_id: str
    ) -> Optional[BatchProcessingConfig]:
        """
        Get effective configuration (collection or global).
        
        Args:
            collection_id: Collection identifier
            
        Returns:
            Effective configuration
        """
        try:
            row = await self._fetch_one(
                "SELECT * FROM get_batch_processing_config($1)",
                collection_id
            )
            
            return BatchProcessingConfig(**row) if row else None
        
        except Exception as e:
            logger.error(f"Failed to get effective config: {e}")
            return None
    
    # =============================================
    # PARTIAL BATCH OPERATIONS
    # =============================================
    
    async def update_batch_timeout(
        self,
        batch_uuid: UUID,
        timeout_at: datetime,
        last_video_time: Optional[datetime] = None
    ) -> bool:
        """
        Update batch timeout tracking fields.
        
        Args:
            batch_uuid: Batch to update
            timeout_at: When timeout should trigger
            last_video_time: Time of last video added (optional)
            
        Returns:
            True if updated successfully
        """
        try:
            if last_video_time:
                query = """
                    UPDATE batch_processing_state
                    SET timeout_at = $2,
                        last_video_time = $3,
                        updated_at = NOW()
                    WHERE batch_uuid = $1
                """
                result = await self._execute(
                    query,
                    batch_uuid,
                    timeout_at,
                    last_video_time
                )
            else:
                query = """
                    UPDATE batch_processing_state
                    SET timeout_at = $2,
                        updated_at = NOW()
                    WHERE batch_uuid = $1
                """
                result = await self._execute(
                    query,
                    batch_uuid,
                    timeout_at
                )
            
            logger.debug(f"Updated timeout for batch {batch_uuid} to {timeout_at}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update batch timeout: {e}")
            return False
    
    async def mark_batch_as_partial(
        self,
        batch_uuid: UUID,
        trigger_reason: TriggerReason
    ) -> bool:
        """
        Mark batch as partial batch with trigger reason.
        
        Args:
            batch_uuid: Batch to mark
            trigger_reason: Why batch was triggered
            
        Returns:
            True if marked successfully
        """
        try:
            query = """
                UPDATE batch_processing_state
                SET is_partial_batch = TRUE,
                    trigger_reason = $2,
                    triggered_at = NOW(),
                    updated_at = NOW()
                WHERE batch_uuid = $1
            """
            
            await self._execute(
                query,
                batch_uuid,
                trigger_reason.value
            )
            
            logger.info(
                f"Marked batch {batch_uuid} as partial with reason: {trigger_reason.value}"
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark batch as partial: {e}")
            return False
    
    async def get_partial_batches(
        self,
        collection_id: Optional[str] = None,
        limit: int = 50
    ) -> List[BatchProcessingState]:
        """
        Get partial batches for analysis.
        
        Args:
            collection_id: Filter by collection (optional)
            limit: Maximum results
            
        Returns:
            List of partial batches
        """
        try:
            if collection_id:
                query = """
                    SELECT * FROM batch_processing_state
                    WHERE is_partial_batch = TRUE
                      AND collection_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                rows = await self._fetch_all(query, collection_id, limit)
            else:
                query = """
                    SELECT * FROM batch_processing_state
                    WHERE is_partial_batch = TRUE
                    ORDER BY created_at DESC
                    LIMIT $1
                """
                rows = await self._fetch_all(query, limit)
            
            return [BatchProcessingState(**row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get partial batches: {e}")
            raise BatchRepositoryError(f"Failed to get partial batches: {e}")
    
    async def get_incomplete_batches(
        self,
        collection_id: Optional[str] = None
    ) -> List[BatchProcessingState]:
        """
        Get incomplete batches that haven't been processed.
        
        Args:
            collection_id: Filter by collection (optional)
            
        Returns:
            List of incomplete batches
        """
        try:
            if collection_id:
                query = """
                    SELECT * FROM batch_processing_state
                    WHERE status = 'incomplete'
                      AND collection_id = $1
                    ORDER BY created_at DESC
                """
                rows = await self._fetch_all(query, collection_id)
            else:
                query = """
                    SELECT * FROM batch_processing_state
                    WHERE status = 'incomplete'
                    ORDER BY created_at DESC
                """
                rows = await self._fetch_all(query)
            
            return [BatchProcessingState(**row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get incomplete batches: {e}")
            raise BatchRepositoryError(f"Failed to get incomplete batches: {e}")
