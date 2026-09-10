"""
Vehicle + Plate Trigger Worker

Tracks COCO vehicle detections across instant cycles with IoU association.
Fire once per track when STABLE in ROI for T_stable. Plate text is metadata.
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

VEHICLE_HISTORY_KEY_PREFIX = "instant_vehicles:"
DEFAULT_ALLOWLIST = ["car", "motorcycle", "bicycle", "truck", "bus"]
DEFAULT_T_STABLE = 15
DEFAULT_MIN_AREA = 800
DEFAULT_IOU = 0.3
DEFAULT_MOTION_EPS_PX = 40.0
MAX_MISSED_CYCLES = 3

_METRICS = {
    "vehicle_tracks": 0,
    "vehicle_fired": 0,
    "vehicle_cleared": 0,
    "plate_ocr_ok": 0,
    "plate_ocr_fail": 0,
}


def get_vehicle_plate_metrics() -> Dict[str, int]:
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
class VehicleObservation:
    timestamp: datetime
    bbox: List[float]
    class_label: str
    confidence: float
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None


@dataclass
class VehicleTrack:
    track_id: str
    class_label: str
    last_bbox: List[float]
    first_seen: datetime
    last_seen: datetime
    stable_since: Optional[datetime] = None
    state: str = "NEW"  # NEW | STABLE | ACKNOWLEDGED | CLEARED
    fired: bool = False
    missed_cycles: int = 0
    confidence: float = 0.0
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    plate_bbox: Optional[List[float]] = None
    observations: List[VehicleObservation] = field(default_factory=list)


@dataclass
class CameraVehicleState:
    camera_id: str
    tracks: Dict[str, VehicleTrack] = field(default_factory=dict)
    last_frame_wh: Tuple[float, float] = (1920.0, 1080.0)


class VehiclePlateWorker:
    """In-memory multicamera evaluator for vehicle_plate triggers."""

    def __init__(self) -> None:
        self._active_trigger_ids: set[str] = set()
        self._camera_state: Dict[str, CameraVehicleState] = {}
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
        if legacy and legacy not in (
            "vehicle_plate",
            "left_object",
            "body_posture",
            "vprofile_match",
            "velocity",
        ):
            return [str(legacy)]
        return []

    @staticmethod
    def _trigger_params(trigger: Trigger) -> Dict[str, Any]:
        allowlist = [
            c.strip().lower()
            for c in _parse_json_list(getattr(trigger, "vehicle_class_allowlist", None))
            if c and str(c).strip()
        ]
        if not allowlist:
            allowlist = list(DEFAULT_ALLOWLIST)
        roi = _parse_roi(getattr(trigger, "vehicle_roi", None))
        t_stable = int(
            getattr(trigger, "vehicle_t_stable_seconds", None) or DEFAULT_T_STABLE
        )
        min_area = int(
            getattr(trigger, "vehicle_min_box_area_px", None) or DEFAULT_MIN_AREA
        )
        iou = float(getattr(trigger, "vehicle_iou_threshold", None) or DEFAULT_IOU)
        plate_ocr = getattr(trigger, "vehicle_plate_ocr_enabled", None)
        if plate_ocr is None:
            plate_ocr = True
        every_n = int(
            getattr(trigger, "vehicle_plate_ocr_every_n_cycles", None) or 2
        )
        return {
            "allowlist": allowlist,
            "roi": roi,
            "t_stable": max(5, t_stable),
            "min_area": max(1, min_area),
            "iou_threshold": max(0.05, min(1.0, iou)),
            "motion_eps_px": DEFAULT_MOTION_EPS_PX,
            "plate_ocr_enabled": bool(plate_ocr),
            "plate_ocr_every_n": max(1, every_n),
        }

    def _load_history_from_redis(self, camera_id: str) -> List[Dict[str, Any]]:
        try:
            client = self._get_redis()
            key = f"{VEHICLE_HISTORY_KEY_PREFIX}{camera_id}"
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
                "Failed to load vehicle history for %s: %s", camera_id, exc
            )
            return []

    def _ensure_camera_state(self, camera_id: str) -> CameraVehicleState:
        state = self._camera_state.get(camera_id)
        if state is None:
            state = CameraVehicleState(camera_id=camera_id)
            self._camera_state[camera_id] = state
        return state

    def _normalize_vehicles(
        self,
        vehicles: Any,
        *,
        allowlist: List[str],
        min_area: int,
        roi: Optional[List[List[float]]],
        frame_wh: Tuple[float, float],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        fw, fh = frame_wh
        for det in vehicles or []:
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
                nx, ny = cx / max(fw, 1.0), cy / max(fh, 1.0)
                if not _point_in_polygon(nx, ny, roi):
                    continue
            try:
                conf = float(det.get("confidence") or 0.0)
            except (TypeError, ValueError):
                conf = 0.0
            plate_text = det.get("plate_text")
            plate_conf = det.get("plate_confidence")
            plate_bbox = det.get("plate_bbox")
            try:
                plate_conf_f = (
                    float(plate_conf) if plate_conf is not None else None
                )
            except (TypeError, ValueError):
                plate_conf_f = None
            plate_bbox_f = None
            if isinstance(plate_bbox, (list, tuple)) and len(plate_bbox) >= 4:
                try:
                    plate_bbox_f = [float(v) for v in plate_bbox[:4]]
                except (TypeError, ValueError):
                    plate_bbox_f = None
            if plate_text:
                _METRICS["plate_ocr_ok"] += 1
            elif det.get("plate_ocr_attempted"):
                _METRICS["plate_ocr_fail"] += 1
            out.append(
                {
                    "bbox": bbox_f,
                    "class_label": label,
                    "confidence": conf,
                    "plate_text": str(plate_text) if plate_text else None,
                    "plate_confidence": plate_conf_f,
                    "plate_bbox": plate_bbox_f,
                }
            )
            fw = max(fw, bbox_f[2])
            fh = max(fh, bbox_f[3])
        return out

    def _ingest_cycle(
        self,
        state: CameraVehicleState,
        *,
        timestamp: datetime,
        vehicles: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        iou_threshold = params["iou_threshold"]
        motion_eps = params["motion_eps_px"]
        t_stable = params["t_stable"]

        active_tracks = list(state.tracks.values())
        used: set[str] = set()
        fire_info: Optional[Dict[str, Any]] = None

        for det in vehicles:
            bbox = det["bbox"]
            label = det["class_label"]
            best: Optional[VehicleTrack] = None
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
                best = VehicleTrack(
                    track_id=str(uuid4()),
                    class_label=label,
                    last_bbox=bbox,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    confidence=det["confidence"],
                )
                state.tracks[best.track_id] = best
                _METRICS["vehicle_tracks"] += 1
            used.add(best.track_id)

            prev_c = _bbox_center(best.last_bbox)
            cur_c = _bbox_center(bbox)
            moved = math.hypot(prev_c[0] - cur_c[0], prev_c[1] - cur_c[1]) > motion_eps

            best.last_bbox = bbox
            best.last_seen = timestamp
            best.missed_cycles = 0
            best.confidence = det["confidence"]
            if det.get("plate_text"):
                best.plate_text = det["plate_text"]
                best.plate_confidence = det.get("plate_confidence")
                best.plate_bbox = det.get("plate_bbox")
            best.observations.append(
                VehicleObservation(
                    timestamp=timestamp,
                    bbox=bbox,
                    class_label=label,
                    confidence=det["confidence"],
                    plate_text=det.get("plate_text"),
                    plate_confidence=det.get("plate_confidence"),
                )
            )
            if len(best.observations) > 48:
                best.observations = best.observations[-48:]

            if best.fired or best.state == "ACKNOWLEDGED":
                continue

            if moved:
                best.stable_since = None
                best.state = "NEW"
                continue

            if best.stable_since is None:
                best.stable_since = timestamp
            dwell = (timestamp - best.stable_since).total_seconds()

            if dwell < t_stable:
                best.state = "NEW"
                continue

            best.state = "STABLE"
            if not best.fired:
                best.fired = True
                best.state = "ACKNOWLEDGED"
                fire_info = self._fire_payload(
                    state.camera_id, best, timestamp, state_name="STABLE"
                )

        stale: List[str] = []
        for tid, track in state.tracks.items():
            if tid in used:
                continue
            track.missed_cycles += 1
            if track.missed_cycles > MAX_MISSED_CYCLES:
                stale.append(tid)
        for tid in stale:
            state.tracks.pop(tid, None)
            _METRICS["vehicle_cleared"] += 1

        if fire_info:
            _METRICS["vehicle_fired"] += 1
            logger.info(
                "vehicle_plate FIRE camera=%s track=%s class=%s plate=%s metrics=%s",
                state.camera_id,
                fire_info.get("track_id"),
                fire_info.get("class_label"),
                fire_info.get("plate_text"),
                _METRICS,
            )
        return fire_info

    @staticmethod
    def _fire_payload(
        camera_id: str,
        track: VehicleTrack,
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
            "plate_text": track.plate_text,
            "plate_confidence": (
                round(float(track.plate_confidence), 4)
                if track.plate_confidence is not None
                else None
            ),
            "plate_bbox": track.plate_bbox,
            "confidence": round(float(track.confidence), 4),
            "fired_at": timestamp.isoformat(),
        }

    async def activate_trigger(self, trigger: Trigger) -> None:
        trigger_id = str(trigger.uuid)
        self._active_trigger_ids.add(trigger_id)
        cameras = self.get_camera_device_ids(trigger)
        for camera_id in cameras:
            self._ensure_camera_state(camera_id)
        logger.info(
            "Activated vehicle_plate trigger %s — cameras=%s params=%s",
            trigger_id,
            cameras,
            self._trigger_params(trigger),
        )

    async def deactivate_trigger(self, trigger_uuid: str) -> None:
        self._active_trigger_ids.discard(str(trigger_uuid))
        logger.info("Deactivated vehicle_plate trigger %s", trigger_uuid)

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
                    Trigger.trigger_mode == "vehicle_plate",
                )
                .all()
            )
            for trigger in triggers:
                try:
                    await self.activate_trigger(trigger)
                except Exception as exc:
                    logger.error(
                        "Failed to restore vehicle_plate trigger %s: %s",
                        trigger.uuid,
                        exc,
                    )
            logger.info(
                "Restored %d active vehicle_plate trigger(s)", len(triggers)
            )
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

        vehicles_raw = event_data.get("vehicles")
        if not vehicles_raw:
            history = self._load_history_from_redis(camera_id)
            if history:
                latest = history[-1]
                vehicles_raw = latest.get("vehicles") or []
                timestamp = _parse_timestamp(
                    latest.get("timestamp") or event_data.get("timestamp")
                )
            else:
                return False, "No vehicles on event or Redis history", None

        fw, fh = state.last_frame_wh
        for det in vehicles_raw or []:
            if isinstance(det, dict) and isinstance(det.get("bbox"), (list, tuple)):
                try:
                    b = [float(v) for v in det["bbox"][:4]]
                    fw = max(fw, b[2])
                    fh = max(fh, b[3])
                except (TypeError, ValueError, IndexError):
                    pass
        state.last_frame_wh = (fw, fh)

        vehicles = self._normalize_vehicles(
            vehicles_raw,
            allowlist=params["allowlist"],
            min_area=params["min_area"],
            roi=params["roi"],
            frame_wh=state.last_frame_wh,
        )

        fire_info = self._ingest_cycle(
            state,
            timestamp=timestamp,
            vehicles=vehicles,
            params=params,
        )

        if fire_info:
            plate = fire_info.get("plate_text") or "null"
            reason = (
                f"vehicle_plate MET: {fire_info.get('class_label')} "
                f"track {str(fire_info.get('track_id'))[:8]} "
                f"dwell={fire_info.get('dwell_seconds')}s plate={plate}"
            )
            return True, reason, fire_info

        return (
            False,
            f"vehicle_plate not met for {camera_id} "
            f"(tracks={len(state.tracks)}, vehicles_in={len(vehicles)})",
            None,
        )


_worker: Optional[VehiclePlateWorker] = None


def get_vehicle_plate_worker() -> VehiclePlateWorker:
    global _worker
    if _worker is None:
        _worker = VehiclePlateWorker()
    return _worker
