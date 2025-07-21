#!/usr/bin/env python3
"""
Clear face detection data from the database.
This script will:
1. Clear all face detection records
2. Reset media face counts to 0
3. Set has_stored_faces to false
"""

import asyncio
import sys
from pathlib import Path

import asyncpg

# Database configuration (standard PostgreSQL)
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ppl_db",
    "user": "nickadmin",
    "password": "change-this-password",
}


async def clear_face_data():
    """Clear all face detection data from the database."""
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        # Start transaction
        async with conn.transaction():
            print("🗑️  Clearing face detection data...")

            # Clear all face detections
            face_count = await conn.fetchval("SELECT COUNT(*) FROM face_detections")
            print(f"📊 Found {face_count} face detection records to clear")

            await conn.execute("DELETE FROM face_detections")
            print("✅ Cleared all face detection records")

            # Reset media face counts
            media_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM media 
                WHERE total_faces > 0 OR has_stored_faces = true
            """
            )
            print(f"📊 Found {media_count} media records with face data to reset")

            await conn.execute(
                """
                UPDATE media 
                SET total_faces = 0, 
                    has_stored_faces = false,
                    face_processing_status = 'pending'
                WHERE total_faces > 0 OR has_stored_faces = true
            """
            )
            print("✅ Reset all media face counts and flags")

            # Verify cleanup
            remaining_faces = await conn.fetchval(
                "SELECT COUNT(*) FROM face_detections"
            )
            remaining_media_with_faces = await conn.fetchval(
                """
                SELECT COUNT(*) FROM media 
                WHERE total_faces > 0 OR has_stored_faces = true
            """
            )

            print(f"🔍 Verification:")
            print(f"   - Remaining face detections: {remaining_faces}")
            print(f"   - Media with face flags: {remaining_media_with_faces}")

            if remaining_faces == 0 and remaining_media_with_faces == 0:
                print("🎉 Face data cleanup completed successfully!")
            else:
                print("⚠️  Warning: Some face data may still remain")

        await conn.close()
        print("🔌 Database connection closed")

    except Exception as e:
        print(f"❌ Error clearing face data: {e}")
        sys.exit(1)


async def main():
    """Main function."""
    print("🧹 PPL Meta Platform - Face Data Cleanup Script")
    print("=" * 50)

    await clear_face_data()

    print("\n✅ Face data cleanup completed!")
    print("You can now test face detection with fresh data.")


if __name__ == "__main__":
    asyncio.run(main())
