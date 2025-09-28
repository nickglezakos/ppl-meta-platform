#!/usr/bin/env python3
"""
PPL Meta Vision Service - Phase 1 Person Objects Schema Test
Test script to validate the person objects database schema migration.

This script tests:
- Database migration execution
- Table creation and structure validation
- Index creation and performance
- Foreign key constraints
- Data integrity operations
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import psycopg2
import psycopg2.extras
from database.person_objects_migrations import PersonObjectsMigration

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PersonObjectsSchemaTest:
    """Test suite for person objects database schema."""

    def __init__(self):
        """Initialize test suite with database connection."""
        self.connection = None
        self.migration = None
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

            # Initialize migration instance
            self.migration = PersonObjectsMigration(self.connection)

            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            sys.exit(1)

    async def test_migration_execution(self) -> bool:
        """Test complete migration execution."""
        logger.info("\n🧪 Testing Phase 1: Database Migration Execution")

        try:
            # Clean slate - rollback any existing migration
            await self.migration.rollback_migration()

            # Execute migration
            success = await self.migration.migrate_schema()

            if success:
                logger.info("✅ Migration execution test passed")
                return True
            else:
                logger.error("❌ Migration execution test failed")
                return False

        except Exception as e:
            logger.error(f"❌ Migration test error: {e}")
            return False

    async def test_table_structure(self) -> bool:
        """Test that all tables are created with correct structure."""
        logger.info("\n🧪 Testing Table Structure Validation")

        success = True

        # Define expected table structures
        expected_tables = {
            "person_objects": [
                "person_id",
                "session_uuid",
                "workflow_id",
                "face_count",
                "average_position_x",
                "average_position_y",
                "quality_score",
                "best_face_id",
                "estimated_age",
                "distance_from_camera",
                "tracking_algorithm",
                "tolerance_percent",
                "created_at",
                "updated_at",
            ],
            "person_face_mappings": [
                "id",
                "person_id",
                "face_detection_id",
                "match_type",
                "match_distance",
                "frame_number",
                "position_x",
                "position_y",
                "created_at",
            ],
            "person_workflows": [
                "workflow_id",
                "session_uuid",
                "status",
                "input_face_count",
                "output_person_count",
                "tolerance_percent",
                "processing_method",
                "enable_quality_analysis",
                "enable_age_detection",
                "started_at",
                "completed_at",
                "error_message",
                "metadata",
                "processing_duration_ms",
            ],
            "face_crops": [
                "id",
                "face_detection_id",
                "crop_base64",
                "pre_computed_quality_score",
                "crop_width",
                "crop_height",
                "extracted_at",
                "extraction_method",
            ],
        }

        cursor = self.connection.cursor()

        for table_name, expected_columns in expected_tables.items():
            try:
                # Check table exists
                cursor.execute(
                    """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = %s AND table_schema = 'public'
                """,
                    (table_name,),
                )

                if not cursor.fetchone():
                    logger.error(f"❌ Table '{table_name}' does not exist")
                    success = False
                    continue

                logger.info(f"✅ Table '{table_name}' exists")

                # Check columns
                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position
                """,
                    (table_name,),
                )

                actual_columns = [row[0] for row in cursor.fetchall()]

                # Verify all expected columns exist
                missing_columns = set(expected_columns) - set(actual_columns)
                if missing_columns:
                    logger.error(
                        f"❌ Table '{table_name}' missing columns: {missing_columns}"
                    )
                    success = False
                else:
                    logger.info(f"✅ Table '{table_name}' has all expected columns")

            except Exception as e:
                logger.error(f"❌ Error validating table '{table_name}': {e}")
                success = False

        cursor.close()

        if success:
            logger.info("✅ Table structure validation passed")
        else:
            logger.error("❌ Table structure validation failed")

        return success

    async def test_indexes_creation(self) -> bool:
        """Test that all performance indexes are created."""
        logger.info("\n🧪 Testing Index Creation")

        success = True
        cursor = self.connection.cursor()

        # Expected indexes
        expected_indexes = [
            "idx_person_objects_session_uuid",
            "idx_person_objects_workflow_id",
            "idx_person_objects_quality_score",
            "idx_person_face_mappings_person_id",
            "idx_person_face_mappings_face_id",
            "idx_person_face_mappings_frame_number",
            "idx_person_workflows_session_uuid",
            "idx_person_workflows_status",
            "idx_person_workflows_started_at",
            "idx_face_crops_face_detection_id",
            "idx_face_crops_quality_score",
        ]

        for index_name in expected_indexes:
            try:
                cursor.execute(
                    """
                    SELECT indexname FROM pg_indexes 
                    WHERE indexname = %s AND schemaname = 'public'
                """,
                    (index_name,),
                )

                if cursor.fetchone():
                    logger.info(f"✅ Index '{index_name}' exists")
                else:
                    logger.error(f"❌ Index '{index_name}' missing")
                    success = False

            except Exception as e:
                logger.error(f"❌ Error checking index '{index_name}': {e}")
                success = False

        cursor.close()

        if success:
            logger.info("✅ Index creation test passed")
        else:
            logger.error("❌ Index creation test failed")

        return success

    async def test_foreign_key_constraints(self) -> bool:
        """Test foreign key constraints."""
        logger.info("\n🧪 Testing Foreign Key Constraints")

        success = True
        cursor = self.connection.cursor()

        try:
            # Test foreign key constraint: person_face_mappings -> person_objects
            # First create a person object
            cursor.execute(
                """
                INSERT INTO person_objects 
                (person_id, session_uuid, workflow_id, face_count, average_position_x, average_position_y)
                VALUES 
                (gen_random_uuid(), 'test-session-123', 'test-workflow-123', 1, 100.0, 200.0)
                RETURNING person_id
            """
            )

            person_id = cursor.fetchone()[0]
            logger.info("✅ Created test person object")

            # Test valid foreign key reference
            cursor.execute(
                """
                INSERT INTO person_face_mappings 
                (person_id, face_detection_id, match_type, position_x, position_y)
                VALUES (%s, 'test-face-123', 'tracked', 100.0, 200.0)
            """,
                (person_id,),
            )

            logger.info("✅ Valid foreign key reference works")

            # Test invalid foreign key reference (should fail)
            try:
                cursor.execute(
                    """
                    INSERT INTO person_face_mappings 
                    (person_id, face_detection_id, match_type, position_x, position_y)
                    VALUES ('00000000-0000-0000-0000-000000000000', 'test-face-456', 'tracked', 100.0, 200.0)
                """
                )

                logger.error("❌ Invalid foreign key reference should have failed")
                success = False

            except psycopg2.IntegrityError:
                logger.info("✅ Foreign key constraint properly enforced")
                # Rollback the failed transaction
                self.connection.rollback()
                self.connection.autocommit = True

            # Clean up test data
            cursor.execute(
                "DELETE FROM person_face_mappings WHERE person_id = %s", (person_id,)
            )
            cursor.execute(
                "DELETE FROM person_objects WHERE person_id = %s", (person_id,)
            )

        except Exception as e:
            logger.error(f"❌ Foreign key constraint test error: {e}")
            success = False

        cursor.close()

        if success:
            logger.info("✅ Foreign key constraint test passed")
        else:
            logger.error("❌ Foreign key constraint test failed")

        return success

    async def test_data_integrity_operations(self) -> bool:
        """Test basic CRUD operations and data integrity."""
        logger.info("\n🧪 Testing Data Integrity Operations")

        success = True
        cursor = self.connection.cursor()

        try:
            # Test workflow creation
            workflow_id = "test-workflow-integrity"
            session_uuid = "test-session-integrity"

            cursor.execute(
                """
                INSERT INTO person_workflows 
                (workflow_id, session_uuid, input_face_count, tolerance_percent, metadata)
                VALUES (%s, %s, 10, 20.0, %s)
            """,
                (workflow_id, session_uuid, '{"test": true}'),
            )

            logger.info("✅ Workflow record created")

            # Test person object creation
            cursor.execute(
                """
                INSERT INTO person_objects 
                (session_uuid, workflow_id, face_count, average_position_x, average_position_y)
                VALUES (%s, %s, 3, 150.0, 250.0)
                RETURNING person_id
            """,
                (session_uuid, workflow_id),
            )

            person_id = cursor.fetchone()[0]
            logger.info(f"✅ Person object created: {person_id}")

            # Test multiple face mappings
            face_ids = ["face-1", "face-2", "face-3"]
            for i, face_id in enumerate(face_ids):
                cursor.execute(
                    """
                    INSERT INTO person_face_mappings 
                    (person_id, face_detection_id, match_type, match_distance, frame_number, position_x, position_y)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        person_id,
                        face_id,
                        "tracked" if i > 0 else "new_track",
                        i * 0.1,
                        i + 1,
                        150.0 + i,
                        250.0 + i,
                    ),
                )

            logger.info("✅ Face mappings created")

            # Test face crop storage
            cursor.execute(
                """
                INSERT INTO face_crops 
                (face_detection_id, pre_computed_quality_score, crop_width, crop_height)
                VALUES (%s, %s, %s, %s)
            """,
                (face_ids[0], 0.85, 64, 64),
            )

            logger.info("✅ Face crop record created")

            # Test complex query - get person with face data
            cursor.execute(
                """
                SELECT 
                    po.person_id,
                    po.face_count,
                    po.quality_score,
                    COUNT(pfm.id) as mapped_faces
                FROM person_objects po
                LEFT JOIN person_face_mappings pfm ON po.person_id = pfm.person_id
                WHERE po.session_uuid = %s
                GROUP BY po.person_id, po.face_count, po.quality_score
            """,
                (session_uuid,),
            )

            result = cursor.fetchone()
            if result:
                mapped_faces = result[3]
                if mapped_faces == 3:
                    logger.info("✅ Complex query returned correct face count")
                else:
                    logger.error(f"❌ Expected 3 mapped faces, got {mapped_faces}")
                    success = False
            else:
                logger.error("❌ Complex query returned no results")
                success = False

            # Test workflow completion update
            cursor.execute(
                """
                UPDATE person_workflows 
                SET status = 'completed', output_person_count = 1, completed_at = NOW()
                WHERE workflow_id = %s
            """,
                (workflow_id,),
            )

            logger.info("✅ Workflow status updated")

            # Clean up test data
            cursor.execute(
                "DELETE FROM face_crops WHERE face_detection_id = ANY(%s)", (face_ids,)
            )
            cursor.execute(
                "DELETE FROM person_face_mappings WHERE person_id = %s", (person_id,)
            )
            cursor.execute(
                "DELETE FROM person_objects WHERE person_id = %s", (person_id,)
            )
            cursor.execute(
                "DELETE FROM person_workflows WHERE workflow_id = %s", (workflow_id,)
            )

            logger.info("✅ Test data cleaned up")

        except Exception as e:
            logger.error(f"❌ Data integrity test error: {e}")
            success = False

        cursor.close()

        if success:
            logger.info("✅ Data integrity operations test passed")
        else:
            logger.error("❌ Data integrity operations test failed")

        return success

    async def test_migration_validation(self) -> bool:
        """Test migration validation functions."""
        logger.info("\n🧪 Testing Migration Validation")

        try:
            # Test schema validation
            validation_results = await self.migration.validate_schema()

            all_valid = True
            for component, valid in validation_results.items():
                if "error" not in component and not valid:
                    logger.error(f"❌ Validation failed for: {component}")
                    all_valid = False
                elif "error" not in component:
                    logger.info(f"✅ Validation passed for: {component}")

            # Test migration info
            migration_info = await self.migration.get_migration_info()

            if migration_info.get("migration_applied"):
                logger.info("✅ Migration info shows applied status")
            else:
                logger.error("❌ Migration info shows not applied")
                all_valid = False

            if migration_info.get("schema_valid"):
                logger.info("✅ Schema validation check passed")
            else:
                logger.error("❌ Schema validation check failed")
                all_valid = False

            return all_valid

        except Exception as e:
            logger.error(f"❌ Migration validation test error: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run complete Phase 1 test suite."""
        logger.info("🚀 Starting PPL Thread Phase 1: Database Schema Tests")
        logger.info("=" * 60)

        all_tests_passed = True

        tests = [
            ("Migration Execution", self.test_migration_execution),
            ("Table Structure", self.test_table_structure),
            ("Index Creation", self.test_indexes_creation),
            ("Foreign Key Constraints", self.test_foreign_key_constraints),
            ("Data Integrity Operations", self.test_data_integrity_operations),
            ("Migration Validation", self.test_migration_validation),
        ]

        for test_name, test_func in tests:
            try:
                result = await test_func()
                if not result:
                    all_tests_passed = False
                    logger.error(f"❌ {test_name} test failed")
                else:
                    logger.info(f"✅ {test_name} test passed")

            except Exception as e:
                logger.error(f"❌ {test_name} test error: {e}")
                all_tests_passed = False

        logger.info("\n" + "=" * 60)

        if all_tests_passed:
            logger.info("🎉 ALL PHASE 1 TESTS PASSED!")
            logger.info("✅ Person objects database schema is ready for Phase 2")
        else:
            logger.error("❌ SOME PHASE 1 TESTS FAILED!")
            logger.error("🔧 Please review and fix schema issues before proceeding")

        return all_tests_passed

    def cleanup(self):
        """Clean up database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


async def main():
    """Main test execution."""
    test_suite = PersonObjectsSchemaTest()

    try:
        success = await test_suite.run_all_tests()

        if success:
            logger.info("\n📋 Phase 1 Summary:")
            logger.info("✅ Database schema migration completed successfully")
            logger.info("✅ All tables, indexes, and constraints created")
            logger.info("✅ Data integrity operations validated")
            logger.info("✅ Ready to proceed to Phase 2: Core Face Grouping Engine")

            # Show migration info
            migration_info = await test_suite.migration.get_migration_info()
            logger.info(f"\n📊 Migration Details:")
            logger.info(f"   Applied: {migration_info.get('applied_at')}")
            logger.info(f"   Version: {migration_info.get('version')}")

            table_counts = migration_info.get("table_counts", {})
            logger.info(f"   Table Counts:")
            for table, count in table_counts.items():
                logger.info(f"     {table}: {count}")

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        return 1
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
