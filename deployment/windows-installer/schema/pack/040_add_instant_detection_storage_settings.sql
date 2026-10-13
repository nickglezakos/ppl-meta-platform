-- Migration: Add instant detection storage settings to cameras table
-- Date: 2026-03-19
-- Description: Add storage_multiple and tracking_session_duration_minutes columns
--              for MVR People Persistent Storage feature

ALTER TABLE cameras
  ADD COLUMN IF NOT EXISTS storage_multiple INTEGER DEFAULT 1,
  ADD COLUMN IF NOT EXISTS tracking_session_duration_minutes INTEGER DEFAULT 0;

-- Set defaults for any existing cameras
UPDATE cameras
SET storage_multiple = 1
WHERE storage_multiple IS NULL;

UPDATE cameras
SET tracking_session_duration_minutes = 0
WHERE tracking_session_duration_minutes IS NULL;

COMMENT ON COLUMN cameras.storage_multiple IS 'Persist every Nth detection cycle to MVR storage (1 = every cycle, higher = less frequent)';
COMMENT ON COLUMN cameras.tracking_session_duration_minutes IS 'Auto-rotate tracking session after N minutes (0 = no rotation)';
