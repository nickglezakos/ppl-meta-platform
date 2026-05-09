"""
PPL Meta Orchestrator - People Counters Worker.

Long-lived asyncio task that drains the `people_counters_jobs` queue and
calls the vmeta `persisted-merge-session-batch` endpoint for each batch.

Lifecycle (see docs/proposals/people-counters.md §5.5, §5.5.1, §5.5.2):
1. Startup recovery pass — `reset_orphans()` returns dead-worker rows to
   pending, then a one-shot enumeration ensures today/yesterday windows
   are queued.
2. Supervisor loop — every tick: re-read settings, check load gates,
   compute the active worker concurrency (quiet-hours scaled), claim up
   to N batches and dispatch them to vmeta concurrently.
3. Per-batch worker — fetches videos for the camera+window from the
   media service, calls the vmeta wrapper, heartbeats every ~30s,
   marks success / fail / dead-letter based on the outcome.

The worker is designed to be cheap to disable: setting
`people_counters_enabled = 0` causes the supervisor loop to idle without
claiming new work (in-flight tasks finish naturally).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from database import SessionLocal
from service_auth import service_auth
from services.people_counters_repository import (
    PeopleCountersRepository,
    STATUS_PENDING,
    STATUS_RUNNING,
    TIER_OLDER_BACKFILL,
)
from services.workflow_settings_service import WorkflowSettingsService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------- #
# Settings access
# ---------------------------------------------------------------------- #

# Default values mirror the migration's seed rows. They are used when the
# workflow_settings table is unreachable (e.g. migration not yet applied).
_DEFAULTS: Dict[str, float] = {
    "people_counters_enabled": 0.0,
    "people_counters_batch_seconds": 3600.0,
    "people_counters_workers": 2.0,
    "people_counters_quiet_workers": 4.0,
    "people_counters_max_cpu_pct": 60.0,
    "people_counters_max_inflight": 5.0,
    "people_counters_backoff_seconds": 60.0,
    "people_counters_per_batch_timeout_seconds": 300.0,
    "people_counters_max_attempts": 3.0,
    "people_counters_backfill_daily_budget": 200.0,
    "people_counters_quiet_hours_start": 1.0,
    "people_counters_quiet_hours_end": 6.0,
}


async def _read_settings() -> Dict[str, float]:
    """Pull the latest people_counters_* values from workflow_settings."""
    out = dict(_DEFAULTS)
    db = SessionLocal()
    try:
        svc = WorkflowSettingsService(db)
        for key in _DEFAULTS:
            try:
                value = await svc.get_setting(key)
            except Exception:  # pylint: disable=broad-exception-caught
                value = None
            if value is not None:
                out[key] = float(value)
    finally:
        db.close()
    return out


def _is_quiet_hours(now_local: datetime, start_hr: int, end_hr: int) -> bool:
    """Inclusive-start, exclusive-end. Equal start/end disables quiet-hours."""
    if start_hr == end_hr:
        return False
    h = now_local.hour
    if start_hr < end_hr:
        return start_hr <= h < end_hr
    # Wraps midnight (e.g. 22 → 6).
    return h >= start_hr or h < end_hr


# ---------------------------------------------------------------------- #
# HTTP helpers
# ---------------------------------------------------------------------- #


def _service_token() -> Optional[str]:
    """Mint a short-lived service JWT for vmeta/media calls."""
    try:
        return service_auth.create_service_token(
            user_id="orchestrator-people-counters", expires_hours=1
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("Failed to mint service token: %s", exc)
        return None


def _service_urls() -> Tuple[str, str, str]:
    return (
        os.getenv("VMETA_SERVICE_URL", "http://localhost:8008").rstrip("/"),
        os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000").rstrip("/"),
        os.getenv("CAMERA_SERVICE_URL", "http://localhost:8005").rstrip("/"),
    )


async def _list_videos_for_window(
    *,
    media_url: str,
    camera_id: str,
    start_utc: datetime,
    end_utc: datetime,
    auth_header: Dict[str, str],
    timeout: float,
) -> List[Dict[str, Any]]:
    """
    Page through media-service `/api/v1/media/search` for a (camera, window).

    Returns a list of {uuid, media_timestamp, ...} dicts.
    """
    page_size = 500
    page = 1
    out: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            params: Dict[str, Any] = {
                "collection": camera_id,
                "start_time": start_utc.isoformat(),
                "end_time": end_utc.isoformat(),
                "page_size": page_size,
                "page": page,
            }
            try:
                resp = await client.get(
                    f"{media_url}/api/v1/media/search",
                    params=params,
                    headers=auth_header,
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning(
                    "media search failed for camera=%s page=%d: %s",
                    camera_id, page, exc,
                )
                break
            payload = resp.json()
            batch = payload if isinstance(payload, list) else payload.get("results", [])
            if not batch:
                break
            out.extend(batch)
            if len(batch) < page_size:
                break
            page += 1
            if page > 50:  # safety stop — 25k videos per batch is already absurd
                logger.warning("media search hit page-cap for camera=%s window=%s", camera_id, start_utc)
                break
    return out


async def _list_active_cameras(
    *, camera_url: str, auth_header: Dict[str, str], timeout: float
) -> List[str]:
    """Return device_ids of active (non-archived) cameras."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for path in ("/api/v1/cameras/active", "/api/v1/cameras/"):
            try:
                resp = await client.get(f"{camera_url}{path}", headers=auth_header)
                resp.raise_for_status()
                payload = resp.json()
                items = payload if isinstance(payload, list) else payload.get("cameras", [])
                ids = [
                    str(c.get("device_id") or c.get("id"))
                    for c in items
                    if (c.get("device_id") or c.get("id"))
                ]
                if ids:
                    return ids
            except httpx.HTTPError as exc:
                logger.debug("camera enumeration via %s failed: %s", path, exc)
    return []


# ---------------------------------------------------------------------- #
# Batch enumeration (queue producer)
# ---------------------------------------------------------------------- #


def _floor_to_batch(ts_utc: datetime, batch_seconds: int) -> datetime:
    """Floor a UTC timestamp to the nearest batch boundary."""
    epoch = int(ts_utc.replace(tzinfo=timezone.utc).timestamp())
    floored = epoch - (epoch % batch_seconds)
    return datetime.utcfromtimestamp(floored)


async def enqueue_windows(
    *,
    camera_ids: List[str],
    range_start_utc: datetime,
    range_end_utc: datetime,
    batch_seconds: int,
) -> int:
    """
    Idempotently insert pending rows for every (camera × batch-window) tuple
    in [range_start, range_end). Returns the number of new rows actually
    inserted (excludes ON CONFLICT no-ops — best-effort estimate).
    """
    if not camera_ids:
        return 0
    inserted = 0
    db = SessionLocal()
    try:
        repo = PeopleCountersRepository(db)
        cursor = _floor_to_batch(range_start_utc, batch_seconds)
        end_floor = _floor_to_batch(range_end_utc, batch_seconds)
        while cursor < end_floor:
            window_end = cursor + timedelta(seconds=batch_seconds)
            for camera_id in camera_ids:
                before = repo.get_by_batch_key(
                    PeopleCountersRepository.build_batch_key(camera_id, cursor, window_end)
                )
                if before is not None:
                    continue
                repo.upsert_pending(
                    camera_id=camera_id,
                    batch_start_utc=cursor,
                    batch_end_utc=window_end,
                )
                inserted += 1
            cursor = window_end
    finally:
        db.close()
    return inserted


# ---------------------------------------------------------------------- #
# Per-batch worker
# ---------------------------------------------------------------------- #


async def _process_batch(
    *,
    batch: Dict[str, Any],
    settings_snapshot: Dict[str, float],
    urls: Tuple[str, str, str],
    auth_header: Dict[str, str],
) -> None:
    """Run a single claimed batch end-to-end."""
    vmeta_url, media_url, _ = urls
    batch_key = batch["batch_key"]
    camera_id = batch["camera_id"]
    start_utc = batch["batch_start_utc"]
    end_utc = batch["batch_end_utc"]
    per_batch_timeout = settings_snapshot["people_counters_per_batch_timeout_seconds"]
    max_attempts = int(settings_snapshot["people_counters_max_attempts"])

    heartbeat_task: Optional[asyncio.Task] = None

    async def _heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(30)
            db = SessionLocal()
            try:
                PeopleCountersRepository(db).heartbeat(batch_key)
            finally:
                db.close()

    try:
        heartbeat_task = asyncio.create_task(_heartbeat_loop())

        videos = await _list_videos_for_window(
            media_url=media_url,
            camera_id=camera_id,
            start_utc=start_utc,
            end_utc=end_utc,
            auth_header=auth_header,
            timeout=min(per_batch_timeout, 60.0),
        )
        video_uuids = [str(v["uuid"]) for v in videos if v.get("uuid")]
        video_details = [
            {
                "uuid": str(v["uuid"]),
                "camera_id": camera_id,
                "media_timestamp": v.get("media_timestamp") or v.get("created_at"),
            }
            for v in videos
            if v.get("uuid")
        ]

        payload = {
            "batch_camera_id": camera_id,
            "batch_start_utc": start_utc.isoformat(),
            "batch_end_utc": end_utc.isoformat(),
            "video_uuids": video_uuids,
            "video_details": video_details,
            "ignore_existing_session": False,
        }
        async with httpx.AsyncClient(timeout=per_batch_timeout) as client:
            resp = await client.post(
                f"{vmeta_url}/api/v1/mvr-people/search/by-videos/persisted-merge-session-batch",
                json=payload,
                headers=auth_header,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"vmeta returned {resp.status_code}: {resp.text[:500]}"
                )
            result = resp.json()

        session_uuid = result.get("search_session_uuid")
        db = SessionLocal()
        try:
            PeopleCountersRepository(db).complete_batch(
                batch_key, search_session_uuid=session_uuid
            )
        finally:
            db.close()

        logger.info(
            "people-counters batch ok: key=%s videos=%d people=%s",
            batch_key, len(video_uuids), result.get("people_count"),
        )

    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("people-counters batch failed: key=%s err=%s", batch_key, exc)
        db = SessionLocal()
        try:
            PeopleCountersRepository(db).fail_batch(
                batch_key, error=str(exc), max_attempts=max_attempts
            )
        finally:
            db.close()
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except (asyncio.CancelledError, Exception):  # pylint: disable=broad-exception-caught
                pass


# ---------------------------------------------------------------------- #
# Supervisor loop
# ---------------------------------------------------------------------- #


class PeopleCountersWorker:
    """Long-lived supervisor for the people-counters job queue."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()
        self._inflight: int = 0
        self._daily_backfill_started_at = datetime.utcnow()
        self._daily_backfill_count = 0

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running():
            return
        self._shutdown.clear()
        self._task = asyncio.create_task(self._run(), name="people-counters-supervisor")
        logger.info("People Counters worker supervisor started")

    async def stop(self) -> None:
        if not self.is_running():
            return
        self._shutdown.set()
        try:
            await asyncio.wait_for(self._task, timeout=10.0)
        except asyncio.TimeoutError:
            self._task.cancel()
        logger.info("People Counters worker supervisor stopped")

    # -------------------------------------------------------------- #

    def _reset_backfill_window_if_due(self) -> None:
        if datetime.utcnow() - self._daily_backfill_started_at >= timedelta(hours=24):
            self._daily_backfill_started_at = datetime.utcnow()
            self._daily_backfill_count = 0

    async def _startup_recovery(self, settings_snapshot: Dict[str, float]) -> None:
        db = SessionLocal()
        try:
            count = PeopleCountersRepository(db).reset_orphans(heartbeat_timeout_seconds=180)
            if count:
                logger.info("Startup recovery: reset %d orphaned people-counters jobs", count)
        finally:
            db.close()

        # Best-effort: ensure today + yesterday windows are queued for all
        # active cameras. Failure here is non-fatal (operators can also call
        # the manual /run-daily-batch endpoint).
        try:
            urls = _service_urls()
            token = _service_token()
            auth_header = {"Authorization": f"Bearer {token}"} if token else {}
            cameras = await _list_active_cameras(
                camera_url=urls[2], auth_header=auth_header, timeout=10.0
            )
            if cameras:
                batch_seconds = int(settings_snapshot["people_counters_batch_seconds"])
                now = datetime.utcnow()
                day_start = datetime(now.year, now.month, now.day)
                yesterday_start = day_start - timedelta(days=1)
                inserted = await enqueue_windows(
                    camera_ids=cameras,
                    range_start_utc=yesterday_start,
                    range_end_utc=now,
                    batch_seconds=batch_seconds,
                )
                if inserted:
                    logger.info(
                        "Startup recovery: queued %d new batches across %d cameras",
                        inserted, len(cameras),
                    )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Startup batch enumeration skipped: %s", exc)

    async def _tick(self, settings_snapshot: Dict[str, float]) -> None:
        """One supervisor iteration."""
        # Quiet-hours concurrency scaling.
        now_local = datetime.now()
        in_quiet = _is_quiet_hours(
            now_local,
            int(settings_snapshot["people_counters_quiet_hours_start"]),
            int(settings_snapshot["people_counters_quiet_hours_end"]),
        )
        target_workers = int(
            settings_snapshot["people_counters_quiet_workers"] if in_quiet
            else settings_snapshot["people_counters_workers"]
        )

        slots = max(0, target_workers - self._inflight)
        if slots == 0:
            await asyncio.sleep(2.0)
            return

        self._reset_backfill_window_if_due()
        max_backfill = int(settings_snapshot["people_counters_backfill_daily_budget"])
        backfill_remaining = max(0, max_backfill - self._daily_backfill_count)

        # Periodic orphan recovery in case a worker died after the supervisor
        # started but the orphan-timeout was not yet reached at startup.
        if int(time.time()) % 300 < 2:  # roughly every 5 minutes
            db = SessionLocal()
            try:
                PeopleCountersRepository(db).reset_orphans(heartbeat_timeout_seconds=180)
            finally:
                db.close()

        # Claim up to `slots` batches.
        claimed: List[Dict[str, Any]] = []
        max_attempts = int(settings_snapshot["people_counters_max_attempts"])
        for _ in range(slots):
            db = SessionLocal()
            try:
                row = PeopleCountersRepository(db).claim_batch(
                    max_attempts=max_attempts,
                    daily_backfill_remaining=backfill_remaining,
                )
            finally:
                db.close()
            if row is None:
                break
            claimed.append(row)
            if int(row.get("priority_tier", 0)) == TIER_OLDER_BACKFILL:
                self._daily_backfill_count += 1
                backfill_remaining = max(0, backfill_remaining - 1)

        if not claimed:
            await asyncio.sleep(5.0)
            return

        urls = _service_urls()
        token = _service_token()
        auth_header = {"Authorization": f"Bearer {token}"} if token else {}

        async def _run_one(batch_row: Dict[str, Any]) -> None:
            self._inflight += 1
            try:
                await _process_batch(
                    batch=batch_row,
                    settings_snapshot=settings_snapshot,
                    urls=urls,
                    auth_header=auth_header,
                )
            finally:
                self._inflight -= 1

        # Fire-and-forget: tasks track their own lifecycle and decrement _inflight.
        for row in claimed:
            asyncio.create_task(
                _run_one(row),
                name=f"pcj:{row['batch_key']}",
            )

    async def _run(self) -> None:
        """Supervisor entry-point."""
        try:
            initial = await _read_settings()
            await self._startup_recovery(initial)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("People Counters startup recovery failed: %s", exc)

        while not self._shutdown.is_set():
            try:
                snapshot = await _read_settings()
                if snapshot["people_counters_enabled"] < 1.0:
                    await asyncio.sleep(10.0)
                    continue
                await self._tick(snapshot)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.exception("People Counters supervisor tick failed: %s", exc)
                await asyncio.sleep(15.0)


# Module-level singleton; main.py wires this into the FastAPI lifespan.
people_counters_worker = PeopleCountersWorker()


__all__ = [
    "PeopleCountersWorker",
    "people_counters_worker",
    "enqueue_windows",
]
