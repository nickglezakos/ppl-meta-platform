-- ============================================================================
-- Migration: People Counters — batch tagging on mvr_search_sessions
-- ============================================================================
-- Description: Adds optional columns that mark a row in `mvr_search_sessions`
--              as a *people-counters batch* — a deterministic, hour-aligned
--              per-camera merge result that can be reused by sub-period
--              queries without recomputation.
--
--              See: docs/proposals/people-counters.md §5.2
--
-- Strategy: All additions are nullable / default-FALSE so existing ad-hoc
--           sessions continue to work unchanged. A row is a "batch" iff
--           batch_key IS NOT NULL.
--
-- Created: 2026-05-09
-- ============================================================================

ALTER TABLE mvr_search_sessions
    ADD COLUMN IF NOT EXISTS batch_key       TEXT,
    ADD COLUMN IF NOT EXISTS batch_camera_id TEXT,
    ADD COLUMN IF NOT EXISTS batch_start_utc TIMESTAMP,
    ADD COLUMN IF NOT EXISTS batch_end_utc   TIMESTAMP,
    ADD COLUMN IF NOT EXISTS is_stale        BOOLEAN NOT NULL DEFAULT FALSE;

-- Idempotency for the daily batch job: re-running on the same
-- (camera, hour) MUST NOT produce duplicate batch rows.
CREATE UNIQUE INDEX IF NOT EXISTS idx_mvr_search_sessions_batch_key
    ON mvr_search_sessions(batch_key)
    WHERE batch_key IS NOT NULL;

-- Sub-period query: find every batch fully inside [user_start, user_end]
-- for a camera. Partial index keeps it small and excludes stale rows so
-- the planner gets only reusable batches.
CREATE INDEX IF NOT EXISTS idx_mvr_search_sessions_batch_lookup
    ON mvr_search_sessions(batch_camera_id, batch_start_utc, batch_end_utc)
    WHERE batch_key IS NOT NULL AND is_stale = FALSE;

-- Diagnostic: scan stale batches awaiting refresh.
CREATE INDEX IF NOT EXISTS idx_mvr_search_sessions_stale
    ON mvr_search_sessions(batch_camera_id, batch_start_utc)
    WHERE batch_key IS NOT NULL AND is_stale = TRUE;

COMMENT ON COLUMN mvr_search_sessions.batch_key IS
    'People-counters batch identifier: "{camera_id}|{batch_start_utc}|{batch_end_utc}". '
    'NULL for ad-hoc (non-batch) sessions.';
COMMENT ON COLUMN mvr_search_sessions.is_stale IS
    'TRUE when the underlying mvr_people referenced by this batch have changed '
    '(new materialization, hierarchical merge, video deletion). The people-counters '
    'worker re-runs stale batches as a self-healing pass.';
