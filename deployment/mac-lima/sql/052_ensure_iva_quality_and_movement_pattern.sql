-- Ensure IVA columns used by route expand + analytics quality fallback exist.
-- quality_score also packed in 049; movement_pattern comes from cross-video schema.
-- This file is a hard Stage 3 gate companion for 2.25.107 (idempotent).

ALTER TABLE individual_video_appearances
    ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION;

ALTER TABLE individual_video_appearances
    ADD COLUMN IF NOT EXISTS movement_pattern JSONB;

COMMENT ON COLUMN individual_video_appearances.quality_score IS
    'Appearance / face quality (0-1); used by analytics Image Quality fallback';
COMMENT ON COLUMN individual_video_appearances.movement_pattern IS
    'Route points + movement/velocity statistics JSON for Routes/Motion analytics';
