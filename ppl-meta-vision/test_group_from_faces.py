"""Tests for memory-only group-from-faces service."""

import asyncio
import uuid

from person_objects.group_from_faces import group_faces_in_memory, normalize_face_record


def _sample_faces():
    return [
        {
            "face_id": str(uuid.uuid4()),
            "frame_index": 0,
            "bbox": [100, 100, 150, 150],
            "confidence": 0.9,
            "timestamp": 0.0,
        },
        {
            "face_id": str(uuid.uuid4()),
            "frame_index": 1,
            "bbox": [105, 105, 155, 155],
            "confidence": 0.88,
            "timestamp": 0.5,
        },
        {
            "face_id": str(uuid.uuid4()),
            "frame_index": 0,
            "bbox": [400, 200, 460, 260],
            "confidence": 0.92,
            "timestamp": 0.0,
        },
    ]


def test_normalize_face_record_maps_instant_shape():
    face = _sample_faces()[0]
    normalized = normalize_face_record(face)

    assert normalized["frame_number"] == 0
    assert normalized["bbox_x1"] == 100
    assert normalized["bbox_y2"] == 150
    assert normalized["confidence"] == 0.9
    # Relative in-cycle offsets must not be promoted to Unix epochs.
    assert "timestamp" not in normalized or normalized.get("timestamp", 0) >= 1_000_000_000.0


def test_normalize_face_record_preserves_absolute_source_timestamp():
    face = {
        "face_id": str(uuid.uuid4()),
        "frame_index": 0,
        "bbox": [10, 20, 30, 40],
        "confidence": 0.9,
        "timestamp": 1_764_000_123.5,
    }
    normalized = normalize_face_record(face)
    assert normalized["timestamp"] == 1_764_000_123.5


def test_normalize_face_record_null_bbox_fields_use_list():
    """Instant Detection flush payloads may include bbox_* keys set to null."""
    face = {
        "face_id": str(uuid.uuid4()),
        "frame_index": 0,
        "bbox": [491, 270, 763, 542],
        "bbox_x1": None,
        "bbox_y1": None,
        "bbox_x2": None,
        "bbox_y2": None,
        "confidence": 0.5,
    }
    normalized = normalize_face_record(face)
    assert normalized["bbox_x1"] == 491
    assert normalized["bbox_y1"] == 270
    assert normalized["bbox_x2"] == 763
    assert normalized["bbox_y2"] == 542


def test_group_faces_in_memory_returns_person_groups():
    faces = _sample_faces()
    correlation_id = str(uuid.uuid4())

    result = asyncio.run(
        group_faces_in_memory(
            face_detections=faces,
            correlation_id=correlation_id,
            consumer="instant_detection",
            tolerance_percent=20.0,
            enable_quality_analysis=True,
            enable_tier3_embedding=False,
        )
    )

    assert result["success"] is True
    assert result["persisted"] is False
    assert result["correlation_id"] == correlation_id
    assert result["summary"]["total_faces"] == 3
    assert result["summary"]["total_persons"] == 2
    assert len(result["person_groups"]) == 2

    for group in result["person_groups"]:
        assert group["person_object_uuid"]
        assert group["face_count"] >= 1
        assert group["faces"]
        assert group["best_face"] is not None
