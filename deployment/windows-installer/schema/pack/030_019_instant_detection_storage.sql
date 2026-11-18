-- Instant Detection Persistent Storage Schema Changes
-- PPL Meta Platform v2.25.0+
-- Migration: 019 - Instant Detection Storage
-- Created: March 2026
--
-- Purpose: Add source_type columns and expand link_method to support
--          persisting instant detection results into the existing schema.
--
-- Design Reference: docs/proposals/mvr-people-persistent-storage-for-instant-detection.md

-- ============================================================================
-- 1. tracking_sessions: Add source_type and camera_device_id
-- ============================================================================

ALTER TABLE tracking_sessions
ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'recording_pipeline'
    CHECK (source_type IN ('recording_pipeline', 'instant_detection'));

ALTER TABLE tracking_sessions
ADD COLUMN IF NOT EXISTS camera_device_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_source_type
    ON tracking_sessions(source_type);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_camera_device
    ON tracking_sessions(camera_device_id);

COMMENT ON COLUMN tracking_sessions.source_type IS 'Origin of the tracking session: recording_pipeline (default) or instant_detection';
COMMENT ON COLUMN tracking_sessions.camera_device_id IS 'Camera device ID for instant detection sessions (NULL for recording pipeline)';

-- ============================================================================
-- 2. individuals: Add source_type
-- ============================================================================

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'recording_pipeline'
    CHECK (source_type IN ('recording_pipeline', 'instant_detection'));

CREATE INDEX IF NOT EXISTS idx_individuals_source_type
    ON individuals(source_type);

COMMENT ON COLUMN individuals.source_type IS 'Origin of the individual: recording_pipeline (default) or instant_detection';

-- ============================================================================
-- 3. individual_mvr_mapping: Expand link_method CHECK constraint
-- ============================================================================

ALTER TABLE individual_mvr_mapping
DROP CONSTRAINT IF EXISTS individual_mvr_mapping_link_method_check;

ALTER TABLE individual_mvr_mapping
ADD CONSTRAINT individual_mvr_mapping_link_method_check
    CHECK (link_method IN ('auto_create', 'auto_merge', 'manual_link', 'batch_import', 'instant_detection'));

COMMENT ON COLUMN individual_mvr_mapping.link_method IS 'How this mapping was created: auto_create (1st individual), auto_merge, manual_link, batch_import, or instant_detection';

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    col_exists BOOLEAN;
BEGIN
    -- Verify tracking_sessions.source_type
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tracking_sessions' AND column_name = 'source_type'
    ) INTO col_exists;
    IF NOT col_exists THEN
        RAISE EXCEPTION 'Migration failed: tracking_sessions.source_type not found';
    END IF;

    -- Verify tracking_sessions.camera_device_id
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tracking_sessions' AND column_name = 'camera_device_id'
    ) INTO col_exists;
    IF NOT col_exists THEN
        RAISE EXCEPTION 'Migration failed: tracking_sessions.camera_device_id not found';
    END IF;

    -- Verify individuals.source_type
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'individuals' AND column_name = 'source_type'
    ) INTO col_exists;
    IF NOT col_exists THEN
        RAISE EXCEPTION 'Migration failed: individuals.source_type not found';
    END IF;

    RAISE NOTICE '✅ Migration 019_instant_detection_storage applied successfully';
END $$;
