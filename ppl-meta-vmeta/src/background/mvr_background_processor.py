"""
MVR-People Background Processor

Handles automatic MVR-People creation and matching in the background
when new Individuals are created.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from services.mvr_matcher import MVRMatcher
from services.mvr_service import MVRService

logger = logging.getLogger(__name__)


class MVRBackgroundProcessor:
    """
    Background processor for automatic MVR-People creation and matching.
    
    This class manages the background processing pipeline:
    1. Automatic MVR-People creation when Individual is created
    2. Automatic matching against existing MVR-People
    3. Automatic merging if high-confidence match found
    4. Error handling and retry logic
    """
    
    def __init__(
        self,
        mvr_service: MVRService,
        mvr_matcher: MVRMatcher,
        hierarchical_scheduler: Optional['HierarchicalMergeScheduler'] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0
    ):
        """
        Initialize background processor.
        
        Args:
            mvr_service: MVRService instance for creating MVR-People
            mvr_matcher: MVRMatcher instance for matching and merging
            hierarchical_scheduler: Optional hierarchical merge scheduler (Queue C)
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.mvr_service = mvr_service
        self.mvr_matcher = mvr_matcher
        self.hierarchical_scheduler = hierarchical_scheduler
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Task tracking
        self._pending_tasks: Dict[UUID, asyncio.Task] = {}
        self._completed_tasks: Dict[UUID, Dict] = {}
        self._failed_tasks: Dict[UUID, Dict] = {}
        
        logger.info(
            f"✅ MVRBackgroundProcessor initialized "
            f"(max_retries={max_retries}, retry_delay={retry_delay}s, "
            f"hierarchical_scheduler={'enabled' if hierarchical_scheduler else 'disabled'})"
        )
    
    async def process_new_individual(
        self,
        individual_uuid: UUID,
        session_uuid: Optional[UUID] = None,
        auto_match: bool = True
    ) -> Dict:
        """
        Process new Individual in background (non-blocking).
        
        This is the main entry point called when a new Individual is created.
        It creates a background task that:
        1. Creates MVR-People from Individual
        2. Optionally matches against existing MVR-People
        3. Optionally merges if match found
        
        Args:
            individual_uuid: UUID of newly created Individual
            session_uuid: Optional session UUID for context
            auto_match: Whether to automatically match and merge
        
        Returns:
            Task status dict with task_id
        """
        # Create background task
        task = asyncio.create_task(
            self._process_individual_pipeline(
                individual_uuid=individual_uuid,
                session_uuid=session_uuid,
                auto_match=auto_match
            )
        )
        
        # Track task
        self._pending_tasks[individual_uuid] = task
        
        logger.info(
            f"🔄 Started background processing for Individual {individual_uuid} "
            f"(auto_match={auto_match})"
        )
        
        return {
            "task_id": str(individual_uuid),
            "status": "processing",
            "started_at": datetime.utcnow().isoformat(),
            "auto_match": auto_match
        }
    
    async def _process_individual_pipeline(
        self,
        individual_uuid: UUID,
        session_uuid: Optional[UUID],
        auto_match: bool
    ) -> None:
        """
        Internal pipeline for processing Individual with retries.
        
        Pipeline stages:
        1. Create MVR-People from Individual
        2. If auto_match enabled: Find and merge if match exists
        3. Log results
        4. Update task tracking
        """
        start_time = datetime.utcnow()
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                logger.info(
                    f"🔄 Processing Individual {individual_uuid} "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1})"
                )
                
                # Stage 1: Create MVR-People
                mvr_data = await self._create_mvr_with_retry(
                    individual_uuid=individual_uuid,
                    session_uuid=session_uuid
                )
                
                if not mvr_data:
                    raise Exception("Failed to create MVR-People")
                
                mvr_uuid = mvr_data.get("mvr_people_uuid")
                logger.info(
                    f"✅ Created MVR-People {mvr_uuid} for Individual {individual_uuid}"
                )
                
                # Stage 2: Match and merge if enabled
                merge_result = None
                if auto_match:
                    merge_result = await self._match_and_merge_with_retry(
                        individual_uuid=individual_uuid
                    )
                    
                    if merge_result and merge_result.get("merged"):
                        logger.info(
                            f"✅ Merged Individual {individual_uuid} "
                            f"(winner={merge_result.get('winner_mvr_uuid')}, "
                            f"similarity={merge_result.get('similarity_score', 0):.3f})"
                        )
                    elif merge_result and merge_result.get("matched"):
                        logger.info(
                            f"ℹ️ Match found for Individual {individual_uuid} "
                            f"but below merge threshold "
                            f"(similarity={merge_result.get('similarity_score', 0):.3f})"
                        )
                    else:
                        logger.info(
                            f"ℹ️ No match found for Individual {individual_uuid} "
                            "(new unique person)"
                        )
                
                # Stage 3: Mark success
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                self._completed_tasks[individual_uuid] = {
                    "individual_uuid": str(individual_uuid),
                    "mvr_uuid": str(mvr_uuid),
                    "merge_result": merge_result,
                    "processing_time_seconds": processing_time,
                    "retry_count": retry_count,
                    "completed_at": end_time.isoformat()
                }
                
                # Remove from pending
                if individual_uuid in self._pending_tasks:
                    del self._pending_tasks[individual_uuid]
                
                logger.info(
                    f"✅ Background processing completed for Individual {individual_uuid} "
                    f"in {processing_time:.2f}s (retries={retry_count})"
                )
                return
                
            except Exception as e:
                retry_count += 1
                
                if retry_count > self.max_retries:
                    # Max retries reached - mark as failed
                    logger.error(
                        f"❌ Background processing failed for Individual {individual_uuid} "
                        f"after {self.max_retries} retries: {e}"
                    )
                    
                    self._failed_tasks[individual_uuid] = {
                        "individual_uuid": str(individual_uuid),
                        "error": str(e),
                        "retry_count": retry_count - 1,
                        "failed_at": datetime.utcnow().isoformat()
                    }
                    
                    # Remove from pending
                    if individual_uuid in self._pending_tasks:
                        del self._pending_tasks[individual_uuid]
                    
                    return
                else:
                    # Retry with delay
                    logger.warning(
                        f"⚠️ Retry {retry_count}/{self.max_retries} for Individual {individual_uuid} "
                        f"after error: {e}"
                    )
                    await asyncio.sleep(self.retry_delay)
    
    async def _create_mvr_with_retry(
        self,
        individual_uuid: UUID,
        session_uuid: Optional[UUID]
    ) -> Optional[Dict]:
        """
        Create MVR-People with error handling.
        
        Args:
            individual_uuid: Individual UUID
            session_uuid: Optional session UUID
        
        Returns:
            MVR data dict or None if failed
        """
        try:
            mvr_data = await self.mvr_service.create_mvr_people_from_individual(
                individual_uuid=individual_uuid,
                session_uuid=session_uuid
            )
            return mvr_data
        except Exception as e:
            logger.error(f"❌ Failed to create MVR for Individual {individual_uuid}: {e}")
            raise
    
    async def _match_and_merge_with_retry(
        self,
        individual_uuid: UUID
    ) -> Optional[Dict]:
        """
        Match and merge with error handling.
        
        Args:
            individual_uuid: Individual UUID
        
        Returns:
            Merge result dict or None if failed
        """
        try:
            merge_result = await self.mvr_matcher.find_and_merge_if_match(
                individual_uuid=individual_uuid
            )
            return merge_result
        except Exception as e:
            logger.error(
                f"❌ Failed to match/merge Individual {individual_uuid}: {e}"
            )
            raise
    
    async def get_task_status(self, individual_uuid: UUID) -> Dict:
        """
        Get status of background processing task.
        
        Args:
            individual_uuid: Individual UUID
        
        Returns:
            Task status dict
        """
        # Check if pending
        if individual_uuid in self._pending_tasks:
            task = self._pending_tasks[individual_uuid]
            return {
                "task_id": str(individual_uuid),
                "status": "processing",
                "done": task.done()
            }
        
        # Check if completed
        if individual_uuid in self._completed_tasks:
            result = self._completed_tasks[individual_uuid]
            return {
                "task_id": str(individual_uuid),
                "status": "completed",
                **result
            }
        
        # Check if failed
        if individual_uuid in self._failed_tasks:
            result = self._failed_tasks[individual_uuid]
            return {
                "task_id": str(individual_uuid),
                "status": "failed",
                **result
            }
        
        # Not found
        return {
            "task_id": str(individual_uuid),
            "status": "not_found"
        }
    
    async def get_all_pending_tasks(self) -> Dict:
        """
        Get all pending background tasks.
        
        Returns:
            Dict with pending task count and task IDs
        """
        return {
            "pending_count": len(self._pending_tasks),
            "task_ids": [str(uuid) for uuid in self._pending_tasks.keys()]
        }
    
    async def get_statistics(self) -> Dict:
        """
        Get background processing statistics.
        
        Returns:
            Statistics dict with counts and metrics
        """
        completed_count = len(self._completed_tasks)
        failed_count = len(self._failed_tasks)
        pending_count = len(self._pending_tasks)
        
        # Calculate success rate
        total_finished = completed_count + failed_count
        success_rate = (
            (completed_count / total_finished * 100) if total_finished > 0 else 0.0
        )
        
        # Calculate average processing time
        avg_processing_time = 0.0
        if completed_count > 0:
            total_time = sum(
                task.get("processing_time_seconds", 0)
                for task in self._completed_tasks.values()
            )
            avg_processing_time = total_time / completed_count
        
        # Count merged tasks
        merged_count = sum(
            1 for task in self._completed_tasks.values()
            if task.get("merge_result", {}).get("merged", False)
        )
        
        return {
            "pending": pending_count,
            "completed": completed_count,
            "failed": failed_count,
            "success_rate_percent": round(success_rate, 2),
            "average_processing_time_seconds": round(avg_processing_time, 2),
            "merged_count": merged_count,
            "unique_individuals_count": completed_count - merged_count
        }
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed tasks from memory.
        
        Args:
            max_age_hours: Maximum age in hours to keep tasks
        
        Returns:
            Number of tasks cleaned up
        """
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        # Clean completed tasks
        to_remove = []
        for uuid, task in self._completed_tasks.items():
            completed_at = datetime.fromisoformat(task["completed_at"])
            if completed_at < cutoff_time:
                to_remove.append(uuid)
        
        for uuid in to_remove:
            del self._completed_tasks[uuid]
            cleaned_count += 1
        
        # Clean failed tasks
        to_remove = []
        for uuid, task in self._failed_tasks.items():
            failed_at = datetime.fromisoformat(task["failed_at"])
            if failed_at < cutoff_time:
                to_remove.append(uuid)
        
        for uuid in to_remove:
            del self._failed_tasks[uuid]
            cleaned_count += 1
        
        logger.info(
            f"🧹 Cleaned up {cleaned_count} old tasks "
            f"(older than {max_age_hours} hours)"
        )
        
        return cleaned_count
    
    # ========================================================================
    # SESSION-LEVEL MVR PROCESSING (Queue B)
    # ========================================================================
    
    async def queue_session_mvr_creation(
        self,
        session_uuid: UUID,
        individual_uuids: List[UUID],
        auth_token: Optional[str] = None,
        similarity_threshold: float = 0.70
    ) -> Dict:
        """
        Queue MVR creation for all individuals in a tracking session.
        
        This is Queue B in the three-queue architecture. It decouples MVR
        creation from video discovery/individual creation, allowing:
        - Independent retry on failure
        - Processing even if individuals created later
        - Non-blocking session completion
        
        Args:
            session_uuid: Tracking session UUID
            individual_uuids: List of individual UUIDs to process
            auth_token: Optional auth token for API calls
            similarity_threshold: Similarity threshold for merging (default 0.70)
        
        Returns:
            Task status dict with task_id and queued count
        """
        # Create background task
        task = asyncio.create_task(
            self._process_session_mvr_pipeline(
                session_uuid=session_uuid,
                individual_uuids=individual_uuids,
                auth_token=auth_token,
                similarity_threshold=similarity_threshold
            )
        )
        
        # Track task by session UUID
        self._pending_tasks[session_uuid] = task
        
        logger.info(
            f"🔄 [Queue B] Started MVR creation for session {session_uuid} "
            f"({len(individual_uuids)} individuals, threshold={similarity_threshold})"
        )
        
        return {
            "task_id": str(session_uuid),
            "status": "queued",
            "individual_count": len(individual_uuids),
            "queued_at": datetime.utcnow().isoformat()
        }
    
    async def _process_session_mvr_pipeline(
        self,
        session_uuid: UUID,
        individual_uuids: List[UUID],
        auth_token: Optional[str],
        similarity_threshold: float
    ) -> None:
        """
        Internal pipeline for session-level MVR creation with retries.
        
        Pipeline stages:
        1. Fetch individual data from database (with person_objects)
        2. Call merge_individuals_by_similarity (existing function)
        3. Update session MVR status
        4. Queue hierarchical merge (Queue C) if configured
        """
        start_time = datetime.utcnow()
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                logger.info(
                    f"🔄 [Queue B] Processing session {session_uuid} MVR creation "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1})"
                )
                
                # Stage 1: Fetch individuals with person_objects from DB
                matched_individuals = await self._fetch_session_individuals(
                    session_uuid=session_uuid,
                    individual_uuids=individual_uuids
                )
                
                if not matched_individuals:
                    raise Exception("No individuals found for session")
                
                logger.info(
                    f"✅ [Queue B] Fetched {len(matched_individuals)} individuals "
                    f"from session {session_uuid}"
                )
                
                # Stage 2: Run embedding-based merge
                from api.v1.cross_video_tracking_simple import merge_individuals_by_similarity, get_database_client
                
                db_client = get_database_client()
                
                merged_count = await merge_individuals_by_similarity(
                    db_client=db_client,
                    session_uuid=session_uuid,
                    matched_individuals=matched_individuals,
                    auth_token=auth_token,
                    similarity_threshold=similarity_threshold
                )
                
                logger.info(
                    f"✅ [Queue B] MVR creation complete for session {session_uuid}: "
                    f"{len(matched_individuals)} individuals → "
                    f"{len(matched_individuals) - merged_count} MVR people"
                )
                
                # Stage 3: Update session MVR status
                await self._update_session_mvr_status(
                    session_uuid=session_uuid,
                    status="mvr_complete",
                    mvr_count=len(matched_individuals) - merged_count
                )
                
                # Stage 4: Queue hierarchical merge (Queue C) if scheduler available
                created_mvr_uuids = []
                if self.hierarchical_scheduler:
                    try:
                        # Get MVR UUIDs created in this session
                        from api.v1.cross_video_tracking_simple import get_database_client
                        db_client = get_database_client()
                        
                        async with db_client.pool.acquire() as conn:
                            rows = await conn.fetch("""
                                SELECT DISTINCT mvr_people_uuid
                                FROM individual_mvr_mapping
                                WHERE individual_uuid IN (
                                    SELECT individual_uuid
                                    FROM session_individuals
                                    WHERE session_uuid = $1
                                )
                            """, session_uuid)
                        
                        created_mvr_uuids = [row['mvr_people_uuid'] for row in rows]
                        
                        if created_mvr_uuids:
                            # Queue hierarchical merge
                            queue_result = await self.hierarchical_scheduler.queue_post_session_merge(
                                session_uuid=session_uuid,
                                mvr_uuids=created_mvr_uuids
                            )
                            
                            logger.info(
                                f"✅ [Queue B→C] Hierarchical merge queued for session {session_uuid}: "
                                f"{len(created_mvr_uuids)} MVR people, "
                                f"task_id={queue_result.get('task_id')}"
                            )
                    except Exception as queue_error:
                        logger.warning(
                            f"⚠️ [Queue B→C] Failed to queue hierarchical merge "
                            f"for session {session_uuid}: {queue_error}"
                        )
                        # Don't fail the entire pipeline if Queue C fails
                
                # Stage 5: Mark success
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                self._completed_tasks[session_uuid] = {
                    "session_uuid": str(session_uuid),
                    "individual_count": len(matched_individuals),
                    "mvr_count": len(matched_individuals) - merged_count,
                    "merged_count": merged_count,
                    "hierarchical_merge_queued": len(created_mvr_uuids) > 0,
                    "processing_time_seconds": processing_time,
                    "retry_count": retry_count,
                    "completed_at": end_time.isoformat()
                }
                
                # Remove from pending
                if session_uuid in self._pending_tasks:
                    del self._pending_tasks[session_uuid]
                
                logger.info(
                    f"✅ [Queue B] Session {session_uuid} MVR processing completed "
                    f"in {processing_time:.2f}s (retries={retry_count})"
                )
                return
                
            except Exception as e:
                retry_count += 1
                
                if retry_count > self.max_retries:
                    # Max retries reached - mark as failed
                    logger.error(
                        f"❌ [Queue B] Session {session_uuid} MVR processing failed "
                        f"after {self.max_retries} retries: {e}"
                    )
                    
                    # Update session status to failed
                    try:
                        await self._update_session_mvr_status(
                            session_uuid=session_uuid,
                            status="mvr_failed",
                            error_message=str(e)
                        )
                    except Exception:
                        pass
                    
                    self._failed_tasks[session_uuid] = {
                        "session_uuid": str(session_uuid),
                        "individual_count": len(individual_uuids),
                        "error": str(e),
                        "retry_count": retry_count - 1,
                        "failed_at": datetime.utcnow().isoformat()
                    }
                    
                    # Remove from pending
                    if session_uuid in self._pending_tasks:
                        del self._pending_tasks[session_uuid]
                    
                    return
                else:
                    # Retry with delay
                    logger.warning(
                        f"⚠️ [Queue B] Retry {retry_count}/{self.max_retries} "
                        f"for session {session_uuid} after error: {e}"
                    )
                    await asyncio.sleep(self.retry_delay)
    
    async def _fetch_session_individuals(
        self,
        session_uuid: UUID,
        individual_uuids: List[UUID]
    ) -> List[Dict]:
        """
        Fetch individual data from database including person_objects.
        
        This reconstructs the matched_individuals structure needed by
        merge_individuals_by_similarity function.
        
        Args:
            session_uuid: Session UUID
            individual_uuids: List of individual UUIDs
        
        Returns:
            List of matched_individuals dicts with person_objects
        """
        from api.v1.cross_video_tracking_simple import get_database_client
        
        db_client = get_database_client()
        matched_individuals = []
        
        async with db_client.pool.acquire() as conn:
            for individual_uuid in individual_uuids:
                # Fetch individual data
                individual_row = await conn.fetchrow("""
                    SELECT individual_uuid, individual_id, confidence_score
                    FROM individuals
                    WHERE individual_uuid = $1
                """, individual_uuid)
                
                if not individual_row:
                    logger.warning(f"Individual {individual_uuid} not found in database")
                    continue
                
                # Fetch video appearances
                video_rows = await conn.fetch("""
                    SELECT video_uuid, start_timestamp, end_timestamp, 
                           confidence, representative_faces
                    FROM individual_video_appearances
                    WHERE individual_uuid = $1
                    ORDER BY start_timestamp
                """, individual_uuid)
                
                video_uuids = [str(row['video_uuid']) for row in video_rows]
                
                # Build person_objects from representative_faces in video_rows
                person_objects_by_video = {}
                for row in video_rows:
                    video_uuid = str(row['video_uuid'])
                    representative_faces = row['representative_faces'] if row['representative_faces'] else []
                    
                    # Convert representative_faces to person_objects format
                    person_objects_by_video[video_uuid] = {
                        'confidence': float(row['confidence']),
                        'representative_faces': representative_faces
                    }
                
                # Build matched_individuals structure
                matched_individuals.append({
                    'individual_uuid': str(individual_uuid),
                    'video_uuids': video_uuids,
                    'person_objects': person_objects_by_video,
                    'temporal_score': float(individual_row['confidence_score'])
                })
        
        return matched_individuals
    
    async def _update_session_mvr_status(
        self,
        session_uuid: UUID,
        status: str,
        mvr_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update tracking session MVR processing status.
        
        Args:
            session_uuid: Session UUID
            status: MVR status (mvr_processing, mvr_complete, mvr_failed)
            mvr_count: Number of MVR people created (optional)
            error_message: Error message if failed (optional)
        """
        from api.v1.cross_video_tracking_simple import get_database_client
        
        db_client = get_database_client()
        
        try:
            async with db_client.pool.acquire() as conn:
                if status == "mvr_complete" and mvr_count is not None:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET unique_mvr_people_count = $2,
                            failed_videos = array_append(
                                failed_videos,
                                $3
                            )
                        WHERE session_uuid = $1
                    """, session_uuid, mvr_count,
                         f"mvr_status: {status}, mvr_count: {mvr_count}")
                elif status == "mvr_failed" and error_message:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(
                            failed_videos,
                            $2
                        )
                        WHERE session_uuid = $1
                    """, session_uuid,
                         f"mvr_status: {status}, error: {error_message[:200]}")
                else:
                    await conn.execute("""
                        UPDATE tracking_sessions
                        SET failed_videos = array_append(
                            failed_videos,
                            $2
                        )
                        WHERE session_uuid = $1
                    """, session_uuid, f"mvr_status: {status}")
        except Exception as e:
            logger.error(f"Failed to update session MVR status: {e}")
