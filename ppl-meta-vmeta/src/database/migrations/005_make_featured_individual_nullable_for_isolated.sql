-- =================================================================
-- Make featured_individual_uuid Nullable for Isolated MVR People
-- PPL Meta Platform v2.19.43
-- File: 005_make_featured_individual_nullable_for_isolated.sql
-- Created: November 29, 2025
-- Purpose: Allow NULL featured_individual_uuid for isolated MVR people
-- =================================================================

-- Drop the NOT NULL constraint on featured_individual_uuid
-- Isolated MVR people (from single-media processing) don't have cross-video individuals
ALTER TABLE mvr_people
ALTER COLUMN featured_individual_uuid DROP NOT NULL;

-- Add a check constraint to ensure:
-- - Non-isolated MVR people MUST have a featured_individual_uuid
-- - Isolated MVR people can have NULL featured_individual_uuid
ALTER TABLE mvr_people
ADD CONSTRAINT mvr_people_featured_individual_check
CHECK (
    (is_isolated = FALSE AND featured_individual_uuid IS NOT NULL) OR
    (is_isolated = TRUE)
);

-- Add comment for documentation
COMMENT ON COLUMN mvr_people.featured_individual_uuid IS 
'UUID of the featured individual (required for non-isolated MVR, optional for isolated MVR)';

-- =================================================================
-- COMPLETION MESSAGE
-- =================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ featured_individual_uuid Constraints Updated!';
    RAISE NOTICE '📊 Changes:';
    RAISE NOTICE '   - Removed NOT NULL constraint from featured_individual_uuid';
    RAISE NOTICE '   - Added check constraint for isolated MVR people';
    RAISE NOTICE '   - Isolated MVR can have NULL featured_individual_uuid';
    RAISE NOTICE '   - Non-isolated MVR must have featured_individual_uuid';
    RAISE NOTICE '📅 Created: November 29, 2025';
    RAISE NOTICE '🎯 Ready for single-media MVR creation';
END $$;
