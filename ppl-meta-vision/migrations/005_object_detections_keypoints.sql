-- Add pose keypoints to object_detections
ALTER TABLE object_detections ADD COLUMN IF NOT EXISTS keypoints_json TEXT;
ALTER TABLE object_detections ADD COLUMN IF NOT EXISTS keypoint_score REAL;
CREATE INDEX IF NOT EXISTS idx_object_detections_session_frame
    ON object_detections (session_uuid, frame_number);
