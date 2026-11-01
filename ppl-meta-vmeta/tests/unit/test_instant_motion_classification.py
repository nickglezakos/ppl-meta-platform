"""Unit tests for Instant Detection motion classification."""

from src.services.instant_motion_classification import (
    MAX_CARICATURE_KEYPOINTS,
    build_route_caricature,
    classify_instant_motion,
)


def _point(x: float, y: float, t: float, vx: float = 0.0, vy: float = 0.0) -> dict:
    mag = (vx**2 + vy**2) ** 0.5
    return {
        "center_x": x,
        "center_y": y,
        "timestamp": t,
        "velocity_x": vx,
        "velocity_y": vy,
        "velocity_magnitude": mag,
    }


def test_sparse_points_unknown():
    result = classify_instant_motion(
        route_points=[_point(0, 0, 0), _point(10, 0, 1)],
        average_speed_mps=1.5,
    )
    assert result["motion_class"] == "unknown"
    assert result["route_caricature"]["keypoints"]


def test_straight_path_directed_transit():
    # Long straight horizontal path at walking+ speed.
    points = [
        _point(0 + i * 40, 100, float(i), vx=40.0, vy=0.0) for i in range(8)
    ]
    result = classify_instant_motion(
        route_points=points,
        average_speed_mps=1.6,
        movement_statistics={"time_in_frame_seconds": 7.0},
    )
    assert result["motion_class"] == "directed_transit"
    assert result["motion_features"]["straightness"] >= 0.75
    assert result["motion_features"]["heading_R"] >= 0.7


def test_compact_winding_loitering():
    # Slow wandering in a small area with long dwell.
    points = [
        _point(100, 100, 0.0),
        _point(110, 105, 2.0, vx=5, vy=2.5),
        _point(105, 115, 4.0, vx=-2.5, vy=5),
        _point(95, 110, 6.0, vx=-5, vy=-2.5),
        _point(100, 100, 8.0, vx=2.5, vy=-5),
        _point(108, 102, 10.0, vx=4, vy=1),
        _point(102, 108, 12.0, vx=-3, vy=3),
        _point(98, 104, 14.0, vx=-2, vy=-2),
    ]
    result = classify_instant_motion(
        route_points=points,
        average_speed_mps=0.6,
        movement_statistics={"time_in_frame_seconds": 14.0},
    )
    assert result["motion_class"] == "loitering"


def test_back_and_forth_pacing():
    # Elongated corridor with reversing direction.
    points = [
        _point(0, 50, 0.0, vx=30, vy=0),
        _point(80, 50, 1.0, vx=30, vy=0),
        _point(160, 50, 2.0, vx=30, vy=0),
        _point(80, 50, 3.0, vx=-30, vy=0),
        _point(0, 50, 4.0, vx=-30, vy=0),
        _point(80, 50, 5.0, vx=30, vy=0),
        _point(160, 50, 6.0, vx=30, vy=0),
        _point(80, 52, 7.0, vx=-30, vy=1),
        _point(0, 50, 8.0, vx=-30, vy=-1),
    ]
    result = classify_instant_motion(
        route_points=points,
        average_speed_mps=1.0,
        movement_statistics={"time_in_frame_seconds": 8.0},
    )
    assert result["motion_class"] == "pacing"
    assert result["route_caricature"]["zigzag_score"] >= 0.0


def test_stationary_almost_no_motion():
    points = [
        _point(50, 50, 0.0),
        _point(51, 50, 1.0, vx=1, vy=0),
        _point(50, 51, 2.0, vx=-1, vy=1),
        _point(50, 50, 3.0, vx=0, vy=-1),
        _point(50.5, 50, 4.0, vx=0.5, vy=0),
    ]
    result = classify_instant_motion(
        route_points=points,
        average_speed_mps=0.05,
        movement_statistics={"time_in_frame_seconds": 4.0},
    )
    assert result["motion_class"] == "stationary"


def test_caricature_bounds():
    points = [
        _point(float(i * 10), float((i % 3) * 5), float(i), vx=10, vy=1)
        for i in range(20)
    ]
    caricature = build_route_caricature(points)
    assert 2 <= len(caricature["keypoints"]) <= MAX_CARICATURE_KEYPOINTS
    for kp in caricature["keypoints"]:
        assert 0.0 <= kp["x_norm"] <= 1.0 + 1e-6
        assert 0.0 <= kp["y_norm"] <= 1.0 + 1e-6
        assert 0.0 <= kp["t_norm"] <= 1.0 + 1e-6
    assert "chord_vector" in caricature
    assert "turn_signature" in caricature
    assert "extent_bbox" in caricature


def test_classify_includes_expected_keys():
    points = [_point(0, 0, 0), _point(20, 0, 1, vx=20), _point(40, 0, 2, vx=20)]
    result = classify_instant_motion(
        route_points=points,
        average_speed_mps=1.4,
    )
    assert set(result.keys()) >= {
        "motion_class",
        "motion_confidence",
        "motion_features",
        "route_caricature",
    }
    assert "straightness" in result["motion_features"]
    assert "heading_R" in result["motion_features"]
