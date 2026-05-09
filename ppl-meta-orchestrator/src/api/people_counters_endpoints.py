"""
PPL Meta Orchestrator - People Counters API.

REST endpoints exposing the People Counters automation worker:
- run a daily-batch enumeration on demand
- inspect job state, dead-letter, retry, invalidate
- get/update worker settings
- pause/resume the supervisor

See docs/proposals/people-counters.md §5.9 for the contract.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.people_counters_repository import (
    PeopleCountersRepository,
    STATUS_DEAD_LETTER,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCESS,
)
from services.people_counters_worker import (
    enqueue_windows,
    people_counters_worker,
)
from services.workflow_settings_service import WorkflowSettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/people-counters", tags=["people-counters"])


# ---------------------------------------------------------------------- #
# Models
# ---------------------------------------------------------------------- #


class RunDailyBatchRequest(BaseModel):
    """Body for POST /run-daily-batch."""

    date: Optional[str] = Field(
        None,
        description="UTC date YYYY-MM-DD to enqueue. Defaults to yesterday (UTC).",
    )
    camera_ids: Optional[List[str]] = Field(
        None,
        description="Restrict enqueue to these cameras. If omitted, the worker "
        "uses its active-cameras list at dispatch time.",
    )
    force: bool = Field(
        False,
        description="If true, also requeue already-completed windows for refresh.",
    )


class StatusSummaryResponse(BaseModel):
    enabled: bool
    running: bool
    inflight: int
    counts: Dict[str, int]


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #


def _resolve_target_date(date_str: Optional[str]) -> datetime:
    if not date_str:
        return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date '{date_str}': expected YYYY-MM-DD",
        ) from exc


async def _get_setting(db: Session, key: str, default: float) -> float:
    svc = WorkflowSettingsService(db)
    val = await svc.get_setting(key)
    return float(val) if val is not None else default


def _serialize_job(row: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce datetimes to ISO strings so FastAPI's JSON encoder is happy."""
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------- #
# Status / control
# ---------------------------------------------------------------------- #


@router.get("/status", response_model=StatusSummaryResponse)
async def get_status(db: Session = Depends(get_db)) -> StatusSummaryResponse:
    """Aggregate status counts + supervisor liveness for the Settings UI."""
    repo = PeopleCountersRepository(db)
    enabled = (await _get_setting(db, "people_counters_enabled", 0.0)) >= 1.0
    return StatusSummaryResponse(
        enabled=enabled,
        running=people_counters_worker.is_running(),
        inflight=people_counters_worker._inflight,  # pylint: disable=protected-access
        counts=repo.status_summary(),
    )


@router.post("/pause")
async def pause(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Disable dispatching of new batches (in-flight batches keep running)."""
    svc = WorkflowSettingsService(db)
    await svc.update_setting("people_counters_enabled", 0.0, updated_by="api:pause")
    return {"success": True, "enabled": False}


@router.post("/resume")
async def resume(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Re-enable dispatching."""
    svc = WorkflowSettingsService(db)
    await svc.update_setting("people_counters_enabled", 1.0, updated_by="api:resume")
    return {"success": True, "enabled": True}


# ---------------------------------------------------------------------- #
# Settings
# ---------------------------------------------------------------------- #

_SETTING_KEYS = [
    "people_counters_enabled",
    "people_counters_batch_seconds",
    "people_counters_workers",
    "people_counters_quiet_workers",
    "people_counters_max_cpu_pct",
    "people_counters_max_inflight",
    "people_counters_backoff_seconds",
    "people_counters_per_batch_timeout_seconds",
    "people_counters_max_attempts",
    "people_counters_backfill_daily_budget",
    "people_counters_quiet_hours_start",
    "people_counters_quiet_hours_end",
]


@router.get("/settings")
async def get_settings(db: Session = Depends(get_db)) -> Dict[str, Any]:
    svc = WorkflowSettingsService(db)
    out: Dict[str, Any] = {}
    for key in _SETTING_KEYS:
        out[key] = await svc.get_setting(key)
    return {"settings": out}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    value: float = Body(..., embed=True),
    updated_by: str = Body("api", embed=True),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if key not in _SETTING_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown setting '{key}'. Valid keys: {_SETTING_KEYS}",
        )
    svc = WorkflowSettingsService(db)
    result = await svc.update_setting(key, value, updated_by=updated_by)
    return {"success": True, "key": key, "value": value, "result": result}


# ---------------------------------------------------------------------- #
# Manual enqueue
# ---------------------------------------------------------------------- #


@router.post("/run-daily-batch")
async def run_daily_batch(
    body: RunDailyBatchRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Idempotently enqueue every (camera × hour-window) tuple for the given UTC day.

    If `camera_ids` is omitted the request is accepted but no rows are inserted —
    the supervisor's startup recovery (which knows the active-cameras list)
    handles enumeration on its own. Specify cameras explicitly here when you
    want a one-shot replay.
    """
    target = _resolve_target_date(body.date)
    end = target + timedelta(days=1)
    batch_seconds = int(await _get_setting(db, "people_counters_batch_seconds", 3600.0))
    if not body.camera_ids:
        return {
            "success": True,
            "queued": 0,
            "message": "No camera_ids provided; supervisor will enumerate active cameras on next tick.",
            "date": target.date().isoformat(),
        }

    if body.force:
        # Mark any existing matching batches as stale-refresh so they're picked up.
        repo = PeopleCountersRepository(db)
        cursor = target
        refreshed = 0
        while cursor < end:
            window_end = cursor + timedelta(seconds=batch_seconds)
            for cam in body.camera_ids:
                key = PeopleCountersRepository.build_batch_key(cam, cursor, window_end)
                if repo.requeue_stale(key):
                    refreshed += 1
            cursor = window_end
        logger.info("run-daily-batch force-refresh: %d rows", refreshed)

    inserted = await enqueue_windows(
        camera_ids=body.camera_ids,
        range_start_utc=target,
        range_end_utc=end,
        batch_seconds=batch_seconds,
    )
    return {
        "success": True,
        "queued": inserted,
        "date": target.date().isoformat(),
        "cameras": body.camera_ids,
        "batch_seconds": batch_seconds,
    }


# ---------------------------------------------------------------------- #
# Job inspection
# ---------------------------------------------------------------------- #


@router.get("/jobs")
async def list_jobs(
    camera_id: Optional[str] = Query(None),
    job_status: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None, description="UTC YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="UTC YYYY-MM-DD"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if job_status and job_status not in (
        STATUS_PENDING, STATUS_RUNNING, STATUS_SUCCESS, STATUS_FAILED, STATUS_DEAD_LETTER,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{job_status}'",
        )
    df = _resolve_target_date(date_from) if date_from else None
    dt = _resolve_target_date(date_to) + timedelta(days=1) if date_to else None
    rows = PeopleCountersRepository(db).list_jobs(
        camera_id=camera_id,
        status=job_status,
        date_from=df,
        date_to=dt,
        limit=limit,
    )
    return {"count": len(rows), "jobs": [_serialize_job(r) for r in rows]}


@router.get("/jobs/{batch_key}")
async def get_job(batch_key: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = PeopleCountersRepository(db).get_by_batch_key(batch_key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No job for batch_key {batch_key}")
    return {"job": _serialize_job(row)}


@router.get("/dead-letter")
async def list_dead_letter(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    rows = PeopleCountersRepository(db).list_dead_letter(limit=limit)
    return {"count": len(rows), "jobs": [_serialize_job(r) for r in rows]}


@router.post("/jobs/{batch_key}/retry")
async def retry_job(batch_key: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    ok = PeopleCountersRepository(db).retry_dead_letter(batch_key)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"No dead-letter / failed job for batch_key {batch_key}",
        )
    return {"success": True, "batch_key": batch_key, "status": STATUS_PENDING}


@router.post("/jobs/{batch_key}/invalidate")
async def invalidate_batch(batch_key: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Mark a batch as stale-refresh so the worker re-runs it.

    Uses requeue_stale (pending-on-success) — does not affect rows currently
    in 'pending' or 'running'. To force a recompute of a running batch, wait
    for it to finish and then invalidate.
    """
    ok = PeopleCountersRepository(db).requeue_stale(batch_key)
    return {"success": True, "batch_key": batch_key, "requeued": ok}
