#!/usr/bin/env python3
"""
Download and crop the best-quality representative face image for each of the
4 raw individuals in video d46124c8.

Uses:
  - representative_faces.quality_score  (selection rank 1 = highest quality)
  - representative_faces.face_data.bbox  (crop region)
  - Gateway thumbnail URL for the source video frame
  - PIL for the actual crop
"""
import io
import json
import os

import psycopg
import requests
from PIL import Image

DB_DSN = "postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_vmeta"
VIDEO_UUID = "d46124c8-8944-4784-be9f-3e6314e1f0b8"
NODE_SERVICE_URL = "http://localhost:8001"
VMETA_SERVICE_URL = "http://localhost:8008"
GATEWAY_URL = "http://localhost:8080"
TEST_EMAIL = "fresh.user@example.com"
TEST_PASSWORD = "NewPassword234!"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PADDING = 20  # px padding around each cropped face


def get_token():
    r = requests.post(
        f"{NODE_SERVICE_URL}/api/v1/users/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"username={TEST_EMAIL}&password={TEST_PASSWORD}",
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_best_image_info(token, mvr_uuid):
    """Call the best-image API endpoint; return (image_url, bbox, quality, face_data)."""
    r = requests.get(
        f"{VMETA_SERVICE_URL}/api/v1/mvr-people/{mvr_uuid}/best-image",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    bf = r.json().get("best_face", {})
    return (
        bf.get("image_url"),
        bf.get("bbox"),
        bf.get("quality_score"),
        bf.get("face_data", {}),
    )


def download_and_crop(token, image_url, bbox, out_path, padding=PADDING):
    """Fetch the gateway thumbnail, crop to bbox (scaling if needed), save as JPEG."""
    full_url = f"{GATEWAY_URL}{image_url}" if image_url.startswith("/") else image_url
    r = requests.get(full_url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code != 200:
        return False
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    w, h = img.size
    print(f"    Thumbnail size: {w}x{h}")
    if bbox and len(bbox) == 4:
        x1, y1, x2, y2 = [float(v) for v in bbox]
        # If bbox exceeds image dimensions, scale it proportionally
        if x2 > w or y2 > h:
            scale_x = w / max(x2, 1)
            scale_y = h / max(y2, 1)
            scale = min(scale_x, scale_y)
            x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
            print(f"    Bbox scaled by {scale:.3f}: [{x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}]")
        # apply padding, clamp to image bounds
        x1 = max(0, int(x1) - padding)
        y1 = max(0, int(y1) - padding)
        x2 = min(w, int(x2) + padding)
        y2 = min(h, int(y2) + padding)
        if x2 > x1 and y2 > y1:
            img = img.crop((x1, y1, x2, y2))
    img.save(out_path, "JPEG", quality=90)
    return True


def get_individuals_with_best_face(conn):
    """Return individual UUIDs with their best (rank-1) representative face."""
    sql = """
        SELECT DISTINCT
            i.individual_uuid,
            imm.mvr_people_uuid  AS mapped_mvr_uuid,
            mp.gender            AS mvr_gender,
            mp.age_min, mp.age_max,
            mp.quality_score     AS mvr_quality,
            mp.merged_into_mvr_uuid
        FROM individual_video_appearances iva
        JOIN individuals i ON i.individual_uuid = iva.individual_uuid
        LEFT JOIN individual_mvr_mapping imm ON imm.individual_uuid = i.individual_uuid
        LEFT JOIN mvr_people mp ON mp.mvr_people_uuid = imm.mvr_people_uuid
        WHERE iva.video_uuid = %s::uuid
        ORDER BY i.individual_uuid
    """
    with conn.cursor() as cur:
        cur.execute(sql, (VIDEO_UUID,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def get_root_mvr_gender(conn, mvr_uuid):
    sql = """
        WITH RECURSIVE chain AS (
            SELECT mvr_people_uuid, merged_into_mvr_uuid, gender, age_min, age_max
            FROM mvr_people WHERE mvr_people_uuid = %s::uuid
            UNION ALL
            SELECT p.mvr_people_uuid, p.merged_into_mvr_uuid, p.gender, p.age_min, p.age_max
            FROM mvr_people p JOIN chain c ON p.mvr_people_uuid = c.merged_into_mvr_uuid
        )
        SELECT * FROM chain WHERE merged_into_mvr_uuid IS NULL LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (str(mvr_uuid),))
        row = cur.fetchone()
        if row:
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    return None


def main():
    token = get_token()
    print(f"✅ Authenticated\n")

    with psycopg.connect(DB_DSN) as conn:
        individuals = get_individuals_with_best_face(conn)

    print(f"Found {len(individuals)} raw individuals in video {VIDEO_UUID}\n")

    summary_lines = []
    gender_counts = {}

    for idx, ind in enumerate(individuals):
        ind_uuid = str(ind["individual_uuid"])
        mvr_uuid = str(ind["mapped_mvr_uuid"]) if ind["mapped_mvr_uuid"] else None

        print(f"{'='*60}")
        print(f"Individual {idx+1}: {ind_uuid}")

        # --- Gender from root MVR ---
        root_gender = None
        root_age_min = None
        root_age_max = None
        if mvr_uuid:
            with psycopg.connect(DB_DSN) as conn:
                root = get_root_mvr_gender(conn, mvr_uuid)
            if root:
                root_gender = root.get("gender")
                root_age_min = root.get("age_min")
                root_age_max = root.get("age_max")
                print(f"  Root MVR gender: {root_gender}  age: {root_age_min}-{root_age_max}")
                print(f"  Root MVR uuid:   {root['mvr_people_uuid']}")
        else:
            print("  No mapped MVR")

        gender_counts[root_gender or "unknown"] = gender_counts.get(root_gender or "unknown", 0) + 1

        # --- Best-image API (quality-selected representative face) ---
        fname = None
        quality = None
        if mvr_uuid:
            info = get_best_image_info(token, mvr_uuid)
            if info:
                image_url, bbox, quality, face_data = info
                print(f"  Best-image quality: {quality}")
                print(f"  Best-image bbox:    {bbox}")
                if image_url:
                    fname = f"face_p{idx+1}_{ind_uuid[:8]}_{root_gender or 'unknown'}.jpg"
                    fpath = os.path.join(OUT_DIR, fname)
                    ok = download_and_crop(token, image_url, bbox, fpath)
                    if ok:
                        print(f"  ✅ Saved: {fname}")
                    else:
                        fname = None
                        print(f"  ⚠️  Thumbnail download failed")

        summary_lines.append({
            "idx": idx + 1,
            "individual_uuid": ind_uuid,
            "mvr_uuid": mvr_uuid,
            "gender": root_gender,
            "age": f"{root_age_min}-{root_age_max}" if root_age_min else "N/A",
            "quality": quality,
            "face_file": fname,
        })

    # --- Summary ---
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total raw individuals : {len(individuals)}")
    for g, count in sorted(gender_counts.items()):
        print(f"  {g}: {count}")
    print()
    for s in summary_lines:
        print(f"  Person {s['idx']}: gender={s['gender']}  age={s['age']}  "
              f"quality={s['quality']}  face={s['face_file']}")


if __name__ == "__main__":
    main()
