#!/usr/bin/env python3
"""
Quick script to assign cameras:admin capability to a user
"""

import os
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.role import Capability, Role, RoleCapability, UserRole
from src.models.user import User


def assign_camera_admin_to_user(db: Session, user_id: int):
    """Assign cameras:admin capability to a user by ID."""

    # Find the user by ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"❌ User with ID {user_id} not found")
        return False

    print(f"✅ Found user: {user.email} (ID: {user.id})")

    # Find the cameras:admin capability
    camera_admin_cap = (
        db.query(Capability).filter(Capability.name == "cameras:admin").first()
    )
    if not camera_admin_cap:
        print("❌ cameras:admin capability not found")
        return False

    print(f"✅ Found cameras:admin capability (ID: {camera_admin_cap.id})")

    # Find or create an admin role
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        print("❌ Admin role not found")
        return False

    print(f"✅ Found admin role (ID: {admin_role.id})")

    # Check if the admin role already has cameras:admin capability
    role_cap = (
        db.query(RoleCapability)
        .filter(
            RoleCapability.role_id == admin_role.id,
            RoleCapability.capability_id == camera_admin_cap.id,
        )
        .first()
    )

    if not role_cap:
        # Add the capability to the admin role
        role_cap = RoleCapability(
            role_id=admin_role.id, capability_id=camera_admin_cap.id
        )
        db.add(role_cap)
        print("✅ Added cameras:admin capability to admin role")
    else:
        print("✅ Admin role already has cameras:admin capability")

    # Check if user already has admin role
    user_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == admin_role.id)
        .first()
    )

    if not user_role:
        # Assign admin role to user
        user_role = UserRole(user_id=user.id, role_id=admin_role.id)
        db.add(user_role)
        print("✅ Assigned admin role to user")
    else:
        print("✅ User already has admin role")

    db.commit()
    print(f"🎉 Successfully assigned cameras:admin capability to user {user_id}")
    return True


if __name__ == "__main__":
    db = SessionLocal()
    try:
        success = assign_camera_admin_to_user(db, 7)
        if success:
            print("\n✅ User should now have cameras:admin permission!")
        else:
            print("\n❌ Failed to assign permission")
    finally:
        db.close()
