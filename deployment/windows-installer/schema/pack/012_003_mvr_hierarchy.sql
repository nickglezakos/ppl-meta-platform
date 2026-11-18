-- Migration: Create MVR Merge Hierarchy Table
-- Version: 2.19.92
-- Description: Adds support for hierarchical MVR merging

-- =============================================
-- MVR MERGE HIERARCHY TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS mvr_merge_hierarchy (
    super_individual_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    merged_mvr_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    similarity_score FLOAT NOT NULL CHECK (similarity_score >= 0 AND similarity_score <= 1),
    merge_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    merge_level INT NOT NULL DEFAULT 1 CHECK (merge_level >= 1),
    
    PRIMARY KEY (super_individual_uuid, merged_mvr_uuid),
    
    -- Prevent self-merging
    CONSTRAINT no_self_merge CHECK (super_individual_uuid != merged_mvr_uuid)
);

-- Add comments
COMMENT ON TABLE mvr_merge_hierarchy IS 'Hierarchical relationships between super-individuals and merged MVR people';
COMMENT ON COLUMN mvr_merge_hierarchy.super_individual_uuid IS 'The parent super-individual MVR UUID';
COMMENT ON COLUMN mvr_merge_hierarchy.merged_mvr_uuid IS 'The merged child MVR UUID';
COMMENT ON COLUMN mvr_merge_hierarchy.similarity_score IS 'Similarity score that triggered the merge (0-1)';
COMMENT ON COLUMN mvr_merge_hierarchy.merge_timestamp IS 'When the merge was performed';
COMMENT ON COLUMN mvr_merge_hierarchy.merge_level IS 'Level in the hierarchy (1=direct child, 2+=transitive)';

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_mvr_hierarchy_super 
ON mvr_merge_hierarchy(super_individual_uuid);

CREATE INDEX IF NOT EXISTS idx_mvr_hierarchy_merged 
ON mvr_merge_hierarchy(merged_mvr_uuid);

CREATE INDEX IF NOT EXISTS idx_mvr_hierarchy_timestamp 
ON mvr_merge_hierarchy(merge_timestamp);

-- Add flag to mvr_people table to mark merged MVR
ALTER TABLE mvr_people 
ADD COLUMN IF NOT EXISTS is_merged BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE mvr_people 
ADD COLUMN IF NOT EXISTS merged_into_uuid UUID REFERENCES mvr_people(mvr_people_uuid) ON DELETE SET NULL;

-- Add comments for new columns
COMMENT ON COLUMN mvr_people.is_merged IS 'True if this MVR has been merged into a super-individual';
COMMENT ON COLUMN mvr_people.merged_into_uuid IS 'UUID of the super-individual this MVR was merged into';

-- Create index on merged status for efficient filtering
CREATE INDEX IF NOT EXISTS idx_mvr_people_merged 
ON mvr_people(is_merged, merged_into_uuid) 
WHERE is_merged = TRUE;
