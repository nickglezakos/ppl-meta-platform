-- Migration 003: catalog provenance on sessions and detections
-- Enables SQL filters for model_id / version and archive/delete 409 checks.

ALTER TABLE face_detection_sessions
    ADD COLUMN IF NOT EXISTS model_id VARCHAR(128),
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(64),
    ADD COLUMN IF NOT EXISTS runtime VARCHAR(64),
    ADD COLUMN IF NOT EXISTS confidence_threshold REAL,
    ADD COLUMN IF NOT EXISTS path VARCHAR(32),
    ADD COLUMN IF NOT EXISTS serving BOOLEAN DEFAULT TRUE;

ALTER TABLE face_detections
    ADD COLUMN IF NOT EXISTS model_id VARCHAR(128),
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(64),
    ADD COLUMN IF NOT EXISTS runtime VARCHAR(64),
    ADD COLUMN IF NOT EXISTS confidence_threshold REAL,
    ADD COLUMN IF NOT EXISTS path VARCHAR(32),
    ADD COLUMN IF NOT EXISTS serving BOOLEAN DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_face_detection_sessions_model
    ON face_detection_sessions (model_id, model_version);

CREATE INDEX IF NOT EXISTS idx_face_detections_model
    ON face_detections (model_id, model_version);
