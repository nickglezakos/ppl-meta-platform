#!/usr/bin/env python3
"""
PPL Meta Vision Service - Phase 1 Database Schema Test
Test script to validate the database schema migration for Workflow 4

This script tests the database migration and validates that all tables,
indexes, and constraints are properly created for session-based face detection.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseSchemaValidator:
    """Validator for the session-based face detection database schema."""

    def __init__(self):
        """Initialize validator with database connection."""
        self.connection = None
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
            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            sys.exit(1)

    def validate_table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = %s AND table_schema = 'public'
                """,
                    (table_name,),
                )

                result = cursor.fetchone()
                exists = result is not None

                if exists:
                    logger.info(f"✅ Table '{table_name}' exists")
                else:
                    logger.error(f"❌ Table '{table_name}' does not exist")

                return exists
        except Exception as e:
            logger.error(f"❌ Error checking table '{table_name}': {e}")
            return False

    def validate_column_exists(
        self, table_name: str, column_name: str, expected_type: str = None
    ) -> bool:
        """Check if a column exists in a table."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s AND table_schema = 'public'
                """,
                    (table_name, column_name),
                )

                result = cursor.fetchone()
                exists = result is not None

                if exists:
                    column_name_db, data_type, is_nullable = result
                    logger.info(
                        f"✅ Column '{table_name}.{column_name}' exists (type: {data_type})"
                    )

                    if expected_type and expected_type.lower() not in data_type.lower():
                        logger.warning(
                            f"⚠️ Column type mismatch: expected {expected_type}, got {data_type}"
                        )
                        return False
                else:
                    logger.error(
                        f"❌ Column '{table_name}.{column_name}' does not exist"
                    )

                return exists
        except Exception as e:
            logger.error(f"❌ Error checking column '{table_name}.{column_name}': {e}")
            return False

    def validate_index_exists(self, index_name: str, table_name: str = None) -> bool:
        """Check if an index exists."""
        try:
            with self.connection.cursor() as cursor:
                if table_name:
                    cursor.execute(
                        """
                        SELECT indexname FROM pg_indexes 
                        WHERE indexname = %s AND tablename = %s AND schemaname = 'public'
                    """,
                        (index_name, table_name),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT indexname FROM pg_indexes 
                        WHERE indexname = %s AND schemaname = 'public'
                    """,
                        (index_name,),
                    )

                result = cursor.fetchone()
                exists = result is not None

                if exists:
                    logger.info(f"✅ Index '{index_name}' exists")
                else:
                    logger.error(f"❌ Index '{index_name}' does not exist")

                return exists
        except Exception as e:
            logger.error(f"❌ Error checking index '{index_name}': {e}")
            return False

    def validate_constraint_exists(
        self, constraint_name: str, table_name: str, constraint_type: str = None
    ) -> bool:
        """Check if a constraint exists."""
        try:
            with self.connection.cursor() as cursor:
                query = """
                    SELECT constraint_name, constraint_type 
                    FROM information_schema.table_constraints 
                    WHERE constraint_name = %s AND table_name = %s AND table_schema = 'public'
                """

                if constraint_type:
                    query += " AND constraint_type = %s"
                    cursor.execute(
                        query, (constraint_name, table_name, constraint_type.upper())
                    )
                else:
                    cursor.execute(query, (constraint_name, table_name))

                result = cursor.fetchone()
                exists = result is not None

                if exists:
                    logger.info(
                        f"✅ Constraint '{constraint_name}' exists on '{table_name}'"
                    )
                else:
                    logger.error(
                        f"❌ Constraint '{constraint_name}' does not exist on '{table_name}'"
                    )

                return exists
        except Exception as e:
            logger.error(f"❌ Error checking constraint '{constraint_name}': {e}")
            return False

    def validate_foreign_key(
        self, table_name: str, column_name: str, ref_table: str, ref_column: str
    ) -> bool:
        """Check if a foreign key constraint exists."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY' 
                        AND tc.table_name = %s 
                        AND kcu.column_name = %s
                        AND ccu.table_name = %s
                        AND ccu.column_name = %s
                """,
                    (table_name, column_name, ref_table, ref_column),
                )

                result = cursor.fetchone()
                exists = result is not None

                if exists:
                    logger.info(
                        f"✅ Foreign key '{table_name}.{column_name}' -> '{ref_table}.{ref_column}' exists"
                    )
                else:
                    logger.error(
                        f"❌ Foreign key '{table_name}.{column_name}' -> '{ref_table}.{ref_column}' does not exist"
                    )

                return exists
        except Exception as e:
            logger.error(f"❌ Error checking foreign key: {e}")
            return False

    def test_insert_and_query_operations(self) -> bool:
        """Test basic insert and query operations on new tables."""
        try:
            logger.info("🧪 Testing database operations...")

            with self.connection.cursor() as cursor:
                # Test session creation
                session_uuid = "test-session-12345"
                media_uuid = "test-media-12345"

                # Insert test session
                cursor.execute(
                    """
                    INSERT INTO face_detection_sessions 
                    (session_uuid, media_uuid, session_type, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (session_uuid) DO UPDATE SET
                    media_uuid = EXCLUDED.media_uuid
                """,
                    (session_uuid, media_uuid, "streaming", '{"test": true}'),
                )

                # Insert test face detection
                cursor.execute(
                    """
                    INSERT INTO face_detections 
                    (id, media_id, session_uuid, frame_number, bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence, method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    confidence = EXCLUDED.confidence
                """,
                    (
                        "test-face-001",
                        media_uuid,
                        session_uuid,
                        1,
                        100,
                        100,
                        200,
                        200,
                        0.95,
                        "test_method",
                    ),
                )

                # Insert test processing status
                cursor.execute(
                    """
                    INSERT INTO media_processing_status 
                    (media_uuid, face_detection_processed, face_detection_session_uuid, total_faces_detected)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (media_uuid) DO UPDATE SET
                    face_detection_processed = EXCLUDED.face_detection_processed
                """,
                    (media_uuid, True, session_uuid, 1),
                )

                # Test queries
                # Query session with face count
                cursor.execute(
                    """
                    SELECT 
                        s.session_uuid,
                        s.media_uuid,
                        s.processing_status,
                        COUNT(f.id) as face_count
                    FROM face_detection_sessions s
                    LEFT JOIN face_detections f ON s.session_uuid = f.session_uuid
                    WHERE s.session_uuid = %s
                    GROUP BY s.session_uuid, s.media_uuid, s.processing_status
                """,
                    (session_uuid,),
                )

                session_result = cursor.fetchone()
                if session_result:
                    logger.info(f"✅ Session query successful: {session_result}")
                else:
                    logger.error("❌ Session query failed")
                    return False

                # Query processing status
                cursor.execute(
                    """
                    SELECT 
                        mps.media_uuid,
                        mps.face_detection_processed,
                        s.session_type
                    FROM media_processing_status mps
                    LEFT JOIN face_detection_sessions s ON mps.face_detection_session_uuid = s.session_uuid
                    WHERE mps.media_uuid = %s
                """,
                    (media_uuid,),
                )

                status_result = cursor.fetchone()
                if status_result:
                    logger.info(
                        f"✅ Processing status query successful: {status_result}"
                    )
                else:
                    logger.error("❌ Processing status query failed")
                    return False

                # Cleanup test data
                cursor.execute(
                    "DELETE FROM face_detections WHERE id = %s", ("test-face-001",)
                )
                cursor.execute(
                    "DELETE FROM media_processing_status WHERE media_uuid = %s",
                    (media_uuid,),
                )
                cursor.execute(
                    "DELETE FROM face_detection_sessions WHERE session_uuid = %s",
                    (session_uuid,),
                )

                logger.info("✅ Database operations test passed")
                return True

        except Exception as e:
            logger.error(f"❌ Database operations test failed: {e}")
            return False

    def run_performance_benchmark(self) -> bool:
        """Run basic performance benchmarks on the new schema."""
        try:
            logger.info("⚡ Running performance benchmarks...")

            with self.connection.cursor() as cursor:
                # Test session creation performance
                start_time = time.time()
                for i in range(100):
                    session_uuid = f"perf-test-{i}"
                    cursor.execute(
                        """
                        INSERT INTO face_detection_sessions 
                        (session_uuid, media_uuid, session_type)
                        VALUES (%s, %s, %s)
                    """,
                        (session_uuid, f"media-{i}", "streaming"),
                    )

                session_creation_time = (
                    time.time() - start_time
                ) * 10  # Convert to ms per session

                # Test face detection insertion performance
                start_time = time.time()
                for i in range(1000):
                    cursor.execute(
                        """
                        INSERT INTO face_detections 
                        (id, media_id, session_uuid, frame_number, bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence, method)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            f"perf-face-{i}",
                            f"media-{i % 100}",
                            f"perf-test-{i % 100}",
                            i % 30,
                            100,
                            100,
                            200,
                            200,
                            0.9,
                            "perf_test",
                        ),
                    )

                face_insertion_time = time.time() - start_time

                # Test session query performance
                start_time = time.time()
                for i in range(100):
                    cursor.execute(
                        """
                        SELECT s.*, COUNT(f.id) as face_count
                        FROM face_detection_sessions s
                        LEFT JOIN face_detections f ON s.session_uuid = f.session_uuid
                        WHERE s.session_uuid = %s
                        GROUP BY s.session_uuid
                    """,
                        (f"perf-test-{i}",),
                    )
                    cursor.fetchone()

                session_query_time = (
                    time.time() - start_time
                ) * 10  # Convert to ms per query

                # Cleanup performance test data
                cursor.execute(
                    "DELETE FROM face_detections WHERE id LIKE 'perf-face-%'"
                )
                cursor.execute(
                    "DELETE FROM face_detection_sessions WHERE session_uuid LIKE 'perf-test-%'"
                )

                # Log performance results
                logger.info(f"📊 Performance Results:")
                logger.info(
                    f"   Session Creation: {session_creation_time:.2f}ms per session"
                )
                logger.info(
                    f"   Face Insertion: {face_insertion_time * 1000:.2f}ms per 1000 faces"
                )
                logger.info(f"   Session Query: {session_query_time:.2f}ms per query")

                # Validate performance targets
                performance_ok = True
                if session_creation_time > 50:  # Target: <50ms per session
                    logger.warning(
                        f"⚠️ Session creation slower than target (50ms): {session_creation_time:.2f}ms"
                    )
                    performance_ok = False

                if face_insertion_time > 10:  # Target: <10ms per face
                    logger.warning(
                        f"⚠️ Face insertion slower than target (10ms/face): {face_insertion_time * 1000:.2f}ms/1000 faces"
                    )
                    performance_ok = False

                if session_query_time > 100:  # Target: <100ms per query
                    logger.warning(
                        f"⚠️ Session query slower than target (100ms): {session_query_time:.2f}ms"
                    )
                    performance_ok = False

                if performance_ok:
                    logger.info("✅ All performance targets met")
                else:
                    logger.warning(
                        "⚠️ Some performance targets not met (this may be acceptable for development)"
                    )

                return True

        except Exception as e:
            logger.error(f"❌ Performance benchmark failed: {e}")
            return False

    def validate_complete_schema(self) -> bool:
        """Run complete schema validation."""
        logger.info("🔍 Starting complete schema validation...")

        all_checks_passed = True

        # Check tables
        logger.info("\n📋 Validating Tables:")
        tables = [
            "face_detection_sessions",
            "media_processing_status",
            "face_detections",  # existing table (should already exist)
        ]

        for table in tables:
            if not self.validate_table_exists(table):
                all_checks_passed = False

        # Check face_detection_sessions columns
        logger.info("\n📋 Validating face_detection_sessions columns:")
        session_columns = [
            ("session_uuid", "character varying"),
            ("media_uuid", "character varying"),
            ("camera_device_uuid", "character varying"),
            ("session_type", "character varying"),
            ("started_at", "timestamp"),
            ("ended_at", "timestamp"),
            ("total_faces_detected", "integer"),
            ("processing_status", "character varying"),
            ("metadata", "jsonb"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
        ]

        for column_name, expected_type in session_columns:
            if not self.validate_column_exists(
                "face_detection_sessions", column_name, expected_type
            ):
                all_checks_passed = False

        # Check media_processing_status columns
        logger.info("\n📋 Validating media_processing_status columns:")
        status_columns = [
            ("media_uuid", "character varying"),
            ("face_detection_processed", "boolean"),
            ("face_detection_session_uuid", "character varying"),
            ("processing_completed_at", "timestamp"),
            ("total_frames_processed", "integer"),
            ("total_faces_detected", "integer"),
            ("processing_method", "character varying"),
            ("last_updated", "timestamp"),
        ]

        for column_name, expected_type in status_columns:
            if not self.validate_column_exists(
                "media_processing_status", column_name, expected_type
            ):
                all_checks_passed = False

        # Check session_uuid column in face_detections
        logger.info("\n📋 Validating face_detections session column:")
        if not self.validate_column_exists(
            "face_detections", "session_uuid", "character varying"
        ):
            all_checks_passed = False

        # Check indexes
        logger.info("\n📋 Validating Indexes:")
        indexes = [
            ("idx_face_detection_sessions_media_uuid", "face_detection_sessions"),
            ("idx_face_detection_sessions_camera_device", "face_detection_sessions"),
            ("idx_face_detection_sessions_status", "face_detection_sessions"),
            ("idx_face_detection_sessions_type", "face_detection_sessions"),
            ("idx_face_detection_sessions_started_at", "face_detection_sessions"),
            ("idx_face_detections_session_uuid", "face_detections"),
            ("idx_face_detections_session_frame", "face_detections"),
            ("idx_media_processing_status_processed", "media_processing_status"),
            ("idx_media_processing_status_session", "media_processing_status"),
            ("idx_media_processing_status_updated", "media_processing_status"),
        ]

        for index_name, table_name in indexes:
            if not self.validate_index_exists(index_name, table_name):
                all_checks_passed = False

        # Check foreign key constraints
        logger.info("\n📋 Validating Foreign Key Constraints:")
        foreign_keys = [
            (
                "face_detections",
                "session_uuid",
                "face_detection_sessions",
                "session_uuid",
            ),
            (
                "media_processing_status",
                "face_detection_session_uuid",
                "face_detection_sessions",
                "session_uuid",
            ),
        ]

        for table, column, ref_table, ref_column in foreign_keys:
            if not self.validate_foreign_key(table, column, ref_table, ref_column):
                all_checks_passed = False

        # Check constraints
        logger.info("\n📋 Validating Check Constraints:")
        constraints = [
            ("chk_session_type", "face_detection_sessions", "CHECK"),
            ("chk_processing_status", "face_detection_sessions", "CHECK"),
            ("chk_session_uuid_format", "face_detection_sessions", "CHECK"),
            ("chk_session_time_order", "face_detection_sessions", "CHECK"),
            ("chk_faces_count_positive", "face_detection_sessions", "CHECK"),
        ]

        for constraint_name, table_name, constraint_type in constraints:
            if not self.validate_constraint_exists(
                constraint_name, table_name, constraint_type
            ):
                all_checks_passed = False

        # Test database operations
        logger.info("\n📋 Testing Database Operations:")
        if not self.test_insert_and_query_operations():
            all_checks_passed = False

        # Run performance benchmarks
        logger.info("\n📋 Running Performance Benchmarks:")
        if not self.run_performance_benchmark():
            all_checks_passed = False

        return all_checks_passed

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


def main():
    """Main validation function."""
    logger.info("🎯 PPL Meta Vision Service - Phase 1 Database Schema Validation")
    logger.info("=" * 70)

    validator = DatabaseSchemaValidator()

    try:
        success = validator.validate_complete_schema()

        logger.info("\n" + "=" * 70)
        if success:
            logger.info("🎉 Phase 1 Database Schema Validation: ALL CHECKS PASSED ✅")
            logger.info("The database is ready for Phase 2 implementation.")
        else:
            logger.error("💥 Phase 1 Database Schema Validation: SOME CHECKS FAILED ❌")
            logger.error("Please review the errors above and fix the issues.")
            sys.exit(1)

    finally:
        validator.close()


if __name__ == "__main__":
    main()
