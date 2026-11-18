-- Soft-archive columns for mvr_people (kept in sync with installer pack).
-- See deployment/windows-installer/schema/pack/055_add_mvr_people_archive.sql

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL;

ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS archived_by TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_mvr_people_not_archived
    ON mvr_people (mvr_people_uuid)
    WHERE is_archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_mvr_people_is_archived
    ON mvr_people (is_archived)
    WHERE is_archived = TRUE;

ALTER TABLE mvr_merge_audit_log
    DROP CONSTRAINT IF EXISTS mvr_merge_audit_log_merge_action_check;

ALTER TABLE mvr_merge_audit_log
    ADD CONSTRAINT mvr_merge_audit_log_merge_action_check
        CHECK (merge_action IN (
            'merged', 'rejected', 'manual_review', 'unmerged', 'archived'
        ));
