-- Per-camera Instant Detection normalisation settings
ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS normalise_enabled BOOLEAN DEFAULT TRUE;

ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS normalise_span_seconds INTEGER DEFAULT 300;

ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS normalise_merge_threshold DOUBLE PRECISION DEFAULT 0.70;

COMMENT ON COLUMN cameras.normalise_enabled IS
  'When true, enqueue cross-flush Instant Detection normalisation after Y-flush / catch-up';
COMMENT ON COLUMN cameras.normalise_span_seconds IS
  'Fixed calendar span length in seconds for Instant Detection normalisation buckets (default 300)';
COMMENT ON COLUMN cameras.normalise_merge_threshold IS
  'Similarity threshold for hierarchical merge across flush logs within a normalisation span';
