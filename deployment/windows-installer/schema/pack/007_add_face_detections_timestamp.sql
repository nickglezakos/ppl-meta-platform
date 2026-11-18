-- Ensure face_detections.timestamp exists for route velocity / Vision route persist.
-- Vision writes timestamp = frame_number / fps; route builders SELECT this column.
-- Idempotent for greenfield and labs where the app table already exists.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'face_detections'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'face_detections'
      AND column_name = 'timestamp'
  ) THEN
    ALTER TABLE face_detections ADD COLUMN timestamp REAL;
    COMMENT ON COLUMN face_detections.timestamp IS
      'Seconds from media start (typically frame_number / fps)';
  END IF;
END $$;
