#!/usr/bin/env python3
"""
MVR Merge Logic Integration Test — NEW CODEBASE (DRY RUN)

Imports HierarchicalMVRMerger and UnionFind directly from the production
codebase (ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py) and runs
the new merge logic — including the confidence-aware cross-gender guard —
in dry-run mode (no DB writes).

Old false merges are completely ignored: all mvr_people records for the
collection are fetched REGARDLESS of is_orphaned / merged_into_mvr_uuid.

Output:
  - results.txt      full text report
  - merge_g<N>_m<M>_<uuid>_<gender>.jpg  cropped face per person per group

Collection: 360460d5-4c00-4f90-a623-42a71811b0b3
Date range:  2026-03-01 13:00 – 17:00 EET (local, service handles natively)

PYTHON: autonomous/ppl-meta-mini/venv/bin/python3
Run:    python test_merge.py
"""
from __future__ import annotations
import asyncio, io, os, sys
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Import the NEW codebase merger.
# Mock out DB/ML deps so the module loads without the full service stack.
# ---------------------------------------------------------------------------
_VMETA_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ppl-meta-vmeta", "src")
)
sys.path.insert(0, _VMETA_SRC)

for _mod in (
    "database", "database.mvr_repository",
    "services.mvr_matcher",
    "ml", "ml.mvr_processor", "ml.facenet_processor",
    "ml.age_estimator", "ml.gender_classifier",
    "asyncpg", "httpx",
):
    sys.modules.setdefault(_mod, MagicMock())

# Real production classes from codebase:
from services.hierarchical_mvr_merger import HierarchicalMVRMerger, UnionFind  # noqa

import numpy as np
import psycopg
import requests
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
NODE_SERVICE_URL  = "http://localhost:8001"
MEDIA_SERVICE_URL = "http://localhost:8000"
VMETA_SERVICE_URL = "http://localhost:8008"
GATEWAY_URL       = "http://localhost:8080"

TEST_EMAIL    = "fresh.user@example.com"
TEST_PASSWORD = "NewPassword234!"

COLLECTION_ID = "360460d5-4c00-4f90-a623-42a71811b0b3"
# Times in local EET (UTC+2) — media service handles local time natively
START_TIME    = "2026-03-01T13:00:00"
END_TIME      = "2026-03-01T17:00:00"

DB_DSN = "postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta_vmeta"

SIMILARITY_THRESHOLD = 0.70
MIN_SIMILARITY_CHECK = 0.50
GENDER_CONF_GATE     = 0.80

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_auth_token() -> str:
    resp = requests.post(
        f"{NODE_SERVICE_URL}/api/v1/users/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"username={TEST_EMAIL}&password={TEST_PASSWORD}",
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"No access_token: {resp.json()}")
    print(f"OK Authenticated as {TEST_EMAIL}")
    return token


def get_video_uuids(token: str) -> list:
    resp = requests.get(
        f"{MEDIA_SERVICE_URL}/api/v1/media/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"collection_id": COLLECTION_ID, "start_time": START_TIME,
                "end_time": END_TIME, "page_size": 200, "page": 1},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", data.get("results", []))
    uuids = [it.get("uuid") or it.get("media_uuid") for it in items
             if it.get("media_type") == "video" or it.get("type") == "video"]
    uuids = [u for u in uuids if u]
    print(f"Found {len(uuids)} video(s) in collection")
    return uuids


def fetch_all_mvr_people_raw(video_uuids: list) -> list:
    """
    Query ALL mvr_people for these videos — INCLUDING orphaned records.
    Old false merges are completely bypassed; is_orphaned is IGNORED.
    Dict keys match what HierarchicalMVRMerger._fetch_mvr_people() returns.
    """
    sql = """
        SELECT DISTINCT
            mp.mvr_people_uuid,
            mp.face_embedding,
            mp.quality_score,
            mp.confidence_score,
            mp.featured_individual_uuid,
            mp.gender,
            mp.gender_confidence,
            mp.age_min,
            mp.age_max,
            mp.is_orphaned,
            mp.merged_into_mvr_uuid
        FROM mvr_people mp
        INNER JOIN individual_mvr_mapping imm
            ON imm.mvr_people_uuid = mp.mvr_people_uuid
        INNER JOIN individual_video_appearances iva
            ON iva.individual_uuid = imm.individual_uuid
        WHERE iva.video_uuid = ANY(%s::uuid[])
          AND mp.face_embedding IS NOT NULL
        ORDER BY mp.quality_score DESC
    """
    rows = []
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (video_uuids,))
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                emb_str = d.pop("face_embedding")
                vals = [float(x) for x in emb_str.strip("[]").split(",")]
                d["face_embedding"] = np.array(vals)
                rows.append(d)
    return rows


def download_and_crop_face(token: str, mvr_uuid: str, label: str) -> str | None:
    """Download best-image for mvr_uuid, crop to face bbox, save as <label>.jpg."""
    try:
        r = requests.get(
            f"{VMETA_SERVICE_URL}/api/v1/mvr-people/{mvr_uuid}/best-image",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        best_face = r.json().get("best_face")
        if not best_face or not best_face.get("image_url"):
            return None
        image_url = best_face["image_url"]
        full_url = f"{GATEWAY_URL}{image_url}" if image_url.startswith("/") else image_url
        img_r = requests.get(full_url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if img_r.status_code != 200:
            return None
        img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
        w, h = img.size
        bbox = best_face.get("bbox")
        if bbox and len(bbox) == 4:
            x1, y1, x2, y2 = [float(v) for v in bbox]
            if x2 > w or y2 > h:
                scale = min(w / x2, h / y2)
                x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
            pad = max(4, int((x2 - x1) * 0.1))
            x1, y1 = max(0, int(x1) - pad), max(0, int(y1) - pad)
            x2, y2 = min(w, int(x2) + pad), min(h, int(y2) + pad)
            if x2 > x1 and y2 > y1:
                img = img.crop((x1, y1, x2, y2))
        filename = f"{label}.jpg"
        img.save(os.path.join(OUTPUT_DIR, filename))
        return filename
    except Exception as exc:
        print(f"  WARN: Face crop failed for {mvr_uuid[:8]}: {exc}")
        return None


async def dry_run_merge(mvr_people: list) -> tuple:
    """Run production HierarchicalMVRMerger similarity + grouping (no DB writes)."""
    merger = HierarchicalMVRMerger(repository=MagicMock(), mvr_matcher=MagicMock())
    merger.gender_conflict_min_confidence = GENDER_CONF_GATE
    similarity_matrix = await merger._calculate_similarity_matrix(
        mvr_people, min_similarity=MIN_SIMILARITY_CHECK
    )
    merge_groups = merger._find_merge_groups(
        mvr_people, similarity_matrix, SIMILARITY_THRESHOLD
    )
    stats = {
        "total_mvr":     len(mvr_people),
        "groups":        len(merge_groups),
        "merged_groups": sum(1 for g in merge_groups if len(g) > 1),
        "standalone":    sum(1 for g in merge_groups if len(g) == 1),
    }
    return merge_groups, stats


def main() -> None:
    sep = "=" * 68
    print(sep)
    print("MVR Merge Test - NEW CODEBASE (DRY RUN, gender guard enabled)")
    print(f"Collection : {COLLECTION_ID}")
    print(f"Time range : {START_TIME} - {END_TIME}")
    print(f"Threshold  : {SIMILARITY_THRESHOLD}  Gender gate: {GENDER_CONF_GATE}")
    print(sep)

    token       = get_auth_token()
    video_uuids = get_video_uuids(token)
    if not video_uuids:
        print("ERROR: No videos found - aborting.")
        sys.exit(1)

    print(f"\nFetching ALL MVR people from DB (including old orphaned records)...")
    mvr_people  = fetch_all_mvr_people_raw(video_uuids)
    male_raw    = sum(1 for m in mvr_people if m.get("gender") == "male")
    female_raw  = sum(1 for m in mvr_people if m.get("gender") == "female")
    unknown_raw = len(mvr_people) - male_raw - female_raw
    print(f"   {len(mvr_people)} raw MVR records: male={male_raw} female={female_raw} unknown={unknown_raw}")

    print(f"\nRunning HierarchicalMVRMerger from codebase (DRY RUN)...")
    merge_groups, stats = asyncio.run(dry_run_merge(mvr_people))
    group_genders = [g[0].get("gender") or "unknown" for g in merge_groups]
    print(f"   {stats['groups']} group(s): male={group_genders.count('male')} "
          f"female={group_genders.count('female')} unknown={group_genders.count('unknown')}")

    lines = [
        "MVR Merge Test - NEW CODEBASE (DRY RUN, gender guard enabled)",
        f"Run at     : {datetime.now().isoformat()}",
        f"Collection : {COLLECTION_ID}",
        f"Time range : {START_TIME} - {END_TIME}",
        f"Threshold  : {SIMILARITY_THRESHOLD}  Gender gate: {GENDER_CONF_GATE}",
        "",
        f"Raw MVR count (incl. orphaned from old false merges): {stats['total_mvr']}",
        f"  male={male_raw}  female={female_raw}  unknown={unknown_raw}",
        "",
        f"NEW CODE dry-run result: {stats['groups']} group(s)",
        f"  merged groups = {stats['merged_groups']}  standalone = {stats['standalone']}",
        f"  winner gender: male={group_genders.count('male')} "
        f"female={group_genders.count('female')} unknown={group_genders.count('unknown')}",
        "",
        sep,
        "MERGE GROUPS",
        "(* = winner/highest-quality  | - = loser/would be orphaned under new code)",
        "Gender guard blocks high-confidence male/female pairs from merging.",
        sep, "",
    ]

    print(f"\n{sep}")
    print(f"DOWNLOADING FACE CROPS ({len(mvr_people)} MVR people)...")
    print(sep)

    for g_idx, group in enumerate(merge_groups):
        winner   = group[0]
        w_gender = winner.get("gender") or "unknown"
        w_qual   = winner.get("quality_score", 0)
        print(f"\nGroup {g_idx + 1:3d}  [{len(group)} member(s)]  winner-gender={w_gender}  quality={w_qual:.3f}")
        lines.append(f"Group {g_idx + 1:3d}  ({len(group)} member(s))")

        for m_idx, mvr in enumerate(group):
            uuid_str  = str(mvr["mvr_people_uuid"])
            gender    = mvr.get("gender") or "unknown"
            age_str   = f"{mvr.get('age_min')}-{mvr.get('age_max')}" if mvr.get("age_min") else "?"
            qual      = mvr.get("quality_score", 0)
            g_conf    = mvr.get("gender_confidence")
            g_conf_s  = f"{g_conf:.4f}" if g_conf is not None else "None"
            star      = "*" if m_idx == 0 else "-"
            role      = "WINNER" if m_idx == 0 else "loser "
            old_into  = str(mvr.get("merged_into_mvr_uuid") or "")[:8] or "None"

            label     = f"merge_g{g_idx + 1:02d}_m{m_idx + 1:02d}_{uuid_str[:8]}_{gender}"
            face_file = download_and_crop_face(token, uuid_str, label)
            face_s    = face_file if face_file else "(no face)"

            print(f"  {star} {role}  {uuid_str[:8]}  gender={gender:7s}  qual={qual:.3f}  -> {face_s}")
            lines += [
                f"  {star} {role}  MVR={uuid_str}",
                f"      gender={gender}  g_conf={g_conf_s}  age={age_str}  quality={qual:.4f}",
                f"      old_orphaned={mvr.get('is_orphaned', False)}  old_merged_into={old_into}",
                f"      face={face_s}",
            ]
        lines.append("")

    lines += [
        sep, "SUMMARY", sep,
        f"Raw MVR count (incl. old orphaned): {stats['total_mvr']}",
        f"  male={male_raw}  female={female_raw}  unknown={unknown_raw}",
        "",
        f"NEW code result: {stats['groups']} distinct person group(s)",
        f"  male groups    = {group_genders.count('male')}",
        f"  female groups  = {group_genders.count('female')}",
        f"  unknown groups = {group_genders.count('unknown')}",
        "",
        "Old code problem:",
        "  Old merge algorithm followed merged_into_mvr_uuid chains and",
        "  merged males and females into a single super-individual.",
        "  The new confidence-aware gender guard (threshold >= 0.80)",
        "  blocks high-confidence cross-gender merges automatically.",
    ]

    out_path = os.path.join(OUTPUT_DIR, "results.txt")
    with open(out_path, "w") as fh:
        fh.write("\n".join(lines))

    print(f"\nOK Results -> {out_path}")
    print(f"\nFINAL SUMMARY")
    print(f"  Raw MVR: {stats['total_mvr']} (male={male_raw} female={female_raw} unknown={unknown_raw})")
    print(f"  NEW CODE: {stats['groups']} group(s) "
          f"[male={group_genders.count('male')} female={group_genders.count('female')} unknown={group_genders.count('unknown')}]")


if __name__ == "__main__":
    main()
