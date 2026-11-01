"""
Rule-based Instant Detection motion classification.

Combines velocity magnitude, heading consistency, and a simplified route
caricature into an explainable motion_class for Instant analysis.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Tunable defaults (see Instant motion classification plan).
MIN_ROUTE_POINTS = 3
STOP_SPEED_MPS = 0.3
# When only pixel speeds are available, treat this as a soft stop floor.
STOP_SPEED_PX_S = 15.0
HIGH_STRAIGHTNESS = 0.75
HIGH_HEADING_R = 0.7
HIGH_ZIGZAG = 0.4
HIGH_STOP_FRACTION = 0.8
HIGH_DWELL_SECONDS = 8.0
WALKING_SPEED_MPS = 1.25
LIGHT_RUNNING_MPS = 2.2
HIGH_TURN_RATE_RAD = 0.9
MAX_CARICATURE_KEYPOINTS = 6
RDP_EPSILON_NORM = 0.04
ELONGATION_ASPECT = 1.8


MOTION_CLASSES = (
    "stationary",
    "directed_transit",
    "loitering",
    "pacing",
    "erratic",
    "unknown",
)


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _point_xy(point: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    x = _safe_float(point.get("center_x"))
    y = _safe_float(point.get("center_y"))
    if x is None or y is None:
        return None
    return (x, y)


def _point_ts(point: Dict[str, Any], index: int) -> float:
    ts = _safe_float(point.get("timestamp"))
    if ts is not None:
        return ts
    return float(index)


def _segment_speeds_and_headings(
    points: Sequence[Dict[str, Any]],
) -> Tuple[List[float], List[float], List[float], float]:
    """
    Return (speeds_px_s, headings_rad, turn_deltas_rad, path_length_px).

    Speeds prefer velocity_magnitude when present; else segment length / dt.
    """
    speeds: List[float] = []
    headings: List[float] = []
    turns: List[float] = []
    path_length = 0.0
    prev_heading: Optional[float] = None

    coords: List[Tuple[float, float, float]] = []
    for i, point in enumerate(points):
        xy = _point_xy(point)
        if xy is None:
            continue
        coords.append((xy[0], xy[1], _point_ts(point, i)))

    for i in range(1, len(coords)):
        x0, y0, t0 = coords[i - 1]
        x1, y1, t1 = coords[i]
        dx = x1 - x0
        dy = y1 - y0
        dist = math.hypot(dx, dy)
        path_length += dist
        dt = t1 - t0
        mag = _safe_float(points[i].get("velocity_magnitude")) if i < len(points) else None
        if mag is not None and mag > 0:
            speed = mag
        elif dt > 0:
            speed = dist / dt
        else:
            speed = 0.0
        speeds.append(float(speed))
        if dist > 1e-6:
            heading = math.atan2(dy, dx)
            headings.append(heading)
            if prev_heading is not None:
                delta = heading - prev_heading
                # Wrap to [-pi, pi]
                while delta > math.pi:
                    delta -= 2 * math.pi
                while delta < -math.pi:
                    delta += 2 * math.pi
                turns.append(abs(delta))
            prev_heading = heading

    return speeds, headings, turns, path_length


def _heading_resultant_length(headings: Sequence[float]) -> float:
    if not headings:
        return 0.0
    sx = sum(math.cos(h) for h in headings)
    sy = sum(math.sin(h) for h in headings)
    return math.hypot(sx, sy) / len(headings)


def _heading_reversal_score(headings: Sequence[float]) -> float:
    """Fraction of consecutive heading pairs that reverse (~180 deg)."""
    if len(headings) < 2:
        return 0.0
    reversals = 0
    for i in range(1, len(headings)):
        delta = headings[i] - headings[i - 1]
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        if abs(delta) >= math.radians(120):
            reversals += 1
    return reversals / (len(headings) - 1)


def _normalize_points(
    points: Sequence[Dict[str, Any]],
) -> List[Tuple[float, float, float]]:
    """Return (x_norm, y_norm, t_norm) in 0..1 based on route bbox / time span."""
    coords: List[Tuple[float, float, float]] = []
    for i, point in enumerate(points):
        xy = _point_xy(point)
        if xy is None:
            continue
        coords.append((xy[0], xy[1], _point_ts(point, i)))
    if not coords:
        return []

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    ts = [c[2] for c in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_t, max_t = min(ts), max(ts)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    # Keep aspect using the larger spatial span so shapes stay proportional.
    span = max(span_x, span_y)
    span_t = max(max_t - min_t, 1e-6)

    return [
        (
            (x - min_x) / span,
            (y - min_y) / span,
            (t - min_t) / span_t,
        )
        for x, y, t in coords
    ]


def _perpendicular_distance(
    point: Tuple[float, float],
    start: Tuple[float, float],
    end: Tuple[float, float],
) -> float:
    x0, y0 = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return math.hypot(x0 - x1, y0 - y1)
    return abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def _rdp_indices(
    points: Sequence[Tuple[float, float]],
    epsilon: float,
) -> List[int]:
    if len(points) < 3:
        return list(range(len(points)))

    stack = [(0, len(points) - 1)]
    keep = {0, len(points) - 1}
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        max_dist = -1.0
        index = start
        for i in range(start + 1, end):
            dist = _perpendicular_distance(points[i], points[start], points[end])
            if dist > max_dist:
                max_dist = dist
                index = i
        if max_dist > epsilon:
            keep.add(index)
            stack.append((start, index))
            stack.append((index, end))
    return sorted(keep)


def _downsample_indices(indices: Sequence[int], max_points: int) -> List[int]:
    if len(indices) <= max_points:
        return list(indices)
    if max_points <= 2:
        return [indices[0], indices[-1]]
    out = [indices[0]]
    step = (len(indices) - 1) / float(max_points - 1)
    for i in range(1, max_points - 1):
        out.append(indices[int(round(i * step))])
    out.append(indices[-1])
    # Deduplicate while preserving order.
    deduped: List[int] = []
    for idx in out:
        if not deduped or deduped[-1] != idx:
            deduped.append(idx)
    return deduped


def _turn_label(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> str:
    abx, aby = b[0] - a[0], b[1] - a[1]
    bcx, bcy = c[0] - b[0], c[1] - b[1]
    cross = abx * bcy - aby * bcx
    dot = abx * bcx + aby * bcy
    mag_ab = math.hypot(abx, aby)
    mag_bc = math.hypot(bcx, bcy)
    if mag_ab < 1e-9 or mag_bc < 1e-9:
        return "straight"
    cos_ang = max(-1.0, min(1.0, dot / (mag_ab * mag_bc)))
    ang = math.acos(cos_ang)
    if ang < math.radians(25):
        return "straight"
    return "left" if cross > 0 else "right"


def build_route_caricature(points: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Simplify route into a compact caricature (≤ MAX_CARICATURE_KEYPOINTS)."""
    normalized = _normalize_points(points)
    empty = {
        "keypoints": [],
        "chord_vector": {"dx": 0.0, "dy": 0.0, "length": 0.0},
        "turn_signature": [],
        "loop_score": 0.0,
        "zigzag_score": 0.0,
        "extent_bbox": {"w": 0.0, "h": 0.0, "aspect": 1.0},
    }
    if len(normalized) < 2:
        if len(normalized) == 1:
            x, y, t = normalized[0]
            empty["keypoints"] = [{"x_norm": round(x, 4), "y_norm": round(y, 4), "t_norm": round(t, 4)}]
        return empty

    xy = [(p[0], p[1]) for p in normalized]
    indices = _rdp_indices(xy, RDP_EPSILON_NORM)
    indices = _downsample_indices(indices, MAX_CARICATURE_KEYPOINTS)
    keypoints_xy = [xy[i] for i in indices]
    keypoints = [
        {
            "x_norm": round(normalized[i][0], 4),
            "y_norm": round(normalized[i][1], 4),
            "t_norm": round(normalized[i][2], 4),
        }
        for i in indices
    ]

    start, end = keypoints_xy[0], keypoints_xy[-1]
    chord_dx = end[0] - start[0]
    chord_dy = end[1] - start[1]
    chord_len = math.hypot(chord_dx, chord_dy)

    turns: List[str] = []
    for i in range(1, len(keypoints_xy) - 1):
        turns.append(
            _turn_label(keypoints_xy[i - 1], keypoints_xy[i], keypoints_xy[i + 1])
        )

    # Zigzag: alternating left/right turns.
    zigzag = 0.0
    if len(turns) >= 2:
        flips = sum(
            1
            for i in range(1, len(turns))
            if turns[i] in ("left", "right")
            and turns[i - 1] in ("left", "right")
            and turns[i] != turns[i - 1]
        )
        zigzag = flips / (len(turns) - 1)

    xs = [p[0] for p in keypoints_xy]
    ys = [p[1] for p in keypoints_xy]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    aspect = (max(w, h) / max(min(w, h), 1e-6)) if (w > 0 or h > 0) else 1.0

    loop_score = 0.0
    if chord_len < 0.15 and len(keypoints_xy) >= 3:
        # Path roughly closes and has area extent.
        loop_score = max(0.0, min(1.0, 1.0 - chord_len / 0.15)) * min(1.0, (w + h))

    return {
        "keypoints": keypoints,
        "chord_vector": {
            "dx": round(chord_dx, 4),
            "dy": round(chord_dy, 4),
            "length": round(chord_len, 4),
        },
        "turn_signature": turns,
        "loop_score": round(loop_score, 4),
        "zigzag_score": round(zigzag, 4),
        "extent_bbox": {
            "w": round(w, 4),
            "h": round(h, 4),
            "aspect": round(aspect, 4),
        },
    }


def compute_motion_features(
    route_points: Sequence[Dict[str, Any]],
    *,
    average_speed_mps: Optional[float] = None,
    movement_statistics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Aggregate kinematic features used by the rule classifier."""
    stats = movement_statistics or {}
    speeds_px, headings, turns, path_length = _segment_speeds_and_headings(route_points)

    coords = [_point_xy(p) for p in route_points]
    coords = [c for c in coords if c is not None]
    net = 0.0
    if len(coords) >= 2:
        net = math.hypot(coords[-1][0] - coords[0][0], coords[-1][1] - coords[0][1])
    straightness = (net / path_length) if path_length > 1e-6 else 0.0
    straightness = max(0.0, min(1.0, straightness))

    heading_r = _heading_resultant_length(headings)
    mean_turn = sum(turns) / len(turns) if turns else 0.0

    mean_px = sum(speeds_px) / len(speeds_px) if speeds_px else 0.0
    max_px = max(speeds_px) if speeds_px else 0.0

    mean_speed_mps = _safe_float(average_speed_mps)
    if mean_speed_mps is None:
        mean_speed_mps = _safe_float(stats.get("average_speed_mps"))

    # Prefer m/s for stop fraction when available; else pixel speeds.
    if mean_speed_mps is not None and speeds_px:
        # Scale pixel segment speeds relative to mean px → approximate m/s series.
        if mean_px > 1e-6:
            scale = mean_speed_mps / mean_px
            speeds_mps_est = [s * scale for s in speeds_px]
        else:
            speeds_mps_est = [mean_speed_mps] * len(speeds_px)
        stop_floor = STOP_SPEED_MPS
        stop_fraction = sum(1 for s in speeds_mps_est if s < stop_floor) / len(
            speeds_mps_est
        )
        max_speed_mps = max(speeds_mps_est) if speeds_mps_est else mean_speed_mps
    else:
        stop_fraction = (
            sum(1 for s in speeds_px if s < STOP_SPEED_PX_S) / len(speeds_px)
            if speeds_px
            else 1.0
        )
        max_speed_mps = None

    dwell = _safe_float(stats.get("time_in_frame_seconds"))
    if dwell is None and len(route_points) >= 2:
        t0 = _point_ts(route_points[0], 0)
        t1 = _point_ts(route_points[-1], len(route_points) - 1)
        dwell = max(0.0, t1 - t0)
    if dwell is None:
        dwell = 0.0

    return {
        "point_count": len(coords),
        "straightness": round(straightness, 4),
        "heading_R": round(heading_r, 4),
        "heading_reversal": round(_heading_reversal_score(headings), 4),
        "stop_fraction": round(stop_fraction, 4),
        "mean_speed_mps": round(mean_speed_mps, 4) if mean_speed_mps is not None else None,
        "max_speed_mps": round(max_speed_mps, 4) if max_speed_mps is not None else None,
        "mean_speed_px_s": round(mean_px, 4),
        "max_speed_px_s": round(max_px, 4),
        "mean_turn_rad": round(mean_turn, 4),
        "dwell_seconds": round(float(dwell), 4),
        "path_length_px": round(path_length, 4),
        "net_displacement_px": round(net, 4),
    }


def _score_rules(
    features: Dict[str, Any],
    caricature: Dict[str, Any],
) -> Dict[str, float]:
    """Return soft scores per class; higher is better."""
    scores = {cls: 0.0 for cls in MOTION_CLASSES}
    n = int(features.get("point_count") or 0)
    if n < MIN_ROUTE_POINTS:
        scores["unknown"] = 1.0
        return scores

    straightness = float(features.get("straightness") or 0.0)
    heading_r = float(features.get("heading_R") or 0.0)
    stop_fraction = float(features.get("stop_fraction") or 0.0)
    mean_mps = features.get("mean_speed_mps")
    max_mps = features.get("max_speed_mps")
    mean_px = float(features.get("mean_speed_px_s") or 0.0)
    max_px = float(features.get("max_speed_px_s") or 0.0)
    mean_turn = float(features.get("mean_turn_rad") or 0.0)
    dwell = float(features.get("dwell_seconds") or 0.0)
    caricature_zigzag = float(caricature.get("zigzag_score") or 0.0)
    heading_reversal = float(features.get("heading_reversal") or 0.0)
    zigzag = max(caricature_zigzag, heading_reversal)
    extent = caricature.get("extent_bbox") or {}
    aspect = float(extent.get("aspect") or 1.0)
    # Cap absurd aspect from near-zero height.
    aspect = min(aspect, 20.0)
    elongated = aspect >= ELONGATION_ASPECT

    moving = False
    if mean_mps is not None:
        moving = mean_mps >= STOP_SPEED_MPS
        low_walking = mean_mps <= WALKING_SPEED_MPS
        high_speed = (max_mps or mean_mps) >= LIGHT_RUNNING_MPS
    else:
        moving = mean_px >= STOP_SPEED_PX_S
        low_walking = mean_px < 80.0
        high_speed = max_px >= 150.0

    # Stationary
    if stop_fraction >= HIGH_STOP_FRACTION and not moving:
        scores["stationary"] = 0.6 + 0.4 * stop_fraction

    # Directed transit
    if (
        straightness >= HIGH_STRAIGHTNESS
        and heading_r >= HIGH_HEADING_R
        and moving
    ):
        scores["directed_transit"] = 0.5 + 0.25 * straightness + 0.25 * heading_r

    # Pacing (evaluate before loitering so corridor reverse-walk wins)
    oscillating = heading_r < 0.55 and zigzag >= HIGH_ZIGZAG
    if oscillating and elongated and moving and low_walking:
        scores["pacing"] = 0.45 + 0.35 * zigzag + 0.2 * min(1.0, aspect / 4.0)

    # Loitering: compact footprint preferred (not elongated pacing corridor)
    if (
        dwell >= HIGH_DWELL_SECONDS
        and straightness < 0.5
        and low_walking
        and stop_fraction < 0.95
        and not (elongated and zigzag >= HIGH_ZIGZAG)
    ):
        scores["loitering"] = (
            0.35
            + 0.25 * min(1.0, dwell / (HIGH_DWELL_SECONDS * 2))
            + 0.25 * (1.0 - straightness)
            + 0.15 * (1.0 - heading_r)
        )

    # Erratic: prefer high speed + disordered heading. Do not steal
    # loitering (slow + long dwell) or pacing (zigzag corridor) cases.
    if heading_r < 0.5 and high_speed and zigzag < HIGH_ZIGZAG:
        scores["erratic"] = (
            0.45
            + 0.3 * (1.0 - heading_r)
            + 0.25 * min(1.0, mean_turn / (HIGH_TURN_RATE_RAD * 2))
        )
    elif (
        heading_r < 0.45
        and mean_turn >= HIGH_TURN_RATE_RAD
        and not low_walking
        and zigzag < HIGH_ZIGZAG
        and dwell < HIGH_DWELL_SECONDS
    ):
        scores["erratic"] = (
            0.35
            + 0.35 * (1.0 - heading_r)
            + 0.3 * min(1.0, mean_turn / (HIGH_TURN_RATE_RAD * 2))
        )

    if max(scores.values()) <= 0.0:
        scores["unknown"] = 0.5
    return scores


def _pick_class(scores: Dict[str, float]) -> Tuple[str, float]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_cls, best = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    if best <= 0.0:
        return "unknown", 0.0
    # Priority tie-break when scores are equal: follow plan order after unknown check.
    priority = [
        "stationary",
        "directed_transit",
        "pacing",
        "loitering",
        "erratic",
        "unknown",
    ]
    tied = [cls for cls, score in ordered if abs(score - best) < 1e-9]
    for cls in priority:
        if cls in tied:
            best_cls = cls
            break
    margin = best - second
    confidence = max(0.0, min(1.0, margin / max(best, 1e-6)))
    # Boost confidence when winner clearly matches a strong rule.
    confidence = round(max(confidence, min(1.0, best * 0.5)), 4)
    return best_cls, confidence


def classify_instant_motion(
    *,
    route_points: Optional[Sequence[Dict[str, Any]]] = None,
    average_speed_mps: Optional[float] = None,
    movement_statistics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Classify Instant person motion from route + speed.

    Returns motion_class, motion_confidence, motion_features, route_caricature.
    """
    points = [p for p in (route_points or []) if isinstance(p, dict)]
    features = compute_motion_features(
        points,
        average_speed_mps=average_speed_mps,
        movement_statistics=movement_statistics,
    )
    caricature = build_route_caricature(points)
    features["zigzag_score"] = max(
        float(caricature.get("zigzag_score") or 0.0),
        float(features.get("heading_reversal") or 0.0),
    )

    scores = _score_rules(features, caricature)
    motion_class, confidence = _pick_class(scores)

    # Compact features for API / UI.
    compact_features = {
        "straightness": features.get("straightness"),
        "heading_R": features.get("heading_R"),
        "stop_fraction": features.get("stop_fraction"),
        "mean_speed_mps": features.get("mean_speed_mps"),
        "zigzag_score": features.get("zigzag_score"),
        "dwell_seconds": features.get("dwell_seconds"),
        "point_count": features.get("point_count"),
    }

    return {
        "motion_class": motion_class,
        "motion_confidence": confidence,
        "motion_features": compact_features,
        "route_caricature": caricature,
    }
