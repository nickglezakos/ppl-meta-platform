-- Migration: Add support for video-level individual caching
-- Created: November 5, 2025
-- Purpose: Support MVR-aware caching with merge tracking

-- Add merge tracking column to individuals table
ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS merged_into_uuid UUID REFERENCES individuals(individual_uuid);

-- Add algorithm versioning for cache invalidation
ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS algorithm_version TEXT DEFAULT '1.0',
ADD COLUMN IF NOT EXISTS last_appearance_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS cache_invalidated_at TIMESTAMP;

-- Index for efficient merge lookups
CREATE INDEX IF NOT EXISTS idx_individuals_merged_into 
ON individuals(merged_into_uuid)
WHERE merged_into_uuid IS NOT NULL;

-- Index for cache validation queries
CREATE INDEX IF NOT EXISTS idx_individuals_algorithm_version 
ON individuals(algorithm_version);

CREATE INDEX IF NOT EXISTS idx_individuals_last_appearance 
ON individuals(last_appearance_at DESC);

-- Add check constraint: individual cannot be merged into itself
DO $$
BEGIN
    ALTER TABLE individuals
    ADD CONSTRAINT chk_no_self_merge 
    CHECK (merged_into_uuid IS NULL OR merged_into_uuid != individual_uuid);
EXCEPTION
    WHEN duplicate_object THEN
        -- Constraint already exists, ignore
        NULL;
END $$;

-- Create table to track cache statistics
CREATE TABLE IF NOT EXISTS individual_cache_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID NOT NULL,
    video_uuid UUID NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    individuals_reused INTEGER DEFAULT 0,
    individuals_created INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cache_stats_session 
ON individual_cache_stats(session_uuid);

CREATE INDEX IF NOT EXISTS idx_cache_stats_video 
ON individual_cache_stats(video_uuid);

-- Add comment to explain merged_into_uuid
COMMENT ON COLUMN individuals.merged_into_uuid IS 
'UUID of the individual this one was merged into. NULL if not merged.';

COMMENT ON COLUMN individuals.algorithm_version IS 
'Version of the tracking algorithm used to create this individual. Used for cache invalidation.';

COMMENT ON COLUMN individuals.last_appearance_at IS 
'Timestamp of the most recent appearance of this individual. Used for staleness detection.';

COMMENT ON TABLE individual_cache_stats IS 
'Tracks cache hit/miss statistics for video-level individual caching.';
