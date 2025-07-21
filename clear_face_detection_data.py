#!/usr/bin/env python3
"""
PPL Meta Platform - Clear Face Detection Data Script
Systematically clears all face detection data from the database and resets media face flags.
"""

import json
import os
import sqlite3
from pathlib import Path


def get_database_path():
    """Get the correct database path for the PPL Meta platform."""
    # Try multiple possible locations
    possible_paths = [
        "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/ppl_meta.db",
        "/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta.db",
        "./ppl-meta-node/ppl_meta.db",
        "./ppl_meta.db",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        f"Database not found in any of the expected locations: {possible_paths}"
    )


def clear_face_detection_data():
    """Clear all face detection data and reset media flags."""

    try:
        db_path = get_database_path()
        print(f"🔍 Found database at: {db_path}")

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\n🧹 Starting systematic face detection data cleanup...")

        # 1. Get count of existing face detection records
        cursor.execute("SELECT COUNT(*) FROM faces")
        face_count = cursor.fetchone()[0]
        print(f"📊 Found {face_count} face detection records to clear")

        # 2. Get count of media with face flags
        cursor.execute(
            "SELECT COUNT(*) FROM media WHERE has_faces = 1 OR face_detection_completed = 1"
        )
        media_with_faces_count = cursor.fetchone()[0]
        print(
            f"📊 Found {media_with_faces_count} media records with face detection flags to reset"
        )

        # 3. Clear all face detection records
        cursor.execute("DELETE FROM faces")
        deleted_faces = cursor.rowcount
        print(f"🗑️  Deleted {deleted_faces} face detection records")

        # 4. Reset all media face detection flags
        cursor.execute(
            """
            UPDATE media 
            SET has_faces = 0, 
                face_detection_completed = 0,
                has_stored_faces = 0
            WHERE has_faces = 1 OR face_detection_completed = 1
        """
        )
        reset_media = cursor.rowcount
        print(f"🔄 Reset face detection flags for {reset_media} media records")

        # 5. Specifically update the test video
        test_media_id = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
        cursor.execute(
            """
            UPDATE media 
            SET has_faces = 0, 
                face_detection_completed = 0,
                has_stored_faces = 0
            WHERE uuid = ?
        """,
            (test_media_id,),
        )

        if cursor.rowcount > 0:
            print(f"✅ Specifically reset test video {test_media_id}")
        else:
            print(f"⚠️  Test video {test_media_id} not found in database")

        # 6. Show final state for test video
        cursor.execute(
            """
            SELECT uuid, filename, has_faces, face_detection_completed, has_stored_faces 
            FROM media 
            WHERE uuid = ?
        """,
            (test_media_id,),
        )

        test_video = cursor.fetchone()
        if test_video:
            uuid, filename, has_faces, face_completed, has_stored = test_video
            print(f"📹 Test video status:")
            print(f"   UUID: {uuid}")
            print(f"   Filename: {filename}")
            print(f"   has_faces: {has_faces}")
            print(f"   face_detection_completed: {face_completed}")
            print(f"   has_stored_faces: {has_stored}")

        # 7. Commit all changes
        conn.commit()
        print("\n✅ Database cleanup completed successfully!")

        # 8. Verify cleanup
        cursor.execute("SELECT COUNT(*) FROM faces")
        remaining_faces = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM media WHERE has_faces = 1 OR face_detection_completed = 1"
        )
        remaining_media_flags = cursor.fetchone()[0]

        print(f"🔍 Verification:")
        print(f"   Remaining face records: {remaining_faces}")
        print(f"   Remaining media with face flags: {remaining_media_flags}")

        if remaining_faces == 0 and remaining_media_flags == 0:
            print(
                "🎉 Perfect cleanup! Database is ready for fresh face detection testing."
            )
        else:
            print("⚠️  Some data may still remain. Check database manually.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if "conn" in locals():
            conn.close()
            print("🔌 Database connection closed")

    return True


def show_database_schema():
    """Show relevant database schema for debugging."""
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\n📋 Database Schema Information:")

        # Show faces table schema
        cursor.execute("PRAGMA table_info(faces)")
        faces_schema = cursor.fetchall()
        print("\n🔍 Faces table columns:")
        for column in faces_schema:
            print(f"   {column[1]} ({column[2]})")

        # Show media table relevant columns
        cursor.execute("PRAGMA table_info(media)")
        media_schema = cursor.fetchall()
        print("\n📁 Media table columns (face-related):")
        face_related_columns = [col for col in media_schema if "face" in col[1].lower()]
        for column in face_related_columns:
            print(f"   {column[1]} ({column[2]})")

        conn.close()

    except Exception as e:
        print(f"❌ Error showing schema: {e}")


if __name__ == "__main__":
    print("🧹 PPL Meta Platform - Face Detection Data Cleanup")
    print("=" * 60)

    # Show schema for reference
    show_database_schema()

    # Perform cleanup
    success = clear_face_detection_data()

    if success:
        print("\n🎯 READY FOR TESTING!")
        print("=" * 60)
        print("✅ Frame interval set to 1 (maximum efficiency)")
        print("✅ All face detection data cleared from database")
        print("✅ Test video 170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e reset")
        print("✅ Ready for hot reload in Flutter")
        print("\n🚀 Next steps:")
        print("   1. Hot reload Flutter frontend")
        print("   2. Navigate to Gallery and click test video")
        print("   3. Observe frame-by-frame face detection efficiency")
    else:
        print("\n❌ Cleanup failed. Check error messages above.")
