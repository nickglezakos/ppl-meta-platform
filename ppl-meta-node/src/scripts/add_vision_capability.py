#!/usr/bin/env python3
"""
Script to add the 'vision' capability to the PPL Meta Node system
and assign it to the fresh user.
"""

import os
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models.role import Capability, Role, RoleCapability, UserRole
from src.models.user import Base, User


def create_vision_capability(db: Session):
    """Create the vision capability if it doesn't exist."""

    # Check if vision capability already exists
    existing_capability = (
        db.query(Capability).filter(Capability.name == "vision").first()
    )
    if existing_capability:
        print("✅ Vision capability already exists")
        return existing_capability

    # Create vision capability
    vision_capability = Capability(name="vision")
    db.add(vision_capability)
    db.commit()
    db.refresh(vision_capability)

    print("✅ Created vision capability")
    return vision_capability


def get_or_create_vision_role(db: Session):
    """Get or create a vision role."""

    # Check if vision role already exists
    existing_role = db.query(Role).filter(Role.name == "vision_user").first()
    if existing_role:
        print("✅ Vision role already exists")
        return existing_role

    # Create vision role
    vision_role = Role(name="vision_user")
    db.add(vision_role)
    db.commit()
    db.refresh(vision_role)

    print("✅ Created vision_user role")
    return vision_role


def assign_capability_to_role(db: Session, role: Role, capability: Capability):
    """Assign capability to role if not already assigned."""

    # Check if already assigned
    existing_assignment = (
        db.query(RoleCapability)
        .filter(
            RoleCapability.role_id == role.id,
            RoleCapability.capability_id == capability.id,
        )
        .first()
    )

    if existing_assignment:
        print("✅ Vision capability already assigned to vision_user role")
        return existing_assignment

    # Create role-capability assignment
    role_capability = RoleCapability(role_id=role.id, capability_id=capability.id)
    db.add(role_capability)
    db.commit()
    db.refresh(role_capability)

    print("✅ Assigned vision capability to vision_user role")
    return role_capability


def assign_user_to_role(db: Session, user_email: str, role: Role):
    """Assign user to role if not already assigned."""

    # Find user by email
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        print(f"❌ User with email {user_email} not found")
        return None

    # Check if user already has this role
    existing_user_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
        .first()
    )

    if existing_user_role:
        print(f"✅ User {user_email} already has vision_user role")
        return existing_user_role

    # Create user-role assignment
    user_role = UserRole(user_id=user.id, role_id=role.id)
    db.add(user_role)
    db.commit()
    db.refresh(user_role)

    print(f"✅ Assigned vision_user role to user {user_email}")
    return user_role


def verify_user_capabilities(db: Session, user_email: str):
    """Verify that the user has the vision capability."""

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        print(f"❌ User {user_email} not found")
        return False

    # Get user capabilities
    user_capabilities = set()
    for user_role in user.roles:
        for role_capability in user_role.role.capabilities:
            user_capabilities.add(role_capability.capability.name)

    if "vision" in user_capabilities:
        print(f"✅ User {user_email} has vision capability")
        print(f"   User capabilities: {list(user_capabilities)}")
        return True
    else:
        print(f"❌ User {user_email} does not have vision capability")
        print(f"   User capabilities: {list(user_capabilities)}")
        return False


def main():
    """Main function to set up vision capability system."""

    print("🎯 Setting up Vision Capability System")
    print("=" * 50)

    # Create database session
    db = SessionLocal()

    try:
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)

        # 1. Create vision capability
        vision_capability = create_vision_capability(db)

        # 2. Get or create vision role
        vision_role = get_or_create_vision_role(db)

        # 3. Assign capability to role
        assign_capability_to_role(db, vision_role, vision_capability)

        # 4. Assign fresh user to vision role
        fresh_user_email = "fresh.user@example.com"
        assign_user_to_role(db, fresh_user_email, vision_role)

        # 5. Verify the setup
        print("\n📊 Verification:")
        print("-" * 30)
        verify_user_capabilities(db, fresh_user_email)

        print("\n🎉 Vision capability system setup complete!")
        print(f"   - Vision capability created")
        print(f"   - Vision role created")
        print(f"   - Fresh user ({fresh_user_email}) assigned vision capability")

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
