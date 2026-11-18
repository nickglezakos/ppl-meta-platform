-- ============================================================================
-- Migration: Add hybrid settings support (mobile + admin)
-- 
-- This migration adds fields to support both mobile-first and admin-driven
-- settings updates:
-- 1. pending_settings: source and admin_override columns
-- 2. cameras: settings JSON, last_modified_by, last_modified_at columns
--
-- Run this migration before implementing Phase 3B/3C features.
-- ============================================================================

-- ============================================================================
-- Part 1: Enhance pending_camera_settings table for hybrid approach
-- ============================================================================

-- Add source column to track who initiated the setting change
ALTER TABLE pending_camera_settings
ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'admin';

-- Add admin_override flag for enterprise policy enforcement
ALTER TABLE pending_camera_settings
ADD COLUMN IF NOT EXISTS admin_override BOOLEAN DEFAULT FALSE;

-- Add priority column for future use
ALTER TABLE pending_camera_settings
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;

-- Add index on camera_device_id and applied_at for faster queries
CREATE INDEX IF NOT EXISTS idx_pending_settings_camera_applied 
ON pending_camera_settings(camera_device_id, applied_at);

-- Add comment explaining the columns
COMMENT ON COLUMN pending_camera_settings.source IS 'Who initiated the change: mobile or admin';
COMMENT ON COLUMN pending_camera_settings.admin_override IS 'If true, mobile app must apply this setting (enterprise policy)';
COMMENT ON COLUMN pending_camera_settings.priority IS 'Priority for applying settings (0=low, 10=high)';

-- ============================================================================
-- Part 2: Add settings tracking to cameras table
-- ============================================================================

-- Add settings JSON column to store all camera settings
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS settings JSONB;

-- Add last_modified_by column to track who last changed settings
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(20);

-- Add last_modified_at column to track when settings were last changed
ALTER TABLE cameras
ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP;

-- Add index on last_modified_at for sorting
CREATE INDEX IF NOT EXISTS idx_cameras_last_modified 
ON cameras(last_modified_at DESC);

-- Add comments
COMMENT ON COLUMN cameras.settings IS 'JSON object containing all camera settings';
COMMENT ON COLUMN cameras.last_modified_by IS 'Who last modified settings: mobile or admin';
COMMENT ON COLUMN cameras.last_modified_at IS 'When settings were last modified';

-- ============================================================================
-- Part 3: Initialize default settings for existing mobile cameras
-- ============================================================================

-- Set default settings for mobile cameras that don't have any
UPDATE cameras
SET settings = jsonb_build_object(
    'recording_enabled', true,
    'resolution', '1920x1080',
    'frame_rate', 30,
    'orientation', 'portrait',
    'auto_start_recording', false,
    'max_recording_duration', 300,
    'storage_limit_mb', 1000
),
last_modified_by = 'system',
last_modified_at = NOW()
WHERE camera_type = 'MOBILE' 
AND settings IS NULL;

-- ============================================================================
-- Part 4: Verify migration
-- ============================================================================

-- Check pending_settings columns
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'pending_camera_settings'
AND column_name IN ('source', 'admin_override', 'priority');

-- Check cameras columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'cameras'
AND column_name IN ('settings', 'last_modified_by', 'last_modified_at');

-- Count mobile cameras with settings
SELECT COUNT(*) as mobile_cameras_with_settings
FROM cameras
WHERE camera_type = 'MOBILE' AND settings IS NOT NULL;
