-- Migration: Create pending_camera_settings table
-- Date: 2026-02-11
-- Purpose: Queue camera setting updates for offline cameras (especially mobile cameras)

-- Create pending_camera_settings table
CREATE TABLE IF NOT EXISTS pending_camera_settings (
    id SERIAL PRIMARY KEY,
    camera_device_id VARCHAR(255) NOT NULL,
    setting_type VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE,
    is_applied VARCHAR(20) DEFAULT 'pending' NOT NULL,
    error_message VARCHAR(500),
    retry_count INTEGER DEFAULT 0
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_pending_settings_camera_id 
ON pending_camera_settings(camera_device_id);

CREATE INDEX IF NOT EXISTS idx_pending_settings_lookup 
ON pending_camera_settings(camera_device_id, is_applied);

CREATE INDEX IF NOT EXISTS idx_pending_settings_created_at 
ON pending_camera_settings(created_at);

-- Add foreign key constraint (optional - can be removed if you want loose coupling)
-- ALTER TABLE pending_camera_settings
-- ADD CONSTRAINT fk_pending_settings_camera
-- FOREIGN KEY (camera_device_id) REFERENCES cameras(device_id) ON DELETE CASCADE;

-- Add comments
COMMENT ON TABLE pending_camera_settings IS 'Stores camera settings to be applied when cameras come online';
COMMENT ON COLUMN pending_camera_settings.camera_device_id IS 'UUID of the camera';
COMMENT ON COLUMN pending_camera_settings.setting_type IS 'Type of setting: name_update, workflow_settings, etc.';
COMMENT ON COLUMN pending_camera_settings.setting_value IS 'JSON data containing the setting values';
COMMENT ON COLUMN pending_camera_settings.is_applied IS 'Status: pending, applied, failed';
