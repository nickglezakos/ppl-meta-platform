#!/usr/bin/env python3
"""
Script to add camera-related capabilities to the PPL Meta Node system
and assign them to users for cross-service authentication.
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


def create_camera_capabilities(db: Session):
    """Create camera-related capabilities if they don't exist."""

    # Camera capabilities to create (matching the Camera service permissions)
    camera_capabilities = [
        "detect_cameras",  # Detect available cameras
        "view_cameras",  # View camera list and information
        "connect_camera",  # Connect to cameras
        "disconnect_camera",  # Disconnect from cameras
        "view_stream",  # Access video streams
        "start_stream",  # Start video streaming
        "stop_stream",  # Stop video streaming
        "capture_snapshot",  # Take snapshots
        "manage_sessions",  # Manage camera sessions
        "view_capabilities",  # View camera technical specifications
        "admin_disconnect_all",  # Disconnect all cameras (admin only)
        "view_active_connections",  # View all active connections
        "manage_camera_settings",  # Configure camera parameters
        "admin_camera_functions",  # Administrative camera operations
        "full_admin_access",  # Complete administrative access
    ]

    created_capabilities = []

    for capability_name in camera_capabilities:
        # Check if capability already exists
        existing_capability = (
            db.query(Capability).filter(Capability.name == capability_name).first()
        )
        if existing_capability:
            print(f"✅ Camera capability '{capability_name}' already exists")
            created_capabilities.append(existing_capability)
            continue

        # Create camera capability
        camera_capability = Capability(name=capability_name)
        db.add(camera_capability)
        created_capabilities.append(camera_capability)
        print(f"✅ Created camera capability: {capability_name}")

    db.commit()
    for cap in created_capabilities:
        db.refresh(cap)

    print(f"✅ Created {len(created_capabilities)} camera capabilities")
    return created_capabilities


def get_or_create_camera_role(db: Session):
    """Get or create a camera role."""

    # Check if camera role already exists
    existing_role = db.query(Role).filter(Role.name == "camera_user").first()
    if existing_role:
        print("✅ Camera role already exists")
        return existing_role

    # Create camera role
    camera_role = Role(name="camera_user")
    db.add(camera_role)
    db.commit()
    db.refresh(camera_role)

    print("✅ Created camera role")
    return camera_role


def assign_capabilities_to_role(db: Session, role: Role, capabilities: list):
    """Assign camera capabilities to camera role."""

    for capability in capabilities:
        # Check if role-capability assignment already exists
        existing_assignment = (
            db.query(RoleCapability)
            .filter(
                RoleCapability.role_id == role.id,
                RoleCapability.capability_id == capability.id,
            )
            .first()
        )
        if existing_assignment:
            print(
                f"✅ Capability '{capability.name}' already assigned to role '{role.name}'"
            )
            continue

        # Create role-capability assignment
        role_capability = RoleCapability(role_id=role.id, capability_id=capability.id)
        db.add(role_capability)
        print(f"✅ Assigned capability '{capability.name}' to role '{role.name}'")

    db.commit()
    print("✅ All camera capabilities assigned to camera role")


def assign_role_to_user(db: Session, role: Role, user_email: str):
    """Assign camera role to specified user."""

    # Find user by email
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        print(f"❌ User with email '{user_email}' not found")
        return False

    # Check if user-role assignment already exists
    existing_assignment = (
        db.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == role.id)
        .first()
    )
    if existing_assignment:
        print(f"✅ Role '{role.name}' already assigned to user '{user_email}'")
        return True

    # Create user-role assignment
    user_role = UserRole(user_id=user.id, role_id=role.id)
    db.add(user_role)
    db.commit()

    print(f"✅ Assigned role '{role.name}' to user '{user_email}'")
    return True


def verify_user_capabilities(db: Session, user_email: str):
    """Verify that user has camera capabilities."""

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        print(f"❌ User '{user_email}' not found")
        return

    print(f"\n🔍 User capabilities for '{user_email}':")
    print(f"User ID: {user.id}")

    # Get user roles
    user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    print(f"Roles ({len(user_roles)}):")

    user_capabilities = set()
    for user_role in user_roles:
        role = user_role.role
        print(f"  - {role.name}")

        # Get role capabilities
        role_capabilities = (
            db.query(RoleCapability).filter(RoleCapability.role_id == role.id).all()
        )
        for role_capability in role_capabilities:
            capability = role_capability.capability
            user_capabilities.add(capability.name)

    print(f"Capabilities ({len(user_capabilities)}):")
    for capability in sorted(user_capabilities):
        print(f"  - {capability}")

    return user_capabilities


def main():
    """Main function to set up camera capabilities."""

    print("🎥 PPL Meta Node - Camera Capabilities Setup")
    print("=" * 50)

    # Create database session
    db = SessionLocal()

    try:
        # 1. Create camera capabilities
        print("\n1. Creating camera capabilities...")
        camera_capabilities = create_camera_capabilities(db)

        # 2. Create or get camera role
        print("\n2. Creating camera role...")
        camera_role = get_or_create_camera_role(db)

        # 3. Assign capabilities to role
        print("\n3. Assigning capabilities to role...")
        assign_capabilities_to_role(db, camera_role, camera_capabilities)

        # 4. Assign role to test user
        print("\n4. Assigning camera role to test user...")
        test_user_email = "fresh.user@example.com"
        assign_role_to_user(db, camera_role, test_user_email)

        # 5. Verify user capabilities
        print("\n5. Verifying user capabilities...")
        verify_user_capabilities(db, test_user_email)

        print("\n🎉 Camera capabilities setup completed successfully!")
        print(
            "\nThe test user can now authenticate with Node service and access Camera service endpoints."
        )

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    main()
