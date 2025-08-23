#!/usr/bin/env python3
"""
Database cleanup script for duplicate collections.
This connects directly to the media service database.
"""

import os
import sys
from datetime import datetime

# Add the media service to the path
sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def cleanup_database_duplicates():
    """Clean up duplicate collections directly from database."""
    print("🧹 Database cleanup for duplicate collections...")

    # Database connection (same as media service)
    DATABASE_URL = "sqlite:////Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src/media.db"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as db:
        try:
            # Get all collections grouped by name
            query = text(
                """
                SELECT id, name, created_at, created_by
                FROM media_collections 
                ORDER BY name, created_at
            """
            )

            result = db.execute(query)
            collections = result.fetchall()

            print(f"📋 Found {len(collections)} total collections")

            # Group by name and find duplicates
            collections_by_name = {}
            for collection in collections:
                name = collection.name
                if name not in collections_by_name:
                    collections_by_name[name] = []
                collections_by_name[name].append(collection)

            # Find and delete duplicates
            deleted_count = 0
            for name, cols in collections_by_name.items():
                if len(cols) > 1:
                    print(f"\n🔍 Found {len(cols)-1} duplicates for '{name}':")

                    # Keep the first (earliest) one
                    keep = cols[0]
                    duplicates = cols[1:]

                    print(f"   ✅ Keeping: ID {keep.id} (created: {keep.created_at})")

                    for dup in duplicates:
                        print(
                            f"   🗑️  Deleting: ID {dup.id} (created: {dup.created_at})"
                        )

                        # Delete the duplicate
                        delete_query = text(
                            "DELETE FROM media_collections WHERE id = :collection_id"
                        )
                        db.execute(delete_query, {"collection_id": dup.id})
                        deleted_count += 1

            # Commit the changes
            db.commit()

            print(f"\n📊 Database cleanup summary:")
            print(f"   ✅ Duplicates deleted: {deleted_count}")

            # Verify final state
            final_query = text(
                """
                SELECT name, COUNT(*) as count 
                FROM media_collections 
                GROUP BY name 
                ORDER BY name
            """
            )

            final_result = db.execute(final_query)
            final_collections = final_result.fetchall()

            print(f"\n📋 Final collection counts:")
            for collection in final_collections:
                status = "✅" if collection.count == 1 else "⚠️"
                print(f"   {status} {collection.name}: {collection.count}")

        except Exception as e:
            print(f"❌ Database error: {e}")
            db.rollback()


if __name__ == "__main__":
    # Change to media service directory
    os.chdir("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/src")
    cleanup_database_duplicates()
