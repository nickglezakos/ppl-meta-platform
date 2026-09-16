-- MVR-People (Machine Vision Representation - People) Schema
-- PPL Meta Platform v2.20.0+
-- Migration: 002 - MVR-People Tables
-- Created: October 31, 2025
--
-- Purpose: Create tables for cross-video person aggregation with automatic
--          matching, merging, and orphan management.
--
-- Design Reference: docs/vision-vmeta/MVR_PEOPLE_DESIGN.md

-- ============================================================================
-- Table 1: mvr_people
-- ============================================================================
-- Primary table storing aggregated person representations across videos.
-- Each MVR-People represents the "best known" view of a unique person
-- combining multiple Individual observations.

CREATE TABLE IF NOT EXISTS mvr_people (
    mvr_people_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Biometric Features (from best quality Individual)
    face_embedding VECTOR(512) NOT NULL,  -- pgvector: Primary face signature
    face_quality FLOAT NOT NULL CHECK (face_quality >= 0.0 AND face_quality <= 1.0),
    
    -- Demographic Estimates (from best quality Individual)
    age_min INTEGER CHECK (age_min >= 0 AND age_min <= 120),
    age_max INTEGER CHECK (age_max >= 0 AND age_max <= 120),
    age_confidence FLOAT CHECK (age_confidence >= 0.0 AND age_confidence <= 1.0),
    
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'unknown')),
    gender_confidence FLOAT CHECK (gender_confidence >= 0.0 AND gender_confidence <= 1.0),
    
    -- Quality Metrics (from best quality Individual)
    quality_score FLOAT NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    -- Featured Individual (highest quality source)
    featured_individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid),
    featured_person_object_uuid UUID,  -- Best single person object
    featured_video_uuid UUID,          -- Video containing best appearance
    
    -- Statistics
    total_linked_individuals INTEGER NOT NULL DEFAULT 1,
    total_appearances INTEGER NOT NULL DEFAULT 0,
    total_videos INTEGER NOT NULL DEFAULT 0,
    
    -- Temporal Information
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    
    -- Creation & Update Tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_session UUID REFERENCES tracking_sessions(session_uuid),
    
    -- Matching & Merging Metadata
    is_orphaned BOOLEAN NOT NULL DEFAULT FALSE,
    orphaned_at TIMESTAMP WITH TIME ZONE,
    merged_into_mvr_uuid UUID REFERENCES mvr_people(mvr_people_uuid),
    previous_individual_uuids JSONB DEFAULT '[]'::JSONB,  -- Array of UUIDs
    auto_created BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT valid_age_range CHECK (age_max >= age_min),
    CONSTRAINT valid_statistics CHECK (
        total_linked_individuals >= 0 AND
        total_appearances >= 0 AND
        total_videos >= 0
    ),
    CONSTRAINT valid_orphan_state CHECK (
        (is_orphaned = FALSE AND orphaned_at IS NULL AND merged_into_mvr_uuid IS NULL) OR
        (is_orphaned = TRUE AND orphaned_at IS NOT NULL AND merged_into_mvr_uuid IS NOT NULL)
    ),
    CONSTRAINT valid_time_range CHECK (
        first_seen IS NULL OR last_seen IS NULL OR last_seen >= first_seen
    )
);

-- Comments for documentation
COMMENT ON TABLE mvr_people IS 'Machine Vision Representation - People: Aggregated person identities across multiple video observations with automatic matching and merging';
COMMENT ON COLUMN mvr_people.face_embedding IS 'FaceNet 512-dimensional face embedding from highest quality individual';
COMMENT ON COLUMN mvr_people.featured_individual_uuid IS 'UUID of the individual with the highest quality score';
COMMENT ON COLUMN mvr_people.is_orphaned IS 'TRUE when this MVR-People has been merged into another (deprecated record)';
COMMENT ON COLUMN mvr_people.previous_individual_uuids IS 'JSONB array of individual UUIDs that were previously linked before merging';


-- ============================================================================
-- Table 2: individual_mvr_mapping
-- ============================================================================
-- Junction table linking Individuals to their parent MVR-People.
-- Maintains 1:N relationship (one MVR-People can have many Individuals).
-- Initially 1:1, becomes 1:N after merging.

CREATE TABLE IF NOT EXISTS individual_mvr_mapping (
    mapping_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    mvr_people_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    
    -- Quality & Confidence at time of linking
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    quality_score FLOAT NOT NULL CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    similarity_score FLOAT CHECK (similarity_score >= 0.0 AND similarity_score <= 1.0),
    
    -- Representative Status
    is_representative BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE if this is the featured individual
    
    -- Temporal Information
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    linked_by_session UUID REFERENCES tracking_sessions(session_uuid),
    
    -- Linking Method
    link_method VARCHAR(20) NOT NULL DEFAULT 'auto_create' 
        CHECK (link_method IN ('auto_create', 'auto_merge', 'manual_link', 'batch_import')),
    
    -- Metadata
    notes TEXT,
    
    -- Constraints
    CONSTRAINT unique_individual_mapping UNIQUE (individual_uuid, mvr_people_uuid)
);

-- Create partial unique index for PostgreSQL 14 compatibility
-- (NULLS NOT DISTINCT requires PostgreSQL 15+)
CREATE UNIQUE INDEX idx_one_representative_per_mvr
    ON individual_mvr_mapping(mvr_people_uuid)
    WHERE is_representative = TRUE;

-- Comments
COMMENT ON TABLE individual_mvr_mapping IS 'Maps Individuals to their parent MVR-People. Initially 1:1, becomes 1:N after merging.';
COMMENT ON COLUMN individual_mvr_mapping.is_representative IS 'TRUE only for the featured individual with highest quality';
COMMENT ON COLUMN individual_mvr_mapping.link_method IS 'How this mapping was created: auto_create (1st individual), auto_merge, manual_link, or batch_import';
COMMENT ON COLUMN individual_mvr_mapping.similarity_score IS 'Face embedding similarity score used for matching (NULL for auto_create)';


-- ============================================================================
-- Table 3: mvr_merge_audit_log
-- ============================================================================
-- Audit trail for all MVR-People merge operations.
-- Tracks source MVR, target MVR, similarity scores, and merge decisions.

CREATE TABLE IF NOT EXISTS mvr_merge_audit_log (
    audit_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Merge Participants
    source_mvr_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid),
    target_mvr_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid),
    source_individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid),
    
    -- Merge Decision
    merge_action VARCHAR(20) NOT NULL CHECK (merge_action IN ('merged', 'rejected', 'manual_review')),
    merge_reason VARCHAR(50) NOT NULL,  -- 'similarity_threshold', 'quality_comparison', 'manual_decision'
    
    -- Matching Metrics
    similarity_score FLOAT NOT NULL CHECK (similarity_score >= 0.0 AND similarity_score <= 1.0),
    matching_threshold FLOAT NOT NULL CHECK (matching_threshold >= 0.0 AND matching_threshold <= 1.0),
    
    -- Quality Comparison (at time of merge)
    source_quality_score FLOAT NOT NULL CHECK (source_quality_score >= 0.0 AND source_quality_score <= 1.0),
    target_quality_score FLOAT NOT NULL CHECK (target_quality_score >= 0.0 AND target_quality_score <= 1.0),
    winner_mvr_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid),  -- Which MVR was kept
    
    -- Temporal Information
    merged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    merged_by_session UUID REFERENCES tracking_sessions(session_uuid),
    
    -- User & System Context
    user_id VARCHAR(100),  -- If manually triggered
    system_mode VARCHAR(20) DEFAULT 'automatic' CHECK (system_mode IN ('automatic', 'manual', 'batch')),
    
    -- Additional Metadata
    metadata JSONB,  -- Store additional context (demographics, appearance deltas, etc.)
    
    -- Constraints
    CONSTRAINT different_mvr_sources CHECK (source_mvr_uuid != target_mvr_uuid),
    CONSTRAINT valid_winner CHECK (winner_mvr_uuid IN (source_mvr_uuid, target_mvr_uuid))
);

-- Comments
COMMENT ON TABLE mvr_merge_audit_log IS 'Complete audit trail of all MVR-People merge operations for compliance and debugging';
COMMENT ON COLUMN mvr_merge_audit_log.merge_action IS 'Final decision: merged (approved), rejected (below threshold), manual_review (flagged)';
COMMENT ON COLUMN mvr_merge_audit_log.winner_mvr_uuid IS 'UUID of the MVR-People that was kept (higher quality), other becomes orphaned';


-- ============================================================================
-- Table 4: mvr_matching_config
-- ============================================================================
-- Configuration table for MVR-People matching and merging behavior.
-- Single row table with updateable thresholds and settings.

CREATE TABLE IF NOT EXISTS mvr_matching_config (
    config_id INTEGER PRIMARY KEY DEFAULT 1,  -- Single row table
    
    -- Matching Thresholds
    similarity_threshold FLOAT NOT NULL DEFAULT 0.85 
        CHECK (similarity_threshold >= 0.0 AND similarity_threshold <= 1.0),
    min_quality_threshold FLOAT NOT NULL DEFAULT 0.3 
        CHECK (min_quality_threshold >= 0.0 AND min_quality_threshold <= 1.0),
    
    -- Auto-Merge Behavior
    auto_merge_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    require_manual_review_above FLOAT DEFAULT 0.95 
        CHECK (require_manual_review_above >= 0.0 AND require_manual_review_above <= 1.0),
    
    -- Orphan Management
    orphan_retention_days INTEGER DEFAULT 90 CHECK (orphan_retention_days > 0),
    auto_cleanup_orphans BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Performance Settings
    max_candidates_to_check INTEGER NOT NULL DEFAULT 50 CHECK (max_candidates_to_check > 0),
    batch_processing_size INTEGER NOT NULL DEFAULT 100 CHECK (batch_processing_size > 0),
    
    -- Temporal Information
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(100),
    
    -- Metadata
    notes TEXT,
    
    -- Constraints
    CONSTRAINT single_config_row CHECK (config_id = 1),
    CONSTRAINT valid_threshold_order CHECK (similarity_threshold >= min_quality_threshold)
);

-- Comments
COMMENT ON TABLE mvr_matching_config IS 'Global configuration for MVR-People matching algorithm. Single row table (config_id=1).';
COMMENT ON COLUMN mvr_matching_config.similarity_threshold IS 'Face embedding cosine similarity required for automatic merging (default 0.85)';
COMMENT ON COLUMN mvr_matching_config.require_manual_review_above IS 'Similarity scores above this trigger manual review instead of auto-merge';
COMMENT ON COLUMN mvr_matching_config.orphan_retention_days IS 'How long to keep orphaned MVR-People before cleanup (default 90 days)';

-- Insert default configuration
INSERT INTO mvr_matching_config (config_id, similarity_threshold, auto_merge_enabled, notes)
VALUES (1, 0.85, TRUE, 'Default MVR-People matching configuration - Phase 1 implementation')
ON CONFLICT (config_id) DO NOTHING;


-- ============================================================================
-- INDEXES
-- ============================================================================

-- Primary Lookup Indexes
CREATE INDEX IF NOT EXISTS idx_mvr_people_featured_individual 
    ON mvr_people(featured_individual_uuid);

CREATE INDEX IF NOT EXISTS idx_mvr_people_created_at 
    ON mvr_people(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvr_people_updated_at 
    ON mvr_people(updated_at DESC);

-- Orphan Management Indexes
CREATE INDEX IF NOT EXISTS idx_mvr_people_orphaned 
    ON mvr_people(is_orphaned, orphaned_at DESC) 
    WHERE is_orphaned = TRUE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_active 
    ON mvr_people(is_orphaned, updated_at DESC) 
    WHERE is_orphaned = FALSE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_merged_into 
    ON mvr_people(merged_into_mvr_uuid) 
    WHERE merged_into_mvr_uuid IS NOT NULL;

-- Demographic Search Indexes
CREATE INDEX IF NOT EXISTS idx_mvr_people_gender 
    ON mvr_people(gender) 
    WHERE is_orphaned = FALSE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_age_range 
    ON mvr_people(age_min, age_max) 
    WHERE is_orphaned = FALSE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_quality 
    ON mvr_people(quality_score DESC) 
    WHERE is_orphaned = FALSE;

-- Temporal Search Indexes
CREATE INDEX IF NOT EXISTS idx_mvr_people_first_seen 
    ON mvr_people(first_seen DESC) 
    WHERE is_orphaned = FALSE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_last_seen 
    ON mvr_people(last_seen DESC) 
    WHERE is_orphaned = FALSE;

-- pgvector Similarity Search Index (IVFFlat for approximate nearest neighbor)
-- Note: This index should be created AFTER data is populated for optimal performance
-- For initial deployment, comment out and create manually after 10k+ records
CREATE INDEX IF NOT EXISTS idx_mvr_people_face_embedding_ivfflat 
    ON mvr_people 
    USING ivfflat (face_embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE is_orphaned = FALSE;

-- For small datasets, use this instead:
-- CREATE INDEX IF NOT EXISTS idx_mvr_people_face_embedding_hnsw
--     ON mvr_people 
--     USING hnsw (face_embedding vector_cosine_ops)
--     WHERE is_orphaned = FALSE;


-- Individual-MVR Mapping Indexes
CREATE INDEX IF NOT EXISTS idx_individual_mvr_mapping_individual 
    ON individual_mvr_mapping(individual_uuid);

CREATE INDEX IF NOT EXISTS idx_individual_mvr_mapping_mvr 
    ON individual_mvr_mapping(mvr_people_uuid);

CREATE INDEX IF NOT EXISTS idx_individual_mvr_mapping_representative 
    ON individual_mvr_mapping(mvr_people_uuid, is_representative) 
    WHERE is_representative = TRUE;

CREATE INDEX IF NOT EXISTS idx_individual_mvr_mapping_linked_at 
    ON individual_mvr_mapping(linked_at DESC);

CREATE INDEX IF NOT EXISTS idx_individual_mvr_mapping_method 
    ON individual_mvr_mapping(link_method);


-- Merge Audit Log Indexes
CREATE INDEX IF NOT EXISTS idx_mvr_merge_audit_source 
    ON mvr_merge_audit_log(source_mvr_uuid, merged_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvr_merge_audit_target 
    ON mvr_merge_audit_log(target_mvr_uuid, merged_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvr_merge_audit_individual 
    ON mvr_merge_audit_log(source_individual_uuid);

CREATE INDEX IF NOT EXISTS idx_mvr_merge_audit_action 
    ON mvr_merge_audit_log(merge_action, merged_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvr_merge_audit_timestamp 
    ON mvr_merge_audit_log(merged_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvr_merge_audit_user 
    ON mvr_merge_audit_log(user_id, merged_at DESC) 
    WHERE user_id IS NOT NULL;


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function: Calculate cosine similarity between two face embeddings
-- Used for matching algorithm (can be called from Python or SQL)
CREATE OR REPLACE FUNCTION mvr_cosine_similarity(
    embedding1 VECTOR(512),
    embedding2 VECTOR(512)
)
RETURNS FLOAT AS $$
BEGIN
    RETURN 1 - (embedding1 <=> embedding2);  -- pgvector cosine distance to similarity
END;
$$ LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;

COMMENT ON FUNCTION mvr_cosine_similarity IS 'Calculate cosine similarity (0-1) between two face embeddings for matching';


-- Function: Find top N similar MVR-People for a given face embedding
-- Returns candidate matches for automatic merging
CREATE OR REPLACE FUNCTION mvr_find_similar_people(
    query_embedding VECTOR(512),
    max_candidates INTEGER DEFAULT 10,
    min_similarity FLOAT DEFAULT 0.80
)
RETURNS TABLE (
    mvr_people_uuid UUID,
    similarity_score FLOAT,
    quality_score FLOAT,
    total_linked_individuals INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.mvr_people_uuid,
        mvr_cosine_similarity(m.face_embedding, query_embedding) AS similarity_score,
        m.quality_score,
        m.total_linked_individuals
    FROM mvr_people m
    WHERE 
        m.is_orphaned = FALSE
        AND mvr_cosine_similarity(m.face_embedding, query_embedding) >= min_similarity
    ORDER BY 
        m.face_embedding <=> query_embedding  -- pgvector distance operator
    LIMIT max_candidates;
END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;

COMMENT ON FUNCTION mvr_find_similar_people IS 'Find top N most similar active MVR-People for matching algorithm';


-- Function: Update MVR-People statistics after Individual linking
CREATE OR REPLACE FUNCTION mvr_update_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update total_linked_individuals count
    UPDATE mvr_people
    SET 
        total_linked_individuals = (
            SELECT COUNT(*) 
            FROM individual_mvr_mapping 
            WHERE mvr_people_uuid = NEW.mvr_people_uuid
        ),
        updated_at = NOW()
    WHERE mvr_people_uuid = NEW.mvr_people_uuid;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update MVR statistics on mapping changes
CREATE TRIGGER trigger_update_mvr_statistics
    AFTER INSERT OR DELETE ON individual_mvr_mapping
    FOR EACH ROW
    EXECUTE FUNCTION mvr_update_statistics();


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Query 1: Verify all tables exist
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('mvr_people', 'individual_mvr_mapping', 'mvr_merge_audit_log', 'mvr_matching_config');
    
    IF table_count = 4 THEN
        RAISE NOTICE '✅ All 4 MVR-People tables created successfully';
    ELSE
        RAISE WARNING '❌ Expected 4 tables, found %', table_count;
    END IF;
END $$;

-- Query 2: Verify pgvector extension
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE NOTICE '✅ pgvector extension is installed';
    ELSE
        RAISE WARNING '❌ pgvector extension not found';
    END IF;
END $$;

-- Query 3: Verify indexes
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename IN ('mvr_people', 'individual_mvr_mapping', 'mvr_merge_audit_log');
    
    RAISE NOTICE '✅ Created % indexes for MVR-People tables', index_count;
END $$;

-- Query 4: Show default configuration
SELECT 
    similarity_threshold,
    auto_merge_enabled,
    max_candidates_to_check,
    notes
FROM mvr_matching_config
WHERE config_id = 1;

-- Final migration summary
DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'MVR-People Schema Migration Complete';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Tables Created:';
    RAISE NOTICE '  • mvr_people';
    RAISE NOTICE '  • individual_mvr_mapping';
    RAISE NOTICE '  • mvr_merge_audit_log';
    RAISE NOTICE '  • mvr_matching_config';
    RAISE NOTICE '';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '  1. Verify tables with: SELECT * FROM mvr_matching_config;';
    RAISE NOTICE '  2. Proceed to Phase 2: ML Models Setup';
    RAISE NOTICE '  3. See: docs/vision-vmeta/MVR_PEOPLE_DESIGN.md';
    RAISE NOTICE '============================================================================';
END $$;
