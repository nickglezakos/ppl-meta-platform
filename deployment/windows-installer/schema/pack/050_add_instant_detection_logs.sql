-- Instant Detection Automation flush logs (separate from action / trigger_execution logs)
CREATE TABLE IF NOT EXISTS instant_detection_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    camera_device_id VARCHAR(255) NOT NULL,
    session_uuid UUID,
    flush_started_at TIMESTAMPTZ NOT NULL,
    flush_ended_at TIMESTAMPTZ NOT NULL,
    cycle_count INTEGER NOT NULL DEFAULT 0,
    frames_per_cycle INTEGER NOT NULL DEFAULT 3,
    merge_threshold DOUBLE PRECISION,
    people_count INTEGER NOT NULL DEFAULT 0,
    payload_json JSONB NOT NULL,
    log_type VARCHAR(64) NOT NULL DEFAULT 'instant_detection'
);

CREATE INDEX IF NOT EXISTS idx_instant_detection_logs_camera
    ON instant_detection_logs (camera_device_id);
CREATE INDEX IF NOT EXISTS idx_instant_detection_logs_session
    ON instant_detection_logs (session_uuid);
CREATE INDEX IF NOT EXISTS idx_instant_detection_logs_flush_started
    ON instant_detection_logs (flush_started_at DESC);
CREATE INDEX IF NOT EXISTS idx_instant_detection_logs_log_type
    ON instant_detection_logs (log_type);

COMMENT ON TABLE instant_detection_logs IS
  'Flushed Instant Detection windows (Y-cycle re-group + hierarchical merge). Analytics SoT.';
