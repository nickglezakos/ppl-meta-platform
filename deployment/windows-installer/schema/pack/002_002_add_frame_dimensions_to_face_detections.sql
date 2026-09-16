-- Migration 002: Add frame_width and frame_height columns to face_detections
-- These columns record the exact pixel dimensions of the video frame at the time
-- the bbox was detected, enabling accurate bbox alignment when crops are later
-- extracted from frames that may differ in resolution.

ALTER TABLE face_detections
    ADD COLUMN IF NOT EXISTS frame_width INTEGER,
    ADD COLUMN IF NOT EXISTS frame_height INTEGER;

-- Index for future queries filtering by resolution
CREATE INDEX IF NOT EXISTS idx_face_detections_frame_dims
    ON face_detections (frame_width, frame_height)
    WHERE frame_width IS NOT NULL AND frame_height IS NOT NULL;
