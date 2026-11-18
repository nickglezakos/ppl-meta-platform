-- Migration 008: Batch Processing History Table
-- Purpose: Audit log of all completed batches with performance metrics
-- Created: 2025-11-13

-- Create batch_processing_history table
CREATE TABLE IF NOT EXISTS batch_processing_history (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- References
    batch_uuid UUID NOT NULL,
    collection_id VARCHAR(255) NOT NULL,
    batch_number INTEGER NOT NULL,
    
    -- Batch summary
    video_count INTEGER NOT NULL,
    individuals_created INTEGER NOT NULL,
    individuals_cached INTEGER NOT NULL,
    mvr_people_created INTEGER NOT NULL,
    mvr_people_cached INTEGER NOT NULL,
    
    -- Performance metrics
    processing_time_seconds DOUBLE PRECISION NOT NULL,
    cache_hit_rate DOUBLE PRECISION,  -- Percentage (0.0 - 100.0)
    throughput_videos_per_sec DOUBLE PRECISION,
    
    -- Time range
    batch_start_time TIMESTAMP NOT NULL,
    batch_end_time TIMESTAMP NOT NULL,
    triggered_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    
    -- Processing metadata
    session_uuid UUID,
    status VARCHAR(50) NOT NULL,
    is_partial_batch BOOLEAN DEFAULT FALSE,
    trigger_reason VARCHAR(50),
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_history_status CHECK (
        status IN ('completed', 'failed')
    ),
    CONSTRAINT check_video_count_positive CHECK (video_count > 0),
    CONSTRAINT check_processing_time CHECK (processing_time_seconds >= 0),
    CONSTRAINT check_cache_hit_rate CHECK (
        cache_hit_rate IS NULL OR (cache_hit_rate >= 0 AND cache_hit_rate <= 100)
    )
);

-- Create indexes for efficient queries
CREATE INDEX idx_batch_processing_history_collection 
    ON batch_processing_history(collection_id, created_at DESC);

CREATE INDEX idx_batch_processing_history_batch_uuid 
    ON batch_processing_history(batch_uuid);

CREATE INDEX idx_batch_processing_history_status 
    ON batch_processing_history(status)
    WHERE status = 'failed';

CREATE INDEX idx_batch_processing_history_time_range 
    ON batch_processing_history(batch_start_time, batch_end_time);

CREATE INDEX idx_batch_processing_history_performance 
    ON batch_processing_history(collection_id, processing_time_seconds, cache_hit_rate);

-- Create function to add batch to history
CREATE OR REPLACE FUNCTION archive_batch_to_history(p_batch_uuid UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO batch_processing_history (
        batch_uuid,
        collection_id,
        batch_number,
        video_count,
        individuals_created,
        individuals_cached,
        mvr_people_created,
        mvr_people_cached,
        processing_time_seconds,
        cache_hit_rate,
        throughput_videos_per_sec,
        batch_start_time,
        batch_end_time,
        triggered_at,
        completed_at,
        session_uuid,
        status,
        is_partial_batch,
        trigger_reason,
        error_message
    )
    SELECT 
        bps.batch_uuid,
        bps.collection_id,
        bps.batch_number,
        bps.video_count,
        bps.individuals_created,
        bps.individuals_cached,
        bps.mvr_people_created,
        bps.mvr_people_cached,
        bps.processing_time_seconds,
        CASE 
            WHEN (bps.individuals_created + bps.individuals_cached) > 0 
            THEN (bps.individuals_cached::DOUBLE PRECISION / 
                  (bps.individuals_created + bps.individuals_cached) * 100)
            ELSE 0
        END as cache_hit_rate,
        CASE 
            WHEN bps.processing_time_seconds > 0 
            THEN (bps.video_count::DOUBLE PRECISION / bps.processing_time_seconds)
            ELSE 0
        END as throughput_videos_per_sec,
        bps.first_video_start_time,
        bps.last_video_end_time,
        bps.triggered_at,
        bps.completed_at,
        bps.session_uuid,
        bps.status,
        bps.is_partial_batch,
        bps.trigger_reason,
        bps.error_message
    FROM batch_processing_state bps
    WHERE bps.batch_uuid = p_batch_uuid
      AND bps.status IN ('completed', 'failed');
    
    IF NOT FOUND THEN
        RAISE NOTICE 'Batch % not found or not in completed/failed status', p_batch_uuid;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to get performance statistics for collection
CREATE OR REPLACE FUNCTION get_collection_batch_stats(
    p_collection_id VARCHAR(255),
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE(
    total_batches BIGINT,
    avg_processing_time DOUBLE PRECISION,
    avg_cache_hit_rate DOUBLE PRECISION,
    avg_throughput DOUBLE PRECISION,
    total_videos_processed BIGINT,
    total_individuals_created BIGINT,
    total_mvr_people_created BIGINT,
    success_rate DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_batches,
        AVG(bph.processing_time_seconds) as avg_processing_time,
        AVG(bph.cache_hit_rate) as avg_cache_hit_rate,
        AVG(bph.throughput_videos_per_sec) as avg_throughput,
        SUM(bph.video_count)::BIGINT as total_videos_processed,
        SUM(bph.individuals_created + bph.individuals_cached)::BIGINT as total_individuals_created,
        SUM(bph.mvr_people_created + bph.mvr_people_cached)::BIGINT as total_mvr_people_created,
        (COUNT(*) FILTER (WHERE bph.status = 'completed')::DOUBLE PRECISION / 
         NULLIF(COUNT(*), 0) * 100) as success_rate
    FROM (
        SELECT * 
        FROM batch_processing_history 
        WHERE collection_id = p_collection_id
        ORDER BY created_at DESC
        LIMIT p_limit
    ) bph;
END;
$$ LANGUAGE plpgsql;

-- Create view for recent batch history
CREATE OR REPLACE VIEW recent_batch_history AS
SELECT 
    bph.id,
    bph.batch_uuid,
    bph.collection_id,
    bph.batch_number,
    bph.video_count,
    bph.individuals_created + bph.individuals_cached as total_individuals,
    bph.mvr_people_created + bph.mvr_people_cached as total_mvr_people,
    bph.cache_hit_rate,
    bph.processing_time_seconds,
    bph.throughput_videos_per_sec,
    bph.status,
    bph.is_partial_batch,
    bph.trigger_reason,
    bph.created_at
FROM batch_processing_history bph
ORDER BY bph.created_at DESC
LIMIT 100;

COMMENT ON VIEW recent_batch_history IS 'Most recent 100 batch processing history records with calculated totals';

-- Add comments for documentation
COMMENT ON TABLE batch_processing_history IS 'Audit log of all completed batches with performance metrics';
COMMENT ON COLUMN batch_processing_history.cache_hit_rate IS 'Percentage of individuals that were cached (0-100)';
COMMENT ON COLUMN batch_processing_history.throughput_videos_per_sec IS 'Videos processed per second';
COMMENT ON COLUMN batch_processing_history.is_partial_batch IS 'True if batch was triggered before reaching threshold';
COMMENT ON COLUMN batch_processing_history.trigger_reason IS 'What triggered batch: threshold, timeout, recording_stopped, manual';

-- Verify table creation
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'batch_processing_history'
    ) THEN
        RAISE NOTICE 'Table batch_processing_history created successfully';
    ELSE
        RAISE EXCEPTION 'Failed to create table batch_processing_history';
    END IF;
END $$;
