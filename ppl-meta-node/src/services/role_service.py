from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.role import Capability, Role, RoleCapability, UserRole
from src.models.user import User


SYSTEM_ROLE_NAMES = {"owner", "admin", "user"}

DEFAULT_ROLE_CAPABILITIES = {
    "user": {
        "auth.session.use",
        "users.profile.read",
        "users.profile.update",
        "users.password.change_self",
        "users.password.recover_self",
        "analytics.view",
        "cameras.view",
        "media.view",
        "workflows.use",
    },
    "admin": {
        "auth.session.use",
        "users.profile.read",
        "users.profile.update",
        "users.password.change_self",
        "users.password.recover_self",
        "analytics.view",
        "cameras.view",
        "media.view",
        "workflows.use",
        "users.accounts.read",
        "users.accounts.create",
        "users.accounts.update",
        "users.accounts.disable",
        "cameras.manage",
        "media.manage",
        "operations.execute",
        "auth.roles.read",
    },
    "owner": {
        "auth.session.use",
        "users.profile.read",
        "users.profile.update",
        "users.password.change_self",
        "users.password.recover_self",
        "analytics.view",
        "cameras.view",
        "media.view",
        "workflows.use",
        "users.accounts.read",
        "users.accounts.create",
        "users.accounts.update",
        "users.accounts.disable",
        "users.accounts.delete",
        "cameras.manage",
        "media.manage",
        "operations.execute",
        "auth.roles.read",
        "auth.roles.create",
        "auth.roles.update",
        "auth.roles.delete",
        "auth.roles.assign",
        "auth.roles.unassign",
        "auth.capabilities.read",
        "auth.capabilities.assign",
        "auth.capabilities.unassign",
        "auth.capabilities.manage",
        "system.installation.manage",
        "system.licensing.manage",
        "system.recovery.manage",
    },
}


def create_role(db: Session, role_name: str) -> Role:
    role = Role(name=role_name)
    db.add(role)
    try:
        db.commit()
        db.refresh(role)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Role already exists") from exc
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
    if role.name in SYSTEM_ROLE_NAMES and role.name != new_name:
        raise ValueError("System roles cannot be renamed")
    role.name = new_name
    try:
        db.commit()
        db.refresh(role)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Role name must be unique") from exc
    return role

def delete_role(db: Session, role_id: int):
    role = get_role_by_id(db, role_id)
    if not role:
        raise ValueError("Role not found")
    if role.name in SYSTEM_ROLE_NAMES:
        raise ValueError("System roles cannot be deleted")
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
    if user_role.role.name == "owner":
        owner_assignments = db.query(UserRole).join(Role).filter(Role.name == "owner").count()
        if owner_assignments <= 1:
            raise ValueError("Cannot remove the final owner role assignment")
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


def ensure_owner_role(db: Session, owner_username: str):
    """Ensure the system owner role exists and is assigned to the given user."""
    owner_role = get_role_by_name(db, "owner")
    if not owner_role:
        owner_role = create_role(db, "owner")
    owner_user = db.query(User).filter(User.username == owner_username).first()
    if owner_user and not db.query(UserRole).filter_by(user_id=owner_user.id, role_id=owner_role.id).first():
        assign_role_to_user(db, owner_user.id, owner_role.id)


def ensure_user_role(db: Session, username: str):
    """Ensure 'user' role exists and is assigned to the given user."""
    user_role = get_role_by_name(db, "user")
    if not user_role:
        user_role = create_role(db, "user")
    user = db.query(User).filter(User.username == username).first()
    if user and not db.query(UserRole).filter_by(user_id=user.id, role_id=user_role.id).first():
        assign_role_to_user(db, user.id, user_role.id)


def ensure_exact_system_roles(db: Session, user_identifier: str, role_names: set[str]):
    """Ensure the user has exactly the given set of system roles."""
    if not role_names:
        raise ValueError("At least one system role is required")
    unknown_roles = set(role_names) - SYSTEM_ROLE_NAMES
    if unknown_roles:
        raise ValueError(f"Unknown system roles requested: {sorted(unknown_roles)}")

    user = (
        db.query(User)
        .filter(
            (User.username == user_identifier) | (User.email == user_identifier)
        )
        .first()
    )
    if not user:
        raise ValueError(f"User not found: {user_identifier}")

    roles_by_name = {}
    for role_name in sorted(role_names):
        role = get_role_by_name(db, role_name)
        if not role:
            role = create_role(db, role_name)
        roles_by_name[role_name] = role

    current_assignments = (
        db.query(UserRole)
        .join(Role)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    current_system_roles = {
        assignment.role.name: assignment
        for assignment in current_assignments
        if assignment.role.name in SYSTEM_ROLE_NAMES
    }

    for role_name in role_names:
        if role_name not in current_system_roles:
            db.add(UserRole(user_id=user.id, role_id=roles_by_name[role_name].id))

    db.flush()

    removable_roles = sorted(set(current_system_roles) - set(role_names))
    for role_name in removable_roles:
        assignment = current_system_roles[role_name]
        if role_name == "owner":
            owner_assignments = db.query(UserRole).join(Role).filter(Role.name == "owner").count()
            if owner_assignments <= 1:
                raise ValueError("Cannot remove the final owner role assignment")
        db.delete(assignment)

    db.commit()


def ensure_default_capabilities(db: Session):
    """Ensure default system capabilities and role mappings exist."""
    roles = {}
    for role_name in DEFAULT_ROLE_CAPABILITIES:
        role = get_role_by_name(db, role_name)
        if not role:
            role = create_role(db, role_name)
        roles[role_name] = role

    capability_names = sorted(
        {
            capability_name
            for capability_names in DEFAULT_ROLE_CAPABILITIES.values()
            for capability_name in capability_names
        }
    )
    capabilities = {}
    for capability_name in capability_names:
        capability = db.query(Capability).filter(Capability.name == capability_name).first()
        if not capability:
            capability = Capability(name=capability_name)
            db.add(capability)
            db.commit()
            db.refresh(capability)
        capabilities[capability_name] = capability

    for role_name, capability_names in DEFAULT_ROLE_CAPABILITIES.items():
        role = roles[role_name]
        for capability_name in capability_names:
            capability = capabilities[capability_name]
            existing = db.query(RoleCapability).filter_by(
                role_id=role.id,
                capability_id=capability.id,
            ).first()
            if not existing:
                db.add(RoleCapability(role_id=role.id, capability_id=capability.id))

    db.commit()