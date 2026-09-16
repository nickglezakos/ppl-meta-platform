-- Link face detections to sessions + complete individuals columns for instant detection.
-- Required for recording face pipeline / Enhanced Logic V2 / MVR people persistence.

ALTER TABLE face_detections
ADD COLUMN IF NOT EXISTS session_uuid TEXT;

CREATE INDEX IF NOT EXISTS idx_face_detections_session_uuid
ON face_detections (session_uuid);

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS total_appearances INTEGER DEFAULT 0;

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS first_seen TIMESTAMP;

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP;

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS person_objects JSONB DEFAULT '[]'::jsonb;

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS gender_estimate VARCHAR(20);

ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS age_estimate INTEGER;

CREATE TABLE IF NOT EXISTS session_individuals (
    session_uuid UUID NOT NULL REFERENCES tracking_sessions(session_uuid) ON DELETE CASCADE,
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    processing_type VARCHAR(20) NOT NULL DEFAULT 'new',
    confidence_contribution FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (session_uuid, individual_uuid)
);

CREATE INDEX IF NOT EXISTS idx_session_individuals_session
ON session_individuals(session_uuid);

CREATE INDEX IF NOT EXISTS idx_session_individuals_individual
ON session_individuals(individual_uuid);
