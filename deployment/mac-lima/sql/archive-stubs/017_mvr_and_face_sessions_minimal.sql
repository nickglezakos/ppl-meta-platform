-- Minimal MVR + face-session tables for Lima/Windows installer smoke tests.
-- Uses float8[] instead of pgvector when the vector extension is unavailable.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Optional: ignore failure if vector package is not installed.
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pgvector not available; using float8[] for embeddings';
END $$;

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

CREATE TABLE IF NOT EXISTS workflow_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(128) UNIQUE NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- mvr_people without requiring pgvector
CREATE TABLE IF NOT EXISTS mvr_people (
    mvr_people_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    face_embedding float8[] NOT NULL,
    featured_individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    age_min INTEGER,
    age_max INTEGER,
    gender_estimate VARCHAR(20),
    gender_confidence FLOAT,
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    is_orphaned BOOLEAN NOT NULL DEFAULT FALSE,
    orphaned_at TIMESTAMP,
    replaced_by_mvr_uuid UUID,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS individual_mvr_mapping (
    mapping_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    mvr_people_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    link_method VARCHAR(50) DEFAULT 'auto_create',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (individual_uuid)
);

CREATE INDEX IF NOT EXISTS idx_mvr_mapping_individual ON individual_mvr_mapping(individual_uuid);
CREATE INDEX IF NOT EXISTS idx_mvr_mapping_mvr ON individual_mvr_mapping(mvr_people_uuid);
CREATE INDEX IF NOT EXISTS idx_face_sessions_media ON face_detection_sessions(media_uuid);
