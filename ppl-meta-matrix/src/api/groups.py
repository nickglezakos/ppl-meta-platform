"""Matrix Group CRUD API endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.matrix_service import matrix_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["matrix-groups"])


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    multi_install: bool = False


class UpdateGroupRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.post("/groups")
async def create_group(request: CreateGroupRequest):
    try:
        group = matrix_service.create_group(
            name=request.name,
            description=request.description,
            multi_install=request.multi_install,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "licence_multi_install": group.licence_multi_install,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


@router.get("/groups")
async def list_groups():
    groups = matrix_service.list_groups()
    return {
        "groups": [
            {
                "id": str(g.id),
                "name": g.name,
                "description": g.description,
                "licence_multi_install": g.licence_multi_install,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in groups
        ],
        "count": len(groups),
    }


@router.get("/groups/{group_id}")
async def get_group(group_id: str):
    group = matrix_service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "licence_multi_install": group.licence_multi_install,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


@router.put("/groups/{group_id}")
async def update_group(group_id: str, request: UpdateGroupRequest):
    group = matrix_service.update_group(group_id, name=request.name, description=request.description)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }


@router.delete("/groups/{group_id}")
async def delete_group(group_id: str):
    try:
        deleted = matrix_service.delete_group(group_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"status": "deleted", "group_id": group_id}