"""
Memory-only person grouping from in-memory face detections.

Used by instant detection and other ephemeral consumers that need the same
three-tier grouping engine as the bulk workflow without Vision DB writes.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .face_grouping_engine import VisionFaceGroupingEngine
from .quality_analyzer import PersonQualityAnalyzer

logger = logging.getLogger(__name__)


def _parse_created_at(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _to_xyxy_bbox(face: Dict[str, Any]) -> Tuple[int, int, int, int]:
    if all(key in face for key in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2")):
        return (
            int(face["bbox_x1"]),
            int(face["bbox_y1"]),
            int(face["bbox_x2"]),
            int(face["bbox_y2"]),
        )

    bbox = face.get("bbox") or [0, 0, 0, 0]
    if len(bbox) < 4:
        return (0, 0, 0, 0)

    x1, y1, x2_or_w, y2_or_h = [int(v) for v in bbox[:4]]
    if x2_or_w > x1 and y2_or_h > y1 and (x2_or_w - x1) < 5000 and (y2_or_h - y1) < 5000:
        return (x1, y1, x2_or_w, y2_or_h)

    return (x1, y1, x1 + x2_or_w, y1 + y2_or_h)


def normalize_face_record(
    face: Dict[str, Any],
    cycle_base_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Normalize caller face payloads into the grouping engine schema."""
    face_id = face.get("id") or face.get("face_id")
    if face_id is None:
        face_id = str(uuid.uuid4())

    frame_number = face.get("frame_number", face.get("frame_index", 0))
    x1, y1, x2, y2 = _to_xyxy_bbox(face)

    normalized: Dict[str, Any] = {
        "id": face_id,
        "frame_number": int(frame_number),
        "bbox_x1": x1,
        "bbox_y1": y1,
        "bbox_x2": x2,
        "bbox_y2": y2,
        "confidence": float(face.get("confidence", 0.0)),
        "method": face.get("method", "two_stage_haar_dlib"),
    }

    if face.get("embedding") is not None:
        normalized["embedding"] = face["embedding"]

    created_at = _parse_created_at(face.get("created_at"))
    if created_at is None and cycle_base_time is not None:
        offset_ms = int(float(face.get("timestamp", frame_number * 0.5)) * 1000)
        created_at = cycle_base_time + timedelta(milliseconds=offset_ms)
    if created_at is not None:
        normalized["created_at"] = created_at

    for optional_key in ("position_x", "position_y", "sharpness", "brightness"):
        if optional_key in face:
            normalized[optional_key] = face[optional_key]

    return normalized


def _face_payload_from_record(face: Dict[str, Any], match_type: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "id": str(face["id"]),
        "frame_number": int(face.get("frame_number", 0)),
        "bbox_x1": int(face["bbox_x1"]),
        "bbox_y1": int(face["bbox_y1"]),
        "bbox_x2": int(face["bbox_x2"]),
        "bbox_y2": int(face["bbox_y2"]),
        "confidence": float(face.get("confidence", 0.0)),
    }
    if face.get("embedding") is not None:
        payload["embedding"] = face["embedding"]
    created_at = face.get("created_at")
    if created_at is not None:
        if isinstance(created_at, datetime):
            payload["created_at"] = created_at.isoformat()
        else:
            payload["created_at"] = created_at
    if match_type:
        payload["match_type"] = match_type
    return payload


def _best_face_payload(best_face_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not best_face_data:
        return None

    face_record = best_face_data.get("face_record") or {}
    x1, y1, x2, y2 = _to_xyxy_bbox(face_record)
    return {
        "face_id": str(face_record.get("id", "")),
        "frame_number": int(face_record.get("frame_number", 0)),
        "bbox": [x1, y1, x2, y2],
        "confidence": float(face_record.get("confidence", 0.0)),
        "quality_score": float(best_face_data.get("quality_score", 0.0)),
    }


async def group_faces_in_memory(
    face_detections: List[Dict[str, Any]],
    correlation_id: str,
    consumer: str = "instant_detection",
    tolerance_percent: float = 20.0,
    enable_quality_analysis: bool = True,
    enable_tier3_embedding: bool = False,
    grouping_metadata: Optional[Dict[str, Any]] = None,
    cycle_base_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Run the three-tier grouping cascade without persisting workflow state.
    """
    started = time.perf_counter()
    grouping_run_id = str(uuid.uuid4())
    cycle_base_time = cycle_base_time or datetime.utcnow()

    normalized_faces = [
        normalize_face_record(face, cycle_base_time=cycle_base_time)
        for face in face_detections
    ]

    engine = VisionFaceGroupingEngine(
        embedding_extractor=None if not enable_tier3_embedding else None
    )
    grouping_results = await engine.apply_percentage_based_tracking(
        normalized_faces, tolerance_percent
    )

    best_quality_faces: Dict[str, Any] = {}
    if enable_quality_analysis and grouping_results["person_objects"]:
        analyzer = PersonQualityAnalyzer()
        quality_results = analyzer.select_best_face_per_person(
            grouping_results["person_objects"],
            normalized_faces,
            grouping_results["face_mappings"],
        )
        best_quality_faces = quality_results.get("best_faces", {})

    face_lookup = {str(face["id"]): face for face in normalized_faces}
    mapping_lookup: Dict[str, str] = {}
    person_uuid_by_track: Dict[str, str] = {}

    person_groups: List[Dict[str, Any]] = []
    for person in grouping_results["person_objects"]:
        person_id = person["person_id"]
        person_object_uuid = str(uuid.uuid4())
        person_uuid_by_track[person_id] = person_object_uuid

        person_face_ids = [
            str(mapping["face_detection_id"])
            for mapping in grouping_results["face_mappings"]
            if mapping["person_id"] == person_id
        ]
        for face_id in person_face_ids:
            mapping_lookup[face_id] = person_object_uuid

        group_faces: List[Dict[str, Any]] = []
        confidences: List[float] = []
        for face_id in person_face_ids:
            face_record = face_lookup.get(face_id)
            if not face_record:
                continue
            confidences.append(float(face_record.get("confidence", 0.0)))
            group_faces.append(_face_payload_from_record(face_record))

        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )

        velocity = person.get("velocity") or {"x": 0.0, "y": 0.0}
        frame_history = int(
            person.get("frame_history", person.get("samples", len(group_faces))) or 0
        )
        # Prefer live track state when available (authoritative after grouping).
        track_info = engine.active_tracks.get(person_id) or {}
        if track_info:
            velocity = track_info.get("velocity") or velocity
            frame_history = int(
                track_info.get("frame_history", frame_history) or frame_history
            )

        person_groups.append(
            {
                "person_id": person_id,
                "person_object_uuid": person_object_uuid,
                "face_count": person.get("face_count", len(group_faces)),
                "avg_confidence": round(avg_confidence, 4),
                "average_position": person.get("average_position", {"x": 0.0, "y": 0.0}),
                "faces": group_faces,
                "best_face": _best_face_payload(best_quality_faces.get(person_id)),
                "velocity": {
                    "x": float(velocity.get("x", 0.0)),
                    "y": float(velocity.get("y", 0.0)),
                },
                "frame_history": frame_history,
                "samples": frame_history,
            }
        )

    face_mappings: List[Dict[str, Any]] = []
    for mapping in grouping_results["face_mappings"]:
        face_id = str(mapping["face_detection_id"])
        face_mappings.append(
            {
                "face_id": face_id,
                "person_id": mapping["person_id"],
                "person_object_uuid": person_uuid_by_track.get(mapping["person_id"]),
                "frame_number": mapping["frame_number"],
                "match_type": mapping.get("match_type"),
                "match_distance": mapping.get("match_distance", 0.0),
            }
        )

    statistics = grouping_results.get("statistics", {})
    summary = {
        "total_faces": statistics.get("total_faces", len(normalized_faces)),
        "total_persons": statistics.get("total_persons", len(person_groups)),
        "frames_processed": statistics.get("frames_processed", 0),
        "grouping_algorithm": statistics.get("algorithm", "percentage_based_tracking"),
        "tolerance_percent": statistics.get("tolerance_percent", tolerance_percent),
        "tier1_position_matched": statistics.get("tier1_position_matched", 0),
        "tier2_velocity_rejected": statistics.get("tier2_velocity_rejected", 0),
        "tier3_embedding_rejected": statistics.get("tier3_embedding_rejected", 0),
    }

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Memory-only grouping complete for %s (%s): %d faces -> %d persons in %dms",
        consumer,
        correlation_id[:8],
        summary["total_faces"],
        summary["total_persons"],
        elapsed_ms,
    )

    return {
        "success": True,
        "grouping_run_id": grouping_run_id,
        "correlation_id": correlation_id,
        "consumer": consumer,
        "persisted": False,
        "summary": summary,
        "person_groups": person_groups,
        "face_mappings": face_mappings,
        "grouping_metadata": grouping_metadata or {},
        "processing_timestamp": datetime.utcnow().isoformat() + "Z",
        "processing_time_ms": elapsed_ms,
    }
