-- Migration: Add representative_faces and all_faces_route_data to person_objects
-- Purpose: Store multiple quality faces and complete face routes for overlays
-- Date: 2026-01-24
-- 
-- This enables:
-- 1. Top 3-5 representative faces for MVR/person-object quality display
-- 2. Complete face detection routes (all 72 faces) for video overlay visualization
-- 3. Preserves existing best_face_id for backward compatibility

-- Add representative_faces column (top 3-5 quality ranked faces per person)
ALTER TABLE person_objects 
ADD COLUMN IF NOT EXISTS representative_faces JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN person_objects.representative_faces IS 
'Top 3-5 highest quality faces for this person, ranked by quality score. 
Format: [{"face_id": "uuid", "quality_score": 85.3, "rank": 1, "bbox": [x1,y1,x2,y2], "frame_number": 530}, ...]
Used for MVR person images and quality display.';

-- Add all_faces_route_data column (complete face detections for overlay routes)
ALTER TABLE person_objects
ADD COLUMN IF NOT EXISTS all_faces_route_data JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN person_objects.all_faces_route_data IS 
'Complete face detection route data for video overlay visualization. Contains ALL detected faces for this person across all frames.
Format: [{"face_id": "uuid", "frame_number": 100, "bbox": [x1,y1,x2,y2], "position": {"x": 0.5, "y": 0.3}, "confidence": 0.95}, ...]
Used for drawing face rectangles synchronized with video playback.';

-- Create indexes for JSONB queries
CREATE INDEX IF NOT EXISTS idx_person_objects_representative_faces 
ON person_objects USING GIN (representative_faces);

CREATE INDEX IF NOT EXISTS idx_person_objects_route_data 
ON person_objects USING GIN (all_faces_route_data);

-- Verify migration
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'person_objects' 
        AND column_name = 'representative_faces'
    ) THEN
        RAISE NOTICE '✅ Migration successful: representative_faces column added';
    ELSE
        RAISE EXCEPTION '❌ Migration failed: representative_faces column not found';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'person_objects' 
        AND column_name = 'all_faces_route_data'
    ) THEN
        RAISE NOTICE '✅ Migration successful: all_faces_route_data column added';
    ELSE
        RAISE EXCEPTION '❌ Migration failed: all_faces_route_data column not found';
    END IF;
END $$;
