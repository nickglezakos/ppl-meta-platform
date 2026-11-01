"""Unit tests for Face | Body | Both analytics merge."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))

from services.face_body_analytics_merge import (  # noqa: E402
    apply_detection_modality,
    merge_face_body_people,
    normalize_detection_modality,
    route_points_from_bbox_trajectory,
)


def _face(person_id: str, *, camera: str = "cam-1", flush_id: int = 1, bbox=None, ts0=1000.0, ts1=1002.0):
    bbox = bbox or [100.0, 100.0, 140.0, 160.0]
    return {
        "person_id": person_id,
        "camera_id": camera,
        "flush_log_id": flush_id,
        "gender": "male",
        "age": 30,
        "identity_modality": "face",
        "first_seen": "1970-01-01T00:16:40+00:00",
        "last_seen": "1970-01-01T00:16:42+00:00",
        "route_points": [
            {"timestamp": ts0, "center_x": 120.0, "center_y": 130.0, "bbox": bbox, "frame_number": 1},
            {"timestamp": ts1, "center_x": 125.0, "center_y": 132.0, "bbox": bbox, "frame_number": 2},
        ],
    }


def _body(person_id: str, *, camera: str = "cam-1", flush_id: int = 1, bbox=None, ts0=1000.5, ts1=1003.0):
    bbox = bbox or [90.0, 80.0, 160.0, 220.0]
    return {
        "person_id": person_id,
        "body_person_id": person_id,
        "mvr_people_body_uuid": person_id,
        "camera_id": camera,
        "flush_log_id": flush_id,
        "identity_modality": "body",
        "first_seen": "1970-01-01T00:16:40.500000+00:00",
        "last_seen": "1970-01-01T00:16:43+00:00",
        "route_points": [
            {"timestamp": ts0, "center_x": 125.0, "center_y": 150.0, "bbox": bbox, "frame_number": 1},
            {"timestamp": ts1, "center_x": 130.0, "center_y": 155.0, "bbox": bbox, "frame_number": 3},
        ],
    }


def test_normalize_detection_modality_defaults_to_face():
    assert normalize_detection_modality(None) == "face"
    assert normalize_detection_modality("FACE") == "face"
    assert normalize_detection_modality("body") == "body"
    assert normalize_detection_modality("both") == "both"
    assert normalize_detection_modality("nope") == "face"


def test_merge_overlapping_face_body_counts_as_one():
    faces = [_face("face-1")]
    bodies = [_body("body-1")]
    merged = merge_face_body_people(faces, bodies)
    assert len(merged) == 1
    assert merged[0]["identity_modality"] == "merged"
    assert merged[0]["gender"] == "male"
    assert merged[0]["linked_mvr_people_body_uuid"] == "body-1"
    assert len(merged[0]["route_points"]) >= 2


def test_merge_gap_over_threshold_keeps_two():
    faces = [_face("face-1", ts0=1000.0, ts1=1001.0)]
    faces[0]["first_seen"] = "1970-01-01T00:16:40+00:00"
    faces[0]["last_seen"] = "1970-01-01T00:16:41+00:00"
    bodies = [_body("body-1", ts0=1010.0, ts1=1012.0)]  # 9s gap > 3s
    bodies[0]["first_seen"] = "1970-01-01T00:16:50+00:00"
    bodies[0]["last_seen"] = "1970-01-01T00:16:52+00:00"
    merged = merge_face_body_people(faces, bodies)
    assert len(merged) == 2


def test_merge_spatial_miss_keeps_two():
    faces = [_face("face-1", bbox=[10.0, 10.0, 40.0, 50.0])]
    bodies = [_body("body-1", bbox=[800.0, 800.0, 900.0, 1000.0])]
    merged = merge_face_body_people(faces, bodies)
    assert len(merged) == 2


def test_apply_modality_face_body_both():
    faces = [_face("face-1"), _face("face-2", flush_id=2)]
    bodies = [_body("body-1")]
    assert len(apply_detection_modality(faces, bodies, "face")) == 2
    assert len(apply_detection_modality(faces, bodies, "body")) == 1
    both = apply_detection_modality(faces, bodies, "both")
    # face-1 merges with body-1; face-2 remains
    assert len(both) == 2
    modalities = {p["identity_modality"] for p in both}
    assert "merged" in modalities
    assert "face" in modalities


def test_route_points_from_bbox_trajectory_ordered():
    traj = [
        {"frame": 2, "bbox": [10, 10, 20, 40], "confidence": 0.9},
        {"frame": 0, "bbox": [12, 12, 22, 42], "confidence": 0.8},
        {"frame": 4, "bbox": [14, 14, 24, 44], "confidence": 0.7},
    ]
    points = route_points_from_bbox_trajectory(traj, frame_dt_sec=0.5)
    assert len(points) == 3
    assert points[0]["frame_number"] == 0 or points[0]["timestamp"] <= points[-1]["timestamp"]
    assert points[0]["sequence_number"] == 1
    assert points[-1]["sequence_number"] == 3


def test_face_demographics_preserved_on_merge():
    faces = [_face("face-1")]
    bodies = [_body("body-1")]
    merged = merge_face_body_people(faces, bodies)[0]
    assert merged["gender"] == "male"
    assert merged["age"] == 30
    # Route union should include body points
    assert any(
        abs(float(p["center_y"]) - 150.0) < 1e-6 for p in merged["route_points"]
    )


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
