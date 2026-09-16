-- Add representative_faces / all_faces_route_data used by Vision person_objects queries.
-- Without these columns Enhanced Logic V2 retrieval fails with 500s.

ALTER TABLE person_objects
ADD COLUMN IF NOT EXISTS representative_faces JSONB DEFAULT '[]'::jsonb;

ALTER TABLE person_objects
ADD COLUMN IF NOT EXISTS all_faces_route_data JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_person_objects_representative_faces
ON person_objects USING GIN (representative_faces);

CREATE INDEX IF NOT EXISTS idx_person_objects_route_data
ON person_objects USING GIN (all_faces_route_data);
