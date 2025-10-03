-- Phase 1 Missing Tables Creation
-- These are the base tables that Phase 1 needs to function

-- Create person_objects table
CREATE TABLE IF NOT EXISTS person_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID NOT NULL,
    source_identifier TEXT NOT NULL,
    source_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Phase 1 movement summary fields
    total_route_points INTEGER DEFAULT 0,
    movement_distance_pixels FLOAT DEFAULT 0.0,
    average_velocity FLOAT DEFAULT 0.0,
    time_in_frame_seconds FLOAT DEFAULT 0.0,
    average_distance_from_camera FLOAT,
    min_distance_from_camera FLOAT,
    max_distance_from_camera FLOAT
);

-- Create face_detections table
CREATE TABLE IF NOT EXISTS face_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_uuid UUID NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    frame_number INTEGER,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Phase 1 enhanced fields
    distance_from_camera FLOAT,
    face_area_pixels INTEGER,
    facial_embedding vector(512),  -- 512-dimensional vector for DeepFace Facenet512
    embedding_confidence FLOAT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_person_objects_session ON person_objects(session_uuid);
CREATE INDEX IF NOT EXISTS idx_person_objects_source ON person_objects(source_identifier);
CREATE INDEX IF NOT EXISTS idx_face_detections_session ON face_detections(session_uuid);
CREATE INDEX IF NOT EXISTS idx_face_detections_timestamp ON face_detections(timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_face_detections_frame ON face_detections(frame_number);

-- Vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_face_detections_embedding 
ON face_detections USING ivfflat (facial_embedding vector_cosine_ops) 
WITH (lists = 100);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Phase 1 missing tables created successfully!';
    RAISE NOTICE 'Tables ready: person_objects, face_detections';
    RAISE NOTICE 'Vector search enabled with pgvector';
END $$;