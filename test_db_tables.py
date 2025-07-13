#!/usr/bin/env python3
"""
Test script to verify database tables and create them manually if needed.
"""

import os
import sys

# Add the media service to Python path
sys.path.insert(0, "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media")

from sqlalchemy import text
from src.database import Base, SessionLocal, engine
from src.models.media import (
    Media,
    MediaCollection,
    MediaCollectionItem,
    MediaDetails,
    MediaShare,
    MediaVariant,
)


def main():
    print("🔍 Testing database connection...")

    # Test basic connection
    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT 1")).fetchone()
            print(f"✅ Database connection successful: {result}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    print("\n📋 Checking existing tables...")
    try:
        with SessionLocal() as session:
            # Check if tables exist
            tables_result = session.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """
            ).fetchall()

            existing_tables = [row[0] for row in tables_result]
            print(f"Existing tables: {existing_tables}")

    except Exception as e:
        print(f"❌ Failed to check tables: {e}")

    print("\n🏗️ Creating tables...")
    try:
        # Force table creation
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")

        # Verify tables were created
        with SessionLocal() as session:
            tables_result = session.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """
            ).fetchall()

            new_tables = [row[0] for row in tables_result]
            print(f"Tables after creation: {new_tables}")

    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
