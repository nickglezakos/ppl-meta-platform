-- Minimal MVR appearance tables required by video preview count-by-videos.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS individuals (
    individual_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_id VARCHAR(50) UNIQUE NOT NULL,
    confidence_score FLOAT NOT NULL DEFAULT 0.5 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    spatial_signature JSONB,
    temporal_signature JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_appearances INTEGER DEFAULT 0,
    total_videos INTEGER DEFAULT 0,
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS individual_video_appearances (
    appearance_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    individual_uuid UUID NOT NULL REFERENCES individuals(individual_uuid) ON DELETE CASCADE,
    video_uuid UUID NOT NULL,
    person_object_uuid UUID NOT NULL,
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + interval '1 second'),
    entry_bbox FLOAT[4],
    exit_bbox FLOAT[4],
    average_bbox FLOAT[4],
    bbox_trajectory JSONB,
    confidence FLOAT NOT NULL DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    quality_score FLOAT,
    face_quality FLOAT,
    processing_method VARCHAR(50),
    source_session_uuid UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    representative_faces JSONB,
    CONSTRAINT unique_person_object UNIQUE (individual_uuid, video_uuid, person_object_uuid)
);
