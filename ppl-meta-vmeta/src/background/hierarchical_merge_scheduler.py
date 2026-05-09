"""
Hierarchical MVR Merge Scheduler (Queue C)

Background scheduler for automatic hierarchical merging of MVR People.
Runs in two modes:
1. Post-Session: After recording session MVR creation completes
2. Periodic: Every N minutes for recent MVR people

Part of the three-queue architecture:
- Queue A: Videos → Individuals
- Queue B: Individuals → MVR People
- Queue C: MVR People → Super-Individuals (THIS FILE)

Two-Tier Merge (v3.2):
- Tier 1: Source-separated hard merge (recording and instant detection
  MVR people are merged independently within their own source)
- Tier 2: Cross-source soft link (surviving winners from different sources
  that represent the same person are linked via identity_group_uuid
  without orphaning either side)

Created: January 9, 2026
Author: PPL Meta Platform Team
Version: 2.23.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from services.hierarchical_mvr_merger import HierarchicalMVRMerger
from database.mvr_repository import MVRRepository
from services.mvr_matcher import MVRMatcher

logger = logging.getLogger(__name__)


class HierarchicalMergeScheduler:
    """
    Background scheduler for hierarchical MVR merging (Queue C).
    
    Consolidates duplicate MVR people across batches/sessions into
    super-individuals for improved accuracy and deduplication.
    
    Features:
    - Post-session merging: Triggers after Queue B completes
    - Periodic merging: Runs every N minutes for recent MVR people
    - Task tracking: Monitor merge progress and results
    - Retry logic: Handles transient failures gracefully
    """
    
    def __init__(
        self,
        repository: MVRRepository,
        mvr_matcher: MVRMatcher,
        enabled: bool = True,
        periodic_interval_minutes: int = 30,
        lookback_minutes: int = 120,
        post_session_delay_seconds: int = 30,
        similarity_threshold: float = 0.60,
        max_retries: int = 3,
        retry_delay_seconds: float = 10.0
    ):
        """
        Initialize hierarchical merge scheduler.
        
        Args:
            repository: MVR database repository
            mvr_matcher: MVR matcher for quality comparison
            enabled: Whether scheduler is enabled (default True)
            periodic_interval_minutes: Interval for periodic merges (default 30)
            lookback_minutes: How far back to look for MVR people (default 120)
            post_session_delay_seconds: Delay before post-session merge (default 30)
            similarity_threshold: Similarity threshold for merging (default 0.60)
            max_retries: Maximum retry attempts (default 3)
            retry_delay_seconds: Delay between retries (default 10.0)
        """
        self.repository = repository
        self.mvr_matcher = mvr_matcher
        self.enabled = enabled
        self.periodic_interval_minutes = periodic_interval_minutes
        self.lookback_minutes = lookback_minutes
        self.post_session_delay_seconds = post_session_delay_seconds
        self.similarity_threshold = similarity_threshold
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        
        # Task tracking
        self._pending_tasks: Dict[UUID, asyncio.Task] = {}
        self._completed_tasks: Dict[UUID, Dict] = {}
        self._failed_tasks: Dict[UUID, Dict] = {}
        
        # Periodic task
        self._periodic_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(
            f"✅ HierarchicalMergeScheduler initialized "
            f"(enabled={enabled}, periodic={periodic_interval_minutes}min, "
            f"lookback={lookback_minutes}min, threshold={similarity_threshold})"
        )
    
    # ========================================================================
    # POST-SESSION MERGING
    # ========================================================================
    
    async def queue_post_session_merge(
        self,
        session_uuid: UUID,
        mvr_uuids: List[UUID],
        delay_seconds: Optional[int] = None
    ) -> Dict:
        """
        Queue hierarchical merge after session MVR creation completes.
        
        This is triggered by Queue B after MVR people are created.
        Adds a delay to ensure all background processing is complete.
        
        Args:
            session_uuid: Tracking session UUID
            mvr_uuids: List of MVR UUIDs created in this session
            delay_seconds: Optional delay override (uses config default if None)
        
        Returns:
            Task status dict
        """
        if not self.enabled:
            logger.info("[Queue C] Scheduler disabled, skipping post-session merge")
            return {"status": "disabled"}
        
        if not mvr_uuids:
            logger.warning(f"[Queue C] No MVR UUIDs provided for session {session_uuid}")
            return {"status": "skipped", "reason": "no_mvr_uuids"}
        
        delay = delay_seconds if delay_seconds is not None else self.post_session_delay_seconds
        
        # Create background task with delay
        task = asyncio.create_task(
            self._process_post_session_merge(
                session_uuid=session_uuid,
                mvr_uuids=mvr_uuids,
                delay_seconds=delay
            )
        )
        
        # Track task
        self._pending_tasks[session_uuid] = task
        
        logger.info(
            f"🔄 [Queue C] Queued post-session merge for {session_uuid}: "
            f"{len(mvr_uuids)} MVR people (delay={delay}s)"
        )
        
        return {
            "task_id": str(session_uuid),
            "status": "queued",
            "mvr_count": len(mvr_uuids),
            "delay_seconds": delay,
            "queued_at": datetime.utcnow().isoformat()
        }
    
    async def _process_post_session_merge(
        self,
        session_uuid: UUID,
        mvr_uuids: List[UUID],
        delay_seconds: int
    ) -> None:
        """
        Internal: Process post-session hierarchical merge with retry logic.
        
        Pipeline:
        1. Wait for delay (ensure all background tasks complete)
        2. Run hierarchical merge on session MVR people
        3. Update session with super-individual results
        4. Track success/failure
        """
        start_time = datetime.utcnow()
        retry_count = 0
        
        # Wait for delay
        if delay_seconds > 0:
            logger.info(
                f"[Queue C] Waiting {delay_seconds}s before merging session {session_uuid}"
            )
            await asyncio.sleep(delay_seconds)
        
        while retry_count <= self.max_retries:
            try:
                logger.info(
                    f"🔄 [Queue C] Processing post-session merge for {session_uuid} "
                    f"(attempt {retry_count + 1}/{self.max_retries + 1})"
                )
                
                # Run hierarchical merge
                merger = HierarchicalMVRMerger(
                    repository=self.repository,
                    mvr_matcher=self.mvr_matcher
                )
                
                result = await merger.merge_hierarchical(
                    mvr_uuids=mvr_uuids,
                    similarity_threshold=self.similarity_threshold,
                    min_similarity_check=0.50
                )
                
                stats = result['statistics']
                logger.info(
                    f"✅ [Queue C] Post-session merge complete for {session_uuid}: "
                    f"{stats['total_mvr']} MVR → {stats['super_individuals']} super-individuals "
                    f"({stats['merges_performed']} merges)"
                )
                
                # Update session with super-individual count
                await self._update_session_hierarchical_status(
                    session_uuid=session_uuid,
                    super_individual_count=stats['super_individuals'],
                    merge_count=stats['merges_performed']
                )
                
                # Mark success
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                self._completed_tasks[session_uuid] = {
                    "session_uuid": str(session_uuid),
                    "mvr_count": stats['total_mvr'],
                    "super_individual_count": stats['super_individuals'],
                    "merges_performed": stats['merges_performed'],
                    "processing_time_seconds": processing_time,
                    "retry_count": retry_count,
                    "completed_at": end_time.isoformat()
                }
                
                # Remove from pending
                if session_uuid in self._pending_tasks:
                    del self._pending_tasks[session_uuid]
                
                return
                
            except Exception as e:
                retry_count += 1
                
                if retry_count > self.max_retries:
                    logger.error(
                        f"❌ [Queue C] Post-session merge failed for {session_uuid} "
                        f"after {self.max_retries} retries: {e}"
                    )
                    
                    self._failed_tasks[session_uuid] = {
                        "session_uuid": str(session_uuid),
                        "mvr_count": len(mvr_uuids),
                        "error": str(e),
                        "retry_count": retry_count - 1,
                        "failed_at": datetime.utcnow().isoformat()
                    }
                    
                    if session_uuid in self._pending_tasks:
                        del self._pending_tasks[session_uuid]
                    
                    return
                else:
                    logger.warning(
                        f"⚠️ [Queue C] Retry {retry_count}/{self.max_retries} "
                        f"for session {session_uuid} after error: {e}"
                    )
                    await asyncio.sleep(self.retry_delay_seconds)
    
    # ========================================================================
    # PERIODIC MERGING
    # ========================================================================
    
    async def start_periodic_merge(self) -> None:
        """
        Start periodic hierarchical merging background task.
        
        Runs every N minutes (configured by periodic_interval_minutes)
        and merges MVR people created in the last M minutes (lookback_minutes).
        """
        if not self.enabled:
            logger.info("[Queue C] Scheduler disabled, not starting periodic merge")
            return
        
        if self._periodic_task and not self._periodic_task.done():
            logger.warning("[Queue C] Periodic merge already running")
            return
        
        self._shutdown_event.clear()
        self._periodic_task = asyncio.create_task(self._run_periodic_merge_loop())
        
        logger.info(
            f"✅ [Queue C] Started periodic merge "
            f"(interval={self.periodic_interval_minutes}min, "
            f"lookback={self.lookback_minutes}min)"
        )
    
    async def stop_periodic_merge(self) -> None:
        """Stop periodic merging background task."""
        if not self._periodic_task or self._periodic_task.done():
            logger.info("[Queue C] Periodic merge not running")
            return
        
        logger.info("[Queue C] Stopping periodic merge...")
        self._shutdown_event.set()
        
        try:
            await asyncio.wait_for(self._periodic_task, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("[Queue C] Periodic merge did not stop gracefully")
            self._periodic_task.cancel()
        
        logger.info("✅ [Queue C] Periodic merge stopped")
    
    async def _run_periodic_merge_loop(self) -> None:
        """Internal: Periodic merge loop."""
        logger.info(f"[Queue C] Periodic merge loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for interval or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.periodic_interval_minutes * 60
                    )
                    # Shutdown event triggered
                    break
                except asyncio.TimeoutError:
                    # Interval elapsed, run merge
                    pass
                
                logger.info("[Queue C] Running periodic hierarchical merge...")
                await self._run_periodic_merge()
                
            except Exception as e:
                logger.error(f"[Queue C] Periodic merge error: {e}", exc_info=True)
                # Continue loop despite error
                await asyncio.sleep(60)  # Wait 1 minute before retry
        
        logger.info("[Queue C] Periodic merge loop stopped")
    
    async def _run_periodic_merge(self) -> None:
        """
        Internal: Execute two-tier periodic merge for recent MVR people.

        Tier 1 — Source-separated hard merge:
          Pass 1: recording_pipeline MVR people only
          Pass 2: instant_detection MVR people only
          Within each pass losers are orphaned (same as before).

        Tier 2 — Cross-source soft link:
          All surviving (non-orphaned) winners from both sources are compared.
          Matches above the similarity threshold share an identity_group_uuid
          without orphaning either side.
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.lookback_minutes)

            # ── Tier 1: Source-separated hard merges ──────────────────────
            for source_type in ('recording_pipeline', 'instant_detection'):
                async with self.repository.pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT mp.mvr_people_uuid
                        FROM mvr_people mp
                        JOIN tracking_sessions ts
                          ON mp.created_by_session = ts.session_uuid
                        WHERE mp.created_at >= $1
                          AND ts.source_type = $2
                        ORDER BY mp.created_at DESC
                    """, cutoff_time, source_type)

                mvr_uuids = [row['mvr_people_uuid'] for row in rows]

                if not mvr_uuids:
                    logger.info(
                        f"[Queue C] Tier 1: No recent {source_type} MVR people "
                        f"(lookback={self.lookback_minutes}min)"
                    )
                    continue

                logger.info(
                    f"[Queue C] Tier 1: Found {len(mvr_uuids)} {source_type} MVR people "
                    f"in last {self.lookback_minutes} minutes"
                )

                merger = HierarchicalMVRMerger(
                    repository=self.repository,
                    mvr_matcher=self.mvr_matcher
                )

                result = await merger.merge_hierarchical(
                    mvr_uuids=mvr_uuids,
                    similarity_threshold=self.similarity_threshold,
                    min_similarity_check=0.50
                )

                stats = result['statistics']
                logger.info(
                    f"✅ [Queue C] Tier 1 ({source_type}): "
                    f"{stats['total_mvr']} MVR → {stats['super_individuals']} super-individuals "
                    f"({stats['merges_performed']} merges)"
                )

            # ── Tier 2: Cross-source soft link ────────────────────────────
            await self._run_cross_source_link(cutoff_time)

        except Exception as e:
            logger.error(f"[Queue C] Periodic merge failed: {e}", exc_info=True)
            raise

    async def _run_cross_source_link(self, cutoff_time: datetime) -> None:
        """
        Tier 2: Link surviving MVR winners across sources via identity_group_uuid.

        Fetches all non-orphaned MVR people created since *cutoff_time*,
        computes pairwise cosine similarity, finds connected components,
        and assigns the same identity_group_uuid to each component that
        spans more than one MVR person.  No MVR is orphaned in this step.
        """
        try:
            merger = HierarchicalMVRMerger(
                repository=self.repository,
                mvr_matcher=self.mvr_matcher
            )

            # Fetch all surviving MVR people in the lookback window
            async with self.repository.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT mvr_people_uuid
                    FROM mvr_people
                    WHERE created_at >= $1
                      AND is_orphaned = false
                      AND merged_into_mvr_uuid IS NULL
                    ORDER BY created_at DESC
                """, cutoff_time)

            mvr_uuids = [row['mvr_people_uuid'] for row in rows]

            if len(mvr_uuids) < 2:
                logger.info("[Queue C] Tier 2: Fewer than 2 surviving MVR people, skipping cross-source link")
                return

            logger.info(f"[Queue C] Tier 2: Evaluating {len(mvr_uuids)} surviving MVR people for cross-source linking")

            # Fetch embeddings
            mvr_people = await merger._fetch_mvr_people(mvr_uuids)

            if len(mvr_people) < 2:
                return

            # Calculate similarity matrix
            similarity_matrix = await merger._calculate_similarity_matrix(
                mvr_people,
                min_similarity=0.50
            )

            # Find connected components
            merge_groups = merger._find_merge_groups(
                mvr_people,
                similarity_matrix,
                self.similarity_threshold
            )

            # Assign identity_group_uuid to multi-member groups
            groups_linked = 0
            mvr_linked = 0

            async with self.repository.pool.acquire() as conn:
                for group in merge_groups:
                    if len(group) < 2:
                        continue

                    group_uuid = uuid4()
                    group_uuids = [m["mvr_people_uuid"] for m in group]

                    await conn.execute("""
                        UPDATE mvr_people
                        SET identity_group_uuid = $1
                        WHERE mvr_people_uuid = ANY($2::uuid[])
                    """, group_uuid, group_uuids)

                    groups_linked += 1
                    mvr_linked += len(group)

                # Clear stale identity_group_uuid for MVR people that are no longer
                # part of any cross-source group (singleton after re-evaluation)
                singleton_uuids = [
                    group[0]["mvr_people_uuid"]
                    for group in merge_groups
                    if len(group) == 1
                ]
                if singleton_uuids:
                    await conn.execute("""
                        UPDATE mvr_people
                        SET identity_group_uuid = NULL
                        WHERE mvr_people_uuid = ANY($1::uuid[])
                          AND identity_group_uuid IS NOT NULL
                    """, singleton_uuids)

            logger.info(
                f"✅ [Queue C] Tier 2: Linked {mvr_linked} MVR people into "
                f"{groups_linked} cross-source identity groups"
            )

        except Exception as e:
            logger.error(f"[Queue C] Cross-source link failed: {e}", exc_info=True)
            # Non-fatal — Tier 1 merges already succeeded
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    async def _update_session_hierarchical_status(
        self,
        session_uuid: UUID,
        super_individual_count: int,
        merge_count: int
    ) -> None:
        """Update tracking session with hierarchical merge results."""
        # Use repository's connection pool directly
        try:
            async with self.repository.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE tracking_sessions
                    SET failed_videos = array_append(
                        failed_videos,
                        $2
                    )
                    WHERE session_uuid = $1
                """, session_uuid,
                     f"hierarchical_merge: super_individuals={super_individual_count}, "
                     f"merges={merge_count}")
        except Exception as e:
            logger.error(f"Failed to update session hierarchical status: {e}")
    
    def get_statistics(self) -> Dict:
        """Get scheduler statistics."""
        pending_count = len(self._pending_tasks)
        completed_count = len(self._completed_tasks)
        failed_count = len(self._failed_tasks)
        
        total_merges = sum(
            task.get("merges_performed", 0)
            for task in self._completed_tasks.values()
        )
        
        return {
            "enabled": self.enabled,
            "periodic_running": self._periodic_task and not self._periodic_task.done(),
            "pending_tasks": pending_count,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "total_merges_performed": total_merges,
            "config": {
                "periodic_interval_minutes": self.periodic_interval_minutes,
                "lookback_minutes": self.lookback_minutes,
                "post_session_delay_seconds": self.post_session_delay_seconds,
                "similarity_threshold": self.similarity_threshold
            }
        }
