"""
PPL Meta Orchestrator - People Counters Repository.

Persistence layer for the People Counters automation worker.

See docs/proposals/people-counters.md (§5.2, §5.5, §5.5.1, §5.5.2).

This module owns the `people_counters_jobs` table — the orchestrator's
durable record of "work that needs to be done" for the automated batched
MVR pipeline. Successful merge results are written by vmeta into
`mvr_search_sessions` (rows tagged with the matching `batch_key`).

Design notes:
- Tier ordering for backlog dispatch (§5.5.2):
    0 = today (current local day)
    1 = yesterday
    2 = stale refresh (re-merge after invalidation)
    3 = older backfill
  Lower tier numbers are dispatched first.
- `claim_batch()` uses SELECT ... FOR UPDATE SKIP LOCKED to allow multiple
  workers to safely race for the next pending row.
- `reset_orphans()` is called once at worker startup to recover rows whose
  worker process died mid-flight (heartbeat older than threshold).
"""

import logging
import uuid as _uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# Status constants — keep aligned with the migration's CHECK contract (informal).
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_DEAD_LETTER = "dead_letter"

# Priority tiers (lower = dispatched first).
TIER_TODAY = 0
TIER_YESTERDAY = 1
TIER_STALE_REFRESH = 2
TIER_OLDER_BACKFILL = 3


class PeopleCountersRepository:
    """Repository for `people_counters_jobs` rows."""

    def __init__(self, db_session: Session):
        self.db = db_session

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_batch_key(camera_id: str, start_utc: datetime, end_utc: datetime) -> str:
        """
        Build the deterministic batch key shared with vmeta.

        Format must match `MVRRepository.build_batch_key` in
        ppl-meta-vmeta/src/database/mvr_repository.py.
        """
        return f"{camera_id}|{start_utc.isoformat()}|{end_utc.isoformat()}"

    @staticmethod
    def compute_priority_tier(
        batch_start_utc: datetime,
        is_stale_refresh: bool,
        now_utc: Optional[datetime] = None,
    ) -> int:
        """
        Compute the dispatch tier for a batch (§5.5.2).

        Today/yesterday windows are computed against UTC day boundaries to
        match the worker's enumeration logic. Operators using local-time
        days will see a small offset around midnight UTC — acceptable for
        a backlog ordering signal.
        """
        if is_stale_refresh:
            return TIER_STALE_REFRESH
        now = now_utc or datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        yesterday_start = today_start - timedelta(days=1)
        if batch_start_utc >= today_start:
            return TIER_TODAY
        if batch_start_utc >= yesterday_start:
            return TIER_YESTERDAY
        return TIER_OLDER_BACKFILL

    # ------------------------------------------------------------------ #
    # Insert / enumerate
    # ------------------------------------------------------------------ #

    def upsert_pending(
        self,
        *,
        camera_id: str,
        batch_start_utc: datetime,
        batch_end_utc: datetime,
        is_stale_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Insert a new pending job, or no-op if `batch_key` already exists.

        Returns the inserted row, or the existing one (if conflict).
        """
        batch_key = self.build_batch_key(camera_id, batch_start_utc, batch_end_utc)
        tier = self.compute_priority_tier(batch_start_utc, is_stale_refresh)
        try:
            self.db.execute(
                text(
                    """
                    INSERT INTO people_counters_jobs (
                        batch_key, camera_id, batch_start_utc, batch_end_utc,
                        status, priority_tier, is_stale_refresh, attempts
                    ) VALUES (
                        :batch_key, :camera_id, :start_utc, :end_utc,
                        :status, :tier, :stale, 0
                    )
                    ON CONFLICT (batch_key) DO NOTHING
                    """
                ),
                {
                    "batch_key": batch_key,
                    "camera_id": camera_id,
                    "start_utc": batch_start_utc,
                    "end_utc": batch_end_utc,
                    "status": STATUS_PENDING,
                    "tier": tier,
                    "stale": is_stale_refresh,
                },
            )
            self.db.commit()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("upsert_pending failed for %s: %s", batch_key, exc)
            raise
        return self.get_by_batch_key(batch_key)

    def requeue_stale(self, batch_key: str) -> bool:
        """
        Mark an existing job as a stale refresh and reset to pending.

        Used when an invalidation hook observes that a covered batch's
        underlying data changed (e.g. video re-materialized, MVR merged).
        Returns True if a row was updated.
        """
        try:
            result = self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :pending,
                           is_stale_refresh = TRUE,
                           priority_tier = :tier,
                           attempts = 0,
                           last_error = NULL,
                           heartbeat_at = NULL,
                           started_at = NULL,
                           completed_at = NULL
                     WHERE batch_key = :batch_key
                       AND status IN (:success, :failed, :dead_letter)
                    """
                ),
                {
                    "pending": STATUS_PENDING,
                    "tier": TIER_STALE_REFRESH,
                    "batch_key": batch_key,
                    "success": STATUS_SUCCESS,
                    "failed": STATUS_FAILED,
                    "dead_letter": STATUS_DEAD_LETTER,
                },
            )
            self.db.commit()
            return result.rowcount > 0
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("requeue_stale failed for %s: %s", batch_key, exc)
            raise

    def enumerate_pending(
        self,
        *,
        limit: int = 100,
        camera_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List pending jobs in dispatch order (tier ASC, oldest start first)."""
        params: Dict[str, Any] = {"status": STATUS_PENDING, "limit": limit}
        camera_clause = ""
        if camera_id:
            camera_clause = "AND camera_id = :camera_id"
            params["camera_id"] = camera_id
        rows = self.db.execute(
            text(
                f"""
                SELECT * FROM people_counters_jobs
                 WHERE status = :status {camera_clause}
                 ORDER BY priority_tier ASC, batch_start_utc ASC
                 LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Worker lifecycle
    # ------------------------------------------------------------------ #

    def claim_batch(
        self, *, max_attempts: int, daily_backfill_remaining: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the next pending batch.

        Uses SELECT ... FOR UPDATE SKIP LOCKED so multiple workers can
        race safely. Returns the claimed row, or None if the queue is
        empty / all rows blocked.

        If `daily_backfill_remaining` is 0, tier 3 (older backfill) is
        excluded from the claim — used to honour `people_counters_backfill_daily_budget`.
        """
        tier_filter = ""
        params: Dict[str, Any] = {
            "status": STATUS_PENDING,
            "running": STATUS_RUNNING,
        }
        if daily_backfill_remaining is not None and daily_backfill_remaining <= 0:
            tier_filter = "AND priority_tier < :backfill_tier"
            params["backfill_tier"] = TIER_OLDER_BACKFILL

        try:
            picked = self.db.execute(
                text(
                    f"""
                    SELECT id FROM people_counters_jobs
                     WHERE status = :status {tier_filter}
                     ORDER BY priority_tier ASC, batch_start_utc ASC
                     LIMIT 1
                     FOR UPDATE SKIP LOCKED
                    """
                ),
                params,
            ).first()
            if picked is None:
                self.db.commit()
                return None

            row = self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :running,
                           attempts = attempts + 1,
                           started_at = NOW(),
                           heartbeat_at = NOW(),
                           last_error = NULL
                     WHERE id = :id
                     RETURNING *
                    """
                ),
                {"running": STATUS_RUNNING, "id": picked[0]},
            ).mappings().first()
            self.db.commit()
            # Enforce attempt budget — if the new attempt count exceeds the
            # caller's limit, refuse the claim and dead-letter immediately.
            if row and row["attempts"] > max_attempts:
                self.dead_letter(row["batch_key"], reason="max_attempts_exceeded")
                return None
            return dict(row) if row else None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("claim_batch failed: %s", exc)
            raise

    def heartbeat(self, batch_key: str) -> None:
        """Update the worker heartbeat for a running batch."""
        try:
            self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET heartbeat_at = NOW()
                     WHERE batch_key = :batch_key AND status = :running
                    """
                ),
                {"batch_key": batch_key, "running": STATUS_RUNNING},
            )
            self.db.commit()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.warning("heartbeat failed for %s: %s", batch_key, exc)

    def complete_batch(
        self, batch_key: str, *, search_session_uuid: Optional[str] = None
    ) -> None:
        """Mark a batch as successfully merged."""
        try:
            self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :success,
                           completed_at = NOW(),
                           heartbeat_at = NULL,
                           last_error = NULL,
                           search_session_uuid = :sess
                     WHERE batch_key = :batch_key
                    """
                ),
                {
                    "success": STATUS_SUCCESS,
                    "batch_key": batch_key,
                    "sess": search_session_uuid,
                },
            )
            self.db.commit()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("complete_batch failed for %s: %s", batch_key, exc)
            raise

    def fail_batch(
        self,
        batch_key: str,
        *,
        error: str,
        max_attempts: int,
    ) -> str:
        """
        Record a failed attempt. Returns the new status:
        - 'pending' if the row will be retried
        - 'dead_letter' if attempts have been exhausted
        """
        try:
            row = self.db.execute(
                text("SELECT attempts FROM people_counters_jobs WHERE batch_key = :bk"),
                {"bk": batch_key},
            ).first()
            if row is None:
                return STATUS_FAILED
            attempts = int(row[0])
            if attempts >= max_attempts:
                return self.dead_letter(batch_key, reason=error)
            self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :pending,
                           heartbeat_at = NULL,
                           last_error = :err
                     WHERE batch_key = :bk
                    """
                ),
                {"pending": STATUS_PENDING, "err": error[:8000], "bk": batch_key},
            )
            self.db.commit()
            return STATUS_PENDING
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("fail_batch failed for %s: %s", batch_key, exc)
            raise

    def dead_letter(self, batch_key: str, *, reason: str) -> str:
        """Move a batch to the dead-letter state."""
        try:
            self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :dl,
                           completed_at = NOW(),
                           heartbeat_at = NULL,
                           last_error = :err
                     WHERE batch_key = :bk
                    """
                ),
                {"dl": STATUS_DEAD_LETTER, "err": reason[:8000], "bk": batch_key},
            )
            self.db.commit()
            return STATUS_DEAD_LETTER
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("dead_letter failed for %s: %s", batch_key, exc)
            raise

    def reset_orphans(self, *, heartbeat_timeout_seconds: int = 180) -> int:
        """
        Reset 'running' rows whose worker died (stale heartbeat) back to
        pending so they can be retried. Called once at worker startup
        and periodically by the supervisor loop.
        """
        try:
            cutoff = datetime.utcnow() - timedelta(seconds=heartbeat_timeout_seconds)
            result = self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :pending,
                           heartbeat_at = NULL,
                           last_error = COALESCE(last_error, '') ||
                                        ' [orphan-reset at ' || NOW()::text || ']'
                     WHERE status = :running
                       AND (heartbeat_at IS NULL OR heartbeat_at < :cutoff)
                    """
                ),
                {
                    "pending": STATUS_PENDING,
                    "running": STATUS_RUNNING,
                    "cutoff": cutoff,
                },
            )
            self.db.commit()
            count = result.rowcount or 0
            if count:
                logger.info("Reset %d orphaned people-counters jobs", count)
            return count
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("reset_orphans failed: %s", exc)
            raise

    def retry_dead_letter(self, batch_key: str) -> bool:
        """
        Manually retry a dead-lettered batch (admin endpoint).
        Resets attempts to 0 and returns the row to pending.
        """
        try:
            result = self.db.execute(
                text(
                    """
                    UPDATE people_counters_jobs
                       SET status = :pending,
                           attempts = 0,
                           last_error = NULL,
                           heartbeat_at = NULL,
                           started_at = NULL,
                           completed_at = NULL
                     WHERE batch_key = :bk
                       AND status IN (:dl, :failed)
                    """
                ),
                {
                    "pending": STATUS_PENDING,
                    "dl": STATUS_DEAD_LETTER,
                    "failed": STATUS_FAILED,
                    "bk": batch_key,
                },
            )
            self.db.commit()
            return result.rowcount > 0
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.db.rollback()
            logger.error("retry_dead_letter failed for %s: %s", batch_key, exc)
            raise

    # ------------------------------------------------------------------ #
    # Read / diagnostics
    # ------------------------------------------------------------------ #

    def get_by_batch_key(self, batch_key: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text("SELECT * FROM people_counters_jobs WHERE batch_key = :bk"),
            {"bk": batch_key},
        ).mappings().first()
        return dict(row) if row else None

    def list_jobs(
        self,
        *,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Filtered listing for the Settings UI 'Batches Browser' tab."""
        clauses: List[str] = []
        params: Dict[str, Any] = {"limit": limit}
        if camera_id:
            clauses.append("camera_id = :camera_id")
            params["camera_id"] = camera_id
        if status:
            clauses.append("status = :status")
            params["status"] = status
        if date_from:
            clauses.append("batch_start_utc >= :date_from")
            params["date_from"] = date_from
        if date_to:
            clauses.append("batch_end_utc <= :date_to")
            params["date_to"] = date_to
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.execute(
            text(
                f"""
                SELECT * FROM people_counters_jobs
                 {where}
                 ORDER BY batch_start_utc DESC
                 LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
        return [dict(r) for r in rows]

    def list_dead_letter(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT * FROM people_counters_jobs
                 WHERE status = :dl
                 ORDER BY completed_at DESC NULLS LAST, updated_at DESC
                 LIMIT :limit
                """
            ),
            {"dl": STATUS_DEAD_LETTER, "limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]

    def status_summary(self) -> Dict[str, int]:
        """Aggregate status counts for the Settings UI 'Status' tab."""
        rows = self.db.execute(
            text(
                """
                SELECT status, COUNT(*) AS n
                  FROM people_counters_jobs
                 GROUP BY status
                """
            )
        ).all()
        out = {
            STATUS_PENDING: 0,
            STATUS_RUNNING: 0,
            STATUS_SUCCESS: 0,
            STATUS_FAILED: 0,
            STATUS_DEAD_LETTER: 0,
        }
        for status, count in rows:
            out[status] = int(count)
        return out

    def daily_backfill_count(self, *, since_utc: datetime) -> int:
        """
        Count of tier-3 (older backfill) rows that left the pending state
        since `since_utc` — used to enforce the daily backfill budget.
        """
        row = self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM people_counters_jobs
                 WHERE priority_tier = :tier
                   AND started_at IS NOT NULL
                   AND started_at >= :since
                """
            ),
            {"tier": TIER_OLDER_BACKFILL, "since": since_utc},
        ).first()
        return int(row[0]) if row else 0


__all__ = [
    "PeopleCountersRepository",
    "STATUS_PENDING",
    "STATUS_RUNNING",
    "STATUS_SUCCESS",
    "STATUS_FAILED",
    "STATUS_DEAD_LETTER",
    "TIER_TODAY",
    "TIER_YESTERDAY",
    "TIER_STALE_REFRESH",
    "TIER_OLDER_BACKFILL",
]


# Suppress pylint complaint about unused import in some envs.
_ = _uuid
