"""
Left / Stationary Object Trigger Worker

Tracks COCO object detections across instant cycles with IoU association.
V1: fire when a track is STABLE in ROI for T_stable.
V2: fire only after ATTENDED then ABANDONED when require_person_left is set.
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger

logger = logging.getLogger(__name__)

LEFT_OBJECT_HISTORY_KEY_PREFIX = "instant_left_objects:"
DEFAULT_ALLOWLIST = ["backpack", "handbag", "suitcase", "bottle"]
DEFAULT_T_STABLE = 60
DEFAULT_T_ABANDON = 30
DEFAULT_MIN_AREA = 400
DEFAULT_PROXIMITY_PX = 120.0
DEFAULT_IOU = 0.3
DEFAULT_MOTION_EPS_PX = 25.0
MAX_MISSED_CYCLES = 3

# Metrics counters (process-local)
_METRICS = {
    "left_object_tracks": 0,
    "left_object_fired": 0,
    "left_object_cleared": 0,
}


def get_left_object_metrics() -> Dict[str, int]:
    return dict(_METRICS)


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
            return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def _parse_roi(raw: Any) -> Optional[List[List[float]]]:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    if not isinstance(raw, list) or len(raw) < 3:
        return None
    pts: List[List[float]] = []
    for p in raw:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            return None
        try:
            pts.append([float(p[0]), float(p[1])])
        except (TypeError, ValueError):
            return None
    return pts


def _bbox_iou(a: Any, b: Any) -> float:
    if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)):
        return 0.0
    if len(a) < 4 or len(b) < 4:
        return 0.0
    try:
        ax1, ay1, ax2, ay2 = [float(v) for v in a[:4]]
        bx1, by1, bx2, by2 = [float(v) for v in b[:4]]
    except (TypeError, ValueError):
        return 0.0
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def _bbox_center(bbox: List[float]) -> Tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _bbox_area(bbox: List[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _point_in_polygon(x: float, y: float, polygon: List[List[float]]) -> bool:
    """Ray casting; polygon points in same coordinate space as x,y."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def _parse_timestamp(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw.astimezone(timezone.utc)
    if isinstance(raw, str) and raw:
        try:
            text = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


@dataclass
class ObjectObservation:
    timestamp: datetime
    bbox: List[float]
    class_label: str
    confidence: float


@dataclass
class ObjectTrack:
    track_id: str
    class_label: str
    last_bbox: List[float]
    first_seen: datetime
    last_seen: datetime
    stable_since: Optional[datetime] = None
    attended_at: Optional[datetime] = None
    abandoned_since: Optional[datetime] = None
    state: str = "NEW"  # NEW | STABLE | ATTENDED | ABANDONED | ACKNOWLEDGED | CLEARED
    fired: bool = False
    missed_cycles: int = 0
    confidence: float = 0.0
    observations: List[ObjectObservation] = field(default_factory=list)


@dataclass
class CameraObjectState:
    camera_id: str
    tracks: Dict[str, ObjectTrack] = field(default_factory=dict)
    last_frame_wh: Tuple[float, float] = (1920.0, 1080.0)


class LeftObjectWorker:
    """In-memory multicamera evaluator for left_object triggers."""

    def __init__(self) -> None:
        self._active_trigger_ids: set[str] = set()
        self._camera_state: Dict[str, CameraObjectState] = {}
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        import redis

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return self._redis

    @staticmethod
    def get_camera_device_ids(trigger: Trigger) -> List[str]:
        cameras = _parse_json_list(getattr(trigger, "camera_device_ids", None))
        if cameras:
            return cameras
        legacy = getattr(trigger, "camera_device_id", None)
        if legacy and legacy not in ("left_object", "body_posture", "vprofile_match", "velocity"):
            return [str(legacy)]
        return []

    @staticmethod
    def _trigger_params(trigger: Trigger) -> Dict[str, Any]:
        allowlist = [
            c.strip().lower()
            for c in _parse_json_list(getattr(trigger, "left_object_class_allowlist", None))
            if c and str(c).strip()
        ]
        if not allowlist:
            allowlist = list(DEFAULT_ALLOWLIST)
        roi = _parse_roi(getattr(trigger, "left_object_roi", None))
        t_stable = int(
            getattr(trigger, "left_object_t_stable_seconds", None) or DEFAULT_T_STABLE
        )
        t_abandon = int(
            getattr(trigger, "left_object_t_abandon_seconds", None) or DEFAULT_T_ABANDON
        )
        min_area = int(
            getattr(trigger, "left_object_min_box_area_px", None) or DEFAULT_MIN_AREA
        )
        require_left = bool(
            getattr(trigger, "left_object_require_person_left", None) or False
        )
        proximity = float(
            getattr(trigger, "left_object_proximity_px", None) or DEFAULT_PROXIMITY_PX
        )
        iou = float(
            getattr(trigger, "left_object_iou_threshold", None) or DEFAULT_IOU
        )
        return {
            "allowlist": allowlist,
            "roi": roi,
            "t_stable": max(5, t_stable),
            "t_abandon": max(5, t_abandon),
            "min_area": max(1, min_area),
            "require_person_left": require_left,
            "proximity_px": max(1.0, proximity),
            "iou_threshold": max(0.05, min(1.0, iou)),
            "motion_eps_px": DEFAULT_MOTION_EPS_PX,
        }

    def _load_history_from_redis(self, camera_id: str) -> List[Dict[str, Any]]:
        try:
            client = self._get_redis()
            key = f"{LEFT_OBJECT_HISTORY_KEY_PREFIX}{camera_id}"
            raw_items = client.lrange(key, 0, -1) or []
            cycles: List[Dict[str, Any]] = []
            for raw in raw_items:
                try:
                    item = json.loads(raw)
                    if isinstance(item, dict):
                        cycles.append(item)
                except (json.JSONDecodeError, TypeError):
                    continue
            return cycles
        except Exception as exc:
            logger.warning(
                "Failed to load left_object history for %s: %s", camera_id, exc
            )
            return []

    def _ensure_camera_state(self, camera_id: str) -> CameraObjectState:
        state = self._camera_state.get(camera_id)
        if state is None:
            state = CameraObjectState(camera_id=camera_id)
            self._camera_state[camera_id] = state
        return state

    def _normalize_objects(
        self,
        objects: Any,
        *,
        allowlist: List[str],
        min_area: int,
        roi: Optional[List[List[float]]],
        frame_wh: Tuple[float, float],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        fw, fh = frame_wh
        for det in objects or []:
            if not isinstance(det, dict):
                continue
            label = str(det.get("class_label") or "").strip().lower()
            if label not in allowlist:
                continue
            bbox = det.get("bbox")
            if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                continue
            try:
                bbox_f = [float(v) for v in bbox[:4]]
            except (TypeError, ValueError):
                continue
            if _bbox_area(bbox_f) < min_area:
                continue
            cx, cy = _bbox_center(bbox_f)
            if roi:
                # ROI is normalized 0-1; convert center to normalized for test
                nx, ny = cx / max(fw, 1.0), cy / max(fh, 1.0)
                if not _point_in_polygon(nx, ny, roi):
                    continue
            try:
                conf = float(det.get("confidence") or 0.0)
            except (TypeError, ValueError):
                conf = 0.0
            out.append(
                {
                    "bbox": bbox_f,
                    "class_label": label,
                    "confidence": conf,
                }
            )
            # Infer frame size from bbox extents when larger than default
            fw = max(fw, bbox_f[2])
            fh = max(fh, bbox_f[3])
        return out

    def _body_centers(self, body_persons: Any) -> List[Tuple[float, float]]:
        centers: List[Tuple[float, float]] = []
        for person in body_persons or []:
            if not isinstance(person, dict):
                continue
            bbox = person.get("average_bbox") or person.get("bbox")
            if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                continue
            try:
                bbox_f = [float(v) for v in bbox[:4]]
            except (TypeError, ValueError):
                continue
            centers.append(_bbox_center(bbox_f))
        return centers

    def _person_near(
        self,
        bbox: List[float],
        body_centers: List[Tuple[float, float]],
        proximity_px: float,
    ) -> bool:
        if not body_centers:
            return False
        ox, oy = _bbox_center(bbox)
        for bx, by in body_centers:
            if math.hypot(ox - bx, oy - by) <= proximity_px:
                return True
        return False

    def _ingest_cycle(
        self,
        state: CameraObjectState,
        *,
        timestamp: datetime,
        objects: List[Dict[str, Any]],
        body_persons: Any,
        params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update tracks; return fire payload if a track should fire this cycle."""
        iou_threshold = params["iou_threshold"]
        motion_eps = params["motion_eps_px"]
        t_stable = params["t_stable"]
        t_abandon = params["t_abandon"]
        require_left = params["require_person_left"]
        proximity = params["proximity_px"]

        body_centers = self._body_centers(body_persons)
        active_tracks = list(state.tracks.values())
        used: set[str] = set()
        fire_info: Optional[Dict[str, Any]] = None

        for det in objects:
            bbox = det["bbox"]
            label = det["class_label"]
            best: Optional[ObjectTrack] = None
            best_iou = 0.0
            for track in active_tracks:
                if track.track_id in used:
                    continue
                if track.class_label != label:
                    continue
                iou = _bbox_iou(bbox, track.last_bbox)
                if iou >= iou_threshold and iou > best_iou:
                    best_iou = iou
                    best = track
            if best is None:
                best = ObjectTrack(
                    track_id=str(uuid4()),
                    class_label=label,
                    last_bbox=bbox,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    confidence=det["confidence"],
                )
                state.tracks[best.track_id] = best
                _METRICS["left_object_tracks"] += 1
            used.add(best.track_id)

            # Motion check vs previous bbox
            prev_c = _bbox_center(best.last_bbox)
            cur_c = _bbox_center(bbox)
            moved = math.hypot(prev_c[0] - cur_c[0], prev_c[1] - cur_c[1]) > motion_eps

            best.last_bbox = bbox
            best.last_seen = timestamp
            best.missed_cycles = 0
            best.confidence = det["confidence"]
            best.observations.append(
                ObjectObservation(
                    timestamp=timestamp,
                    bbox=bbox,
                    class_label=label,
                    confidence=det["confidence"],
                )
            )
            if len(best.observations) > 48:
                best.observations = best.observations[-48:]

            if best.fired or best.state == "ACKNOWLEDGED":
                continue

            if moved:
                best.stable_since = None
                if best.state not in ("ATTENDED", "ABANDONED"):
                    best.state = "NEW"
                best.abandoned_since = None
                continue

            # Low motion
            if best.stable_since is None:
                best.stable_since = timestamp
            dwell = (timestamp - best.stable_since).total_seconds()

            if dwell < t_stable:
                best.state = "NEW"
                continue

            # STABLE reached
            if require_left:
                near = self._person_near(bbox, body_centers, proximity)
                if near:
                    best.state = "ATTENDED"
                    best.attended_at = timestamp
                    best.abandoned_since = None
                    continue
                if best.attended_at is None:
                    # Never attended while stable — fail closed for V2
                    best.state = "STABLE"
                    continue
                if best.abandoned_since is None:
                    best.abandoned_since = timestamp
                    best.state = "ABANDONED"
                abandon_dwell = (timestamp - best.abandoned_since).total_seconds()
                if abandon_dwell >= t_abandon and not best.fired:
                    best.fired = True
                    best.state = "ACKNOWLEDGED"
                    fire_info = self._fire_payload(
                        state.camera_id, best, timestamp, state_name="ABANDONED"
                    )
            else:
                best.state = "STABLE"
                if not best.fired:
                    best.fired = True
                    best.state = "ACKNOWLEDGED"
                    fire_info = self._fire_payload(
                        state.camera_id, best, timestamp, state_name="STABLE"
                    )

        # Missed tracks
        stale: List[str] = []
        for tid, track in state.tracks.items():
            if tid in used:
                continue
            track.missed_cycles += 1
            if track.missed_cycles > MAX_MISSED_CYCLES:
                stale.append(tid)
        for tid in stale:
            state.tracks.pop(tid, None)
            _METRICS["left_object_cleared"] += 1

        if fire_info:
            _METRICS["left_object_fired"] += 1
            logger.info(
                "left_object FIRE camera=%s track=%s class=%s state=%s "
                "metrics=%s",
                state.camera_id,
                fire_info.get("track_id"),
                fire_info.get("class_label"),
                fire_info.get("state"),
                _METRICS,
            )
        return fire_info

    @staticmethod
    def _fire_payload(
        camera_id: str,
        track: ObjectTrack,
        timestamp: datetime,
        *,
        state_name: str,
    ) -> Dict[str, Any]:
        dwell = (timestamp - (track.stable_since or track.first_seen)).total_seconds()
        return {
            "source_camera_id": camera_id,
            "track_id": track.track_id,
            "class_label": track.class_label,
            "bbox": track.last_bbox,
            "dwell_seconds": round(dwell, 2),
            "state": state_name,
            "zone_id": "roi",
            "confidence": round(float(track.confidence), 4),
            "crop_media_id": None,
            "fired_at": timestamp.isoformat(),
        }

    async def activate_trigger(self, trigger: Trigger) -> None:
        trigger_id = str(trigger.uuid)
        self._active_trigger_ids.add(trigger_id)
        cameras = self.get_camera_device_ids(trigger)
        for camera_id in cameras:
            self._ensure_camera_state(camera_id)
        logger.info(
            "Activated left_object trigger %s — cameras=%s params=%s",
            trigger_id,
            cameras,
            self._trigger_params(trigger),
        )

    async def deactivate_trigger(self, trigger_uuid: str) -> None:
        self._active_trigger_ids.discard(str(trigger_uuid))
        logger.info("Deactivated left_object trigger %s", trigger_uuid)

    async def ensure_trigger_loaded(self, trigger: Trigger) -> bool:
        trigger_id = str(trigger.uuid)
        cameras = self.get_camera_device_ids(trigger)
        if not cameras:
            return False
        if trigger_id not in self._active_trigger_ids:
            await self.activate_trigger(trigger)
        else:
            for camera_id in cameras:
                self._ensure_camera_state(camera_id)
        return True

    async def load_all_active_triggers(self) -> int:
        db: Session = SessionLocal()
        try:
            triggers = (
                db.query(Trigger)
                .filter(
                    Trigger.is_active == True,  # noqa: E712
                    Trigger.trigger_mode == "left_object",
                )
                .all()
            )
            for trigger in triggers:
                try:
                    await self.activate_trigger(trigger)
                except Exception as exc:
                    logger.error(
                        "Failed to restore left_object trigger %s: %s",
                        trigger.uuid,
                        exc,
                    )
            logger.info("Restored %d active left_object trigger(s)", len(triggers))
            return len(triggers)
        finally:
            db.close()

    async def evaluate(
        self,
        trigger: Trigger,
        event_data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        camera_id = event_data.get("camera_id")
        if not camera_id:
            return False, "Missing camera_id on event", None

        allowed = self.get_camera_device_ids(trigger)
        if allowed and camera_id not in allowed:
            return False, f"Camera {camera_id} not in allowlist", None

        params = self._trigger_params(trigger)
        state = self._ensure_camera_state(camera_id)
        timestamp = _parse_timestamp(event_data.get("timestamp"))

        objects_raw = event_data.get("objects")
        if not objects_raw:
            history = self._load_history_from_redis(camera_id)
            if history:
                latest = history[-1]
                objects_raw = latest.get("objects") or []
                timestamp = _parse_timestamp(
                    latest.get("timestamp") or event_data.get("timestamp")
                )
            else:
                return False, "No objects on event or Redis history", None

        # Infer frame size from bboxes
        fw, fh = state.last_frame_wh
        for det in objects_raw or []:
            if isinstance(det, dict) and isinstance(det.get("bbox"), (list, tuple)):
                try:
                    b = [float(v) for v in det["bbox"][:4]]
                    fw = max(fw, b[2])
                    fh = max(fh, b[3])
                except (TypeError, ValueError, IndexError):
                    pass
        state.last_frame_wh = (fw, fh)

        objects = self._normalize_objects(
            objects_raw,
            allowlist=params["allowlist"],
            min_area=params["min_area"],
            roi=params["roi"],
            frame_wh=state.last_frame_wh,
        )

        body_persons = event_data.get("body_persons") or []
        if params["require_person_left"] and not body_persons:
            # Fail closed for V2 when bodies missing — still ingest for STABLE tracking
            logger.debug(
                "left_object V2: no body_persons on event for %s (fail closed for abandon)",
                camera_id,
            )

        fire_info = self._ingest_cycle(
            state,
            timestamp=timestamp,
            objects=objects,
            body_persons=body_persons,
            params=params,
        )

        if fire_info:
            reason = (
                f"left_object MET: {fire_info.get('class_label')} "
                f"track {str(fire_info.get('track_id'))[:8]} "
                f"state={fire_info.get('state')} "
                f"dwell={fire_info.get('dwell_seconds')}s"
            )
            return True, reason, fire_info

        return (
            False,
            f"left_object not met for {camera_id} "
            f"(tracks={len(state.tracks)}, objects_in={len(objects)}, "
            f"require_person_left={params['require_person_left']})",
            None,
        )


_worker: Optional[LeftObjectWorker] = None


def get_left_object_worker() -> LeftObjectWorker:
    global _worker
    if _worker is None:
        _worker = LeftObjectWorker()
    return _worker
