-- =================================================================
-- Single-Media MVR Processing Schema Addition
-- PPL Meta Platform v2.19.43
-- File: 004_single_media_mvr_columns.sql
-- Created: November 29, 2025
-- Purpose: Add columns to support independent media processing
-- =================================================================

-- Add columns to mvr_people table for single-media processing

ALTER TABLE mvr_people
ADD COLUMN IF NOT EXISTS is_isolated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS source_media_uuid UUID;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_mvr_people_isolated ON mvr_people(is_isolated);
CREATE INDEX IF NOT EXISTS idx_mvr_people_source_media ON mvr_people(source_media_uuid);

-- Add composite index for filtering isolated MVR by source
CREATE INDEX IF NOT EXISTS idx_mvr_people_isolated_source 
ON mvr_people(is_isolated, source_media_uuid) 
WHERE is_isolated = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN mvr_people.is_isolated IS 'Whether this MVR person is isolated (no cross-media merging)';
COMMENT ON COLUMN mvr_people.source_media_uuid IS 'UUID of the single media this MVR was created from';

-- =================================================================
-- COMPLETION MESSAGE
-- =================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Single-Media MVR Processing Schema Added Successfully!';
    RAISE NOTICE '📊 Changes:';
    RAISE NOTICE '   - Added is_isolated column to mvr_people';
    RAISE NOTICE '   - Added source_media_uuid column to mvr_people';
    RAISE NOTICE '   - Created performance indexes';
    RAISE NOTICE '📅 Created: November 29, 2025';
    RAISE NOTICE '🎯 Ready for single-media MVR endpoint';
END $$;
