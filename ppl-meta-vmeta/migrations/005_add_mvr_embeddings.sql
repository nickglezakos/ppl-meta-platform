-- Migration: Add Face Embeddings to MVR People
-- Purpose: Store canonical embeddings on MVR person objects for efficient caching
-- Priority: HIGH - Simplifies Phase 1 MVR caching architecture
-- Date: 2025-11-08
-- Version: 2.19.30

-- ============================================================================
-- PART 1: Add embedding columns to mvr_people table
-- ============================================================================

ALTER TABLE mvr_people 
    ADD COLUMN IF NOT EXISTS face_embedding vector(512),
    ADD COLUMN IF NOT EXISTS embedding_confidence DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(50) DEFAULT 'Facenet512',
    ADD COLUMN IF NOT EXISTS embedding_created_at TIMESTAMP;

-- Add comment explaining the design
COMMENT ON COLUMN mvr_people.face_embedding IS 
    'Quality-weighted mean embedding computed from merged individual faces. Used for cache hits in subsequent sessions.';

COMMENT ON COLUMN mvr_people.embedding_confidence IS 
    'Mean confidence score of individual embeddings used to compute this MVR embedding. Range: 0.0-1.0.';

COMMENT ON COLUMN mvr_people.embedding_model IS 
    'Model used to generate embeddings (e.g., Facenet512). All individual embeddings must use same model.';

COMMENT ON COLUMN mvr_people.embedding_created_at IS 
    'Timestamp when MVR embedding was computed and stored.';

-- ============================================================================
-- PART 2: Create index for fast similarity search
-- ============================================================================

-- Vector similarity index using HNSW (Hierarchical Navigable Small World)
-- Enables fast approximate nearest neighbor search for MVR embeddings
CREATE INDEX IF NOT EXISTS idx_mvr_people_embedding 
    ON mvr_people 
    USING hnsw (face_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index for querying MVR people with embeddings
CREATE INDEX IF NOT EXISTS idx_mvr_people_has_embedding 
    ON mvr_people(embedding_created_at) 
    WHERE face_embedding IS NOT NULL;

-- ============================================================================
-- PART 3: Add validation constraint
-- ============================================================================

-- Ensure embedding confidence is in valid range
ALTER TABLE mvr_people 
    ADD CONSTRAINT check_mvr_embedding_confidence 
    CHECK (embedding_confidence IS NULL OR 
           (embedding_confidence >= 0.0 AND embedding_confidence <= 1.0));

-- ============================================================================
-- Migration complete
-- ============================================================================

-- Verify changes
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'mvr_people' 
  AND column_name LIKE '%embedding%'
ORDER BY ordinal_position;
