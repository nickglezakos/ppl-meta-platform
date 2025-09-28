"""
PPL Meta Vision Service - Person Objects Database Migration
Handles database schema migration for PPL Thread person objects functionality.

This module provides migration functionality for:
- Person objects table structure
- Person-to-face mappings
- Person workflow tracking
- Quality analysis and face crops storage
- Database indexes for performance optimization
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class PersonObjectsMigration:
    """Handle database schema migration for person objects functionality."""

    def __init__(self, database_connection):
        """Initialize migration with database connection."""
        self.connection = database_connection

    async def migrate_schema(self) -> bool:
        """
        Execute complete schema migration for person objects tables.

        Creates all necessary tables, indexes, and constraints for:
        - person_objects: Main person entity storage
        - person_face_mappings: Face-to-person relationship mapping
        - person_workflows: Workflow execution tracking
        - face_crops: Face image data for quality analysis

        Returns:
            bool: True if migration successful, False otherwise
        """
        try:
            logger.info("🚀 Starting PPL Thread person objects schema migration...")

            # Check if migration already applied
            if await self._check_migration_status():
                logger.info("✅ Person objects schema already migrated")
                return True

            # Create all tables
            await self._create_person_objects_table()
            await self._create_person_face_mappings_table()
            await self._create_person_workflows_table()
            await self._create_face_crops_table()

            # Create indexes
            await self._create_indexes()

            # Mark migration as complete
            await self._mark_migration_complete()

            logger.info("✅ Person objects schema migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Schema migration failed: {e}")
            await self._rollback_migration()
            return False

    async def _check_migration_status(self) -> bool:
        """Check if migration has been applied."""
        try:
            cursor = self.connection.cursor()

            # Check if main person_objects table exists
            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = 'person_objects' AND table_schema = 'public'
            """
            )

            result = cursor.fetchone()
            cursor.close()

            return result is not None

        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False

    async def _create_person_objects_table(self):
        """Create person objects table (main entities)."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS person_objects (
                person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_uuid TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                face_count INTEGER NOT NULL,
                average_position_x REAL NOT NULL,
                average_position_y REAL NOT NULL,
                quality_score REAL DEFAULT 0.0,
                best_face_id TEXT,
                estimated_age INTEGER,
                distance_from_camera REAL,
                tracking_algorithm TEXT DEFAULT 'percentage_based_tracking',
                tolerance_percent REAL DEFAULT 20.0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """
        )

        cursor.close()
        logger.info("✅ Created person_objects table")

    async def _create_person_face_mappings_table(self):
        """Create person-to-face mappings table."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS person_face_mappings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                person_id UUID NOT NULL,
                face_detection_id TEXT NOT NULL,
                match_type TEXT NOT NULL, -- 'tracked' or 'new_track'
                match_distance REAL DEFAULT 0.0,
                frame_number INTEGER,
                position_x REAL NOT NULL,
                position_y REAL NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (person_id) REFERENCES person_objects(person_id) ON DELETE CASCADE
            )
        """
        )

        cursor.close()
        logger.info("✅ Created person_face_mappings table")

    async def _create_person_workflows_table(self):
        """Create person workflow tracking table."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS person_workflows (
                workflow_id TEXT PRIMARY KEY,
                session_uuid TEXT NOT NULL,
                status TEXT DEFAULT 'processing', -- 'processing', 'completed', 'failed'
                input_face_count INTEGER NOT NULL,
                output_person_count INTEGER DEFAULT 0,
                tolerance_percent REAL DEFAULT 20.0,
                processing_method TEXT DEFAULT 'percentage_based_tracking',
                enable_quality_analysis BOOLEAN DEFAULT true,
                enable_age_detection BOOLEAN DEFAULT true,
                started_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                error_message TEXT,
                metadata JSONB,
                processing_duration_ms INTEGER
            )
        """
        )

        cursor.close()
        logger.info("✅ Created person_workflows table")

    async def _create_face_crops_table(self):
        """Create face crops table for quality analysis."""
        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS face_crops (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                face_detection_id TEXT NOT NULL UNIQUE,
                crop_base64 TEXT,  -- Base64 encoded face crop image
                pre_computed_quality_score REAL,
                crop_width INTEGER,
                crop_height INTEGER,
                extracted_at TIMESTAMP DEFAULT NOW(),
                extraction_method TEXT DEFAULT 'bbox_coordinates'
            )
        """
        )

        cursor.close()
        logger.info("✅ Created face_crops table")

    async def _create_indexes(self):
        """Create indexes for performance optimization."""
        cursor = self.connection.cursor()

        indexes = [
            # Person objects indexes
            (
                "idx_person_objects_session_uuid",
                "CREATE INDEX IF NOT EXISTS idx_person_objects_session_uuid ON person_objects(session_uuid)",
            ),
            (
                "idx_person_objects_workflow_id",
                "CREATE INDEX IF NOT EXISTS idx_person_objects_workflow_id ON person_objects(workflow_id)",
            ),
            (
                "idx_person_objects_quality_score",
                "CREATE INDEX IF NOT EXISTS idx_person_objects_quality_score ON person_objects(quality_score DESC)",
            ),
            # Person face mappings indexes
            (
                "idx_person_face_mappings_person_id",
                "CREATE INDEX IF NOT EXISTS idx_person_face_mappings_person_id ON person_face_mappings(person_id)",
            ),
            (
                "idx_person_face_mappings_face_id",
                "CREATE INDEX IF NOT EXISTS idx_person_face_mappings_face_id ON person_face_mappings(face_detection_id)",
            ),
            (
                "idx_person_face_mappings_frame_number",
                "CREATE INDEX IF NOT EXISTS idx_person_face_mappings_frame_number ON person_face_mappings(frame_number)",
            ),
            # Person workflows indexes
            (
                "idx_person_workflows_session_uuid",
                "CREATE INDEX IF NOT EXISTS idx_person_workflows_session_uuid ON person_workflows(session_uuid)",
            ),
            (
                "idx_person_workflows_status",
                "CREATE INDEX IF NOT EXISTS idx_person_workflows_status ON person_workflows(status)",
            ),
            (
                "idx_person_workflows_started_at",
                "CREATE INDEX IF NOT EXISTS idx_person_workflows_started_at ON person_workflows(started_at DESC)",
            ),
            # Face crops indexes
            (
                "idx_face_crops_face_detection_id",
                "CREATE INDEX IF NOT EXISTS idx_face_crops_face_detection_id ON face_crops(face_detection_id)",
            ),
            (
                "idx_face_crops_quality_score",
                "CREATE INDEX IF NOT EXISTS idx_face_crops_quality_score ON face_crops(pre_computed_quality_score DESC)",
            ),
        ]

        for index_name, index_sql in indexes:
            try:
                cursor.execute(index_sql)
                logger.info(f"✅ Created index: {index_name}")
            except Exception as e:
                logger.warning(f"⚠️ Index creation warning for {index_name}: {e}")

        cursor.close()

    async def _mark_migration_complete(self):
        """Mark migration as complete in database."""
        cursor = self.connection.cursor()

        # Create migrations tracking table if not exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW(),
                version TEXT DEFAULT '1.0.0'
            )
        """
        )

        # Record this migration
        cursor.execute(
            """
            INSERT INTO schema_migrations (migration_name, version) 
            VALUES ('person_objects_migration', '1.0.0')
            ON CONFLICT (migration_name) DO NOTHING
        """
        )

        cursor.close()
        logger.info("✅ Migration marked as complete")

    async def rollback_migration(self) -> bool:
        """
        Rollback person objects schema changes.

        WARNING: This will drop all person objects data!

        Returns:
            bool: True if rollback successful
        """
        try:
            logger.warning("🔄 Starting person objects schema rollback...")

            cursor = self.connection.cursor()

            # Drop tables in reverse dependency order
            tables_to_drop = [
                "person_face_mappings",  # Has foreign key to person_objects
                "person_objects",
                "person_workflows",
                "face_crops",
            ]

            for table in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"✅ Dropped table: {table}")

            # Remove migration record
            cursor.execute(
                """
                DELETE FROM schema_migrations 
                WHERE migration_name = 'person_objects_migration'
            """
            )

            cursor.close()

            logger.info("✅ Person objects schema rollback completed")
            return True

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False

    async def _rollback_migration(self):
        """Internal rollback helper."""
        await self.rollback_migration()

    async def validate_schema(self) -> Dict[str, bool]:
        """
        Validate that all schema components exist and are correct.

        Returns:
            Dict with validation results for each component
        """
        validation_results = {}

        try:
            cursor = self.connection.cursor()

            # Check tables exist
            tables = [
                "person_objects",
                "person_face_mappings",
                "person_workflows",
                "face_crops",
            ]

            for table in tables:
                cursor.execute(
                    """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = %s AND table_schema = 'public'
                """,
                    (table,),
                )

                validation_results[f"table_{table}"] = cursor.fetchone() is not None

            # Check key columns exist
            key_columns = [
                ("person_objects", "person_id"),
                ("person_objects", "session_uuid"),
                ("person_objects", "workflow_id"),
                ("person_face_mappings", "person_id"),
                ("person_face_mappings", "face_detection_id"),
                ("person_workflows", "workflow_id"),
                ("person_workflows", "session_uuid"),
                ("face_crops", "face_detection_id"),
            ]

            for table, column in key_columns:
                cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s AND table_schema = 'public'
                """,
                    (table, column),
                )

                validation_results[f"column_{table}_{column}"] = (
                    cursor.fetchone() is not None
                )

            cursor.close()

        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            validation_results["validation_error"] = str(e)

        return validation_results

    async def get_migration_info(self) -> Dict[str, any]:
        """Get information about the current migration status."""
        try:
            cursor = self.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            # Check migration record
            cursor.execute(
                """
                SELECT migration_name, applied_at, version 
                FROM schema_migrations 
                WHERE migration_name = 'person_objects_migration'
            """
            )

            migration_record = cursor.fetchone()

            # Get table counts
            table_info = {}
            tables = [
                "person_objects",
                "person_face_mappings",
                "person_workflows",
                "face_crops",
            ]

            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()["count"]
                    table_info[table] = count
                except Exception:
                    table_info[table] = "table_not_exists"

            cursor.close()

            return {
                "migration_applied": migration_record is not None,
                "applied_at": (
                    migration_record["applied_at"] if migration_record else None
                ),
                "version": migration_record["version"] if migration_record else None,
                "table_counts": table_info,
                "schema_valid": await self._quick_schema_check(),
            }

        except Exception as e:
            logger.error(f"Error getting migration info: {e}")
            return {"migration_applied": False, "error": str(e)}

    async def _quick_schema_check(self) -> bool:
        """Quick check if core schema components exist."""
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('person_objects', 'person_face_mappings', 'person_workflows', 'face_crops') 
                AND table_schema = 'public'
            """
            )

            count = cursor.fetchone()[0]
            cursor.close()

            return count == 4  # All 4 tables should exist

        except Exception:
            return False
