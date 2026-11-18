-- Soft-archive columns for mvr_people (irreversible user-facing archive; row retained).
-- Stage 3: apply via schema/apply.sh; verify gates in schema/verify.sh.

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL;

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS archived_by TEXT NULL;

COMMENT ON COLUMN mvr_people.is_archived IS
    'Soft-archive flag; archived MVRs are delinked from groups/PPP and excluded from default search';
COMMENT ON COLUMN mvr_people.archived_at IS
    'When the MVR was archived (UTC)';
COMMENT ON COLUMN mvr_people.archived_by IS
    'User id/email that archived the MVR';

CREATE INDEX IF NOT EXISTS idx_mvr_people_not_archived
    ON mvr_people (mvr_people_uuid)
    WHERE is_archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_is_archived
    ON mvr_people (is_archived)
    WHERE is_archived = TRUE;

-- Allow archive promotions to be recorded in the merge audit log.
ALTER TABLE mvr_merge_audit_log
    DROP CONSTRAINT IF EXISTS mvr_merge_audit_log_merge_action_check;

ALTER TABLE mvr_merge_audit_log
    ADD CONSTRAINT mvr_merge_audit_log_merge_action_check
        CHECK (merge_action IN (
            'merged', 'rejected', 'manual_review', 'unmerged', 'archived'
        ));
