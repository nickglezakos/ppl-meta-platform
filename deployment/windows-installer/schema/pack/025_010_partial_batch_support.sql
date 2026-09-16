-- Migration 010: Partial Batch Support Enhancement
-- Purpose: Ensure partial batch fields exist and add indexes for performance
-- Created: 2025-11-13
-- Phase: Phase 5 - Partial Batch Handling

-- This migration is idempotent - safe to run even if fields already exist

-- =============================================
-- ADD MISSING COLUMNS (IF NOT EXISTS)
-- =============================================

-- Add is_partial_batch column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_state' 
        AND column_name='is_partial_batch'
    ) THEN
        ALTER TABLE batch_processing_state
        ADD COLUMN is_partial_batch BOOLEAN DEFAULT FALSE;
        
        RAISE NOTICE 'Added is_partial_batch column';
    ELSE
        RAISE NOTICE 'Column is_partial_batch already exists';
    END IF;
END $$;

-- Add trigger_reason column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_state' 
        AND column_name='trigger_reason'
    ) THEN
        ALTER TABLE batch_processing_state
        ADD COLUMN trigger_reason VARCHAR(50);
        
        ALTER TABLE batch_processing_state
        ADD CONSTRAINT check_trigger_reason CHECK (
            trigger_reason IS NULL OR 
            trigger_reason IN ('threshold', 'timeout', 'recording_stopped', 'manual', 'batch_size_reached', 'recording_stopped', 'timeout_reached', 'manual_trigger', 'force_processing')
        );
        
        RAISE NOTICE 'Added trigger_reason column with constraint';
    ELSE
        RAISE NOTICE 'Column trigger_reason already exists';
    END IF;
END $$;

-- Add last_video_time column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_state' 
        AND column_name='last_video_time'
    ) THEN
        ALTER TABLE batch_processing_state
        ADD COLUMN last_video_time TIMESTAMP;
        
        RAISE NOTICE 'Added last_video_time column';
    ELSE
        RAISE NOTICE 'Column last_video_time already exists';
    END IF;
END $$;

-- Add timeout_at column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_state' 
        AND column_name='timeout_at'
    ) THEN
        ALTER TABLE batch_processing_state
        ADD COLUMN timeout_at TIMESTAMP;
        
        RAISE NOTICE 'Added timeout_at column';
    ELSE
        RAISE NOTICE 'Column timeout_at already exists';
    END IF;
END $$;

-- =============================================
-- ADD PARTIAL BATCH FIELDS TO HISTORY TABLE
-- =============================================

-- Add is_partial_batch to history if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_history' 
        AND column_name='is_partial_batch'
    ) THEN
        ALTER TABLE batch_processing_history
        ADD COLUMN is_partial_batch BOOLEAN DEFAULT FALSE;
        
        RAISE NOTICE 'Added is_partial_batch column to history';
    ELSE
        RAISE NOTICE 'Column is_partial_batch already exists in history';
    END IF;
END $$;

-- Add trigger_reason to history if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_history' 
        AND column_name='trigger_reason'
    ) THEN
        ALTER TABLE batch_processing_history
        ADD COLUMN trigger_reason VARCHAR(50);
        
        RAISE NOTICE 'Added trigger_reason column to history';
    ELSE
        RAISE NOTICE 'Column trigger_reason already exists in history';
    END IF;
END $$;

-- =============================================
-- CREATE INDEXES FOR PERFORMANCE
-- =============================================

-- Index for timeout monitoring queries
CREATE INDEX IF NOT EXISTS idx_batch_timeout 
ON batch_processing_state(collection_id, timeout_at)
WHERE status = 'accumulating' AND timeout_at IS NOT NULL;

-- Index for partial batch queries
CREATE INDEX IF NOT EXISTS idx_batch_partial 
ON batch_processing_state(collection_id, is_partial_batch, created_at DESC)
WHERE is_partial_batch = TRUE;

-- Index for incomplete batch queries
CREATE INDEX IF NOT EXISTS idx_batch_incomplete 
ON batch_processing_state(collection_id, status, created_at DESC)
WHERE status = 'incomplete';

-- Index for trigger reason analysis
CREATE INDEX IF NOT EXISTS idx_batch_trigger_reason 
ON batch_processing_state(trigger_reason, created_at DESC)
WHERE trigger_reason IS NOT NULL;

-- Index for history partial batch queries
CREATE INDEX IF NOT EXISTS idx_history_partial 
ON batch_processing_history(collection_id, is_partial_batch, created_at DESC)
WHERE is_partial_batch = TRUE;

-- =============================================
-- ADD PARTIAL BATCH CONFIG FIELDS
-- =============================================

-- Add partial_batch_min_videos if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_config' 
        AND column_name='partial_batch_min_videos'
    ) THEN
        ALTER TABLE batch_processing_config
        ADD COLUMN partial_batch_min_videos INTEGER NOT NULL DEFAULT 2;
        
        ALTER TABLE batch_processing_config
        ADD CONSTRAINT check_partial_min_videos CHECK (
            partial_batch_min_videos >= 1 AND 
            partial_batch_min_videos < batch_size_threshold
        );
        
        RAISE NOTICE 'Added partial_batch_min_videos column';
    ELSE
        RAISE NOTICE 'Column partial_batch_min_videos already exists';
    END IF;
END $$;

-- Add partial_batch_timeout_minutes if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='batch_processing_config' 
        AND column_name='partial_batch_timeout_minutes'
    ) THEN
        ALTER TABLE batch_processing_config
        ADD COLUMN partial_batch_timeout_minutes INTEGER NOT NULL DEFAULT 10;
        
        ALTER TABLE batch_processing_config
        ADD CONSTRAINT check_partial_timeout CHECK (
            partial_batch_timeout_minutes >= 1 AND 
            partial_batch_timeout_minutes <= 1440
        );
        
        RAISE NOTICE 'Added partial_batch_timeout_minutes column';
    ELSE
        RAISE NOTICE 'Column partial_batch_timeout_minutes already exists';
    END IF;
END $$;

-- =============================================
-- UPDATE ARCHIVE FUNCTION TO INCLUDE NEW FIELDS
-- =============================================

-- Drop and recreate archive function with partial batch fields
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
        -- Calculate cache hit rate
        CASE 
            WHEN (bps.individuals_created + bps.individuals_cached) > 0 THEN
                (bps.individuals_cached::FLOAT / 
                 (bps.individuals_created + bps.individuals_cached)::FLOAT) * 100
            ELSE NULL
        END as cache_hit_rate,
        -- Calculate throughput
        CASE 
            WHEN bps.processing_time_seconds > 0 THEN
                bps.video_count::FLOAT / bps.processing_time_seconds
            ELSE NULL
        END as throughput_videos_per_sec,
        bps.first_video_start_time as batch_start_time,
        bps.last_video_end_time as batch_end_time,
        bps.triggered_at,
        bps.completed_at,
        bps.session_uuid,
        bps.status,
        bps.is_partial_batch,
        bps.trigger_reason,
        bps.error_message
    FROM batch_processing_state bps
    WHERE bps.batch_uuid = p_batch_uuid
    ON CONFLICT (batch_uuid) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- DATA MIGRATION (BACKFILL)
-- =============================================

-- Backfill is_partial_batch based on video_count and batch_size_threshold
UPDATE batch_processing_state
SET is_partial_batch = TRUE
WHERE status IN ('completed', 'failed')
  AND video_count < batch_size_threshold
  AND is_partial_batch = FALSE;

-- Backfill trigger_reason for threshold batches
UPDATE batch_processing_state
SET trigger_reason = 'threshold'
WHERE status IN ('completed', 'failed')
  AND video_count >= batch_size_threshold
  AND trigger_reason IS NULL;

-- Backfill trigger_reason for partial batches (assume timeout if not specified)
UPDATE batch_processing_state
SET trigger_reason = 'timeout_reached'
WHERE status IN ('completed', 'failed')
  AND is_partial_batch = TRUE
  AND trigger_reason IS NULL;

-- =============================================
-- VERIFICATION QUERIES
-- =============================================

-- Count batches by type
DO $$
DECLARE
    v_full_batches INTEGER;
    v_partial_batches INTEGER;
    v_incomplete_batches INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_full_batches
    FROM batch_processing_state
    WHERE is_partial_batch = FALSE;
    
    SELECT COUNT(*) INTO v_partial_batches
    FROM batch_processing_state
    WHERE is_partial_batch = TRUE;
    
    SELECT COUNT(*) INTO v_incomplete_batches
    FROM batch_processing_state
    WHERE status = 'incomplete';
    
    RAISE NOTICE 'Migration 010 Complete:';
    RAISE NOTICE '  Full batches: %', v_full_batches;
    RAISE NOTICE '  Partial batches: %', v_partial_batches;
    RAISE NOTICE '  Incomplete batches: %', v_incomplete_batches;
END $$;

-- Summary
SELECT 
    'Migration 010: Partial Batch Support Enhancement' as migration,
    'Complete' as status,
    NOW() as completed_at;
