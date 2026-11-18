-- Migration 021: Add 'unmerged' to mvr_merge_audit_log merge_action check constraint
-- Required to support the unmerge (undo manual merge) operation.

ALTER TABLE mvr_merge_audit_log
    DROP CONSTRAINT IF EXISTS mvr_merge_audit_log_merge_action_check;

ALTER TABLE mvr_merge_audit_log
    ADD CONSTRAINT mvr_merge_audit_log_merge_action_check
        CHECK (merge_action IN ('merged', 'rejected', 'manual_review', 'unmerged'));
