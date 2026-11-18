-- =============================================
-- Cross-Video Individual Tracking Database Schema
-- PPL Meta Platform v2.19.13+
-- File: 002_cross_video_tracking_schema.sql
-- Created: October 20, 2025
-- Purpose: Core database schema for cross-video individual tracking algorithm
-- =============================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- CORE TRACKING SESSIONS TABLE
-- =============================================
CREATE TABLE tracking_sessions (
    session_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    collections TEXT[] NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (
        status IN ('initialized', 'running', 'completed', 'failed', 'partial')
    ),
    config_hash VARCHAR(32) NOT NULL,
    algorithm_config JSONB NOT NULL,
    
    -- Processing metrics
    total_videos INTEGER NOT NULL DEFAULT 0,
    processed_videos INTEGER NOT NULL DEFAULT 0,
    failed_videos TEXT[] DEFAULT '{}',
    individuals_found INTEGER NOT NULL DEFAULT 0,
    person_objects_processed INTEGER NOT NULL DEFAULT 0,
    cache_hits INTEGER NOT NULL DEFAULT 0,
    
    -- Timing information
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_seconds FLOAT,
    
    -- Constraints
    CONSTRAINT valid_time_range CHECK (start_time < end_time),
    CONSTRAINT valid_processing_metrics CHECK (
        processed_videos <= total_videos AND
        cache_hits <= total_videos AND
        individuals_found >= 0 AND
        person_objects_processed >= 0
    )
);

-- Add comments for documentation
COMMENT ON TABLE tracking_sessions IS 'User-initiated cross-video tracking execution sessions';
COMMENT ON COLUMN tracking_sessions.config_hash IS 'Hash of algorithm configuration for cache matching';
COMMENT ON COLUMN tracking_sessions.algorithm_config IS 'Complete algorithm configuration as JSONB';
COMMENT ON COLUMN tracking_sessions.collections IS 'Array of collection names to process';

-- =============================================
-- INDIVIDUALS TABLE
-- =============================================
CREATE TABLE individuals (
    individual_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_id VARCHAR(50) UNIQUE NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    spatial_signature JSONB,
    temporal_signature JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add comments
COMMENT ON TABLE individuals IS 'Individual identities spanning multiple videos';
COMMENT ON COLUMN individuals.individual_id IS 'Human-readable identifier (e.g., individual_001)';
COMMENT ON COLUMN individuals.confidence_score IS 'Overall matching confidence (0.0 to 1.0)';
COMMENT ON COLUMN individuals.spatial_signature IS 'Characteristic spatial patterns as JSONB';
COMMENT ON COLUMN individuals.temporal_signature IS 'Movement and timing patterns as JSONB';

-- =============================================
-- INDIVIDUAL VIDEO APPEARANCES TABLE
-- =============================================
CREATE TABLE individual_video_appearances (
    individual_uuid UUID REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    video_uuid UUID NOT NULL,
    person_object_uuid UUID NOT NULL,
    start_timestamp TIMESTAMP NOT NULL,
    end_timestamp TIMESTAMP NOT NULL,
    entry_bbox FLOAT[4],  -- [x1, y1, x2, y2] format
    exit_bbox FLOAT[4],   -- [x1, y1, x2, y2] format
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    representative_faces JSONB,  -- Best quality faces from this video
    movement_pattern JSONB,      -- Spatial movement within video
    
    PRIMARY KEY (individual_uuid, video_uuid, person_object_uuid),
    
    -- Constraints
    CONSTRAINT valid_appearance_time CHECK (start_timestamp <= end_timestamp),
    CONSTRAINT valid_bbox_format CHECK (
        (entry_bbox IS NULL OR array_length(entry_bbox, 1) = 4) AND
        (exit_bbox IS NULL OR array_length(exit_bbox, 1) = 4)
    )
);

-- Add comments
COMMENT ON TABLE individual_video_appearances IS 'Individual appearances in specific videos';
COMMENT ON COLUMN individual_video_appearances.entry_bbox IS 'First face rectangle in video [x1,y1,x2,y2]';
COMMENT ON COLUMN individual_video_appearances.exit_bbox IS 'Last face rectangle in video [x1,y1,x2,y2]';
COMMENT ON COLUMN individual_video_appearances.representative_faces IS 'Best quality faces for identification';

-- =============================================
-- VIDEO PROCESSING STATES TABLE
-- =============================================
CREATE TABLE video_processing_states (
    video_uuid UUID NOT NULL,
    session_uuid UUID REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    processing_status VARCHAR(20) NOT NULL CHECK (
        processing_status IN ('pending', 'processing', 'completed', 'failed', 'cached')
    ),
    processed_at TIMESTAMP DEFAULT NOW(),
    person_objects_count INTEGER DEFAULT 0 CHECK (person_objects_count >= 0),
    processing_time_ms FLOAT DEFAULT 0 CHECK (processing_time_ms >= 0),
    cache_source_session UUID REFERENCES tracking_sessions(session_uuid),
    error_message TEXT,
    
    PRIMARY KEY (video_uuid, session_uuid)
);

-- Add comments
COMMENT ON TABLE video_processing_states IS 'Processing state tracking for individual videos';
COMMENT ON COLUMN video_processing_states.cache_source_session IS 'Original session that created cached results';
COMMENT ON COLUMN video_processing_states.processing_time_ms IS 'Time taken to process this video in milliseconds';

-- =============================================
-- CACHED PERSON OBJECTS TABLE
-- =============================================
CREATE TABLE cached_person_objects (
    cache_key VARCHAR(64) PRIMARY KEY,
    video_uuid UUID NOT NULL,
    session_uuid UUID REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    config_hash VARCHAR(32) NOT NULL,
    person_objects JSONB NOT NULL,
    processing_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0 CHECK (access_count >= 0),
    
    -- Ensure cache key uniqueness per video and config
    UNIQUE(video_uuid, config_hash)
);

-- Add comments
COMMENT ON TABLE cached_person_objects IS 'Cached processing results for efficient reuse';
COMMENT ON COLUMN cached_person_objects.cache_key IS 'Hash of (video_uuid, config_hash)';
COMMENT ON COLUMN cached_person_objects.person_objects IS 'Extracted person objects as JSONB';
COMMENT ON COLUMN cached_person_objects.processing_metadata IS 'Additional processing information';

-- =============================================
-- SESSION-INDIVIDUAL RELATIONSHIPS TABLE
-- =============================================
CREATE TABLE session_individuals (
    session_uuid UUID REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    individual_uuid UUID REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    processing_type VARCHAR(20) NOT NULL CHECK (
        processing_type IN ('new', 'cached', 'merged', 'extended')
    ),
    confidence_contribution FLOAT CHECK (confidence_contribution >= 0 AND confidence_contribution <= 1),
    created_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (session_uuid, individual_uuid)
);

-- Add comments
COMMENT ON TABLE session_individuals IS 'Relationships between sessions and individuals';
COMMENT ON COLUMN session_individuals.processing_type IS 'How individual was processed: new/cached/merged/extended';
COMMENT ON COLUMN session_individuals.confidence_contribution IS 'Contribution to overall individual confidence';

-- =============================================
-- SEQUENCES FOR AUTO-INCREMENTING IDs
-- =============================================

-- Sequence for individual IDs
CREATE SEQUENCE individuals_id_sequence 
    START 1 
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 999999
    CACHE 10;

-- Function to generate individual IDs
CREATE OR REPLACE FUNCTION generate_individual_id()
RETURNS VARCHAR(50) AS $$
BEGIN
    RETURN 'individual_' || LPAD(nextval('individuals_id_sequence')::TEXT, 3, '0');
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-generate individual_id
CREATE OR REPLACE FUNCTION set_individual_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.individual_id IS NULL OR NEW.individual_id = '' THEN
        NEW.individual_id := generate_individual_id();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_individual_id
    BEFORE INSERT ON individuals
    FOR EACH ROW
    EXECUTE FUNCTION set_individual_id();

-- =============================================
-- UTILITY FUNCTIONS
-- =============================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for individuals table
CREATE TRIGGER trigger_update_individuals_updated_at
    BEFORE UPDATE ON individuals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to update cache access statistics
CREATE OR REPLACE FUNCTION update_cache_access()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE cached_person_objects 
    SET 
        last_accessed = NOW(),
        access_count = access_count + 1
    WHERE cache_key = NEW.cache_key;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate cache key
CREATE OR REPLACE FUNCTION calculate_cache_key(
    p_video_uuid UUID,
    p_config_hash VARCHAR(32)
)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(
        digest(p_video_uuid::TEXT || p_config_hash, 'sha256'),
        'hex'
    )::VARCHAR(64);
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VALIDATION FUNCTIONS
-- =============================================

-- Function to validate algorithm configuration
CREATE OR REPLACE FUNCTION validate_algorithm_config(config JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check required fields exist
    IF NOT (config ? 'max_gap_seconds' AND 
            config ? 'iou_threshold' AND 
            config ? 'min_overlap_confidence') THEN
        RETURN FALSE;
    END IF;
    
    -- Validate value ranges
    IF (config->>'iou_threshold')::FLOAT < 0 OR (config->>'iou_threshold')::FLOAT > 1 THEN
        RETURN FALSE;
    END IF;
    
    IF (config->>'min_overlap_confidence')::FLOAT < 0 OR (config->>'min_overlap_confidence')::FLOAT > 1 THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add constraint to validate algorithm config
ALTER TABLE tracking_sessions 
ADD CONSTRAINT valid_algorithm_config 
CHECK (validate_algorithm_config(algorithm_config));

-- =============================================
-- INITIAL DATA / DEFAULT CONFIGURATIONS
-- =============================================

-- Insert default algorithm configurations (for reference)
-- This table can be used to store common configurations
CREATE TABLE algorithm_configurations (
    config_name VARCHAR(50) PRIMARY KEY,
    description TEXT,
    config JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default configurations
INSERT INTO algorithm_configurations (config_name, description, config, is_default) VALUES
('default', 'Default cross-video tracking configuration', '{
    "max_gap_seconds": 3,
    "min_sequence_length": 2,
    "iou_threshold": 0.3,
    "min_overlap_confidence": 0.5,
    "min_appearances": 1,
    "confidence_weight_iou": 0.4,
    "confidence_weight_temporal": 0.3,
    "confidence_weight_spatial": 0.3,
    "max_collections": 10,
    "batch_size": 100
}', true),

('high_precision', 'High precision configuration with stricter thresholds', '{
    "max_gap_seconds": 2,
    "min_sequence_length": 2,
    "iou_threshold": 0.4,
    "min_overlap_confidence": 0.7,
    "min_appearances": 2,
    "confidence_weight_iou": 0.5,
    "confidence_weight_temporal": 0.3,
    "confidence_weight_spatial": 0.2,
    "max_collections": 5,
    "batch_size": 50
}', false),

('high_recall', 'High recall configuration with relaxed thresholds', '{
    "max_gap_seconds": 5,
    "min_sequence_length": 1,
    "iou_threshold": 0.2,
    "min_overlap_confidence": 0.3,
    "min_appearances": 1,
    "confidence_weight_iou": 0.3,
    "confidence_weight_temporal": 0.4,
    "confidence_weight_spatial": 0.3,
    "max_collections": 20,
    "batch_size": 200
}', false);

-- =============================================
-- SCHEMA VALIDATION
-- =============================================

-- Function to validate the entire schema
CREATE OR REPLACE FUNCTION validate_cross_video_schema()
RETURNS TABLE(table_name TEXT, validation_result TEXT) AS $$
BEGIN
    -- Check if all required tables exist
    RETURN QUERY
    SELECT 
        t.table_name::TEXT,
        CASE 
            WHEN t.table_name IS NOT NULL THEN 'EXISTS'
            ELSE 'MISSING'
        END::TEXT as validation_result
    FROM (VALUES 
        ('tracking_sessions'),
        ('individuals'),
        ('individual_video_appearances'),
        ('video_processing_states'),
        ('cached_person_objects'),
        ('session_individuals'),
        ('algorithm_configurations')
    ) AS required_tables(table_name)
    LEFT JOIN information_schema.tables t 
        ON t.table_name = required_tables.table_name 
        AND t.table_schema = 'public';
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- PERFORMANCE MONITORING
-- =============================================

-- Create view for session performance metrics
CREATE OR REPLACE VIEW session_performance_metrics AS
SELECT 
    ts.session_uuid,
    ts.user_id,
    ts.status,
    ts.total_videos,
    ts.processed_videos,
    ts.cache_hits,
    ts.individuals_found,
    ts.processing_time_seconds,
    CASE 
        WHEN ts.total_videos > 0 THEN (ts.cache_hits::FLOAT / ts.total_videos * 100)
        ELSE 0 
    END as cache_hit_rate_percent,
    CASE 
        WHEN ts.processing_time_seconds > 0 AND ts.total_videos > 0 
        THEN (ts.total_videos::FLOAT / ts.processing_time_seconds)
        ELSE 0 
    END as videos_per_second,
    ts.created_at,
    ts.completed_at
FROM tracking_sessions ts;

-- Create view for cache statistics
CREATE OR REPLACE VIEW cache_statistics AS
SELECT 
    COUNT(DISTINCT video_uuid) as total_cached_videos,
    COUNT(*) as total_cache_records,
    SUM(access_count) as total_accesses,
    AVG(access_count) as avg_accesses_per_record,
    SUM(octet_length(person_objects::TEXT)) / (1024 * 1024) as cache_size_mb,
    MIN(created_at) as oldest_cache_entry,
    MAX(created_at) as newest_cache_entry
FROM cached_person_objects;

-- =============================================
-- CLEANUP FUNCTIONS
-- =============================================

-- Function to clean up old cache entries
CREATE OR REPLACE FUNCTION cleanup_old_cache_entries(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM cached_person_objects 
    WHERE last_accessed < NOW() - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up completed sessions older than specified days
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM tracking_sessions 
    WHERE status = 'completed' 
    AND completed_at < NOW() - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- COMPLETION MESSAGE
-- =============================================

-- Log successful schema creation
DO $$
BEGIN
    RAISE NOTICE '✅ Cross-Video Individual Tracking Database Schema Created Successfully!';
    RAISE NOTICE '📊 Schema includes:';
    RAISE NOTICE '   - 7 core tables with proper constraints';
    RAISE NOTICE '   - Performance indexes (to be added in next migration)';
    RAISE NOTICE '   - Utility functions and triggers';
    RAISE NOTICE '   - Validation functions';
    RAISE NOTICE '   - Performance monitoring views';
    RAISE NOTICE '   - Default algorithm configurations';
    RAISE NOTICE '📅 Created: October 20, 2025';
    RAISE NOTICE '🎯 Ready for Phase 1.2: Performance Indexes';
END $$;