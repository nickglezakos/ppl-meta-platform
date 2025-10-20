-- Migration: Create Recording Session Tracking Tables
-- Date: 2025-10-15
-- Purpose: Implement Phase 1 database infrastructure for camera recording session tracking
-- Based on: CAMERA_SEGMENT_RECORDING_DOCUMENTATION.md

BEGIN;

-- ==============================================================================
-- 1. Core Recording Sessions Table
-- ==============================================================================
CREATE TABLE recording_sessions (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) UNIQUE NOT NULL,
    camera_id INTEGER REFERENCES cameras(id),
    user_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'completed', 'failed', 'stopped')),
    started_at TIMESTAMP DEFAULT NOW(),
    stopped_at TIMESTAMP NULL,
    recording_quality VARCHAR(20) DEFAULT 'high' CHECK (recording_quality IN ('low', 'medium', 'high')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Additional tracking fields
    current_duration_seconds REAL DEFAULT 0,
    estimated_file_size_bytes BIGINT DEFAULT 0,
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    error_message TEXT NULL,
    frames_recorded INTEGER DEFAULT 0,
    average_fps REAL NULL
);

-- Indexes for performance
CREATE INDEX idx_recording_sessions_uuid ON recording_sessions(session_uuid);
CREATE INDEX idx_recording_sessions_camera ON recording_sessions(camera_id);
CREATE INDEX idx_recording_sessions_user ON recording_sessions(user_id);
CREATE INDEX idx_recording_sessions_status ON recording_sessions(status);
CREATE INDEX idx_recording_sessions_started ON recording_sessions(started_at);

-- ==============================================================================
-- 2. Recording Metadata Storage
-- ==============================================================================
CREATE TABLE recording_metadata (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    recording_profile_id INTEGER NULL, -- Future: link to recording profiles
    
    -- Configuration parameters
    segment_interval_seconds INTEGER NULL,
    segment_duration_seconds INTEGER DEFAULT 30,
    auto_face_detection_enabled BOOLEAN DEFAULT TRUE,
    video_codec VARCHAR(20) DEFAULT 'h264',
    audio_enabled BOOLEAN DEFAULT FALSE,
    
    -- Technical specifications
    resolution_width INTEGER,
    resolution_height INTEGER,
    fps INTEGER,
    bitrate INTEGER,
    
    -- Processing settings
    face_detection_method VARCHAR(20) DEFAULT 'two_stage',
    quality_preset VARCHAR(20) DEFAULT 'balanced',
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    UNIQUE(session_uuid) -- One metadata record per session
);

CREATE INDEX idx_recording_metadata_session ON recording_metadata(session_uuid);
CREATE INDEX idx_recording_metadata_profile ON recording_metadata(recording_profile_id);

-- ==============================================================================
-- 3. Recording File Path Management
-- ==============================================================================
CREATE TABLE recording_files (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    file_uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- File location and organization
    file_path VARCHAR(500) NOT NULL,
    relative_path VARCHAR(500) NOT NULL, -- Path relative to storage root
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT DEFAULT 0,
    
    -- File type and format
    mime_type VARCHAR(100) DEFAULT 'video/mp4',
    video_codec VARCHAR(20),
    audio_codec VARCHAR(20) NULL,
    duration_seconds REAL DEFAULT 0,
    
    -- Storage backend information
    storage_type VARCHAR(20) DEFAULT 'local' CHECK (storage_type IN ('local', 's3', 'gcs', 'azure')),
    storage_bucket VARCHAR(100) NULL,
    storage_region VARCHAR(50) NULL,
    
    -- File integrity and verification
    checksum_md5 VARCHAR(32) NULL,
    checksum_sha256 VARCHAR(64) NULL,
    file_verified_at TIMESTAMP NULL,
    
    -- Media service integration
    is_uploaded_to_media BOOLEAN DEFAULT FALSE,
    media_collection_id VARCHAR(36) NULL,
    media_uuid VARCHAR(36) NULL, -- UUID from media service
    media_upload_attempted_at TIMESTAMP NULL,
    media_upload_completed_at TIMESTAMP NULL,
    
    -- Lifecycle management
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP NULL,
    retention_until TIMESTAMP NULL,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_recording_files_session ON recording_files(session_uuid);
CREATE INDEX idx_recording_files_uuid ON recording_files(file_uuid);
CREATE INDEX idx_recording_files_media_uuid ON recording_files(media_uuid);
CREATE INDEX idx_recording_files_path ON recording_files(file_path);
CREATE INDEX idx_recording_files_upload_status ON recording_files(is_uploaded_to_media);
CREATE INDEX idx_recording_files_storage_type ON recording_files(storage_type);
CREATE INDEX idx_recording_files_lifecycle ON recording_files(is_archived, is_deleted);

-- ==============================================================================
-- 4. Recording Status and Duration Tracking
-- ==============================================================================
CREATE TABLE recording_status (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    
    -- Real-time recording metrics
    current_duration_seconds REAL DEFAULT 0,
    current_file_size_bytes BIGINT DEFAULT 0,
    frames_recorded INTEGER DEFAULT 0,
    frames_dropped INTEGER DEFAULT 0,
    average_fps REAL NULL,
    current_bitrate INTEGER NULL,
    
    -- System performance metrics
    cpu_usage_percent REAL NULL,
    memory_usage_mb REAL NULL,
    disk_space_available_mb BIGINT NULL,
    network_upload_speed_mbps REAL NULL,
    
    -- Error tracking
    error_count INTEGER DEFAULT 0,
    last_error_message TEXT NULL,
    last_error_at TIMESTAMP NULL,
    
    -- Timestamps
    reported_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance monitoring queries
CREATE INDEX idx_recording_status_session ON recording_status(session_uuid);
CREATE INDEX idx_recording_status_reported ON recording_status(reported_at);
CREATE INDEX idx_recording_status_duration ON recording_status(current_duration_seconds);

-- ==============================================================================
-- 5. Session Workflow Integration
-- ==============================================================================
-- Add session tracking to existing camera_sessions table if needed
ALTER TABLE camera_sessions ADD COLUMN recording_session_uuid VARCHAR(36) NULL;
CREATE INDEX idx_camera_sessions_recording ON camera_sessions(recording_session_uuid);

-- ==============================================================================
-- 6. Database Functions for Session Management
-- ==============================================================================

-- Function to get active recording sessions for a camera
CREATE OR REPLACE FUNCTION get_active_recording_sessions(camera_device_id VARCHAR)
RETURNS TABLE(
    session_uuid VARCHAR,
    status VARCHAR,
    started_at TIMESTAMP,
    current_duration_seconds REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rs.session_uuid,
        rs.status,
        rs.started_at,
        rs.current_duration_seconds
    FROM recording_sessions rs
    JOIN cameras c ON rs.camera_id = c.id
    WHERE c.device_id = camera_device_id 
    AND rs.status = 'active'
    ORDER BY rs.started_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get session with all associated files
CREATE OR REPLACE FUNCTION get_session_with_files(session_id VARCHAR)
RETURNS TABLE(
    session_uuid VARCHAR,
    session_status VARCHAR,
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    file_uuid VARCHAR,
    media_uuid VARCHAR,
    file_path VARCHAR,
    file_size_bytes BIGINT,
    is_uploaded_to_media BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rs.session_uuid,
        rs.status,
        rs.started_at,
        rs.stopped_at,
        rf.file_uuid,
        rf.media_uuid,
        rf.file_path,
        rf.file_size_bytes,
        rf.is_uploaded_to_media
    FROM recording_sessions rs
    LEFT JOIN recording_files rf ON rs.session_uuid = rf.session_uuid
    WHERE rs.session_uuid = session_id
    ORDER BY rf.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- 7. Triggers for Automatic Updates
-- ==============================================================================

-- Update recording_sessions.updated_at on any change
CREATE OR REPLACE FUNCTION update_recording_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_recording_session_timestamp
    BEFORE UPDATE ON recording_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_recording_session_timestamp();

-- Update recording_files.updated_at on any change
CREATE OR REPLACE FUNCTION update_recording_file_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_recording_file_timestamp
    BEFORE UPDATE ON recording_files
    FOR EACH ROW
    EXECUTE FUNCTION update_recording_file_timestamp();

-- ==============================================================================
-- 8. Sample Data for Testing
-- ==============================================================================

-- Insert a sample recording session for testing (optional)
-- INSERT INTO recording_sessions (session_uuid, camera_id, user_id, status)
-- SELECT 
--     'test-session-' || gen_random_uuid(),
--     c.id,
--     '7', -- Fresh user ID
--     'completed'
-- FROM cameras c 
-- WHERE c.device_id = 'usb_camera_0'
-- LIMIT 1;

COMMIT;

-- ==============================================================================
-- Migration Verification Queries
-- ==============================================================================

-- Verify tables were created
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('recording_sessions', 'recording_metadata', 'recording_files', 'recording_status')
ORDER BY table_name, ordinal_position;

-- Check indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('recording_sessions', 'recording_metadata', 'recording_files', 'recording_status')
ORDER BY tablename, indexname;