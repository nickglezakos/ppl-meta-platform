"""
MVR-People Background Processor

Handles automatic MVR-People creation and matching in the background
when new Individuals are created.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
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
        max_retries: int = 3,
        retry_delay: float = 5.0
    ):
        """
        Initialize background processor.
        
        Args:
            mvr_service: MVRService instance for creating MVR-People
            mvr_matcher: MVRMatcher instance for matching and merging
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.mvr_service = mvr_service
        self.mvr_matcher = mvr_matcher
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Task tracking
        self._pending_tasks: Dict[UUID, asyncio.Task] = {}
        self._completed_tasks: Dict[UUID, Dict] = {}
        self._failed_tasks: Dict[UUID, Dict] = {}
        
        logger.info(
            f"✅ MVRBackgroundProcessor initialized "
            f"(max_retries={max_retries}, retry_delay={retry_delay}s)"
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
