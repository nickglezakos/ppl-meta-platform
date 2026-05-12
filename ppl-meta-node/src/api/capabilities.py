"""Endpoints for capability management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.auth_utils import get_current_user, get_user_capability_names, get_user_role_names, require_capability
from src.database import get_db
from src.schemas.user import UserRead
from src.services.capabilites_service import (
    get_capabilities_by_role,
    get_roles_and_capabilities_by_user,
)

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("/by-role/{role_id}", response_model=list[str])
def capabilities_by_role(
    role_id: int,
    db: Session = Depends(get_db),
    _current_user: UserRead = Depends(require_capability("auth.capabilities.read")),
):
    """
    Get a list of capability names for a given role. Only accessible to logged-in users.
    """
    capabilities = get_capabilities_by_role(db, role_id)
    if not capabilities:
        raise HTTPException(status_code=404, detail="Role not found or no capabilities")
    return [cap.name for cap in capabilities]


@router.get("/by-user/{user_id}")
def roles_and_capabilities_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: UserRead = Depends(require_capability("users.accounts.read")),
):
    """
    Returns the roles and capabilities of a given user. Only accessible to logged-in users.
    """
    result = get_roles_and_capabilities_by_user(db, user_id)
    if not result["roles"] and not result["capabilities"]:
        raise HTTPException(
            status_code=404, detail="User not found or no roles/capabilities"
        )
    return result


@router.get("/my-capabilities")
def get_my_capabilities(
    db: Session = Depends(get_db), current_user: UserRead = Depends(get_current_user)
):
    """
    Returns the capabilities of the current logged-in user.
    """
    return {
        "user_id": current_user.id,
        "roles": get_user_role_names(db, current_user.id),
        "capabilities": sorted(get_user_capability_names(db, current_user.id)),
    }
