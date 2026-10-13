-- Migration: Signage rich message templates (non-blocking overlays)
-- Date: 2026-10-01
-- Purpose: Reusable HTML/media/sound overlay templates for signage players

CREATE TABLE IF NOT EXISTS signage_rich_message_templates (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '',
    message TEXT,
    html_body TEXT,
    title_font_size INTEGER NOT NULL DEFAULT 48,
    message_font_size INTEGER NOT NULL DEFAULT 28,
    title_color VARCHAR(32) NOT NULL DEFAULT '#FFFFFF',
    message_color VARCHAR(32) NOT NULL DEFAULT '#F0F0F0',
    background_color VARCHAR(32) NOT NULL DEFAULT '#000000',
    opacity INTEGER NOT NULL DEFAULT 80,
    layout VARCHAR(50) NOT NULL DEFAULT 'card',
    media_id INTEGER REFERENCES media(id) ON DELETE SET NULL,
    sound_media_id INTEGER REFERENCES media(id) ON DELETE SET NULL,
    default_duration_ms INTEGER NOT NULL DEFAULT 15000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_signage_rich_message_templates_uuid
    ON signage_rich_message_templates (uuid);
CREATE INDEX IF NOT EXISTS ix_signage_rich_message_templates_user_id
    ON signage_rich_message_templates (user_id);
CREATE INDEX IF NOT EXISTS ix_signage_rich_message_templates_name
    ON signage_rich_message_templates (name);
CREATE INDEX IF NOT EXISTS ix_signage_rich_message_templates_is_active
    ON signage_rich_message_templates (is_active);

COMMENT ON TABLE signage_rich_message_templates IS
  'Reusable rich media message overlays for signage (shown over continuing playlist playback)';
