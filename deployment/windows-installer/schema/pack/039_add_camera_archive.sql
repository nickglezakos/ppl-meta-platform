-- Migration: Add archived column to cameras table
-- Date: 2026-01-28
-- Description: Add archived column to allow hiding cameras from default camera list without deleting them

-- Add archived column with default value false
ALTER TABLE cameras 
  ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

-- Create index on archived column for efficient filtering
CREATE INDEX IF NOT EXISTS idx_cameras_archived ON cameras(archived);

-- Ensure all existing cameras are not archived by default
UPDATE cameras
SET archived = FALSE
WHERE archived IS NULL;

