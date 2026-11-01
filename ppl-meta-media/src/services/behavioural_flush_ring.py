"""
Per-camera Redis ring of Instant Detection flush snapshots for Behavioural triggers.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RING_KEY_PREFIX = "behavioural:flushes:"
DEFAULT_MAX_LOOKBACK = 60
RING_TTL_SECONDS = 2 * 60 * 60  # 2 hours


def ring_key(camera_device_id: str) -> str:
    return f"{RING_KEY_PREFIX}{camera_device_id}"


def _person_snapshot(person: Dict[str, Any]) -> Dict[str, Any]:
    tracking = person.get("movement_tracking")
    if not isinstance(tracking, dict):
        tracking = {}
    stats = tracking.get("movement_statistics")
    if not isinstance(stats, dict):
        stats = {}
    tif = stats.get("time_in_frame_seconds")
    if tif is None:
        tif = person.get("time_in_frame_seconds")
    vel = person.get("average_route_velocity")
    if vel is None:
        vel = tracking.get("average_route_velocity")
    if vel is None:
        vel = stats.get("average_velocity")
    route_points = tracking.get("route_points") or person.get("route_points") or []
    route_n = len(route_points) if isinstance(route_points, list) else 0
    pou = (
        person.get("person_object_uuid")
        or person.get("person_uuid")
        or person.get("individual_uuid")
        or person.get("mvr_people_uuid")
        or person.get("instant_mvr_uuid")
    )
    return {
        "person_object_uuid": str(pou) if pou else None,
        "time_in_frame_seconds": float(tif) if isinstance(tif, (int, float)) else None,
        "average_route_velocity": float(vel) if isinstance(vel, (int, float)) else None,
        "route_point_count": route_n,
    }


def compact_flush_snapshot(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact ring entry from an instant-detection Redis payload."""
    people_raw: List[Dict[str, Any]] = []
    for key in ("people", "person_groups", "instant_mvrs", "individuals"):
        raw = event_data.get(key)
        if isinstance(raw, list):
            people_raw.extend([p for p in raw if isinstance(p, dict)])
    meta = event_data.get("metadata")
    if isinstance(meta, dict):
        for key in ("people", "person_groups"):
            raw = meta.get(key)
            if isinstance(raw, list):
                people_raw.extend([p for p in raw if isinstance(p, dict)])

    people = [_person_snapshot(p) for p in people_raw]
    people_count = event_data.get("people_count")
    if not isinstance(people_count, (int, float)):
        people_count = len(people)

    return {
        "camera_id": event_data.get("camera_id") or event_data.get("camera_device_id"),
        "timestamp": event_data.get("timestamp"),
        "flush_started_at": event_data.get("flush_started_at")
        or (meta.get("flush_started_at") if isinstance(meta, dict) else None)
        or event_data.get("timestamp"),
        "flush_ended_at": event_data.get("flush_ended_at")
        or (meta.get("flush_ended_at") if isinstance(meta, dict) else None)
        or event_data.get("timestamp"),
        "people_count": int(people_count or 0),
        "people": people,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }


async def push_flush_snapshot(
    redis,
    camera_device_id: str,
    event_data: Dict[str, Any],
    max_lookback: int = DEFAULT_MAX_LOOKBACK,
) -> int:
    """LPUSH compact snapshot and LTRIM to max_lookback. Returns ring length."""
    if not redis or not camera_device_id:
        return 0
    if max_lookback < 2:
        max_lookback = 2
    if max_lookback > DEFAULT_MAX_LOOKBACK:
        max_lookback = DEFAULT_MAX_LOOKBACK
    key = ring_key(camera_device_id)
    snap = compact_flush_snapshot(event_data)
    payload = json.dumps(snap, default=str)
    pipe = redis.pipeline()
    pipe.lpush(key, payload)
    pipe.ltrim(key, 0, max_lookback - 1)
    pipe.expire(key, RING_TTL_SECONDS)
    pipe.llen(key)
    results = await pipe.execute()
    length = int(results[-1] or 0)
    logger.debug("behavioural ring %s len=%s", camera_device_id, length)
    return length


async def load_flush_ring(
    redis,
    camera_device_id: str,
    lookback: int,
) -> List[Dict[str, Any]]:
    """Return newest-first snapshots, capped to lookback."""
    if not redis or not camera_device_id:
        return []
    lookback = max(1, min(int(lookback or 6), DEFAULT_MAX_LOOKBACK))
    raw_list = await redis.lrange(ring_key(camera_device_id), 0, lookback - 1)
    out: List[Dict[str, Any]] = []
    for raw in raw_list or []:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            item = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if isinstance(item, dict):
            out.append(item)
    return out


async def max_lookback_for_camera(db_session, camera_device_id: str) -> int:
    """Largest lookback among active behavioural triggers for this camera."""
    from src.models.trigger import Trigger

    rows = (
        db_session.query(Trigger.behavioural_lookback_flushes)
        .filter(
            Trigger.is_active == True,  # noqa: E712
            Trigger.trigger_mode == "behavioural",
            Trigger.camera_device_id == camera_device_id,
        )
        .all()
    )
    values = [int(r[0] or 6) for r in rows if r]
    if not values:
        return DEFAULT_MAX_LOOKBACK
    return max(2, min(max(values), DEFAULT_MAX_LOOKBACK))
