CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
DECLARE
  emb_udt TEXT;
  has_gender_est BOOLEAN;
  has_gender BOOLEAN;
BEGIN
  SELECT c.udt_name INTO emb_udt
  FROM information_schema.columns c
  WHERE c.table_schema = 'public'
    AND c.table_name = 'mvr_people'
    AND c.column_name = 'face_embedding';

  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='mvr_people' AND column_name='gender_estimate'
  ) INTO has_gender_est;

  SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='mvr_people' AND column_name='gender'
  ) INTO has_gender;

  IF emb_udt IS NOT NULL AND emb_udt <> 'vector' THEN
    RAISE NOTICE 'Dropping stub mvr_people (face_embedding udt=%)', emb_udt;
    DROP TABLE IF EXISTS individual_mvr_mapping CASCADE;
    DROP TABLE IF EXISTS mvr_people CASCADE;
  ELSIF has_gender_est AND NOT has_gender THEN
    RAISE NOTICE 'Dropping stub mvr_people (gender_estimate without gender)';
    DROP TABLE IF EXISTS individual_mvr_mapping CASCADE;
    DROP TABLE IF EXISTS mvr_people CASCADE;
  END IF;
END $$;
