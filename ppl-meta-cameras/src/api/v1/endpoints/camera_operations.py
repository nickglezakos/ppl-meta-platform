"""Camera operations endpoints for live stream operations visibility."""

import logging
import os
from collections import Counter
from datetime import datetime, timezone
from math import ceil
from typing import Dict, List, Optional

from celery.exceptions import CeleryError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.camera import Camera, CameraType
from src.security.auth import (
    get_current_user,
    require_admin_cameras,
    require_view_cameras,
)
from src.services.stream_operations_state import get_stream_operations_state_service
from src.tasks.stream_operations_tasks import reconcile_all, reconcile_camera

logger = logging.getLogger(__name__)
router = APIRouter()


class PolicyUpdateRequest(BaseModel):
    """Policy update payload."""

    reason: str = Field(min_length=8, max_length=500)
    if_version: int = Field(ge=1)
    changes: Dict[str, int]


class ReconcileRequest(BaseModel):
    """Reconciliation trigger payload."""

    camera_id: Optional[str] = None
    sync_fallback: bool = True


def _parse_optional_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


@router.get("/reconcile/health", dependencies=[Depends(require_view_cameras)])
async def get_reconcile_health(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Return lightweight reconciliation scheduler health and recency metadata."""
    _ = current_user

    state_service = get_stream_operations_state_service()
    last_reconcile_at = await state_service.get_last_event_timestamp("reconciled")
    last_reconcile_trigger_at = await state_service.get_last_event_timestamp("policy_updated")

    enabled = os.getenv("STREAM_OPS_RECONCILE_ENABLED", "true").lower() == "true"
    interval_seconds = int(os.getenv("STREAM_OPS_RECONCILE_INTERVAL_SECONDS", "60"))
    beat_enabled = os.getenv("CAMERAS_CELERY_ENABLE_BEAT", "true").lower() == "true"
    now = datetime.now(timezone.utc)

    last_reconcile_dt = _parse_optional_utc(last_reconcile_at)
    age_seconds: Optional[int] = None
    if last_reconcile_dt is not None:
        age_seconds = max(0, int((now - last_reconcile_dt).total_seconds()))

    if not enabled:
        status_value = "disabled"
    elif age_seconds is None:
        status_value = "unknown"
    elif age_seconds <= (interval_seconds * 2):
        status_value = "healthy"
    else:
        status_value = "stale"

    return {
        "meta": {
            "generated_at": now.isoformat(),
        },
        "reconcile": {
            "enabled": enabled,
            "interval_seconds": interval_seconds,
            "beat_enabled": beat_enabled,
            "status": status_value,
            "age_seconds": age_seconds,
            "last_reconcile_at": last_reconcile_at,
            "last_policy_update_at": last_reconcile_trigger_at,
        },
    }


def _parse_utc_or_400(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} timestamp format",
        ) from exc


def _percentile(values: List[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = max(0, min(len(sorted_values) - 1, ceil((percentile / 100.0) * len(sorted_values)) - 1))
    return float(sorted_values[rank])


@router.get("/status", dependencies=[Depends(require_view_cameras)])
async def get_operations_status(
    camera_type: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Return current operations status for active cameras with stream state metadata."""
    _ = current_user

    query = db.query(Camera).filter(Camera.archived == False)
    if camera_type:
        try:
            query = query.filter(Camera.camera_type == CameraType(camera_type.upper()))
        except ValueError:
            return {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total": 0,
                },
                "summary": {
                    "by_state": {},
                    "by_camera_type": {},
                },
                "items": [],
            }

    cameras: List[Camera] = query.limit(limit).all()
    camera_ids = [camera.device_id for camera in cameras]

    state_service = get_stream_operations_state_service()
    state_map = await state_service.get_many_states(camera_ids)

    items: List[Dict] = []
    state_counter: Counter = Counter()
    type_counter: Counter = Counter()

    for camera in cameras:
        camera_state = state_map.get(camera.device_id, {})
        stream_state = camera_state.get("stream_state", "DISCONNECTED")

        if state and stream_state != state:
            continue

        type_value = camera.camera_type.value if camera.camera_type is not None else "UNKNOWN"
        type_counter[type_value] += 1
        state_counter[stream_state] += 1

        items.append(
            {
                "camera_id": camera.device_id,
                "camera_name": camera.name,
                "camera_type": type_value,
                "stream_state": stream_state,
                "active_viewers": int(camera_state.get("active_viewers", 0) or 0),
                "camera_profile": camera_state.get("camera_profile", "usb"),
                "last_frame_at": camera_state.get("last_frame_at"),
                "frame_gap_ms": camera_state.get("frame_gap_ms"),
                "last_transition_reason": camera_state.get("last_transition_reason"),
                "updated_at": camera_state.get("updated_at"),
            }
        )

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(items),
        },
        "summary": {
            "by_state": dict(state_counter),
            "by_camera_type": dict(type_counter),
        },
        "items": items,
    }


@router.get("/policies", dependencies=[Depends(require_view_cameras)])
async def get_operations_policies(
    scope_type: str = Query(default="camera_type"),
    scope_id: Optional[str] = Query(default=None),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Return editable policy profiles and ranges for operations tuning."""
    _ = current_user
    state_service = get_stream_operations_state_service()
    try:
        payload = await state_service.list_policies(scope_type=scope_type, scope_id=scope_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope_type": scope_type,
            "scope_id": scope_id,
        },
        **payload,
    }


@router.patch("/policies/{scope_type}/{scope_id}", dependencies=[Depends(require_admin_cameras)])
async def update_operations_policy(
    scope_type: str,
    scope_id: str,
    request: PolicyUpdateRequest,
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Update policy values within allowed ranges for a given scope."""
    actor = current_user.get("sub", "unknown")
    state_service = get_stream_operations_state_service()

    try:
        result = await state_service.update_policy(
            scope_type=scope_type,
            scope_id=scope_id,
            changes=request.changes,
            if_version=request.if_version,
            reason=request.reason,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": actor,
        },
        "result": result,
    }


@router.get("/analytics/readings", dependencies=[Depends(require_view_cameras)])
async def get_operations_analytics_readings(
    from_ts: str = Query(alias="from"),
    to_ts: str = Query(alias="to"),
    camera_id: Optional[str] = Query(default=None),
    camera_type: Optional[str] = Query(default=None),
    resolution: str = Query(default="10s"),
    limit: int = Query(default=2000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Return time-windowed stream operation readings for support triage."""
    _ = current_user

    from_dt = _parse_utc_or_400(from_ts, "from")
    to_dt = _parse_utc_or_400(to_ts, "to")
    if from_dt >= to_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from must be earlier than to",
        )

    query = db.query(Camera).filter(Camera.archived == False)
    if camera_id:
        query = query.filter(Camera.device_id == camera_id)
    if camera_type:
        try:
            query = query.filter(Camera.camera_type == CameraType(camera_type.upper()))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported camera_type",
            ) from exc

    cameras: List[Camera] = query.all()
    camera_ids = [camera.device_id for camera in cameras]
    camera_type_lookup = {
        camera.device_id: (camera.camera_type.value if camera.camera_type is not None else "UNKNOWN")
        for camera in cameras
    }

    state_service = get_stream_operations_state_service()
    readings = await state_service.query_readings(camera_ids=camera_ids, from_dt=from_dt, to_dt=to_dt, limit=limit)

    # Resolution is currently advisory. Keep contract field and return capped data.
    series_map: Dict[str, Dict] = {}
    for row in readings:
        cid = str(row.get("camera_id", ""))
        if cid not in series_map:
            series_map[cid] = {
                "camera_id": cid,
                "camera_type": camera_type_lookup.get(cid, row.get("camera_type", "UNKNOWN")),
                "points": [],
            }
        series_map[cid]["points"].append(row)

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
            "resolution": resolution,
            "count": len(readings),
        },
        "series": list(series_map.values()),
    }


@router.get("/analytics/aggregates", dependencies=[Depends(require_view_cameras)])
async def get_operations_analytics_aggregates(
    from_ts: str = Query(alias="from"),
    to_ts: str = Query(alias="to"),
    group_by: str = Query(default="camera_type"),
    camera_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Return aggregate operations metrics for support dashboards."""
    _ = current_user

    if group_by not in {"camera_id", "camera_type"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by must be camera_id or camera_type",
        )

    from_dt = _parse_utc_or_400(from_ts, "from")
    to_dt = _parse_utc_or_400(to_ts, "to")
    if from_dt >= to_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from must be earlier than to",
        )

    query = db.query(Camera).filter(Camera.archived == False)
    if camera_type:
        try:
            query = query.filter(Camera.camera_type == CameraType(camera_type.upper()))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported camera_type",
            ) from exc

    cameras: List[Camera] = query.all()
    camera_ids = [camera.device_id for camera in cameras]
    type_lookup = {
        camera.device_id: (camera.camera_type.value if camera.camera_type is not None else "UNKNOWN")
        for camera in cameras
    }

    state_service = get_stream_operations_state_service()
    readings = await state_service.query_readings(camera_ids=camera_ids, from_dt=from_dt, to_dt=to_dt, limit=10000)

    grouped: Dict[str, Dict[str, List[float]]] = {}
    stale_counts: Dict[str, int] = {}
    for row in readings:
        camera_id_value = str(row.get("camera_id", ""))
        group_key = camera_id_value if group_by == "camera_id" else type_lookup.get(camera_id_value, "UNKNOWN")
        bucket = grouped.setdefault(group_key, {"frame_gap_ms": [], "active_viewers": [], "effective_fps": []})

        gap = row.get("frame_gap_ms")
        if isinstance(gap, (int, float)):
            bucket["frame_gap_ms"].append(float(gap))
        viewers = row.get("active_viewers")
        if isinstance(viewers, (int, float)):
            bucket["active_viewers"].append(float(viewers))
        fps = row.get("effective_fps")
        if isinstance(fps, (int, float)):
            bucket["effective_fps"].append(float(fps))
        if row.get("event") == "stale_candidate":
            stale_counts[group_key] = stale_counts.get(group_key, 0) + 1

    rows = []
    for key, values in grouped.items():
        frame_gaps = values["frame_gap_ms"]
        viewers = values["active_viewers"]
        fps_values = values["effective_fps"]
        rows.append(
            {
                "group": key,
                "frame_gap_p95_ms": _percentile(frame_gaps, 95),
                "active_viewers_avg": round(sum(viewers) / len(viewers), 2) if viewers else 0.0,
                "effective_fps_avg": round(sum(fps_values) / len(fps_values), 2) if fps_values else 0.0,
                "stale_events": stale_counts.get(key, 0),
            }
        )

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
            "group_by": group_by,
        },
        "rows": rows,
    }


@router.get("/analytics/incidents/{camera_id}", dependencies=[Depends(require_view_cameras)])
async def get_operations_incident_timeline(
    camera_id: str,
    from_ts: str = Query(alias="from"),
    to_ts: str = Query(alias="to"),
    include_policy_changes: bool = Query(default=True),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Return incident timeline events for a camera, optionally including policy changes."""
    _ = current_user

    from_dt = _parse_utc_or_400(from_ts, "from")
    to_dt = _parse_utc_or_400(to_ts, "to")
    if from_dt >= to_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from must be earlier than to",
        )

    state_service = get_stream_operations_state_service()
    state = await state_service.get_camera_state(camera_id)
    policy_scope_hint = state.get("camera_profile") if state else None
    events = await state_service.query_incident_events(
        camera_id=camera_id,
        from_dt=from_dt,
        to_dt=to_dt,
        include_policy_changes=include_policy_changes,
        policy_scope_hint=policy_scope_hint,
    )

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "camera_id": camera_id,
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
            "include_policy_changes": include_policy_changes,
        },
        "events": events,
    }


@router.post("/reconcile", dependencies=[Depends(require_admin_cameras)])
async def trigger_operations_reconcile(
    request: ReconcileRequest,
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Trigger stream operations reconciliation for one camera or all tracked cameras."""
    actor = current_user.get("sub", "unknown")

    try:
        if request.camera_id:
            task = reconcile_camera.delay(request.camera_id)
            return {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "triggered_by": actor,
                    "mode": "celery",
                },
                "result": {
                    "scope": "camera",
                    "camera_id": request.camera_id,
                    "task_id": task.id,
                    "task_name": "stream_operations.reconcile_camera",
                },
            }

        task = reconcile_all.delay()
        return {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "triggered_by": actor,
                "mode": "celery",
            },
            "result": {
                "scope": "all",
                "task_id": task.id,
                "task_name": "stream_operations.reconcile_all",
            },
        }
    except (CeleryError, ConnectionError, OSError, RuntimeError) as exc:
        if not request.sync_fallback:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to enqueue reconciliation task: {exc}",
            ) from exc

        state_service = get_stream_operations_state_service()
        if request.camera_id:
            result = await state_service.reconcile_camera_state(request.camera_id)
            return {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "triggered_by": actor,
                    "mode": "sync_fallback",
                },
                "result": result,
            }

        camera_ids = await state_service.list_tracked_camera_ids()
        reports = []
        updated = 0
        for camera_id in camera_ids:
            report = await state_service.reconcile_camera_state(camera_id)
            reports.append(report)
            if report.get("status") == "updated":
                updated += 1

        return {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "triggered_by": actor,
                "mode": "sync_fallback",
            },
            "result": {
                "scope": "all",
                "total": len(reports),
                "updated": updated,
                "reports": reports,
            },
        }
