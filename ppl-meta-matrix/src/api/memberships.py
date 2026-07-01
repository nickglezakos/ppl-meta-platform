"""Matrix Installation Membership API endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.matrix_service import matrix_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["matrix-memberships"])


class AddInstallationRequest(BaseModel):
    installation_uuid: str = Field(..., min_length=3)
    installation_name: str = ""
    node_url: str = ""


@router.post("/groups/{group_id}/installations")
async def add_installation(group_id: str, request: AddInstallationRequest):
    try:
        membership = matrix_service.add_installation(
            group_id=group_id,
            installation_uuid=request.installation_uuid,
            installation_name=request.installation_name,
            node_url=request.node_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "id": membership.id,
        "matrix_group_id": group_id,
        "installation_uuid": membership.installation_uuid,
        "installation_name": membership.installation_name,
        "node_url": membership.node_url,
        "added_at": membership.added_at.isoformat() if membership.added_at else None,
    }


@router.get("/groups/{group_id}/installations")
async def list_installations(group_id: str):
    memberships = matrix_service.list_installations(group_id)
    return {
        "installations": [
            {
                "id": m.id,
                "installation_uuid": m.installation_uuid,
                "installation_name": m.installation_name,
                "node_url": m.node_url,
                "added_at": m.added_at.isoformat() if m.added_at else None,
            }
            for m in memberships
        ],
        "count": len(memberships),
    }


@router.delete("/groups/{group_id}/installations/{installation_uuid}")
async def remove_installation(group_id: str, installation_uuid: str):
    try:
        removed = matrix_service.remove_installation(group_id, installation_uuid)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not removed:
        raise HTTPException(status_code=404, detail="Installation not found in group")
    return {"status": "removed", "installation_uuid": installation_uuid}