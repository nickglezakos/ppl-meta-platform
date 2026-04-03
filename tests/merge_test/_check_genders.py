#!/usr/bin/env python3
import psycopg

DB_DSN = "postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_vmeta"
VIDEO_UUID = "d46124c8-8944-4784-be9f-3e6314e1f0b8"

sql = """
    SELECT DISTINCT
        i.individual_uuid,
        i.gender_estimate,
        i.age_estimate,
        i.confidence_score,
        imm.mvr_people_uuid        AS mapped_mvr_uuid,
        mp.gender                  AS mvr_gender,
        mp.age_min,
        mp.age_max,
        mp.quality_score           AS mvr_quality,
        mp.featured_person_object_uuid,
        mp.featured_video_uuid,
        mp.merged_into_mvr_uuid
    FROM individual_video_appearances iva
    JOIN individuals i
        ON i.individual_uuid = iva.individual_uuid
    LEFT JOIN individual_mvr_mapping imm
        ON imm.individual_uuid = i.individual_uuid
    LEFT JOIN mvr_people mp
        ON mp.mvr_people_uuid = imm.mvr_people_uuid
    WHERE iva.video_uuid = %s::uuid
    ORDER BY i.individual_uuid
"""

with psycopg.connect(DB_DSN) as conn:
    with conn.cursor() as cur:
        cur.execute(sql, (VIDEO_UUID,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

for i, r in enumerate(rows):
    print(f"\nIndividual {i+1}: {r['individual_uuid']}")
    print(f"  gender_estimate (raw):  {r['gender_estimate']}")
    print(f"  age_estimate (raw):     {r['age_estimate']}")
    print(f"  individual confidence:  {r['confidence_score']}")
    print(f"  mapped MVR:             {r['mapped_mvr_uuid']}")
    print(f"  MVR gender:             {r['mvr_gender']}")
    print(f"  MVR age range:          {r['age_min']}-{r['age_max']}")
    print(f"  MVR quality_score:      {r['mvr_quality']}")
    print(f"  MVR merged_into:        {r['merged_into_mvr_uuid']}")
    print(f"  featured_person_object: {r['featured_person_object_uuid']}")
    print(f"  featured_video_uuid:    {r['featured_video_uuid']}")
