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
from typing import Optional, List, Dict, Any
from uuid import UUID

from models.batch_processing import BatchProcessingState
from database.batch_repository import BatchProcessingRepository
from services.batch_monitor import BatchMonitor
try:
    # Optional import for submitting batches via local executor
    from services.pipeline_executor import PipelineExecutor
except Exception:
    PipelineExecutor = None

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
    Recording-aware polling manager for MVR batch processing.
    
    Only polls during active recordings (between start and stop events).
    Triggers incremental batches every X videos and a final batch on stop.
    """
    
    def __init__(
        self,
        batch_monitor: BatchMonitor,
        poll_interval_seconds: int = 60,
        enabled: bool = False,
        media_url: str = "http://localhost:8000",
        vision_url: str = "http://localhost:8003",
        vmeta_url: str = "http://localhost:8008",
        node_url: str = "http://localhost:8001",
        batch_size: int = 5,
        collection_id: Optional[str] = None,
        pipeline_executor: Any = None,
    ):
        """
        Initialize recording-aware polling manager.
        
        Args:
            batch_monitor: Batch monitor service
            poll_interval_seconds: Polling interval during recording
            enabled: Whether polling is enabled
            media_url: Media service URL
            vision_url: Vision service URL
            vmeta_url: VMeta service URL
            node_url: Node service URL for auth
            batch_size: Videos per batch (incremental triggers)
            collection_id: DEPRECATED - collections now managed dynamically
                          via recording events (start/stop). Leave as None.
        """
        self.batch_monitor = batch_monitor
        self.poll_interval = poll_interval_seconds
        self.enabled = enabled
        self.media_url = media_url
        self.vision_url = vision_url
        self.vmeta_url = vmeta_url
        self.node_url = node_url
        self.batch_size = batch_size
        self.collection_id = collection_id  # DEPRECATED - kept for fallback only
        
        # Recording sessions tracking
        self._active_recordings = {}  # {collection_id: session_info}
        
        # Background task
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # State tracking per recording
        self._processed_videos = set()  # All processed video UUIDs across collections
        self._pending_videos_by_collection = {}  # {collection_id: [videos]} - separate queues per collection
        self._auth_token = None
        self._token_expires = None
        # Optional local executor for explicit video-based tracking
        self.pipeline_executor = pipeline_executor
        
        # Statistics
        self._stats = {
            'polls_performed': 0,
            'videos_discovered': 0,
            'batches_triggered': 0,
            'polls_failed': 0,
            'recordings_started': 0,
            'recordings_stopped': 0,
            'last_poll_at': None,
            'last_batch_at': None
        }
        
        logger.info(
            f"PollingFallbackManager initialized "
            f"(interval: {poll_interval_seconds}s, batch_size: {batch_size}, "
            f"enabled: {enabled}, recording-aware: True)"
        )
    
    async def start(self):
        """Start the polling background task."""
        if not self.enabled:
            logger.info("Polling fallback disabled, not starting")
            return
        
        if self._running:
            logger.warning("Polling fallback already running")
            return
        
        # Pre-populate processed videos with existing videos to avoid reprocessing
        await self._initialize_processed_videos()
        
        self._running = True
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_polling_loop())
        
        logger.info("Polling fallback started (waiting for recording events)")
    
    async def _initialize_processed_videos(self):
        """
        On startup, mark all existing videos as processed.
        This prevents reprocessing old videos after service restart.
        
        NOTE: With dynamic collection management, we skip initialization.
        Videos will be discovered via recording events and processed from that point.
        Old videos won't be reprocessed since they weren't part of a recording session.
        """
        logger.info(
            "📦 Using dynamic collection management - "
            "no pre-initialization needed. Videos will be tracked "
            "per recording session from recording start events."
        )
        # No-op - we rely on recording events to define the scope
        return
    
    async def start_recording(
        self,
        collection_id: str,
        session_uuid: str
    ):
        """
        Handle recording started event - activate polling for collection.
        
        Args:
            collection_id: Camera collection ID
            session_uuid: Recording session UUID
        """
        logger.info(
            f"📹 Recording started: {collection_id}, session: {session_uuid}"
        )
        
        # CRITICAL: Clear any pending videos from previous recordings
        if not hasattr(self, '_pending_videos_by_collection'):
            self._pending_videos_by_collection = {}
        if collection_id in self._pending_videos_by_collection:
            old_count = len(self._pending_videos_by_collection[collection_id])
            if old_count > 0:
                logger.warning(
                    f"Clearing {old_count} pending videos from "
                    f"previous recording for {collection_id}"
                )
            self._pending_videos_by_collection[collection_id] = []
        
        # CRITICAL: Clear processed videos set for this collection
        # This ensures we don't skip videos from previous recordings
        if not hasattr(self, '_processed_videos'):
            self._processed_videos = set()
        logger.info(
            f"Cleared {len(self._processed_videos)} processed videos "
            f"from tracking (starting fresh for new recording)"
        )
        self._processed_videos = set()
        
        self._active_recordings[collection_id] = {
            'session_uuid': session_uuid,
            'started_at': datetime.utcnow(),
            'videos_processed': 0,
            'batches_triggered': 0
        }
        
        self._stats['recordings_started'] += 1
        
        logger.info(
            f"Polling activated for {collection_id} "
            f"(active recordings: {len(self._active_recordings)})"
        )
    
    async def stop_recording(
        self,
        collection_id: str,
        session_uuid: str,
        grace_period_seconds: int = 120
    ) -> Dict[str, Any]:
        """
        Handle recording stopped event - trigger final batch and stop polling.
        
        Waits for a grace period to catch videos still being processed (upload + face detection)
        before triggering the final batch. This ensures videos that were recorded but still
        processing when stop was called get included in the final batch.
        
        Args:
            collection_id: Camera collection ID
            session_uuid: Recording session UUID
            grace_period_seconds: Time to wait for delayed videos (default 120s/2min)
            
        Returns:
            Dict with processing results
        """
        logger.info(
            f"🛑 Recording stopped: {collection_id}, session: {session_uuid}"
        )
        
        # Keep recording info but mark as stopped
        recording_info = self._active_recordings.get(collection_id)
        
        if not recording_info:
            logger.warning(
                f"Recording {collection_id} not found in active recordings"
            )
            return {
                'videos_processed': 0,
                'message': 'Recording not found'
            }
        
        # Mark as stopped but keep polling for grace period
        recording_info['stopped_at'] = datetime.utcnow()
        recording_info['grace_period_until'] = datetime.utcnow() + timedelta(seconds=grace_period_seconds)
        
        logger.info(
            f"⏰ Keeping polling active for {grace_period_seconds}s grace period "
            f"to catch videos still being processed"
        )
        
        self._stats['recordings_stopped'] += 1
        
        # Wait for grace period while continuing to poll for new videos with faces
        logger.info(f"⏳ Waiting {grace_period_seconds}s for delayed video processing...")
        await asyncio.sleep(grace_period_seconds)
        
        # Now remove from active recordings and trigger final batch
        recording_info = self._active_recordings.pop(collection_id, None)
        
        # Trigger final batch for all remaining pending videos in THIS collection
        videos_processed = 0
        if not hasattr(self, '_pending_videos_by_collection'):
            self._pending_videos_by_collection = {}
        
        if collection_id in self._pending_videos_by_collection:
            pending_videos = self._pending_videos_by_collection[collection_id]
            
            if pending_videos:
                logger.info(
                    f"Processing final batch for {collection_id}: {len(pending_videos)} "
                    f"remaining videos (after {grace_period_seconds}s grace period)"
                )
                
                await self._trigger_batch_processing(
                    pending_videos,
                    is_final=True
                )
                
                videos_processed = len(pending_videos)
                self._pending_videos_by_collection[collection_id] = []
        
        logger.info(
            f"✅ Recording {collection_id} stopped. "
            f"Final batch processed {videos_processed} videos. "
            f"Total batches: {recording_info.get('batches_triggered', 0)}"
        )
        
        return {
            'videos_processed': videos_processed,
            'total_batches': recording_info.get('batches_triggered', 0),
            'session_duration': (
                datetime.utcnow() - recording_info['started_at']
            ).total_seconds(),
            'grace_period_seconds': grace_period_seconds,
            'message': 'Final batch triggered after grace period'
        }

    
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
        """Main polling loop - only polls during active recordings."""
        logger.info("Polling loop started (recording-aware mode)")
        
        try:
            while self._running:
                try:
                    # Only poll if there are active recordings
                    if self._active_recordings:
                        logger.info(
                            f"🔍 Polling {len(self._active_recordings)} "
                            f"active recording(s): {list(self._active_recordings.keys())}"
                        )
                        await self._poll_for_videos()
                    else:
                        logger.debug(
                            "No active recordings, skipping poll"
                        )
                    
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
        Poll for completed videos with cached faces.
        
        Checks Media and Vision services for videos with face detection,
        accumulates them, and triggers batch when threshold reached.
        """
        self._stats['polls_performed'] += 1
        self._stats['last_poll_at'] = datetime.utcnow()
        
        try:
            import httpx
            from datetime import timedelta
            
            # Ensure we have auth token
            if not await self._ensure_auth_token():
                logger.warning("Failed to get auth token, skipping poll")
                return
            
            # Get active collection IDs from recording events
            # If no active recordings, skip polling (wait for recording start event)
            active_collection_ids = list(self._active_recordings.keys())
            
            if not active_collection_ids:
                logger.debug(
                    "No active recordings - skipping poll "
                    "(waiting for recording start event)"
                )
                return
            
            logger.info(
                f"🎥 Polling for videos from {len(active_collection_ids)} "
                f"active collection(s): {active_collection_ids}"
            )
            
            # Process each collection SEPARATELY - each gets its own batch pipeline
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {self._auth_token}"}
                
                # Query each active collection separately
                for coll_id in active_collection_ids:
                    try:
                        # Query with reasonable limit for active recording
                        # page_size=20 allows discovering videos fast enough
                        response = await client.get(
                            f"{self.media_url}/api/v1/media/search"
                            f"?collection_id={coll_id}"
                            f"&page_size=20&order_by=created_at&order=desc",
                            headers=headers
                        )
                        
                        if response.status_code != 200:
                            logger.debug(f"Media service returned {response.status_code} for collection {coll_id}")
                            continue
                        
                        collection_videos = response.json()
                        logger.debug(f"Found {len(collection_videos)} videos from collection {coll_id}")
                        
                        # Get recording start time for THIS collection
                        recording_start_time = None
                        if coll_id in self._active_recordings:
                            recording_start_time = self._active_recordings[coll_id]['started_at']
                        
                        # Filter to videos created AFTER this collection's recording started
                        if recording_start_time:
                            # Use recording start time directly (no buffer)
                            # This ensures only videos from THIS recording are included
                            cutoff_time = recording_start_time
                        else:
                            # Fallback: last 2 hours if no active recording
                            cutoff_time = datetime.utcnow() - timedelta(hours=2)
                        
                        recent_videos = []
                        
                        for video in collection_videos:
                            created_at_str = video.get('created_at', '')
                            try:
                                # Parse ISO format timestamp
                                if created_at_str:
                                    # Remove timezone info for comparison
                                    created_str = created_at_str.split('+')[0].split('Z')[0]
                                    created_dt = datetime.fromisoformat(created_str)
                                    
                                    if created_dt > cutoff_time:
                                        recent_videos.append(video)
                            except Exception:
                                # If parsing fails, include the video
                                recent_videos.append(video)
                        
                        logger.debug(
                            f"Collection {coll_id}: {len(collection_videos)} videos, "
                            f"{len(recent_videos)} created after recording start"
                        )
                        
                        # Filter out already processed videos and check for faces
                        new_videos = []
                        for video in recent_videos:
                            uuid = video.get('uuid')
                            if not uuid or uuid in self._processed_videos:
                                continue
                            
                            # Check if video has faces
                            has_faces, face_count = await self._check_video_faces(
                                client, headers, uuid
                            )
                            
                            if has_faces:
                                logger.info(
                                    f"Collection {coll_id}: Found video {uuid[:8]}... with {face_count} faces"
                                )
                                new_videos.append(video)
                                self._processed_videos.add(uuid)
                                self._stats['videos_discovered'] += 1
                        
                        # Add to THIS collection's pending queue
                        if not hasattr(self, '_pending_videos_by_collection'):
                            self._pending_videos_by_collection = {}
                        
                        if coll_id not in self._pending_videos_by_collection:
                            self._pending_videos_by_collection[coll_id] = []
                        
                        self._pending_videos_by_collection[coll_id].extend(new_videos)
                        
                        # Check if THIS collection has enough videos for a batch
                        pending_count = len(self._pending_videos_by_collection[coll_id])
                        if pending_count >= self.batch_size:
                            # Trigger batch for exactly batch_size videos from THIS collection only
                            videos_to_process = self._pending_videos_by_collection[coll_id][:self.batch_size]
                            self._pending_videos_by_collection[coll_id] = self._pending_videos_by_collection[coll_id][self.batch_size:]
                            
                            logger.info(
                                f"🚀 Triggering batch for collection {coll_id}: {len(videos_to_process)} videos"
                            )
                            await self._trigger_batch_processing(videos_to_process)
                            
                            # Check if this collection has another batch ready
                            if len(self._pending_videos_by_collection[coll_id]) >= self.batch_size:
                                logger.info(
                                    f"Collection {coll_id}: Another batch ready! "
                                    f"{len(self._pending_videos_by_collection[coll_id])} videos pending"
                                )
                        elif pending_count > 0:
                            logger.info(
                                f"Collection {coll_id}: Pending {pending_count}/{self.batch_size} videos (waiting for more)"
                            )
                    
                    except Exception as e:
                        logger.warning(f"Error processing collection {coll_id}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error in _poll_for_videos: {e}", exc_info=True)
            self._stats['polls_failed'] += 1
    
    async def _ensure_auth_token(self) -> bool:
        """Get or refresh authentication token."""
        import httpx
        
        # Check if token is still valid
        if self._auth_token and self._token_expires:
            if datetime.utcnow() < self._token_expires:
                return True
        
        try:
            # Get new token
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.node_url}/api/v1/users/login",
                    data={
                        "username": "fresh.user@example.com",
                        "password": "NewPassword234!"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._auth_token = data.get("access_token")
                    # Token expires in 1 hour
                    self._token_expires = datetime.utcnow() + timedelta(hours=1)
                    logger.info("Authentication token refreshed")
                    return True
                else:
                    logger.error(f"Auth failed: {response.status_code}")
                    return False
        
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}")
            return False
    
    async def _check_video_faces(
        self,
        client: 'httpx.AsyncClient',
        headers: dict,
        video_uuid: str
    ) -> tuple[bool, int]:
        """Check if video has cached face data."""
        try:
            response = await client.post(
                f"{self.vision_url}/faces/media/{video_uuid}/bulk-process",
                json={},
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                face_count = data.get('total_faces', 0)
                return face_count > 0, face_count
            return False, 0
        
        except Exception as e:
            logger.debug(f"Error checking faces for {video_uuid}: {e}")
            return False, 0
    
    async def _trigger_batch_processing(
        self,
        videos_to_process: list,
        is_final: bool = False
    ):
        """
        Trigger cross-video tracking for specified videos.
        
        Args:
            videos_to_process: List of video objects to process
            is_final: Whether this is the final batch on recording stop
        """
        if not videos_to_process:
            return
        
        try:
            import httpx
            
            batch_type = "FINAL" if is_final else "incremental"
            logger.info(
                f"🚀 Triggering {batch_type} batch processing for "
                f"{len(videos_to_process)} videos with explicit UUIDs"
            )
            
            # Extract video UUIDs
            video_uuids = [v['uuid'] for v in videos_to_process if v.get('uuid')]
            
            if not video_uuids:
                logger.error("No valid video UUIDs found in videos_to_process!")
                return
            
            # Since we're providing explicit video_uuids, use dummy timestamps
            # The endpoint will process these specific videos regardless of time range
            # Videos are already sorted by created_at in chronological order
            from datetime import datetime as dt_class
            now = dt_class.utcnow()
            start_time = now.isoformat().replace('+00:00', 'Z')
            end_time = (now + timedelta(microseconds=1)).isoformat().replace('+00:00', 'Z')
            
            # Create tracking session with explicit video_uuids
            session_data = {
                "collections": [f"{self.collection_id} Collection"],
                "start_time": start_time.replace(
                    "+02:00", "Z"
                ).replace("+00:00", "Z"),
                "end_time": end_time.replace(
                    "+02:00", "Z"
                ).replace("+00:00", "Z"),
                "video_uuids": video_uuids,  # Explicit video UUIDs!
                "background_processing": True  # CRITICAL: Enable background processing for automatic execution
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.vmeta_url}/api/v1/cross-video/individuals"
                    f"/tracking/sessions",
                    json=session_data,
                    headers={
                        "Authorization": f"Bearer {self._auth_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    session_uuid = result.get('session_uuid', 'N/A')
                    logger.info(
                        f"✅ {batch_type.upper()} batch triggered! "
                        f"Session: {session_uuid}"
                    )
                    logger.info(
                        f"   Explicit UUIDs: {len(video_uuids)} videos - "
                        f"Status: {result.get('status')} - "
                        f"Total: {result.get('total_videos')}"
                    )
                    
                    self._stats['batches_triggered'] += 1
                    self._stats['last_batch_at'] = datetime.utcnow()
                    
                    # Update recording stats
                    for rec in self._active_recordings.values():
                        rec['batches_triggered'] = rec.get('batches_triggered', 0) + 1
                else:
                    logger.error(
                        f"Failed to trigger batch: {response.status_code} - "
                        f"{response.text}"
                    )
        
        except Exception as e:
            logger.error(f"Error triggering batch: {e}", exc_info=True)
    
    def get_status(self) -> dict:
        """
        Get current polling manager status.
        
        Returns:
            Status dictionary with recordings and statistics
        """
        # Calculate total pending videos across all collections
        total_pending = sum(
            len(videos) 
            for videos in self._pending_videos_by_collection.values()
        )
        
        # Per-collection pending counts
        pending_by_collection = {
            coll_id: len(videos)
            for coll_id, videos in self._pending_videos_by_collection.items()
            if videos  # Only include collections with pending videos
        }
        
        return {
            'enabled': self.enabled,
            'running': self._running,
            'poll_interval': self.poll_interval,
            'batch_size': self.batch_size,
            'active_recordings': len(self._active_recordings),
            'recordings': {
                coll_id: {
                    'session_uuid': info['session_uuid'],
                    'started_at': info['started_at'].isoformat(),
                    'duration_seconds': (
                        datetime.utcnow() - info['started_at']
                    ).total_seconds(),
                    'batches_triggered': info.get('batches_triggered', 0),
                    'pending_videos': pending_by_collection.get(coll_id, 0)
                }
                for coll_id, info in self._active_recordings.items()
            },
            'total_pending_videos': total_pending,
            'pending_by_collection': pending_by_collection,
            'statistics': self._stats
        }
    
    async def manual_trigger(self, collection_id: str = None) -> dict:
        """
        Manually trigger batch processing for pending videos.
        Useful for testing and debugging.
        
        Args:
            collection_id: Optional specific collection to trigger.
                          If None, triggers all collections.
        
        Returns:
            Result dictionary
        """
        if not self._pending_videos_by_collection:
            return {
                'status': 'no_videos',
                'message': 'No pending videos to process'
            }
        
        # If specific collection requested
        if collection_id:
            if collection_id not in self._pending_videos_by_collection:
                return {
                    'status': 'not_found',
                    'message': f'No pending videos for collection {collection_id}'
                }
            
            pending_videos = self._pending_videos_by_collection[collection_id]
            if not pending_videos:
                return {
                    'status': 'no_videos',
                    'message': f'No pending videos for collection {collection_id}'
                }
            
            video_count = len(pending_videos)
            await self._trigger_batch_processing(pending_videos, is_final=False)
            self._pending_videos_by_collection[collection_id] = []
            
            return {
                'status': 'success',
                'collection_id': collection_id,
                'videos_processed': video_count,
                'message': f'Manually triggered batch for collection {collection_id}: {video_count} videos'
            }
        
        # Trigger all collections
        total_videos = 0
        collections_triggered = []
        
        for coll_id, pending_videos in list(self._pending_videos_by_collection.items()):
            if pending_videos:
                video_count = len(pending_videos)
                await self._trigger_batch_processing(pending_videos, is_final=False)
                self._pending_videos_by_collection[coll_id] = []
                total_videos += video_count
                collections_triggered.append(coll_id)
        
        if total_videos == 0:
            return {
                'status': 'no_videos',
                'message': 'No pending videos to process'
            }
        
        return {
            'status': 'success',
            'videos_processed': total_videos,
            'collections': collections_triggered,
            'message': f'Manually triggered batches for {len(collections_triggered)} collections: {total_videos} videos'
        }
