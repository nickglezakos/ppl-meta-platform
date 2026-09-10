"""License plate readings persistence (never faces / MVR people)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def ensure_plate_readings_table(connection) -> None:
    """Idempotent CREATE for plate_readings (Postgres)."""
    if connection is None:
        return
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS plate_readings (
                id TEXT PRIMARY KEY,
                media_id TEXT,
                session_uuid TEXT,
                frame_number INTEGER,
                timestamp DOUBLE PRECISION,
                vehicle_bbox_json TEXT,
                plate_bbox_json TEXT,
                plate_text TEXT,
                plate_confidence REAL,
                method TEXT,
                model_id TEXT,
                model_version TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
            )
            for stmt in (
                "CREATE INDEX IF NOT EXISTS idx_plate_readings_media ON plate_readings (media_id)",
                "CREATE INDEX IF NOT EXISTS idx_plate_readings_session ON plate_readings (session_uuid)",
                "CREATE INDEX IF NOT EXISTS idx_plate_readings_text ON plate_readings (plate_text)",
            ):
                cur.execute(stmt)
            connection.commit()
    except Exception as exc:
        logger.warning("ensure_plate_readings_table failed: %s", exc)
        try:
            connection.rollback()
        except Exception:
            pass


def store_plate_reading(connection, reading: Dict[str, Any]) -> bool:
    if connection is None:
        return False
    try:
        ensure_plate_readings_table(connection)
        rid = reading.get("id") or str(uuid.uuid4())
        vehicle_bbox = reading.get("vehicle_bbox")
        plate_bbox = reading.get("plate_bbox")
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO plate_readings (
                    id, media_id, session_uuid, frame_number, timestamp,
                    vehicle_bbox_json, plate_bbox_json, plate_text, plate_confidence,
                    method, model_id, model_version
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    rid,
                    reading.get("media_id"),
                    reading.get("session_uuid"),
                    reading.get("frame_number"),
                    reading.get("timestamp"),
                    json.dumps(vehicle_bbox) if vehicle_bbox is not None else None,
                    json.dumps(plate_bbox) if plate_bbox is not None else None,
                    reading.get("plate_text"),
                    reading.get("plate_confidence"),
                    reading.get("method") or "ocr",
                    reading.get("model_id"),
                    reading.get("model_version"),
                ),
            )
            connection.commit()
        return True
    except Exception as exc:
        logger.warning("store_plate_reading failed: %s", exc)
        try:
            connection.rollback()
        except Exception:
            pass
        return False
