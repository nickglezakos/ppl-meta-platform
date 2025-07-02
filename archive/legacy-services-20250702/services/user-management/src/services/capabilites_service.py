from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth_utils import get_current_user
from src.database import get_db
from src.schemas.user import UserRead
from src.models.role import Capability, RoleCapability
from src.models.user import User


def user_has_capability(required_capability: str):
    def checker(
        current_user: UserRead = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        user = db.query(User).filter(User.id == current_user.id).first()
        user_capabilities = set()
        for ur in user.roles:
            for rc in ur.role.capabilities:
                user_capabilities.add(rc.capability.name)
        if required_capability in user_capabilities:
            return current_user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker

def get_capabilities_by_role(db: Session, role_id: int) -> list:
    """
    Returns a list of capabilities for a given role.
    """
    capabilities = (
        db.query(Capability)
        .join(RoleCapability, Capability.id == RoleCapability.capability_id)
        .filter(RoleCapability.role_id == role_id)
        .all()
    )
    return capabilities

def get_roles_and_capabilities_by_user(db: Session, user_id: int) -> dict:
    """
    Returns a dictionary with the roles and capabilities of a given user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"roles": [], "capabilities": []}

    roles = []
    capabilities = set()
    for user_role in user.roles:
        role = user_role.role
        roles.append(role.name)
        for rc in role.capabilities:
            capabilities.add(rc.capability.name)

    return {
        "roles": roles,
        "capabilities": list(capabilities)
    }
