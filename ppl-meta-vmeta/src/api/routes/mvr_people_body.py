"""MVR People Body API routes (parallel to mvr_people for body tracks)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_current_user_or_internal_service, get_db_connection
from services import mvr_people_body_service as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/mvr-people-body", tags=["mvr-people-body"])


class MaterializeRequest(BaseModel):
    body_persons: List[Dict[str, Any]] = Field(default_factory=list)
    media_id: Optional[str] = None
    camera_id: Optional[str] = None
    session_uuid: Optional[str] = None


class StitchRequest(BaseModel):
    camera_id: str
    mvr_uuid_a: str
    mvr_uuid_b: str
    media_id_a: Optional[str] = None
    media_id_b: Optional[str] = None
    iou: float = 0.0
    center_distance_px: float = 0.0
    time_gap_sec: float = 0.0


@router.get("/health")
async def health():
    return {"status": "ok", "service": "mvr-people-body"}


@router.post("/materialize/persisted-body-person-objects")
async def materialize_body_persons(
    body: MaterializeRequest,
    _user: dict = Depends(get_current_user_or_internal_service),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    if not body.body_persons:
        return {"success": True, "created": [], "count": 0}
    result = await svc.materialize_from_body_persons(
        conn,
        body.body_persons,
        media_id=body.media_id,
        camera_id=body.camera_id,
        session_uuid=body.session_uuid,
    )
    return result


@router.get("/media/{media_id}")
async def list_media_mvr_people_body(
    media_id: str,
    _user: dict = Depends(get_current_user_or_internal_service),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    items = await svc.list_for_media(conn, media_id)
    return {"media_id": media_id, "mvr_people_body": items, "count": len(items)}


@router.post("/stitch")
async def stitch_mvr_people_body(
    body: StitchRequest,
    _user: dict = Depends(get_current_user_or_internal_service),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """
    Record same-camera continuous track continuation.
    Callers must verify time gap + IoU before invoking (see Vision stitch-segments).
    """
    await svc.record_stitch(
        conn,
        camera_id=body.camera_id,
        mvr_a=body.mvr_uuid_a,
        mvr_b=body.mvr_uuid_b,
        media_a=body.media_id_a,
        media_b=body.media_id_b,
        iou=body.iou,
        center_distance_px=body.center_distance_px,
        time_gap_sec=body.time_gap_sec,
    )
    return {"success": True, "method": "same_camera_continuous_iou_stitch"}


@router.get("/{mvr_uuid}")
async def get_mvr_people_body(
    mvr_uuid: str,
    _user: dict = Depends(get_current_user_or_internal_service),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    await svc.ensure_mvr_people_body_schema(conn)
    row = await conn.fetchrow(
        "SELECT * FROM mvr_people_body WHERE mvr_people_body_uuid = $1::uuid",
        mvr_uuid,
    )
    if not row:
        raise HTTPException(status_code=404, detail="mvr_people_body_not_found")
    return dict(row)
