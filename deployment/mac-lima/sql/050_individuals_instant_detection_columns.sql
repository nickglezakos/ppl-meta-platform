-- Instant-detection persist updates existing individuals in place.
-- Lab symptom: persist-batch 500 with
--   UndefinedColumnError: column "total_appearances" of relation "individuals" does not exist
-- The INSERT path falls back when these columns are missing; the UPDATE path does not,
-- so a later sighting of a known person rolls back the whole batch.

ALTER TABLE individuals
  ADD COLUMN IF NOT EXISTS total_appearances INTEGER DEFAULT 0;

ALTER TABLE individuals
  ADD COLUMN IF NOT EXISTS first_seen TIMESTAMP;

ALTER TABLE individuals
  ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP;

ALTER TABLE individuals
  ADD COLUMN IF NOT EXISTS person_objects JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN individuals.total_appearances IS
  'Appearance count updated by instant-detection persist-batch';
COMMENT ON COLUMN individuals.first_seen IS
  'First time this individual was persisted';
COMMENT ON COLUMN individuals.last_seen IS
  'Last time instant-detection persist updated this individual';
COMMENT ON COLUMN individuals.person_objects IS
  'Person-object ids recorded when the individual was created';
