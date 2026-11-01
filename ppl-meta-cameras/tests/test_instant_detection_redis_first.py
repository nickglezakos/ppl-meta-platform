"""Unit tests for Redis-first Instant Detection helpers."""

from src.services.instant_detection_flush import (
    collect_faces_for_y_regroup,
    flush_buffer_key,
)


def test_flush_buffer_key():
    assert flush_buffer_key("cam-1") == "instant_detection_flush_buffer:cam-1"


def test_attach_movement_tracking_copies_speed_from_cycle_person():
    from src.services.instant_detection_flush import (
        attach_movement_tracking_to_instant_mvrs,
    )

    mvrs = [
        {
            "instant_mvr_uuid": "m1",
            "person_object_uuid": "p1",
            "bbox": [10, 20, 30, 40],
        }
    ]
    cycles = [
        {
            "cycle_id": "c1",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "person_objects": [
                {
                    "person_object_uuid": "p1",
                    "speed_mps": 1.0,
                    "gait_band": "walking",
                    "faces": [
                        {
                            "bbox": [10, 20, 30, 40],
                            "confidence": 0.9,
                            "frame_number": 0,
                            "timestamp": 1700000000.0,
                        },
                        {
                            "bbox": [14, 24, 34, 44],
                            "confidence": 0.8,
                            "frame_number": 1,
                            "timestamp": 1700000000.5,
                        },
                    ],
                }
            ],
        },
        {
            "cycle_id": "c2",
            "timestamp": "2024-01-01T00:00:05+00:00",
            "person_objects": [
                {
                    "person_object_uuid": "p1",
                    "speed_mps": 2.5,
                    "gait_band": "light_running",
                    "faces": [
                        {
                            "bbox": [20, 30, 40, 50],
                            "confidence": 0.9,
                            "frame_number": 2,
                            "timestamp": 1700000005.0,
                        },
                    ],
                }
            ],
        },
    ]
    attach_movement_tracking_to_instant_mvrs(mvrs, [], cycles=cycles)
    assert mvrs[0]["speed_mps"] == 1.75  # mean of positive cycle samples
    assert mvrs[0]["gait_band"] == "light_running"
    assert len(mvrs[0]["speed_samples"]) == 2
    assert mvrs[0]["speed_samples"][0]["speed_mps"] == 1.0
    assert mvrs[0]["speed_samples"][1]["speed_mps"] == 2.5
    stats = mvrs[0]["movement_tracking"]["movement_statistics"]
    assert stats["average_speed_mps"] == 1.75
    assert stats["gait_band"] == "light_running"
    # Route points should carry nearest cycle speed_mps for Motion charts.
    assert any(
        (pt.get("speed_mps") or 0) > 0 for pt in mvrs[0]["route_points"]
    )


def test_attach_movement_tracking_ignores_zero_speeds_in_average():
    from src.services.instant_detection_flush import (
        attach_movement_tracking_to_instant_mvrs,
    )

    mvrs = [
        {
            "instant_mvr_uuid": "m1",
            "person_object_uuid": "p1",
            "bbox": [10, 20, 30, 40],
        }
    ]
    cycles = [
        {
            "cycle_id": "c0",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "person_objects": [
                {
                    "person_object_uuid": "p1",
                    "speed_mps": 0.0,
                    "gait_band": None,
                    "faces": [{"bbox": [10, 20, 30, 40], "timestamp": 1.0}],
                }
            ],
        },
        {
            "cycle_id": "c1",
            "timestamp": "2024-01-01T00:00:05+00:00",
            "person_objects": [
                {
                    "person_object_uuid": "p1",
                    "speed_mps": 2.0,
                    "gait_band": "light_running",
                    "faces": [
                        {"bbox": [10, 20, 30, 40], "timestamp": 5.0},
                        {"bbox": [20, 30, 40, 50], "timestamp": 5.5},
                    ],
                }
            ],
        },
    ]
    attach_movement_tracking_to_instant_mvrs(mvrs, [], cycles=cycles)
    assert mvrs[0]["speed_mps"] == 2.0
    assert len(mvrs[0]["speed_samples"]) == 2
    assert mvrs[0]["speed_samples"][0]["speed_mps"] == 0.0
    assert mvrs[0]["movement_tracking"]["movement_statistics"]["average_speed_mps"] == 2.0


def test_generate_movement_tracking_from_faces():
    from src.services.instant_detection_flush import (
        attach_movement_tracking_to_person_groups,
        generate_movement_tracking,
    )

    faces = [
        {
            "bbox": [10, 20, 30, 40],
            "confidence": 0.9,
            "frame_number": 0,
            "timestamp": 1700000000.0,
        },
        {
            "bbox": [12, 22, 32, 42],
            "confidence": 0.8,
            "frame_number": 1,
            "timestamp": 1700000000.5,
        },
        {
            "bbox": [20, 30, 40, 50],
            "confidence": 0.7,
            "frame_number": 2,
            "timestamp": 1700000001.0,
        },
    ]
    tracking = generate_movement_tracking(faces)
    assert tracking["movement_statistics"]["total_route_points"] == 3
    assert tracking["average_route_velocity"] > 0
    assert len(tracking["route_points"]) == 3
    assert tracking["route_points"][0]["center_x"] == 20.0

    groups = [{"faces": faces, "person_object_uuid": "p1"}]
    attach_movement_tracking_to_person_groups(groups)
    assert groups[0]["movement_tracking"]["route_points"]
    assert groups[0]["average_route_velocity"] > 0


def test_embed_endpoint_exists_in_ml_module():
    # Importability smoke check for cameras-side expectations
    from src.services import instant_detection_flush as flush_mod

    assert hasattr(flush_mod, "run_y_window_flush")
    assert hasattr(flush_mod, "push_cycle_to_flush_buffer")
    assert hasattr(flush_mod, "enqueue_y_window_flush")
    assert hasattr(flush_mod, "collect_faces_for_y_regroup")


def test_person_groups_fallback_from_super_individuals():
    from src.services.instant_detection_flush import _person_groups_from_instant_mvrs

    mvrs = [
        {"instant_mvr_uuid": "a", "face_embedding": [0.1]},
        {"instant_mvr_uuid": "b", "face_embedding": [0.2]},
    ]
    merge = {"super_individuals": ["a"], "merge_groups": []}
    groups = _person_groups_from_instant_mvrs(mvrs, merge)
    assert len(groups) == 1
    assert groups[0]["person_object_uuid"] == "a"


def test_collect_faces_for_y_regroup_remaps_frames_and_timestamps():
    """Cycles reuse frame 0..2; Y-flush must expand them or contamination drops people."""
    cycles = [
        {
            "cycle_id": "c0",
            "timestamp": "2026-10-29T13:12:21.000Z",
            "face_detections": [
                # Relative in-cycle offsets must become absolute via cycle timestamp.
                {"id": "f0", "frame_index": 0, "bbox": [1, 2, 3, 4], "timestamp": 0.0},
                {"id": "f1", "frame_index": 1, "bbox": [1, 2, 3, 4], "timestamp": 0.5},
                {"id": "f2", "frame_index": 2, "bbox": [1, 2, 3, 4], "timestamp": 1.0},
            ],
        },
        {
            "cycle_id": "c1",
            "timestamp": "2026-10-29T13:12:29.000Z",
            "face_detections": [
                {"id": "f3", "frame_index": 0, "bbox": [5, 6, 7, 8], "timestamp": 0.0},
                {"id": "f4", "frame_index": 1, "bbox": [5, 6, 7, 8], "timestamp": 0.5},
                {"id": "f5", "frame_index": 2, "bbox": [5, 6, 7, 8], "timestamp": 1.0},
            ],
        },
    ]
    faces = collect_faces_for_y_regroup(cycles, frames_per_cycle=3)
    assert [f["frame_number"] for f in faces] == [0, 1, 2, 3, 4, 5]
    assert [f["frame_index"] for f in faces] == [0, 1, 2, 3, 4, 5]
    # Wall-clock timestamps must be epoch floats spanning the cycles.
    assert isinstance(faces[0]["timestamp"], float)
    assert isinstance(faces[-1]["timestamp"], float)
    assert faces[0]["timestamp"] >= 1_000_000_000.0
    assert faces[1]["timestamp"] - faces[0]["timestamp"] == 0.5
    assert faces[-1]["timestamp"] - faces[0]["timestamp"] >= 7.0
    assert faces[0]["bbox_x1"] == 1
    assert faces[3]["bbox_x1"] == 5


def test_collect_faces_preserves_absolute_face_source_timestamps():
    abs0 = 1_764_000_000.0
    abs1 = abs0 + 8.25
    cycles = [
        {
            "cycle_id": "c0",
            "timestamp": "2026-10-29T13:12:21.000Z",
            "face_detections": [
                {"id": "f0", "frame_index": 0, "bbox": [1, 2, 3, 4], "timestamp": abs0},
            ],
        },
        {
            "cycle_id": "c1",
            "timestamp": "2026-10-29T13:12:29.000Z",
            "face_detections": [
                {"id": "f1", "frame_index": 0, "bbox": [5, 6, 7, 8], "timestamp": abs1},
            ],
        },
    ]
    faces = collect_faces_for_y_regroup(cycles, frames_per_cycle=3)
    assert faces[0]["timestamp"] == abs0
    assert faces[1]["timestamp"] == abs1
