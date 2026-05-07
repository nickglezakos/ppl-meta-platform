-- ============================================================================
-- Migration: Persistent MVR Search Sessions
-- ============================================================================
-- Description: Store merge-enabled MVR search sessions and their reusable
--              result snapshots without persisting search-owned hierarchy.
-- Created: 2026-05-07
-- ============================================================================

CREATE TABLE IF NOT EXISTS mvr_search_sessions (
    search_session_uuid UUID PRIMARY KEY,
    search_mode VARCHAR(50) NOT NULL,
    same_input_key TEXT NOT NULL,
    requested_start_date TIMESTAMP NULL,
    requested_end_date TIMESTAMP NULL,
    search_time_span_seconds DOUBLE PRECISION NULL,
    total_individuals INTEGER NOT NULL DEFAULT 0,
    total_appearances INTEGER NOT NULL DEFAULT 0,
    unique_videos INTEGER NOT NULL DEFAULT 0,
    average_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    average_quality DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    first_appearance TIMESTAMP NULL,
    last_appearance TIMESTAMP NULL,
    total_men INTEGER NOT NULL DEFAULT 0,
    total_women INTEGER NOT NULL DEFAULT 0,
    total_unknown INTEGER NOT NULL DEFAULT 0,
    average_age DOUBLE PRECISION NULL,
    result_payload JSONB NOT NULL,
    summary_payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mvr_search_sessions_same_input_key
ON mvr_search_sessions(same_input_key);

CREATE INDEX IF NOT EXISTS idx_mvr_search_sessions_created_at
ON mvr_search_sessions(created_at DESC);

CREATE TABLE IF NOT EXISTS mvr_search_session_cameras (
    search_session_uuid UUID NOT NULL REFERENCES mvr_search_sessions(search_session_uuid) ON DELETE CASCADE,
    camera_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (search_session_uuid, camera_id)
);

CREATE INDEX IF NOT EXISTS idx_mvr_search_session_cameras_camera_id
ON mvr_search_session_cameras(camera_id);

CREATE TABLE IF NOT EXISTS mvr_search_session_videos (
    search_session_uuid UUID NOT NULL REFERENCES mvr_search_sessions(search_session_uuid) ON DELETE CASCADE,
    video_uuid UUID NOT NULL,
    camera_id TEXT NULL,
    media_timestamp TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (search_session_uuid, video_uuid)
);

CREATE INDEX IF NOT EXISTS idx_mvr_search_session_videos_video_uuid
ON mvr_search_session_videos(video_uuid);

CREATE INDEX IF NOT EXISTS idx_mvr_search_session_videos_camera_id
ON mvr_search_session_videos(camera_id)
WHERE camera_id IS NOT NULL;

COMMENT ON TABLE mvr_search_sessions IS 'Persistent merge-enabled MVR search sessions keyed by canonical camera and video identity';
COMMENT ON COLUMN mvr_search_sessions.same_input_key IS 'Hash of canonicalized camera IDs and video UUIDs used to detect reusable search sessions';
COMMENT ON COLUMN mvr_search_sessions.result_payload IS 'Full reusable search result payload returned by merge-enabled MVR search';
COMMENT ON COLUMN mvr_search_sessions.summary_payload IS 'Stored summary metrics and search input snapshot for the search session';
