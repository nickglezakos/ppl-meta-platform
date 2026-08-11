from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.auth_utils import require_capability
from src.database import get_db
from src.models.role import UserRole, Role, RoleCapability, Capability
from src.schemas.role import RoleCreate, RoleRead, UserRoleRead, RoleCapabilityCreate
from src.services.role_service import (
    add_capability_to_role,
    assign_role_to_user,
    create_role,
    delete_role,
    get_role_by_id,
    get_role_by_name,
    list_roles,
    remove_capability_from_role,
    unassign_role_from_user,
    update_role,
)
from src.services.user_service import log_user_action

router = APIRouter(prefix="/roles", tags=["roles"])

@router.post("/", response_model=RoleRead)
def api_create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.create")),
):
    try:
        created_role = create_role(db, role.name)
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"role_create:{created_role.name}",
        )
        return created_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@router.get("/", response_model=list[RoleRead])
def api_list_roles(
    db: Session = Depends(get_db),
    _current_user = Depends(require_capability("auth.roles.read")),
):
    return list_roles(db)

@router.get("/{role_id}", response_model=RoleRead)
def api_get_role_by_id(
    role_id: int,
    db: Session = Depends(get_db),
    _current_user = Depends(require_capability("auth.roles.read")),
):
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.get("/by-name/{role_name}", response_model=RoleRead)
def api_get_role_by_name(
    role_name: str,
    db: Session = Depends(get_db),
    _current_user = Depends(require_capability("auth.roles.read")),
):
    role = get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.put("/{role_id}", response_model=RoleRead)
def api_update_role(
    role_id: int,
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.update")),
):
    try:
        updated_role = update_role(db, role_id, role.name)
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"role_update:{updated_role.id}:{updated_role.name}",
        )
        return updated_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@router.delete("/{role_id}")
def api_delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.delete")),
):
    try:
        role = get_role_by_id(db, role_id)
        delete_role(db, role_id)
        role_name = role.name if role else str(role_id)
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"role_delete:{role_name}",
        )
        return {"detail": "Role deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{role_id}/delete-and-migrate")
def api_delete_role_and_migrate(
    role_id: int,
    target_role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.delete")),
):
    """Delete a role, migrating its capabilities to a target role first."""
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    target = get_role_by_id(db, target_role_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target role not found")
    if role_id == target_role_id:
        raise HTTPException(status_code=400, detail="Cannot migrate to the same role")

    # Migrate capabilities
    role_caps = (
        db.query(RoleCapability)
        .filter(RoleCapability.role_id == role_id)
        .all()
    )
    migrated = 0
    for rc in role_caps:
        # Skip duplicates
        existing = (
            db.query(RoleCapability)
            .filter_by(role_id=target_role_id, capability_id=rc.capability_id)
            .first()
        )
        if not existing:
            db.add(RoleCapability(role_id=target_role_id, capability_id=rc.capability_id))
            migrated += 1

    db.commit()
    log_user_action(
        db,
        current_user.username,
        current_user.email,
        f"role_delete_migrate:{role.name}->{target.name}:{migrated}",
    )
    delete_role(db, role_id)
    return {"detail": f"Role deleted, {migrated} capabilities migrated to '{target.name}'"}

@router.post("/assign/", response_model=UserRoleRead)
def api_assign_role_to_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.assign")),
):
    try:
        assign_role_to_user(db, user_id, role_id)
        user_role = db.query(UserRole).filter_by(user_id=user_id, role_id=role_id).first()
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"role_assign:user={user_id}:role={role_id}",
        )
        return user_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@router.post("/unassign/", response_model=dict)
def api_unassign_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.unassign")),
):
    try:
        unassign_role_from_user(db, user_id, role_id)
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"role_unassign:user={user_id}:role={role_id}",
        )
        return {"detail": "Role unassigned from user"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@router.post("/add-capability/", response_model=dict)
def api_add_capability_to_role(
    data: RoleCapabilityCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.capabilities.assign")),
):
    try:
        add_capability_to_role(db, data.role_id, data.capability_id)
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"capability_assign:role={data.role_id}:capability={data.capability_id}",
        )
        return {"detail": "Capability added to role"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

@router.post("/remove-capability/", response_model=dict)
def api_remove_capability_from_role(
    data: RoleCapabilityCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.capabilities.unassign")),
):
    try:
        remove_capability_from_role(db, data.role_id, data.capability_id)
        log_user_action(
            db,
            current_user.username,
            current_user.email,
            f"capability_unassign:role={data.role_id}:capability={data.capability_id}",
        )
        return {"detail": "Capability removed from role"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e