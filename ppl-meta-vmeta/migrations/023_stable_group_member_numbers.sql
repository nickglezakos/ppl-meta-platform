-- Migration 023: Stable group membership numbers
--
-- Membership display numbers ("Group Member 01", "Group Member 02", ...) must
-- stay fixed for a given (group_id, individual_id) across add/remove/reorder.
-- Previously numbers were recomputed from list position (newest-first), so a
-- newly added member always became Member 01.
--
-- Strategy:
--   1. Persist member_number on group_memberships
--   2. On delete, reserve that number for the same MVR uuid so only that
--      individual can reclaim it if re-added
--   3. New members get MAX(active + reserved) + 1 (gaps are never filled)

-- ================================================================
-- Column: group_memberships.member_number
-- ================================================================

ALTER TABLE group_memberships
    ADD COLUMN IF NOT EXISTS member_number INTEGER;

-- Backfill existing rows to match the previous UI ordering (newest-first),
-- so currently displayed labels do not shuffle on upgrade. Only rows still
-- NULL are updated so re-running the migration is safe. After this, numbers
-- are stable and new members always get max+1.
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY group_id
            ORDER BY added_at DESC, individual_id DESC
        ) AS rn
    FROM group_memberships
    WHERE member_number IS NULL
)
UPDATE group_memberships gm
SET member_number = ranked.rn
FROM ranked
WHERE gm.id = ranked.id;

-- Any remaining NULLs (empty table edge cases) get a safe default before NOT NULL.
UPDATE group_memberships
SET member_number = 1
WHERE member_number IS NULL;

ALTER TABLE group_memberships
    ALTER COLUMN member_number SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_group_memberships_group_member_number
    ON group_memberships (group_id, member_number);

-- ================================================================
-- Table: group_member_number_reservations
-- Purpose: Hold freed membership numbers so they are only reclaimable by
--          the same (group_id, individual_id) pair.
-- ================================================================

CREATE TABLE IF NOT EXISTS group_member_number_reservations (
    group_id TEXT NOT NULL,
    individual_id TEXT NOT NULL,
    member_number INTEGER NOT NULL,
    reserved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (group_id, individual_id),

    CONSTRAINT fk_member_number_reservation_group
        FOREIGN KEY (group_id)
        REFERENCES individual_groups(id)
        ON DELETE CASCADE,

    CONSTRAINT unique_reserved_group_member_number
        UNIQUE (group_id, member_number)
);

CREATE INDEX IF NOT EXISTS idx_group_member_number_reservations_group_id
    ON group_member_number_reservations (group_id);

DO $$
BEGIN
    RAISE NOTICE 'Migration 023: stable group member numbers applied';
END $$;
