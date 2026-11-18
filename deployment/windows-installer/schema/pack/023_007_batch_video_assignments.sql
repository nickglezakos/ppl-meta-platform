-- Migration 007: Batch Video Assignments Table
-- Purpose: Tracks which videos belong to which batch
-- Created: 2025-11-13

-- Create batch_video_assignments table
CREATE TABLE IF NOT EXISTS batch_video_assignments (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- References
    batch_uuid UUID NOT NULL REFERENCES batch_processing_state(batch_uuid) ON DELETE CASCADE,
    video_uuid UUID NOT NULL,
    collection_id VARCHAR(255) NOT NULL,
    
    -- Video metadata
    video_start_time TIMESTAMP NOT NULL,
    video_end_time TIMESTAMP NOT NULL,
    face_detection_session_uuid UUID,
    faces_detected INTEGER,
    
    -- Assignment metadata
    added_at TIMESTAMP DEFAULT NOW(),
    sequence_number INTEGER NOT NULL,  -- Order within batch (1, 2, 3, ...)
    
    -- Constraints
    CONSTRAINT unique_batch_video UNIQUE(batch_uuid, video_uuid)
);

-- Create indexes for efficient queries
CREATE INDEX idx_batch_video_assignments_batch 
    ON batch_video_assignments(batch_uuid);

CREATE INDEX idx_batch_video_assignments_video 
    ON batch_video_assignments(video_uuid);

CREATE INDEX idx_batch_video_assignments_collection 
    ON batch_video_assignments(collection_id, video_start_time DESC);

CREATE INDEX idx_batch_video_assignments_sequence 
    ON batch_video_assignments(batch_uuid, sequence_number);

-- Create function to get videos for a batch
CREATE OR REPLACE FUNCTION get_batch_videos(p_batch_uuid UUID)
RETURNS TABLE(
    video_uuid UUID,
    video_start_time TIMESTAMP,
    video_end_time TIMESTAMP,
    sequence_number INTEGER,
    faces_detected INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bva.video_uuid,
        bva.video_start_time,
        bva.video_end_time,
        bva.sequence_number,
        bva.faces_detected
    FROM batch_video_assignments bva
    WHERE bva.batch_uuid = p_batch_uuid
    ORDER BY bva.sequence_number;
END;
$$ LANGUAGE plpgsql;

-- Create function to check if video already assigned to a batch
CREATE OR REPLACE FUNCTION is_video_in_batch(
    p_video_uuid UUID,
    p_collection_id VARCHAR(255)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM batch_video_assignments bva
        JOIN batch_processing_state bps ON bva.batch_uuid = bps.batch_uuid
        WHERE bva.video_uuid = p_video_uuid
          AND bva.collection_id = p_collection_id
          AND bps.status IN ('accumulating', 'processing')
    ) INTO v_exists;
    
    RETURN v_exists;
END;
$$ LANGUAGE plpgsql;

-- Create function to get next sequence number for batch
CREATE OR REPLACE FUNCTION get_next_sequence_number(p_batch_uuid UUID)
RETURNS INTEGER AS $$
DECLARE
    v_next_seq INTEGER;
BEGIN
    SELECT COALESCE(MAX(sequence_number), 0) + 1
    INTO v_next_seq
    FROM batch_video_assignments
    WHERE batch_uuid = p_batch_uuid;
    
    RETURN v_next_seq;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE batch_video_assignments IS 'Tracks which videos belong to which batch in the continuous individuals pipeline';
COMMENT ON COLUMN batch_video_assignments.batch_uuid IS 'Reference to batch in batch_processing_state';
COMMENT ON COLUMN batch_video_assignments.video_uuid IS 'UUID of video from Media Service';
COMMENT ON COLUMN batch_video_assignments.collection_id IS 'Camera collection ID for quick filtering';
COMMENT ON COLUMN batch_video_assignments.sequence_number IS 'Order of video within batch (1-based)';
COMMENT ON COLUMN batch_video_assignments.face_detection_session_uuid IS 'Vision Service face detection session UUID';
COMMENT ON COLUMN batch_video_assignments.faces_detected IS 'Number of faces detected in video';

-- Create view for batch video summary
CREATE OR REPLACE VIEW batch_video_summary AS
SELECT 
    bps.batch_uuid,
    bps.collection_id,
    bps.batch_number,
    bps.status,
    COUNT(bva.id) as video_count,
    MIN(bva.video_start_time) as earliest_video_time,
    MAX(bva.video_end_time) as latest_video_time,
    SUM(bva.faces_detected) as total_faces_detected
FROM batch_processing_state bps
LEFT JOIN batch_video_assignments bva ON bps.batch_uuid = bva.batch_uuid
GROUP BY bps.batch_uuid, bps.collection_id, bps.batch_number, bps.status;

COMMENT ON VIEW batch_video_summary IS 'Summary view of videos per batch with aggregated statistics';

-- Verify table creation
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'batch_video_assignments'
    ) THEN
        RAISE NOTICE 'Table batch_video_assignments created successfully';
    ELSE
        RAISE EXCEPTION 'Failed to create table batch_video_assignments';
    END IF;
END $$;
