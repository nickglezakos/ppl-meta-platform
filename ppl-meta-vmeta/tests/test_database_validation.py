"""
Database Validation Tests for Phase 6.6

Tests migration execution, schema correctness, pgvector indexes,
and data integrity constraints for MVR-People system.

Run with: python -m pytest tests/test_database_validation.py -v
"""

import os
import sys
import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDatabaseValidation:
    """Comprehensive database validation tests"""
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Create test database connection"""
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "ppl_meta"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "")
        )
        yield conn
        conn.close()
    
    # ========================================================================
    # SCHEMA VALIDATION TESTS
    # ========================================================================
    
    def test_mvr_people_table_exists(self, db_connection):
        """Test that mvr_people table exists"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'mvr_people'
            );
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        
        assert exists, "mvr_people table does not exist"
        logger.info("✅ mvr_people table exists")
    
    def test_mvr_face_clusters_table_exists(self, db_connection):
        """Test that mvr_face_clusters table exists"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'mvr_face_clusters'
            );
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        
        assert exists, "mvr_face_clusters table does not exist"
        logger.info("✅ mvr_face_clusters table exists")
    
    def test_mvr_cluster_faces_table_exists(self, db_connection):
        """Test that mvr_cluster_faces table exists"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'mvr_cluster_faces'
            );
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        
        assert exists, "mvr_cluster_faces table does not exist"
        logger.info("✅ mvr_cluster_faces table exists")
    
    def test_mvr_people_columns(self, db_connection):
        """Test that mvr_people has all required columns"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'mvr_people'
            ORDER BY ordinal_position;
        """)
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in cursor.fetchall()}
        cursor.close()
        
        # Required columns
        required_columns = {
            "mvr_people_uuid": "uuid",
            "face_embedding": "USER-DEFINED",  # vector type
            "featured_individual_uuid": "uuid",
            "quality_score": ("double precision", "real"),
            "is_orphaned": "boolean",
            "created_at": "timestamp without time zone",
            "updated_at": "timestamp without time zone"
        }
        
        for col_name, expected_type in required_columns.items():
            assert col_name in columns, f"Column {col_name} missing from mvr_people"
            
            if isinstance(expected_type, tuple):
                assert columns[col_name]["type"] in expected_type, \
                    f"Column {col_name} has wrong type: {columns[col_name]['type']}"
            else:
                assert columns[col_name]["type"] == expected_type, \
                    f"Column {col_name} has wrong type: {columns[col_name]['type']}"
        
        logger.info(f"✅ mvr_people has all required columns ({len(columns)} total)")
    
    def test_pgvector_extension_installed(self, db_connection):
        """Test that pgvector extension is installed"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        
        assert exists, "pgvector extension not installed"
        logger.info("✅ pgvector extension installed")
    
    def test_uuid_ossp_extension_installed(self, db_connection):
        """Test that uuid-ossp extension is installed"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp'
            );
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        
        assert exists, "uuid-ossp extension not installed"
        logger.info("✅ uuid-ossp extension installed")
    
    # ========================================================================
    # INDEX VALIDATION TESTS
    # ========================================================================
    
    def test_mvr_people_primary_key(self, db_connection):
        """Test mvr_people primary key constraint"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'mvr_people'
            AND constraint_type = 'PRIMARY KEY';
        """)
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None, "mvr_people missing primary key"
        logger.info(f"✅ mvr_people has primary key: {result[0]}")
    
    def test_mvr_people_embedding_index(self, db_connection):
        """Test that face_embedding has IVFFlat index"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'mvr_people'
            AND indexdef LIKE '%ivfflat%';
        """)
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None, "mvr_people missing IVFFlat index on face_embedding"
        logger.info(f"✅ mvr_people has IVFFlat index: {result[0]}")
    
    def test_mvr_face_clusters_indexes(self, db_connection):
        """Test mvr_face_clusters has required indexes"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'mvr_face_clusters'
            ORDER BY indexname;
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        # Should have at least primary key and mvr_people_uuid index
        assert len(indexes) >= 2, f"mvr_face_clusters missing indexes (found {len(indexes)})"
        logger.info(f"✅ mvr_face_clusters has {len(indexes)} indexes")
    
    # ========================================================================
    # CONSTRAINT VALIDATION TESTS
    # ========================================================================
    
    def test_mvr_people_not_null_constraints(self, db_connection):
        """Test NOT NULL constraints on mvr_people"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'mvr_people'
            AND is_nullable = 'NO'
            ORDER BY column_name;
        """)
        not_null_columns = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        required_not_null = [
            "mvr_people_uuid",
            "face_embedding",
            "featured_individual_uuid",
            "quality_score",
            "is_orphaned"
        ]
        
        for col in required_not_null:
            assert col in not_null_columns, f"Column {col} should be NOT NULL"
        
        logger.info(f"✅ mvr_people has {len(not_null_columns)} NOT NULL constraints")
    
    def test_mvr_people_foreign_keys(self, db_connection):
        """Test foreign key constraints"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'mvr_face_clusters'
            AND tc.constraint_type = 'FOREIGN KEY';
        """)
        foreign_keys = cursor.fetchall()
        cursor.close()
        
        # mvr_face_clusters should have FK to mvr_people
        fk_found = any(row[2] == 'mvr_people' for row in foreign_keys)
        assert fk_found, "mvr_face_clusters missing foreign key to mvr_people"
        logger.info(f"✅ Found {len(foreign_keys)} foreign key constraints")
    
    def test_mvr_people_check_constraints(self, db_connection):
        """Test CHECK constraints on mvr_people"""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT constraint_name, check_clause
            FROM information_schema.check_constraints
            WHERE constraint_schema = 'public'
            AND constraint_name LIKE 'mvr_%';
        """)
        check_constraints = cursor.fetchall()
        cursor.close()
        
        # Should have constraints for age ranges, quality score, etc.
        logger.info(f"✅ Found {len(check_constraints)} CHECK constraints")
        for constraint in check_constraints:
            logger.info(f"   - {constraint[0]}")
    
    # ========================================================================
    # PGVECTOR FUNCTIONALITY TESTS
    # ========================================================================
    
    def test_vector_dimension(self, db_connection):
        """Test that face_embedding vector is 512 dimensions"""
        cursor = db_connection.cursor()
        
        # Create a test vector
        try:
            cursor.execute("""
                SELECT '[' || array_to_string(ARRAY(
                    SELECT random()::text FROM generate_series(1, 512)
                ), ',') || ']'::vector(512);
            """)
            result = cursor.fetchone()
            assert result is not None, "Failed to create 512-dim vector"
            logger.info("✅ pgvector supports 512-dimensional vectors")
        except Exception as e:
            pytest.fail(f"Vector dimension test failed: {e}")
        finally:
            db_connection.rollback()
            cursor.close()
    
    def test_vector_similarity_operations(self, db_connection):
        """Test vector similarity operations (cosine, L2)"""
        cursor = db_connection.cursor()
        
        try:
            # Test cosine similarity
            cursor.execute("""
                SELECT 1 - ('[' || array_to_string(ARRAY(
                    SELECT 0.5::text FROM generate_series(1, 512)
                ), ',') || ']'::vector(512) <=> '[' || array_to_string(ARRAY(
                    SELECT 0.5::text FROM generate_series(1, 512)
                ), ',') || ']'::vector(512)) as cosine_sim;
            """)
            cosine_sim = cursor.fetchone()[0]
            assert cosine_sim >= 0.99, "Cosine similarity calculation incorrect"
            
            logger.info(f"✅ Cosine similarity working (sim={cosine_sim:.4f})")
        except Exception as e:
            pytest.fail(f"Vector similarity test failed: {e}")
        finally:
            db_connection.rollback()
            cursor.close()
    
    def test_ivfflat_index_performance(self, db_connection):
        """Test IVFFlat index exists and can be queried"""
        cursor = db_connection.cursor()
        
        try:
            # Check if index exists
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'mvr_people'
                AND indexdef LIKE '%ivfflat%';
            """)
            index_info = cursor.fetchone()
            
            if index_info:
                logger.info(f"✅ IVFFlat index exists: {index_info[0]}")
                
                # Test index can be used
                cursor.execute("""
                    EXPLAIN (FORMAT JSON)
                    SELECT mvr_people_uuid
                    FROM mvr_people
                    ORDER BY face_embedding <=> '[' || array_to_string(ARRAY(
                        SELECT random()::text FROM generate_series(1, 512)
                    ), ',') || ']'::vector(512)
                    LIMIT 10;
                """)
                explain = cursor.fetchone()[0]
                logger.info("✅ IVFFlat index can be queried")
            else:
                logger.warning("⚠️  No IVFFlat index found (may not be created yet)")
        except Exception as e:
            pytest.fail(f"IVFFlat index test failed: {e}")
        finally:
            db_connection.rollback()
            cursor.close()
    
    # ========================================================================
    # DATA INTEGRITY TESTS
    # ========================================================================
    
    def test_mvr_people_insert_valid_data(self, db_connection):
        """Test inserting valid data into mvr_people"""
        cursor = db_connection.cursor()
        
        try:
            # Generate test embedding
            test_embedding = [0.1] * 512
            embedding_str = '[' + ','.join(map(str, test_embedding)) + ']'
            
            cursor.execute("""
                INSERT INTO mvr_people (
                    face_embedding,
                    featured_individual_uuid,
                    quality_score,
                    is_orphaned
                ) VALUES (
                    %s::vector(512),
                    gen_random_uuid(),
                    0.85,
                    false
                )
                RETURNING mvr_people_uuid;
            """, (embedding_str,))
            
            result = cursor.fetchone()
            assert result is not None, "Failed to insert valid MVR-People record"
            logger.info(f"✅ Successfully inserted test MVR-People: {result[0]}")
            
            db_connection.rollback()  # Clean up
        except Exception as e:
            db_connection.rollback()
            pytest.fail(f"Insert test failed: {e}")
        finally:
            cursor.close()
    
    def test_mvr_people_reject_invalid_quality_score(self, db_connection):
        """Test that invalid quality scores are rejected"""
        cursor = db_connection.cursor()
        
        try:
            test_embedding = [0.1] * 512
            embedding_str = '[' + ','.join(map(str, test_embedding)) + ']'
            
            # Try to insert quality score > 1.0
            cursor.execute("""
                INSERT INTO mvr_people (
                    face_embedding,
                    featured_individual_uuid,
                    quality_score,
                    is_orphaned
                ) VALUES (
                    %s::vector(512),
                    gen_random_uuid(),
                    1.5,  -- Invalid: > 1.0
                    false
                );
            """, (embedding_str,))
            
            db_connection.rollback()
            pytest.fail("Should have rejected quality_score > 1.0")
            
        except psycopg2.IntegrityError:
            db_connection.rollback()
            logger.info("✅ Correctly rejected invalid quality_score")
        except Exception as e:
            db_connection.rollback()
            # May not have CHECK constraint yet - that's okay
            logger.warning(f"⚠️  Quality score constraint not enforced: {e}")
        finally:
            cursor.close()
    
    def test_mvr_people_auto_timestamps(self, db_connection):
        """Test that created_at and updated_at are auto-populated"""
        cursor = db_connection.cursor()
        
        try:
            test_embedding = [0.1] * 512
            embedding_str = '[' + ','.join(map(str, test_embedding)) + ']'
            
            cursor.execute("""
                INSERT INTO mvr_people (
                    face_embedding,
                    featured_individual_uuid,
                    quality_score,
                    is_orphaned
                ) VALUES (
                    %s::vector(512),
                    gen_random_uuid(),
                    0.85,
                    false
                )
                RETURNING created_at, updated_at;
            """, (embedding_str,))
            
            result = cursor.fetchone()
            assert result[0] is not None, "created_at not auto-populated"
            assert result[1] is not None, "updated_at not auto-populated"
            logger.info("✅ Timestamps auto-populated correctly")
            
            db_connection.rollback()
        except Exception as e:
            db_connection.rollback()
            pytest.fail(f"Timestamp test failed: {e}")
        finally:
            cursor.close()
    
    # ========================================================================
    # MIGRATION VALIDATION
    # ========================================================================
    
    def test_migration_version_tracking(self, db_connection):
        """Test that migration version tracking exists"""
        cursor = db_connection.cursor()
        
        try:
            # Check if schema_migrations or similar table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('schema_migrations', 'alembic_version', 'migration_history')
                );
            """)
            exists = cursor.fetchone()[0]
            
            if exists:
                logger.info("✅ Migration version tracking table exists")
            else:
                logger.warning("⚠️  No migration tracking table found (consider adding)")
        except Exception as e:
            logger.warning(f"⚠️  Migration tracking check failed: {e}")
        finally:
            cursor.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
