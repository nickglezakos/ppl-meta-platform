-- Align camera_settings with ORM expected by cameras service (2.25.x).
BEGIN;

ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS tolerance_percent INTEGER DEFAULT 20 NOT NULL;
ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS auto_recording BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS recording_duration INTEGER DEFAULT 30 NOT NULL;
ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS notification_methods JSONB DEFAULT '["email"]'::jsonb NOT NULL;
ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS store_faces_in_memory BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE camera_settings
  ADD COLUMN IF NOT EXISTS persist_after_recording BOOLEAN DEFAULT TRUE NOT NULL;

UPDATE camera_settings
SET detection_methods = COALESCE(detection_methods, '["two_stage"]'::json),
    processing_options = COALESCE(processing_options, '{}'::json),
    auto_face_detection = COALESCE(auto_face_detection, FALSE);

-- Demo: enable face + body for known Tapo camera so instant detection actually runs.
UPDATE cameras
SET auto_face_detection = TRUE,
    processing_options = (
      COALESCE(processing_options::jsonb, '{}'::jsonb) ||
      '{"auto_body_detection": true, "auto_object_detection": false, "auto_vehicle_detection": false}'::jsonb
    )::json
WHERE device_id = '31652fc6-a2f1-49bb-94eb-7dbb89bbb61c';

COMMIT;
