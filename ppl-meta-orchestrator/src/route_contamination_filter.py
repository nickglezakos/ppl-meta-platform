"""
Route-based face contamination filter (Orchestrator mirror of Vision helper).

Keep both copies in sync via identical unit-test vectors. Continuity is
evaluated in frame space first, then converted to seconds via video_fps.
"""

from __future__ import annotations

import logging
import math
import statistics
from typing import Any, Dict, List, Sequence

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_FRAME_STEP = 10
DEFAULT_VIDEO_FPS = 30.0
MIN_LONGEST_RUN_SECONDS = 1.2
SHORT_SPAN_SECONDS = 2.0
MIN_OCCUPANCY = 0.5
RUN_GAP_FACTOR = 1.5
DEFAULT_MAX_LINK_FRAME_GAP = 20  # 2 * sample_frame_step when step=10


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _face_width_from_bbox(bbox: Any) -> float:
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


def compute_route_metrics(
    route_points: Sequence[Dict[str, Any]],
    sample_frame_step: int = DEFAULT_SAMPLE_FRAME_STEP,
    video_fps: float = DEFAULT_VIDEO_FPS,
) -> Dict[str, Any]:
    step = max(int(sample_frame_step or DEFAULT_SAMPLE_FRAME_STEP), 1)
    fps = float(video_fps) if video_fps and video_fps > 0 else DEFAULT_VIDEO_FPS

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
    span_seconds = span_frames / fps

    max_gap = RUN_GAP_FACTOR * step
    longest_run_frames = 1
    longest_wall_frames = 0
    run_start = frames[0]
    run_end = frames[0]
    for i in range(1, len(frames)):
        gap = frames[i] - frames[i - 1]
        if gap <= max_gap:
            run_end = frames[i]
        else:
            longest_run_frames = max(longest_run_frames, run_end - run_start + 1)
            longest_wall_frames = max(longest_wall_frames, run_end - run_start)
            run_start = frames[i]
            run_end = frames[i]
    longest_run_frames = max(longest_run_frames, run_end - run_start + 1)
    longest_wall_frames = max(longest_wall_frames, run_end - run_start)
    longest_run_seconds = (
        longest_wall_frames / fps if longest_wall_frames > 0 else step / fps
    )

    expected_samples = (span_frames / step) + 1.0 if span_frames > 0 else 1.0
    occupancy = len(sorted_pts) / expected_samples if expected_samples > 0 else 0.0
    occupancy = min(occupancy, 1.0) if expected_samples >= 1 else occupancy

    xs = [
        _safe_float(p.get("center_x", p.get("x")))
        for p in sorted_pts
    ]
    ys = [
        _safe_float(p.get("center_y", p.get("y")))
        for p in sorted_pts
    ]
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
    metrics = compute_route_metrics(route_points, sample_frame_step, video_fps)

    if metrics["n_points"] == 0:
        return {"keep": False, "reason": "empty_route", "metrics": metrics}

    if metrics["longest_run_seconds"] < min_longest_run_seconds:
        return {"keep": False, "reason": "longest_run", "metrics": metrics}

    if (
        metrics["span_seconds"] >= short_span_seconds
        and metrics["occupancy"] < min_occupancy
    ):
        return {"keep": False, "reason": "occupancy", "metrics": metrics}

    return {"keep": True, "reason": "ok", "metrics": metrics}


def route_points_from_group_faces(
    group_faces: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize Orchestrator group face dicts into route points."""
    points: List[Dict[str, Any]] = []
    for face in group_faces:
        bbox = face.get("bbox")
        if bbox is None and all(
            k in face for k in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2")
        ):
            bbox = [
                face["bbox_x1"],
                face["bbox_y1"],
                face["bbox_x2"],
                face["bbox_y2"],
            ]
        cx = face.get("center_x")
        cy = face.get("center_y")
        if cx is None or cy is None:
            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                cx = (_safe_float(bbox[0]) + _safe_float(bbox[2])) / 2.0
                cy = (_safe_float(bbox[1]) + _safe_float(bbox[3])) / 2.0
            else:
                cx = _safe_float(cx)
                cy = _safe_float(cy)
        point: Dict[str, Any] = {
            "frame_number": int(face.get("frame_number") or 0),
            "center_x": _safe_float(cx),
            "center_y": _safe_float(cy),
        }
        if bbox is not None:
            point["bbox"] = bbox
        if face.get("timestamp") is not None:
            point["timestamp"] = face.get("timestamp")
        points.append(point)
    points.sort(key=_point_frame)
    return points


def should_keep_person_group(
    group_faces: Sequence[Dict[str, Any]] = None,
    route_points: Sequence[Dict[str, Any]] = None,
    sample_frame_step: int = DEFAULT_SAMPLE_FRAME_STEP,
    video_fps: float = DEFAULT_VIDEO_FPS,
) -> Dict[str, Any]:
    points = list(route_points or [])
    if not points and group_faces:
        points = route_points_from_group_faces(group_faces)
    return should_keep_route(points, sample_frame_step, video_fps)
