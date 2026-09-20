-- Ensure individuals.created_by_session exists when the table was created by
-- ORM/runtime without the column from 001_cross_video_tracking_schema.
-- Missing column makes vmeta POST /instant-detection/persist-batch abort the
-- transaction (InFailedSQLTransactionError) so mobile/RTSP instant detection
-- never shows results even though start/submit succeed.

ALTER TABLE individuals
  ADD COLUMN IF NOT EXISTS created_by_session UUID REFERENCES tracking_sessions(session_uuid);

CREATE INDEX IF NOT EXISTS idx_individuals_created_by_session
  ON individuals(created_by_session);

COMMENT ON COLUMN individuals.created_by_session IS
  'Tracking session that created this individual (required by instant-detection persist)';
