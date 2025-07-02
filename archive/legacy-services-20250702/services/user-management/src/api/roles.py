from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.schemas.role import RoleCreate, RoleRead, UserRoleRead, RoleCapabilityCreate
from src.services.role_service import (
    create_role, get_role_by_name, get_role_by_id, list_roles,
    update_role, delete_role, assign_role_to_user, unassign_role_from_user,
    add_capability_to_role, remove_capability_from_role
)
from src.models.role import UserRole
from src.database import get_db

router = APIRouter(prefix="/roles", tags=["roles"])

@router.post("/", response_model=RoleRead)
def api_create_role(role: RoleCreate, db: Session = Depends(get_db)):
    try:
        return create_role(db, role.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[RoleRead])
def api_list_roles(db: Session = Depends(get_db)):
    return list_roles(db)

@router.get("/{role_id}", response_model=RoleRead)
def api_get_role_by_id(role_id: int, db: Session = Depends(get_db)):
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.get("/by-name/{role_name}", response_model=RoleRead)
def api_get_role_by_name(role_name: str, db: Session = Depends(get_db)):
    role = get_role_by_name(db, role_name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.put("/{role_id}", response_model=RoleRead)
def api_update_role(role_id: int, role: RoleCreate, db: Session = Depends(get_db)):
    try:
        return update_role(db, role_id, role.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{role_id}")
def api_delete_role(role_id: int, db: Session = Depends(get_db)):
    try:
        delete_role(db, role_id)
        return {"detail": "Role deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/assign/", response_model=UserRoleRead)
def api_assign_role_to_user(user_id: int, role_id: int, db: Session = Depends(get_db)):
    try:
        assign_role_to_user(db, user_id, role_id)
        user_role = db.query(UserRole).filter_by(user_id=user_id, role_id=role_id).first()
        return user_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/unassign/", response_model=dict)
def api_unassign_role_from_user(user_id: int, role_id: int, db: Session = Depends(get_db)):
    try:
        unassign_role_from_user(db, user_id, role_id)
        return {"detail": "Role unassigned from user"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/add-capability/", response_model=dict)
def api_add_capability_to_role(
    data: RoleCapabilityCreate,
    db: Session = Depends(get_db)
):
    try:
        add_capability_to_role(db, data.role_id, data.capability_id)
        return {"detail": "Capability added to role"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/remove-capability/", response_model=dict)
def api_remove_capability_from_role(
    data: RoleCapabilityCreate,
    db: Session = Depends(get_db)
):
    try:
        remove_capability_from_role(db, data.role_id, data.capability_id)
        return {"detail": "Capability removed from role"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))