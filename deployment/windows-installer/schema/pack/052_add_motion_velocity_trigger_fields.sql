-- Pack Media trigger DDL previously only in Alembic:
-- body_posture → velocity → left_object → vehicle_plate → motion
-- Idempotent for Stage 3 schema pack / clean installs.

-- Body posture
ALTER TABLE triggers
  ADD COLUMN IF NOT EXISTS body_posture_target VARCHAR(32) DEFAULT 'horizontal',
  ADD COLUMN IF NOT EXISTS body_posture_window_size INTEGER DEFAULT 4,
  ADD COLUMN IF NOT EXISTS body_posture_min_matches INTEGER DEFAULT 3,
  ADD COLUMN IF NOT EXISTS body_posture_min_confidence DOUBLE PRECISION DEFAULT 0.5,
  ADD COLUMN IF NOT EXISTS body_posture_iou_threshold DOUBLE PRECISION DEFAULT 0.3;

-- Legacy velocity (kept for fallback when motion_conditions empty)
ALTER TABLE triggers
  ADD COLUMN IF NOT EXISTS velocity_scope VARCHAR(16) DEFAULT 'crowd',
  ADD COLUMN IF NOT EXISTS velocity_band VARCHAR(32) DEFAULT 'walking';

-- Left object
ALTER TABLE triggers
  ADD COLUMN IF NOT EXISTS left_object_class_allowlist TEXT,
  ADD COLUMN IF NOT EXISTS left_object_roi TEXT,
  ADD COLUMN IF NOT EXISTS left_object_t_stable_seconds INTEGER DEFAULT 60,
  ADD COLUMN IF NOT EXISTS left_object_t_abandon_seconds INTEGER DEFAULT 30,
  ADD COLUMN IF NOT EXISTS left_object_min_box_area_px INTEGER DEFAULT 400,
  ADD COLUMN IF NOT EXISTS left_object_require_person_left BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS left_object_proximity_px DOUBLE PRECISION DEFAULT 120,
  ADD COLUMN IF NOT EXISTS left_object_iou_threshold DOUBLE PRECISION DEFAULT 0.3;

-- Vehicle / plate
ALTER TABLE triggers
  ADD COLUMN IF NOT EXISTS vehicle_class_allowlist TEXT,
  ADD COLUMN IF NOT EXISTS vehicle_roi TEXT,
  ADD COLUMN IF NOT EXISTS vehicle_t_stable_seconds INTEGER DEFAULT 15,
  ADD COLUMN IF NOT EXISTS vehicle_min_box_area_px INTEGER DEFAULT 800,
  ADD COLUMN IF NOT EXISTS vehicle_plate_ocr_enabled BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS vehicle_plate_ocr_every_n_cycles INTEGER DEFAULT 2,
  ADD COLUMN IF NOT EXISTS vehicle_iou_threshold DOUBLE PRECISION DEFAULT 0.3;

-- Motion (new path; worker falls back to velocity_band when motion_conditions empty)
ALTER TABLE triggers
  ADD COLUMN IF NOT EXISTS motion_scope VARCHAR(16) DEFAULT 'crowd',
  ADD COLUMN IF NOT EXISTS motion_conditions TEXT,
  ADD COLUMN IF NOT EXISTS motion_condition_logic VARCHAR(8) DEFAULT 'and',
  ADD COLUMN IF NOT EXISTS motion_roi TEXT;

-- Backfill motion_scope from legacy velocity_scope
UPDATE triggers
SET motion_scope = COALESCE(motion_scope, velocity_scope, 'crowd')
WHERE trigger_mode IN ('velocity', 'motion')
   OR velocity_scope IS NOT NULL;

-- Backfill motion_conditions from velocity_band for legacy velocity rows
UPDATE triggers
SET motion_conditions = COALESCE(
      motion_conditions,
      json_build_array(
        json_build_object(
          'field', 'speed_band',
          'operator', 'gte',
          'value', lower(COALESCE(NULLIF(BTRIM(velocity_band), ''), 'walking'))
        )
      )::text
    ),
    motion_condition_logic = COALESCE(motion_condition_logic, 'and')
WHERE trigger_mode = 'velocity'
  AND (motion_conditions IS NULL OR BTRIM(motion_conditions) = '');

-- Rename trigger_mode / sentinel camera id velocity → motion
UPDATE triggers
SET trigger_mode = 'motion'
WHERE trigger_mode = 'velocity';

UPDATE triggers
SET camera_device_id = 'motion'
WHERE camera_device_id = 'velocity';
