#!/usr/bin/env python3
    "ppl_media_db": {
        "host": "localhost", 
        "port": 5432,
        "database": "ppl_media_db",
        "user": "nickadmin",
        "password": "change-this-password",
    }ar face detection data from all databases.
This script will:
1. Clear all face detection records from vision service
2. Reset media face counts to 0 in media service
3. Set has_stored_faces to false for specific media
"""

import asyncio
import sys

import asyncpg

# Database configurations
DATABASES = {
    "ppl_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_db",
        "user": "nickadmin",
        "password": "change-this-password",
    },
    "ppl_media_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_media_db",
        "user": "postgres",
        "password": "postgres",
    },
}

# Target media ID
TARGET_MEDIA_ID = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"


async def clear_face_data():
    """Clear all face detection data from all databases."""

    print("🧹 PPL Meta Platform - Face Data Cleanup Script")
    print("=" * 50)

    for db_name, config in DATABASES.items():
        print(f"\n🔌 Connecting to {db_name}...")

        try:
            conn = await asyncpg.connect(**config)

            # List all tables to see what exists
            tables = await conn.fetch(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            )

            print(f"📊 Tables in {db_name}: {[t['table_name'] for t in tables]}")

            if db_name == "ppl_media_db":
                # Clear face-related data from media service
                await clear_media_face_data(conn)
            else:
                # Check for any face/vision tables in other databases
                face_tables = [
                    t["table_name"] for t in tables if "face" in t["table_name"].lower()
                ]
                if face_tables:
                    print(f"🔍 Found face tables: {face_tables}")
                    for table in face_tables:
                        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                        if count > 0:
                            await conn.execute(f"DELETE FROM {table}")
                            print(f"✅ Cleared {count} records from {table}")

            await conn.close()
            print(f"✅ Completed cleanup for {db_name}")

        except Exception as e:
            print(f"❌ Error with {db_name}: {e}")
            continue


async def clear_media_face_data(conn):
    """Clear face detection data from media service database."""

    # Check if media table exists and has face-related columns
    columns = await conn.fetch(
        """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'media' AND table_schema = 'public'
        ORDER BY column_name
    """
    )

    column_names = [c["column_name"] for c in columns]
    print(f"📋 Media table columns: {column_names}")

    # Look for face-related columns
    face_columns = [col for col in column_names if "face" in col.lower()]

    if face_columns:
        print(f"🎯 Found face-related columns: {face_columns}")

        # Reset face data for target media
        if "total_faces" in face_columns:
            await conn.execute(
                """
                UPDATE media 
                SET total_faces = 0 
                WHERE uuid = $1
            """,
                TARGET_MEDIA_ID,
            )
            print(f"✅ Reset total_faces for media {TARGET_MEDIA_ID}")

        if "has_stored_faces" in face_columns:
            await conn.execute(
                """
                UPDATE media 
                SET has_stored_faces = false 
                WHERE uuid = $1
            """,
                TARGET_MEDIA_ID,
            )
            print(f"✅ Reset has_stored_faces for media {TARGET_MEDIA_ID}")

        # Reset for all media if requested
        print("🔄 Resetting face data for ALL media...")
        face_update_columns = []
        if "total_faces" in face_columns:
            face_update_columns.append("total_faces = 0")
        if "has_stored_faces" in face_columns:
            face_update_columns.append("has_stored_faces = false")

        if face_update_columns:
            update_query = f"UPDATE media SET {', '.join(face_update_columns)}"
            result = await conn.execute(update_query)
            print(f"✅ Updated all media records: {result}")
    else:
        print("ℹ️  No face-related columns found in media table")


async def main():
    """Main function."""
    await clear_face_data()
    print("\n🎉 Face data cleanup completed!")
    print("You can now test face detection with fresh data.")


if __name__ == "__main__":
    asyncio.run(main())
