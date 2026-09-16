-- Migration: Add hardware_identifier column to cameras table
-- Date: 2026-02-11
-- Purpose: Support stable device identification across app reinstalls for mobile cameras

-- Add hardware_identifier column to cameras table
ALTER TABLE cameras 
ADD COLUMN IF NOT EXISTS hardware_identifier VARCHAR(500);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_cameras_hardware_identifier 
ON cameras(hardware_identifier);

-- Backfill hardware_identifier for existing cameras
-- For mobile cameras, use manufacturer_model_serial if available
UPDATE cameras 
SET hardware_identifier = CONCAT(
    COALESCE(manufacturer, 'unknown'), 
    '_', 
    COALESCE(model, 'unknown'),
    '_',
    COALESCE(serial_number, device_id)
)
WHERE hardware_identifier IS NULL
  AND camera_type = 'MOBILE'
  AND (manufacturer IS NOT NULL OR model IS NOT NULL OR serial_number IS NOT NULL);

-- For USB/RTSP cameras, use existing device_id as hardware_identifier if not set
UPDATE cameras
SET hardware_identifier = device_id
WHERE hardware_identifier IS NULL
  AND camera_type IN ('USB', 'RTSP', 'IP');

-- Add comment to column
COMMENT ON COLUMN cameras.hardware_identifier IS 'Stable hardware identifier (manufacturer_model_serial) for device detection across registrations';
