"""
Signage ETL Worker

Background worker for batch synchronization of video lists to signage devices.
Handles queuing, retry logic, parallel processing, and comprehensive error handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.signage import SyncStatus, VideoList, SignageDevice
from ..schemas.signage import SyncMode
from .signage_service import SignageService, SignageSyncService

logger = logging.getLogger(__name__)


class SyncJob:
    """Represents a single sync job."""

    def __init__(
        self,
        job_id: UUID,
        video_list_id: int,
        device_ids: List[UUID],
        sync_mode: str,
        user_id: UUID,
        force_update: bool = False,
        priority: int = 0,
    ):
        self.job_id = job_id
        self.video_list_id = video_list_id
        self.device_ids = device_ids
        self.sync_mode = sync_mode
        self.user_id = user_id
        self.force_update = force_update
        self.priority = priority
        self.created_at = datetime.utcnow()
        self.status = "pending"
        self.result: Optional[Dict] = None


class SignageETLWorker:
    """
    Background worker for processing video list sync jobs.
    
    Handles:
    - Batch synchronization to multiple devices
    - Job queuing and priority management
    - Retry logic with exponential backoff
    - Parallel device sync operations
    - Progress tracking and reporting
    """

    def __init__(self, max_workers: int = 5, max_retries: int = 3):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.active_jobs: Dict[UUID, SyncJob] = {}
        self.completed_jobs: Dict[UUID, SyncJob] = {}
        self.running = False
        self._worker_tasks: List[asyncio.Task] = []

    async def start(self):
        """Start the ETL worker."""
        if self.running:
            logger.warning("ETL worker already running")
            return

        self.running = True
        logger.info(f"Starting ETL worker with {self.max_workers} workers")

        # Start worker coroutines
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._worker_tasks.append(task)

    async def stop(self):
        """Stop the ETL worker gracefully."""
        logger.info("Stopping ETL worker...")
        self.running = False

        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

        logger.info("ETL worker stopped")

    async def enqueue_sync_job(
        self,
        video_list_id: int,
        device_ids: List[UUID],
        sync_mode: str,
        user_id: UUID,
        force_update: bool = False,
        priority: int = 0,
    ) -> UUID:
        """
        Enqueue a new sync job.

        Args:
            video_list_id: Video list database ID
            device_ids: List of device UUIDs to sync to
            sync_mode: "full" or "incremental"
            user_id: User initiating the sync
            force_update: Force re-sync even if up-to-date
            priority: Job priority (higher = processed first)

        Returns:
            Job UUID
        """
        job = SyncJob(
            job_id=UUID(int=len(self.active_jobs) + len(self.completed_jobs) + 1),
            video_list_id=video_list_id,
            device_ids=device_ids,
            sync_mode=sync_mode,
            user_id=user_id,
            force_update=force_update,
            priority=priority,
        )

        self.active_jobs[job.job_id] = job
        await self.job_queue.put(job)

        logger.info(
            f"Enqueued sync job {job.job_id} for video list {video_list_id} "
            f"to {len(device_ids)} device(s)"
        )

        return job.job_id

    async def get_job_status(self, job_id: UUID) -> Optional[Dict]:
        """
        Get status of a sync job.

        Args:
            job_id: Job UUID

        Returns:
            Job status dictionary or None if not found
        """
        # Check active jobs
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            return {
                "job_id": str(job.job_id),
                "status": job.status,
                "video_list_id": job.video_list_id,
                "device_count": len(job.device_ids),
                "created_at": job.created_at.isoformat(),
                "result": job.result,
            }

        # Check completed jobs
        if job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
            return {
                "job_id": str(job.job_id),
                "status": job.status,
                "video_list_id": job.video_list_id,
                "device_count": len(job.device_ids),
                "created_at": job.created_at.isoformat(),
                "result": job.result,
            }

        return None

    async def _worker_loop(self, worker_id: int):
        """Worker coroutine that processes sync jobs."""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get next job from queue (with timeout to allow checking running flag)
                try:
                    job = await asyncio.wait_for(
                        self.job_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                logger.info(f"Worker {worker_id} processing job {job.job_id}")
                job.status = "in_progress"

                # Process the job
                try:
                    result = await self._process_sync_job(job)
                    job.status = "completed"
                    job.result = result
                    logger.info(
                        f"Worker {worker_id} completed job {job.job_id}: "
                        f"{result['successful_devices']}/{result['total_devices']} devices synced"
                    )

                except Exception as e:
                    logger.error(
                        f"Worker {worker_id} failed to process job {job.job_id}: {str(e)}",
                        exc_info=True,
                    )
                    job.status = "failed"
                    job.result = {"error": str(e)}

                # Move to completed jobs
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
                self.completed_jobs[job.job_id] = job

                # Mark task done
                self.job_queue.task_done()

            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} encountered error: {str(e)}", exc_info=True
                )

        logger.info(f"Worker {worker_id} stopped")

    async def _process_sync_job(self, job: SyncJob) -> Dict:
        """
        Process a single sync job by syncing to all devices.

        Args:
            job: SyncJob to process

        Returns:
            Dictionary with sync results
        """
        db = SessionLocal()
        try:
            service = SignageSyncService(db)
            signage_service = SignageService(db)

            # Get video list
            video_list = signage_service.get_video_list(
                job.video_list_id, job.user_id, include_items=True
            )
            if not video_list:
                raise ValueError("Video list not found")

            # Get video list UUID
            video_list_uuid = video_list.uuid

            # job.sync_mode is a string; convert to the SyncMode enum the
            # service expects (it calls sync_mode.value internally).
            sync_mode = SyncMode(job.sync_mode)

            # Sync to each device in parallel (with rate limiting)
            sync_tasks = []
            for device_id in job.device_ids:
                task = service.sync_video_list_to_device(
                    video_list_uuid,
                    device_id,
                    sync_mode,
                    job.user_id,
                    job.force_update,
                )
                sync_tasks.append(task)

            # Execute sync tasks with controlled concurrency
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent device syncs

            async def sync_with_semaphore(task):
                async with semaphore:
                    return await task

            results = await asyncio.gather(
                *[sync_with_semaphore(task) for task in sync_tasks],
                return_exceptions=True,
            )

            # Analyze results.
            # `sync_video_list_to_device` returns a VideoListSyncHistory and does
            # NOT raise when the device push itself fails (it records a "failed"
            # history row). So count a device as successful ONLY when the returned
            # history is `completed` (or `partial` == some succeeded). An exception
            # is also a failure.
            successful = 0
            for result in results:
                if isinstance(result, Exception):
                    continue
                status = getattr(result, "sync_status", None)
                if status == SyncStatus.COMPLETED.value or status == SyncStatus.PARTIAL.value:
                    successful += 1
            failed = len(results) - successful

            # Log any per-device failures (collect with device ids) so silent
            # swallow in `gather(return_exceptions=True)` doesn't hide errors.
            for device_id, result in zip(job.device_ids, results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Sync to device {device_id} failed for video list "
                        f"{video_list.name}: {result}"
                    )
                else:
                    status = getattr(result, "sync_status", None)
                    if status == SyncStatus.FAILED.value:
                        logger.error(
                            f"Sync to device {device_id} FAILED for video list "
                            f"{video_list.name} (history status=failed)"
                        )

            return {
                "total_devices": len(job.device_ids),
                "successful_devices": successful,
                "failed_devices": failed,
                "sync_mode": job.sync_mode,
                "video_list_id": job.video_list_id,
                "video_list_name": video_list.name,
                "video_count": video_list.video_count,
            }

        finally:
            db.close()

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Clean up old completed jobs to prevent memory bloat.

        Args:
            max_age_hours: Maximum age of completed jobs to keep
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed_count = 0

        for job_id, job in list(self.completed_jobs.items()):
            if job.created_at < cutoff_time:
                del self.completed_jobs[job_id]
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old completed jobs")


class BatchSyncManager:
    """
    Manager for batch synchronization operations.
    
    Provides high-level batch sync capabilities:
    - Sync one video list to multiple devices
    - Sync multiple video lists to one device
    - Sync multiple video lists to multiple devices
    """

    def __init__(self, etl_worker: SignageETLWorker):
        self.etl_worker = etl_worker

    async def sync_list_to_devices(
        self,
        video_list_id: int,
        device_ids: List[UUID],
        sync_mode: str,
        user_id: UUID,
        force_update: bool = False,
    ) -> UUID:
        """
        Sync one video list to multiple devices.

        Args:
            video_list_id: Video list database ID
            device_ids: List of device UUIDs
            sync_mode: "full" or "incremental"
            user_id: User initiating sync
            force_update: Force re-sync

        Returns:
            Job UUID
        """
        return await self.etl_worker.enqueue_sync_job(
            video_list_id, device_ids, sync_mode, user_id, force_update
        )

    async def sync_lists_to_device(
        self,
        video_list_ids: List[int],
        device_id: UUID,
        sync_mode: str,
        user_id: UUID,
        force_update: bool = False,
    ) -> List[UUID]:
        """
        Sync multiple video lists to one device.

        Args:
            video_list_ids: List of video list database IDs
            device_id: Device UUID
            sync_mode: "full" or "incremental"
            user_id: User initiating sync
            force_update: Force re-sync

        Returns:
            List of job UUIDs
        """
        job_ids = []
        for video_list_id in video_list_ids:
            job_id = await self.etl_worker.enqueue_sync_job(
                video_list_id, [device_id], sync_mode, user_id, force_update
            )
            job_ids.append(job_id)

        return job_ids

    async def sync_lists_to_devices(
        self,
        video_list_ids: List[int],
        device_ids: List[UUID],
        sync_mode: str,
        user_id: UUID,
        force_update: bool = False,
    ) -> List[UUID]:
        """
        Sync multiple video lists to multiple devices.

        Creates a job for each video list to sync to all specified devices.

        Args:
            video_list_ids: List of video list database IDs
            device_ids: List of device UUIDs
            sync_mode: "full" or "incremental"
            user_id: User initiating sync
            force_update: Force re-sync

        Returns:
            List of job UUIDs
        """
        job_ids = []
        for video_list_id in video_list_ids:
            job_id = await self.etl_worker.enqueue_sync_job(
                video_list_id, device_ids, sync_mode, user_id, force_update
            )
            job_ids.append(job_id)

        return job_ids

    async def sync_to_all_online_devices(
        self,
        video_list_id: int,
        sync_mode: str,
        user_id: UUID,
        force_update: bool = False,
    ) -> Optional[UUID]:
        """
        Sync a video list to all online devices.

        Args:
            video_list_id: Video list database ID
            sync_mode: "full" or "incremental"
            user_id: User initiating sync
            force_update: Force re-sync

        Returns:
            Job UUID or None if no devices online
        """
        db = SessionLocal()
        try:
            service = SignageService(db)

            # Get all online devices
            devices, _ = service.list_devices(
                page=1, page_size=1000, is_online=True
            )

            if not devices:
                logger.warning("No online devices found for batch sync")
                return None

            device_ids = [device.device_id for device in devices]

            return await self.etl_worker.enqueue_sync_job(
                video_list_id, device_ids, sync_mode, user_id, force_update
            )

        finally:
            db.close()


# Global ETL worker instance
_etl_worker: Optional[SignageETLWorker] = None
_batch_sync_manager: Optional[BatchSyncManager] = None


def get_etl_worker() -> SignageETLWorker:
    """Get the global ETL worker instance."""
    global _etl_worker
    if _etl_worker is None:
        _etl_worker = SignageETLWorker(max_workers=5, max_retries=3)
    return _etl_worker


def get_batch_sync_manager() -> BatchSyncManager:
    """Get the global batch sync manager instance."""
    global _batch_sync_manager
    if _batch_sync_manager is None:
        _batch_sync_manager = BatchSyncManager(get_etl_worker())
    return _batch_sync_manager


async def start_etl_worker():
    """Start the ETL worker on application startup."""
    worker = get_etl_worker()
    await worker.start()
    logger.info("✅ ETL worker started successfully")


async def stop_etl_worker():
    """Stop the ETL worker on application shutdown."""
    global _etl_worker
    if _etl_worker:
        await _etl_worker.stop()
        _etl_worker = None
    logger.info("✅ ETL worker stopped")
