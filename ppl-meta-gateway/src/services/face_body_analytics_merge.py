"""
Face ↔ body analytics modality helpers.

detection_modality:
  - face (default): face identities only
  - body: body identities only
  - both: merge overlapping face/body tracks; face wins demographics
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MAX_TEMPORAL_GAP_SEC = 3.0
MIN_IOU = 0.10
MAX_CENTER_DISTANCE_PX = 150.0
BODY_FRAME_DT_SEC = 0.5


def normalize_detection_modality(value: Optional[str]) -> str:
    raw = (value or "face").strip().lower()
    if raw in ("face", "body", "both"):
        return raw
    return "face"


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
        except ValueError:
            try:
                dt = datetime.fromtimestamp(float(text), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _bbox_iou(a: Sequence[float], b: Sequence[float]) -> float:
    try:
        ax1, ay1, ax2, ay2 = [float(v) for v in a[:4]]
        bx1, by1, bx2, by2 = [float(v) for v in b[:4]]
    except (TypeError, ValueError, IndexError):
        return 0.0
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return (inter / union) if union > 0 else 0.0


def _center_distance(a: Sequence[float], b: Sequence[float]) -> float:
    try:
        ax1, ay1, ax2, ay2 = [float(v) for v in a[:4]]
        bx1, by1, bx2, by2 = [float(v) for v in b[:4]]
    except (TypeError, ValueError, IndexError):
        return float("inf")
    acx, acy = (ax1 + ax2) / 2.0, (ay1 + ay2) / 2.0
    bcx, bcy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5


def _bbox_center(bbox: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
        return None
    try:
        x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0
    except (TypeError, ValueError):
        return None


def route_points_from_bbox_trajectory(
    trajectory: Any,
    *,
    media_start: Optional[datetime] = None,
    fps: Optional[float] = None,
    frame_dt_sec: float = BODY_FRAME_DT_SEC,
) -> List[Dict[str, Any]]:
    """Map body bbox_trajectory frames → analytics route_points."""
    if not isinstance(trajectory, list) or not trajectory:
        return []
    frames: List[int] = []
    for i, raw in enumerate(trajectory):
        if not isinstance(raw, dict):
            continue
        try:
            frames.append(int(raw.get("frame", i) if raw.get("frame") is not None else i))
        except (TypeError, ValueError):
            frames.append(i)
    base_frame = min(frames) if frames else 0
    dt = (1.0 / float(fps)) if fps and fps > 0 else float(frame_dt_sec)
    base_epoch = media_start.timestamp() if media_start is not None else None
    points: List[Dict[str, Any]] = []
    for i, raw in enumerate(trajectory):
        if not isinstance(raw, dict):
            continue
        bbox = raw.get("bbox")
        center = _bbox_center(bbox)
        if center is None:
            continue
        try:
            frame = int(raw.get("frame", i) if raw.get("frame") is not None else i)
        except (TypeError, ValueError):
            frame = i
        rel = max(0.0, float(frame - base_frame) * dt)
        ts = (base_epoch + rel) if base_epoch is not None else rel
        points.append(
            {
                "sequence_number": len(points) + 1,
                "frame_number": frame,
                "timestamp": ts,
                "center_x": center[0],
                "center_y": center[1],
                "bbox": list(bbox) if isinstance(bbox, (list, tuple)) else None,
                "confidence": raw.get("confidence"),
            }
        )
    return points


def _route_points_of(person: Dict[str, Any]) -> List[Dict[str, Any]]:
    tracking = person.get("movement_tracking")
    if isinstance(tracking, dict) and isinstance(tracking.get("route_points"), list):
        return [p for p in tracking["route_points"] if isinstance(p, dict)]
    routes = person.get("route_points")
    if isinstance(routes, list):
        return [p for p in routes if isinstance(p, dict)]
    traj = person.get("bbox_trajectory")
    if isinstance(traj, list) and traj:
        return route_points_from_bbox_trajectory(traj)
    return []


def _person_time_span(person: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime]]:
    first = _parse_dt(person.get("first_seen"))
    last = _parse_dt(person.get("last_seen"))
    routes = _route_points_of(person)
    if routes:
        ts_vals = []
        for point in routes:
            ts = _parse_dt(point.get("timestamp"))
            if ts is not None:
                ts_vals.append(ts)
        if ts_vals:
            route_first, route_last = min(ts_vals), max(ts_vals)
            first = min(first, route_first) if first else route_first
            last = max(last, route_last) if last else route_last
    if first and not last:
        last = first
    if last and not first:
        first = last
    return first, last


def _temporal_gap_sec(
    a_first: Optional[datetime],
    a_last: Optional[datetime],
    b_first: Optional[datetime],
    b_last: Optional[datetime],
) -> Optional[float]:
    if not a_first or not a_last or not b_first or not b_last:
        return None
    # Overlap → gap 0
    if a_first <= b_last and b_first <= a_last:
        return 0.0
    if a_last < b_first:
        return (b_first - a_last).total_seconds()
    return (a_first - b_last).total_seconds()


def _sample_bboxes(person: Dict[str, Any], limit: int = 8) -> List[List[float]]:
    boxes: List[List[float]] = []
    for point in _route_points_of(person):
        bbox = point.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            try:
                boxes.append([float(v) for v in bbox[:4]])
            except (TypeError, ValueError):
                continue
    avg = person.get("average_bbox") or person.get("best_bbox") or person.get("bbox")
    if isinstance(avg, (list, tuple)) and len(avg) >= 4:
        try:
            boxes.append([float(v) for v in avg[:4]])
        except (TypeError, ValueError):
            pass
    if not boxes:
        return []
    if len(boxes) <= limit:
        return boxes
    step = max(1, len(boxes) // limit)
    return boxes[::step][:limit]


def _spatial_match_score(face: Dict[str, Any], body: Dict[str, Any]) -> Optional[float]:
    face_boxes = _sample_bboxes(face)
    body_boxes = _sample_bboxes(body)
    if not face_boxes or not body_boxes:
        # No spatial evidence — allow temporal-only soft match with low score
        return 0.05
    best = 0.0
    matched = False
    for fb in face_boxes:
        for bb in body_boxes:
            iou = _bbox_iou(fb, bb)
            dist = _center_distance(fb, bb)
            if iou >= MIN_IOU or dist <= MAX_CENTER_DISTANCE_PX:
                matched = True
                # Prefer higher IoU; distance contributes a small secondary term
                score = iou + max(0.0, 1.0 - (dist / max(MAX_CENTER_DISTANCE_PX, 1.0))) * 0.25
                if score > best:
                    best = score
    return best if matched else None


def _same_scope(face: Dict[str, Any], body: Dict[str, Any]) -> bool:
    face_cam = str(face.get("camera_id") or face.get("camera_device_id") or "").strip()
    body_cam = str(body.get("camera_id") or body.get("camera_device_id") or "").strip()
    if face_cam and body_cam and face_cam != body_cam:
        return False

    face_media = str(
        face.get("source_media_uuid")
        or face.get("video_uuid")
        or face.get("featured_video_uuid")
        or ""
    ).strip()
    body_media = str(
        body.get("source_media_uuid")
        or body.get("video_uuid")
        or body.get("featured_video_uuid")
        or ""
    ).strip()
    if face_media and body_media and face_media != body_media:
        return False

    face_flush = face.get("flush_log_id")
    body_flush = body.get("flush_log_id")
    if face_flush is not None and body_flush is not None and str(face_flush) != str(body_flush):
        return False

    face_span = face.get("normalised_span_id")
    body_span = body.get("normalised_span_id")
    if face_span is not None and body_span is not None and str(face_span) != str(body_span):
        return False

    return True


def _union_route_points(
    face: Dict[str, Any], body: Dict[str, Any]
) -> List[Dict[str, Any]]:
    combined = list(_route_points_of(face)) + list(_route_points_of(body))
    def _key(point: Dict[str, Any]) -> Tuple[float, int]:
        ts = point.get("timestamp")
        try:
            t = float(ts) if isinstance(ts, (int, float)) else (
                _parse_dt(ts).timestamp() if _parse_dt(ts) else 0.0
            )
        except (TypeError, ValueError):
            t = 0.0
        try:
            frame = int(point.get("frame_number") or 0)
        except (TypeError, ValueError):
            frame = 0
        return (t, frame)

    combined.sort(key=_key)
    for i, point in enumerate(combined):
        point["sequence_number"] = i + 1
    return combined


def _merge_pair(face: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(face)
    body_id = (
        body.get("mvr_people_body_uuid")
        or body.get("body_person_id")
        or body.get("person_id")
    )
    merged["identity_modality"] = "merged"
    merged["linked_mvr_people_body_uuid"] = body_id
    merged["linked_body_person"] = {
        "body_person_id": body.get("body_person_id"),
        "mvr_people_body_uuid": body.get("mvr_people_body_uuid"),
        "posture": body.get("posture"),
        "quality_score": body.get("quality_score"),
    }
    route_points = _union_route_points(face, body)
    merged["route_points"] = route_points
    tracking = dict(merged.get("movement_tracking") or {}) if isinstance(
        merged.get("movement_tracking"), dict
    ) else {}
    tracking["route_points"] = route_points
    stats = dict(tracking.get("movement_statistics") or {}) if isinstance(
        tracking.get("movement_statistics"), dict
    ) else {}
    stats["total_route_points"] = len(route_points)
    tracking["movement_statistics"] = stats
    merged["movement_tracking"] = tracking

    f_first, f_last = _person_time_span(face)
    b_first, b_last = _person_time_span(body)
    firsts = [d for d in (f_first, b_first) if d is not None]
    lasts = [d for d in (f_last, b_last) if d is not None]
    if firsts:
        merged["first_seen"] = min(firsts).isoformat()
    if lasts:
        merged["last_seen"] = max(lasts).isoformat()
    if body.get("average_route_velocity") is not None and merged.get(
        "average_route_velocity"
    ) is None:
        merged["average_route_velocity"] = body.get("average_route_velocity")
    if body.get("speed_mps") is not None and merged.get("speed_mps") is None:
        merged["speed_mps"] = body.get("speed_mps")
    return merged


def merge_face_body_people(
    face_people: List[Dict[str, Any]],
    body_people: List[Dict[str, Any]],
    *,
    max_temporal_gap_sec: float = MAX_TEMPORAL_GAP_SEC,
) -> List[Dict[str, Any]]:
    """Greedy 1:1 face↔body merge by temporal + spatial overlap."""
    faces = [dict(p) for p in face_people if isinstance(p, dict)]
    bodies = [dict(p) for p in body_people if isinstance(p, dict)]
    for face in faces:
        face.setdefault("identity_modality", "face")
    for body in bodies:
        body.setdefault("identity_modality", "body")

    candidates: List[Tuple[float, int, int]] = []
    for fi, face in enumerate(faces):
        f_first, f_last = _person_time_span(face)
        for bi, body in enumerate(bodies):
            if not _same_scope(face, body):
                continue
            b_first, b_last = _person_time_span(body)
            gap = _temporal_gap_sec(f_first, f_last, b_first, b_last)
            if gap is None:
                # Missing times but same flush/media scope — soft-allow
                gap = 0.0
            if gap > max_temporal_gap_sec:
                continue
            spatial = _spatial_match_score(face, body)
            if spatial is None:
                continue
            # Prefer tighter temporal gaps
            score = spatial + max(0.0, 1.0 - (gap / max(max_temporal_gap_sec, 1e-6))) * 0.5
            candidates.append((score, fi, bi))

    candidates.sort(key=lambda item: item[0], reverse=True)
    used_faces: set = set()
    used_bodies: set = set()
    merged: List[Dict[str, Any]] = []
    for score, fi, bi in candidates:
        if fi in used_faces or bi in used_bodies:
            continue
        used_faces.add(fi)
        used_bodies.add(bi)
        pair = _merge_pair(faces[fi], bodies[bi])
        pair["merge_score"] = round(float(score), 4)
        merged.append(pair)

    for fi, face in enumerate(faces):
        if fi not in used_faces:
            merged.append(face)
    for bi, body in enumerate(bodies):
        if bi not in used_bodies:
            merged.append(body)
    return merged


def apply_detection_modality(
    face_people: List[Dict[str, Any]],
    body_people: List[Dict[str, Any]],
    modality: str,
) -> List[Dict[str, Any]]:
    mode = normalize_detection_modality(modality)
    if mode == "face":
        out = [dict(p) for p in face_people if isinstance(p, dict)]
        for person in out:
            person.setdefault("identity_modality", "face")
        return out
    if mode == "body":
        out = [dict(p) for p in body_people if isinstance(p, dict)]
        for person in out:
            person.setdefault("identity_modality", "body")
        return out
    return merge_face_body_people(face_people, body_people)


def body_people_from_flush_log(log: Dict[str, Any]) -> List[Dict[str, Any]]:
    camera_id = str(log.get("camera_device_id") or "").strip()
    payload = log.get("payload_json") or {}
    if not isinstance(payload, dict):
        payload = {}
    flush_ts = (
        _parse_dt(log.get("flush_ended_at"))
        or _parse_dt(log.get("flush_started_at"))
        or datetime.now(timezone.utc)
    )
    flush_iso = flush_ts.isoformat()
    people: List[Dict[str, Any]] = []
    for idx, person in enumerate(payload.get("body_persons") or []):
        if not isinstance(person, dict):
            continue
        pid = (
            person.get("body_person_id")
            or person.get("mvr_people_body_uuid")
            or f"body-flush-{log.get('id')}-{idx}"
        )
        route_points = _route_points_of(person)
        first = person.get("first_seen") or flush_iso
        last = person.get("last_seen") or flush_iso
        if route_points:
            first_ts = _parse_dt(route_points[0].get("timestamp"))
            last_ts = _parse_dt(route_points[-1].get("timestamp"))
            if first_ts:
                first = first_ts.isoformat()
            if last_ts:
                last = last_ts.isoformat()
        people.append(
            {
                "person_id": str(pid),
                "body_person_id": person.get("body_person_id"),
                "mvr_people_body_uuid": person.get("mvr_people_body_uuid"),
                "camera_id": camera_id or person.get("camera_id"),
                "gender": "unknown",
                "age": None,
                "quality_score": person.get("quality_score"),
                "average_route_velocity": person.get("average_route_velocity"),
                "speed_mps": person.get("speed_mps"),
                "gait_band": person.get("gait_band"),
                "motion_class": person.get("motion_class"),
                "posture": person.get("posture"),
                "first_seen": first,
                "last_seen": last,
                "route_points": route_points,
                "movement_tracking": person.get("movement_tracking")
                or {"route_points": route_points},
                "bbox_trajectory": person.get("bbox_trajectory"),
                "average_bbox": person.get("average_bbox") or person.get("best_bbox"),
                "flush_log_id": log.get("id"),
                "source": "instant_detection_logs",
                "identity_modality": "body",
            }
        )
    return people


def body_people_from_normalised_span(span: Dict[str, Any]) -> List[Dict[str, Any]]:
    camera_id = str(span.get("camera_device_id") or "").strip()
    payload = span.get("payload_json") or {}
    if not isinstance(payload, dict):
        payload = {}
    span_ts = (
        _parse_dt(span.get("span_end"))
        or _parse_dt(span.get("span_start"))
        or datetime.now(timezone.utc)
    )
    span_iso = span_ts.isoformat()
    people: List[Dict[str, Any]] = []
    for idx, person in enumerate(payload.get("body_persons") or []):
        if not isinstance(person, dict):
            continue
        pid = (
            person.get("body_person_id")
            or person.get("mvr_people_body_uuid")
            or f"body-norm-{span.get('id')}-{idx}"
        )
        route_points = _route_points_of(person)
        people.append(
            {
                "person_id": str(pid),
                "body_person_id": person.get("body_person_id"),
                "mvr_people_body_uuid": person.get("mvr_people_body_uuid"),
                "camera_id": camera_id or person.get("camera_id"),
                "gender": "unknown",
                "age": None,
                "quality_score": person.get("quality_score"),
                "average_route_velocity": person.get("average_route_velocity"),
                "speed_mps": person.get("speed_mps"),
                "gait_band": person.get("gait_band"),
                "motion_class": person.get("motion_class"),
                "posture": person.get("posture"),
                "first_seen": person.get("first_seen") or span_iso,
                "last_seen": person.get("last_seen") or span_iso,
                "route_points": route_points,
                "movement_tracking": person.get("movement_tracking")
                or {"route_points": route_points},
                "bbox_trajectory": person.get("bbox_trajectory"),
                "average_bbox": person.get("average_bbox") or person.get("best_bbox"),
                "normalised_span_id": span.get("id"),
                "source": "instant_detection_normalised_spans",
                "identity_modality": "body",
            }
        )
    return people


def recording_body_person_to_analytics(
    body: Dict[str, Any],
    *,
    video_uuid: str,
    camera_id: Optional[str] = None,
    camera_name: Optional[str] = None,
    media_timestamp: Optional[datetime] = None,
    fps: Optional[float] = None,
) -> Dict[str, Any]:
    """Shape a VMeta mvr_people_body row like an analytics mvr_people entry."""
    route_points = route_points_from_bbox_trajectory(
        body.get("bbox_trajectory"),
        media_start=media_timestamp,
        fps=fps,
    )
    first = body.get("first_seen") or body.get("created_at")
    last = body.get("last_seen") or body.get("created_at")
    if route_points:
        first_ts = _parse_dt(route_points[0].get("timestamp"))
        last_ts = _parse_dt(route_points[-1].get("timestamp"))
        if first_ts:
            first = first_ts.isoformat()
        if last_ts:
            last = last_ts.isoformat()
    uid = str(body.get("mvr_people_body_uuid") or body.get("body_person_id") or "")
    return {
        "mvr_people_uuid": uid,
        "person_id": uid,
        "mvr_people_body_uuid": body.get("mvr_people_body_uuid"),
        "body_person_id": body.get("featured_body_person_uuid")
        or body.get("body_person_id"),
        "camera_id": camera_id or body.get("camera_id"),
        "camera_name": camera_name,
        "source_media_uuid": video_uuid,
        "video_uuid": video_uuid,
        "featured_video_uuid": video_uuid,
        "gender": "unknown",
        "age": None,
        "quality_score": body.get("quality_score"),
        "posture": body.get("posture"),
        "first_seen": first,
        "last_seen": last,
        "route_points": route_points,
        "movement_tracking": {"route_points": route_points},
        "bbox_trajectory": body.get("bbox_trajectory"),
        "average_bbox": None,
        "appearances": [
            {
                "video_uuid": video_uuid,
                "camera_id": camera_id or body.get("camera_id"),
                "timestamp": first,
            }
        ],
        "identity_modality": "body",
    }


def filter_people_for_demographics(
    people: List[Dict[str, Any]],
    selected_genders: Optional[List[str]],
    selected_age_groups: Optional[List[str]],
    *,
    gender_of,
    age_group_of,
) -> List[Dict[str, Any]]:
    """
    Apply gender/age filters. Body-only rows are excluded when any demographic
    filter is active (they have no real demographics).
    """
    has_demo = bool(selected_genders) or bool(selected_age_groups)
    normalized_genders = {g.strip().lower() for g in selected_genders or [] if g.strip()}
    normalized_ages = {a.strip().lower() for a in selected_age_groups or [] if a.strip()}
    out: List[Dict[str, Any]] = []
    for person in people:
        modality = str(person.get("identity_modality") or "face").lower()
        if has_demo and modality == "body":
            continue
        if normalized_genders:
            gender = gender_of(person)
            if gender not in normalized_genders:
                continue
        if normalized_ages:
            age_group = age_group_of(person)
            if age_group not in normalized_ages:
                continue
        out.append(person)
    return out
