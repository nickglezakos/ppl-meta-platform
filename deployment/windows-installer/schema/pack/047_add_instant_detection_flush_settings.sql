-- Instant Detection Redis-first flush settings (frames per cycle + Y flush interval)
ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS frames_per_cycle INTEGER DEFAULT 3;

ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS flush_interval_cycles INTEGER DEFAULT 12;

ALTER TABLE cameras
    ADD COLUMN IF NOT EXISTS flush_merge_similarity_threshold DOUBLE PRECISION DEFAULT 0.60;

COMMENT ON COLUMN cameras.frames_per_cycle IS
  'Instant detection frames sampled and grouped per cycle (default 3)';
COMMENT ON COLUMN cameras.flush_interval_cycles IS
  'Y: cycles between in-memory re-group+contamination+hierarchical merge and flush to instant_detection_logs';
COMMENT ON COLUMN cameras.flush_merge_similarity_threshold IS
  'Similarity threshold for hierarchical MVR merge at Instant Detection flush';
