-- ppl-meta-cameras/migrations/create_profile_templates.sql
-- Migration for User Profile Templates - Phase 3 Implementation
-- Creates tables for custom user templates, favorites, and usage analytics

-- Create user profile templates table
CREATE TABLE IF NOT EXISTS user_profile_templates (
    id SERIAL PRIMARY KEY,
    template_uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- Template metadata
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    tags JSONB,
    
    -- Recording Quality Settings (matching CameraRecordingProfile)
    quality VARCHAR(20) DEFAULT 'high',
    format VARCHAR(10) DEFAULT 'mp4',
    resolution VARCHAR(20) DEFAULT '1920x1080',
    frame_rate INTEGER DEFAULT 30,
    bitrate_kbps INTEGER DEFAULT 5000,
    
    -- Duration and Timing
    default_duration_seconds INTEGER DEFAULT 30,
    max_duration_seconds INTEGER DEFAULT 3600,
    segment_interval_seconds INTEGER,
    
    -- Automatic Recording Settings
    enable_auto_recording BOOLEAN DEFAULT FALSE,
    auto_recording_schedule JSONB,
    motion_detection_enabled BOOLEAN DEFAULT FALSE,
    motion_sensitivity VARCHAR(20) DEFAULT 'medium',
    
    -- Audio Settings
    enable_audio BOOLEAN DEFAULT TRUE,
    audio_quality VARCHAR(20) DEFAULT 'medium',
    audio_bitrate_kbps INTEGER DEFAULT 128,
    
    -- Storage and Retention
    storage_location VARCHAR(200) DEFAULT 'default',
    retention_days INTEGER DEFAULT 30,
    auto_delete_enabled BOOLEAN DEFAULT TRUE,
    compression_enabled BOOLEAN DEFAULT TRUE,
    
    -- Processing Settings
    enable_face_detection BOOLEAN DEFAULT FALSE,
    enable_object_detection BOOLEAN DEFAULT FALSE,
    processing_priority VARCHAR(20) DEFAULT 'normal',
    
    -- Advanced Configuration
    custom_ffmpeg_params JSONB,
    metadata_config JSONB,
    notification_config JSONB,
    
    -- User and ownership
    created_by_user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    is_public BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    favorite_count INTEGER DEFAULT 0,
    
    -- Version and sharing
    version VARCHAR(20) DEFAULT '1.0',
    parent_template_id INTEGER REFERENCES user_profile_templates(id),
    is_template_copy BOOLEAN DEFAULT FALSE,
    shared_by_user_id VARCHAR(100),
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_template_name_per_user UNIQUE (name, created_by_user_id),
    CONSTRAINT valid_quality CHECK (quality IN ('low', 'medium', 'high', 'ultra')),
    CONSTRAINT valid_format CHECK (format IN ('mp4', 'avi', 'mkv', 'webm')),
    CONSTRAINT valid_motion_sensitivity CHECK (motion_sensitivity IN ('low', 'medium', 'high')),
    CONSTRAINT valid_audio_quality CHECK (audio_quality IN ('low', 'medium', 'high')),
    CONSTRAINT valid_processing_priority CHECK (processing_priority IN ('low', 'normal', 'high')),
    CONSTRAINT positive_duration CHECK (default_duration_seconds > 0),
    CONSTRAINT max_duration_valid CHECK (max_duration_seconds >= default_duration_seconds),
    CONSTRAINT positive_bitrate CHECK (bitrate_kbps > 0),
    CONSTRAINT positive_audio_bitrate CHECK (audio_bitrate_kbps > 0),
    CONSTRAINT positive_retention CHECK (retention_days > 0)
);

-- Create indexes for user profile templates
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_created_by ON user_profile_templates(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_organization ON user_profile_templates(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_category ON user_profile_templates(category);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_public ON user_profile_templates(is_public);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_featured ON user_profile_templates(is_featured);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_usage_count ON user_profile_templates(usage_count);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_favorite_count ON user_profile_templates(favorite_count);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_created_at ON user_profile_templates(created_at);
CREATE INDEX IF NOT EXISTS idx_user_profile_templates_tags ON user_profile_templates USING GIN(tags);

-- Create user template favorites table
CREATE TABLE IF NOT EXISTS user_template_favorites (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    template_id INTEGER NOT NULL REFERENCES user_profile_templates(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Constraints
    CONSTRAINT unique_user_template_favorite UNIQUE (user_id, template_id)
);

-- Create indexes for user template favorites
CREATE INDEX IF NOT EXISTS idx_user_template_favorites_user ON user_template_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_user_template_favorites_template ON user_template_favorites(template_id);
CREATE INDEX IF NOT EXISTS idx_user_template_favorites_created_at ON user_template_favorites(created_at);

-- Create template usage analytics table
CREATE TABLE IF NOT EXISTS template_usage_analytics (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES user_profile_templates(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    camera_id VARCHAR(100),
    context_data JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for template usage analytics
CREATE INDEX IF NOT EXISTS idx_template_usage_analytics_template ON template_usage_analytics(template_id);
CREATE INDEX IF NOT EXISTS idx_template_usage_analytics_user ON template_usage_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_template_usage_analytics_action ON template_usage_analytics(action);
CREATE INDEX IF NOT EXISTS idx_template_usage_analytics_camera ON template_usage_analytics(camera_id);
CREATE INDEX IF NOT EXISTS idx_template_usage_analytics_timestamp ON template_usage_analytics(timestamp);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profile_templates_updated_at
    BEFORE UPDATE ON user_profile_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create trigger to update favorite count when favorites are added/removed
CREATE OR REPLACE FUNCTION update_template_favorite_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE user_profile_templates 
        SET favorite_count = favorite_count + 1 
        WHERE id = NEW.template_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE user_profile_templates 
        SET favorite_count = favorite_count - 1 
        WHERE id = OLD.template_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_template_favorite_count_trigger
    AFTER INSERT OR DELETE ON user_template_favorites
    FOR EACH ROW
    EXECUTE FUNCTION update_template_favorite_count();

-- Insert featured system templates
INSERT INTO user_profile_templates (
    template_uuid,
    name,
    description,
    category,
    tags,
    quality,
    format,
    resolution,
    frame_rate,
    bitrate_kbps,
    default_duration_seconds,
    max_duration_seconds,
    enable_auto_recording,
    motion_detection_enabled,
    enable_face_detection,
    created_by_user_id,
    is_public,
    is_featured,
    version
) VALUES 
-- Security Monitoring Template
(
    'template-security-monitoring-001',
    'Security Monitoring - High Quality',
    'High-quality recording template for security applications with motion detection and face detection enabled',
    'security',
    '["security", "monitoring", "motion", "face-detection"]',
    'high',
    'mp4',
    '1920x1080',
    30,
    8000,
    60,
    7200,
    true,
    true,
    true,
    'system',
    true,
    true,
    '1.0'
),
-- Event Recording Template
(
    'template-event-recording-001',
    'Event Recording - Ultra Quality',
    'Ultra-quality recording template for important events with extended duration',
    'event',
    '["event", "ultra-quality", "long-duration"]',
    'ultra',
    'mp4',
    '3840x2160',
    60,
    15000,
    300,
    18000,
    false,
    false,
    false,
    'system',
    true,
    true,
    '1.0'
),
-- Motion Detection Template
(
    'template-motion-detection-001',
    'Motion Detection - Efficient',
    'Efficient recording template optimized for motion-triggered recording',
    'monitoring',
    '["motion", "efficient", "auto-recording"]',
    'medium',
    'mp4',
    '1280x720',
    24,
    3000,
    30,
    1800,
    true,
    true,
    false,
    'system',
    true,
    true,
    '1.0'
),
-- General Purpose Template
(
    'template-general-purpose-001',
    'General Purpose - Balanced',
    'Balanced recording template suitable for most general recording needs',
    'general',
    '["general", "balanced", "default"]',
    'medium',
    'mp4',
    '1920x1080',
    30,
    5000,
    60,
    3600,
    false,
    false,
    false,
    'system',
    true,
    true,
    '1.0'
),
-- Low Storage Template
(
    'template-low-storage-001',
    'Low Storage - Compressed',
    'Optimized for minimal storage usage while maintaining acceptable quality',
    'storage',
    '["low-storage", "compressed", "efficient"]',
    'low',
    'mp4',
    '854x480',
    15,
    1500,
    30,
    1800,
    false,
    false,
    false,
    'system',
    true,
    true,
    '1.0'
);

-- Add comments
COMMENT ON TABLE user_profile_templates IS 'User-created recording profile templates for saving and sharing configurations';
COMMENT ON TABLE user_template_favorites IS 'User favorites for profile templates';
COMMENT ON TABLE template_usage_analytics IS 'Analytics tracking for template usage patterns';

COMMENT ON COLUMN user_profile_templates.template_uuid IS 'Unique identifier for the template';
COMMENT ON COLUMN user_profile_templates.is_public IS 'Whether template can be shared publicly';
COMMENT ON COLUMN user_profile_templates.is_featured IS 'Whether template is featured in the template library';
COMMENT ON COLUMN user_profile_templates.usage_count IS 'Number of times template has been applied';
COMMENT ON COLUMN user_profile_templates.favorite_count IS 'Number of users who have favorited this template';
COMMENT ON COLUMN user_profile_templates.parent_template_id IS 'Reference to parent template if this is a copy';
COMMENT ON COLUMN user_profile_templates.is_template_copy IS 'Whether this template is a copy of another template';

COMMENT ON COLUMN template_usage_analytics.action IS 'Action performed: applied, copied, favorited, shared';
COMMENT ON COLUMN template_usage_analytics.context_data IS 'Additional context information about the usage';