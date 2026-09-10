"""
Instant-detection velocity helpers.

Converts Vision track velocity (px/ms) to estimated ground speed (m/s) using
face bbox height as a scale proxy (assumed adult face ~0.20 m).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Assumed adult face height for metres-per-pixel scale (no camera calibration).
FACE_HEIGHT_M = 0.20
# Optional body-height scale when face path is unavailable.
BODY_HEIGHT_M = 1.70
# Minimum face observations required for a valid speed (matches Tier-2).
MIN_SAMPLES_FOR_VELOCITY = 2
VELOCITY_SMOOTHING_ALPHA = 0.3

# Gait band floors (m/s). Trigger fires when speed >= selected band floor.
GAIT_THRESHOLD_MPS = {
    "walking": 1.25,  # ~4.5 km/h
    "light_running": 2.2,  # ~8 km/h
    "running": 3.3,  # ~12 km/h
    "fast_running": 5.0,  # ~18 km/h
}

GAIT_BAND_ORDER = ("walking", "light_running", "running", "fast_running")


def gait_band_for_speed(speed_mps: Optional[float]) -> Optional[str]:
    """Return the highest gait band whose floor the speed meets, or None."""
    if speed_mps is None:
        return None
    matched: Optional[str] = None
    for band in GAIT_BAND_ORDER:
        if speed_mps >= GAIT_THRESHOLD_MPS[band]:
            matched = band
    return matched


def _parse_created_at(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _bbox_center_and_height(bbox: Any) -> Tuple[float, float, float]:
    """Return (cx, cy, height_px) from xyxy or xywh-ish bbox."""
    if not bbox or len(bbox) < 4:
        return (0.0, 0.0, 0.0)
    x1, y1, x2_or_w, y2_or_h = [float(v) for v in bbox[:4]]
    if x2_or_w > x1 and y2_or_h > y1 and (x2_or_w - x1) < 5000 and (y2_or_h - y1) < 5000:
        x2, y2 = x2_or_w, y2_or_h
    else:
        x2, y2 = x1 + x2_or_w, y1 + y2_or_h
    height = max(0.0, y2 - y1)
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0, height)


def _mean_face_height_px(faces: List[Dict[str, Any]]) -> float:
    heights: List[float] = []
    for face in faces:
        _, _, h = _bbox_center_and_height(face.get("bbox"))
        if h > 0:
            heights.append(h)
    if not heights:
        return 0.0
    return sum(heights) / len(heights)


def _fallback_velocity_px_ms(faces: List[Dict[str, Any]]) -> Tuple[Dict[str, float], int]:
    """
    EMA velocity (px/ms) from timestamped face bboxes — same formula as Vision Tier-2.
    """
    if len(faces) < MIN_SAMPLES_FOR_VELOCITY:
        return ({"x": 0.0, "y": 0.0}, len(faces))

    ordered = sorted(
        faces,
        key=lambda f: (
            _parse_created_at(f.get("created_at")) or datetime.min,
            int(f.get("frame_index", f.get("frame_number", 0)) or 0),
        ),
    )

    velocity = {"x": 0.0, "y": 0.0}
    prev_cx, prev_cy, _ = _bbox_center_and_height(ordered[0].get("bbox"))
    prev_at = _parse_created_at(ordered[0].get("created_at"))
    prev_frame = int(ordered[0].get("frame_index", ordered[0].get("frame_number", 0)) or 0)
    samples = 1

    for face in ordered[1:]:
        cx, cy, _ = _bbox_center_and_height(face.get("bbox"))
        cur_at = _parse_created_at(face.get("created_at"))
        cur_frame = int(face.get("frame_index", face.get("frame_number", 0)) or 0)

        dt_ms: float = 0.0
        if prev_at is not None and cur_at is not None:
            dt_ms = (cur_at - prev_at).total_seconds() * 1000.0
        elif cur_frame != prev_frame:
            # Fallback heuristic: 500 ms between instant-detection sample frames.
            dt_ms = abs(cur_frame - prev_frame) * 500.0

        if dt_ms > 0:
            inst_vx = (cx - prev_cx) / dt_ms
            inst_vy = (cy - prev_cy) / dt_ms
            alpha = VELOCITY_SMOOTHING_ALPHA
            velocity = {
                "x": alpha * inst_vx + (1 - alpha) * velocity["x"],
                "y": alpha * inst_vy + (1 - alpha) * velocity["y"],
            }

        prev_cx, prev_cy = cx, cy
        prev_at = cur_at if cur_at is not None else prev_at
        prev_frame = cur_frame
        samples += 1

    return (velocity, samples)


def px_ms_to_mps(
    velocity_px_ms: Dict[str, float],
    height_px: float,
    height_m: float = FACE_HEIGHT_M,
) -> Optional[float]:
    """Convert image-plane velocity (px/ms) to estimated m/s via object height scale."""
    if height_px <= 0 or height_m <= 0:
        return None
    meters_per_pixel = height_m / height_px
    mag_px_ms = math.hypot(
        float(velocity_px_ms.get("x", 0.0)),
        float(velocity_px_ms.get("y", 0.0)),
    )
    return mag_px_ms * 1000.0 * meters_per_pixel


def enrich_person_with_velocity(person: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach velocity_px_ms / speed_mps / gait_band onto a person object in-place.

    People with fewer than MIN_SAMPLES_FOR_VELOCITY faces get speed_mps=None
    (excluded from crowd mean and single-person firing).
    """
    faces = person.get("faces") or []
    samples = int(person.get("samples") or person.get("frame_history") or len(faces) or 0)

    velocity = person.get("velocity") or person.get("velocity_px_ms")
    if not isinstance(velocity, dict):
        velocity = None

    if velocity is None or samples < MIN_SAMPLES_FOR_VELOCITY:
        velocity, samples = _fallback_velocity_px_ms(faces)

    person["velocity_px_ms"] = {
        "x": float(velocity.get("x", 0.0)),
        "y": float(velocity.get("y", 0.0)),
    }
    person["samples"] = samples
    person["scale_face_height_m"] = FACE_HEIGHT_M

    if samples < MIN_SAMPLES_FOR_VELOCITY:
        person["speed_mps"] = None
        person["gait_band"] = None
        return person

    mean_h = _mean_face_height_px(faces)
    speed = px_ms_to_mps(person["velocity_px_ms"], mean_h, FACE_HEIGHT_M)
    if speed is None:
        person["speed_mps"] = None
        person["gait_band"] = None
        return person

    person["speed_mps"] = round(float(speed), 4)
    person["gait_band"] = gait_band_for_speed(person["speed_mps"])
    return person


def body_person_speed_mps(body_person: Dict[str, Any]) -> Optional[float]:
    """Optional body-trajectory speed using 1.70 m body height scale."""
    trajectory = body_person.get("bbox_trajectory") or []
    if len(trajectory) < MIN_SAMPLES_FOR_VELOCITY:
        return None

    faces_like: List[Dict[str, Any]] = []
    heights: List[float] = []
    for i, point in enumerate(trajectory):
        bbox = point.get("bbox")
        _, _, h = _bbox_center_and_height(bbox)
        if h > 0:
            heights.append(h)
        # Body trajectory usually has frame indices; assume 0.5s spacing like faces.
        faces_like.append(
            {
                "bbox": bbox,
                "frame_index": int(point.get("frame", i)),
                "created_at": None,
            }
        )

    velocity, samples = _fallback_velocity_px_ms(faces_like)
    if samples < MIN_SAMPLES_FOR_VELOCITY or not heights:
        return None
    return px_ms_to_mps(velocity, sum(heights) / len(heights), BODY_HEIGHT_M)


def attach_cycle_velocity(
    person_objects: List[Dict[str, Any]],
    body_persons: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Enrich person_objects and return cycle-level crowd velocity summary.
    Falls back to body trajectories when no face people have valid speeds.
    """
    for person in person_objects:
        enrich_person_with_velocity(person)

    valid_speeds: List[float] = []
    people_compact: List[Dict[str, Any]] = []
    for person in person_objects:
        speed = person.get("speed_mps")
        if speed is None:
            continue
        valid_speeds.append(float(speed))
        people_compact.append(
            {
                "person_object_uuid": person.get("person_object_uuid")
                or person.get("person_id"),
                "speed_mps": person.get("speed_mps"),
                "gait_band": person.get("gait_band"),
            }
        )

    # Optional body fallback when face path produced no valid speeds.
    if not valid_speeds and body_persons:
        for body in body_persons:
            speed = body_person_speed_mps(body)
            if speed is None:
                continue
            speed = round(float(speed), 4)
            band = gait_band_for_speed(speed)
            body["speed_mps"] = speed
            body["gait_band"] = band
            valid_speeds.append(speed)
            people_compact.append(
                {
                    "person_object_uuid": body.get("body_person_id")
                    or body.get("person_object_uuid"),
                    "speed_mps": speed,
                    "gait_band": band,
                }
            )

    crowd_mps = (
        round(sum(valid_speeds) / len(valid_speeds), 4) if valid_speeds else None
    )
    max_mps = round(max(valid_speeds), 4) if valid_speeds else None

    return {
        "crowd_velocity_mps": crowd_mps,
        "crowd_person_count": len(valid_speeds),
        "max_person_speed_mps": max_mps,
        "velocity": {
            "crowd_mps": crowd_mps,
            "max_mps": max_mps,
            "valid_count": len(valid_speeds),
            "people": people_compact,
        },
    }
