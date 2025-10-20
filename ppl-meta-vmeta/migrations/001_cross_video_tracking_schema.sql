-- Cross-Video Individual Tracking Database Schema
-- PPL Meta Platform v2.19.13+
-- Migration: 001 - Initial Schema Creation
-- Created: October 20, 2025

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create tracking sessions table
CREATE TABLE IF NOT EXISTS tracking_sessions (
    session_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    collections TEXT[] NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'initialized' 
        CHECK (status IN ('initialized', 'running', 'completed', 'failed', 'partial', 'cancelled')),
    config_hash VARCHAR(64) NOT NULL,
    algorithm_config JSONB NOT NULL,
    
    -- Processing metrics
    total_videos INTEGER NOT NULL DEFAULT 0,
    processed_videos INTEGER NOT NULL DEFAULT 0,
    failed_videos TEXT[] DEFAULT '{}',
    individuals_found INTEGER NOT NULL DEFAULT 0,
    person_objects_processed INTEGER NOT NULL DEFAULT 0,
    cache_hits INTEGER NOT NULL DEFAULT 0,
    
    -- Timing information
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    processing_time_seconds FLOAT,
    
    -- Metadata
    description TEXT,
    error_message TEXT,
    
    -- Constraints
    CONSTRAINT valid_time_range CHECK (end_time > start_time),
    CONSTRAINT valid_metrics CHECK (
        processed_videos >= 0 AND 
        processed_videos <= total_videos AND
        individuals_found >= 0 AND
        person_objects_processed >= 0 AND
        cache_hits >= 0 AND
        cache_hits <= total_videos
    )
);

-- Create individuals table
CREATE TABLE IF NOT EXISTS individuals (
    individual_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_id VARCHAR(50) UNIQUE NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    -- Signature data
    spatial_signature JSONB,
    temporal_signature JSONB,
    appearance_features VECTOR(512), -- pgvector for face embeddings
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by_session UUID REFERENCES tracking_sessions(session_uuid),
    
    -- Statistics
    total_appearances INTEGER DEFAULT 0,
    total_videos INTEGER DEFAULT 0,
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE
);

-- Create individual video appearances table
CREATE TABLE IF NOT EXISTS individual_video_appearances (
    appearance_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    video_uuid UUID NOT NULL,
    person_object_uuid UUID NOT NULL,
    
    -- Temporal information
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds FLOAT GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (end_timestamp - start_timestamp))
    ) STORED,
    
    -- Spatial information
    entry_bbox FLOAT[4], -- [x, y, width, height]
    exit_bbox FLOAT[4],
    average_bbox FLOAT[4],
    bbox_trajectory JSONB, -- Array of bboxes over time
    
    -- Quality metrics
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    quality_score FLOAT CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    face_quality FLOAT CHECK (face_quality >= 0.0 AND face_quality <= 1.0),
    
    -- Processing metadata
    processing_method VARCHAR(50), -- 'cached', 'new', 'merged'
    source_session_uuid UUID REFERENCES tracking_sessions(session_uuid),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_appearance_time CHECK (end_timestamp > start_timestamp),
    CONSTRAINT unique_person_object UNIQUE (individual_uuid, video_uuid, person_object_uuid)
);

-- Create video processing states table
CREATE TABLE IF NOT EXISTS video_processing_states (
    state_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_uuid UUID NOT NULL,
    session_uuid UUID NOT NULL REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    
    -- Processing status
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'cached', 'skipped')),
    
    -- Timing
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    processing_time_ms FLOAT DEFAULT 0,
    
    -- Results
    person_objects_count INTEGER DEFAULT 0,
    individuals_created INTEGER DEFAULT 0,
    cache_source_session UUID REFERENCES tracking_sessions(session_uuid),
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    PRIMARY KEY (video_uuid, session_uuid),
    CONSTRAINT valid_processing_time CHECK (
        processing_completed_at IS NULL OR 
        processing_completed_at >= processing_started_at
    )
);

-- Create cached person objects table
CREATE TABLE IF NOT EXISTS cached_person_objects (
    cache_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(128) UNIQUE NOT NULL,
    
    -- Cache identity
    video_uuid UUID NOT NULL,
    session_uuid UUID REFERENCES tracking_sessions(session_uuid),
    config_hash VARCHAR(64) NOT NULL,
    
    -- Cached data
    person_objects JSONB NOT NULL,
    processing_metadata JSONB,
    
    -- Cache management
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    cache_size_bytes INTEGER,
    
    -- TTL and expiration
    expires_at TIMESTAMP WITH TIME ZONE,
    is_expired BOOLEAN GENERATED ALWAYS AS (
        expires_at IS NOT NULL AND expires_at < NOW()
    ) STORED,
    
    -- Validation
    checksum VARCHAR(64),
    
    -- Constraints
    CONSTRAINT cache_key_format CHECK (cache_key ~ '^[a-f0-9]{32}_[a-f0-9-]{36}$')
);

-- Create session individuals relationship table
CREATE TABLE IF NOT EXISTS session_individuals (
    session_uuid UUID NOT NULL REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    
    -- Processing information
    processing_type VARCHAR(20) NOT NULL DEFAULT 'new'
        CHECK (processing_type IN ('new', 'cached', 'merged', 'extended', 'linked')),
    confidence_contribution FLOAT CHECK (confidence_contribution >= 0.0 AND confidence_contribution <= 1.0),
    
    -- Metrics
    appearances_in_session INTEGER DEFAULT 0,
    videos_in_session INTEGER DEFAULT 0,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    PRIMARY KEY (session_uuid, individual_uuid)
);

-- Create overlap detection results table (for debugging and analysis)
CREATE TABLE IF NOT EXISTS overlap_detection_results (
    overlap_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_uuid UUID NOT NULL REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    
    -- Video pair information
    video1_uuid UUID NOT NULL,
    video2_uuid UUID NOT NULL,
    temporal_gap_seconds FLOAT NOT NULL,
    
    -- Overlap detection results
    overlaps_detected INTEGER DEFAULT 0,
    overlap_details JSONB, -- Array of overlap objects with IoU scores
    
    -- Algorithm parameters used
    iou_threshold FLOAT NOT NULL,
    confidence_threshold FLOAT NOT NULL,
    
    -- Processing metadata
    processing_time_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_video_pair CHECK (video1_uuid != video2_uuid),
    CONSTRAINT valid_gap CHECK (temporal_gap_seconds >= 0)
);

-- Create performance indexes for optimal query performance

-- Tracking sessions indexes
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_user_time 
    ON tracking_sessions(user_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_collections 
    ON tracking_sessions USING GIN(collections);
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_status 
    ON tracking_sessions(status) WHERE status != 'completed';
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_config_hash 
    ON tracking_sessions(config_hash);
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_created_at 
    ON tracking_sessions(created_at DESC);

-- Individuals indexes
CREATE INDEX IF NOT EXISTS idx_individuals_confidence 
    ON individuals(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_individuals_created_session 
    ON individuals(created_by_session);
CREATE INDEX IF NOT EXISTS idx_individuals_temporal 
    ON individuals(first_seen, last_seen);
CREATE INDEX IF NOT EXISTS idx_individuals_appearance_count 
    ON individuals(total_appearances DESC);

-- Individual appearances indexes
CREATE INDEX IF NOT EXISTS idx_appearances_individual 
    ON individual_video_appearances(individual_uuid);
CREATE INDEX IF NOT EXISTS idx_appearances_video 
    ON individual_video_appearances(video_uuid);
CREATE INDEX IF NOT EXISTS idx_appearances_temporal 
    ON individual_video_appearances(start_timestamp, end_timestamp);
CREATE INDEX IF NOT EXISTS idx_appearances_confidence 
    ON individual_video_appearances(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_appearances_session 
    ON individual_video_appearances(source_session_uuid);

-- Video processing states indexes
CREATE INDEX IF NOT EXISTS idx_video_processing_status 
    ON video_processing_states(processing_status);
CREATE INDEX IF NOT EXISTS idx_video_processing_session 
    ON video_processing_states(session_uuid);
CREATE INDEX IF NOT EXISTS idx_video_processing_video 
    ON video_processing_states(video_uuid);
CREATE INDEX IF NOT EXISTS idx_video_processing_time 
    ON video_processing_states(processing_completed_at DESC);

-- Cached objects indexes
CREATE INDEX IF NOT EXISTS idx_cached_objects_config 
    ON cached_person_objects(config_hash, video_uuid);
CREATE INDEX IF NOT EXISTS idx_cached_objects_video 
    ON cached_person_objects(video_uuid);
CREATE INDEX IF NOT EXISTS idx_cached_objects_access 
    ON cached_person_objects(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_cached_objects_session 
    ON cached_person_objects(session_uuid);
CREATE INDEX IF NOT EXISTS idx_cached_objects_expiry 
    ON cached_person_objects(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cached_objects_size 
    ON cached_person_objects(cache_size_bytes DESC);

-- Session individuals indexes
CREATE INDEX IF NOT EXISTS idx_session_individuals_session 
    ON session_individuals(session_uuid);
CREATE INDEX IF NOT EXISTS idx_session_individuals_individual 
    ON session_individuals(individual_uuid);
CREATE INDEX IF NOT EXISTS idx_session_individuals_processing_type 
    ON session_individuals(processing_type);

-- Overlap results indexes
CREATE INDEX IF NOT EXISTS idx_overlap_results_session 
    ON overlap_detection_results(session_uuid);
CREATE INDEX IF NOT EXISTS idx_overlap_results_videos 
    ON overlap_detection_results(video1_uuid, video2_uuid);
CREATE INDEX IF NOT EXISTS idx_overlap_results_gap 
    ON overlap_detection_results(temporal_gap_seconds);

-- Vector similarity index for face embeddings (if using pgvector)
CREATE INDEX IF NOT EXISTS idx_individuals_appearance_features 
    ON individuals USING ivfflat (appearance_features vector_cosine_ops)
    WITH (lists = 100);

-- Partial indexes for active sessions
CREATE INDEX IF NOT EXISTS idx_active_sessions 
    ON tracking_sessions(session_uuid, status) 
    WHERE status IN ('initialized', 'running');

-- Partial indexes for recent cache entries
CREATE INDEX IF NOT EXISTS idx_recent_cache 
    ON cached_person_objects(video_uuid, config_hash, last_accessed) 
    WHERE last_accessed > NOW() - INTERVAL '30 days';

-- Add helpful views for common queries

-- View for session overview with statistics
CREATE OR REPLACE VIEW session_overview AS
SELECT 
    ts.session_uuid,
    ts.user_id,
    ts.collections,
    ts.start_time,
    ts.end_time,
    ts.status,
    ts.total_videos,
    ts.processed_videos,
    ts.individuals_found,
    ts.cache_hits,
    ROUND((ts.cache_hits::FLOAT / NULLIF(ts.total_videos, 0) * 100)::NUMERIC, 2) as cache_hit_rate_percent,
    ts.processing_time_seconds,
    ts.created_at,
    ts.completed_at,
    COALESCE(si_stats.processing_types, '{}') as individual_processing_types
FROM tracking_sessions ts
LEFT JOIN (
    SELECT 
        session_uuid,
        jsonb_object_agg(processing_type, count) as processing_types
    FROM (
        SELECT 
            session_uuid, 
            processing_type, 
            COUNT(*) as count
        FROM session_individuals 
        GROUP BY session_uuid, processing_type
    ) pt
    GROUP BY session_uuid
) si_stats ON ts.session_uuid = si_stats.session_uuid;

-- View for individual summary with appearance statistics
CREATE OR REPLACE VIEW individual_summary AS
SELECT 
    i.individual_uuid,
    i.individual_id,
    i.confidence_score,
    i.total_appearances,
    i.total_videos,
    i.first_seen,
    i.last_seen,
    EXTRACT(EPOCH FROM (i.last_seen - i.first_seen)) / 3600 as lifespan_hours,
    i.created_at,
    COALESCE(session_stats.session_count, 0) as session_count,
    COALESCE(avg_confidence.avg_confidence, 0) as avg_appearance_confidence
FROM individuals i
LEFT JOIN (
    SELECT 
        individual_uuid, 
        COUNT(DISTINCT session_uuid) as session_count
    FROM session_individuals 
    GROUP BY individual_uuid
) session_stats ON i.individual_uuid = session_stats.individual_uuid
LEFT JOIN (
    SELECT 
        individual_uuid,
        AVG(confidence) as avg_confidence
    FROM individual_video_appearances 
    GROUP BY individual_uuid
) avg_confidence ON i.individual_uuid = avg_confidence.individual_uuid;

-- View for cache efficiency analysis
CREATE OR REPLACE VIEW cache_efficiency AS
SELECT 
    config_hash,
    COUNT(*) as total_entries,
    SUM(access_count) as total_accesses,
    AVG(access_count) as avg_access_count,
    SUM(cache_size_bytes) as total_size_bytes,
    AVG(cache_size_bytes) as avg_size_bytes,
    COUNT(CASE WHEN is_expired THEN 1 END) as expired_entries,
    MIN(created_at) as oldest_entry,
    MAX(last_accessed) as most_recent_access,
    COUNT(CASE WHEN last_accessed > NOW() - INTERVAL '7 days' THEN 1 END) as recent_accesses
FROM cached_person_objects
GROUP BY config_hash
ORDER BY total_accesses DESC;

-- Add helpful functions

-- Function to calculate cache hit rate for a session
CREATE OR REPLACE FUNCTION calculate_session_cache_hit_rate(session_uuid_param UUID)
RETURNS FLOAT AS $$
DECLARE
    hit_rate FLOAT;
BEGIN
    SELECT 
        CASE 
            WHEN total_videos = 0 THEN 0.0
            ELSE cache_hits::FLOAT / total_videos::FLOAT * 100
        END
    INTO hit_rate
    FROM tracking_sessions
    WHERE session_uuid = session_uuid_param;
    
    RETURN COALESCE(hit_rate, 0.0);
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM cached_person_objects 
    WHERE is_expired = true;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update individual statistics
CREATE OR REPLACE FUNCTION update_individual_stats(individual_uuid_param UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE individuals SET
        total_appearances = (
            SELECT COUNT(*)
            FROM individual_video_appearances
            WHERE individual_uuid = individual_uuid_param
        ),
        total_videos = (
            SELECT COUNT(DISTINCT video_uuid)
            FROM individual_video_appearances
            WHERE individual_uuid = individual_uuid_param
        ),
        first_seen = (
            SELECT MIN(start_timestamp)
            FROM individual_video_appearances
            WHERE individual_uuid = individual_uuid_param
        ),
        last_seen = (
            SELECT MAX(end_timestamp)
            FROM individual_video_appearances
            WHERE individual_uuid = individual_uuid_param
        ),
        updated_at = NOW()
    WHERE individual_uuid = individual_uuid_param;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for automatic statistics updates

-- Trigger to update individual stats when appearances change
CREATE OR REPLACE FUNCTION trigger_update_individual_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        PERFORM update_individual_stats(NEW.individual_uuid);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM update_individual_stats(OLD.individual_uuid);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_individual_appearances_stats
    AFTER INSERT OR UPDATE OR DELETE ON individual_video_appearances
    FOR EACH ROW EXECUTE FUNCTION trigger_update_individual_stats();

-- Trigger to update cache access tracking
CREATE OR REPLACE FUNCTION trigger_update_cache_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = NOW();
    NEW.access_count = OLD.access_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cache_access_update
    BEFORE UPDATE ON cached_person_objects
    FOR EACH ROW 
    WHEN (OLD.person_objects IS NOT DISTINCT FROM NEW.person_objects)
    EXECUTE FUNCTION trigger_update_cache_access();

-- Add comments for documentation
COMMENT ON TABLE tracking_sessions IS 'Cross-video individual tracking sessions with configuration and metrics';
COMMENT ON TABLE individuals IS 'Unique individuals identified across videos with confidence scores and signatures';
COMMENT ON TABLE individual_video_appearances IS 'Individual appearances in specific videos with spatial and temporal data';
COMMENT ON TABLE video_processing_states IS 'Processing status and results for videos within tracking sessions';
COMMENT ON TABLE cached_person_objects IS 'Cached person object detection results for performance optimization';
COMMENT ON TABLE session_individuals IS 'Many-to-many relationship between sessions and individuals created';
COMMENT ON TABLE overlap_detection_results IS 'Cross-video overlap detection results for algorithm analysis';

COMMENT ON VIEW session_overview IS 'Comprehensive session statistics with cache hit rates and processing types';
COMMENT ON VIEW individual_summary IS 'Individual statistics with appearance counts and session involvement';
COMMENT ON VIEW cache_efficiency IS 'Cache performance analysis by configuration hash';

-- Migration completion
INSERT INTO tracking_sessions (
    session_uuid,
    user_id,
    collections,
    start_time,
    end_time,
    status,
    config_hash,
    algorithm_config,
    description
) VALUES (
    uuid_generate_v4(),
    'system',
    ARRAY['migration'],
    NOW(),
    NOW(),
    'completed',
    'migration_001',
    '{"migration": "initial_schema", "version": "001"}',
    'Initial schema migration for cross-video individual tracking'
) ON CONFLICT DO NOTHING;