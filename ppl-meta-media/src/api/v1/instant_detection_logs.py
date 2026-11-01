"""
Instant Detection flush logs API (Automation domain).

Separate from trigger_execution_logs and action delivery logs.
Also hosts the derived normalised-span path (immutable raw logs untouched).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.instant_detection_log import InstantDetectionLog
from src.models.instant_detection_normalised_span import InstantDetectionNormalisedSpan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instant-detection-logs", tags=["instant-detection-logs"])

DEFAULT_SPAN_SECONDS = int(os.getenv("INSTANT_NORMALISATION_SPAN_SECONDS", "300"))
DEFAULT_MERGE_THRESHOLD = float(
    os.getenv("INSTANT_NORMALISATION_MERGE_THRESHOLD", "0.70")
)


class InstantDetectionLogCreate(BaseModel):
    camera_device_id: str
    session_uuid: Optional[UUID] = None
    flush_started_at: datetime
    flush_ended_at: datetime
    cycle_count: int = 0
    frames_per_cycle: int = 3
    merge_threshold: Optional[float] = None
    people_count: int = 0
    payload_json: Dict[str, Any] = Field(default_factory=dict)
    log_type: str = "instant_detection"


class InstantDetectionLogResponse(BaseModel):
    id: int
    camera_device_id: str
    session_uuid: Optional[UUID] = None
    flush_started_at: datetime
    flush_ended_at: datetime
    cycle_count: int
    frames_per_cycle: int
    merge_threshold: Optional[float] = None
    people_count: int
    payload_json: Dict[str, Any]
    log_type: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NormalisedSpanUpsert(BaseModel):
    camera_device_id: str
    span_start: datetime
    span_end: datetime
    span_seconds: int = DEFAULT_SPAN_SECONDS
    merge_threshold: float = DEFAULT_MERGE_THRESHOLD
    people_count: int = 0
    source_log_ids: List[Any] = Field(default_factory=list)
    payload_json: Dict[str, Any] = Field(default_factory=dict)
    computed_at: Optional[datetime] = None


class NormalisedSpanResponse(BaseModel):
    id: int
    camera_device_id: str
    span_start: datetime
    span_end: datetime
    span_seconds: int
    merge_threshold: float
    people_count: int
    source_log_ids: List[Any]
    payload_json: Dict[str, Any]
    computed_at: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NormalisedRecomputeRequest(BaseModel):
    camera_device_id: str
    start_time: datetime
    end_time: datetime
    # Omit to let Cameras resolve per-camera normalise_* settings.
    merge_threshold: Optional[float] = None
    span_seconds: Optional[int] = None
    force: bool = False
    auth_token: Optional[str] = None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _floor_span_start(dt: datetime, span_seconds: int) -> datetime:
    utc = _as_utc(dt)
    epoch = int(utc.timestamp())
    floored = epoch - (epoch % max(1, span_seconds))
    return datetime.fromtimestamp(floored, tz=timezone.utc)


def _iter_span_starts(
    start_time: datetime, end_time: datetime, span_seconds: int
) -> List[datetime]:
    span_seconds = max(1, int(span_seconds))
    cursor = _floor_span_start(start_time, span_seconds)
    end = _as_utc(end_time)
    starts: List[datetime] = []
    # Inclusive of any span that overlaps [start, end)
    while cursor < end:
        starts.append(cursor)
        cursor = cursor + timedelta(seconds=span_seconds)
    return starts


@router.post("", response_model=InstantDetectionLogResponse, status_code=status.HTTP_201_CREATED)
def create_instant_detection_log(
    body: InstantDetectionLogCreate,
    db: Session = Depends(get_db),
):
    """Persist one Y-window Instant Detection flush (internal / service callers)."""
    row = InstantDetectionLog(
        camera_device_id=body.camera_device_id,
        session_uuid=body.session_uuid,
        flush_started_at=body.flush_started_at,
        flush_ended_at=body.flush_ended_at,
        cycle_count=body.cycle_count,
        frames_per_cycle=body.frames_per_cycle,
        merge_threshold=body.merge_threshold,
        people_count=body.people_count,
        payload_json=body.payload_json,
        log_type=body.log_type or "instant_detection",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "instant_detection_logs: camera=%s people=%s cycles=%s id=%s",
        body.camera_device_id,
        body.people_count,
        body.cycle_count,
        row.id,
    )
    return row


@router.get("", response_model=List[InstantDetectionLogResponse])
def list_instant_detection_logs(
    camera_device_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(
        None, description="Include logs whose flush window overlaps this start"
    ),
    end_time: Optional[datetime] = Query(
        None, description="Include logs whose flush window overlaps this end"
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(InstantDetectionLog).filter(
        InstantDetectionLog.log_type == "instant_detection"
    )
    if camera_device_id:
        q = q.filter(InstantDetectionLog.camera_device_id == camera_device_id)
    # Overlap: flush_started_at <= end_time AND flush_ended_at >= start_time
    if start_time is not None:
        q = q.filter(InstantDetectionLog.flush_ended_at >= start_time)
    if end_time is not None:
        q = q.filter(InstantDetectionLog.flush_started_at <= end_time)
    rows = (
        q.order_by(InstantDetectionLog.flush_started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


@router.get("/analytics/summary")
def instant_detection_analytics_summary(
    camera_device_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Aggregate Instant Detection analytics from flush logs only."""
    q = db.query(InstantDetectionLog).filter(
        InstantDetectionLog.log_type == "instant_detection"
    )
    if camera_device_id:
        q = q.filter(InstantDetectionLog.camera_device_id == camera_device_id)
    rows = q.order_by(InstantDetectionLog.flush_started_at.desc()).limit(limit).all()

    total_people = sum(int(r.people_count or 0) for r in rows)
    total_flushes = len(rows)
    by_camera: Dict[str, Any] = {}
    for r in rows:
        entry = by_camera.setdefault(
            r.camera_device_id,
            {"camera_device_id": r.camera_device_id, "flushes": 0, "people_count": 0},
        )
        entry["flushes"] += 1
        entry["people_count"] += int(r.people_count or 0)

    return {
        "source": "instant_detection_logs",
        "total_flushes": total_flushes,
        "total_people": total_people,
        "cameras": list(by_camera.values()),
        "recent": [
            {
                "id": r.id,
                "camera_device_id": r.camera_device_id,
                "people_count": r.people_count,
                "cycle_count": r.cycle_count,
                "flush_started_at": r.flush_started_at.isoformat()
                if r.flush_started_at
                else None,
                "flush_ended_at": r.flush_ended_at.isoformat()
                if r.flush_ended_at
                else None,
            }
            for r in rows[:20]
        ],
    }


@router.put(
    "/normalised/spans",
    response_model=NormalisedSpanResponse,
    status_code=status.HTTP_200_OK,
)
def upsert_normalised_span(
    body: NormalisedSpanUpsert,
    db: Session = Depends(get_db),
):
    """Upsert one derived normalisation span (worker / recompute)."""
    span_start = _as_utc(body.span_start)
    span_end = _as_utc(body.span_end)
    computed_at = _as_utc(body.computed_at or datetime.now(timezone.utc))
    threshold = float(body.merge_threshold)

    row = (
        db.query(InstantDetectionNormalisedSpan)
        .filter(
            InstantDetectionNormalisedSpan.camera_device_id == body.camera_device_id,
            InstantDetectionNormalisedSpan.span_start == span_start,
            InstantDetectionNormalisedSpan.merge_threshold == threshold,
        )
        .first()
    )
    if row is None:
        row = InstantDetectionNormalisedSpan(
            camera_device_id=body.camera_device_id,
            span_start=span_start,
            span_end=span_end,
            span_seconds=int(body.span_seconds or DEFAULT_SPAN_SECONDS),
            merge_threshold=threshold,
            people_count=int(body.people_count or 0),
            source_log_ids=list(body.source_log_ids or []),
            payload_json=dict(body.payload_json or {}),
            computed_at=computed_at,
        )
        db.add(row)
    else:
        row.span_end = span_end
        row.span_seconds = int(body.span_seconds or row.span_seconds or DEFAULT_SPAN_SECONDS)
        row.people_count = int(body.people_count or 0)
        row.source_log_ids = list(body.source_log_ids or [])
        row.payload_json = dict(body.payload_json or {})
        row.computed_at = computed_at

    db.commit()
    db.refresh(row)
    logger.info(
        "instant_detection_normalised_spans upsert: camera=%s start=%s people=%s id=%s",
        body.camera_device_id,
        span_start.isoformat(),
        row.people_count,
        row.id,
    )
    return row


@router.get("/normalised/spans", response_model=List[NormalisedSpanResponse])
def list_normalised_spans(
    camera_device_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(
        None, description="Include spans whose window overlaps this start"
    ),
    end_time: Optional[datetime] = Query(
        None, description="Include spans whose window overlaps this end"
    ),
    merge_threshold: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(InstantDetectionNormalisedSpan)
    if camera_device_id:
        q = q.filter(
            InstantDetectionNormalisedSpan.camera_device_id == camera_device_id
        )
    if start_time is not None:
        q = q.filter(InstantDetectionNormalisedSpan.span_end >= _as_utc(start_time))
    if end_time is not None:
        q = q.filter(InstantDetectionNormalisedSpan.span_start <= _as_utc(end_time))
    if merge_threshold is not None:
        q = q.filter(
            InstantDetectionNormalisedSpan.merge_threshold == float(merge_threshold)
        )
    rows = (
        q.order_by(InstantDetectionNormalisedSpan.span_start.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


@router.post("/normalised/recompute")
def recompute_normalised_spans(body: NormalisedRecomputeRequest):
    """
    Ask Cameras to enqueue Celery normalisation for every calendar span in range.
    Idempotent: worker upserts replace existing derived rows.
    When span/threshold omitted, Cameras uses per-camera settings.
    """
    preview_span = int(body.span_seconds or DEFAULT_SPAN_SECONDS)
    starts = _iter_span_starts(body.start_time, body.end_time, preview_span)
    cameras_base = os.getenv("CAMERAS_SERVICE_URL", "http://localhost:8002").rstrip(
        "/"
    )
    payload: Dict[str, Any] = {
        "camera_device_id": body.camera_device_id,
        "start_time": _as_utc(body.start_time).isoformat(),
        "end_time": _as_utc(body.end_time).isoformat(),
        "force": bool(body.force),
        "auth_token": body.auth_token or "",
    }
    if body.merge_threshold is not None:
        payload["merge_threshold"] = float(body.merge_threshold)
    if body.span_seconds is not None:
        payload["span_seconds"] = int(body.span_seconds)
    enqueued = False
    cameras_response: Any = None
    try:
        headers = {"Content-Type": "application/json"}
        if body.auth_token:
            token = body.auth_token
            headers["Authorization"] = (
                token if token.startswith("Bearer ") else f"Bearer {token}"
            )
        resp = requests.post(
            f"{cameras_base}/api/v1/instant-detection/normalise/recompute",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if resp.status_code in (200, 202):
            enqueued = True
            try:
                cameras_response = resp.json()
            except Exception:
                cameras_response = {"status_code": resp.status_code}
        else:
            logger.warning(
                "Cameras normalise recompute failed: %s %s",
                resp.status_code,
                resp.text[:300],
            )
            cameras_response = {
                "status_code": resp.status_code,
                "detail": resp.text[:300],
            }
    except Exception as exc:
        logger.warning("Cameras normalise recompute unreachable: %s", exc)
        cameras_response = {"error": str(exc)}

    return {
        "accepted": True,
        "enqueued": enqueued,
        "camera_device_id": body.camera_device_id,
        "span_seconds": body.span_seconds,
        "merge_threshold": body.merge_threshold,
        "span_seconds_preview": preview_span,
        "span_count": len(starts),
        "span_starts": [s.isoformat() for s in starts],
        "force": bool(body.force),
        "cameras": cameras_response,
    }


@router.get("/{log_id}", response_model=InstantDetectionLogResponse)
def get_instant_detection_log(log_id: int, db: Session = Depends(get_db)):
    row = db.query(InstantDetectionLog).filter(InstantDetectionLog.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instant detection log not found")
    return row
