-- ================================================================
-- PPL Meta Vision Service - Migration 001
-- Session-Based Face Detection Schema Implementation
-- 
-- Date: September 15, 2025
-- Version: 2.17.2
-- Purpose: Add session-based tracking tables for Workflow 4
-- 
-- Changes:
-- 1. Create face_detection_sessions table
-- 2. Create media_processing_status table  
-- 3. Add session_uuid column to existing face_detections table
-- 4. Create performance indexes
-- ================================================================

-- Begin Transaction
BEGIN;

-- ================================================================
-- 1. CREATE face_detection_sessions TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS face_detection_sessions (
    session_uuid VARCHAR(36) PRIMARY KEY,
    media_uuid VARCHAR(36) NOT NULL,
    camera_device_uuid VARCHAR(36),
    session_type VARCHAR(20) NOT NULL DEFAULT 'streaming',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    total_faces_detected INTEGER DEFAULT 0,
    processing_status VARCHAR(20) NOT NULL DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to document the table structure
COMMENT ON TABLE face_detection_sessions IS 'Track face detection sessions with complete traceability from camera device to individual faces';
COMMENT ON COLUMN face_detection_sessions.session_uuid IS 'Unique identifier for each face detection session';
COMMENT ON COLUMN face_detection_sessions.media_uuid IS 'Reference to media file being processed';
COMMENT ON COLUMN face_detection_sessions.camera_device_uuid IS 'Optional reference to camera device that captured the media';
COMMENT ON COLUMN face_detection_sessions.session_type IS 'Type of session: streaming, bulk_processing';
COMMENT ON COLUMN face_detection_sessions.processing_status IS 'Status: active, completed, failed';
COMMENT ON COLUMN face_detection_sessions.metadata IS 'Additional session metadata (user_id, detection_settings, etc.)';

-- ================================================================
-- 2. CREATE media_processing_status TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS media_processing_status (
    media_uuid VARCHAR(36) PRIMARY KEY,
    face_detection_processed BOOLEAN DEFAULT FALSE,
    face_detection_session_uuid VARCHAR(36),
    processing_completed_at TIMESTAMP NULL,
    total_frames_processed INTEGER,
    total_faces_detected INTEGER,
    processing_method VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments for documentation
COMMENT ON TABLE media_processing_status IS 'Track processing status of media files for optimized playback';
COMMENT ON COLUMN media_processing_status.face_detection_processed IS 'Whether media has been fully processed for face detection';
COMMENT ON COLUMN media_processing_status.face_detection_session_uuid IS 'Reference to the processing session';
COMMENT ON COLUMN media_processing_status.processing_method IS 'Detection method used: two_stage, haar, dlib, mtcnn';

-- ================================================================
-- 3. ADD session_uuid COLUMN TO EXISTING face_detections TABLE
-- ================================================================
-- Check if column already exists before adding
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'face_detections' 
        AND column_name = 'session_uuid'
    ) THEN
        ALTER TABLE face_detections ADD COLUMN session_uuid VARCHAR(36);
        COMMENT ON COLUMN face_detections.session_uuid IS 'Reference to face detection session for complete traceability';
    END IF;
END $$;

-- ================================================================
-- 4. CREATE FOREIGN KEY CONSTRAINTS
-- ================================================================
-- Add foreign key constraint for session relationship
DO $$
BEGIN
    -- Add FK constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_face_detections_session_uuid'
        AND table_name = 'face_detections'
    ) THEN
        ALTER TABLE face_detections 
        ADD CONSTRAINT fk_face_detections_session_uuid 
        FOREIGN KEY (session_uuid) REFERENCES face_detection_sessions(session_uuid)
        ON DELETE SET NULL;
    END IF;
END $$;

-- Add FK constraint for media processing status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_media_processing_session_uuid'
        AND table_name = 'media_processing_status'
    ) THEN
        ALTER TABLE media_processing_status 
        ADD CONSTRAINT fk_media_processing_session_uuid 
        FOREIGN KEY (face_detection_session_uuid) REFERENCES face_detection_sessions(session_uuid)
        ON DELETE SET NULL;
    END IF;
END $$;

-- ================================================================
-- 5. CREATE PERFORMANCE INDEXES
-- ================================================================

-- Indexes for face_detection_sessions table
CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_media_uuid 
    ON face_detection_sessions(media_uuid);

CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_camera_device 
    ON face_detection_sessions(camera_device_uuid);

CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_status 
    ON face_detection_sessions(processing_status);

CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_type 
    ON face_detection_sessions(session_type);

CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_started_at 
    ON face_detection_sessions(started_at);

-- Index for face_detections session lookup
CREATE INDEX IF NOT EXISTS idx_face_detections_session_uuid 
    ON face_detections(session_uuid);

-- Composite index for efficient session face queries
CREATE INDEX IF NOT EXISTS idx_face_detections_session_frame 
    ON face_detections(session_uuid, frame_number);

-- Indexes for media_processing_status table
CREATE INDEX IF NOT EXISTS idx_media_processing_status_processed 
    ON media_processing_status(face_detection_processed);

CREATE INDEX IF NOT EXISTS idx_media_processing_status_session 
    ON media_processing_status(face_detection_session_uuid);

CREATE INDEX IF NOT EXISTS idx_media_processing_status_updated 
    ON media_processing_status(last_updated);

-- ================================================================
-- 6. CREATE DATA VALIDATION CONSTRAINTS
-- ================================================================

-- Session type validation
ALTER TABLE face_detection_sessions 
    ADD CONSTRAINT chk_session_type 
    CHECK (session_type IN ('streaming', 'bulk_processing'));

-- Processing status validation
ALTER TABLE face_detection_sessions 
    ADD CONSTRAINT chk_processing_status 
    CHECK (processing_status IN ('active', 'completed', 'failed'));

-- UUID format validation (basic check)
ALTER TABLE face_detection_sessions 
    ADD CONSTRAINT chk_session_uuid_format 
    CHECK (LENGTH(session_uuid) = 36 AND session_uuid ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

-- Ensure started_at is before ended_at when both are present
ALTER TABLE face_detection_sessions 
    ADD CONSTRAINT chk_session_time_order 
    CHECK (ended_at IS NULL OR ended_at >= started_at);

-- Ensure total_faces_detected is non-negative
ALTER TABLE face_detection_sessions 
    ADD CONSTRAINT chk_faces_count_positive 
    CHECK (total_faces_detected >= 0);

-- ================================================================
-- 7. CREATE UPDATE TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- ================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for face_detection_sessions
DROP TRIGGER IF EXISTS trigger_face_detection_sessions_updated_at ON face_detection_sessions;
CREATE TRIGGER trigger_face_detection_sessions_updated_at
    BEFORE UPDATE ON face_detection_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for media_processing_status
DROP TRIGGER IF EXISTS trigger_media_processing_status_updated_at ON media_processing_status;
CREATE TRIGGER trigger_media_processing_status_updated_at
    BEFORE UPDATE ON media_processing_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- 8. INSERT MIGRATION RECORD
-- ================================================================
-- Create migrations table if it doesn't exist
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT
);

-- Record this migration
INSERT INTO schema_migrations (version, description, checksum) 
VALUES ('001', 'Session-Based Face Detection Schema Implementation', 'migration-001-workflow4-session-schema')
ON CONFLICT (version) DO NOTHING;

-- Commit Transaction
COMMIT;

-- ================================================================
-- VERIFICATION QUERIES
-- ================================================================
-- Run these queries to verify the migration was successful

-- Check table creation
SELECT 
    table_name, 
    table_type 
FROM information_schema.tables 
WHERE table_name IN ('face_detection_sessions', 'media_processing_status')
    AND table_schema = 'public';

-- Check column addition
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'face_detections' 
    AND column_name = 'session_uuid'
    AND table_schema = 'public';

-- Check indexes
SELECT 
    indexname, 
    tablename 
FROM pg_indexes 
WHERE tablename IN ('face_detection_sessions', 'face_detections', 'media_processing_status')
    AND schemaname = 'public'
ORDER BY tablename, indexname;

-- Check constraints
SELECT 
    constraint_name, 
    table_name, 
    constraint_type 
FROM information_schema.table_constraints 
WHERE table_name IN ('face_detection_sessions', 'face_detections', 'media_processing_status')
    AND table_schema = 'public'
ORDER BY table_name, constraint_type;

-- Migration complete message
SELECT 'Migration 001: Session-Based Face Detection Schema - COMPLETED SUCCESSFULLY' AS status;