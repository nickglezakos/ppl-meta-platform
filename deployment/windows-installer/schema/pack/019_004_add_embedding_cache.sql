-- Migration: Add Embedding Cache for MVR People
-- Purpose: Store facial embeddings persistently to avoid regeneration
-- Priority: HIGH - Phase 1 of MVR caching architecture
-- Date: 2025-11-07
-- Version: 2.19.30

-- ============================================================================
-- PART 1: Create individual_embeddings_cache table
-- ============================================================================

CREATE TABLE IF NOT EXISTS individual_embeddings_cache (
    -- Primary identifier (links to individuals table)
    individual_uuid UUID PRIMARY KEY REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    
    -- Embedding data (512-dimensional vector for Facenet512)
    face_embedding vector(512) NOT NULL,
    embedding_model VARCHAR(50) NOT NULL DEFAULT 'Facenet512',
    embedding_confidence FLOAT NOT NULL CHECK (embedding_confidence >= 0 AND embedding_confidence <= 1),
    
    -- Source metadata (for debugging and quality assessment)
    source_video_uuid UUID,
    source_frame_number INTEGER,
    bbox_x INTEGER,
    bbox_y INTEGER,
    bbox_width INTEGER,
    bbox_height INTEGER,
    
    -- Cache metadata
    cache_version INTEGER DEFAULT 1,  -- For future embedding model upgrades
    is_valid BOOLEAN DEFAULT TRUE,     -- For manual invalidation
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMP NOT NULL DEFAULT NOW(),  -- Track last access for LRU cleanup
    
    -- Quality metrics (for cache replacement decisions)
    source_video_quality FLOAT DEFAULT 0.5,
    face_detection_confidence FLOAT DEFAULT 0.95
);

-- ============================================================================
-- PART 2: Create indexes for fast lookups
-- ============================================================================

-- Primary lookup index (already covered by PRIMARY KEY)
-- CREATE INDEX idx_individual_embeddings_cache_individual 
--     ON individual_embeddings_cache(individual_uuid);

-- Index for finding invalid/stale embeddings
CREATE INDEX idx_individual_embeddings_cache_valid 
    ON individual_embeddings_cache(is_valid, updated_at);

-- Index for LRU cleanup (find least recently accessed)
CREATE INDEX idx_individual_embeddings_cache_accessed 
    ON individual_embeddings_cache(accessed_at);

-- Index for cache version filtering (for model upgrades)
CREATE INDEX idx_individual_embeddings_cache_version 
    ON individual_embeddings_cache(cache_version);

-- Vector similarity index (for future direct embedding queries)
-- Using HNSW index for fast approximate nearest neighbor search
CREATE INDEX idx_individual_embeddings_cache_embedding 
    ON individual_embeddings_cache 
    USING hnsw (face_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- PART 3: Add cache tracking columns to tracking_sessions
-- ============================================================================

ALTER TABLE tracking_sessions 
    ADD COLUMN IF NOT EXISTS embedding_cache_hits INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS embedding_cache_misses INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS embedding_cache_hit_rate FLOAT DEFAULT 0.0;

-- Update comment for tracking_sessions table
COMMENT ON COLUMN tracking_sessions.embedding_cache_hits IS 
    'Number of individuals with cached embeddings reused in this session';
COMMENT ON COLUMN tracking_sessions.embedding_cache_misses IS 
    'Number of individuals requiring new embedding generation in this session';
COMMENT ON COLUMN tracking_sessions.embedding_cache_hit_rate IS 
    'Percentage of embeddings served from cache (0.0 to 1.0)';

-- ============================================================================
-- PART 4: Create helper functions
-- ============================================================================

-- Function to update accessed_at timestamp on cache reads
CREATE OR REPLACE FUNCTION update_embedding_cache_accessed()
RETURNS TRIGGER AS $$
BEGIN
    NEW.accessed_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update accessed_at on SELECT
-- Note: Triggers on SELECT are not supported in PostgreSQL
-- Instead, we'll update accessed_at in application code

-- Function to calculate embedding cache statistics
CREATE OR REPLACE FUNCTION calculate_embedding_cache_stats(session_uuid_param UUID)
RETURNS TABLE (
    total_embeddings INTEGER,
    cached_embeddings INTEGER,
    new_embeddings INTEGER,
    cache_hit_rate FLOAT,
    avg_cache_age_days FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_embeddings,
        COUNT(*) FILTER (WHERE ec.individual_uuid IS NOT NULL)::INTEGER as cached_embeddings,
        COUNT(*) FILTER (WHERE ec.individual_uuid IS NULL)::INTEGER as new_embeddings,
        COALESCE(
            COUNT(*) FILTER (WHERE ec.individual_uuid IS NOT NULL)::FLOAT / 
            NULLIF(COUNT(*), 0),
            0.0
        ) as cache_hit_rate,
        AVG(EXTRACT(EPOCH FROM (NOW() - ec.created_at)) / 86400.0)::FLOAT as avg_cache_age_days
    FROM session_individuals si
    LEFT JOIN individual_embeddings_cache ec ON si.individual_uuid = ec.individual_uuid
    WHERE si.session_uuid = session_uuid_param;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 5: Create cleanup/maintenance procedures
-- ============================================================================

-- Procedure to invalidate embeddings older than X days
CREATE OR REPLACE PROCEDURE invalidate_old_embeddings(days_old INTEGER DEFAULT 30)
LANGUAGE plpgsql AS $$
DECLARE
    affected_count INTEGER;
BEGIN
    UPDATE individual_embeddings_cache
    SET is_valid = FALSE
    WHERE updated_at < NOW() - INTERVAL '1 day' * days_old
      AND is_valid = TRUE;
    
    GET DIAGNOSTICS affected_count = ROW_COUNT;
    
    RAISE NOTICE 'Invalidated % embeddings older than % days', affected_count, days_old;
END;
$$;

-- Procedure to clean up least recently accessed embeddings (LRU eviction)
CREATE OR REPLACE PROCEDURE cleanup_lru_embeddings(keep_count INTEGER DEFAULT 10000)
LANGUAGE plpgsql AS $$
DECLARE
    affected_count INTEGER;
BEGIN
    DELETE FROM individual_embeddings_cache
    WHERE individual_uuid IN (
        SELECT individual_uuid
        FROM individual_embeddings_cache
        ORDER BY accessed_at ASC
        OFFSET keep_count
    );
    
    GET DIAGNOSTICS affected_count = ROW_COUNT;
    
    RAISE NOTICE 'Removed % least recently accessed embeddings', affected_count;
END;
$$;

-- ============================================================================
-- PART 6: Add table and column comments
-- ============================================================================

COMMENT ON TABLE individual_embeddings_cache IS 
    'Persistent cache of facial embeddings for individuals to avoid expensive regeneration. Part of Phase 1 MVR caching architecture.';

COMMENT ON COLUMN individual_embeddings_cache.face_embedding IS 
    '512-dimensional Facenet512 embedding vector representing the individual''s facial features';

COMMENT ON COLUMN individual_embeddings_cache.embedding_confidence IS 
    'DeepFace confidence score for this embedding (0.0 to 1.0)';

COMMENT ON COLUMN individual_embeddings_cache.cache_version IS 
    'Version number for cache invalidation during model upgrades (default: 1)';

COMMENT ON COLUMN individual_embeddings_cache.is_valid IS 
    'Whether this embedding is still valid (FALSE = invalidated, needs regeneration)';

COMMENT ON COLUMN individual_embeddings_cache.accessed_at IS 
    'Last time this embedding was accessed (for LRU cleanup)';

-- ============================================================================
-- PART 7: Grant permissions (adjust as needed for your setup)
-- ============================================================================

-- Grant SELECT/INSERT/UPDATE to application user
-- GRANT SELECT, INSERT, UPDATE ON individual_embeddings_cache TO vmeta_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vmeta_app_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify table was created
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'individual_embeddings_cache'
ORDER BY ordinal_position;

-- Verify indexes were created
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'individual_embeddings_cache';

-- Verify new columns in tracking_sessions
SELECT 
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'tracking_sessions'
  AND (column_name LIKE '%embedding_cache%' 
       OR column_name LIKE '%mvr_cache%');

-- Add MVR-level cache metrics columns
ALTER TABLE tracking_sessions 
    ADD COLUMN IF NOT EXISTS mvr_cache_hits INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS mvr_created_count INTEGER DEFAULT 0;

COMMENT ON COLUMN tracking_sessions.mvr_cache_hits IS 
    'Number of MVR people found in cache (reused existing MVR)';

COMMENT ON COLUMN tracking_sessions.mvr_created_count IS 
    'Number of new MVR people created in this session';

-- Show table size (should be 0 rows initially)
SELECT 
    COUNT(*) as total_cached_embeddings,
    pg_size_pretty(pg_total_relation_size('individual_embeddings_cache')) as table_size
FROM individual_embeddings_cache;

-- ============================================================================
-- ROLLBACK SCRIPT (save as 004_rollback_embedding_cache.sql)
-- ============================================================================

/*
-- To rollback this migration:

-- Drop helper functions and procedures
DROP PROCEDURE IF EXISTS cleanup_lru_embeddings(INTEGER);
DROP PROCEDURE IF EXISTS invalidate_old_embeddings(INTEGER);
DROP FUNCTION IF EXISTS calculate_embedding_cache_stats(UUID);
DROP FUNCTION IF EXISTS update_embedding_cache_accessed();

-- Remove columns from tracking_sessions
ALTER TABLE tracking_sessions 
    DROP COLUMN IF EXISTS embedding_cache_hit_rate,
    DROP COLUMN IF EXISTS embedding_cache_misses,
    DROP COLUMN IF EXISTS embedding_cache_hits;

-- Drop table (CASCADE will drop all dependent objects)
DROP TABLE IF EXISTS individual_embeddings_cache CASCADE;

-- Verify cleanup
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'individual_embeddings_cache';
*/
