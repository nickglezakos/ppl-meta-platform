"""
Instant Detection Y-window flush: re-group + contamination + hierarchical merge → Media logs.

Live cycles only buffer into Redis. Database writes happen here only.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

FLUSH_BUFFER_KEY = "instant_detection_flush_buffer:{camera_id}"
FLUSH_BUFFER_MAX = 500


def _redis():
    import redis

    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=False,
    )


def flush_buffer_key(camera_id: str) -> str:
    return FLUSH_BUFFER_KEY.format(camera_id=camera_id)


def push_cycle_to_flush_buffer(
    camera_id: str,
    *,
    cycle_id: str,
    timestamp: str,
    face_detections: List[Dict[str, Any]],
    person_objects: List[Dict[str, Any]],
    instant_mvrs: List[Dict[str, Any]],
) -> int:
    """Append one cycle's faces / InstantMvrs for the Y-window flush.

    Returns the buffer length after push (for threshold-triggered flush).
    """
    r = _redis()
    key = flush_buffer_key(camera_id)
    payload = {
        "cycle_id": cycle_id,
        "timestamp": timestamp,
        "face_detections": face_detections or [],
        "person_objects": person_objects or [],
        "instant_mvrs": instant_mvrs or [],
    }
    r.lpush(key, json.dumps(payload))
    r.ltrim(key, 0, FLUSH_BUFFER_MAX - 1)
    return int(r.llen(key))


def buffer_length(camera_id: str) -> int:
    try:
        return int(_redis().llen(flush_buffer_key(camera_id)))
    except Exception:
        return 0


def enqueue_y_window_flush(
    camera_id: str,
    *,
    session_uuid: Optional[str] = None,
    auth_token: Optional[str] = None,
    frames_per_cycle: int = 3,
    flush_interval_cycles: int = 12,
    merge_threshold: float = 0.60,
    sync_fallback: bool = True,
) -> Dict[str, Any]:
    """Queue (or sync-run) a Y-window flush for leftover / threshold cycles."""
    try:
        from src.tasks.instant_detection_tasks import flush_instant_detection_y_window

        flush_instant_detection_y_window.delay(
            camera_id=camera_id,
            session_uuid=session_uuid,
            auth_token=auth_token or "",
            frames_per_cycle=frames_per_cycle,
            flush_interval_cycles=flush_interval_cycles,
            merge_threshold=merge_threshold,
        )
        return {"queued": True, "camera_id": camera_id}
    except Exception as exc:
        logger.warning(
            "Celery Y-window flush enqueue failed for %s: %s", camera_id, exc
        )
        if not sync_fallback:
            return {"queued": False, "error": str(exc)}
        return run_y_window_flush(
            camera_id,
            session_uuid=session_uuid,
            auth_token=auth_token,
            frames_per_cycle=frames_per_cycle,
            flush_interval_cycles=flush_interval_cycles,
            merge_threshold=merge_threshold,
        )


def drain_flush_buffer(camera_id: str, max_cycles: Optional[int] = None) -> List[Dict[str, Any]]:
    r = _redis()
    key = flush_buffer_key(camera_id)
    items: List[Dict[str, Any]] = []
    while True:
        raw = r.rpop(key)
        if raw is None:
            break
        try:
            items.append(json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw))
        except Exception as exc:
            logger.warning("Bad flush buffer item for %s: %s", camera_id, exc)
        if max_cycles is not None and len(items) >= max_cycles:
            break
    return items


def _vision_group_url() -> str:
    base = os.getenv("VISION_SERVICE_URL", "http://localhost:8003")
    return f"{base}/api/v1/person-objects/group-from-faces"


def _vmeta_preview_url() -> str:
    base = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
    return f"{base}/api/v1/mvr-people/merge/hierarchical/preview-from-records"


def _media_logs_url() -> str:
    base = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000")
    return f"{base}/api/v1/instant-detection-logs"


def _normalize_face_for_regroup(face: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure Vision group-from-faces gets concrete bbox_* values (not null keys)."""
    out = dict(face)
    if out.get("id") is None:
        out["id"] = out.get("face_id") or str(uuid.uuid4())
    if out.get("face_id") is None:
        out["face_id"] = out["id"]
    bbox = out.get("bbox")
    needs_xyxy = any(
        out.get(k) is None for k in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2")
    )
    if needs_xyxy and isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        out["bbox_x1"], out["bbox_y1"], out["bbox_x2"], out["bbox_y2"] = (
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3],
        )
    return out


# Values below this are treated as relative in-cycle offsets (0.0/0.5/1.0s),
# not Unix wall-clock epochs.
_EPOCH_FLOOR = 1_000_000_000.0  # ~2001-09-09


def _to_epoch_seconds(value: Any) -> Optional[float]:
    """Parse ISO / datetime / large numeric values into wall-clock epoch seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        epoch = float(value)
        return epoch if epoch >= _EPOCH_FLOOR else None
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            epoch = float(text)
            return epoch if epoch >= _EPOCH_FLOOR else None
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            return None
    return None


def _relative_offset_seconds(value: Any) -> Optional[float]:
    """Return in-cycle relative offset when value is clearly not wall-clock."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        offset = float(value)
        return offset if 0.0 <= offset < _EPOCH_FLOOR else None
    if isinstance(value, str):
        try:
            offset = float(value.strip())
            return offset if 0.0 <= offset < _EPOCH_FLOOR else None
        except ValueError:
            return None
    return None


def _local_frame_index(face: Dict[str, Any], frames_per_cycle: int) -> int:
    raw = face.get("frame_number", face.get("frame_index", 0))
    try:
        local = int(raw if raw is not None else 0)
    except (TypeError, ValueError):
        local = 0
    if frames_per_cycle > 0:
        # Instant Detection cycles always reuse 0..N-1; clamp noise.
        local = max(0, min(local, frames_per_cycle - 1))
    return local


def collect_faces_for_y_regroup(
    cycles: List[Dict[str, Any]],
    *,
    frames_per_cycle: int = 3,
    assumed_cycle_gap_seconds: float = 8.0,
    assumed_fps: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Flatten buffered cycle faces for Vision Y re-group.

    Each Instant Detection cycle stores frame_index as 0..frames_per_cycle-1.
    Concatenating cycles without remapping makes Vision's route contamination
    filter see ~3 frames / ~0.07s and drop real people (longest_run). Remap
    frames across the Y window and emit absolute source timestamps (epoch).
    """
    fpc = max(1, int(frames_per_cycle or 3))
    fps = max(float(assumed_fps or 30.0), 1.0)
    within_cycle_dt = 1.0 / fps
    # When cycle timestamps are missing, space virtual frames by ~cycle gap so
    # contamination's frame→seconds conversion still exceeds its 1.2s keep rule.
    gap_frames = max(fpc, int(max(float(assumed_cycle_gap_seconds or 8.0), 1.0) * fps))
    has_cycle_timestamps = any(
        _to_epoch_seconds((cycle or {}).get("timestamp")) is not None
        for cycle in (cycles or [])
    )
    frame_stride = fpc if has_cycle_timestamps else gap_frames
    out: List[Dict[str, Any]] = []

    for cycle_idx, cycle in enumerate(cycles or []):
        cycle_epoch = _to_epoch_seconds(cycle.get("timestamp"))
        for face in cycle.get("face_detections") or []:
            normalized = _normalize_face_for_regroup(face)
            local = _local_frame_index(normalized, fpc)
            remapped = cycle_idx * frame_stride + local
            normalized["frame_number"] = remapped
            normalized["frame_index"] = remapped
            normalized["cycle_index"] = cycle_idx
            normalized["local_frame_index"] = local

            # Prefer absolute face source time; else cycle wall-clock + relative offset.
            face_epoch = _to_epoch_seconds(normalized.get("timestamp"))
            if face_epoch is None:
                face_epoch = _to_epoch_seconds(normalized.get("created_at"))
            if face_epoch is None and cycle_epoch is not None:
                rel = _relative_offset_seconds(normalized.get("timestamp"))
                if rel is None:
                    rel = local * within_cycle_dt
                face_epoch = cycle_epoch + max(rel, 0.0)
            if face_epoch is not None:
                normalized["timestamp"] = face_epoch
                # Also stamp created_at so Vision normalize can recover epoch if needed.
                normalized["created_at"] = datetime.fromtimestamp(
                    face_epoch, tz=timezone.utc
                ).isoformat()

            out.append(normalized)
    return out


def _face_center_xy(face: Dict[str, Any]) -> tuple:
    """Return (center_x, center_y) from face center fields or bbox."""
    if face.get("center_x") is not None and face.get("center_y") is not None:
        try:
            return float(face["center_x"]), float(face["center_y"])
        except (TypeError, ValueError):
            pass
    position = face.get("position") if isinstance(face.get("position"), dict) else {}
    if position.get("x") is not None and position.get("y") is not None:
        try:
            return float(position["x"]), float(position["y"])
        except (TypeError, ValueError):
            pass
    bbox = face.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        try:
            x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
            return (x1 + x2) / 2.0, (y1 + y2) / 2.0
        except (TypeError, ValueError):
            pass
    try:
        x1 = float(face.get("bbox_x1"))
        y1 = float(face.get("bbox_y1"))
        x2 = float(face.get("bbox_x2"))
        y2 = float(face.get("bbox_y2"))
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0
    except (TypeError, ValueError):
        return 0.0, 0.0


def _face_timestamp_seconds(face: Dict[str, Any], fallback_index: int = 0) -> float:
    """Prefer wall-clock epoch; fall back to relative/frame-based ordering."""
    for key in ("timestamp", "created_at", "captured_at", "source_timestamp"):
        epoch = _to_epoch_seconds(face.get(key))
        if epoch is not None:
            return epoch
    raw = face.get("timestamp")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            pass
    frame = face.get("frame_number", face.get("frame_index", fallback_index))
    try:
        return float(frame) / 30.0
    except (TypeError, ValueError):
        return float(fallback_index)


def _bbox_from_face(face: Dict[str, Any]) -> Optional[List[float]]:
    bbox = face.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        try:
            return [float(v) for v in bbox[:4]]
        except (TypeError, ValueError):
            return None
    try:
        return [
            float(face["bbox_x1"]),
            float(face["bbox_y1"]),
            float(face["bbox_x2"]),
            float(face["bbox_y2"]),
        ]
    except (TypeError, ValueError, KeyError):
        return None


def generate_movement_tracking(group_faces: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build recording-pipeline-compatible movement_tracking from Instant faces.

    Shape matches Orchestrator `_generate_movement_tracking`:
    route_points + movement_statistics (incl. average_velocity).
    """
    if not group_faces:
        return {
            "route_points": [],
            "movement_statistics": {
                "total_route_points": 0,
                "total_distance_pixels": 0.0,
                "average_velocity": 0.0,
                "max_velocity": 0.0,
                "time_in_frame_seconds": 0.0,
            },
            "average_route_velocity": 0.0,
        }

    enriched: List[Dict[str, Any]] = []
    for i, face in enumerate(group_faces):
        if not isinstance(face, dict):
            continue
        cx, cy = _face_center_xy(face)
        ts = _face_timestamp_seconds(face, fallback_index=i)
        item = dict(face)
        item["center_x"] = cx
        item["center_y"] = cy
        item["timestamp"] = ts
        item["_sort_frame"] = int(
            face.get("frame_number", face.get("frame_index", i)) or i
        )
        enriched.append(item)

    enriched.sort(key=lambda f: (f.get("timestamp") or 0.0, f.get("_sort_frame") or 0))

    route_points: List[Dict[str, Any]] = []
    velocities: List[float] = []
    for i, face in enumerate(enriched):
        velocity_x = velocity_y = velocity_magnitude = 0.0
        if i > 0:
            prev = enriched[i - 1]
            time_diff = float(face["timestamp"]) - float(prev["timestamp"])
            if time_diff > 0:
                velocity_x = (float(face["center_x"]) - float(prev["center_x"])) / time_diff
                velocity_y = (float(face["center_y"]) - float(prev["center_y"])) / time_diff
                velocity_magnitude = (velocity_x**2 + velocity_y**2) ** 0.5

        point: Dict[str, Any] = {
            "sequence_number": i + 1,
            "frame_number": face.get("frame_number", face.get("frame_index")),
            "timestamp": face["timestamp"],
            "center_x": face["center_x"],
            "center_y": face["center_y"],
            "distance_from_camera": face.get("distance_from_camera"),
            "velocity_x": round(velocity_x, 2),
            "velocity_y": round(velocity_y, 2),
            "velocity_magnitude": round(velocity_magnitude, 2),
            "confidence": face.get("confidence"),
        }
        bbox = _bbox_from_face(face)
        if bbox is not None:
            point["bbox"] = bbox
        route_points.append(point)
        if velocity_magnitude > 0:
            velocities.append(velocity_magnitude)

    average_velocity = sum(velocities) / len(velocities) if velocities else 0.0
    max_velocity = max(velocities) if velocities else 0.0
    time_in_frame = (
        float(route_points[-1]["timestamp"]) - float(route_points[0]["timestamp"])
        if len(route_points) > 1
        else 0.0
    )
    # total_distance_pixels: integrate velocity*dt ≈ sum of segment lengths
    total_distance = 0.0
    for i in range(1, len(route_points)):
        dx = float(route_points[i]["center_x"]) - float(route_points[i - 1]["center_x"])
        dy = float(route_points[i]["center_y"]) - float(route_points[i - 1]["center_y"])
        total_distance += (dx**2 + dy**2) ** 0.5

    return {
        "route_points": route_points,
        "movement_statistics": {
            "total_route_points": len(route_points),
            "total_distance_pixels": round(total_distance, 2),
            "average_velocity": round(average_velocity, 2),
            "max_velocity": round(max_velocity, 2),
            "time_in_frame_seconds": round(time_in_frame, 2),
        },
        "average_route_velocity": round(average_velocity, 2),
    }


def _merge_movement_trackings(
    trackings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Concatenate route points from multiple trackings and recompute stats."""
    faces: List[Dict[str, Any]] = []
    for tracking in trackings:
        if not isinstance(tracking, dict):
            continue
        for point in tracking.get("route_points") or []:
            if isinstance(point, dict):
                faces.append(point)
    return generate_movement_tracking(faces)


def attach_movement_tracking_to_person_groups(
    person_groups: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach movement_tracking / route_points / average_route_velocity on groups."""
    for group in person_groups or []:
        if not isinstance(group, dict):
            continue
        faces = group.get("faces") or []
        if not faces and isinstance(group.get("best_face"), dict):
            faces = [group["best_face"]]
        tracking = generate_movement_tracking(
            [f for f in faces if isinstance(f, dict)]
        )
        group["movement_tracking"] = {
            "route_points": tracking["route_points"],
            "movement_statistics": tracking["movement_statistics"],
        }
        group["route_points"] = tracking["route_points"]
        group["average_route_velocity"] = tracking["average_route_velocity"]
    return person_groups


def attach_movement_tracking_to_instant_mvrs(
    instant_mvrs: List[Dict[str, Any]],
    person_groups: List[Dict[str, Any]],
    cycles: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Copy / build movement_tracking onto InstantMvrs.

    Prefer matching person_groups by person_object_uuid; else use cycle
    person_objects faces; else a single-point route from InstantMvr bbox.
    """
    group_by_pou: Dict[str, Dict[str, Any]] = {}
    for group in person_groups or []:
        if not isinstance(group, dict):
            continue
        pou = group.get("person_object_uuid") or group.get("person_id")
        if pou:
            group_by_pou[str(pou)] = group

    cycle_persons_by_pou: Dict[str, Dict[str, Any]] = {}
    for cycle in cycles or []:
        for person in cycle.get("person_objects") or []:
            if not isinstance(person, dict):
                continue
            pou = person.get("person_object_uuid") or person.get("person_id")
            if pou:
                cycle_persons_by_pou[str(pou)] = person

    for mvr in instant_mvrs or []:
        if not isinstance(mvr, dict):
            continue
        pou = mvr.get("person_object_uuid")
        tracking = None
        if pou and str(pou) in group_by_pou:
            group = group_by_pou[str(pou)]
            tracking = group.get("movement_tracking")
            if not tracking and group.get("route_points"):
                tracking = generate_movement_tracking(group.get("faces") or [])
        if tracking is None and pou and str(pou) in cycle_persons_by_pou:
            person = cycle_persons_by_pou[str(pou)]
            tracking = generate_movement_tracking(person.get("faces") or [])
        if tracking is None:
            # Single-point fallback from InstantMvr best bbox.
            bbox = mvr.get("bbox")
            faces = []
            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                faces = [
                    {
                        "bbox": list(bbox),
                        "confidence": mvr.get("face_quality") or mvr.get("quality_score"),
                        "frame_number": 0,
                        "timestamp": mvr.get("timestamp") or mvr.get("flush_started_at"),
                    }
                ]
            tracking = generate_movement_tracking(faces)

        mvr["movement_tracking"] = {
            "route_points": tracking.get("route_points") or [],
            "movement_statistics": tracking.get("movement_statistics") or {},
        }
        mvr["route_points"] = tracking.get("route_points") or []
        mvr["average_route_velocity"] = tracking.get("average_route_velocity") or 0.0
    return instant_mvrs


def attach_movement_tracking_to_merge_result(
    merge_result: Dict[str, Any],
    instant_mvrs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Union member InstantMvr routes onto each hierarchical merge group."""
    if not isinstance(merge_result, dict):
        return merge_result
    mvr_by_uid: Dict[str, Dict[str, Any]] = {}
    for mvr in instant_mvrs or []:
        if not isinstance(mvr, dict):
            continue
        uid = mvr.get("instant_mvr_uuid") or mvr.get("mvr_people_uuid")
        if uid:
            mvr_by_uid[str(uid)] = mvr

    for group in merge_result.get("merge_groups") or []:
        if not isinstance(group, dict):
            continue
        member_uids: List[str] = []
        super_uid = group.get("super_individual_uuid")
        if super_uid:
            member_uids.append(str(super_uid))
        for uid in group.get("merged_mvr_uuids") or []:
            if uid is not None:
                member_uids.append(str(uid))
        for member in group.get("members") or []:
            if isinstance(member, dict):
                uid = member.get("instant_mvr_uuid") or member.get("mvr_people_uuid")
                if uid:
                    member_uids.append(str(uid))

        trackings = []
        for uid in member_uids:
            mvr = mvr_by_uid.get(uid)
            if not mvr:
                continue
            tracking = mvr.get("movement_tracking")
            if isinstance(tracking, dict):
                trackings.append(tracking)
        combined = _merge_movement_trackings(trackings)
        group["movement_tracking"] = {
            "route_points": combined["route_points"],
            "movement_statistics": combined["movement_statistics"],
        }
        group["route_points"] = combined["route_points"]
        group["average_route_velocity"] = combined["average_route_velocity"]
    return merge_result


def _person_groups_from_instant_mvrs(
    instant_mvrs: List[Dict[str, Any]],
    merge_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Fallback person_groups when Vision re-group returns empty."""
    groups: List[Dict[str, Any]] = []
    supers = merge_result.get("super_individuals") or []
    merge_groups = merge_result.get("merge_groups") or []

    if merge_groups:
        for idx, group in enumerate(merge_groups):
            members = (
                group.get("members")
                or group.get("mvr_uuids")
                or group.get("mvr_people_uuids")
                or []
            )
            groups.append(
                {
                    "person_object_uuid": str(
                        group.get("group_id")
                        or group.get("super_individual_uuid")
                        or (members[0] if members else uuid.uuid4())
                    ),
                    "face_count": max(1, len(members)),
                    "faces": [],
                    "instant_mvr_uuids": [str(m) for m in members],
                    "source": "hierarchical_merge_fallback",
                    "group_index": idx,
                }
            )
        return groups

    if supers:
        for sid in supers:
            groups.append(
                {
                    "person_object_uuid": str(sid),
                    "face_count": 1,
                    "faces": [],
                    "instant_mvr_uuids": [str(sid)],
                    "source": "super_individual_fallback",
                }
            )
        return groups

    for mvr in instant_mvrs or []:
        uid = mvr.get("instant_mvr_uuid") or mvr.get("mvr_people_uuid") or str(uuid.uuid4())
        groups.append(
            {
                "person_object_uuid": str(uid),
                "face_count": 1,
                "faces": [],
                "instant_mvr_uuids": [str(uid)],
                "source": "instant_mvr_fallback",
            }
        )
    return groups


def _regroup_faces(
    face_detections: List[Dict[str, Any]],
    *,
    camera_id: str,
    auth_token: Optional[str],
    enable_contamination: bool = True,
) -> List[Dict[str, Any]]:
    if not face_detections:
        return []
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = (
            auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        )
    normalized = [_normalize_face_for_regroup(f) for f in face_detections]
    body = {
        "correlation_id": str(uuid.uuid4()),
        "consumer": "instant_detection",
        "face_detections": normalized,
        "tolerance_percent": 20.0,
        "enable_quality_analysis": True,
        "enable_tier3_embedding": False,
        "enable_contamination_filter": enable_contamination,
        "grouping_metadata": {"camera_id": camera_id, "phase": "y_flush_regroup"},
    }
    resp = requests.post(_vision_group_url(), json=body, headers=headers, timeout=60)
    if resp.status_code != 200:
        logger.warning(
            "Y re-group failed for %s: %s %s",
            camera_id,
            resp.status_code,
            resp.text[:200],
        )
        return []
    data = resp.json()
    return data.get("person_groups") or []


def _hierarchical_merge(
    instant_mvrs: List[Dict[str, Any]],
    *,
    threshold: float,
    auth_token: Optional[str],
) -> Dict[str, Any]:
    if not instant_mvrs:
        return {"super_individuals": [], "merge_groups": [], "statistics": {}}
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = (
            auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        )
    records = []
    for mvr in instant_mvrs:
        emb = mvr.get("face_embedding")
        if not emb:
            continue
        records.append(
            {
                "mvr_people_uuid": mvr.get("instant_mvr_uuid") or mvr.get("mvr_people_uuid"),
                "instant_mvr_uuid": mvr.get("instant_mvr_uuid"),
                "face_embedding": emb,
                "quality_score": mvr.get("quality_score") or mvr.get("face_quality") or 0.5,
                "face_quality": mvr.get("face_quality") or 0.5,
                "gender": (mvr.get("age_gender") or {}).get("gender")
                if isinstance(mvr.get("age_gender"), dict)
                else mvr.get("gender"),
                "age_min": (mvr.get("age_gender") or {}).get("age_min")
                if isinstance(mvr.get("age_gender"), dict)
                else mvr.get("age_min"),
                "age_max": (mvr.get("age_gender") or {}).get("age_max")
                if isinstance(mvr.get("age_gender"), dict)
                else mvr.get("age_max"),
                "person_object_uuid": mvr.get("person_object_uuid"),
                "camera_id": mvr.get("camera_id"),
            }
        )
    if not records:
        return {"super_individuals": [], "merge_groups": [], "statistics": {}}

    resp = requests.post(
        _vmeta_preview_url(),
        json={
            "mvr_records": records,
            "similarity_threshold": threshold,
            "min_similarity_check": min(0.50, threshold),
            "force_merge": False,
        },
        headers=headers,
        timeout=90,
    )
    if resp.status_code != 200:
        logger.warning(
            "hierarchical preview-from-records failed: %s %s",
            resp.status_code,
            resp.text[:200],
        )
        return {
            "super_individuals": [r["mvr_people_uuid"] for r in records],
            "merge_groups": [],
            "statistics": {"total_mvr": len(records), "error": True},
            "fallback_records": records,
        }
    return resp.json()


def _write_media_log(payload: Dict[str, Any], auth_token: Optional[str]) -> Optional[int]:
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = (
            auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        )
    resp = requests.post(_media_logs_url(), json=payload, headers=headers, timeout=30)
    if resp.status_code not in (200, 201):
        logger.error(
            "Failed to write instant_detection_logs: %s %s",
            resp.status_code,
            resp.text[:300],
        )
        return None
    return (resp.json() or {}).get("id")


def run_y_window_flush(
    camera_id: str,
    *,
    session_uuid: Optional[str],
    auth_token: Optional[str],
    frames_per_cycle: int = 3,
    flush_interval_cycles: int = 12,
    merge_threshold: float = 0.60,
) -> Dict[str, Any]:
    """
    Drain up to Y cycles from Redis, re-group with contamination, hierarchical-merge,
    write Media instant_detection_logs. Only DB write for Instant Detection identity path.
    """
    started = datetime.now(timezone.utc)
    cycles = drain_flush_buffer(camera_id, max_cycles=flush_interval_cycles)
    if not cycles:
        return {"success": True, "flushed": False, "reason": "empty_buffer"}

    all_faces = collect_faces_for_y_regroup(cycles, frames_per_cycle=frames_per_cycle)
    all_mvrs: List[Dict[str, Any]] = []
    for cycle in cycles:
        for mvr in cycle.get("instant_mvrs") or []:
            all_mvrs.append(mvr)

    person_groups = _regroup_faces(
        all_faces,
        camera_id=camera_id,
        auth_token=auth_token,
        enable_contamination=True,
    )
    merge_result = _hierarchical_merge(
        all_mvrs,
        threshold=merge_threshold,
        auth_token=auth_token,
    )
    if not person_groups:
        person_groups = _person_groups_from_instant_mvrs(all_mvrs, merge_result)
        logger.info(
            "Y re-group empty for %s — fallback person_groups=%s from InstantMvrs/merge",
            camera_id,
            len(person_groups),
        )

    # Recording-parity movement trajectories for Instant Detection consumers.
    attach_movement_tracking_to_person_groups(person_groups)
    attach_movement_tracking_to_instant_mvrs(
        all_mvrs,
        person_groups,
        cycles=cycles,
    )
    attach_movement_tracking_to_merge_result(merge_result, all_mvrs)

    ended = datetime.now(timezone.utc)
    people_count = (
        len(merge_result.get("super_individuals") or [])
        or len(person_groups)
        or 0
    )

    log_body = {
        "camera_device_id": camera_id,
        "session_uuid": session_uuid,
        "flush_started_at": started.isoformat(),
        "flush_ended_at": ended.isoformat(),
        "cycle_count": len(cycles),
        "frames_per_cycle": frames_per_cycle,
        "merge_threshold": merge_threshold,
        "people_count": people_count,
        "log_type": "instant_detection",
        "payload_json": {
            "person_groups": person_groups,
            "instant_mvrs": all_mvrs,
            "hierarchical_merge": merge_result,
            "cycle_ids": [c.get("cycle_id") for c in cycles],
            "flush_interval_cycles": flush_interval_cycles,
        },
    }
    log_id = _write_media_log(log_body, auth_token)
    return {
        "success": bool(log_id),
        "flushed": True,
        "log_id": log_id,
        "people_count": people_count,
        "cycle_count": len(cycles),
    }
