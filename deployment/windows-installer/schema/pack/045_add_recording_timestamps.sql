-- Migration: Add recording timestamps to media table
-- Date: 2025-11-02
-- Purpose: Store video recording start/end times for cross-video tracking

-- Add start_timestamp and end_timestamp columns
ALTER TABLE media 
ADD COLUMN IF NOT EXISTS start_timestamp TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS end_timestamp TIMESTAMP WITH TIME ZONE;

-- Create indexes for timestamp-based queries
CREATE INDEX IF NOT EXISTS idx_media_start_timestamp ON media(start_timestamp);
CREATE INDEX IF NOT EXISTS idx_media_end_timestamp ON media(end_timestamp);

-- Update existing camera recordings to populate timestamps from filename
-- Format: camera_usb_camera_0_segment_001_20251013_080603.mp4
-- Extract: 20251013_080603 -> 2025-10-13 08:06:03
UPDATE media
SET 
    start_timestamp = TO_TIMESTAMP(
        SUBSTRING(original_filename FROM '(\d{8}_\d{6})'),
        'YYYYMMDD_HH24MISS'
    ),
    end_timestamp = TO_TIMESTAMP(
        SUBSTRING(original_filename FROM '(\d{8}_\d{6})'),
        'YYYYMMDD_HH24MISS'
    ) + INTERVAL '30 seconds'
WHERE original_filename LIKE 'camera_%_segment_%_%.mp4'
  AND start_timestamp IS NULL;

-- Verify migration
SELECT COUNT(*) as total_videos,
       COUNT(start_timestamp) as videos_with_start,
       COUNT(end_timestamp) as videos_with_end
FROM media
WHERE media_type = 'video';

COMMENT ON COLUMN media.start_timestamp IS 'Recording start time (for camera videos)';
COMMENT ON COLUMN media.end_timestamp IS 'Recording end time (for camera videos)';
