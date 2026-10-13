-- Add workflow settings columns to cameras table
-- These fields enable per-camera face detection and performance optimization configuration

ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS auto_face_detection BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS detection_methods JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS processing_options JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS confidence_threshold DOUBLE PRECISION DEFAULT 0.7,
ADD COLUMN IF NOT EXISTS enable_performance_optimization BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS show_performance_indicators BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS default_playback_mode VARCHAR(50) DEFAULT 'auto',
ADD COLUMN IF NOT EXISTS mvr_quality_threshold DOUBLE PRECISION DEFAULT 0.20;

-- Add index for auto_face_detection for faster queries
CREATE INDEX IF NOT EXISTS idx_cameras_auto_face_detection ON cameras(auto_face_detection);

-- Add comments for documentation
COMMENT ON COLUMN cameras.auto_face_detection IS 'Enable automatic face detection for this camera';
COMMENT ON COLUMN cameras.detection_methods IS 'Array of face detection methods to use: opencv, dlib, mtcnn, yolo';
COMMENT ON COLUMN cameras.processing_options IS 'Additional processing configuration options';
COMMENT ON COLUMN cameras.confidence_threshold IS 'Minimum confidence threshold for face detection (0.0-1.0)';
COMMENT ON COLUMN cameras.enable_performance_optimization IS 'Enable performance optimization (Workflow 5) for CPU reduction';
COMMENT ON COLUMN cameras.show_performance_indicators IS 'Display performance metrics and CPU usage indicators';
COMMENT ON COLUMN cameras.default_playback_mode IS 'Default playback mode: auto, optimized, standard';
COMMENT ON COLUMN cameras.mvr_quality_threshold IS 'Minimum quality threshold for creating MVR people (0.0-1.0)';
