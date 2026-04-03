#!/usr/bin/env python3
"""Probe ALL MVR people for video d46124c8 including orphaned, to understand raw data."""
import psycopg

DB_DSN = "postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_vmeta"
VIDEO_UUID = "d46124c8-8944-4784-be9f-3e6314e1f0b8"

sql_all_mvr = """
    SELECT
        mp.mvr_people_uuid,
        mp.gender,
        mp.gender_confidence,
        mp.age_min, mp.age_max,
        mp.quality_score,
        mp.confidence_score,
        mp.is_orphaned,
        mp.merged_into_mvr_uuid,
        mp.face_embedding IS NOT NULL AS has_embedding,
        COUNT(imm_inner.individual_uuid) AS linked_individuals
    FROM mvr_people mp
    LEFT JOIN individual_mvr_mapping imm_inner ON imm_inner.mvr_people_uuid = mp.mvr_people_uuid
    WHERE mp.mvr_people_uuid IN (
        SELECT DISTINCT imm.mvr_people_uuid
        FROM individual_video_appearances iva
        JOIN individual_mvr_mapping imm ON imm.individual_uuid = iva.individual_uuid
        WHERE iva.video_uuid = %s::uuid
    )
    GROUP BY mp.mvr_people_uuid
    ORDER BY mp.is_orphaned, mp.quality_score DESC
"""

with psycopg.connect(DB_DSN) as conn:
    with conn.cursor() as cur:
        cur.execute(sql_all_mvr, (VIDEO_UUID,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

print(f"Total MVR people for video {VIDEO_UUID[:8]}: {len(rows)}\n")
for row in rows:
    d = dict(zip(cols, row))
    merged_into = str(d["merged_into_mvr_uuid"])[:8] if d["merged_into_mvr_uuid"] else "None"
    print(
        f"  MVR={str(d['mvr_people_uuid'])[:8]}"
        f"  gender={d['gender']}"
        f"  g_conf={d['gender_confidence']}"
        f"  age={d['age_min']}-{d['age_max']}"
        f"  qual={d['quality_score']:.3f}"
        f"  orphaned={d['is_orphaned']}"
        f"  merged_into={merged_into}"
        f"  has_emb={d['has_embedding']}"
        f"  linked_ind={d['linked_individuals']}"
    )
