-- Minimal individual_groups schema for installer/demo (no pgvector required)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS individual_groups (
    id TEXT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    member_count INTEGER DEFAULT 0 CHECK (member_count >= 0),
    member_ids TEXT[] DEFAULT '{}',
    visibility TEXT DEFAULT 'private' CHECK (visibility IN ('private', 'shared', 'public')),
    tags TEXT[] DEFAULT '{}',
    cover_individual_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_name_length CHECK (char_length(name) > 0)
);

CREATE TABLE IF NOT EXISTS group_memberships (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    individual_id TEXT NOT NULL,
    added_by TEXT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    CONSTRAINT fk_group
        FOREIGN KEY (group_id)
        REFERENCES individual_groups(id)
        ON DELETE CASCADE,
    CONSTRAINT unique_group_member
        UNIQUE (group_id, individual_id)
);

CREATE INDEX IF NOT EXISTS idx_individual_groups_created_by ON individual_groups(created_by);
CREATE INDEX IF NOT EXISTS idx_individual_groups_updated_at ON individual_groups(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_individual_groups_visibility ON individual_groups(visibility);
CREATE INDEX IF NOT EXISTS idx_group_memberships_group_id ON group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_individual_id ON group_memberships(individual_id);

CREATE OR REPLACE FUNCTION update_individual_groups_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_individual_groups_updated_at ON individual_groups;
CREATE TRIGGER trigger_update_individual_groups_updated_at
    BEFORE UPDATE ON individual_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_individual_groups_updated_at();
