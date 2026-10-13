-- Migration 024: Renumber group memberships oldest-first
--
-- Migration 023 originally backfilled member_number with newest = 1 (to match
-- the old UI list order). Product rule is chronological: first join =
-- Group Member 01, later joins get higher numbers. New inserts already use
-- MAX+1; this migration reassigns existing rows once.
--
-- Reservations are cleared: they referred to the previous numbering scheme and
-- would collide after renumber. Same-MVR reclaim still works for deletes after
-- this point.
--
-- Two-phase update avoids unique (group_id, member_number) conflicts while
-- swapping ordinals in place.

DELETE FROM group_member_number_reservations;

-- Phase 1: park current numbers in a negative range (still unique per group).
UPDATE group_memberships
SET member_number = -member_number - 1000000
WHERE member_number > 0;

-- Phase 2: assign chronological ranks (oldest = 1).
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY group_id
            ORDER BY added_at ASC, individual_id ASC
        ) AS rn
    FROM group_memberships
)
UPDATE group_memberships gm
SET member_number = ranked.rn
FROM ranked
WHERE gm.id = ranked.id
  AND gm.member_number IS DISTINCT FROM ranked.rn;

DO $$
BEGIN
    RAISE NOTICE 'Migration 024: group member numbers renumbered oldest-first';
END $$;
