-- Migration 004: object_detections for body / generic object boxes (Phase C slim).
-- Never store body detections in face_detections.

CREATE TABLE IF NOT EXISTS object_detections (
    id TEXT PRIMARY KEY,
    media_id TEXT,
    session_uuid TEXT,
    frame_number INTEGER,
    timestamp REAL,
    bbox_x1 INTEGER NOT NULL,
    bbox_y1 INTEGER NOT NULL,
    bbox_x2 INTEGER NOT NULL,
    bbox_y2 INTEGER NOT NULL,
    confidence REAL NOT NULL,
    class_id INTEGER,
    class_label TEXT,
    capability TEXT NOT NULL DEFAULT 'body_detection',
    method TEXT,
    model_id VARCHAR(128),
    model_version VARCHAR(64),
    recipe_id VARCHAR(128),
    runtime VARCHAR(64),
    confidence_threshold REAL,
    path VARCHAR(32),
    serving BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_object_detections_media
    ON object_detections (media_id);

CREATE INDEX IF NOT EXISTS idx_object_detections_session
    ON object_detections (session_uuid);

CREATE INDEX IF NOT EXISTS idx_object_detections_capability
    ON object_detections (capability);

CREATE INDEX IF NOT EXISTS idx_object_detections_model
    ON object_detections (model_id, model_version);

CREATE INDEX IF NOT EXISTS idx_object_detections_session_frame
    ON object_detections (session_uuid, frame_number);
