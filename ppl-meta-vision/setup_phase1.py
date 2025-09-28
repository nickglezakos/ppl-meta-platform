#!/usr/bin/env python3
"""
PPL Thread Workflow - Phase 1 Setup Script
Simple setup script to initialize the person objects database schema.

Usage:
    python setup_phase1.py [--rollback]

Options:
    --rollback    Rollback the migration (removes all person objects tables)
"""

import asyncio
import logging
import os
import sys
from argparse import ArgumentParser

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import psycopg2
from database.person_objects_migrations import PersonObjectsMigration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_connection():
    """Get database connection."""
    conn_params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "ppl_vision_db"),
        "user": os.getenv("DB_USER", "nickgklezakos"),
        "password": os.getenv("DB_PASSWORD", "change-this-password"),
    }

    try:
        connection = psycopg2.connect(**conn_params)
        connection.autocommit = True
        logger.info("✅ Connected to database")
        return connection
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)


async def setup_phase1():
    """Setup Phase 1: Person Objects Database Schema."""
    logger.info("🚀 PPL Thread Workflow - Phase 1 Setup")
    logger.info("Setting up person objects database schema...")

    connection = get_database_connection()
    migration = PersonObjectsMigration(connection)

    try:
        # Execute migration
        success = await migration.migrate_schema()

        if success:
            logger.info("✅ Phase 1 setup completed successfully!")

            # Show migration info
            info = await migration.get_migration_info()
            logger.info(f"Migration applied at: {info.get('applied_at')}")
            logger.info(f"Schema version: {info.get('version')}")

            logger.info("\nCreated tables:")
            for table in [
                "person_objects",
                "person_face_mappings",
                "person_workflows",
                "face_crops",
            ]:
                logger.info(f"  ✅ {table}")

            logger.info("\n🎯 Next Steps:")
            logger.info("  1. Run test: python test_phase1_person_objects_schema.py")
            logger.info("  2. Proceed to Phase 2: Core Face Grouping Engine")
        else:
            logger.error("❌ Phase 1 setup failed!")
            return False

    except Exception as e:
        logger.error(f"❌ Setup error: {e}")
        return False
    finally:
        connection.close()

    return True


async def rollback_phase1():
    """Rollback Phase 1: Remove person objects schema."""
    logger.warning("🔄 PPL Thread Workflow - Phase 1 Rollback")
    logger.warning("This will remove all person objects tables and data!")

    confirm = input("Are you sure you want to continue? (yes/no): ")
    if confirm.lower() != "yes":
        logger.info("Rollback cancelled")
        return

    connection = get_database_connection()
    migration = PersonObjectsMigration(connection)

    try:
        success = await migration.rollback_migration()

        if success:
            logger.info("✅ Phase 1 rollback completed successfully!")
        else:
            logger.error("❌ Phase 1 rollback failed!")

    except Exception as e:
        logger.error(f"❌ Rollback error: {e}")
    finally:
        connection.close()


async def main():
    """Main entry point."""
    parser = ArgumentParser(description="PPL Thread Workflow Phase 1 Setup")
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback the migration"
    )

    args = parser.parse_args()

    if args.rollback:
        await rollback_phase1()
    else:
        success = await setup_phase1()
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
