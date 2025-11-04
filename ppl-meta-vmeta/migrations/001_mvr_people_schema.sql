-- ============================================================================
-- MVR-People Database Migration Script
-- Version: 1.0.0
-- Date: November 1, 2025
-- Description: Creates MVR-People (Machine Vision Representation) tables
--              for cross-video person tracking and deduplication
-- ============================================================================

-- Prerequisites:
-- 1. PostgreSQL 14.18+
-- 2. pgvector extension installed
-- 3. uuid-ossp extension installed

-- IMPORTANT: This script is idempotent - safe to run multiple times

BEGIN;

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- TABLE 1: mvr_people
-- Core MVR-People records with face embeddings and demographics
-- ============================================================================

CREATE TABLE IF NOT EXISTS mvr_people (
    -- Primary Key
    mvr_people_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Face Embedding (512 dimensions from FaceNet)
    face_embedding vector(512) NOT NULL,
    
    -- Featured Individual (the Individual that "owns" this MVR)
    featured_individual_uuid UUID NOT NULL,
    
    -- Demographics
    age_min INTEGER,
    age_max INTEGER,
    gender_estimate VARCHAR(20),
    gender_confidence FLOAT,
    
    -- Quality Metrics
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    
    -- Orphaning (for merge tracking)
    is_orphaned BOOLEAN NOT NULL DEFAULT FALSE,
    orphaned_at TIMESTAMP,
    replaced_by_mvr_uuid UUID,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT mvr_people_quality_check CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    CONSTRAINT mvr_people_age_check CHECK (
        (age_min IS NULL AND age_max IS NULL) OR 
        (age_min IS NOT NULL AND age_max IS NOT NULL AND age_min <= age_max)
    ),
    CONSTRAINT mvr_people_gender_check CHECK (
        gender_estimate IS NULL OR 
        gender_estimate IN ('male', 'female', 'unknown')
    ),
    CONSTRAINT mvr_people_orphan_check CHECK (
        (is_orphaned = FALSE AND orphaned_at IS NULL AND replaced_by_mvr_uuid IS NULL) OR
        (is_orphaned = TRUE AND orphaned_at IS NOT NULL AND replaced_by_mvr_uuid IS NOT NULL)
    ),
    
    -- Foreign Key to Individuals table
    CONSTRAINT fk_mvr_people_featured_individual 
        FOREIGN KEY (featured_individual_uuid) 
        REFERENCES individuals(individual_uuid) 
        ON DELETE CASCADE,
        
    -- Self-referencing FK for replacement tracking
    CONSTRAINT fk_mvr_people_replaced_by 
        FOREIGN KEY (replaced_by_mvr_uuid) 
        REFERENCES mvr_people(mvr_people_uuid) 
        ON DELETE SET NULL
);

-- Indexes for mvr_people
CREATE INDEX IF NOT EXISTS idx_mvr_people_featured_individual 
    ON mvr_people(featured_individual_uuid);
    
CREATE INDEX IF NOT EXISTS idx_mvr_people_orphaned 
    ON mvr_people(is_orphaned);
    
CREATE INDEX IF NOT EXISTS idx_mvr_people_quality_active 
    ON mvr_people(quality_score DESC) 
    WHERE is_orphaned = FALSE;
    
CREATE INDEX IF NOT EXISTS idx_mvr_people_demographics 
    ON mvr_people(gender_estimate, age_min, age_max) 
    WHERE is_orphaned = FALSE;
    
CREATE INDEX IF NOT EXISTS idx_mvr_people_created_at 
    ON mvr_people(created_at DESC);

-- **CRITICAL:** pgvector GIN index for similarity search
CREATE INDEX IF NOT EXISTS idx_mvr_people_embedding_vector 
    ON mvr_people 
    USING ivfflat (face_embedding vector_cosine_ops)
    WITH (lists = 100);

-- Comment on table
COMMENT ON TABLE mvr_people IS 
    'Machine Vision Representation for People - Core MVR records with face embeddings';

-- ============================================================================
-- TABLE 2: individual_mvr_mapping
-- Links Individuals to their MVR-People representations
-- ============================================================================

CREATE TABLE IF NOT EXISTS individual_mvr_mapping (
    -- Primary Key
    mapping_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Individual Reference
    individual_uuid UUID NOT NULL,
    
    -- MVR-People Reference
    mvr_people_uuid UUID NOT NULL,
    
    -- Quality Score (cached from MVR for quick lookup)
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_individual_mvr_individual 
        FOREIGN KEY (individual_uuid) 
        REFERENCES individuals(individual_uuid) 
        ON DELETE CASCADE,
        
    CONSTRAINT fk_individual_mvr_mvr_people 
        FOREIGN KEY (mvr_people_uuid) 
        REFERENCES mvr_people(mvr_people_uuid) 
        ON DELETE CASCADE,
    
    -- Unique constraint: One MVR per Individual
    CONSTRAINT uk_individual_mvr_mapping 
        UNIQUE (individual_uuid)
);

-- Indexes for individual_mvr_mapping
CREATE INDEX IF NOT EXISTS idx_mvr_mapping_individual 
    ON individual_mvr_mapping(individual_uuid);
    
CREATE INDEX IF NOT EXISTS idx_mvr_mapping_mvr_people 
    ON individual_mvr_mapping(mvr_people_uuid);
    
CREATE INDEX IF NOT EXISTS idx_mvr_mapping_quality 
    ON individual_mvr_mapping(quality_score DESC);

-- Comment on table
COMMENT ON TABLE individual_mvr_mapping IS 
    'Maps Individuals to their MVR-People representations (one-to-one)';

-- ============================================================================
-- TABLE 3: mvr_merge_audit_log
-- Tracks merge operations for compliance and debugging
-- ============================================================================

CREATE TABLE IF NOT EXISTS mvr_merge_audit_log (
    -- Primary Key
    audit_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Merge Details
    winner_mvr_uuid UUID NOT NULL,
    loser_mvr_uuid UUID NOT NULL,
    
    -- Reassignment Info
    individuals_reassigned INTEGER NOT NULL DEFAULT 0,
    
    -- Metadata
    merge_reason VARCHAR(255),
    similarity_score FLOAT,
    quality_difference FLOAT,
    
    -- Timestamp
    merge_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys (use ON DELETE SET NULL to preserve audit trail)
    CONSTRAINT fk_mvr_audit_winner 
        FOREIGN KEY (winner_mvr_uuid) 
        REFERENCES mvr_people(mvr_people_uuid) 
        ON DELETE SET NULL,
        
    CONSTRAINT fk_mvr_audit_loser 
        FOREIGN KEY (loser_mvr_uuid) 
        REFERENCES mvr_people(mvr_people_uuid) 
        ON DELETE SET NULL
);

-- Indexes for mvr_merge_audit_log
CREATE INDEX IF NOT EXISTS idx_mvr_audit_winner 
    ON mvr_merge_audit_log(winner_mvr_uuid);
    
CREATE INDEX IF NOT EXISTS idx_mvr_audit_loser 
    ON mvr_merge_audit_log(loser_mvr_uuid);
    
CREATE INDEX IF NOT EXISTS idx_mvr_audit_timestamp 
    ON mvr_merge_audit_log(merge_timestamp DESC);

-- Comment on table
COMMENT ON TABLE mvr_merge_audit_log IS 
    'Audit trail for MVR-People merge operations';

-- ============================================================================
-- TABLE 4: mvr_matching_config
-- Configurable thresholds for matching and merging
-- ============================================================================

CREATE TABLE IF NOT EXISTS mvr_matching_config (
    -- Primary Key
    config_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Similarity Thresholds
    similarity_threshold FLOAT NOT NULL DEFAULT 0.85,
    quality_weight FLOAT NOT NULL DEFAULT 0.3,
    
    -- Demographic Matching
    age_tolerance INTEGER NOT NULL DEFAULT 5,
    gender_match_required BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Auto-Merge Settings
    auto_merge_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT mvr_config_similarity_check 
        CHECK (similarity_threshold >= 0.0 AND similarity_threshold <= 1.0),
    CONSTRAINT mvr_config_quality_check 
        CHECK (quality_weight >= 0.0 AND quality_weight <= 1.0),
    CONSTRAINT mvr_config_age_check 
        CHECK (age_tolerance >= 0)
);

-- Index for mvr_matching_config
CREATE INDEX IF NOT EXISTS idx_mvr_config_created 
    ON mvr_matching_config(created_at DESC);

-- Comment on table
COMMENT ON TABLE mvr_matching_config IS 
    'Configuration settings for MVR-People matching and merging algorithms';

-- ============================================================================
-- DEFAULT CONFIGURATION
-- ============================================================================

-- Insert default matching configuration (if not exists)
INSERT INTO mvr_matching_config (
    config_uuid,
    similarity_threshold,
    quality_weight,
    age_tolerance,
    gender_match_required,
    auto_merge_enabled,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid(),
    0.85,           -- 85% similarity threshold (good for face matching)
    0.3,            -- 30% weight to quality score
    5,              -- ±5 years age tolerance
    FALSE,          -- Don't require gender match (allow unknowns)
    TRUE,           -- Enable auto-merge by default
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM mvr_matching_config
);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables created
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'mvr_people',
        'individual_mvr_mapping',
        'mvr_merge_audit_log',
        'mvr_matching_config'
    );
    
    IF table_count = 4 THEN
        RAISE NOTICE '✅ All 4 MVR-People tables created successfully';
    ELSE
        RAISE WARNING '⚠️ Only % out of 4 tables created', table_count;
    END IF;
END $$;

-- Verify indexes created
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename IN (
        'mvr_people',
        'individual_mvr_mapping',
        'mvr_merge_audit_log',
        'mvr_matching_config'
    );
    
    RAISE NOTICE '✅ Created % indexes for MVR-People tables', index_count;
END $$;

-- Verify pgvector extension
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) THEN
        RAISE NOTICE '✅ pgvector extension is installed';
    ELSE
        RAISE WARNING '⚠️ pgvector extension not found - similarity search will not work!';
    END IF;
END $$;

-- Verify default configuration
DO $$
DECLARE
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO config_count FROM mvr_matching_config;
    
    IF config_count > 0 THEN
        RAISE NOTICE '✅ Default MVR matching configuration created';
    ELSE
        RAISE WARNING '⚠️ No default configuration found';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Display summary
SELECT 
    '✅ MVR-People migration completed successfully!' as status,
    CURRENT_TIMESTAMP as completed_at;

-- Display table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'mvr_people',
    'individual_mvr_mapping',
    'mvr_merge_audit_log',
    'mvr_matching_config'
)
ORDER BY tablename;

-- ============================================================================
-- ROLLBACK SCRIPT (save separately as rollback_mvr_people.sql)
-- ============================================================================

/*
-- To rollback this migration, run:
-- psql -U postgres -d ppl_meta -f rollback_mvr_people.sql

BEGIN;

-- Drop tables in reverse order (handle FK constraints)
DROP TABLE IF EXISTS mvr_merge_audit_log CASCADE;
DROP TABLE IF EXISTS individual_mvr_mapping CASCADE;
DROP TABLE IF EXISTS mvr_people CASCADE;
DROP TABLE IF EXISTS mvr_matching_config CASCADE;

-- Optionally drop indexes (they cascade with tables, but explicit for clarity)
DROP INDEX IF EXISTS idx_mvr_people_embedding_vector;
DROP INDEX IF EXISTS idx_mvr_people_featured_individual;
DROP INDEX IF EXISTS idx_mvr_people_orphaned;
DROP INDEX IF EXISTS idx_mvr_people_quality_active;
DROP INDEX IF EXISTS idx_mvr_people_demographics;
DROP INDEX IF EXISTS idx_mvr_people_created_at;
DROP INDEX IF EXISTS idx_mvr_mapping_individual;
DROP INDEX IF EXISTS idx_mvr_mapping_mvr_people;
DROP INDEX IF EXISTS idx_mvr_mapping_quality;
DROP INDEX IF EXISTS idx_mvr_audit_winner;
DROP INDEX IF EXISTS idx_mvr_audit_loser;
DROP INDEX IF EXISTS idx_mvr_audit_timestamp;
DROP INDEX IF EXISTS idx_mvr_config_created;

COMMIT;

SELECT '✅ MVR-People rollback completed' as status;
*/
