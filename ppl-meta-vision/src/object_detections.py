"""Object detection persistence helpers (body / Phase C + pose keypoints)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def ensure_object_detections_table(connection) -> None:
    """Idempotent CREATE for object_detections (Postgres)."""
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS object_detections (
                id TEXT PRIMARY KEY,
                media_id TEXT,
                session_uuid TEXT,
                frame_number INTEGER,
                timestamp REAL,
                bbox_x1 INTEGER NOT NULL,
                bbox_y1 INTEGER NOT NULL,
                bbox_x2 INTEGER NOT NULL,
                bbox_y2 INTEGER NOT NULL,
                confidence REAL NOT NULL,
                class_id INTEGER,
                class_label TEXT,
                capability TEXT NOT NULL DEFAULT 'body_detection',
                method TEXT,
                model_id VARCHAR(128),
                model_version VARCHAR(64),
                recipe_id VARCHAR(128),
                runtime VARCHAR(64),
                confidence_threshold REAL,
                path VARCHAR(32),
                serving BOOLEAN DEFAULT TRUE,
                keypoints_json TEXT,
                keypoint_score REAL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        for stmt in (
            "ALTER TABLE object_detections ADD COLUMN IF NOT EXISTS keypoints_json TEXT",
            "ALTER TABLE object_detections ADD COLUMN IF NOT EXISTS keypoint_score REAL",
            "CREATE INDEX IF NOT EXISTS idx_object_detections_media ON object_detections (media_id)",
            "CREATE INDEX IF NOT EXISTS idx_object_detections_session ON object_detections (session_uuid)",
            "CREATE INDEX IF NOT EXISTS idx_object_detections_capability ON object_detections (capability)",
            "CREATE INDEX IF NOT EXISTS idx_object_detections_model ON object_detections (model_id, model_version)",
            "CREATE INDEX IF NOT EXISTS idx_object_detections_session_frame ON object_detections (session_uuid, frame_number)",
        ):
            try:
                cursor.execute(stmt)
            except Exception:
                pass
        connection.commit()
        cursor.close()
    except Exception as exc:
        logger.warning("ensure_object_detections_table failed: %s", exc)


def _keypoints_payload(detection: Dict[str, Any]) -> tuple[Optional[str], Optional[float]]:
    kpts = detection.get("keypoints")
    if not kpts:
        return None, detection.get("keypoint_score")
    try:
        raw = json.dumps(kpts)
    except (TypeError, ValueError):
        return None, None
    visibles = [k for k in kpts if isinstance(k, dict) and k.get("visible")]
    score = detection.get("keypoint_score")
    if score is None and kpts:
        confs = [float(k.get("confidence") or 0) for k in kpts if isinstance(k, dict)]
        score = (sum(confs) / len(confs)) if confs else None
    if visibles is not None and score is None:
        score = len(visibles) / max(1, len(kpts))
    return raw, float(score) if score is not None else None


def store_object_detection(connection, detection: Dict[str, Any]) -> bool:
    if connection is None:
        return False
    try:
        bbox = detection.get("bbox") or [0, 0, 0, 0]
        if len(bbox) < 4:
            return False
        det_id = detection.get("id") or str(uuid.uuid4())
        kpts_json, kpt_score = _keypoints_payload(detection)
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO object_detections (
                id, media_id, session_uuid, frame_number, timestamp,
                bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence,
                class_id, class_label, capability, method,
                model_id, model_version, recipe_id, runtime,
                confidence_threshold, path, serving,
                keypoints_json, keypoint_score
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            """,
            (
                det_id,
                detection.get("media_id"),
                detection.get("session_uuid"),
                detection.get("frame_number"),
                detection.get("timestamp"),
                int(bbox[0]),
                int(bbox[1]),
                int(bbox[2]),
                int(bbox[3]),
                float(detection.get("confidence") or 0.0),
                detection.get("class_id"),
                detection.get("class_label"),
                detection.get("capability") or "body_detection",
                detection.get("method") or "onnx",
                detection.get("model_id"),
                detection.get("model_version"),
                detection.get("recipe_id"),
                detection.get("runtime") or "onnx",
                detection.get("confidence_threshold"),
                detection.get("path"),
                detection.get("serving", True),
                kpts_json,
                kpt_score,
            ),
        )
        connection.commit()
        cursor.close()
        return True
    except Exception as exc:
        logger.warning("store_object_detection failed: %s", exc)
        try:
            connection.rollback()
        except Exception:
            pass
        return False


def list_object_detections(
    connection,
    *,
    session_uuid: Optional[str] = None,
    media_id: Optional[str] = None,
    capability: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if connection is None:
        return []
    try:
        cursor = connection.cursor()
        clauses = []
        params: list[Any] = []
        if session_uuid:
            clauses.append("session_uuid = %s")
            params.append(session_uuid)
        if media_id:
            clauses.append("media_id = %s")
            params.append(media_id)
        if capability:
            clauses.append("capability = %s")
            params.append(capability)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        cursor.execute(
            f"""
            SELECT id, media_id, session_uuid, frame_number, timestamp,
                   bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence,
                   class_id, class_label, capability, method,
                   model_id, model_version, recipe_id, runtime,
                   confidence_threshold, path, serving, created_at,
                   keypoints_json, keypoint_score
            FROM object_detections
            {where}
            ORDER BY COALESCE(frame_number, 0) ASC, created_at DESC
            LIMIT 5000
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        cursor.close()
        out = []
        for row in rows:
            kpts = None
            if len(row) > 22 and row[22]:
                try:
                    kpts = json.loads(row[22])
                except (TypeError, ValueError, json.JSONDecodeError):
                    kpts = None
            out.append(
                {
                    "id": row[0],
                    "media_id": row[1],
                    "session_uuid": row[2],
                    "frame_number": row[3],
                    "timestamp": row[4],
                    "bbox": [row[5], row[6], row[7], row[8]],
                    "confidence": row[9],
                    "class_id": row[10],
                    "class_label": row[11],
                    "capability": row[12],
                    "method": row[13],
                    "model_id": row[14],
                    "model_version": row[15],
                    "recipe_id": row[16],
                    "runtime": row[17],
                    "confidence_threshold": row[18],
                    "path": row[19],
                    "serving": row[20],
                    "created_at": row[21].isoformat() if row[21] else None,
                    "keypoints": kpts,
                    "keypoint_score": row[23] if len(row) > 23 else None,
                }
            )
        return out
    except Exception as exc:
        logger.warning("list_object_detections failed: %s", exc)
        return []


def bodies_by_frame(
    connection,
    *,
    media_id: Optional[str] = None,
    session_uuid: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group body detections by frame_number for replay overlays."""
    items = list_object_detections(
        connection,
        media_id=media_id,
        session_uuid=session_uuid,
        capability="body_detection",
    )
    by_frame: Dict[str, List[Dict[str, Any]]] = {}
    for det in items:
        key = str(det.get("frame_number") if det.get("frame_number") is not None else 0)
        by_frame.setdefault(key, []).append(det)
    return by_frame
