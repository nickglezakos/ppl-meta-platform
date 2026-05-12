#!/usr/bin/env python3
"""
Probe ALL MVR people for collection 360460d5 in the 1pm-5pm time range,
including orphaned ones, to see true gender breakdown.
"""
import sys
from pathlib import Path

media_site_packages = (
    Path(__file__).resolve().parents[2]
    / "ppl-meta-media"
    / "venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
if media_site_packages.exists():
    sys.path.insert(0, str(media_site_packages))

import psycopg
import requests

DB_DSN = "postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_vmeta"
COLLECTION_UUID = "360460d5-4c00-4f90-a623-42a71811b0b3"
NODE_URL = "http://localhost:8001"
MEDIA_URL = "http://localhost:8000"

# Auth
resp = requests.post(
    f"{NODE_URL}/api/v1/users/login",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data="username=fresh.user@example.com&password=NewPassword234!",
    timeout=30,
)
resp.raise_for_status()
token = resp.json()["access_token"]
print("Auth ok")

# Fetch videos in collection/time window
media_resp = requests.get(
    f"{MEDIA_URL}/api/v1/media/search",
    headers={"Authorization": f"Bearer {token}"},
    params={
        "collection_id": COLLECTION_UUID,
        "start_time": "2026-03-01T13:00:00",
        "end_time": "2026-03-01T17:00:00",
        "page_size": 200,
        "page": 1,
    },
    timeout=60,
)
media_resp.raise_for_status()
items = media_resp.json()
if isinstance(items, dict):
    items = items.get("items", []) or items.get("results", []) or []
video_uuids = [it.get("uuid") or it.get("media_uuid") for it in items if (it.get("media_type") == "video" or it.get("type") == "video")]
video_uuids = [u for u in video_uuids if u]
print(f"Videos in collection time window: {len(video_uuids)}")

if not video_uuids:
    print("No videos found - exiting")
    sys.exit(1)

# Now query ALL mvr_people for these videos (including orphaned)
with psycopg.connect(DB_DSN) as conn:
    with conn.cursor() as cur:
        cur.execute("""
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
                COUNT(DISTINCT iva2.video_uuid) AS video_count
            FROM mvr_people mp
            INNER JOIN individual_mvr_mapping imm ON imm.mvr_people_uuid = mp.mvr_people_uuid
            INNER JOIN individual_video_appearances iva ON iva.individual_uuid = imm.individual_uuid
            INNER JOIN individual_video_appearances iva2 ON iva2.individual_uuid = imm.individual_uuid
            WHERE iva.video_uuid = ANY(%s::uuid[])
            GROUP BY mp.mvr_people_uuid
            ORDER BY mp.is_orphaned, mp.quality_score DESC
        """, (video_uuids,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

print(f"\nTotal MVR people (incl orphaned) for collection: {len(rows)}")
print()
female_count = 0
male_count = 0
unknown_count = 0
for row in rows:
    d = dict(zip(cols, row))
    gender = d['gender'] or 'unknown'
    if gender == 'female':
        female_count += 1
    elif gender == 'male':
        male_count += 1
    else:
        unknown_count += 1
    merged_into = str(d["merged_into_mvr_uuid"])[:8] if d["merged_into_mvr_uuid"] else "None"
    print(
        f"  MVR={str(d['mvr_people_uuid'])[:8]}"
        f"  gender={gender:8s}"
        f"  g_conf={str(round(d['gender_confidence'], 3)) if d['gender_confidence'] else 'None':7s}"
        f"  age={d['age_min']}-{d['age_max']}"
        f"  qual={d['quality_score']:.3f}"
        f"  orphaned={d['is_orphaned']}"
        f"  merged_into={merged_into}"
        f"  vids={d['video_count']}"
    )

print()
print(f"Gender summary: male={male_count}  female={female_count}  unknown={unknown_count}")
print(f"Total: {len(rows)} MVR people")
