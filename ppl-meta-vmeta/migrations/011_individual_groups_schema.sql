-- ================================================================
-- Individual Groups Feature Database Schema
-- PPL Meta Platform - vmeta Service
-- ================================================================
-- 
-- This migration creates the database schema for the Individual Groups feature,
-- which allows users to organize detected individuals into custom groups.
--
-- Version: 1.0.0
-- Date: December 17, 2025
-- Service: vmeta (port 8008)
-- ================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- ================================================================
-- Table: individual_groups
-- Purpose: Store user-created groups for organizing individuals
-- ================================================================

CREATE TABLE IF NOT EXISTS individual_groups (
    -- Identity
    id TEXT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Ownership & Timestamps
    created_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Members
    member_count INTEGER DEFAULT 0 CHECK (member_count >= 0),
    member_ids TEXT[] DEFAULT '{}',
    
    -- Settings
    visibility TEXT DEFAULT 'private' CHECK (visibility IN ('private', 'shared', 'public')),
    tags TEXT[] DEFAULT '{}',
    
    -- Display
    cover_individual_id TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT valid_name_length CHECK (char_length(name) > 0)
);

-- ================================================================
-- Table: group_memberships
-- Purpose: Junction table for many-to-many relationship between
--          groups and individuals
-- ================================================================

CREATE TABLE IF NOT EXISTS group_memberships (
    -- Identity
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    individual_id TEXT NOT NULL,
    
    -- Audit
    added_by TEXT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Optional metadata
    notes TEXT,
    
    -- Foreign Keys
    CONSTRAINT fk_group
        FOREIGN KEY (group_id)
        REFERENCES individual_groups(id)
        ON DELETE CASCADE,
    
    -- Unique constraint: Each individual can only appear once per group
    CONSTRAINT unique_group_member
        UNIQUE (group_id, individual_id)
);

-- ================================================================
-- Indexes for Performance
-- ================================================================

-- Individual Groups Indexes
CREATE INDEX IF NOT EXISTS idx_individual_groups_created_by ON individual_groups(created_by);
CREATE INDEX IF NOT EXISTS idx_individual_groups_updated_at ON individual_groups(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_individual_groups_visibility ON individual_groups(visibility);
CREATE INDEX IF NOT EXISTS idx_individual_groups_tags ON individual_groups USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_individual_groups_name_search ON individual_groups USING GIN (to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_individual_groups_description_search ON individual_groups USING GIN (to_tsvector('english', description));

-- Group Memberships Indexes
CREATE INDEX IF NOT EXISTS idx_group_memberships_group_id ON group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_individual_id ON group_memberships(individual_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_added_at ON group_memberships(added_at DESC);
CREATE INDEX IF NOT EXISTS idx_group_memberships_added_by ON group_memberships(added_by);

-- ================================================================
-- Triggers for Automatic Timestamp Updates
-- ================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_individual_groups_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on individual_groups table
DROP TRIGGER IF EXISTS trigger_update_individual_groups_updated_at ON individual_groups;
CREATE TRIGGER trigger_update_individual_groups_updated_at
    BEFORE UPDATE ON individual_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_individual_groups_updated_at();

-- ================================================================
-- Functions for Member Count Management
-- ================================================================

-- Function to automatically update member_count when memberships change
CREATE OR REPLACE FUNCTION update_group_member_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE individual_groups
        SET member_count = array_length(member_ids, 1)
        WHERE id = NEW.group_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE individual_groups
        SET member_count = array_length(member_ids, 1)
        WHERE id = OLD.group_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Note: This trigger is optional as member_count is managed by the application
-- Uncomment if you want automatic database-level management:
-- DROP TRIGGER IF EXISTS trigger_update_group_member_count ON group_memberships;
-- CREATE TRIGGER trigger_update_group_member_count
--     AFTER INSERT OR DELETE ON group_memberships
--     FOR EACH ROW
--     EXECUTE FUNCTION update_group_member_count();

-- ================================================================
-- Sample Data (Optional - for development/testing)
-- ================================================================

-- Insert a sample group (commented out for production)
/*
INSERT INTO individual_groups (
    id, name, description, created_by, visibility, tags
) VALUES (
    'grp_sample001',
    'VIP Customers',
    'High-value customers identified across multiple store locations',
    'system',
    'private',
    ARRAY['vip', 'loyalty', 'high-value']
) ON CONFLICT (id) DO NOTHING;
*/

-- ================================================================
-- Views for Common Queries
-- ================================================================

-- View: Group summary with member counts
CREATE OR REPLACE VIEW individual_groups_summary AS
SELECT
    ig.id,
    ig.name,
    ig.description,
    ig.created_by,
    ig.created_at,
    ig.updated_at,
    ig.member_count,
    ig.visibility,
    ig.tags,
    COUNT(DISTINCT gm.individual_id) as actual_member_count,
    array_agg(DISTINCT gm.individual_id) FILTER (WHERE gm.individual_id IS NOT NULL) as member_list
FROM individual_groups ig
LEFT JOIN group_memberships gm ON ig.id = gm.group_id
GROUP BY ig.id, ig.name, ig.description, ig.created_by, ig.created_at, 
         ig.updated_at, ig.member_count, ig.visibility, ig.tags;

-- View: Individual membership summary
CREATE OR REPLACE VIEW individual_group_memberships AS
SELECT
    gm.individual_id,
    array_agg(ig.id) as group_ids,
    array_agg(ig.name) as group_names,
    COUNT(*) as group_count
FROM group_memberships gm
JOIN individual_groups ig ON gm.group_id = ig.id
GROUP BY gm.individual_id;

-- ================================================================
-- Permissions (Adjust based on your setup)
-- ================================================================

-- Grant permissions to vmeta service user (adjust username as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON individual_groups TO vmeta_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON group_memberships TO vmeta_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vmeta_user;

-- ================================================================
-- Migration Verification Queries
-- ================================================================

-- Check if tables were created successfully
DO $$
BEGIN
    RAISE NOTICE 'Verifying individual_groups table...';
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'individual_groups') THEN
        RAISE NOTICE '✅ individual_groups table created successfully';
    ELSE
        RAISE WARNING '❌ individual_groups table not found';
    END IF;
    
    RAISE NOTICE 'Verifying group_memberships table...';
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'group_memberships') THEN
        RAISE NOTICE '✅ group_memberships table created successfully';
    ELSE
        RAISE WARNING '❌ group_memberships table not found';
    END IF;
END $$;

-- ================================================================
-- Rollback Script (saved in separate file: 011_individual_groups_rollback.sql)
-- ================================================================
-- 
-- To rollback this migration, run:
-- DROP VIEW IF EXISTS individual_group_memberships;
-- DROP VIEW IF EXISTS individual_groups_summary;
-- DROP TRIGGER IF EXISTS trigger_update_group_member_count ON group_memberships;
-- DROP TRIGGER IF EXISTS trigger_update_individual_groups_updated_at ON individual_groups;
-- DROP FUNCTION IF EXISTS update_group_member_count();
-- DROP FUNCTION IF EXISTS update_individual_groups_updated_at();
-- DROP TABLE IF EXISTS group_memberships CASCADE;
-- DROP TABLE IF EXISTS individual_groups CASCADE;
-- 
-- ================================================================

-- End of migration
