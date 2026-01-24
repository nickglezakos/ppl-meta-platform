-- Rollback workflow settings columns from cameras table

-- Drop index
DROP INDEX IF EXISTS idx_cameras_auto_face_detection;

-- Remove columns
ALTER TABLE cameras
DROP COLUMN IF EXISTS auto_face_detection,
DROP COLUMN IF EXISTS detection_methods,
DROP COLUMN IF EXISTS processing_options,
DROP COLUMN IF EXISTS confidence_threshold,
DROP COLUMN IF EXISTS enable_performance_optimization,
DROP COLUMN IF EXISTS show_performance_indicators,
DROP COLUMN IF EXISTS default_playback_mode,
DROP COLUMN IF EXISTS mvr_quality_threshold;
