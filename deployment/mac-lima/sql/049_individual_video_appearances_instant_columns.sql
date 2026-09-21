-- Instant detection appearances: columns required by VMeta persist-batch.
-- Lab symptom: persist-batch 500 with
--   UndefinedColumnError: column "quality_score" of relation "individual_video_appearances" does not exist

ALTER TABLE individual_video_appearances
    ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION;

ALTER TABLE individual_video_appearances
    ADD COLUMN IF NOT EXISTS processing_method TEXT;

ALTER TABLE individual_video_appearances
    ADD COLUMN IF NOT EXISTS source_session_uuid UUID;

ALTER TABLE individual_video_appearances
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW();

COMMENT ON COLUMN individual_video_appearances.quality_score IS
    'Appearance quality used by instant-detection persist-batch';
COMMENT ON COLUMN individual_video_appearances.processing_method IS
    'How this appearance was produced (e.g. instant_detection)';
COMMENT ON COLUMN individual_video_appearances.source_session_uuid IS
    'Tracking session that created this appearance for instant detection';
