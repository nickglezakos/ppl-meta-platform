# ppl-meta-cameras/migrations/create_recording_profiles.sql

-- Migration: Create Recording Profiles Infrastructure
-- Version: Phase 2.1 - Recording Profiles Foundation
-- Date: October 14, 2025

-- Create the camera_recording_profiles table
CREATE TABLE IF NOT EXISTS camera_recording_profiles (
    -- Primary identification
    id SERIAL PRIMARY KEY,
    profile_uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- Profile metadata
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- User and ownership
    created_by_user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    
    -- Recording configuration parameters
    segment_interval_seconds INTEGER NULL, -- null = manual recording only
    segment_duration_seconds INTEGER DEFAULT 30 NOT NULL,
    auto_segment_recording BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Video quality settings
    recording_quality VARCHAR(20) DEFAULT 'high' NOT NULL 
        CHECK (recording_quality IN ('low', 'medium', 'high')),
    video_codec VARCHAR(20) DEFAULT 'h264' NOT NULL
        CHECK (video_codec IN ('h264', 'h265', 'vp8', 'vp9')),
    audio_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Processing settings
    auto_face_detection_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    face_detection_method VARCHAR(20) DEFAULT 'two_stage' NOT NULL
        CHECK (face_detection_method IN ('single_stage', 'two_stage', 'cascade')),
    enable_motion_detection BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Storage and retention
    storage_location VARCHAR(50) DEFAULT 'local' NOT NULL
        CHECK (storage_location IN ('local', 's3', 'gcs', 'azure')),
    retention_days INTEGER DEFAULT 30 NOT NULL
        CHECK (retention_days >= 1 AND retention_days <= 365),
    auto_cleanup_enabled BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Schedule and triggers (JSON for flexibility)
    schedule_config JSONB,
    trigger_conditions JSONB,
    
    -- Metadata and tracking
    usage_count INTEGER DEFAULT 0 NOT NULL,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT valid_segment_interval CHECK (
        segment_interval_seconds IS NULL OR 
        (segment_interval_seconds >= 5 AND segment_interval_seconds <= 3600)
    ),
    CONSTRAINT valid_segment_duration CHECK (
        segment_duration_seconds >= 5 AND segment_duration_seconds <= 300
    )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_recording_profiles_uuid 
    ON camera_recording_profiles(profile_uuid);
    
CREATE INDEX IF NOT EXISTS idx_recording_profiles_system_default 
    ON camera_recording_profiles(is_system_default);
    
CREATE INDEX IF NOT EXISTS idx_recording_profiles_active 
    ON camera_recording_profiles(is_active);
    
CREATE INDEX IF NOT EXISTS idx_recording_profiles_user 
    ON camera_recording_profiles(created_by_user_id);
    
CREATE INDEX IF NOT EXISTS idx_recording_profiles_organization 
    ON camera_recording_profiles(organization_id);
    
CREATE INDEX IF NOT EXISTS idx_recording_profiles_usage 
    ON camera_recording_profiles(usage_count DESC);

-- Add foreign key constraint to cameras table to link to recording profiles
ALTER TABLE cameras 
ADD COLUMN IF NOT EXISTS recording_profile_id INTEGER 
REFERENCES camera_recording_profiles(id) ON DELETE SET NULL;

-- Create index for camera-profile relationship
CREATE INDEX IF NOT EXISTS idx_cameras_recording_profile 
    ON cameras(recording_profile_id);

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_recording_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER trigger_recording_profile_updated_at
    BEFORE UPDATE ON camera_recording_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_recording_profile_updated_at();

-- Insert system default profiles
INSERT INTO camera_recording_profiles (
    profile_uuid, name, description, is_system_default, created_by_user_id,
    segment_interval_seconds, segment_duration_seconds, auto_segment_recording,
    recording_quality, auto_face_detection_enabled, enable_motion_detection, retention_days
) VALUES 
-- Manual Recording Only
(
    gen_random_uuid()::text,
    'Manual Recording Only',
    'Basic on-demand recording without automatic segments',
    TRUE,
    'system',
    NULL, -- Manual only
    30,
    FALSE,
    'high',
    TRUE,
    FALSE,
    30
),

-- Security Monitor
(
    gen_random_uuid()::text,
    'Security Monitor', 
    '60-second segments every 5 minutes for security monitoring',
    TRUE,
    'system',
    300, -- Every 5 minutes
    60,  -- 60-second segments
    TRUE,
    'high',
    TRUE,
    TRUE,
    60
),

-- Activity Logger
(
    gen_random_uuid()::text,
    'Activity Logger',
    '15-second segments every 30 seconds for detailed activity logging', 
    TRUE,
    'system',
    30,  -- Every 30 seconds
    15,  -- 15-second segments
    TRUE,
    'medium',
    TRUE,
    FALSE,
    14
),

-- Event Detection
(
    gen_random_uuid()::text,
    'Event Detection',
    '30-second segments every minute for balanced event detection',
    TRUE, 
    'system',
    60,  -- Every minute
    30,  -- 30-second segments
    TRUE,
    'high',
    TRUE,
    TRUE,
    30
),

-- High Traffic
(
    gen_random_uuid()::text,
    'High Traffic',
    '10-second segments every 15 seconds for high-traffic areas',
    TRUE,
    'system', 
    15,  -- Every 15 seconds
    10,  -- 10-second segments
    TRUE,
    'medium', -- Balance quality vs storage
    TRUE,
    FALSE,
    7    -- Shorter retention due to high volume
)

-- Handle conflicts (in case profiles already exist)
ON CONFLICT (profile_uuid) DO NOTHING;