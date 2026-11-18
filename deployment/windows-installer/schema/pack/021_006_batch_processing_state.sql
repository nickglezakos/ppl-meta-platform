-- Migration 006: Batch Processing State Table
-- Purpose: Tracks current state of batch accumulation per collection
-- Created: 2025-11-13

-- Create batch_processing_state table
CREATE TABLE IF NOT EXISTS batch_processing_state (
    -- Primary key
    batch_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Batch identification
    collection_id VARCHAR(255) NOT NULL,
    batch_number INTEGER NOT NULL,  -- Sequential number per collection
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'accumulating',
    video_count INTEGER NOT NULL DEFAULT 0,
    batch_size_threshold INTEGER NOT NULL DEFAULT 5,
    
    -- Time tracking
    first_video_start_time TIMESTAMP,
    last_video_end_time TIMESTAMP,
    last_video_time TIMESTAMP,  -- Time when last video was added
    timeout_at TIMESTAMP,  -- When timeout trigger should fire
    triggered_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Processing results
    session_uuid UUID,  -- Tracking session UUID
    individuals_created INTEGER DEFAULT 0,
    individuals_cached INTEGER DEFAULT 0,
    mvr_people_created INTEGER DEFAULT 0,
    mvr_people_cached INTEGER DEFAULT 0,
    processing_time_seconds DOUBLE PRECISION,
    
    -- Partial batch handling
    is_partial_batch BOOLEAN DEFAULT FALSE,
    trigger_reason VARCHAR(50),  -- 'threshold', 'timeout', 'recording_stopped', 'manual'
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_status CHECK (
        status IN ('accumulating', 'processing', 'completed', 'failed', 'incomplete')
    ),
    CONSTRAINT check_video_count CHECK (video_count >= 0),
    CONSTRAINT check_trigger_reason CHECK (
        trigger_reason IS NULL OR 
        trigger_reason IN ('threshold', 'timeout', 'recording_stopped', 'manual')
    )
);

-- Create indexes for efficient queries
CREATE INDEX idx_batch_processing_state_collection 
    ON batch_processing_state(collection_id, status);

CREATE INDEX idx_batch_processing_state_status 
    ON batch_processing_state(status)
    WHERE status IN ('accumulating', 'processing');

CREATE UNIQUE INDEX idx_batch_processing_state_active 
    ON batch_processing_state(collection_id)
    WHERE status = 'accumulating';

CREATE INDEX idx_batch_timeout 
    ON batch_processing_state(collection_id, timeout_at)
    WHERE status = 'accumulating' AND timeout_at IS NOT NULL;

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_batch_processing_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
CREATE TRIGGER trigger_batch_processing_state_updated_at
    BEFORE UPDATE ON batch_processing_state
    FOR EACH ROW
    EXECUTE FUNCTION update_batch_processing_state_updated_at();

-- Create function to get next batch number for collection
CREATE OR REPLACE FUNCTION get_next_batch_number(p_collection_id VARCHAR(255))
RETURNS INTEGER AS $$
DECLARE
    v_next_number INTEGER;
BEGIN
    SELECT COALESCE(MAX(batch_number), 0) + 1
    INTO v_next_number
    FROM batch_processing_state
    WHERE collection_id = p_collection_id;
    
    RETURN v_next_number;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE batch_processing_state IS 'Tracks current state of batch accumulation per collection for continuous individuals and MVR pipeline';
COMMENT ON COLUMN batch_processing_state.batch_uuid IS 'Unique identifier for batch';
COMMENT ON COLUMN batch_processing_state.collection_id IS 'Camera collection ID (e.g., usb_camera_0)';
COMMENT ON COLUMN batch_processing_state.batch_number IS 'Sequential batch number per collection';
COMMENT ON COLUMN batch_processing_state.status IS 'Current batch status: accumulating, processing, completed, failed, incomplete';
COMMENT ON COLUMN batch_processing_state.video_count IS 'Current number of videos in batch';
COMMENT ON COLUMN batch_processing_state.batch_size_threshold IS 'Number of videos that trigger batch processing';
COMMENT ON COLUMN batch_processing_state.is_partial_batch IS 'True if batch was triggered before reaching threshold';
COMMENT ON COLUMN batch_processing_state.trigger_reason IS 'What triggered batch processing: threshold, timeout, recording_stopped, manual';
COMMENT ON COLUMN batch_processing_state.timeout_at IS 'Timestamp when timeout trigger should fire (for partial batch handling)';

-- Insert initial test data (optional, for development)
-- INSERT INTO batch_processing_state (
--     collection_id,
--     batch_number,
--     status,
--     batch_size_threshold
-- ) VALUES (
--     'test_camera_001',
--     1,
--     'accumulating',
--     5
-- );

-- Verify table creation
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'batch_processing_state'
    ) THEN
        RAISE NOTICE 'Table batch_processing_state created successfully';
    ELSE
        RAISE EXCEPTION 'Failed to create table batch_processing_state';
    END IF;
END $$;
