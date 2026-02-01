-- Rollback: Remove archived column from cameras table
-- Date: 2026-01-28
-- Description: Rollback migration to remove archived column if needed

-- Drop the index first
DROP INDEX IF EXISTS idx_cameras_archived;

-- Remove the archived column
ALTER TABLE cameras 
  DROP COLUMN IF EXISTS archived;
