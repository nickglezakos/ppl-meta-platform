#!/usr/bin/env python3
"""
Clear face detection data from all PostgreSQL databases.
This script will:
1. Clear all face detection records from vision service PostgreSQL database
2. Reset media face counts to 0 in media service PostgreSQL database
3. Set has_stored_faces to false for specific media
4. Update target media with fresh processing status
"""

import asyncio
import logging

import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
    "ppl_gateway_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_gateway_db",
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
    "ppl_orchestrator_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_orchestrator_db",
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
    "ppl_vision_db": {
        "host": "localhost",
        "port": 5432,
        "database": "ppl_vision_db",
        "user": "nickgklezakos",
        "password": "change-this-password",
    },
}

# Target media ID
TARGET_MEDIA_ID = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"


async def clear_face_data():
    """Clear all face detection data from PostgreSQL databases."""

    print("🧹 PPL Meta Platform - PostgreSQL Face Data Cleanup Script")
    print("=" * 60)

    for db_name, config in DATABASES.items():
        print(f"\n🔌 Connecting to PostgreSQL database: {db_name}...")

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

            table_names = [t["table_name"] for t in tables]
            print(f"📊 Tables in {db_name}: {table_names}")

            if db_name == "ppl_media_db":
                # Clear face-related data from media service
                await clear_media_face_data(conn)
            elif db_name == "ppl_vision_db":
                # Clear vision service face detection data
                await clear_vision_face_data(conn)
            else:
                # Check for any face/vision tables in other databases
                face_tables = [t for t in table_names if "face" in t.lower()]
                if face_tables:
                    print(f"🔍 Found face tables: {face_tables}")
                    for table in face_tables:
                        count_q = f"SELECT COUNT(*) FROM {table}"
                        count = await conn.fetchval(count_q)
                        if count > 0:
                            await conn.execute(f"DELETE FROM {table}")
                            print(f"✅ Cleared {count} records from {table}")
                        else:
                            print(f"ℹ️  Table {table} is already empty")

            await conn.close()
            print(f"✅ Completed cleanup for {db_name}")

        except asyncpg.exceptions.InvalidCatalogNameError:
            print(f"⚠️  Database {db_name} does not exist - skipping")
        except asyncpg.PostgresConnectionError as e:
            print(f"❌ Connection failed for {db_name}: {e}")
        except asyncpg.PostgresError as e:
            print(f"❌ PostgreSQL error with {db_name}: {e}")
        except Exception as e:
            print(f"❌ Unexpected error with {db_name}: {e}")
            continue


async def clear_vision_face_data(conn):
    """Clear face detection data from vision service PostgreSQL database."""

    print("🎯 Clearing vision service face detection data...")

    # Clear face detections table
    face_count = await conn.fetchval("SELECT COUNT(*) FROM face_detections")
    if face_count > 0:
        await conn.execute("DELETE FROM face_detections")
        print(f"✅ Cleared {face_count} face detection records")
    else:
        print("ℹ️  No face detection records to clear")

    # Clear media records table
    media_count = await conn.fetchval("SELECT COUNT(*) FROM media_records")
    if media_count > 0:
        await conn.execute("DELETE FROM media_records")
        print(f"✅ Cleared {media_count} media records")
    else:
        print("ℹ️  No media records to clear")

    # Reset sequences if they exist
    try:
        await conn.execute("SELECT setval('face_detections_id_seq', 1, false)")
        await conn.execute("SELECT setval('media_records_id_seq', 1, false)")
        print("✅ Reset PostgreSQL sequences")
    except asyncpg.UndefinedTableError:
        print("ℹ️  No sequences to reset (using TEXT IDs)")

    print("🎯 Vision service cleanup completed")


async def clear_media_face_data(conn):
    """Clear face detection data from media service PostgreSQL database."""

    print("🎯 Clearing media service face-related data...")

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

        # Reset face data for target media specifically
        if "total_faces" in face_columns:
            result = await conn.execute(
                """
                UPDATE media
                SET total_faces = 0
                WHERE uuid = $1
            """,
                TARGET_MEDIA_ID,
            )
            print(
                f"✅ Reset total_faces for target media " f"{TARGET_MEDIA_ID}: {result}"
            )

        if "has_stored_faces" in face_columns:
            result = await conn.execute(
                """
                UPDATE media
                SET has_stored_faces = false
                WHERE uuid = $1
            """,
                TARGET_MEDIA_ID,
            )
            print(
                f"✅ Reset has_stored_faces for target media "
                f"{TARGET_MEDIA_ID}: {result}"
            )

        # Update processing status to allow re-processing
        if "processing_status" in column_names:
            result = await conn.execute(
                """
                UPDATE media
                SET processing_status = 'pending'
                WHERE uuid = $1
            """,
                TARGET_MEDIA_ID,
            )
            print(
                f"✅ Reset processing_status for target media "
                f"{TARGET_MEDIA_ID}: {result}"
            )

        # Reset for all media if requested (optional - uncomment if needed)
        print("🔄 Resetting face data for ALL media...")
        face_update_columns = []
        if "total_faces" in face_columns:
            face_update_columns.append("total_faces = 0")
        if "has_stored_faces" in face_columns:
            face_update_columns.append("has_stored_faces = false")
        if "processing_status" in column_names:
            face_update_columns.append("processing_status = 'pending'")

        if face_update_columns:
            update_query = f"UPDATE media SET {', '.join(face_update_columns)}"
            result = await conn.execute(update_query)
            print(f"✅ Updated all media records: {result}")

            # Show count of affected records
            total_media = await conn.fetchval("SELECT COUNT(*) FROM media")
            print(f"📊 Total media records affected: {total_media}")
    else:
        print("ℹ️  No face-related columns found in media table")

    # Check for specific target media existence
    target_exists = await conn.fetchval(
        "SELECT COUNT(*) FROM media WHERE uuid = $1", TARGET_MEDIA_ID
    )
    if target_exists:
        print(f"✅ Target media {TARGET_MEDIA_ID} exists and has been reset")
    else:
        print(f"⚠️  Target media {TARGET_MEDIA_ID} not found in database")

    print("🎯 Media service cleanup completed")


async def main():
    """Main function to clear face detection data from PostgreSQL databases."""
    print("🚀 Starting PostgreSQL Face Data Cleanup...")
    print(f"🎯 Target Media ID: {TARGET_MEDIA_ID}")
    print("")

    await clear_face_data()

    print("\n🎉 PostgreSQL Face data cleanup completed!")
    print("=" * 60)
    print("📝 Summary:")
    print("  • Vision service face detections cleared")
    print("  • Media service face counts reset")
    print("  • Target media processing status reset to 'pending'")
    print("  • All media face flags reset")
    print("")
    print("✅ You can now test face detection with fresh data")
    print("   and frame_interval=1 for maximum efficiency")
    print("🌐 Frontend available at: http://localhost:3000")
    print("🔍 Vision service health: http://localhost:8003/health")


if __name__ == "__main__":
    asyncio.run(main())
