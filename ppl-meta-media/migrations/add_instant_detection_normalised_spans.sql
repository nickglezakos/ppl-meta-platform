-- Derived Instant Detection normalisation spans (immutable raw logs untouched)
CREATE TABLE IF NOT EXISTS instant_detection_normalised_spans (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    camera_device_id VARCHAR(255) NOT NULL,
    span_start TIMESTAMPTZ NOT NULL,
    span_end TIMESTAMPTZ NOT NULL,
    span_seconds INTEGER NOT NULL DEFAULT 300,
    merge_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.70,
    people_count INTEGER NOT NULL DEFAULT 0,
    source_log_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_instant_norm_span_camera_start_threshold
    ON instant_detection_normalised_spans (camera_device_id, span_start, merge_threshold);

CREATE INDEX IF NOT EXISTS idx_instant_norm_spans_camera
    ON instant_detection_normalised_spans (camera_device_id);

CREATE INDEX IF NOT EXISTS idx_instant_norm_spans_span_start
    ON instant_detection_normalised_spans (span_start DESC);

COMMENT ON TABLE instant_detection_normalised_spans IS
  'Derived cross-flush Instant Detection people merges per fixed calendar span. Raw instant_detection_logs stay immutable.';
