"""
Instant Detection flush logs API (Automation domain).

Separate from trigger_execution_logs and action delivery logs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.instant_detection_log import InstantDetectionLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instant-detection-logs", tags=["instant-detection-logs"])


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


@router.get("/{log_id}", response_model=InstantDetectionLogResponse)
def get_instant_detection_log(log_id: int, db: Session = Depends(get_db)):
    row = db.query(InstantDetectionLog).filter(InstantDetectionLog.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instant detection log not found")
    return row
