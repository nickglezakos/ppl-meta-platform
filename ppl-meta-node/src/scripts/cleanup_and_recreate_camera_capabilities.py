#!/usr/bin/env python3
"""
Script to clean up and recreate camera capabilities in the PPL Meta Node system
to match the Camera service permission format exactly.
"""

import os
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models.role import Capability, Role, RoleCapability, UserRole
from src.models.user import User


def delete_old_camera_capabilities(db: Session):
    """Delete all old camera-related capabilities."""

    # Old camera capability names to remove
    old_capabilities = [
        "detect_cameras",
        "view_cameras",
        "connect_camera",
        "disconnect_camera",
        "view_stream",
        "start_stream",
        "stop_stream",
        "capture_snapshot",
        "manage_sessions",
        "view_capabilities",
        "admin_disconnect_all",
        "view_active_connections",
        "manage_camera_settings",
        "admin_camera_functions",
        "full_admin_access",
    ]

    deleted_count = 0

    for cap_name in old_capabilities:
        # Find the capability
        capability = db.query(Capability).filter(Capability.name == cap_name).first()
        if capability:
            # First delete role-capability assignments
            role_capabilities = (
                db.query(RoleCapability)
                .filter(RoleCapability.capability_id == capability.id)
                .all()
            )
            for rc in role_capabilities:
                db.delete(rc)

            # Then delete the capability
            db.delete(capability)
            deleted_count += 1
            print(f"🗑️ Deleted old capability: {cap_name}")

    db.commit()
    print(f"✅ Deleted {deleted_count} old camera capabilities")


def create_new_camera_capabilities(db: Session):
    """Create new camera capabilities matching Camera service permission format."""

    # New camera capabilities in correct format (matching Camera service)
    new_capabilities = [
        "cameras:detect",  # CameraPermission.DETECT_CAMERAS
        "cameras:view",  # CameraPermission.VIEW_CAMERAS
        "cameras:connect",  # CameraPermission.CONNECT_CAMERA
        "cameras:disconnect",  # CameraPermission.DISCONNECT_CAMERA
        "cameras:stream:view",  # CameraPermission.VIEW_STREAM
        "cameras:stream:start",  # CameraPermission.START_STREAM
        "cameras:stream:stop",  # CameraPermission.STOP_STREAM
        "cameras:record:start",  # CameraPermission.CAPTURE_SNAPSHOT
        "cameras:sessions:manage",  # CameraPermission.MANAGE_SESSIONS
        "cameras:view",  # CameraPermission.VIEW_CAPABILITIES (same as view)
        "cameras:admin",  # CameraPermission.ADMIN_DISCONNECT_ALL
        "cameras:view",  # CameraPermission.VIEW_ACTIVE_CONNECTIONS (same as view)
        "cameras:settings:update",  # CameraPermission.MANAGE_CAMERA_SETTINGS
        "cameras:admin",  # CameraPermission.ADMIN_CAMERA_FUNCTIONS (same as admin)
        "cameras:admin",  # CameraPermission.FULL_ADMIN_ACCESS (same as admin)
    ]

    # Remove duplicates while preserving order
    unique_capabilities = []
    seen = set()
    for cap in new_capabilities:
        if cap not in seen:
            unique_capabilities.append(cap)
            seen.add(cap)

    created_count = 0

    for cap_name in unique_capabilities:
        # Check if capability already exists
        existing = db.query(Capability).filter(Capability.name == cap_name).first()
        if not existing:
            # Create new capability
            new_capability = Capability(name=cap_name)
            db.add(new_capability)
            created_count += 1
            print(f"✅ Created new capability: {cap_name}")
        else:
            print(f"✅ Capability already exists: {cap_name}")

    db.commit()
    print(f"✅ Created {created_count} new camera capabilities")
    return unique_capabilities


def setup_camera_role_and_user(db: Session, capabilities_list: list):
    """Set up camera role with new capabilities and assign to test user."""

    # Get or create camera role
    camera_role = db.query(Role).filter(Role.name == "camera_user").first()
    if not camera_role:
        camera_role = Role(name="camera_user")
        db.add(camera_role)
        db.commit()
        db.refresh(camera_role)
        print("✅ Created camera_user role")
    else:
        print("✅ Camera role already exists")

    # Clear existing role-capability assignments for this role
    existing_assignments = (
        db.query(RoleCapability).filter(RoleCapability.role_id == camera_role.id).all()
    )
    for assignment in existing_assignments:
        db.delete(assignment)
    print(f"🗑️ Cleared {len(existing_assignments)} old role-capability assignments")

    # Assign new capabilities to role
    assigned_count = 0
    for cap_name in capabilities_list:
        capability = db.query(Capability).filter(Capability.name == cap_name).first()
        if capability:
            role_capability = RoleCapability(
                role_id=camera_role.id, capability_id=capability.id
            )
            db.add(role_capability)
            assigned_count += 1
            print(f"✅ Assigned capability '{cap_name}' to camera_user role")

    db.commit()
    print(f"✅ Assigned {assigned_count} capabilities to camera role")

    # Assign role to test user
    test_user_email = "fresh.user@example.com"
    user = db.query(User).filter(User.email == test_user_email).first()
    if user:
        # Check if user-role assignment already exists
        existing_assignment = (
            db.query(UserRole)
            .filter(UserRole.user_id == user.id, UserRole.role_id == camera_role.id)
            .first()
        )

        if not existing_assignment:
            user_role = UserRole(user_id=user.id, role_id=camera_role.id)
            db.add(user_role)
            db.commit()
            print(f"✅ Assigned camera_user role to {test_user_email}")
        else:
            print(f"✅ User {test_user_email} already has camera_user role")
    else:
        print(f"❌ User {test_user_email} not found")


def verify_setup(db: Session):
    """Verify the camera capabilities setup."""

    print("\n🔍 Verification Results:")

    # Check capabilities
    camera_capabilities = (
        db.query(Capability).filter(Capability.name.like("cameras:%")).all()
    )
    print(f"Camera capabilities ({len(camera_capabilities)}):")
    for cap in camera_capabilities:
        print(f"  - {cap.name}")

    # Check camera role
    camera_role = db.query(Role).filter(Role.name == "camera_user").first()
    if camera_role:
        role_caps = (
            db.query(RoleCapability)
            .filter(RoleCapability.role_id == camera_role.id)
            .all()
        )
        print(f"Camera role capabilities ({len(role_caps)}):")
        for rc in role_caps:
            print(f"  - {rc.capability.name}")

    # Check test user
    user = db.query(User).filter(User.email == "fresh.user@example.com").first()
    if user:
        user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        print(f"Test user roles ({len(user_roles)}):")
        for ur in user_roles:
            print(f"  - {ur.role.name}")


def main():
    """Main function to clean up and recreate camera capabilities."""

    print("🧹 PPL Meta Node - Camera Capabilities Cleanup & Recreation")
    print("=" * 65)

    # Create database session
    db = SessionLocal()

    try:
        # 1. Delete old camera capabilities
        print("\n1. Deleting old camera capabilities...")
        delete_old_camera_capabilities(db)

        # 2. Create new camera capabilities in correct format
        print("\n2. Creating new camera capabilities...")
        new_capabilities = create_new_camera_capabilities(db)

        # 3. Set up camera role and assign to user
        print("\n3. Setting up camera role and user assignments...")
        setup_camera_role_and_user(db, new_capabilities)

        # 4. Verify setup
        print("\n4. Verifying setup...")
        verify_setup(db)

        print("\n🎉 Camera capabilities cleanup and recreation completed successfully!")
        print(
            "\nThe system now uses the correct permission format matching the Camera service."
        )
        print(
            "Test user 'fresh.user@example.com' can now authenticate and access camera endpoints."
        )

    except Exception as e:
        print(f"❌ Error during cleanup and recreation: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
