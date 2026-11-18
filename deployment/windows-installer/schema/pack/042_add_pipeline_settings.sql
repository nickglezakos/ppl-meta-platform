-- Migration: Add pipeline settings to cameras table
-- Date: 2026-01-24
-- Description: Add instant detection and recording pipeline configuration columns to cameras table

-- Add pipeline configuration columns
ALTER TABLE cameras 
  ADD COLUMN IF NOT EXISTS instant_detection_enabled BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS recording_pipeline_enabled BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS instant_detection_interval_seconds INTEGER DEFAULT 5,
  ADD COLUMN IF NOT EXISTS segment_duration_seconds INTEGER DEFAULT 30;

-- Add constraint to ensure at least one pipeline is enabled
ALTER TABLE cameras
  DROP CONSTRAINT IF EXISTS at_least_one_pipeline_enabled;

ALTER TABLE cameras
  ADD CONSTRAINT at_least_one_pipeline_enabled
  CHECK (instant_detection_enabled OR recording_pipeline_enabled);

-- Update existing cameras to have both pipelines enabled (backward compatibility)
UPDATE cameras
SET 
  instant_detection_enabled = TRUE,
  recording_pipeline_enabled = TRUE,
  instant_detection_interval_seconds = 5,
  segment_duration_seconds = 30
WHERE 
  instant_detection_enabled IS NULL 
  OR recording_pipeline_enabled IS NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_cameras_pipeline_settings 
  ON cameras(instant_detection_enabled, recording_pipeline_enabled);

-- Verification query (run manually to verify)
-- SELECT device_id, instant_detection_enabled, recording_pipeline_enabled, 
--        instant_detection_interval_seconds, segment_duration_seconds 
-- FROM cameras LIMIT 10;
