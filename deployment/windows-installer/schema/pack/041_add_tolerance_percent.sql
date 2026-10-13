-- Migration: Add tolerance_percent to camera_settings
-- Date: 2026-02-08
-- Description: Add IoU tolerance threshold setting for person grouping across frames

-- Add tolerance_percent column with default value of 20%
ALTER TABLE camera_settings 
ADD COLUMN IF NOT EXISTS tolerance_percent INTEGER DEFAULT 20 NOT NULL;

-- Add comment to column
COMMENT ON COLUMN camera_settings.tolerance_percent IS 'IoU (Intersection over Union) threshold percentage for grouping detected faces into person objects across frames. Range: 10-50%. Lower = more sensitive grouping, Higher = stricter grouping. Default: 20%';

-- Update existing rows to have the default value
UPDATE camera_settings 
SET tolerance_percent = 20 
WHERE tolerance_percent IS NULL;
