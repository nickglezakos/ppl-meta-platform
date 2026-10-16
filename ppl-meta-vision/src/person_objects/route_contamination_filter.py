"""
Route-based face contamination filter.

Hard-drops person tracks whose detections do not behave like a real person
over time (short blinks, scattered hits, frozen texture FPs). Continuity is
evaluated in frame space first, then converted to seconds via video_fps.
"""

from __future__ import annotations

import logging
import math
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# --- Tunable constants (v1) ---
DEFAULT_SAMPLE_FRAME_STEP = 10
DEFAULT_VIDEO_FPS = 30.0
MIN_LONGEST_RUN_SECONDS = 1.2
SHORT_SPAN_SECONDS = 2.0
MIN_OCCUPANCY = 0.5
RUN_GAP_FACTOR = 1.5  # run continues while frame_gap <= factor * sample_frame_step


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _face_width_from_bbox(bbox: Any) -> float:
    """Return face width from [x1,y1,x2,y2] or dict bbox; 0 if unavailable."""
    if bbox is None:
        return 0.0
    try:
        if isinstance(bbox, dict):
            x1 = _safe_float(bbox.get("x1", bbox.get("bbox_x1")))
            x2 = _safe_float(bbox.get("x2", bbox.get("bbox_x2")))
            return abs(x2 - x1)
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            return abs(_safe_float(bbox[2]) - _safe_float(bbox[0]))
    except (TypeError, ValueError, IndexError):
        return 0.0
    return 0.0


def _point_frame(point: Dict[str, Any]) -> int:
    return int(point.get("frame_number") or 0)


def infer_video_fps_from_points(
    route_points: Sequence[Dict[str, Any]],
    default: float = DEFAULT_VIDEO_FPS,
) -> float:
    """Infer FPS from (frame_number, timestamp) pairs when metadata is missing."""
    samples: List[Tuple[int, float]] = []
    for point in route_points:
        ts = point.get("timestamp")
        if ts is None:
            continue
        try:
            samples.append((_point_frame(point), float(ts)))
        except (TypeError, ValueError):
            continue
    if len(samples) < 2:
        return default
    samples.sort(key=lambda item: item[0])
    rates: List[float] = []
    for i in range(1, len(samples)):
        d_frame = samples[i][0] - samples[i - 1][0]
        d_time = samples[i][1] - samples[i - 1][1]
        if d_frame > 0 and d_time > 1e-3:
            rates.append(d_frame / d_time)
    if not rates:
        return default
    return max(float(statistics.median(rates)), 0.1)


def compute_route_metrics(
    route_points: Sequence[Dict[str, Any]],
    sample_frame_step: int = DEFAULT_SAMPLE_FRAME_STEP,
    video_fps: float = DEFAULT_VIDEO_FPS,
) -> Dict[str, Any]:
    """
    Compute continuity metrics for a person track.

    Args:
        route_points: Points with frame_number, optional center_x/center_y/bbox.
        sample_frame_step: Frames between samples (e.g. Vision frame_interval=10).
        video_fps: Source video FPS for converting frame spans to seconds.
    """
    step = max(int(sample_frame_step or DEFAULT_SAMPLE_FRAME_STEP), 1)
    fps = float(video_fps) if video_fps and video_fps > 0 else DEFAULT_VIDEO_FPS
    # Prefer real timestamps over an assumed 30fps — low-FPS edge recordings
    # otherwise look "too short" and get dropped as contamination.
    if fps == DEFAULT_VIDEO_FPS:
        fps = infer_video_fps_from_points(route_points, default=fps)

    if not route_points:
        return {
            "n_points": 0,
            "start_frame": 0,
            "end_frame": 0,
            "span_frames": 0,
            "span_seconds": 0.0,
            "longest_run_frames": 0,
            "longest_run_seconds": 0.0,
            "occupancy": 0.0,
            "normalized_center_std": 0.0,
            "sample_frame_step": step,
            "video_fps": fps,
        }

    sorted_pts = sorted(route_points, key=_point_frame)
    frames = [_point_frame(p) for p in sorted_pts]
    start_frame = frames[0]
    end_frame = frames[-1]
    span_frames = max(end_frame - start_frame, 0)

    timestamps: List[Optional[float]] = []
    for p in sorted_pts:
        ts = p.get("timestamp")
        try:
            timestamps.append(float(ts) if ts is not None else None)
        except (TypeError, ValueError):
            timestamps.append(None)
    has_timestamps = sum(1 for t in timestamps if t is not None) >= 2

    if has_timestamps:
        first_ts = next(t for t in timestamps if t is not None)
        last_ts = next(t for t in reversed(timestamps) if t is not None)
        span_seconds = max(last_ts - first_ts, 0.0)
    else:
        span_seconds = span_frames / fps

    max_gap = RUN_GAP_FACTOR * step
    longest_run_frames = 1
    longest_wall_frames = 0
    longest_run_seconds = 0.0
    run_start_idx = 0
    run_end_idx = 0
    for i in range(1, len(frames)):
        gap = frames[i] - frames[i - 1]
        if gap <= max_gap:
            run_end_idx = i
        else:
            wall = frames[run_end_idx] - frames[run_start_idx]
            longest_run_frames = max(
                longest_run_frames, frames[run_end_idx] - frames[run_start_idx] + 1
            )
            longest_wall_frames = max(longest_wall_frames, wall)
            if has_timestamps:
                t0 = timestamps[run_start_idx]
                t1 = timestamps[run_end_idx]
                if t0 is not None and t1 is not None:
                    longest_run_seconds = max(longest_run_seconds, max(t1 - t0, 0.0))
            run_start_idx = i
            run_end_idx = i
    wall = frames[run_end_idx] - frames[run_start_idx]
    longest_run_frames = max(
        longest_run_frames, frames[run_end_idx] - frames[run_start_idx] + 1
    )
    longest_wall_frames = max(longest_wall_frames, wall)
    if has_timestamps:
        t0 = timestamps[run_start_idx]
        t1 = timestamps[run_end_idx]
        if t0 is not None and t1 is not None:
            longest_run_seconds = max(longest_run_seconds, max(t1 - t0, 0.0))
        # Single-sample run: credit one sample interval from FPS.
        if longest_run_seconds <= 0:
            longest_run_seconds = step / fps
    else:
        # Single-sample runs have wall span 0; credit one sample interval.
        longest_run_seconds = (
            longest_wall_frames / fps if longest_wall_frames > 0 else step / fps
        )

    expected_samples = (span_frames / step) + 1.0 if span_frames > 0 else 1.0
    occupancy = len(sorted_pts) / expected_samples if expected_samples > 0 else 0.0
    occupancy = min(occupancy, 1.0) if expected_samples >= 1 else occupancy

    xs = [_safe_float(p.get("center_x", p.get("x"))) for p in sorted_pts]
    ys = [_safe_float(p.get("center_y", p.get("y"))) for p in sorted_pts]
    widths = [_face_width_from_bbox(p.get("bbox")) for p in sorted_pts]
    widths = [w for w in widths if w > 0]
    median_width = statistics.median(widths) if widths else 1.0

    if len(xs) >= 2:
        std_x = statistics.pstdev(xs)
        std_y = statistics.pstdev(ys)
        normalized_center_std = math.hypot(std_x, std_y) / median_width
    else:
        normalized_center_std = 0.0

    return {
        "n_points": len(sorted_pts),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "span_frames": span_frames,
        "span_seconds": round(span_seconds, 4),
        "longest_run_frames": longest_run_frames,
        "longest_run_seconds": round(longest_run_seconds, 4),
        "occupancy": round(occupancy, 4),
        "normalized_center_std": round(normalized_center_std, 4),
        "sample_frame_step": step,
        "video_fps": fps,
    }


def should_keep_route(
    route_points: Sequence[Dict[str, Any]],
    sample_frame_step: int = DEFAULT_SAMPLE_FRAME_STEP,
    video_fps: float = DEFAULT_VIDEO_FPS,
    min_longest_run_seconds: float = MIN_LONGEST_RUN_SECONDS,
    short_span_seconds: float = SHORT_SPAN_SECONDS,
    min_occupancy: float = MIN_OCCUPANCY,
) -> Dict[str, Any]:
    """
    Decide whether a person track should be kept.

    Keep rule (v1):
        keep if longest_run_seconds >= 1.2
             and (span_seconds < 2.0 or occupancy >= 0.5)
    """
    metrics = compute_route_metrics(route_points, sample_frame_step, video_fps)

    if metrics["n_points"] == 0:
        return {
            "keep": False,
            "reason": "empty_route",
            "metrics": metrics,
        }

    if metrics["longest_run_seconds"] < min_longest_run_seconds:
        return {
            "keep": False,
            "reason": "longest_run",
            "metrics": metrics,
        }

    if (
        metrics["span_seconds"] >= short_span_seconds
        and metrics["occupancy"] < min_occupancy
    ):
        return {
            "keep": False,
            "reason": "occupancy",
            "metrics": metrics,
        }

    return {
        "keep": True,
        "reason": "ok",
        "metrics": metrics,
    }


def _bbox_from_face(face: Dict[str, Any]) -> Optional[List[float]]:
    if all(k in face for k in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2")):
        return [
            _safe_float(face["bbox_x1"]),
            _safe_float(face["bbox_y1"]),
            _safe_float(face["bbox_x2"]),
            _safe_float(face["bbox_y2"]),
        ]
    bbox = face.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        return [
            _safe_float(bbox[0]),
            _safe_float(bbox[1]),
            _safe_float(bbox[2]),
            _safe_float(bbox[3]),
        ]
    return None


def _center_from_face(face: Dict[str, Any]) -> Tuple[float, float]:
    if "position_x" in face and "position_y" in face:
        return _safe_float(face["position_x"]), _safe_float(face["position_y"])
    if "center_x" in face and "center_y" in face:
        return _safe_float(face["center_x"]), _safe_float(face["center_y"])
    position = face.get("position") or {}
    if isinstance(position, dict) and ("x" in position or "y" in position):
        return _safe_float(position.get("x")), _safe_float(position.get("y"))
    bbox = _bbox_from_face(face)
    if bbox:
        return (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
    return 0.0, 0.0


def build_route_points_for_person(
    person_id: str,
    face_mappings: Sequence[Dict[str, Any]],
    face_detections: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build route points for one person from mappings + original detections."""
    face_by_id: Dict[str, Dict[str, Any]] = {}
    for face in face_detections:
        face_id = face.get("id")
        if face_id is not None:
            face_by_id[str(face_id)] = face

    points: List[Dict[str, Any]] = []
    for mapping in face_mappings:
        if str(mapping.get("person_id")) != str(person_id):
            continue
        face_id = mapping.get("face_detection_id", mapping.get("face_id"))
        face = face_by_id.get(str(face_id)) if face_id is not None else None

        frame_number = mapping.get("frame_number")
        if frame_number is None and face is not None:
            frame_number = face.get("frame_number", 0)
        frame_number = int(frame_number or 0)

        if face is not None:
            cx, cy = _center_from_face(face)
            bbox = _bbox_from_face(face)
            timestamp = face.get("timestamp")
        else:
            cx = _safe_float(mapping.get("position_x", (mapping.get("position") or {}).get("x")))
            cy = _safe_float(mapping.get("position_y", (mapping.get("position") or {}).get("y")))
            bbox = None
            timestamp = None

        point: Dict[str, Any] = {
            "frame_number": frame_number,
            "center_x": cx,
            "center_y": cy,
        }
        if bbox is not None:
            point["bbox"] = bbox
        if timestamp is not None:
            point["timestamp"] = timestamp
        points.append(point)

    points.sort(key=_point_frame)
    return points


def filter_contaminated_person_tracks(
    grouping_results: Dict[str, Any],
    face_detections: Sequence[Dict[str, Any]],
    sample_frame_step: int = DEFAULT_SAMPLE_FRAME_STEP,
    video_fps: float = DEFAULT_VIDEO_FPS,
) -> Dict[str, Any]:
    """
    Hard-drop contaminated person objects from grouping_results in place.

    Returns the same dict with filtered person_objects / face_mappings and
    updated statistics counters.
    """
    person_objects = list(grouping_results.get("person_objects") or [])
    face_mappings = list(grouping_results.get("face_mappings") or [])
    statistics = dict(grouping_results.get("statistics") or {})

    kept_persons: List[Dict[str, Any]] = []
    kept_person_ids = set()
    dropped = 0
    reasons: Dict[str, int] = {}

    for person in person_objects:
        person_id = person.get("person_id")
        route_points = build_route_points_for_person(
            str(person_id), face_mappings, face_detections
        )
        decision = should_keep_route(
            route_points,
            sample_frame_step=sample_frame_step,
            video_fps=video_fps,
        )
        if decision["keep"]:
            kept_persons.append(person)
            kept_person_ids.add(str(person_id))
        else:
            dropped += 1
            reason = decision["reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
            logger.info(
                "route_contaminant_dropped person_id=%s reason=%s face_count=%s metrics=%s",
                person_id,
                reason,
                person.get("face_count"),
                decision["metrics"],
            )

    kept_mappings = [
        m for m in face_mappings if str(m.get("person_id")) in kept_person_ids
    ]

    statistics["route_contaminants_dropped"] = dropped
    statistics["route_contaminant_reasons"] = reasons
    statistics["total_persons"] = len(kept_persons)
    statistics["total_faces"] = len(kept_mappings)

    grouping_results["person_objects"] = kept_persons
    grouping_results["face_mappings"] = kept_mappings
    grouping_results["statistics"] = statistics
    return grouping_results


def infer_sample_frame_step(
    face_detections: Iterable[Dict[str, Any]],
    default: int = DEFAULT_SAMPLE_FRAME_STEP,
) -> int:
    """Infer sample step from consecutive unique frame numbers when possible."""
    frames = sorted(
        {
            int(f.get("frame_number") or 0)
            for f in face_detections
            if f.get("frame_number") is not None
        }
    )
    if len(frames) < 2:
        return default
    gaps = [frames[i] - frames[i - 1] for i in range(1, len(frames)) if frames[i] > frames[i - 1]]
    if not gaps:
        return default
    # Use median positive gap as the typical sample step.
    return max(int(statistics.median(gaps)), 1)
