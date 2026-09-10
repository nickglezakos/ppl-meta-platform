"""MVR People Body service — materialize from Vision body_person_objects (asyncpg)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


def estimate_fallen(*_args, **_kwargs) -> Dict[str, Any]:
    """
    PLACEHOLDER — not implemented in V1.

    Posture==horizontal is NOT certified fallen / life-safety.
    Future: temporal hip/shoulder velocity + pose classifier.
    """
    # TODO: implement fallen classifier for industrial/ship scenes
    return {"fallen": "unknown", "fallen_confidence": 0.0, "method": "placeholder"}


def estimate_dominant_colors(*_args, **_kwargs) -> Optional[list]:
    """
    PLACEHOLDER — dominant clothing colors within body bbox.

    Future: crop bbox → k-means / HSV histogram.
    """
    # TODO: dominant_colors = kmeans(crop(bbox))
    return None


async def ensure_mvr_people_body_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mvr_people_body (
            mvr_people_body_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            posture VARCHAR(32) DEFAULT 'uncertain',
            posture_confidence FLOAT DEFAULT 0.0,
            height_px FLOAT,
            height_relative FLOAT,
            height_m FLOAT,
            dominant_colors JSONB,
            fallen VARCHAR(16) DEFAULT 'unknown',
            fallen_confidence FLOAT DEFAULT 0.0,
            quality_score FLOAT DEFAULT 0.0,
            confidence_score FLOAT DEFAULT 0.0,
            featured_body_person_uuid UUID,
            featured_video_uuid UUID,
            source_media_uuid UUID,
            camera_id TEXT,
            created_by_session UUID,
            total_appearances INTEGER NOT NULL DEFAULT 0,
            total_videos INTEGER NOT NULL DEFAULT 0,
            first_seen TIMESTAMP WITH TIME ZONE,
            last_seen TIMESTAMP WITH TIME ZONE,
            bbox_trajectory JSONB DEFAULT '[]'::JSONB,
            is_isolated BOOLEAN DEFAULT TRUE,
            auto_created BOOLEAN DEFAULT TRUE,
            stitched_from_mvr_uuid UUID,
            previous_body_person_uuids JSONB DEFAULT '[]'::JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mvr_people_body_stitch_audit (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            camera_id TEXT NOT NULL,
            mvr_uuid_a UUID,
            mvr_uuid_b UUID,
            media_id_a UUID,
            media_id_b UUID,
            iou FLOAT,
            center_distance_px FLOAT,
            time_gap_sec FLOAT,
            reason TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
    )


async def materialize_from_body_persons(
    conn: asyncpg.Connection,
    body_persons: List[Dict[str, Any]],
    *,
    media_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    session_uuid: Optional[str] = None,
) -> Dict[str, Any]:
    await ensure_mvr_people_body_schema(conn)
    created = []
    now = datetime.now(timezone.utc)
    if media_id:
        try:
            media_uuid = uuid.UUID(str(media_id))
            await conn.execute(
                """
                DELETE FROM mvr_people_body
                WHERE source_media_uuid = $1 OR featured_video_uuid = $1
                """,
                media_uuid,
            )
        except (ValueError, TypeError):
            pass
    for person in body_persons:
        fallen_info = estimate_fallen(person)
        # Prefer colors computed in Vision; stub only if missing
        colors = person.get("dominant_colors")
        if not colors:
            colors = estimate_dominant_colors(person)
        mvr_uuid = uuid.uuid4()
        traj = person.get("bbox_trajectory") or []
        body_person_id = person.get("body_person_id")
        try:
            featured_bp = uuid.UUID(str(body_person_id)) if body_person_id else None
        except (ValueError, TypeError):
            featured_bp = None
        try:
            media_uuid = uuid.UUID(str(media_id)) if media_id else None
        except (ValueError, TypeError):
            media_uuid = None
        try:
            session_u = uuid.UUID(str(session_uuid)) if session_uuid else None
        except (ValueError, TypeError):
            session_u = None

        await conn.execute(
            """
            INSERT INTO mvr_people_body (
                mvr_people_body_uuid, posture, posture_confidence,
                height_px, height_relative, height_m, dominant_colors,
                fallen, fallen_confidence, quality_score, confidence_score,
                featured_body_person_uuid, featured_video_uuid, source_media_uuid,
                camera_id, created_by_session, total_appearances, total_videos,
                first_seen, last_seen, bbox_trajectory, is_isolated, auto_created,
                previous_body_person_uuids
            ) VALUES (
                $1,$2,$3,
                $4,$5,$6,$7::jsonb,
                $8,$9,$10,$11,
                $12,$13,$14,
                $15,$16,$17,$18,
                $19,$20,$21::jsonb,$22,$23,
                $24::jsonb
            )
            """,
            mvr_uuid,
            person.get("posture") or "uncertain",
            float(person.get("posture_confidence") or 0),
            person.get("height_px"),
            person.get("height_relative"),
            None,
            json.dumps(colors) if colors else None,
            fallen_info.get("fallen") or "unknown",
            float(fallen_info.get("fallen_confidence") or 0),
            float(person.get("quality_score") or 0),
            float(person.get("quality_score") or 0),
            featured_bp,
            media_uuid,
            media_uuid,
            camera_id,
            session_u,
            int(person.get("detection_count") or 1),
            1 if media_id else 0,
            now,
            now,
            json.dumps(traj),
            True,
            True,
            json.dumps([str(body_person_id)] if body_person_id else []),
        )
        created.append(
            {
                "mvr_people_body_uuid": str(mvr_uuid),
                "body_person_id": body_person_id,
                "posture": person.get("posture"),
                "height_px": person.get("height_px"),
            }
        )
    return {"success": True, "created": created, "count": len(created)}


def _normalize_dominant_colors(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return raw


async def list_for_media(conn: asyncpg.Connection, media_id: str) -> List[Dict[str, Any]]:
    await ensure_mvr_people_body_schema(conn)
    rows = await conn.fetch(
        """
        SELECT mvr_people_body_uuid, posture, posture_confidence,
               height_px, height_relative, height_m, dominant_colors,
               fallen, fallen_confidence, quality_score,
               featured_body_person_uuid, source_media_uuid, camera_id,
               total_appearances, bbox_trajectory, created_at
        FROM mvr_people_body
        WHERE source_media_uuid::text = $1 OR featured_video_uuid::text = $1
        ORDER BY created_at DESC
        LIMIT 2000
        """,
        media_id,
    )
    out = []
    for row in rows:
        out.append(
            {
                "mvr_people_body_uuid": str(row["mvr_people_body_uuid"]),
                "posture": row["posture"],
                "posture_confidence": row["posture_confidence"],
                "height_px": row["height_px"],
                "height_relative": row["height_relative"],
                "height_m": row["height_m"],
                "dominant_colors": _normalize_dominant_colors(row["dominant_colors"]),
                "fallen": row["fallen"],
                "fallen_confidence": row["fallen_confidence"],
                "quality_score": row["quality_score"],
                "featured_body_person_uuid": (
                    str(row["featured_body_person_uuid"])
                    if row["featured_body_person_uuid"]
                    else None
                ),
                "source_media_uuid": (
                    str(row["source_media_uuid"]) if row["source_media_uuid"] else None
                ),
                "camera_id": row["camera_id"],
                "total_appearances": row["total_appearances"],
                "bbox_trajectory": row["bbox_trajectory"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        )
    if not out:
        return out
    # Prefer newest row with computed colors; otherwise newest overall.
    with_colors = [item for item in out if item.get("dominant_colors")]
    if with_colors:
        return [with_colors[0]]
    return [out[0]]


async def record_stitch(
    conn: asyncpg.Connection,
    *,
    camera_id: str,
    mvr_a: str,
    mvr_b: str,
    media_a: Optional[str],
    media_b: Optional[str],
    iou: float,
    center_distance_px: float,
    time_gap_sec: float,
) -> None:
    await ensure_mvr_people_body_schema(conn)
    await conn.execute(
        """
        INSERT INTO mvr_people_body_stitch_audit (
            camera_id, mvr_uuid_a, mvr_uuid_b, media_id_a, media_id_b,
            iou, center_distance_px, time_gap_sec, reason
        ) VALUES ($1,$2::uuid,$3::uuid,$4::uuid,$5::uuid,$6,$7,$8,$9)
        """,
        camera_id,
        mvr_a,
        mvr_b,
        media_a,
        media_b,
        iou,
        center_distance_px,
        time_gap_sec,
        "same_camera_continuous_iou_stitch",
    )
    await conn.execute(
        """
        UPDATE mvr_people_body
        SET stitched_from_mvr_uuid = $1::uuid, updated_at = NOW()
        WHERE mvr_people_body_uuid = $2::uuid
        """,
        mvr_a,
        mvr_b,
    )
