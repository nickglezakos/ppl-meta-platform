-- Align shared recording_sessions with ppl-meta-cameras ORM
-- (orchestrator created camera_device_id; cameras model expects camera_id + recording_quality).

BEGIN;

ALTER TABLE recording_sessions
  ADD COLUMN IF NOT EXISTS camera_id INTEGER;

ALTER TABLE recording_sessions
  ADD COLUMN IF NOT EXISTS recording_quality VARCHAR(20) DEFAULT 'high';

-- Backfill camera_id from cameras.device_id when possible
UPDATE recording_sessions rs
SET camera_id = c.id
FROM cameras c
WHERE rs.camera_id IS NULL
  AND rs.camera_device_id IS NOT NULL
  AND rs.camera_device_id = c.device_id;

CREATE INDEX IF NOT EXISTS ix_recording_sessions_camera_id
  ON recording_sessions(camera_id);

COMMIT;
