-- Minimal tracking_sessions (+ related columns) for instant detection persistence.
-- Based on ppl-meta-vmeta migrations 002 + 019, without heavy constraints.

BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS tracking_sessions (
    session_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    collections TEXT[] NOT NULL DEFAULT '{}',
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP NOT NULL DEFAULT (NOW() + INTERVAL '1 second'),
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    config_hash VARCHAR(32) NOT NULL DEFAULT 'instant_detection',
    algorithm_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_videos INTEGER NOT NULL DEFAULT 0,
    processed_videos INTEGER NOT NULL DEFAULT 0,
    failed_videos TEXT[] DEFAULT '{}',
    individuals_found INTEGER NOT NULL DEFAULT 0,
    person_objects_processed INTEGER NOT NULL DEFAULT 0,
    cache_hits INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_seconds FLOAT,
    source_type VARCHAR(30) NOT NULL DEFAULT 'recording_pipeline',
    camera_device_id VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_tracking_sessions_source_type
  ON tracking_sessions(source_type);
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_camera_device_id
  ON tracking_sessions(camera_device_id);

CREATE TABLE IF NOT EXISTS individuals (
    individual_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_id VARCHAR(50) UNIQUE NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.5,
    spatial_signature JSONB,
    temporal_signature JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    source_type VARCHAR(30) NOT NULL DEFAULT 'recording_pipeline'
);

COMMIT;
