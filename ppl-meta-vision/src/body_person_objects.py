"""Body person objects: within-session tracking from object_detections."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def ensure_body_person_tables(connection) -> None:
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS body_person_objects (
                body_person_id TEXT PRIMARY KEY,
                session_uuid TEXT NOT NULL,
                media_id TEXT,
                track_id INTEGER,
                detection_count INTEGER DEFAULT 0,
                average_bbox_x1 REAL,
                average_bbox_y1 REAL,
                average_bbox_x2 REAL,
                average_bbox_y2 REAL,
                quality_score REAL,
                best_detection_id TEXT,
                posture TEXT,
                posture_confidence REAL,
                height_px REAL,
                height_relative REAL,
                height_m REAL,
                dominant_colors TEXT,
                fallen TEXT DEFAULT 'unknown',
                fallen_confidence REAL DEFAULT 0,
                first_frame INTEGER,
                last_frame INTEGER,
                bbox_trajectory TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS body_detection_mappings (
                id TEXT PRIMARY KEY,
                body_person_id TEXT NOT NULL REFERENCES body_person_objects(body_person_id) ON DELETE CASCADE,
                object_detection_id TEXT NOT NULL,
                frame_number INTEGER,
                match_type TEXT,
                iou REAL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_body_po_session ON body_person_objects(session_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_body_po_media ON body_person_objects(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_body_map_person ON body_detection_mappings(body_person_id)",
            "CREATE INDEX IF NOT EXISTS idx_body_map_det ON body_detection_mappings(object_detection_id)",
        ):
            try:
                cursor.execute(stmt)
            except Exception:
                pass
        connection.commit()
        cursor.close()
    except Exception as exc:
        logger.warning("ensure_body_person_tables failed: %s", exc)


def _iou(a: List[float], b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


def _center(bbox: List[float]) -> Tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def group_detections_into_body_persons(
    detections: List[Dict[str, Any]],
    *,
    session_uuid: str,
    media_id: Optional[str] = None,
    iou_threshold: float = 0.3,
    max_frame_gap: int = 45,
) -> List[Dict[str, Any]]:
    """
    Greedy within-video IoU tracking across frames.
    Returns body person dicts with mappings (memory; caller may persist).
    """
    # Sort by frame then confidence
    ordered = sorted(
        detections,
        key=lambda d: (
            int(d.get("frame_number") or 0),
            -float(d.get("confidence") or 0),
        ),
    )
    tracks: List[Dict[str, Any]] = []
    next_track = 1

    for det in ordered:
        bbox = det.get("bbox") or [0, 0, 0, 0]
        if len(bbox) < 4:
            continue
        frame = int(det.get("frame_number") or 0)
        best_idx = -1
        best_iou = 0.0
        for i, track in enumerate(tracks):
            last_frame = int(track.get("last_frame") or 0)
            if frame - last_frame > max_frame_gap:
                continue
            if frame < last_frame:
                continue
            iou = _iou(bbox, track["last_bbox"])
            if iou > best_iou:
                best_iou = iou
                best_idx = i
        if best_idx >= 0 and best_iou >= iou_threshold:
            track = tracks[best_idx]
            track["detections"].append(det)
            track["last_bbox"] = bbox
            track["last_frame"] = frame
            track["mappings"].append(
                {
                    "object_detection_id": det.get("id"),
                    "frame_number": frame,
                    "match_type": "iou",
                    "iou": best_iou,
                }
            )
        else:
            tracks.append(
                {
                    "track_id": next_track,
                    "detections": [det],
                    "last_bbox": bbox,
                    "first_frame": frame,
                    "last_frame": frame,
                    "mappings": [
                        {
                            "object_detection_id": det.get("id"),
                            "frame_number": frame,
                            "match_type": "seed",
                            "iou": 1.0,
                        }
                    ],
                }
            )
            next_track += 1

    persons: List[Dict[str, Any]] = []
    for track in tracks:
        dets = track["detections"]
        boxes = [d["bbox"] for d in dets if d.get("bbox")]
        avg = [0.0, 0.0, 0.0, 0.0]
        if boxes:
            for i in range(4):
                avg[i] = sum(float(b[i]) for b in boxes) / len(boxes)
        best = max(dets, key=lambda d: float(d.get("confidence") or 0))
        posture = best.get("posture") or "uncertain"
        posture_conf = float(best.get("posture_confidence") or 0)
        # Prefer most confident non-uncertain posture if available
        for d in dets:
            if d.get("posture") in ("upright", "horizontal"):
                if float(d.get("posture_confidence") or 0) >= posture_conf:
                    posture = d["posture"]
                    posture_conf = float(d.get("posture_confidence") or 0)
        height_vals = [float(d["height_px"]) for d in dets if d.get("height_px") is not None]
        height_px = (sum(height_vals) / len(height_vals)) if height_vals else None
        # Prefer colors from the highest-confidence detection that has them
        dominant_colors = None
        for d in sorted(
            dets, key=lambda x: float(x.get("confidence") or 0), reverse=True
        ):
            if d.get("dominant_colors"):
                dominant_colors = d.get("dominant_colors")
                break
        trajectory = [
            {
                "frame": d.get("frame_number"),
                "bbox": d.get("bbox"),
                "confidence": d.get("confidence"),
            }
            for d in dets
        ]
        persons.append(
            {
                "body_person_id": str(uuid.uuid4()),
                "session_uuid": session_uuid,
                "media_id": media_id,
                "track_id": track["track_id"],
                "detection_count": len(dets),
                "average_bbox": avg,
                "quality_score": float(best.get("confidence") or 0),
                "best_detection_id": best.get("id"),
                "posture": posture,
                "posture_confidence": posture_conf,
                "height_px": height_px,
                "height_relative": height_px,
                "height_m": None,
                "dominant_colors": dominant_colors,
                # PLACEHOLDER: fallen classifier (see estimate_fallen)
                "fallen": "unknown",
                "fallen_confidence": 0.0,
                "first_frame": track["first_frame"],
                "last_frame": track["last_frame"],
                "bbox_trajectory": trajectory,
                "mappings": track["mappings"],
                "best_bbox": best.get("bbox"),
                "keypoints": best.get("keypoints"),
            }
        )
    return persons


def persist_body_persons(connection, persons: List[Dict[str, Any]]) -> int:
    if connection is None or not persons:
        return 0
    import json

    ensure_body_person_tables(connection)
    stored = 0
    try:
        cursor = connection.cursor()
        for p in persons:
            pid = p.get("body_person_id") or str(uuid.uuid4())
            avg = p.get("average_bbox") or [None, None, None, None]
            cursor.execute(
                """
                INSERT INTO body_person_objects (
                    body_person_id, session_uuid, media_id, track_id, detection_count,
                    average_bbox_x1, average_bbox_y1, average_bbox_x2, average_bbox_y2,
                    quality_score, best_detection_id, posture, posture_confidence,
                    height_px, height_relative, height_m, dominant_colors,
                    fallen, fallen_confidence, first_frame, last_frame, bbox_trajectory
                ) VALUES (
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s,%s
                )
                ON CONFLICT (body_person_id) DO UPDATE SET
                    detection_count = EXCLUDED.detection_count,
                    posture = EXCLUDED.posture,
                    posture_confidence = EXCLUDED.posture_confidence,
                    height_px = EXCLUDED.height_px,
                    updated_at = NOW()
                """,
                (
                    pid,
                    p.get("session_uuid"),
                    p.get("media_id"),
                    p.get("track_id"),
                    p.get("detection_count"),
                    avg[0],
                    avg[1],
                    avg[2],
                    avg[3],
                    p.get("quality_score"),
                    p.get("best_detection_id"),
                    p.get("posture"),
                    p.get("posture_confidence"),
                    p.get("height_px"),
                    p.get("height_relative"),
                    p.get("height_m"),
                    json.dumps(p["dominant_colors"]) if p.get("dominant_colors") else None,
                    p.get("fallen") or "unknown",
                    p.get("fallen_confidence") or 0,
                    p.get("first_frame"),
                    p.get("last_frame"),
                    json.dumps(p.get("bbox_trajectory") or []),
                ),
            )
            for m in p.get("mappings") or []:
                cursor.execute(
                    """
                    INSERT INTO body_detection_mappings (
                        id, body_person_id, object_detection_id, frame_number, match_type, iou
                    ) VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        str(uuid.uuid4()),
                        pid,
                        m.get("object_detection_id"),
                        m.get("frame_number"),
                        m.get("match_type"),
                        m.get("iou"),
                    ),
                )
            stored += 1
        connection.commit()
        cursor.close()
    except Exception as exc:
        logger.warning("persist_body_persons failed: %s", exc)
        try:
            connection.rollback()
        except Exception:
            pass
        return 0
    return stored


def list_body_persons(
    connection,
    *,
    session_uuid: Optional[str] = None,
    media_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if connection is None:
        return []
    try:
        ensure_body_person_tables(connection)
        cursor = connection.cursor()
        clauses = []
        params: list[Any] = []
        if session_uuid:
            clauses.append("session_uuid = %s")
            params.append(session_uuid)
        if media_id:
            clauses.append("media_id = %s")
            params.append(media_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        cursor.execute(
            f"""
            SELECT body_person_id, session_uuid, media_id, track_id, detection_count,
                   average_bbox_x1, average_bbox_y1, average_bbox_x2, average_bbox_y2,
                   quality_score, best_detection_id, posture, posture_confidence,
                   height_px, height_relative, height_m, dominant_colors,
                   fallen, fallen_confidence, first_frame, last_frame, bbox_trajectory,
                   created_at
            FROM body_person_objects
            {where}
            ORDER BY track_id ASC NULLS LAST, created_at ASC
            LIMIT 2000
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        cursor.close()
        import json

        out = []
        for row in rows:
            traj = None
            if row[21]:
                try:
                    traj = json.loads(row[21])
                except Exception:
                    traj = None
            colors = None
            if row[16]:
                try:
                    colors = json.loads(row[16])
                except Exception:
                    colors = None
            out.append(
                {
                    "body_person_id": row[0],
                    "session_uuid": row[1],
                    "media_id": row[2],
                    "track_id": row[3],
                    "detection_count": row[4],
                    "average_bbox": [row[5], row[6], row[7], row[8]],
                    "quality_score": row[9],
                    "best_detection_id": row[10],
                    "posture": row[11],
                    "posture_confidence": row[12],
                    "height_px": row[13],
                    "height_relative": row[14],
                    "height_m": row[15],
                    "dominant_colors": colors,
                    "fallen": row[17],
                    "fallen_confidence": row[18],
                    "first_frame": row[19],
                    "last_frame": row[20],
                    "bbox_trajectory": traj,
                    "created_at": row[22].isoformat() if row[22] else None,
                }
            )
        return out
    except Exception as exc:
        logger.warning("list_body_persons failed: %s", exc)
        return []
