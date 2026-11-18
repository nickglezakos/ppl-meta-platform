-- Migration 006: Add video_uuids column for optimization
-- This allows tracking sessions to use explicit video UUIDs instead of time-based queries
-- Created: November 19, 2025

ALTER TABLE tracking_sessions 
ADD COLUMN IF NOT EXISTS video_uuids JSONB;

-- Add index for faster queries on explicit video_uuids
CREATE INDEX IF NOT EXISTS idx_tracking_sessions_video_uuids 
ON tracking_sessions USING GIN (video_uuids);

-- Add comment
COMMENT ON COLUMN tracking_sessions.video_uuids IS 
'Optional array of explicit video UUIDs to process. When provided, skips time-based video discovery for better performance.';
