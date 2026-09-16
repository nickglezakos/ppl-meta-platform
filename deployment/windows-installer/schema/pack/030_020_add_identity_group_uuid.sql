-- Migration 020: Add identity_group_uuid for cross-source identity linking
--
-- Part of the two-tier merge system:
--   Tier 1: Source-separated hard merge (orphan losers within each source)
--   Tier 2: Cross-source soft link (assign shared identity_group_uuid)
--
-- MVR people representing the same real person across recording and instant
-- detection pipelines share the same identity_group_uuid without orphaning either.
-- This allows accurate counting in all analytics filter modes.

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS identity_group_uuid UUID DEFAULT NULL;

-- Index for efficient GROUP BY / COUNT(DISTINCT) in analytics queries
CREATE INDEX IF NOT EXISTS idx_mvr_people_identity_group
    ON mvr_people (identity_group_uuid)
    WHERE identity_group_uuid IS NOT NULL;
