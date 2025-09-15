#!/usr/bin/env python3
"""
PPL Meta Vision Service - Database Migration Runner
Migration management for session-based face detection schema

Usage:
    python migration_runner.py apply 001     # Apply migration 001
    python migration_runner.py rollback 001  # Rollback migration 001
    python migration_runner.py status        # Show migration status
    python migration_runner.py verify 001    # Verify migration was applied correctly
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Database migration runner for PPL Meta Vision Service."""

    def __init__(self):
        """Initialize migration runner with database connection."""
        self.connection = None
        self.migrations_dir = os.path.join(os.path.dirname(__file__))
        self.connect_to_database()

    def _get_connection_params(self) -> Dict[str, Any]:
        """Get database connection parameters."""
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "ppl_vision_db"),
            "user": os.getenv("DB_USER", "nickgklezakos"),
            "password": os.getenv("DB_PASSWORD", "change-this-password"),
        }

    def connect_to_database(self):
        """Connect to PostgreSQL database."""
        try:
            conn_params = self._get_connection_params()
            self.connection = psycopg2.connect(**conn_params)
            self.connection.autocommit = True
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            sys.exit(1)

    def ensure_migrations_table(self):
        """Ensure schema_migrations table exists."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(20) PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        checksum TEXT
                    )
                """
                )
            logger.info("Migrations table ready")
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            sys.exit(1)

    def get_migration_file(self, version: str, rollback: bool = False) -> str:
        """Get migration file path."""
        if rollback:
            filename = f"{version}_rollback_session_based_face_detection_schema.sql"
        else:
            filename = f"{version}_session_based_face_detection_schema.sql"

        filepath = os.path.join(self.migrations_dir, filename)

        if not os.path.exists(filepath):
            logger.error(f"Migration file not found: {filepath}")
            sys.exit(1)

        return filepath

    def read_migration_file(self, filepath: str) -> str:
        """Read migration SQL file."""
        try:
            with open(filepath, "r") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Failed to read migration file {filepath}: {e}")
            sys.exit(1)

    def execute_migration(self, sql: str, version: str):
        """Execute migration SQL."""
        try:
            with self.connection.cursor() as cursor:
                # Execute the migration SQL
                cursor.execute(sql)
            logger.info(f"Migration {version} executed successfully")
        except Exception as e:
            logger.error(f"Migration {version} failed: {e}")
            self.connection.rollback()
            sys.exit(1)

    def apply_migration(self, version: str):
        """Apply a migration."""
        logger.info(f"Applying migration {version}...")

        # Check if already applied
        if self.is_migration_applied(version):
            logger.warning(f"Migration {version} is already applied")
            return

        # Get migration file
        migration_file = self.get_migration_file(version)
        sql = self.read_migration_file(migration_file)

        # Execute migration
        self.execute_migration(sql, version)

        logger.info(f"Migration {version} applied successfully")

    def rollback_migration(self, version: str):
        """Rollback a migration."""
        logger.info(f"Rolling back migration {version}...")

        # Check if migration is applied
        if not self.is_migration_applied(version):
            logger.warning(f"Migration {version} is not applied, nothing to rollback")
            return

        # Get rollback file
        rollback_file = self.get_migration_file(version, rollback=True)
        sql = self.read_migration_file(rollback_file)

        # Execute rollback
        self.execute_migration(sql, version)

        logger.info(f"Migration {version} rolled back successfully")

    def is_migration_applied(self, version: str) -> bool:
        """Check if migration is already applied."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT version FROM schema_migrations WHERE version = %s",
                    (version,),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check migration status: {e}")
            return False

    def get_migration_status(self) -> List[Dict[str, Any]]:
        """Get status of all migrations."""
        try:
            with self.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(
                    """
                    SELECT version, description, applied_at, checksum
                    FROM schema_migrations 
                    ORDER BY version
                """
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return []

    def verify_migration(self, version: str):
        """Verify migration was applied correctly."""
        logger.info(f"Verifying migration {version}...")

        if version == "001":
            self._verify_migration_001()
        else:
            logger.warning(f"No verification available for migration {version}")

    def _verify_migration_001(self):
        """Verify migration 001 was applied correctly."""
        verifications = [
            {
                "name": "face_detection_sessions table exists",
                "query": """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'face_detection_sessions' AND table_schema = 'public'
                """,
            },
            {
                "name": "media_processing_status table exists",
                "query": """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'media_processing_status' AND table_schema = 'public'
                """,
            },
            {
                "name": "session_uuid column added to face_detections",
                "query": """
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'face_detections' AND column_name = 'session_uuid'
                """,
            },
            {
                "name": "Required indexes exist",
                "query": """
                    SELECT count(*) as index_count FROM pg_indexes 
                    WHERE tablename IN ('face_detection_sessions', 'face_detections', 'media_processing_status')
                    AND indexname LIKE 'idx_%'
                """,
            },
        ]

        all_passed = True
        for verification in verifications:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(verification["query"])
                    result = cursor.fetchone()

                    if result and result[0]:
                        logger.info(f"✅ {verification['name']}")
                    else:
                        logger.error(f"❌ {verification['name']}")
                        all_passed = False
            except Exception as e:
                logger.error(f"❌ {verification['name']}: {e}")
                all_passed = False

        if all_passed:
            logger.info("🎉 Migration 001 verification PASSED")
        else:
            logger.error("💥 Migration 001 verification FAILED")
            sys.exit(1)

    def show_status(self):
        """Show current migration status."""
        logger.info("Current migration status:")

        migrations = self.get_migration_status()
        if not migrations:
            logger.info("No migrations applied")
            return

        for migration in migrations:
            logger.info(
                f"✅ {migration['version']}: {migration['description']} (applied: {migration['applied_at']})"
            )

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


def main():
    """Main migration runner."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    runner = MigrationRunner()
    runner.ensure_migrations_table()

    try:
        if action == "apply" and len(sys.argv) == 3:
            version = sys.argv[2]
            runner.apply_migration(version)

        elif action == "rollback" and len(sys.argv) == 3:
            version = sys.argv[2]
            runner.rollback_migration(version)

        elif action == "verify" and len(sys.argv) == 3:
            version = sys.argv[2]
            runner.verify_migration(version)

        elif action == "status":
            runner.show_status()

        else:
            print(__doc__)
            sys.exit(1)

    finally:
        runner.close()


if __name__ == "__main__":
    main()
