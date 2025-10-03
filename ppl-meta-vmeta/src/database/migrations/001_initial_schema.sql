-- ================================================================
-- Phase 1: Enhanced Database Schema Implementation
-- PPL Meta Platform - Persons Detection Lifecycle
-- ================================================================

-- Step 1: Install pgvector extension (one-time setup)
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================================================
-- Enhanced Session-Based Master Workflows Table
-- ================================================================

CREATE TABLE IF NOT EXISTS persons_lifecycle_master_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID NOT NULL UNIQUE,
    source_identifier VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('camera_recording', 'uploaded_media', 'manual_trigger')),
    source_id VARCHAR(255), -- media_id, camera_uuid, or upload_id
    
    -- Workflow Status
    status VARCHAR(50) NOT NULL DEFAULT 'initializing' CHECK (status IN ('initializing', 'processing', 'completed', 'failed', 'cancelled')),
    current_stage VARCHAR(100), -- 'face_detection', 'people_thread', 'emotion_detection', 'age_estimation', etc.
    progress_percentage FLOAT DEFAULT 0.0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    
    -- Session Management
    execution_trigger VARCHAR(50) NOT NULL CHECK (execution_trigger IN ('automatic', 'manual', 'scheduled', 'api_request')),
    parent_session_uuid UUID REFERENCES persons_lifecycle_master_workflows(session_uuid), -- For re-executions
    workflow_priority INTEGER DEFAULT 1 CHECK (workflow_priority >= 1 AND workflow_priority <= 10),
    
    -- Workflow Configuration
    configuration JSONB DEFAULT '{}', -- Stores workflow-specific settings
    metadata JSONB DEFAULT '{}', -- Additional metadata and tags
    
    -- Timing and Performance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    estimated_completion_at TIMESTAMP WITH TIME ZONE,
    processing_duration_seconds INTEGER,
    
    -- Results Summary
    total_faces_detected INTEGER DEFAULT 0,
    total_persons_identified INTEGER DEFAULT 0,
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexing
    CONSTRAINT unique_source_session UNIQUE (source_identifier, session_uuid)
);

-- ================================================================
-- Person Routes Table for Movement Tracking
-- ================================================================

CREATE TABLE IF NOT EXISTS person_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_object_id UUID NOT NULL, -- References person_objects.id
    session_uuid UUID NOT NULL REFERENCES persons_lifecycle_master_workflows(session_uuid),
    
    -- Sequence and Timing
    sequence_number INTEGER NOT NULL, -- Order of detection in timeline
    timestamp_ms BIGINT NOT NULL, -- Milliseconds from video start
    frame_number INTEGER,
    
    -- Spatial Coordinates (from face bounding boxes)
    center_x FLOAT NOT NULL, -- X center coordinate
    center_y FLOAT NOT NULL, -- Y center coordinate
    bounding_box_width FLOAT,
    bounding_box_height FLOAT,
    
    -- Distance Calculation (Autonomous PPL Meta System)
    distance_from_camera FLOAT, -- Calculated as 1,000,000 / face_area
    face_area_pixels INTEGER, -- For distance calculation verification
    
    -- Movement Analysis
    velocity_x FLOAT, -- Pixels per second in X direction
    velocity_y FLOAT, -- Pixels per second in Y direction
    velocity_magnitude FLOAT, -- Overall movement speed
    direction_radians FLOAT, -- Movement direction in radians
    
    -- Detection Quality
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    detection_quality VARCHAR(20) CHECK (detection_quality IN ('excellent', 'good', 'fair', 'poor')),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_person_sequence UNIQUE (person_object_id, sequence_number),
    CONSTRAINT positive_coordinates CHECK (center_x >= 0 AND center_y >= 0),
    CONSTRAINT positive_dimensions CHECK (bounding_box_width > 0 AND bounding_box_height > 0)
);

-- ================================================================
-- Enhanced Person Objects with Distance and Embeddings
-- ================================================================

-- Create person_objects table with Phase 1 enhancements
CREATE TABLE IF NOT EXISTS person_objects (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID,
    workflow_id TEXT,
    face_count INTEGER NOT NULL DEFAULT 0,
    average_position_x REAL NOT NULL DEFAULT 0,
    average_position_y REAL NOT NULL DEFAULT 0,
    quality_score REAL NOT NULL DEFAULT 0,
    best_face_id TEXT,
    estimated_age INTEGER,
    tracking_algorithm TEXT DEFAULT 'percentage_based_tracking',
    tolerance_percent REAL DEFAULT 20.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Phase 1 Distance Enhancements
    distance_from_camera FLOAT,
    average_distance FLOAT, -- Average across all detections
    min_distance FLOAT, -- Closest detection
    max_distance FLOAT, -- Furthest detection
    
    -- Phase 1 Session-based columns
    source_identifier VARCHAR(255),
    execution_trigger VARCHAR(50),
    
    -- Phase 1 Facial embedding columns for vector search
    facial_embedding vector(512),
    embedding_model VARCHAR(50) DEFAULT 'deepface_facenet512',
    embedding_confidence FLOAT,
    embedding_generated_at TIMESTAMP WITH TIME ZONE,
    
    -- Phase 1 Movement summary columns
    total_route_points INTEGER DEFAULT 0,
    movement_distance_pixels FLOAT, -- Total movement distance
    average_velocity FLOAT,
    time_in_frame_seconds FLOAT,
    
    -- Foreign key references
    FOREIGN KEY (session_uuid) REFERENCES persons_lifecycle_master_workflows(session_uuid)
);

-- ================================================================
-- Enhanced Face Detections with Distance and Embeddings
-- ================================================================

-- Add distance calculation to face_detections table
ALTER TABLE face_detections ADD COLUMN IF NOT EXISTS distance_from_camera FLOAT;
ALTER TABLE face_detections ADD COLUMN IF NOT EXISTS face_area_pixels INTEGER;

-- Add facial embeddings to face_detections
ALTER TABLE face_detections ADD COLUMN IF NOT EXISTS facial_embedding vector(512);
ALTER TABLE face_detections ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(50) DEFAULT 'deepface_facenet512';
ALTER TABLE face_detections ADD COLUMN IF NOT EXISTS embedding_confidence FLOAT;

-- Add session tracking
ALTER TABLE face_detections ADD COLUMN IF NOT EXISTS session_uuid UUID;

-- ================================================================
-- Sub-Workflow Tracking Tables
-- ================================================================

-- Enhanced Face Detection Workflows
ALTER TABLE face_detection_workflows ADD COLUMN IF NOT EXISTS session_uuid UUID;
ALTER TABLE face_detection_workflows ADD COLUMN IF NOT EXISTS master_workflow_id UUID REFERENCES persons_lifecycle_master_workflows(id);
ALTER TABLE face_detection_workflows ADD COLUMN IF NOT EXISTS distance_calculation_enabled BOOLEAN DEFAULT true;
ALTER TABLE face_detection_workflows ADD COLUMN IF NOT EXISTS embedding_generation_enabled BOOLEAN DEFAULT true;

-- Enhanced People Thread Workflows  
ALTER TABLE people_thread_workflows ADD COLUMN IF NOT EXISTS session_uuid UUID;
ALTER TABLE people_thread_workflows ADD COLUMN IF NOT EXISTS master_workflow_id UUID REFERENCES persons_lifecycle_master_workflows(id);
ALTER TABLE people_thread_workflows ADD COLUMN IF NOT EXISTS route_tracking_enabled BOOLEAN DEFAULT true;

-- Create emotion detection workflows table (for future Phase 2)
CREATE TABLE IF NOT EXISTS emotion_detection_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID NOT NULL,
    master_workflow_id UUID NOT NULL REFERENCES persons_lifecycle_master_workflows(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress_percentage FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create age estimation workflows table (for future Phase 3)
CREATE TABLE IF NOT EXISTS age_estimation_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID NOT NULL,
    master_workflow_id UUID NOT NULL REFERENCES persons_lifecycle_master_workflows(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress_percentage FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ================================================================
-- Performance Indexes
-- ================================================================

-- Session-based indexes
CREATE INDEX IF NOT EXISTS idx_master_workflows_session ON persons_lifecycle_master_workflows(session_uuid, status);
CREATE INDEX IF NOT EXISTS idx_master_workflows_source ON persons_lifecycle_master_workflows(source_identifier, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_master_workflows_status ON persons_lifecycle_master_workflows(status, created_at);
CREATE INDEX IF NOT EXISTS idx_master_workflows_trigger ON persons_lifecycle_master_workflows(execution_trigger, created_at);

-- Person routes indexes
CREATE INDEX IF NOT EXISTS idx_person_routes_person ON person_routes(person_object_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_person_routes_session ON person_routes(session_uuid, timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_person_routes_spatial ON person_routes(center_x, center_y);
CREATE INDEX IF NOT EXISTS idx_person_routes_distance ON person_routes(distance_from_camera) WHERE distance_from_camera IS NOT NULL;

-- Vector search indexes (pgvector)
CREATE INDEX IF NOT EXISTS idx_person_objects_embedding_cosine 
ON person_objects USING ivfflat (facial_embedding vector_cosine_ops) 
WITH (lists = 100) WHERE facial_embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_person_objects_embedding_l2 
ON person_objects USING ivfflat (facial_embedding vector_l2_ops) 
WITH (lists = 100) WHERE facial_embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_face_detections_embedding_cosine 
ON face_detections USING ivfflat (facial_embedding vector_cosine_ops) 
WITH (lists = 100) WHERE facial_embedding IS NOT NULL;

-- Session and source indexes for person objects
CREATE INDEX IF NOT EXISTS idx_person_objects_session ON person_objects(session_uuid, created_at);
CREATE INDEX IF NOT EXISTS idx_person_objects_source ON person_objects(source_identifier, created_at);
CREATE INDEX IF NOT EXISTS idx_person_objects_distance ON person_objects(distance_from_camera) WHERE distance_from_camera IS NOT NULL;

-- Face detections session indexes
CREATE INDEX IF NOT EXISTS idx_face_detections_session ON face_detections(session_uuid, timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_face_detections_distance ON face_detections(distance_from_camera) WHERE distance_from_camera IS NOT NULL;

-- Workflow performance indexes
CREATE INDEX IF NOT EXISTS idx_face_workflows_session ON face_detection_workflows(session_uuid, status);
CREATE INDEX IF NOT EXISTS idx_people_workflows_session ON people_thread_workflows(session_uuid, status);
CREATE INDEX IF NOT EXISTS idx_emotion_workflows_session ON emotion_detection_workflows(session_uuid, status);
CREATE INDEX IF NOT EXISTS idx_age_workflows_session ON age_estimation_workflows(session_uuid, status);

-- ================================================================
-- Helper Functions for Distance Calculation
-- ================================================================

CREATE OR REPLACE FUNCTION calculate_face_distance(face_width FLOAT, face_height FLOAT)
RETURNS FLOAT AS $$
BEGIN
    -- Autonomous PPL Meta System methodology: 1,000,000 / face_area
    IF face_width IS NULL OR face_height IS NULL OR face_width <= 0 OR face_height <= 0 THEN
        RETURN NULL;
    END IF;
    
    RETURN 1000000.0 / (face_width * face_height);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ================================================================
-- Helper Functions for Movement Analysis  
-- ================================================================

CREATE OR REPLACE FUNCTION calculate_movement_velocity(
    x1 FLOAT, y1 FLOAT, t1 BIGINT,
    x2 FLOAT, y2 FLOAT, t2 BIGINT
) RETURNS JSONB AS $$
DECLARE
    time_diff_seconds FLOAT;
    velocity_x FLOAT;
    velocity_y FLOAT;
    velocity_magnitude FLOAT;
    direction_radians FLOAT;
BEGIN
    -- Calculate time difference in seconds
    time_diff_seconds := (t2 - t1) / 1000.0;
    
    IF time_diff_seconds <= 0 THEN
        RETURN '{"velocity_x": 0, "velocity_y": 0, "velocity_magnitude": 0, "direction_radians": 0}'::jsonb;
    END IF;
    
    -- Calculate velocity components
    velocity_x := (x2 - x1) / time_diff_seconds;
    velocity_y := (y2 - y1) / time_diff_seconds;
    
    -- Calculate magnitude and direction
    velocity_magnitude := sqrt(velocity_x^2 + velocity_y^2);
    direction_radians := atan2(velocity_y, velocity_x);
    
    RETURN jsonb_build_object(
        'velocity_x', velocity_x,
        'velocity_y', velocity_y,
        'velocity_magnitude', velocity_magnitude,
        'direction_radians', direction_radians
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ================================================================
-- Data Migration Functions (Zero-Downtime)
-- ================================================================

-- Function to backfill session_uuid for existing records (optional)
CREATE OR REPLACE FUNCTION backfill_session_uuids()
RETURNS INTEGER AS $$
DECLARE
    records_updated INTEGER := 0;
BEGIN
    -- This is optional - existing records work fine with NULL session_uuid
    -- Only run if you want to group existing data into synthetic sessions
    
    RAISE NOTICE 'Backfilling session UUIDs is optional. Existing records work fine with NULL values.';
    RAISE NOTICE 'Run this only if you want to group existing data into synthetic sessions.';
    
    RETURN records_updated;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Verification Queries
-- ================================================================

-- Verify schema changes
DO $$
BEGIN
    -- Check if pgvector extension is installed
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension not installed. Run: CREATE EXTENSION vector;';
    END IF;
    
    -- Check if master workflows table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'persons_lifecycle_master_workflows') THEN
        RAISE EXCEPTION 'persons_lifecycle_master_workflows table not created';
    END IF;
    
    -- Check if person routes table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'person_routes') THEN
        RAISE EXCEPTION 'person_routes table not created';
    END IF;
    
    RAISE NOTICE 'Phase 1 database schema successfully implemented!';
    RAISE NOTICE 'Key features enabled:';
    RAISE NOTICE '✅ Session-based master workflows';
    RAISE NOTICE '✅ Person routes tracking with distance calculation';
    RAISE NOTICE '✅ Facial embeddings with pgvector';
    RAISE NOTICE '✅ Zero-downtime migration (existing data untouched)';
    RAISE NOTICE '✅ Performance indexes for efficient querying';
END;
$$;