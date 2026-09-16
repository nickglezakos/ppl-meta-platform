-- MVR People Body schema (parallel to mvr_people; posture/height instead of age/gender)
-- Migration: 022_mvr_people_body.sql

CREATE TABLE IF NOT EXISTS mvr_people_body (
    mvr_people_body_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Body metadata (analogous to age/gender on mvr_people)
    posture VARCHAR(32) DEFAULT 'uncertain'
        CHECK (posture IN ('upright', 'horizontal', 'uncertain')),
    posture_confidence FLOAT DEFAULT 0.0
        CHECK (posture_confidence >= 0.0 AND posture_confidence <= 1.0),
    height_px FLOAT,
    height_relative FLOAT,
    height_m FLOAT,  -- null until camera calibration
    -- PLACEHOLDER: dominant clothing colors (JSON array); not computed in V1
    dominant_colors JSONB,
    -- PLACEHOLDER: fallen classifier; unknown until estimate_fallen is implemented
    fallen VARCHAR(16) DEFAULT 'unknown'
        CHECK (fallen IN ('unknown', 'fallen', 'not_fallen')),
    fallen_confidence FLOAT DEFAULT 0.0,

    quality_score FLOAT DEFAULT 0.0,
    confidence_score FLOAT DEFAULT 0.0,

    featured_body_person_uuid UUID,
    featured_video_uuid UUID,
    source_media_uuid UUID,
    camera_id TEXT,
    created_by_session UUID,

    total_appearances INTEGER NOT NULL DEFAULT 0,
    total_videos INTEGER NOT NULL DEFAULT 0,
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    bbox_trajectory JSONB DEFAULT '[]'::JSONB,

    is_isolated BOOLEAN DEFAULT TRUE,
    auto_created BOOLEAN DEFAULT TRUE,

    -- Same-camera continuous stitch linkage
    stitched_from_mvr_uuid UUID REFERENCES mvr_people_body(mvr_people_body_uuid),
    previous_body_person_uuids JSONB DEFAULT '[]'::JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mvr_people_body_media ON mvr_people_body(source_media_uuid);
CREATE INDEX IF NOT EXISTS idx_mvr_people_body_camera ON mvr_people_body(camera_id);
CREATE INDEX IF NOT EXISTS idx_mvr_people_body_session ON mvr_people_body(created_by_session);
CREATE INDEX IF NOT EXISTS idx_mvr_people_body_posture ON mvr_people_body(posture);

CREATE TABLE IF NOT EXISTS mvr_people_body_stitch_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id TEXT NOT NULL,
    mvr_uuid_a UUID REFERENCES mvr_people_body(mvr_people_body_uuid),
    mvr_uuid_b UUID REFERENCES mvr_people_body(mvr_people_body_uuid),
    media_id_a UUID,
    media_id_b UUID,
    iou FLOAT,
    center_distance_px FLOAT,
    time_gap_sec FLOAT,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE mvr_people_body IS
  'MVR People Body: body-track identities with posture/height metadata; colors and fallen are V1 placeholders';
COMMENT ON COLUMN mvr_people_body.dominant_colors IS
  'PLACEHOLDER — not computed in V1; future bbox crop k-means / HSV histogram';
COMMENT ON COLUMN mvr_people_body.fallen IS
  'PLACEHOLDER — estimate_fallen stub; posture horizontal is not certified fallen';
COMMENT ON COLUMN mvr_people_body.height_m IS
  'Null without camera intrinsics + ground-plane calibration; use height_px / height_relative';
