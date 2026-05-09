-- ============================================================================
-- Migration: People Counters Invalidation Link Table
-- ============================================================================
-- Description: Link table mapping each persisted MVR search session to the
--              mvr_people identities that participated in its merge result.
--              Enables fast invalidation of any tagged batch session whose
--              underlying mvr_people row was later mutated by a hierarchical
--              merge or unmerge.
-- Created: 2026-05-09
-- See: docs/proposals/people-counters.md §5.7
-- ============================================================================

CREATE TABLE IF NOT EXISTS mvr_search_session_people (
    search_session_uuid UUID NOT NULL
        REFERENCES mvr_search_sessions(search_session_uuid) ON DELETE CASCADE,
    mvr_people_uuid UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (search_session_uuid, mvr_people_uuid)
);

CREATE INDEX IF NOT EXISTS idx_mvr_search_session_people_mvr_people_uuid
ON mvr_search_session_people(mvr_people_uuid);

CREATE INDEX IF NOT EXISTS idx_mvr_search_session_people_session
ON mvr_search_session_people(search_session_uuid);

COMMENT ON TABLE mvr_search_session_people IS
    'Maps persisted MVR search sessions to the mvr_people identities present in their result; used to invalidate tagged people-counters batches when underlying identities are merged/unmerged.';
COMMENT ON COLUMN mvr_search_session_people.mvr_people_uuid IS
    'A canonical mvr_people identity that appeared in the search session result_payload';
