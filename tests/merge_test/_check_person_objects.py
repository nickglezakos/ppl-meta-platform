#!/usr/bin/env python3
"""
Inspect gender + best-quality face for the 4 raw individuals in video d46124c8.
Sources checked (in order):
  1. representative_faces JSON in individual_video_appearances
  2. cached_person_objects (person_objects JSON blob from orchestrator)
  3. individual_thumbnails (binary thumbnail + quality_score)
  4. mvr_people.gender (from the individual's mapped MVR and its root)
"""
import json
import os

import psycopg

DB_DSN = "postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_vmeta"
VIDEO_UUID = "d46124c8-8944-4784-be9f-3e6314e1f0b8"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_individuals(conn):
    sql = """
        SELECT DISTINCT
            i.individual_uuid,
            i.gender_estimate,
            imm.mvr_people_uuid AS mapped_mvr_uuid
        FROM individual_video_appearances iva
        JOIN individuals i ON i.individual_uuid = iva.individual_uuid
        LEFT JOIN individual_mvr_mapping imm ON imm.individual_uuid = i.individual_uuid
        WHERE iva.video_uuid = %s::uuid
        ORDER BY i.individual_uuid
    """
    with conn.cursor() as cur:
        cur.execute(sql, (VIDEO_UUID,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def get_representative_faces(conn, individual_uuid):
    """Return parsed representative_faces list from iva (highest confidence first)."""
    sql = """
        SELECT representative_faces, confidence
        FROM individual_video_appearances
        WHERE individual_uuid = %s::uuid
        ORDER BY confidence DESC NULLS LAST
        LIMIT 5
    """
    with conn.cursor() as cur:
        cur.execute(sql, (str(individual_uuid),))
        results = []
        for row in cur.fetchall():
            rf_raw, conf = row
            if rf_raw:
                try:
                    faces = json.loads(rf_raw) if isinstance(rf_raw, str) else rf_raw
                    # unwrap {'faces': [...]} wrapper if present
                    if isinstance(faces, dict) and 'faces' in faces:
                        faces = faces['faces']
                    if isinstance(faces, list):
                        results.extend(faces)
                    elif isinstance(faces, dict):
                        results.append(faces)
                except Exception:
                    pass
        return results


def get_best_thumbnail(conn, individual_uuid):
    """Return (quality_score, thumbnail_bytes) for the best stored thumbnail."""
    sql = """
        SELECT quality_score, thumbnail_data
        FROM individual_thumbnails
        WHERE individual_uuid = %s::uuid
        ORDER BY quality_score DESC NULLS LAST
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (str(individual_uuid),))
        row = cur.fetchone()
        return (row[0], bytes(row[1])) if row else (None, None)


def get_root_mvr(conn, mvr_uuid):
    """Walk merged_into_mvr_uuid chain to the root MVR record."""
    sql = """
        WITH RECURSIVE chain AS (
            SELECT mvr_people_uuid, merged_into_mvr_uuid, gender, age_min, age_max, quality_score
            FROM mvr_people WHERE mvr_people_uuid = %s::uuid
            UNION ALL
            SELECT p.mvr_people_uuid, p.merged_into_mvr_uuid, p.gender, p.age_min, p.age_max, p.quality_score
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


def get_cached_po_gender(conn, individual_uuid):
    """Try to extract gender from cached_person_objects blobs linked to this individual."""
    # cached_person_objects has a person_objects JSON column; scan for entries
    # where any person_object mentions this individual_uuid
    sql = """
        SELECT person_objects FROM cached_person_objects
        WHERE person_objects::text LIKE %s
        LIMIT 10
    """
    uid_short = str(individual_uuid).replace('-', '')
    with conn.cursor() as cur:
        cur.execute(sql, (f'%{uid_short[:12]}%',))
        for row in cur.fetchall():
            try:
                pos = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if isinstance(pos, list):
                    for po in pos:
                        if isinstance(po, dict):
                            g = po.get('gender') or po.get('predicted_gender') or po.get('gender_label')
                            if g:
                                return g
            except Exception:
                pass
    return None


def main():
    with psycopg.connect(DB_DSN) as conn:
        individuals = get_individuals(conn)
        print(f"Found {len(individuals)} raw individuals in video {VIDEO_UUID}\n")

        for idx, ind in enumerate(individuals):
            ind_uuid = ind['individual_uuid']
            mvr_uuid = ind['mapped_mvr_uuid']
            print(f"{'='*60}")
            print(f"Individual {idx+1}: {ind_uuid}")

            # --- Gender from representative_faces ---
            rf_faces = get_representative_faces(conn, ind_uuid)
            rf_genders = []
            for f in rf_faces:
                g = f.get('gender') or f.get('predicted_gender') or f.get('gender_label')
                q = f.get('quality_score') or f.get('quality') or f.get('face_quality')
                if g:
                    rf_genders.append((g, q))
            print(f"  representative_faces genders: {rf_genders[:5] or '(none stored)'}")
            # print first 3 faces in full to find gender fields
            if rf_faces:
                print(f"  representative_faces[0] keys: {list(rf_faces[0].keys())}")
                for fi, face in enumerate(rf_faces[:3]):
                    print(f"    face[{fi}]: {face}")

            # --- Gender from cached_person_objects ---
            cached_gender = get_cached_po_gender(conn, ind_uuid)
            print(f"  cached_po gender: {cached_gender}")

            # --- Root MVR gender ---
            root = None
            if mvr_uuid:
                root = get_root_mvr(conn, mvr_uuid)
            print(f"  Root MVR gender: {root['gender'] if root else 'N/A'}  "
                  f"({root['mvr_people_uuid'] if root else 'no root'})")

            # --- Best thumbnail ---
            quality, thumb = get_best_thumbnail(conn, ind_uuid)
            if thumb:
                fname = f"best_quality_p{idx+1}_{str(ind_uuid)[:8]}.jpg"
                fpath = os.path.join(OUT_DIR, fname)
                with open(fpath, 'wb') as fh:
                    fh.write(thumb)
                print(f"  Best thumbnail: {fname}  (quality={quality})")
            else:
                print(f"  Best thumbnail: (not in individual_thumbnails table)")


if __name__ == '__main__':
    main()
