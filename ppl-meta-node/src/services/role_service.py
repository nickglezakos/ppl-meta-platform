from sqlalchemy.orm import Session
from src.models.role import Role, UserRole, RoleCapability, Capability
from src.models.user import User
from sqlalchemy.exc import IntegrityError


def create_role(db: Session, role_name: str) -> Role:
    role = Role(name=role_name)
    db.add(role)
    try:
        db.commit()
        db.refresh(role)
    except IntegrityError:
        db.rollback()
        raise ValueError("Role already exists")
    return role

def get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.query(Role).filter(Role.name == role_name).first()

def get_role_by_id(db: Session, role_id: int) -> Role | None:
    return db.query(Role).filter(Role.id == role_id).first()

def list_roles(db: Session) -> list[Role]:
    return db.query(Role).all()

def update_role(db: Session, role_id: int, new_name: str) -> Role:
    role = get_role_by_id(db, role_id)
    if not role:
        raise ValueError("Role not found")
    role.name = new_name
    try:
        db.commit()
        db.refresh(role)
    except IntegrityError:
        db.rollback()
        raise ValueError("Role name must be unique")
    return role

def delete_role(db: Session, role_id: int):
    role = get_role_by_id(db, role_id)
    if not role:
        raise ValueError("Role not found")
    db.delete(role)
    db.commit()

def assign_role_to_user(db: Session, user_id: int, role_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    role = get_role_by_id(db, role_id)
    if not user or not role:
        raise ValueError("User or Role not found")
    if db.query(UserRole).filter_by(user_id=user_id, role_id=role_id).first():
        raise ValueError("Role already assigned to user")
    user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(user_role)
    db.commit()
 
def add_capability_to_role(db: Session, role_id: int, capability_id: int):
    role = get_role_by_id(db, role_id)
    if not role:
        raise ValueError("Role not found")
    # Check if capability already assigned
    if db.query(RoleCapability).filter_by(role_id=role_id, capability_id=capability_id).first():
        raise ValueError("Capability already assigned to role")
    role_capability = RoleCapability(role_id=role_id, capability_id=capability_id)
    db.add(role_capability)
    db.commit()

def remove_capability_from_role(db: Session, role_id: int, capability_id: int):
    role_capability = db.query(RoleCapability).filter_by(role_id=role_id, capability_id=capability_id).first()
    if not role_capability:
        raise ValueError("Capability not assigned to role")
    db.delete(role_capability)
    db.commit()

def unassign_role_from_user(db: Session, user_id: int, role_id: int):
    user_role = db.query(UserRole).filter_by(user_id=user_id, role_id=role_id).first()
    if not user_role:
        raise ValueError("Role not assigned to user")
    db.delete(user_role)
    db.commit()

# Startup: Ensure default admin role for a given admin user

def ensure_admin_role(db: Session, admin_username: str):
    admin_role = get_role_by_name(db, "admin")
    if not admin_role:
        admin_role = create_role(db, "admin")
    admin_user = db.query(User).filter(User.username == admin_username).first()
    if admin_user and not db.query(UserRole).filter_by(user_id=admin_user.id, role_id=admin_role.id).first():
        assign_role_to_user(db, admin_user.id, admin_role.id)


def ensure_user_role(db: Session, username: str):
    """Ensure 'user' role exists and is assigned to the given user."""
    user_role = get_role_by_name(db, "user")
    if not user_role:
        user_role = create_role(db, "user")
    user = db.query(User).filter(User.username == username).first()
    if user and not db.query(UserRole).filter_by(user_id=user.id, role_id=user_role.id).first():
        assign_role_to_user(db, user.id, user_role.id)


def ensure_default_capabilities(db: Session):
    """Ensure default capabilities exist and are assigned to appropriate roles."""
    # Ensure media:view capability exists
    media_view_cap = db.query(Capability).filter(Capability.name == "media:view").first()
    if not media_view_cap:
        media_view_cap = Capability(name="media:view")
        db.add(media_view_cap)
        db.commit()
        db.refresh(media_view_cap)

    # Assign media:view to admin role
    admin_role = get_role_by_name(db, "admin")
    if admin_role:
        if not db.query(RoleCapability).filter_by(role_id=admin_role.id, capability_id=media_view_cap.id).first():
            rc = RoleCapability(role_id=admin_role.id, capability_id=media_view_cap.id)
            db.add(rc)
            db.commit()

    # Assign media:view to user role
    user_role = get_role_by_name(db, "user")
    if user_role:
        if not db.query(RoleCapability).filter_by(role_id=user_role.id, capability_id=media_view_cap.id).first():
            rc = RoleCapability(role_id=user_role.id, capability_id=media_view_cap.id)
            db.add(rc)
            db.commit()