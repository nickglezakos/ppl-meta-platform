-- ppl-meta-orchestrator/migrations/create_recording_sessions.sql
-- Migration for Recording Session Tracking - Phase 4 Implementation
-- Creates tables for comprehensive recording session management and workflow tracking

-- Create recording sessions table
CREATE TABLE IF NOT EXISTS recording_sessions (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- Camera and user context
    camera_device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    recording_profile_id INTEGER NULL,
    
    -- Session status and lifecycle
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'stopped', 'timeout')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    stopped_at TIMESTAMP NULL,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Recording configuration and metadata
    recording_config JSONB NULL,
    workflow_metadata JSONB NULL,
    
    -- Performance and tracking
    current_duration_seconds REAL DEFAULT 0.0,
    estimated_file_size_bytes BIGINT DEFAULT 0,
    frames_recorded INTEGER DEFAULT 0,
    average_fps REAL NULL,
    
    -- Error handling and diagnostics
    error_message TEXT NULL,
    warning_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    
    -- Workflow integration
    face_detection_triggered BOOLEAN DEFAULT FALSE,
    face_detection_completed BOOLEAN DEFAULT FALSE,
    face_detection_session_uuid VARCHAR(36) NULL,
    workflow_execution_id VARCHAR(36) NULL,
    
    -- Media service integration
    media_upload_started BOOLEAN DEFAULT FALSE,
    media_upload_completed BOOLEAN DEFAULT FALSE,
    media_collection_id VARCHAR(36) NULL,
    media_uuid VARCHAR(36) NULL,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for recording sessions
CREATE INDEX IF NOT EXISTS idx_recording_sessions_uuid ON recording_sessions(session_uuid);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_camera ON recording_sessions(camera_device_id);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_user ON recording_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_status ON recording_sessions(status);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_started ON recording_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_profile ON recording_sessions(recording_profile_id);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_workflow ON recording_sessions(workflow_execution_id);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_media_uuid ON recording_sessions(media_uuid);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_face_detection ON recording_sessions(face_detection_session_uuid);
CREATE INDEX IF NOT EXISTS idx_recording_sessions_heartbeat ON recording_sessions(last_heartbeat);

-- Create recording session status table for time-series monitoring
CREATE TABLE IF NOT EXISTS recording_session_status (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) NOT NULL REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    status_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Recording progress
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    file_size_bytes BIGINT DEFAULT 0,
    frames_recorded INTEGER DEFAULT 0,
    current_fps REAL NULL,
    
    -- System performance metrics
    cpu_usage_percent REAL NULL,
    memory_usage_mb INTEGER NULL,
    disk_write_speed_mbps REAL NULL,
    disk_space_available_gb REAL NULL,
    
    -- Quality metrics
    video_bitrate_kbps INTEGER NULL,
    audio_bitrate_kbps INTEGER NULL,
    frame_drop_count INTEGER DEFAULT 0,
    encoding_lag_seconds REAL DEFAULT 0.0,
    
    -- Error tracking
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    last_error TEXT NULL,
    last_warning TEXT NULL,
    
    -- Additional context
    context_data JSONB NULL
);

-- Create indexes for recording session status
CREATE INDEX IF NOT EXISTS idx_recording_session_status_session ON recording_session_status(session_uuid);
CREATE INDEX IF NOT EXISTS idx_recording_session_status_timestamp ON recording_session_status(status_timestamp);
CREATE INDEX IF NOT EXISTS idx_recording_session_status_duration ON recording_session_status(duration_seconds);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_recording_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_recording_sessions_updated_at
    BEFORE UPDATE ON recording_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_recording_session_updated_at();

-- Create function to automatically update heartbeat on status updates
CREATE OR REPLACE FUNCTION update_recording_session_heartbeat()
RETURNS TRIGGER AS $$
BEGIN
    -- Update heartbeat whenever session status changes
    IF OLD.status != NEW.status OR 
       OLD.current_duration_seconds != NEW.current_duration_seconds OR
       OLD.frames_recorded != NEW.frames_recorded THEN
        NEW.last_heartbeat = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_recording_sessions_heartbeat
    BEFORE UPDATE ON recording_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_recording_session_heartbeat();

-- Create function to clean up old session status records (keep last 1000 per session)
CREATE OR REPLACE FUNCTION cleanup_old_session_status()
RETURNS void AS $$
BEGIN
    -- Keep only the last 1000 status records per session
    DELETE FROM recording_session_status 
    WHERE id NOT IN (
        SELECT id FROM (
            SELECT id, 
                   ROW_NUMBER() OVER (PARTITION BY session_uuid ORDER BY status_timestamp DESC) as rn
            FROM recording_session_status
        ) ranked 
        WHERE rn <= 1000
    );
END;
$$ language 'plpgsql';

-- Create view for active recording sessions with latest status
CREATE OR REPLACE VIEW active_recording_sessions AS
SELECT 
    rs.*,
    latest_status.duration_seconds as latest_duration,
    latest_status.current_fps as latest_fps,
    latest_status.file_size_bytes as latest_file_size,
    latest_status.status_timestamp as latest_status_timestamp
FROM recording_sessions rs
LEFT JOIN LATERAL (
    SELECT *
    FROM recording_session_status rss
    WHERE rss.session_uuid = rs.session_uuid
    ORDER BY rss.status_timestamp DESC
    LIMIT 1
) latest_status ON true
WHERE rs.status = 'active';

-- Create view for recording session summary statistics
CREATE OR REPLACE VIEW recording_session_summary AS
SELECT 
    camera_device_id,
    user_id,
    status,
    COUNT(*) as session_count,
    AVG(current_duration_seconds) as avg_duration_seconds,
    SUM(estimated_file_size_bytes) as total_file_size_bytes,
    AVG(frames_recorded) as avg_frames_recorded,
    COUNT(CASE WHEN face_detection_triggered THEN 1 END) as face_detection_count,
    COUNT(CASE WHEN media_upload_completed THEN 1 END) as completed_uploads,
    MIN(started_at) as first_session,
    MAX(started_at) as last_session
FROM recording_sessions
GROUP BY camera_device_id, user_id, status;

-- Add comments for documentation
COMMENT ON TABLE recording_sessions IS 'Comprehensive tracking of camera recording sessions with workflow integration';
COMMENT ON TABLE recording_session_status IS 'Time-series monitoring data for recording session performance';

COMMENT ON COLUMN recording_sessions.session_uuid IS 'Unique identifier for the recording session';
COMMENT ON COLUMN recording_sessions.status IS 'Current status: active, completed, failed, stopped, timeout';
COMMENT ON COLUMN recording_sessions.recording_config IS 'Recording parameters and configuration';
COMMENT ON COLUMN recording_sessions.workflow_metadata IS 'Workflow execution context and metadata';
COMMENT ON COLUMN recording_sessions.face_detection_session_uuid IS 'UUID of associated face detection session';
COMMENT ON COLUMN recording_sessions.workflow_execution_id IS 'UUID of workflow execution';
COMMENT ON COLUMN recording_sessions.last_heartbeat IS 'Last activity timestamp for monitoring';

COMMENT ON VIEW active_recording_sessions IS 'Active recording sessions with latest performance metrics';
COMMENT ON VIEW recording_session_summary IS 'Summary statistics for recording sessions by camera and user';

-- Insert example/test data (optional - remove for production)
-- INSERT INTO recording_sessions (
--     session_uuid, camera_device_id, user_id, status, recording_config
-- ) VALUES (
--     'test-session-001', 'camera-001', 'user-123', 'active',
--     '{"quality": "high", "duration": 30, "format": "mp4"}'::jsonb
-- );