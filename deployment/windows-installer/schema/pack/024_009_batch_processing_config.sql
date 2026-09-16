-- Migration 009: Batch Processing Configuration Table
-- Purpose: Store batch processing configuration per collection with global defaults
-- Created: 2025-11-13

-- Create batch_processing_config table
CREATE TABLE IF NOT EXISTS batch_processing_config (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Collection identifier (NULL for global config)
    collection_id VARCHAR(255) UNIQUE,
    
    -- Batch size configuration
    batch_size_threshold INTEGER NOT NULL DEFAULT 5,
    
    -- Partial batch handling
    partial_batch_min_videos INTEGER NOT NULL DEFAULT 2,
    partial_batch_timeout_minutes INTEGER NOT NULL DEFAULT 10,
    partial_batch_max_wait_hours INTEGER NOT NULL DEFAULT 24,
    
    -- Recording stop event configuration
    enable_recording_stop_event BOOLEAN NOT NULL DEFAULT TRUE,
    recording_stop_trigger_delay_seconds INTEGER NOT NULL DEFAULT 2,
    
    -- Timeout fallback configuration
    enable_timeout_fallback BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Concurrency limits
    max_concurrent_batches INTEGER NOT NULL DEFAULT 3,
    worker_pool_size INTEGER NOT NULL DEFAULT 3,
    
    -- Resource limits
    max_batch_memory_gb INTEGER NOT NULL DEFAULT 2,
    max_videos_per_session INTEGER NOT NULL DEFAULT 10,
    max_processing_time_seconds INTEGER NOT NULL DEFAULT 300,
    
    -- Event configuration
    enable_event_triggering BOOLEAN NOT NULL DEFAULT TRUE,
    enable_polling_fallback BOOLEAN NOT NULL DEFAULT TRUE,
    polling_interval_seconds INTEGER NOT NULL DEFAULT 30,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_batch_size_threshold CHECK (
        batch_size_threshold >= 2 AND batch_size_threshold <= 50
    ),
    CONSTRAINT check_partial_batch_min CHECK (
        partial_batch_min_videos >= 1 AND partial_batch_min_videos < batch_size_threshold
    ),
    CONSTRAINT check_timeout CHECK (
        partial_batch_timeout_minutes > 0 AND partial_batch_timeout_minutes <= 1440
    ),
    CONSTRAINT check_max_wait CHECK (
        partial_batch_max_wait_hours > 0 AND partial_batch_max_wait_hours <= 168
    ),
    CONSTRAINT check_concurrent_batches CHECK (
        max_concurrent_batches > 0 AND max_concurrent_batches <= 10
    ),
    CONSTRAINT check_worker_pool CHECK (
        worker_pool_size > 0 AND worker_pool_size <= 10
    )
);

-- Create index for quick global config lookup
CREATE INDEX idx_batch_processing_config_global 
    ON batch_processing_config(id)
    WHERE collection_id IS NULL;

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_batch_processing_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
CREATE TRIGGER trigger_batch_processing_config_updated_at
    BEFORE UPDATE ON batch_processing_config
    FOR EACH ROW
    EXECUTE FUNCTION update_batch_processing_config_updated_at();

-- Create function to get effective config for collection
CREATE OR REPLACE FUNCTION get_batch_processing_config(p_collection_id VARCHAR(255))
RETURNS batch_processing_config AS $$
DECLARE
    v_config batch_processing_config;
BEGIN
    -- Try to get collection-specific config first
    SELECT * INTO v_config
    FROM batch_processing_config
    WHERE collection_id = p_collection_id;
    
    -- If not found, get global config
    IF NOT FOUND THEN
        SELECT * INTO v_config
        FROM batch_processing_config
        WHERE collection_id IS NULL;
    END IF;
    
    RETURN v_config;
END;
$$ LANGUAGE plpgsql;

-- Create function to update batch size
CREATE OR REPLACE FUNCTION update_batch_size(
    p_collection_id VARCHAR(255),
    p_batch_size INTEGER
)
RETURNS VOID AS $$
BEGIN
    -- Validate batch size
    IF p_batch_size < 2 OR p_batch_size > 50 THEN
        RAISE EXCEPTION 'Batch size must be between 2 and 50, got %', p_batch_size;
    END IF;
    
    -- Update or insert collection-specific config
    IF p_collection_id IS NOT NULL THEN
        INSERT INTO batch_processing_config (
            collection_id,
            batch_size_threshold
        ) VALUES (
            p_collection_id,
            p_batch_size
        )
        ON CONFLICT (collection_id) 
        DO UPDATE SET 
            batch_size_threshold = p_batch_size,
            updated_at = NOW();
    ELSE
        -- Update global config
        UPDATE batch_processing_config
        SET batch_size_threshold = p_batch_size,
            updated_at = NOW()
        WHERE collection_id IS NULL;
    END IF;
    
    -- Update active accumulating batches with new threshold
    UPDATE batch_processing_state
    SET batch_size_threshold = p_batch_size
    WHERE collection_id = COALESCE(p_collection_id, collection_id)
      AND status = 'accumulating';
END;
$$ LANGUAGE plpgsql;

-- Insert global default configuration
INSERT INTO batch_processing_config (
    collection_id,
    batch_size_threshold,
    partial_batch_min_videos,
    partial_batch_timeout_minutes,
    partial_batch_max_wait_hours,
    enable_recording_stop_event,
    recording_stop_trigger_delay_seconds,
    enable_timeout_fallback,
    max_concurrent_batches,
    worker_pool_size,
    max_batch_memory_gb,
    max_videos_per_session,
    max_processing_time_seconds,
    enable_event_triggering,
    enable_polling_fallback,
    polling_interval_seconds
) VALUES (
    NULL,  -- Global config
    5,     -- batch_size_threshold
    2,     -- partial_batch_min_videos
    10,    -- partial_batch_timeout_minutes
    24,    -- partial_batch_max_wait_hours
    TRUE,  -- enable_recording_stop_event
    2,     -- recording_stop_trigger_delay_seconds
    TRUE,  -- enable_timeout_fallback
    3,     -- max_concurrent_batches
    3,     -- worker_pool_size
    2,     -- max_batch_memory_gb
    10,    -- max_videos_per_session
    300,   -- max_processing_time_seconds (5 minutes)
    TRUE,  -- enable_event_triggering
    TRUE,  -- enable_polling_fallback
    30     -- polling_interval_seconds
) ON CONFLICT (collection_id) DO NOTHING;

-- Add comments for documentation
COMMENT ON TABLE batch_processing_config IS 'Configuration for batch processing per collection with global defaults';
COMMENT ON COLUMN batch_processing_config.collection_id IS 'Camera collection ID, NULL for global default config';
COMMENT ON COLUMN batch_processing_config.batch_size_threshold IS 'Number of videos that trigger batch processing (2-50)';
COMMENT ON COLUMN batch_processing_config.partial_batch_min_videos IS 'Minimum videos required to process partial batch';
COMMENT ON COLUMN batch_processing_config.partial_batch_timeout_minutes IS 'Minutes to wait before triggering partial batch timeout';
COMMENT ON COLUMN batch_processing_config.enable_recording_stop_event IS 'Use recording stop event as primary trigger for partial batches';
COMMENT ON COLUMN batch_processing_config.enable_timeout_fallback IS 'Use timeout as fallback trigger if event fails';
COMMENT ON COLUMN batch_processing_config.max_concurrent_batches IS 'Maximum number of batches processing concurrently';
COMMENT ON COLUMN batch_processing_config.worker_pool_size IS 'Number of dedicated worker processes';

-- Create view for config summary
CREATE OR REPLACE VIEW batch_processing_config_summary AS
SELECT 
    COALESCE(bpc.collection_id, 'GLOBAL') as config_scope,
    bpc.batch_size_threshold,
    bpc.partial_batch_min_videos,
    bpc.partial_batch_timeout_minutes,
    bpc.enable_recording_stop_event,
    bpc.enable_timeout_fallback,
    bpc.max_concurrent_batches,
    bpc.updated_at
FROM batch_processing_config bpc
ORDER BY 
    CASE WHEN bpc.collection_id IS NULL THEN 0 ELSE 1 END,
    bpc.collection_id;

COMMENT ON VIEW batch_processing_config_summary IS 'Summary of all batch processing configurations (global and per-collection)';

-- Verify table creation and default config
DO $$
DECLARE
    v_config_count INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'batch_processing_config'
    ) THEN
        RAISE EXCEPTION 'Failed to create table batch_processing_config';
    END IF;
    
    SELECT COUNT(*) INTO v_config_count
    FROM batch_processing_config
    WHERE collection_id IS NULL;
    
    IF v_config_count = 0 THEN
        RAISE EXCEPTION 'Failed to insert global default config';
    END IF;
    
    RAISE NOTICE 'Table batch_processing_config created successfully with global default config';
END $$;
