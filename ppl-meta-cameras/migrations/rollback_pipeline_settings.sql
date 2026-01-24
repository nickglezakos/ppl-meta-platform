-- Rollback Migration: Remove pipeline settings from cameras table
-- Date: 2026-01-24
-- Description: Rollback script to remove pipeline configuration columns if needed

-- Drop constraint first
ALTER TABLE cameras
  DROP CONSTRAINT IF EXISTS at_least_one_pipeline_enabled;

-- Drop index
DROP INDEX IF EXISTS idx_cameras_pipeline_settings;

-- Remove columns
ALTER TABLE cameras 
  DROP COLUMN IF EXISTS instant_detection_enabled,
  DROP COLUMN IF EXISTS recording_pipeline_enabled,
  DROP COLUMN IF EXISTS instant_detection_interval_seconds,
  DROP COLUMN IF EXISTS segment_duration_seconds;

-- Verification query (run manually to verify)
-- SELECT * FROM cameras LIMIT 1;
