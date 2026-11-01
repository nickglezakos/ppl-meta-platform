"""
Motion Trigger Worker

Evaluates instant-detection motion events against demographic-style conditions
across three dimensions (speed_band, motion_class, roi_transit) combined with
AND or OR logic. Replaces the former velocity trigger.
"""

from __future__ import annotations

import json
import logging
import math
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger
from src.services.motion_classification import classify_motion

logger = logging.getLogger(__name__)

# Keep in sync with ppl-meta-cameras/src/services/instant_velocity.py
GAIT_THRESHOLD_MPS = {
    "walking": 1.25,
    "light_running": 2.2,
    "running": 3.3,
    "fast_running": 5.0,
}

VALID_SCOPES = ("crowd", "single")
VALID_BANDS = tuple(GAIT_THRESHOLD_MPS.keys())
VALID_MOTION_CLASSES = (
    "stationary",
    "directed_transit",
    "loitering",
    "pacing",
    "erratic",
    "unknown",
)
VALID_ROI_TRANSITS = ("approach", "retreat", "inside")
VALID_CONDITION_FIELDS = ("speed_band", "motion_class", "roi_transit")
VALID_LOGIC = ("and", "or")

ROUTE_HISTORY_MAX = 12
ROUTE_HISTORY_TTL_S = 45.0
ROI_DIST_EPS = 0.02  # normalized units
SENTINEL_CAMERA_IDS = frozenset(
    {
        "velocity",
        "motion",
        "body_posture",
        "vprofile_match",
        "left_object",
        "vehicle_plate",
    }
)


def _parse_json_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x]
        except (json.JSONDecodeError, TypeError, ValueError):
            if raw.startswith("{") and raw.endswith("}"):
                items = raw[1:-1].split(",")
                return [item.strip().strip('"') for item in items if item.strip()]
    return []


def _parse_json_any(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return None


def _parse_roi(raw: Any) -> Optional[List[List[float]]]:
    parsed = _parse_json_any(raw)
    if not isinstance(parsed, list) or len(parsed) < 3:
        return None
    pts: List[List[float]] = []
    for p in parsed:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            return None
        try:
            pts.append([float(p[0]), float(p[1])])
        except (TypeError, ValueError):
            return None
    return pts


def _point_in_polygon(x: float, y: float, polygon: Sequence[Sequence[float]]) -> bool:
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = float(polygon[i][0]), float(polygon[i][1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def _dist_point_to_segment(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby
    if ab2 < 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    return math.hypot(px - (ax + t * abx), py - (ay + t * aby))


def distance_to_roi(x: float, y: float, polygon: Sequence[Sequence[float]]) -> float:
    """0 if inside; else min distance to polygon edges (same units as x,y)."""
    if _point_in_polygon(x, y, polygon):
        return 0.0
    n = len(polygon)
    best = float("inf")
    for i in range(n):
        ax, ay = float(polygon[i][0]), float(polygon[i][1])
        bx, by = float(polygon[(i + 1) % n][0]), float(polygon[(i + 1) % n][1])
        best = min(best, _dist_point_to_segment(x, y, ax, ay, bx, by))
    return best if best < float("inf") else 0.0


def _roi_centroid(polygon: Sequence[Sequence[float]]) -> Tuple[float, float]:
    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def classify_roi_transit(
    *,
    center: Optional[Tuple[float, float]],
    prev_center: Optional[Tuple[float, float]],
    velocity_xy: Optional[Tuple[float, float]],
    polygon: Optional[Sequence[Sequence[float]]],
    eps: float = ROI_DIST_EPS,
) -> Optional[str]:
    """
    Return approach | retreat | inside based on distance trend (primary)
    and optional velocity toward/away ROI centroid.
    """
    if polygon is None or center is None:
        return None
    cx, cy = center
    if _point_in_polygon(cx, cy, polygon):
        return "inside"

    d_now = distance_to_roi(cx, cy, polygon)
    delta_d: Optional[float] = None
    if prev_center is not None:
        d_prev = distance_to_roi(prev_center[0], prev_center[1], polygon)
        delta_d = d_now - d_prev

    toward = False
    away = False
    if velocity_xy is not None:
        vx, vy = velocity_xy
        speed = math.hypot(vx, vy)
        if speed > 1e-9:
            rcx, rcy = _roi_centroid(polygon)
            to_roi = (rcx - cx, rcy - cy)
            to_len = math.hypot(to_roi[0], to_roi[1])
            if to_len > 1e-9:
                # Cosine of angle between velocity and vector-to-ROI
                cos = (vx * to_roi[0] + vy * to_roi[1]) / (speed * to_len)
                toward = cos > 0.3
                away = cos < -0.3

    if delta_d is not None:
        if delta_d < -eps or (delta_d <= 0 and toward):
            return "approach"
        if delta_d > eps or (delta_d >= 0 and away):
            return "retreat"

    if toward:
        return "approach"
    if away:
        return "retreat"
    return None


def _normalize_condition_value(field: str, value: Any) -> Any:
    if field == "speed_band":
        return str(value or "").strip().lower()
    if field in ("motion_class", "roi_transit"):
        if isinstance(value, list):
            return [str(v).strip().lower() for v in value if v is not None]
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                parsed = _parse_json_any(text)
                if isinstance(parsed, list):
                    return [str(v).strip().lower() for v in parsed if v is not None]
            return [text.lower()] if text else []
    return value


def parse_motion_conditions(trigger: Trigger) -> List[Dict[str, Any]]:
    """Load motion_conditions; fall back to legacy velocity_band as speed_band."""
    raw = _parse_json_any(getattr(trigger, "motion_conditions", None))
    conditions: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip().lower()
            if field not in VALID_CONDITION_FIELDS:
                continue
            op = str(item.get("operator") or "eq").strip().lower()
            value = _normalize_condition_value(field, item.get("value"))
            conditions.append({"field": field, "operator": op, "value": value})

    if not conditions:
        band = str(
            getattr(trigger, "velocity_band", None)
            or getattr(trigger, "motion_band", None)
            or "walking"
        ).lower()
        if band in VALID_BANDS:
            conditions.append(
                {"field": "speed_band", "operator": "gte", "value": band}
            )
    return conditions


def _eval_speed_band(
    *,
    band: str,
    scope: str,
    velocity: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    floor = float(GAIT_THRESHOLD_MPS[band])
    crowd_mps = velocity.get("crowd_mps")
    max_mps = velocity.get("max_mps")
    valid_count = int(velocity.get("valid_count") or 0)
    people = velocity.get("people") or []
    info: Dict[str, Any] = {
        "band": band,
        "band_floor_mps": floor,
        "scope": scope,
        "crowd_mps": crowd_mps,
        "max_mps": max_mps,
        "valid_count": valid_count,
    }
    if scope == "crowd":
        if crowd_mps is None or valid_count < 1:
            return False, info
        ok = float(crowd_mps) >= floor
        info["measured_mps"] = float(crowd_mps)
        return ok, info

    if max_mps is None or valid_count < 1:
        return False, info
    offenders = [
        p
        for p in people
        if isinstance(p, dict)
        and p.get("speed_mps") is not None
        and float(p["speed_mps"]) >= floor
    ]
    ok = float(max_mps) >= floor
    info["measured_mps"] = float(max_mps)
    info["offending_people"] = offenders
    return ok, info


def _as_center_norm(person: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    cn = person.get("center_norm")
    if isinstance(cn, (list, tuple)) and len(cn) >= 2:
        try:
            return (float(cn[0]), float(cn[1]))
        except (TypeError, ValueError):
            pass
    cx = person.get("center_x")
    cy = person.get("center_y")
    # Already normalized if both in 0..1
    try:
        if cx is not None and cy is not None:
            fx, fy = float(cx), float(cy)
            if 0.0 <= fx <= 1.0 and 0.0 <= fy <= 1.0:
                return (fx, fy)
    except (TypeError, ValueError):
        pass
    return None


def _as_velocity_xy(person: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    for key in ("velocity_norm", "velocity_px_ms", "velocity"):
        v = person.get(key)
        if isinstance(v, dict):
            try:
                return (float(v.get("x", 0.0)), float(v.get("y", 0.0)))
            except (TypeError, ValueError):
                continue
    return None


def _route_points_from_tail(person: Dict[str, Any]) -> List[Dict[str, Any]]:
    tail = person.get("route_tail") or []
    points: List[Dict[str, Any]] = []
    if isinstance(tail, list):
        for i, pt in enumerate(tail):
            if not isinstance(pt, dict):
                continue
            cn = pt.get("center_norm")
            if isinstance(cn, (list, tuple)) and len(cn) >= 2:
                x, y = float(cn[0]), float(cn[1])
            else:
                try:
                    x = float(pt.get("center_x"))
                    y = float(pt.get("center_y"))
                except (TypeError, ValueError):
                    continue
            # Scale normalized coords to a synthetic pixel space for classifier.
            points.append(
                {
                    "center_x": x * 1000.0 if 0 <= x <= 1 and 0 <= y <= 1 else x,
                    "center_y": y * 1000.0 if 0 <= x <= 1 and 0 <= y <= 1 else y,
                    "timestamp": pt.get("timestamp", i),
                    "velocity_magnitude": pt.get("velocity_magnitude"),
                }
            )
    return points


class MotionTriggerWorker:
    """Multicamera evaluator for motion triggers (speed / class / ROI)."""

    def __init__(self) -> None:
        self._cameras: Dict[str, List[str]] = {}
        # camera:person_id -> deque of route samples
        self._routes: Dict[str, Deque[Dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=ROUTE_HISTORY_MAX)
        )
        self._last_center: Dict[str, Tuple[float, float]] = {}
        self._last_seen: Dict[str, float] = {}

    def get_camera_device_ids(self, trigger: Trigger) -> List[str]:
        cached = self._cameras.get(str(trigger.uuid))
        if cached is not None:
            return cached
        cameras = _parse_json_list(getattr(trigger, "camera_device_ids", None))
        legacy = getattr(trigger, "camera_device_id", None)
        if legacy and legacy not in SENTINEL_CAMERA_IDS:
            if legacy not in cameras:
                cameras.append(str(legacy))
        return cameras

    async def activate_trigger(self, trigger: Trigger) -> None:
        cameras = _parse_json_list(getattr(trigger, "camera_device_ids", None))
        self._cameras[str(trigger.uuid)] = cameras
        conditions = parse_motion_conditions(trigger)
        logger.info(
            "Activated motion trigger %s — cameras=%s scope=%s logic=%s conditions=%s",
            trigger.uuid,
            cameras,
            getattr(trigger, "motion_scope", None)
            or getattr(trigger, "velocity_scope", None),
            getattr(trigger, "motion_condition_logic", None) or "and",
            conditions,
        )

    async def deactivate_trigger(self, trigger_uuid: str) -> None:
        self._cameras.pop(str(trigger_uuid), None)
        logger.info("Deactivated motion trigger %s", trigger_uuid)

    async def ensure_trigger_loaded(self, trigger: Trigger) -> bool:
        cameras = self.get_camera_device_ids(trigger)
        if not cameras:
            return False
        self._cameras[str(trigger.uuid)] = cameras
        return True

    async def load_all_active_triggers(self) -> int:
        return self.restore_active_triggers()

    def restore_active_triggers(self, db: Optional[Session] = None) -> int:
        owns_session = db is None
        session = db or SessionLocal()
        try:
            triggers = (
                session.query(Trigger)
                .filter(
                    Trigger.is_active == True,  # noqa: E712
                    Trigger.trigger_mode.in_(["motion", "velocity"]),
                )
                .all()
            )
            for trigger in triggers:
                try:
                    # activate_trigger is async but only does sync work
                    cameras = _parse_json_list(
                        getattr(trigger, "camera_device_ids", None)
                    )
                    self._cameras[str(trigger.uuid)] = cameras
                except Exception as exc:
                    logger.warning(
                        "Failed to restore motion trigger %s: %s",
                        trigger.uuid,
                        exc,
                    )
            logger.info("Restored %d active motion trigger(s)", len(triggers))
            return len(triggers)
        finally:
            if owns_session:
                session.close()

    def _prune_history(self, now: float) -> None:
        stale = [
            key
            for key, ts in self._last_seen.items()
            if now - ts > ROUTE_HISTORY_TTL_S
        ]
        for key in stale:
            self._routes.pop(key, None)
            self._last_center.pop(key, None)
            self._last_seen.pop(key, None)

    def _update_person_history(
        self,
        camera_id: str,
        person: Dict[str, Any],
        timestamp: Any,
    ) -> Tuple[str, List[Dict[str, Any]], Optional[Tuple[float, float]]]:
        pid = str(
            person.get("person_object_uuid")
            or person.get("person_id")
            or person.get("track_id")
            or id(person)
        )
        key = f"{camera_id}:{pid}"
        center = _as_center_norm(person)
        prev = self._last_center.get(key)
        now = time.time()
        self._last_seen[key] = now

        route_points = _route_points_from_tail(person)
        if center is not None:
            sample = {
                "center_x": center[0] * 1000.0,
                "center_y": center[1] * 1000.0,
                "timestamp": timestamp if isinstance(timestamp, (int, float)) else now,
                "velocity_magnitude": None,
            }
            vxy = _as_velocity_xy(person)
            if vxy is not None:
                sample["velocity_magnitude"] = math.hypot(vxy[0], vxy[1])
            self._routes[key].append(sample)
            self._last_center[key] = center

        history = list(self._routes.get(key) or [])
        # Prefer longer of published tail vs rolling history
        if len(route_points) > len(history):
            history = route_points
        return key, history, prev

    def _person_motion_class(
        self, history: List[Dict[str, Any]], speed_mps: Optional[float]
    ) -> Dict[str, Any]:
        return classify_motion(
            route_points=history,
            average_speed_mps=speed_mps,
            movement_statistics={
                "time_in_frame_seconds": (
                    float(history[-1]["timestamp"]) - float(history[0]["timestamp"])
                    if len(history) >= 2
                    and isinstance(history[0].get("timestamp"), (int, float))
                    and isinstance(history[-1].get("timestamp"), (int, float))
                    else None
                )
            },
        )

    def _eval_motion_class_condition(
        self,
        *,
        wanted: List[str],
        people: List[Dict[str, Any]],
        camera_id: str,
        timestamp: Any,
    ) -> Tuple[bool, Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        for person in people:
            if not isinstance(person, dict):
                continue
            _, history, _ = self._update_person_history(camera_id, person, timestamp)
            speed = person.get("speed_mps")
            try:
                speed_f = float(speed) if speed is not None else None
            except (TypeError, ValueError):
                speed_f = None
            result = self._person_motion_class(history, speed_f)
            cls = str(result.get("motion_class") or "unknown")
            if cls in wanted:
                matches.append(
                    {
                        "person_object_uuid": person.get("person_object_uuid"),
                        "motion_class": cls,
                        "motion_confidence": result.get("motion_confidence"),
                    }
                )
        return bool(matches), {"wanted": wanted, "matches": matches}

    def _eval_roi_transit_condition(
        self,
        *,
        wanted: List[str],
        people: List[Dict[str, Any]],
        camera_id: str,
        timestamp: Any,
        roi: Optional[List[List[float]]],
    ) -> Tuple[bool, Dict[str, Any]]:
        if roi is None:
            return False, {"error": "motion_roi required for roi_transit", "wanted": wanted}
        matches: List[Dict[str, Any]] = []
        for person in people:
            if not isinstance(person, dict):
                continue
            key, _, prev = self._update_person_history(camera_id, person, timestamp)
            center = self._last_center.get(key) or _as_center_norm(person)
            transit = classify_roi_transit(
                center=center,
                prev_center=prev,
                velocity_xy=_as_velocity_xy(person),
                polygon=roi,
            )
            if transit and transit in wanted:
                matches.append(
                    {
                        "person_object_uuid": person.get("person_object_uuid"),
                        "roi_transit": transit,
                        "center_norm": list(center) if center else None,
                    }
                )
        return bool(matches), {"wanted": wanted, "matches": matches, "roi_points": len(roi)}

    async def evaluate(
        self, trigger: Trigger, data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        scope = str(
            getattr(trigger, "motion_scope", None)
            or getattr(trigger, "velocity_scope", None)
            or "crowd"
        ).lower()
        if scope not in VALID_SCOPES:
            return False, f"Invalid motion_scope={scope}", None

        logic = str(
            getattr(trigger, "motion_condition_logic", None) or "and"
        ).lower()
        if logic not in VALID_LOGIC:
            logic = "and"

        conditions = parse_motion_conditions(trigger)
        if not conditions:
            return False, "motion: no conditions configured", None

        needs_roi = any(c["field"] == "roi_transit" for c in conditions)
        roi = _parse_roi(getattr(trigger, "motion_roi", None))
        if needs_roi and roi is None:
            return False, "motion: motion_roi required when roi_transit condition set", None

        velocity = data.get("velocity") or {}
        if not isinstance(velocity, dict):
            velocity = {}
        people = [p for p in (velocity.get("people") or []) if isinstance(p, dict)]
        camera_id = str(data.get("camera_id") or "")
        timestamp = data.get("timestamp") or time.time()
        self._prune_history(time.time())

        results: List[bool] = []
        details: List[Dict[str, Any]] = []

        for cond in conditions:
            field = cond["field"]
            op = cond["operator"]
            value = cond["value"]
            ok = False
            info: Dict[str, Any] = {"field": field, "operator": op, "value": value}

            if field == "speed_band":
                band = str(value or "").lower()
                if band not in VALID_BANDS:
                    info["error"] = f"invalid band {band}"
                    ok = False
                else:
                    ok, band_info = _eval_speed_band(
                        band=band, scope=scope, velocity=velocity
                    )
                    info.update(band_info)
            elif field == "motion_class":
                wanted = value if isinstance(value, list) else [value]
                wanted = [str(v).lower() for v in wanted if v]
                ok, class_info = self._eval_motion_class_condition(
                    wanted=wanted,
                    people=people,
                    camera_id=camera_id,
                    timestamp=timestamp,
                )
                info.update(class_info)
            elif field == "roi_transit":
                wanted = value if isinstance(value, list) else [value]
                wanted = [str(v).lower() for v in wanted if v]
                ok, roi_info = self._eval_roi_transit_condition(
                    wanted=wanted,
                    people=people,
                    camera_id=camera_id,
                    timestamp=timestamp,
                    roi=roi,
                )
                info.update(roi_info)
            else:
                info["error"] = f"unknown field {field}"
                ok = False

            # Operators eq/in are covered by membership; gte only for speed_band.
            if field == "speed_band" and op not in ("gte", "eq"):
                # Still treat as floor match for legacy flexibility
                pass

            results.append(ok)
            details.append({**info, "passed": ok})

        if logic == "or":
            passed = any(results)
        else:
            passed = all(results) if results else False

        match_info: Dict[str, Any] = {
            "scope": scope,
            "logic": logic,
            "camera_id": camera_id,
            "conditions": details,
            "crowd_mps": velocity.get("crowd_mps"),
            "max_mps": velocity.get("max_mps"),
            "valid_count": velocity.get("valid_count"),
        }

        if passed:
            reason = (
                f"motion MET ({logic.upper()}): "
                + "; ".join(
                    f"{d['field']}={'pass' if d['passed'] else 'fail'}" for d in details
                )
                + f" on {camera_id}"
            )
            return True, reason, match_info

        reason = (
            f"motion not met ({logic.upper()}): "
            + "; ".join(
                f"{d['field']}={'pass' if d['passed'] else 'fail'}" for d in details
            )
        )
        return False, reason, match_info


_motion_worker: Optional[MotionTriggerWorker] = None


def get_motion_trigger_worker() -> MotionTriggerWorker:
    global _motion_worker
    if _motion_worker is None:
        _motion_worker = MotionTriggerWorker()
    return _motion_worker


# Backward-compatible aliases during velocity → motion rename.
def get_velocity_trigger_worker() -> MotionTriggerWorker:
    return get_motion_trigger_worker()


VelocityTriggerWorker = MotionTriggerWorker
