-- Add individuals.created_by_session used by instant-detection persist-batch.
ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS created_by_session UUID;

CREATE INDEX IF NOT EXISTS idx_individuals_created_by_session
ON individuals (created_by_session);
