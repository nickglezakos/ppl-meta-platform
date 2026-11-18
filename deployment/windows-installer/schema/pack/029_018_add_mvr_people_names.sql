-- Migration: Add name fields to mvr_people table
-- Date: 2025-12-19
-- Description: Adds user-assignable names to MVR people for Individual Groups feature
-- Related: docs/proposals/individual-naming-system.md

-- Add name columns to mvr_people table
ALTER TABLE mvr_people 
ADD COLUMN IF NOT EXISTS name VARCHAR(255) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS name_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
ADD COLUMN IF NOT EXISTS name_updated_by VARCHAR(255) DEFAULT NULL;

-- Add constraints (drop first if they exist to avoid errors)
DO $$ 
BEGIN
    ALTER TABLE mvr_people 
    ADD CONSTRAINT mvr_name_not_whitespace 
        CHECK (name IS NULL OR LENGTH(TRIM(name)) > 0);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ 
BEGIN
    ALTER TABLE mvr_people 
    ADD CONSTRAINT mvr_name_length 
        CHECK (name IS NULL OR LENGTH(name) <= 255);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create index for name lookups
CREATE INDEX IF NOT EXISTS idx_mvr_people_name 
ON mvr_people(name) WHERE name IS NOT NULL;

-- Create index for name search (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_mvr_people_name_search 
ON mvr_people(name text_pattern_ops) WHERE name IS NOT NULL;

-- Add column comments
COMMENT ON COLUMN mvr_people.name IS 'User-assigned human-readable name for this MVR person';
COMMENT ON COLUMN mvr_people.name_updated_at IS 'Timestamp when name was last updated';
COMMENT ON COLUMN mvr_people.name_updated_by IS 'User email who last updated the name';

-- Create name history table for audit trail
CREATE TABLE IF NOT EXISTS mvr_people_name_history (
    id SERIAL PRIMARY KEY,
    mvr_people_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    old_name VARCHAR(255),
    new_name VARCHAR(255),
    changed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255),
    reason VARCHAR(50) CHECK (reason IN ('user_edit', 'merge_inherit', 'merge_consolidate')),
    CONSTRAINT name_history_reason_check CHECK (reason IN ('user_edit', 'merge_inherit', 'merge_consolidate'))
);

-- Create indexes for name history
CREATE INDEX IF NOT EXISTS idx_name_history_mvr 
ON mvr_people_name_history(mvr_people_uuid);

CREATE INDEX IF NOT EXISTS idx_name_history_timestamp 
ON mvr_people_name_history(changed_at DESC);

-- Add comment to history table
COMMENT ON TABLE mvr_people_name_history IS 'Audit trail for MVR people name changes';
COMMENT ON COLUMN mvr_people_name_history.reason IS 'Reason for name change: user_edit (manual), merge_inherit (inherited from merge), merge_consolidate (multiple names merged)';

-- Grant permissions on history table to all potential users
GRANT ALL ON TABLE mvr_people_name_history TO postgres;
GRANT ALL ON TABLE mvr_people_name_history TO nickgklezakos;
GRANT ALL ON TABLE mvr_people_name_history TO ppl_user;
GRANT ALL ON SEQUENCE mvr_people_name_history_id_seq TO postgres;
GRANT ALL ON SEQUENCE mvr_people_name_history_id_seq TO nickgklezakos;
GRANT ALL ON SEQUENCE mvr_people_name_history_id_seq TO ppl_user;
