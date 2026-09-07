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
