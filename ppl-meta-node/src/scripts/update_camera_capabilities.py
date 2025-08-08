#!/usr/bin/env python3
"""
Script to update camera capabilities in the Node service to match Camera service permission format.
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
from src.models.role import Capability


def update_camera_capabilities(db: Session):
    """Update camera capabilities to match Camera service permission format."""

    # Mapping from old format to new format
    capability_mapping = {
        "detect_cameras": "cameras:detect",
        "view_cameras": "cameras:view",
        "connect_camera": "cameras:connect",
        "disconnect_camera": "cameras:disconnect",
        "view_stream": "cameras:stream:view",
        "start_stream": "cameras:stream:start",
        "stop_stream": "cameras:stream:stop",
        "capture_snapshot": "cameras:record:start",  # Assuming snapshot is like recording
        "manage_sessions": "cameras:sessions:manage",
        "view_capabilities": "cameras:view",  # General view permission
        "admin_disconnect_all": "cameras:admin",
        "view_active_connections": "cameras:view",
        "manage_camera_settings": "cameras:settings:update",
        "admin_camera_functions": "cameras:admin",
        "full_admin_access": "cameras:admin",
    }

    updated_count = 0

    for old_name, new_name in capability_mapping.items():
        # Find the old capability
        old_capability = (
            db.query(Capability).filter(Capability.name == old_name).first()
        )
        if old_capability:
            # Check if new capability already exists
            existing_new = (
                db.query(Capability).filter(Capability.name == new_name).first()
            )
            if not existing_new:
                # Update the old capability name
                old_capability.name = new_name
                updated_count += 1
                print(f"✅ Updated capability: {old_name} → {new_name}")
            else:
                print(
                    f"⚠️ New capability {new_name} already exists, skipping {old_name}"
                )
        else:
            print(f"❌ Old capability {old_name} not found")

    # Add any missing essential camera permissions
    essential_permissions = [
        "cameras:detect",
        "cameras:view",
        "cameras:connect",
        "cameras:disconnect",
        "cameras:stream:start",
        "cameras:stream:stop",
        "cameras:stream:view",
        "cameras:admin",
        "cameras:configure",
        "cameras:settings:update",
    ]

    for permission in essential_permissions:
        existing = db.query(Capability).filter(Capability.name == permission).first()
        if not existing:
            new_capability = Capability(name=permission)
            db.add(new_capability)
            print(f"✅ Added missing capability: {permission}")

    db.commit()
    print(f"✅ Updated {updated_count} capabilities and added missing ones")


def main():
    """Main function to update camera capabilities."""

    print("🔧 PPL Meta Node - Camera Capabilities Format Update")
    print("=" * 55)

    # Create database session
    db = SessionLocal()

    try:
        print("\n1. Updating camera capabilities to match Camera service format...")
        update_camera_capabilities(db)

        print("\n🎉 Camera capabilities update completed successfully!")
        print("\nCapabilities now match Camera service permission format.")

    except Exception as e:
        print(f"❌ Error during update: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    main()
