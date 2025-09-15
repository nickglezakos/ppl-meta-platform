-- ================================================================
-- PPL Meta Vision Service - Migration 001 ROLLBACK
-- Session-Based Face Detection Schema Rollback
-- 
-- Date: September 15, 2025
-- Version: 2.17.2
-- Purpose: Safely rollback session-based tracking schema changes
-- 
-- WARNING: This will remove all session tracking data!
-- Only use this if you need to revert the migration completely.
-- ================================================================

-- Begin Transaction
BEGIN;

-- ================================================================
-- 1. REMOVE TRIGGERS AND FUNCTIONS
-- ================================================================
DROP TRIGGER IF EXISTS trigger_face_detection_sessions_updated_at ON face_detection_sessions;
DROP TRIGGER IF EXISTS trigger_media_processing_status_updated_at ON media_processing_status;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- ================================================================
-- 2. REMOVE FOREIGN KEY CONSTRAINTS
-- ================================================================
ALTER TABLE face_detections 
    DROP CONSTRAINT IF EXISTS fk_face_detections_session_uuid;

ALTER TABLE media_processing_status 
    DROP CONSTRAINT IF EXISTS fk_media_processing_session_uuid;

-- ================================================================
-- 3. REMOVE CHECK CONSTRAINTS
-- ================================================================
ALTER TABLE face_detection_sessions 
    DROP CONSTRAINT IF EXISTS chk_session_type;

ALTER TABLE face_detection_sessions 
    DROP CONSTRAINT IF EXISTS chk_processing_status;

ALTER TABLE face_detection_sessions 
    DROP CONSTRAINT IF EXISTS chk_session_uuid_format;

ALTER TABLE face_detection_sessions 
    DROP CONSTRAINT IF EXISTS chk_session_time_order;

ALTER TABLE face_detection_sessions 
    DROP CONSTRAINT IF EXISTS chk_faces_count_positive;

-- ================================================================
-- 4. REMOVE INDEXES
-- ================================================================
-- face_detection_sessions indexes
DROP INDEX IF EXISTS idx_face_detection_sessions_media_uuid;
DROP INDEX IF EXISTS idx_face_detection_sessions_camera_device;
DROP INDEX IF EXISTS idx_face_detection_sessions_status;
DROP INDEX IF EXISTS idx_face_detection_sessions_type;
DROP INDEX IF EXISTS idx_face_detection_sessions_started_at;

-- face_detections session-related indexes
DROP INDEX IF EXISTS idx_face_detections_session_uuid;
DROP INDEX IF EXISTS idx_face_detections_session_frame;

-- media_processing_status indexes
DROP INDEX IF EXISTS idx_media_processing_status_processed;
DROP INDEX IF EXISTS idx_media_processing_status_session;
DROP INDEX IF EXISTS idx_media_processing_status_updated;

-- ================================================================
-- 5. REMOVE COLUMN FROM EXISTING TABLE
-- ================================================================
-- Remove session_uuid column from face_detections
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'face_detections' 
        AND column_name = 'session_uuid'
    ) THEN
        ALTER TABLE face_detections DROP COLUMN session_uuid;
    END IF;
END $$;

-- ================================================================
-- 6. DROP NEW TABLES
-- ================================================================
-- Drop media_processing_status table
DROP TABLE IF EXISTS media_processing_status;

-- Drop face_detection_sessions table  
DROP TABLE IF EXISTS face_detection_sessions;

-- ================================================================
-- 7. REMOVE MIGRATION RECORD
-- ================================================================
DELETE FROM schema_migrations WHERE version = '001';

-- Commit Transaction
COMMIT;

-- ================================================================
-- VERIFICATION QUERIES
-- ================================================================
-- Run these queries to verify the rollback was successful

-- Check tables were removed
SELECT 
    table_name 
FROM information_schema.tables 
WHERE table_name IN ('face_detection_sessions', 'media_processing_status')
    AND table_schema = 'public';

-- Check column was removed
SELECT 
    column_name 
FROM information_schema.columns 
WHERE table_name = 'face_detections' 
    AND column_name = 'session_uuid'
    AND table_schema = 'public';

-- Check migration record was removed
SELECT version FROM schema_migrations WHERE version = '001';

-- Rollback complete message
SELECT 'Migration 001 ROLLBACK: Session-Based Face Detection Schema - COMPLETED SUCCESSFULLY' AS status;