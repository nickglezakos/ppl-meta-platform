"""API for body person objects (parallel to face person_objects)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from body_person_objects import (
    ensure_body_person_tables,
    group_detections_into_body_persons,
    list_body_persons,
    persist_body_persons,
)
from object_detections import list_object_detections

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/body-person-objects", tags=["body-person-objects"])


def _vision_connection():
    try:
        import main as vision_main

        db = getattr(vision_main, "vision_db", None)
        return getattr(db, "connection", None) if db else None
    except Exception:
        return None


class GroupFromDetectionsRequest(BaseModel):
    session_uuid: str
    media_id: Optional[str] = None
    detections: Optional[List[Dict[str, Any]]] = None
    persist: bool = True
    iou_threshold: float = Field(default=0.3, ge=0.05, le=0.95)


class StitchSegmentsRequest(BaseModel):
    """Same-camera continuous track continuation across a media cut."""

    camera_id: str
    media_id_a: str
    media_id_b: str
    session_uuid_a: Optional[str] = None
    session_uuid_b: Optional[str] = None
    t_end_a: float
    t_start_b: float
    max_time_gap_sec: float = 5.0
    min_iou: float = 0.25
    max_center_distance_px: float = 120.0


@router.post("/group-from-detections")
async def group_from_detections(body: GroupFromDetectionsRequest):
    conn = _vision_connection()
    detections = body.detections
    if not detections:
        detections = list_object_detections(
            conn,
            session_uuid=body.session_uuid,
            media_id=body.media_id,
            capability="body_detection",
        )
    if not detections:
        return {"success": True, "body_persons": [], "count": 0}

    persons = group_detections_into_body_persons(
        detections,
        session_uuid=body.session_uuid,
        media_id=body.media_id,
        iou_threshold=body.iou_threshold,
    )
    stored = 0
    if body.persist:
        stored = persist_body_persons(conn, persons)
    return {
        "success": True,
        "body_persons": persons,
        "count": len(persons),
        "stored": stored,
    }


@router.get("/sessions/{session_uuid}")
async def get_session_body_persons(session_uuid: str):
    conn = _vision_connection()
    ensure_body_person_tables(conn)
    items = list_body_persons(conn, session_uuid=session_uuid)
    return {"session_uuid": session_uuid, "body_persons": items, "count": len(items)}


@router.get("/media/{media_id}")
async def get_media_body_persons(media_id: str):
    conn = _vision_connection()
    ensure_body_person_tables(conn)
    items = list_body_persons(conn, media_id=media_id)
    return {"media_id": media_id, "body_persons": items, "count": len(items)}


@router.post("/stitch-segments")
async def stitch_segments(body: StitchSegmentsRequest):
    """
    Cross-segment identity ONLY when:
    - same camera_id
    - continuous time (|t_start_b - t_end_a| <= max_time_gap_sec)
    - nearest bbox / IoU between last frames of A and first frames of B
    - track continuation across a cut — NOT unrelated-video ReID
    """
    gap = abs(float(body.t_start_b) - float(body.t_end_a))
    if gap > body.max_time_gap_sec:
        return {
            "success": False,
            "stitched": [],
            "reason": "time_gap_exceeded",
            "gap_sec": gap,
        }

    conn = _vision_connection()
    persons_a = list_body_persons(
        conn, media_id=body.media_id_a, session_uuid=body.session_uuid_a
    )
    persons_b = list_body_persons(
        conn, media_id=body.media_id_b, session_uuid=body.session_uuid_b
    )
    if not persons_a or not persons_b:
        return {"success": True, "stitched": [], "reason": "missing_persons"}

    def _last_bbox(p: Dict[str, Any]):
        traj = p.get("bbox_trajectory") or []
        if traj:
            last = traj[-1]
            return last.get("bbox") or p.get("average_bbox")
        return p.get("average_bbox")

    def _first_bbox(p: Dict[str, Any]):
        traj = p.get("bbox_trajectory") or []
        if traj:
            first = traj[0]
            return first.get("bbox") or p.get("average_bbox")
        return p.get("average_bbox")

    def _iou(a, b):
        if not a or not b or len(a) < 4 or len(b) < 4:
            return 0.0
        ax1, ay1, ax2, ay2 = [float(x) for x in a[:4]]
        bx1, by1, bx2, by2 = [float(x) for x in b[:4]]
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        return float(inter / union) if union > 0 else 0.0

    def _center_dist(a, b):
        if not a or not b or len(a) < 4 or len(b) < 4:
            return 1e9
        acx = (float(a[0]) + float(a[2])) / 2
        acy = (float(a[1]) + float(a[3])) / 2
        bcx = (float(b[0]) + float(b[2])) / 2
        bcy = (float(b[1]) + float(b[3])) / 2
        return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5

    used_b = set()
    stitched = []
    for pa in persons_a:
        ba = _last_bbox(pa)
        best = None
        best_score = -1.0
        for pb in persons_b:
            if pb["body_person_id"] in used_b:
                continue
            bb = _first_bbox(pb)
            iou = _iou(ba, bb)
            dist = _center_dist(ba, bb)
            if iou < body.min_iou and dist > body.max_center_distance_px:
                continue
            score = iou * 2.0 - (dist / max(1.0, body.max_center_distance_px))
            if score > best_score:
                best_score = score
                best = (pb, iou, dist)
        if best:
            pb, iou, dist = best
            used_b.add(pb["body_person_id"])
            stitched.append(
                {
                    "camera_id": body.camera_id,
                    "body_person_id_a": pa["body_person_id"],
                    "body_person_id_b": pb["body_person_id"],
                    "iou": iou,
                    "center_distance_px": dist,
                    "time_gap_sec": gap,
                    "method": "same_camera_continuous_iou_stitch",
                }
            )
    return {
        "success": True,
        "stitched": stitched,
        "count": len(stitched),
        "guards": {
            "same_camera": True,
            "camera_id": body.camera_id,
            "max_time_gap_sec": body.max_time_gap_sec,
            "note": "Track continuation across a cut only; not unrelated-video ReID",
        },
    }
