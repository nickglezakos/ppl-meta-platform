"""
Migration script to convert existing mobile cameras to UUID v4 system.

This script:
1. Generates new UUID v4 for each mobile camera's device_id
2. Sets hardware_identifier from manufacturer+model+serial (or old device_id as fallback)
3. Preserves all other camera data
4. Updates collections to reference new UUIDs (if applicable)

Run this AFTER applying database migrations 001 and 002.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import get_config
from src.models.camera import Camera, CameraType
from src.services.device_id_service import generate_uuid
from datetime import datetime

def migrate_mobile_cameras_to_uuid():
    """Migrate existing mobile cameras to use server-generated UUIDs."""
    
    config = get_config()
    engine = create_engine(config.DATABASE_URL, echo=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Find all mobile cameras
        mobile_cameras = (
            db.query(Camera)
            .filter(Camera.camera_type == CameraType.MOBILE)
            .all()
        )
        
        print(f"\n📱 Found {len(mobile_cameras)} mobile cameras to migrate\n")
        
        migrated_count = 0
        skipped_count = 0
        
        for camera in mobile_cameras:
            old_device_id = camera.device_id
            
            # Check if already migrated (device_id is already UUID v4 format)
            if len(old_device_id) == 36 and old_device_id.count('-') == 4:
                print(f"⏭️  Skipping {camera.name} - already has UUID format: {old_device_id}")
                skipped_count += 1
                continue
            
            # Generate new UUID
            new_uuid = generate_uuid()
            
            # Set hardware_identifier if not already set
            if not camera.hardware_identifier:
                if camera.manufacturer and camera.model and camera.serial_number:
                    hardware_id = f"{camera.manufacturer}_{camera.model}_{camera.serial_number}"
                else:
                    # Fallback: use old device_id as hardware_identifier
                    hardware_id = old_device_id
                
                camera.hardware_identifier = hardware_id
                print(f"  → Set hardware_identifier: {hardware_id}")
            
            # Update device_id to new UUID
            camera.device_id = new_uuid
            
            print(f"✅ Migrated: {camera.name}")
            print(f"  → Old device_id: {old_device_id}")
            print(f"  → New UUID: {new_uuid}")
            print(f"  → Hardware ID: {camera.hardware_identifier}\n")
            
            migrated_count += 1
        
        # Commit all changes
        db.commit()
        
        print("=" * 60)
        print(f"✅ Migration complete!")
        print(f"   Migrated: {migrated_count} cameras")
        print(f"   Skipped: {skipped_count} cameras (already migrated)")
        print(f"   Total: {len(mobile_cameras)} mobile cameras")
        print("=" * 60)
        
        # Print instructions for mobile app update
        if migrated_count > 0:
            print("\n⚠️  IMPORTANT: Mobile app update required!")
            print("   1. Mobile apps must fetch new UUID on next connection")
            print("   2. Apps will detect existing camera via hardware_identifier")
            print("   3. Server returns new UUID in registration response")
            print("   4. App stores UUID in SharedPreferences for future API calls\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def verify_migration():
    """Verify that migration was successful."""
    
    config = get_config()
    engine = create_engine(config.DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Check mobile cameras
        mobile_cameras = (
            db.query(Camera)
            .filter(Camera.camera_type == CameraType.MOBILE)
            .all()
        )
        
        issues = []
        
        for camera in mobile_cameras:
            # Check UUID format
            if len(camera.device_id) != 36 or camera.device_id.count('-') != 4:
                issues.append(f"❌ {camera.name}: Invalid UUID format: {camera.device_id}")
            
            # Check hardware_identifier is set
            if not camera.hardware_identifier:
                issues.append(f"⚠️  {camera.name}: Missing hardware_identifier")
        
        if issues:
            print("\n⚠️  Verification found issues:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print(f"\n✅ Verification passed! All {len(mobile_cameras)} mobile cameras migrated correctly.")
            return True
            
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Mobile Camera UUID Migration Script")
    print("=" * 60)
    print("\nThis script will:")
    print(" 1. Convert mobile camera device_ids to UUID v4 format")
    print(" 2. Set hardware_identifier for device detection")
    print(" 3. Preserve all camera data and relationships")
    print("\n⚠️  Make sure to backup your database before running!")
    
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\n🚀 Starting migration...\n")
        migrate_mobile_cameras_to_uuid()
        
        print("\n🔍 Running verification...\n")
        verify_migration()
    else:
        print("\n❌ Migration cancelled.")
