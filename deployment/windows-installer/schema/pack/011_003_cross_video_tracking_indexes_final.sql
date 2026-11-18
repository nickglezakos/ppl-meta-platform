-- =============================================
-- Cross-Video Individual Tracking Performance Indexes (Final - Actual Schema)
-- PPL Meta Platform v2.19.13+
-- File: 003_cross_video_tracking_indexes_final.sql
-- Created: October 20, 2025
-- Purpose: Indexes based on ACTUAL schema structure
-- =============================================

-- =============================================
-- TRACKING SESSIONS INDEXES
-- =============================================

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_user_id 
ON tracking_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_status 
ON tracking_sessions(status);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_config_hash 
ON tracking_sessions(config_hash);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_created_at 
ON tracking_sessions(created_at);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_user_status 
ON tracking_sessions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_time_range 
ON tracking_sessions(start_time, end_time);

-- GIN index for collections array queries
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_collections 
ON tracking_sessions USING GIN(collections);

-- =============================================
-- INDIVIDUALS INDEXES
-- =============================================

CREATE INDEX IF NOT EXISTS idx_individuals_individual_id 
ON individuals(individual_id);

CREATE INDEX IF NOT EXISTS idx_individuals_confidence 
ON individuals(confidence_score DESC);

CREATE INDEX IF NOT EXISTS idx_individuals_created_at 
ON individuals(created_at);

CREATE INDEX IF NOT EXISTS idx_individuals_updated_at 
ON individuals(updated_at);

-- GIN indexes for JSONB signature queries
CREATE INDEX IF NOT EXISTS idx_individuals_spatial_signature 
ON individuals USING GIN(spatial_signature);

CREATE INDEX IF NOT EXISTS idx_individuals_temporal_signature 
ON individuals USING GIN(temporal_signature);

-- =============================================
-- INDIVIDUAL VIDEO APPEARANCES INDEXES (ACTUAL SCHEMA)
-- =============================================

CREATE INDEX IF NOT EXISTS idx_appearances_individual_uuid 
ON individual_video_appearances(individual_uuid);

CREATE INDEX IF NOT EXISTS idx_appearances_video_uuid 
ON individual_video_appearances(video_uuid);

CREATE INDEX IF NOT EXISTS idx_appearances_person_object_uuid 
ON individual_video_appearances(person_object_uuid);

CREATE INDEX IF NOT EXISTS idx_appearances_start_timestamp 
ON individual_video_appearances(start_timestamp);

CREATE INDEX IF NOT EXISTS idx_appearances_end_timestamp 
ON individual_video_appearances(end_timestamp);

CREATE INDEX IF NOT EXISTS idx_appearances_confidence 
ON individual_video_appearances(confidence DESC);

-- Compound indexes for common queries
CREATE INDEX IF NOT EXISTS idx_appearances_video_timerange 
ON individual_video_appearances(video_uuid, start_timestamp, end_timestamp);

CREATE INDEX IF NOT EXISTS idx_appearances_individual_timerange 
ON individual_video_appearances(individual_uuid, start_timestamp);

CREATE INDEX IF NOT EXISTS idx_appearances_person_timerange 
ON individual_video_appearances(person_object_uuid, start_timestamp);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_appearances_representative_faces 
ON individual_video_appearances USING GIN(representative_faces);

CREATE INDEX IF NOT EXISTS idx_appearances_movement_pattern 
ON individual_video_appearances USING GIN(movement_pattern);

-- Indexes for bounding box arrays
CREATE INDEX IF NOT EXISTS idx_appearances_entry_bbox 
ON individual_video_appearances USING GIN(entry_bbox);

CREATE INDEX IF NOT EXISTS idx_appearances_exit_bbox 
ON individual_video_appearances USING GIN(exit_bbox);

-- =============================================
-- VIDEO PROCESSING STATES INDEXES (ACTUAL SCHEMA)
-- =============================================

CREATE INDEX IF NOT EXISTS idx_processing_states_session_uuid 
ON video_processing_states(session_uuid);

CREATE INDEX IF NOT EXISTS idx_processing_states_video_uuid 
ON video_processing_states(video_uuid);

CREATE INDEX IF NOT EXISTS idx_processing_states_processing_status 
ON video_processing_states(processing_status);

CREATE INDEX IF NOT EXISTS idx_processing_states_processed_at 
ON video_processing_states(processed_at);

CREATE INDEX IF NOT EXISTS idx_processing_states_session_status 
ON video_processing_states(session_uuid, processing_status);

CREATE INDEX IF NOT EXISTS idx_processing_states_cache_source 
ON video_processing_states(cache_source_session);

-- Index for performance monitoring
CREATE INDEX IF NOT EXISTS idx_processing_states_performance 
ON video_processing_states(processing_status, person_objects_count, processing_time_ms);

-- =============================================
-- CACHED PERSON OBJECTS INDEXES (ACTUAL SCHEMA)
-- =============================================

CREATE INDEX IF NOT EXISTS idx_cache_video_uuid 
ON cached_person_objects(video_uuid);

CREATE INDEX IF NOT EXISTS idx_cache_session_uuid 
ON cached_person_objects(session_uuid);

CREATE INDEX IF NOT EXISTS idx_cache_config_hash 
ON cached_person_objects(config_hash);

CREATE INDEX IF NOT EXISTS idx_cache_created_at 
ON cached_person_objects(created_at);

CREATE INDEX IF NOT EXISTS idx_cache_last_accessed 
ON cached_person_objects(last_accessed);

CREATE INDEX IF NOT EXISTS idx_cache_access_count 
ON cached_person_objects(access_count DESC);

-- Compound index for cache lookup patterns
CREATE INDEX IF NOT EXISTS idx_cache_session_config 
ON cached_person_objects(session_uuid, config_hash);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_cache_person_objects 
ON cached_person_objects USING GIN(person_objects);

CREATE INDEX IF NOT EXISTS idx_cache_processing_metadata 
ON cached_person_objects USING GIN(processing_metadata);

-- =============================================
-- SESSION INDIVIDUALS INDEXES
-- =============================================

CREATE INDEX IF NOT EXISTS idx_session_individuals_session_uuid 
ON session_individuals(session_uuid);

CREATE INDEX IF NOT EXISTS idx_session_individuals_individual_uuid 
ON session_individuals(individual_uuid);

CREATE INDEX IF NOT EXISTS idx_session_individuals_processing_type 
ON session_individuals(processing_type);

CREATE INDEX IF NOT EXISTS idx_session_individuals_confidence 
ON session_individuals(confidence_contribution DESC);

CREATE INDEX IF NOT EXISTS idx_session_individuals_created_at 
ON session_individuals(created_at);

-- =============================================
-- ALGORITHM CONFIGURATIONS INDEXES
-- =============================================

CREATE INDEX IF NOT EXISTS idx_algorithm_configs_config_name 
ON algorithm_configurations(config_name);

CREATE INDEX IF NOT EXISTS idx_algorithm_configs_is_default 
ON algorithm_configurations(is_default);

CREATE INDEX IF NOT EXISTS idx_algorithm_configs_created_at 
ON algorithm_configurations(created_at);

-- GIN index for JSONB config queries
CREATE INDEX IF NOT EXISTS idx_algorithm_configs_config 
ON algorithm_configurations USING GIN(config);

-- =============================================
-- PERFORMANCE MONITORING INDEXES
-- =============================================

-- Index for session performance monitoring
CREATE INDEX IF NOT EXISTS idx_sessions_performance 
ON tracking_sessions(status, total_videos, processed_videos, created_at);

-- Index for individual tracking statistics
CREATE INDEX IF NOT EXISTS idx_individuals_stats 
ON individuals(confidence_score, created_at);

-- Index for appearance statistics
CREATE INDEX IF NOT EXISTS idx_appearances_stats 
ON individual_video_appearances(individual_uuid, confidence, start_timestamp);

-- =============================================
-- CLEANUP AND MAINTENANCE INDEXES
-- =============================================

-- Index for cache cleanup (by last accessed)
CREATE INDEX IF NOT EXISTS idx_cache_cleanup_last_accessed 
ON cached_person_objects(last_accessed);

-- Partial index for cache cleanup (by access count)
CREATE INDEX IF NOT EXISTS idx_cache_cleanup_low_access 
ON cached_person_objects(access_count, created_at) 
WHERE access_count = 0;

-- Partial index for completed sessions cleanup
CREATE INDEX IF NOT EXISTS idx_sessions_cleanup 
ON tracking_sessions(created_at, status) 
WHERE status IN ('COMPLETED', 'FAILED');

-- Partial index for failed processing states
CREATE INDEX IF NOT EXISTS idx_processing_states_errors 
ON video_processing_states(processed_at, processing_status) 
WHERE processing_status = 'failed';

-- =============================================
-- CROSS-COLLECTION TRACKING INDEXES
-- =============================================

-- Index for finding individuals across multiple sessions
CREATE INDEX IF NOT EXISTS idx_cross_session_individuals 
ON session_individuals(individual_uuid, processing_type, confidence_contribution);

-- Index for temporal analysis across sessions
CREATE INDEX IF NOT EXISTS idx_temporal_analysis 
ON individuals(confidence_score, created_at, updated_at);

-- Index for cross-video appearance patterns
CREATE INDEX IF NOT EXISTS idx_cross_video_patterns 
ON individual_video_appearances(individual_uuid, video_uuid, confidence);

-- =============================================
-- SPECIALIZED QUERY OPTIMIZATION INDEXES
-- =============================================

-- Index for timeline queries (appearances over time)
CREATE INDEX IF NOT EXISTS idx_timeline_queries 
ON individual_video_appearances(start_timestamp, end_timestamp, individual_uuid);

-- Index for confidence-based filtering
CREATE INDEX IF NOT EXISTS idx_confidence_filtering 
ON individual_video_appearances(confidence, start_timestamp) 
WHERE confidence >= 0.5;

-- Index for high-confidence individuals
CREATE INDEX IF NOT EXISTS idx_high_confidence_individuals 
ON individuals(individual_id, confidence_score) 
WHERE confidence_score >= 0.8;

-- Index for recent processing activity
CREATE INDEX IF NOT EXISTS idx_recent_processing 
ON video_processing_states(processed_at, processing_status);

-- =============================================
-- FUTURE PGVECTOR INDEXES (commented out for now)
-- =============================================

-- Note: These will be created when face_embedding columns are added
-- and contain actual vector data

-- IVFFLAT index for fast approximate nearest neighbor search
-- CREATE INDEX IF NOT EXISTS idx_faces_embedding_ivfflat 
-- ON individual_video_appearances USING ivfflat (face_embedding vector_cosine_ops)
-- WITH (lists = 100);

-- HNSW index for high-quality nearest neighbor search  
-- CREATE INDEX IF NOT EXISTS idx_faces_embedding_hnsw 
-- ON individual_video_appearances USING hnsw (face_embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- =============================================
-- END OF INDEXES
-- =============================================