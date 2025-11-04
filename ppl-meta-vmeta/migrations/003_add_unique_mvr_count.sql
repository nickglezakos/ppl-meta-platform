-- Migration: Add unique_mvr_people_count to tracking_sessions
-- Purpose: Track unique individuals after MVR auto-matching and merging
-- Date: November 1, 2025
-- Version: 1.0.0

-- Add column to store the count of unique MVR-People after auto-matching
ALTER TABLE tracking_sessions 
ADD COLUMN IF NOT EXISTS unique_mvr_people_count INTEGER DEFAULT 0;

-- Add comment to document the column's purpose
COMMENT ON COLUMN tracking_sessions.unique_mvr_people_count IS 
'Count of unique individuals after MVR auto-matching and merging. This represents the deduplicated count after cross-video face matching.';

-- Add index for queries that filter by unique count
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_unique_mvr_count 
ON tracking_sessions(unique_mvr_people_count) 
WHERE unique_mvr_people_count > 0;

-- Add index for queries comparing individuals_found vs unique count
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_merge_stats 
ON tracking_sessions(individuals_found, unique_mvr_people_count) 
WHERE status = 'completed';

-- Update existing completed sessions to set unique count = individuals count as baseline
-- (They haven't run the new auto-matching yet)
UPDATE tracking_sessions
SET unique_mvr_people_count = individuals_found
WHERE status = 'completed' 
  AND unique_mvr_people_count = 0 
  AND individuals_found > 0;

-- Verification query
DO $$
DECLARE
    sessions_updated INTEGER;
    sessions_with_count INTEGER;
BEGIN
    -- Check how many sessions were updated
    SELECT COUNT(*) INTO sessions_updated
    FROM tracking_sessions
    WHERE unique_mvr_people_count > 0;
    
    -- Check total sessions
    SELECT COUNT(*) INTO sessions_with_count
    FROM tracking_sessions
    WHERE status = 'completed';
    
    RAISE NOTICE 'Migration completed:';
    RAISE NOTICE '  - Sessions with unique count: %', sessions_updated;
    RAISE NOTICE '  - Total completed sessions: %', sessions_with_count;
    RAISE NOTICE '  - Column added: unique_mvr_people_count';
    RAISE NOTICE '  - Indexes created: 2';
END $$;
