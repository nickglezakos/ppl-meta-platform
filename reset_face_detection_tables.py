#!/usr/bin/env python3
"""
Reset Face Detection Tables Script
Drops and recreates all face detection related tables to clear stored data
and allow re-processing with new confidence threshold (0.5 instead of 1.0)
"""

import os
import sqlite3
from pathlib import Path


def reset_face_detection_tables():
    """Drop and recreate face detection tables"""

    # Find the Vision service database
    vision_db_path = (
        "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/vision_service.db"
    )

    if not os.path.exists(vision_db_path):
        print(f"❌ Vision database not found at: {vision_db_path}")
        print("Searching for database file...")

        # Search for the database file
        vision_dir = Path(
            "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision"
        )
        db_files = list(vision_dir.glob("*.db"))

        if db_files:
            vision_db_path = str(db_files[0])
            print(f"✅ Found database at: {vision_db_path}")
        else:
            print("❌ No database files found in vision service directory")
            return False

    try:
        # Connect to the database
        conn = sqlite3.connect(vision_db_path)
        cursor = conn.cursor()

        print(f"🗄️  Connected to database: {vision_db_path}")

        # Check current data before dropping
        cursor.execute("SELECT COUNT(*) FROM face_detections")
        face_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT media_id) FROM face_detections")
        media_count = cursor.fetchone()[0]

        print(
            f"📊 Current data: {face_count} face detections across {media_count} media files"
        )

        # Drop tables in reverse order of dependencies
        print("\n🗑️  Dropping tables...")

        tables_to_drop = ["face_detections", "processing_jobs", "media_records"]

        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"   ✅ Dropped table: {table}")
            except Exception as e:
                print(f"   ⚠️  Could not drop {table}: {e}")

        # Recreate tables with same schema
        print("\n🏗️  Recreating tables...")

        # Media records table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS media_records (
                media_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                original_filename TEXT,
                processed_filename TEXT,
                media_type TEXT,
                file_size INTEGER,
                duration REAL,
                video_width INTEGER,
                video_height INTEGER,
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        print("   ✅ Created table: media_records")

        # Face detections table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS face_detections (
                id TEXT PRIMARY KEY,
                media_id TEXT NOT NULL,
                frame_number INTEGER,
                timestamp REAL,
                bbox_x1 INTEGER NOT NULL,
                bbox_y1 INTEGER NOT NULL,
                bbox_x2 INTEGER NOT NULL,
                bbox_y2 INTEGER NOT NULL,
                confidence REAL NOT NULL,
                method TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_records (media_id)
            )
            """
        )
        print("   ✅ Created table: face_detections")

        # Processing jobs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processing_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'queued',
                total_media INTEGER DEFAULT 0,
                processed_media INTEGER DEFAULT 0,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        print("   ✅ Created table: processing_jobs")

        # Commit changes
        conn.commit()
        conn.close()

        print("\n🎉 Successfully reset face detection tables!")
        print("📝 All stored face detection data has been cleared")
        print("🔄 Videos will be re-processed with new confidence threshold")

        return True

    except Exception as e:
        print(f"❌ Error resetting tables: {e}")
        return False


if __name__ == "__main__":
    print("🧹 Face Detection Tables Reset")
    print("=" * 50)
    print("This script will:")
    print(
        "1. Drop all face detection tables (face_detections, media_records, processing_jobs)"
    )
    print("2. Recreate empty tables with same schema")
    print("3. Clear all stored face detection data")
    print("4. Force re-processing with new confidence threshold")
    print()

    confirm = input("Do you want to continue? (y/N): ")

    if confirm.lower() in ["y", "yes"]:
        success = reset_face_detection_tables()
        if success:
            print("\n✅ Tables reset successfully!")
            print(
                "🎬 You can now test video face detection with updated confidence threshold"
            )
        else:
            print("\n❌ Failed to reset tables")
    else:
        print("❌ Operation cancelled")
