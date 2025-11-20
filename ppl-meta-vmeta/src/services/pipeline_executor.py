"""
Pipeline Executor

Executes the batch processing pipeline that creates individuals and MVR people
with two-level caching (individual cache + MVR cache).

This module provides:
- Dedicated worker pool for batch processing
- Integration with Media Service for video queries
- Integration with Orchestrator for tracking session creation
- Two-level caching support
- Retry logic and error handling
- Performance metrics tracking

Architecture:
    BatchMonitor triggers → PipelineExecutor → Orchestrator (tracking session)
    ├─ Query videos from Media Service
    ├─ Create tracking session via Orchestrator
    ├─ Wait for session completion (polling)
    ├─ Apply two-level caching (individual + MVR)
    └─ Update batch state with results
"""

import asyncio
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID


logger = logging.getLogger(__name__)


class PipelineExecutor:
    """
    Executes the batch processing pipeline for creating individuals and MVR.
    
    Features:
    - Dedicated worker pool for concurrent batch processing
    - Integration with Media Service and Orchestrator
    - Two-level caching (individual + MVR)
    - Retry logic with exponential backoff
    - Session completion polling
    - Performance metrics
    """
    
    def __init__(
        self,
        media_service_url: str = "http://localhost:8000",
        orchestrator_url: str = "http://localhost:8002",
        max_workers: int = 3,
        max_queue_size: int = 10,
        session_timeout_seconds: int = 300,
        retry_max_attempts: int = 3,
        retry_initial_delay: float = 1.0,
        retry_max_delay: float = 30.0,
        retry_backoff_multiplier: float = 2.0
    ):
        """
        Initialize pipeline executor.
        
        Args:
            media_service_url: Media Service base URL
            orchestrator_url: Orchestrator Service base URL
            max_workers: Maximum concurrent batch workers
            max_queue_size: Maximum queue size for pending batches
            session_timeout_seconds: Timeout for tracking session
            retry_max_attempts: Maximum retry attempts
            retry_initial_delay: Initial retry delay in seconds
            retry_max_delay: Maximum retry delay in seconds
            retry_backoff_multiplier: Backoff multiplier for retries
        """
        self.media_service_url = media_service_url.rstrip('/')
        self.orchestrator_url = orchestrator_url.rstrip('/')
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.session_timeout_seconds = session_timeout_seconds
        
        # Retry configuration
        self.retry_max_attempts = retry_max_attempts
        self.retry_initial_delay = retry_initial_delay
        self.retry_max_delay = retry_max_delay
        self.retry_backoff_multiplier = retry_backoff_multiplier
        
        # Worker pool
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # HTTP session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "batches_executed": 0,
            "batches_succeeded": 0,
            "batches_failed": 0,
            "total_processing_time": 0.0,
            "total_individuals_created": 0,
            "total_mvr_created": 0,
            "cache_hits_individual": 0,
            "cache_hits_mvr": 0,
            "started_at": None
        }
        
        logger.info(
            f"PipelineExecutor initialized: {max_workers} workers, "
            f"queue size {max_queue_size}"
        )
    
    async def start(self) -> None:
        """Start the pipeline executor and worker pool."""
        if self.running:
            logger.warning("PipelineExecutor already running")
            return
        
        self.running = True
        self.stats["started_at"] = datetime.now(timezone.utc)
        
        # Create HTTP session
        self.http_session = aiohttp.ClientSession()
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"PipelineExecutor-Worker-{i}"
            )
            self.workers.append(worker)
        
        logger.info(
            f"PipelineExecutor started with {self.max_workers} workers"
        )
    
    async def stop(self) -> None:
        """Stop the pipeline executor gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping PipelineExecutor...")
        self.running = False
        
        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
        
        logger.info("PipelineExecutor stopped")
    
    async def submit_batch(
        self,
        batch_uuid: UUID,
        collection_id: str,
        video_uuids: List[UUID],
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """
        Submit batch for execution.
        
        Args:
            batch_uuid: Batch UUID
            collection_id: Collection identifier
            video_uuids: List of video UUIDs in batch
            start_time: Batch start time
            end_time: Batch end time
            
        Returns:
            True if batch was queued, False if queue full
        """
        try:
            batch_task = {
                "batch_uuid": batch_uuid,
                "collection_id": collection_id,
                "video_uuids": video_uuids,
                "start_time": start_time,
                "end_time": end_time,
                "submitted_at": datetime.now(timezone.utc)
            }
            
            self.queue.put_nowait(batch_task)
            logger.info(
                f"Batch {str(batch_uuid)[:8]} queued for execution "
                f"({len(video_uuids)} videos)"
            )
            return True
            
        except asyncio.QueueFull:
            logger.error(
                f"Pipeline executor queue full, batch {str(batch_uuid)[:8]} "
                "rejected"
            )
            return False
    
    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop to process batches from queue.
        
        Args:
            worker_id: Worker identifier for logging
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get batch from queue with timeout
                batch_task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                # Execute batch pipeline
                try:
                    result = await self._execute_batch_with_retry(
                        batch_task,
                        worker_id
                    )
                    
                    if result["status"] == "completed":
                        self.stats["batches_succeeded"] += 1
                        self._update_cache_statistics(result)
                    else:
                        self.stats["batches_failed"] += 1
                    
                    self.stats["batches_executed"] += 1
                    self.stats["total_processing_time"] += result.get(
                        "processing_time", 0.0
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Worker {worker_id}: Batch execution failed: {e}",
                        exc_info=True
                    )
                    self.stats["batches_failed"] += 1
                
                finally:
                    self.queue.task_done()
                
            except asyncio.TimeoutError:
                # No batches in queue, continue
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
    
    async def _execute_batch_with_retry(
        self,
        batch_task: Dict[str, Any],
        worker_id: int
    ) -> Dict[str, Any]:
        """
        Execute batch with retry logic.
        
        Args:
            batch_task: Batch task dictionary
            worker_id: Worker identifier
            
        Returns:
            Batch execution result
        """
        batch_uuid = batch_task["batch_uuid"]
        
        for attempt in range(self.retry_max_attempts):
            try:
                logger.info(
                    f"Worker {worker_id}: Executing batch "
                    f"{str(batch_uuid)[:8]} (attempt {attempt + 1})"
                )
                
                result = await self.execute_batch_pipeline(
                    batch_uuid=batch_uuid,
                    collection_id=batch_task["collection_id"],
                    video_uuids=batch_task["video_uuids"],
                    start_time=batch_task["start_time"],
                    end_time=batch_task["end_time"]
                )
                
                if attempt > 0:
                    logger.info(
                        f"Worker {worker_id}: Batch {str(batch_uuid)[:8]} "
                        f"succeeded on retry {attempt}"
                    )
                
                return result
                
            except Exception as e:
                logger.error(
                    f"Worker {worker_id}: Batch execution attempt "
                    f"{attempt + 1} failed: {e}"
                )
                
                if attempt < self.retry_max_attempts - 1:
                    # Calculate backoff delay
                    delay = self.retry_initial_delay * (
                        self.retry_backoff_multiplier ** attempt
                    )
                    delay = min(delay, self.retry_max_delay)
                    
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(
            f"Worker {worker_id}: Batch {str(batch_uuid)[:8]} failed "
            f"after {self.retry_max_attempts} attempts"
        )
        
        return {
            "status": "failed",
            "batch_uuid": batch_uuid,
            "error": f"Failed after {self.retry_max_attempts} attempts"
        }
    
    async def execute_batch_pipeline(
        self,
        batch_uuid: UUID,
        collection_id: str,
        video_uuids: List[UUID],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute the complete batch processing pipeline.
        
        Steps:
        1. Query videos from Media Service
        2. Create tracking session via Orchestrator
        3. Wait for session completion (polling)
        4. Extract results (individuals, MVR, cache hits)
        5. Return execution result
        
        Args:
            batch_uuid: Batch UUID
            collection_id: Collection identifier
            video_uuids: List of video UUIDs
            start_time: Batch start time
            end_time: Batch end time
            
        Returns:
            Batch execution result dictionary
        """
        execution_start = datetime.now(timezone.utc)
        
        logger.info(
            f"[BATCH {str(batch_uuid)[:8]}] Starting pipeline execution "
            f"for {len(video_uuids)} videos"
        )
        
        try:
            # Step 1: Query videos from Media Service
            logger.debug(
                f"[BATCH {str(batch_uuid)[:8]}] Querying videos from "
                "Media Service..."
            )
            
            videos_data = await self._query_videos_from_media_service(
                collection_id=collection_id,
                start_time=start_time,
                end_time=end_time
            )
            
            if not videos_data:
                raise Exception("No videos returned from Media Service")
            
            logger.info(
                f"[BATCH {str(batch_uuid)[:8]}] Retrieved {len(videos_data)} "
                "videos from Media Service"
            )
            
            # Step 2: Create tracking session
            logger.debug(
                f"[BATCH {str(batch_uuid)[:8]}] Creating tracking session..."
            )
            
            session_uuid = await self._create_tracking_session(
                collection_id=collection_id,
                video_uuids=video_uuids,
                start_time=start_time,
                end_time=end_time,
                batch_mode=True  # Enable two-level caching
            )
            
            logger.info(
                f"[BATCH {str(batch_uuid)[:8]}] Tracking session created: "
                f"{str(session_uuid)[:8]}"
            )
            
            # Step 3: Wait for session completion
            logger.debug(
                f"[BATCH {str(batch_uuid)[:8]}] Waiting for session "
                "completion..."
            )
            
            session_result = await self._wait_for_session_completion(
                session_uuid=session_uuid,
                timeout_seconds=self.session_timeout_seconds
            )
            
            # Step 4: Extract results
            execution_time = (
                datetime.now(timezone.utc) - execution_start
            ).total_seconds()
            
            result = {
                "status": "completed",
                "batch_uuid": batch_uuid,
                "session_uuid": session_uuid,
                "collection_id": collection_id,
                "video_count": len(video_uuids),
                "individuals_created": session_result.get(
                    "individuals_created", 0
                ),
                "individuals_cached": session_result.get(
                    "individuals_cached", 0
                ),
                "mvr_people_created": session_result.get(
                    "mvr_people_created", 0
                ),
                "mvr_people_cached": session_result.get(
                    "mvr_people_cached", 0
                ),
                "processing_time": execution_time,
                "cache_hit_rate": session_result.get("cache_hit_rate", 0.0),
                "completed_at": datetime.now(timezone.utc)
            }
            
            logger.info(
                f"[BATCH {str(batch_uuid)[:8]}] Pipeline completed in "
                f"{execution_time:.1f}s: "
                f"{result['individuals_created']} individuals "
                f"({result['individuals_cached']} cached), "
                f"{result['mvr_people_created']} MVR people "
                f"({result['mvr_people_cached']} cached), "
                f"{result['cache_hit_rate']:.1f}% cache hit rate"
            )
            
            return result
            
        except Exception as e:
            execution_time = (
                datetime.now(timezone.utc) - execution_start
            ).total_seconds()
            
            logger.error(
                f"[BATCH {str(batch_uuid)[:8]}] Pipeline execution failed "
                f"after {execution_time:.1f}s: {e}",
                exc_info=True
            )
            
            return {
                "status": "failed",
                "batch_uuid": batch_uuid,
                "collection_id": collection_id,
                "video_count": len(video_uuids),
                "processing_time": execution_time,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc)
            }
    
    async def _query_videos_from_media_service(
        self,
        collection_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query videos from Media Service for the batch time range.
        
        Args:
            collection_id: Collection identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of video metadata dictionaries
        """
        # Use Media search endpoint, not non-existent /api/v1/videos
        url = f"{self.media_service_url}/api/v1/media/search"
        
        params = {
            "collection_id": collection_id,
            "date_from": start_time.isoformat(),
            "date_to": end_time.isoformat(),
            "limit": 100  # Batch size should be < 100
        }
        
        async with self.http_session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(
                    f"Media Service query failed ({response.status}): "
                    f"{error_text}"
                )
            
            # Media search returns a list directly, not wrapped in "videos" key
            data = await response.json()
            return data if isinstance(data, list) else []
    
    async def _create_tracking_session(
        self,
        collection_id: str,
        video_uuids: List[UUID],
        start_time: datetime,
        end_time: datetime,
        batch_mode: bool = True
    ) -> UUID:
        """
        Create tracking session via Orchestrator.
        
        Args:
            collection_id: Collection identifier
            video_uuids: List of video UUIDs
            start_time: Session start time
            end_time: Session end time
            batch_mode: Enable batch mode with two-level caching
            
        Returns:
            Tracking session UUID
        """
        url = f"{self.orchestrator_url}/api/v1/tracking/sessions"
        
        payload = {
            "collection_id": collection_id,
            "video_uuids": [str(uuid) for uuid in video_uuids],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "batch_mode": batch_mode,  # Enable two-level caching
            "cache_individuals": True,  # Level 1 cache
            "cache_mvr": True  # Level 2 cache
        }
        
        async with self.http_session.post(url, json=payload) as response:
            if response.status != 201:
                error_text = await response.text()
                raise Exception(
                    f"Tracking session creation failed ({response.status}): "
                    f"{error_text}"
                )
            
            data = await response.json()
            session_uuid_str = data.get("session_uuid")
            
            if not session_uuid_str:
                raise Exception("No session UUID in response")
            
            return UUID(session_uuid_str)
    
    async def _wait_for_session_completion(
        self,
        session_uuid: UUID,
        timeout_seconds: int = 300,
        poll_interval_seconds: int = 5
    ) -> Dict[str, Any]:
        """
        Wait for tracking session to complete by polling status.
        
        Args:
            session_uuid: Session UUID
            timeout_seconds: Maximum wait time
            poll_interval_seconds: Polling interval
            
        Returns:
            Session result dictionary
        """
        url = f"{self.orchestrator_url}/api/v1/tracking/sessions/{session_uuid}"
        
        start_time = datetime.now(timezone.utc)
        timeout_time = start_time + timedelta(seconds=timeout_seconds)
        
        while datetime.now(timezone.utc) < timeout_time:
            try:
                async with self.http_session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(
                            f"Session status query failed ({response.status}): "
                            f"{error_text}"
                        )
                        await asyncio.sleep(poll_interval_seconds)
                        continue
                    
                    data = await response.json()
                    status = data.get("status")
                    
                    if status == "completed":
                        logger.debug(
                            f"Session {str(session_uuid)[:8]} completed"
                        )
                        return data.get("result", {})
                    
                    elif status == "failed":
                        error_msg = data.get("error", "Unknown error")
                        raise Exception(
                            f"Session {str(session_uuid)[:8]} failed: "
                            f"{error_msg}"
                        )
                    
                    elif status in ["pending", "processing"]:
                        # Still processing, continue polling
                        logger.debug(
                            f"Session {str(session_uuid)[:8]} status: {status}"
                        )
                        await asyncio.sleep(poll_interval_seconds)
                    
                    else:
                        logger.warning(
                            f"Unknown session status: {status}"
                        )
                        await asyncio.sleep(poll_interval_seconds)
            
            except Exception as e:
                logger.error(
                    f"Error polling session status: {e}",
                    exc_info=True
                )
                await asyncio.sleep(poll_interval_seconds)
        
        # Timeout reached
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        raise Exception(
            f"Session {str(session_uuid)[:8]} timeout after {elapsed:.1f}s"
        )
    
    def _update_cache_statistics(self, result: Dict[str, Any]) -> None:
        """Update global cache statistics from batch result."""
        self.stats["total_individuals_created"] += result.get(
            "individuals_created", 0
        )
        self.stats["total_mvr_created"] += result.get(
            "mvr_people_created", 0
        )
        self.stats["cache_hits_individual"] += result.get(
            "individuals_cached", 0
        )
        self.stats["cache_hits_mvr"] += result.get(
            "mvr_people_cached", 0
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pipeline executor statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()
        stats["queue_size"] = self.queue.qsize()
        stats["worker_count"] = len(self.workers)
        stats["running"] = self.running
        
        # Calculate uptime
        if stats["started_at"]:
            uptime = datetime.now(timezone.utc) - stats["started_at"]
            stats["uptime_seconds"] = uptime.total_seconds()
        else:
            stats["uptime_seconds"] = 0
        
        # Calculate success rate
        if stats["batches_executed"] > 0:
            stats["success_rate"] = (
                stats["batches_succeeded"] / stats["batches_executed"]
            )
        else:
            stats["success_rate"] = 0.0
        
        # Calculate average processing time
        if stats["batches_succeeded"] > 0:
            stats["avg_processing_time"] = (
                stats["total_processing_time"] / stats["batches_succeeded"]
            )
        else:
            stats["avg_processing_time"] = 0.0
        
        # Calculate cache hit rates
        total_individuals = (
            stats["total_individuals_created"] + 
            stats["cache_hits_individual"]
        )
        if total_individuals > 0:
            stats["individual_cache_hit_rate"] = (
                stats["cache_hits_individual"] / total_individuals
            )
        else:
            stats["individual_cache_hit_rate"] = 0.0
        
        total_mvr = (
            stats["total_mvr_created"] + 
            stats["cache_hits_mvr"]
        )
        if total_mvr > 0:
            stats["mvr_cache_hit_rate"] = (
                stats["cache_hits_mvr"] / total_mvr
            )
        else:
            stats["mvr_cache_hit_rate"] = 0.0
        
        return stats
    
    def is_healthy(self) -> bool:
        """
        Check if pipeline executor is healthy.
        
        Returns:
            True if healthy
        """
        if not self.running:
            return False
        
        # Check if queue is near capacity
        queue_size = self.queue.qsize()
        if queue_size >= self.queue.maxsize * 0.9:
            logger.warning(
                f"Pipeline executor queue near capacity: "
                f"{queue_size}/{self.queue.maxsize}"
            )
            return False
        
        # Check if workers are alive
        alive_workers = sum(1 for w in self.workers if not w.done())
        if alive_workers < self.max_workers:
            logger.error(
                f"Some workers died: {alive_workers}/{self.max_workers}"
            )
            return False
        
        return True
