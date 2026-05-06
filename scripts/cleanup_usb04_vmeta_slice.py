#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List
from urllib import error, parse, request


NODE_BASE_URL = "http://localhost:8001"
VMETA_BASE_URL = "http://localhost:8008"
LOGIN_PATH = "/api/v1/users/login"
DEFAULT_USERNAME = "fresh.user@example.com"
DEFAULT_PASSWORD = "NewPassword234!"
DEFAULT_DB_NAME = "ppl_meta_vmeta"
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_USER = "postgres"
DEFAULT_DB_PASSWORD = "postgres"

TARGET_VIDEO_UUIDS = [
    "cf11360a-1616-4db7-b746-0f9521e3165d",
    "77d9fd50-abab-43b7-b1b5-eee0cb92dc5d",
    "f22b08ec-69af-4a92-8bdd-d569d7ebfe9f",
    "d233ed4e-6b35-4cb7-9bbe-3258d15bd018",
    "e3d88b2c-a3a8-470f-aa47-c7d0210b251c",
    "67a5b5a6-2e1f-49c3-b853-eb97672068be",
]

RECOVERABLE_ERRORS = (
    RuntimeError,
    OSError,
    ValueError,
    error.HTTPError,
    error.URLError,
    subprocess.SubprocessError,
)


@dataclass
class CleanupConfig:
    db_host: str
    db_name: str
    db_user: str
    db_password: str
    node_base_url: str
    vmeta_base_url: str
    username: str
    password: str


def build_values_clause(video_uuids: List[str]) -> str:
    return ",\n        ".join(f"('{video_uuid}'::uuid)" for video_uuid in video_uuids)


def run_psql(sql: str, cfg: CleanupConfig, quiet: bool = True) -> str:
    env = os.environ.copy()
    env["PGPASSWORD"] = cfg.db_password
    command = [
        "psql",
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-A",
        "-F",
        "|",
        "-t",
        "-P",
        "pager=off",
        "-h",
        cfg.db_host,
        "-U",
        cfg.db_user,
        "-d",
        cfg.db_name,
        "-c",
        sql,
    ]
    if quiet:
        command.insert(1, "-q")

    completed = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def login_and_get_token(cfg: CleanupConfig) -> str:
    payload = parse.urlencode(
        {
            "username": cfg.username,
            "password": cfg.password,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{cfg.node_base_url}{LOGIN_PATH}",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Login response did not include access_token: {data}")
    return token


def collect_counts(cfg: CleanupConfig) -> Dict[str, int]:
    values_clause = build_values_clause(TARGET_VIDEO_UUIDS)
    sql = f"""
WITH target_videos(video_uuid) AS (
    VALUES
        {values_clause}
),
target_individuals AS (
    SELECT DISTINCT iva.individual_uuid
    FROM individual_video_appearances iva
    JOIN target_videos tv USING (video_uuid)
),
target_mvr_links AS (
    SELECT DISTINCT imm.mvr_people_uuid
    FROM individual_mvr_mapping imm
    JOIN target_individuals ti ON ti.individual_uuid = imm.individual_uuid
),
shared_mvr_roots AS (
    SELECT DISTINCT imm.mvr_people_uuid
    FROM individual_mvr_mapping imm
    JOIN target_mvr_links tml ON tml.mvr_people_uuid = imm.mvr_people_uuid
    JOIN individual_video_appearances iva ON iva.individual_uuid = imm.individual_uuid
    LEFT JOIN target_videos tv ON tv.video_uuid = iva.video_uuid
    WHERE tv.video_uuid IS NULL
)
SELECT 'target_videos', COUNT(*)::text FROM target_videos
UNION ALL
SELECT 'appearances', COUNT(*)::text FROM individual_video_appearances iva JOIN target_videos tv USING (video_uuid)
UNION ALL
SELECT 'individuals', COUNT(*)::text FROM target_individuals
UNION ALL
SELECT 'mappings', COUNT(*)::text FROM individual_mvr_mapping imm JOIN target_individuals ti ON ti.individual_uuid = imm.individual_uuid
UNION ALL
SELECT 'source_mvrs', COUNT(*)::text FROM mvr_people mp JOIN target_videos tv ON tv.video_uuid = mp.source_media_uuid
UNION ALL
SELECT 'featured_mvrs', COUNT(*)::text FROM mvr_people mp JOIN target_videos tv ON tv.video_uuid = mp.featured_video_uuid
UNION ALL
SELECT 'shared_mvr_roots', COUNT(*)::text FROM shared_mvr_roots
ORDER BY 1;
"""
    output = run_psql(sql, cfg)
    counts: Dict[str, int] = {}
    for line in output.splitlines():
        if not line or line.startswith("("):
            continue
        key, value = line.split("|", 1)
        counts[key] = int(value)
    return counts


def cleanup_slice(cfg: CleanupConfig) -> None:
    values_clause = build_values_clause(TARGET_VIDEO_UUIDS)
    sql = f"""
BEGIN;

CREATE TEMP TABLE target_videos(
    video_uuid uuid PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO target_videos(video_uuid)
SELECT * FROM (VALUES
    {values_clause}
) AS v(video_uuid);

CREATE TEMP TABLE target_individuals(
    individual_uuid uuid PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO target_individuals(individual_uuid)
SELECT DISTINCT iva.individual_uuid
FROM individual_video_appearances iva
JOIN target_videos tv USING (video_uuid);

CREATE TEMP TABLE target_related_mvr_people(
    mvr_people_uuid uuid PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO target_related_mvr_people(mvr_people_uuid)
SELECT DISTINCT imm.mvr_people_uuid
FROM individual_mvr_mapping imm
JOIN target_individuals ti ON ti.individual_uuid = imm.individual_uuid
UNION
SELECT DISTINCT mp.mvr_people_uuid
FROM mvr_people mp
JOIN target_videos tv ON tv.video_uuid = mp.source_media_uuid
UNION
SELECT DISTINCT mp.mvr_people_uuid
FROM mvr_people mp
JOIN target_videos tv ON tv.video_uuid = mp.featured_video_uuid;

DELETE FROM individual_mvr_mapping imm
WHERE imm.individual_uuid IN (SELECT individual_uuid FROM target_individuals);

DELETE FROM individual_video_appearances iva
WHERE iva.video_uuid IN (SELECT video_uuid FROM target_videos);

UPDATE mvr_people mp
SET featured_individual_uuid = remaining.individual_uuid
FROM (
    SELECT imm.mvr_people_uuid, MIN(imm.individual_uuid::text)::uuid AS individual_uuid
        FROM individual_mvr_mapping imm
        GROUP BY imm.mvr_people_uuid
) AS remaining
WHERE mp.mvr_people_uuid = remaining.mvr_people_uuid
    AND mp.featured_individual_uuid IN (SELECT individual_uuid FROM target_individuals);

UPDATE mvr_people mp
SET is_merged = FALSE,
    is_orphaned = FALSE,
    orphaned_at = NULL,
        merged_into_mvr_uuid = NULL,
        merged_into_uuid = NULL
WHERE mp.merged_into_mvr_uuid IN (SELECT mvr_people_uuid FROM target_related_mvr_people)
     OR mp.merged_into_uuid IN (SELECT mvr_people_uuid FROM target_related_mvr_people);

DELETE FROM mvr_merge_audit_log log
WHERE log.source_individual_uuid IN (SELECT individual_uuid FROM target_individuals)
    OR log.source_mvr_uuid IN (SELECT mvr_people_uuid FROM target_related_mvr_people)
    OR log.target_mvr_uuid IN (SELECT mvr_people_uuid FROM target_related_mvr_people)
    OR log.winner_mvr_uuid IN (SELECT mvr_people_uuid FROM target_related_mvr_people);

DELETE FROM mvr_people mp
WHERE mp.mvr_people_uuid IN (SELECT mvr_people_uuid FROM target_related_mvr_people)
    AND NOT EXISTS (
            SELECT 1
            FROM individual_mvr_mapping imm
            WHERE imm.mvr_people_uuid = mp.mvr_people_uuid
    );

DELETE FROM individuals i
WHERE i.individual_uuid IN (SELECT individual_uuid FROM target_individuals);

COMMIT;
"""
    run_psql(sql, cfg, quiet=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean persisted VMeta rows for the USB04 affected video slice."
    )
    parser.add_argument("--db-host", default=DEFAULT_DB_HOST)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=DEFAULT_DB_PASSWORD)
    parser.add_argument("--node-base-url", default=NODE_BASE_URL)
    parser.add_argument("--vmeta-base-url", default=VMETA_BASE_URL)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument(
        "--token-only",
        action="store_true",
        help="Print a fresh bearer token and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show counts only and do not delete anything.",
    )
    args = parser.parse_args()

    cfg = CleanupConfig(
        db_host=args.db_host,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
        node_base_url=args.node_base_url.rstrip("/"),
        vmeta_base_url=args.vmeta_base_url.rstrip("/"),
        username=args.username,
        password=args.password,
    )

    try:
        token = login_and_get_token(cfg)
    except RECOVERABLE_ERRORS as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1

    if args.token_only:
        print(token)
        return 0

    print(f"Authenticated against {cfg.node_base_url} as {cfg.username}")
    print(f"Token preview: {token[:16]}...{token[-8:]}")
    print(f"Target videos: {len(TARGET_VIDEO_UUIDS)}")

    try:
        before = collect_counts(cfg)
    except RECOVERABLE_ERRORS as exc:
        print(f"Failed to collect pre-cleanup counts: {exc}", file=sys.stderr)
        return 1

    print("Pre-cleanup counts:")
    for key in sorted(before):
        print(f"  {key}: {before[key]}")

    if args.dry_run:
        print("Dry run only. No rows deleted.")
        return 0

    try:
        cleanup_slice(cfg)
    except RECOVERABLE_ERRORS as exc:
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1

    try:
        after = collect_counts(cfg)
    except RECOVERABLE_ERRORS as exc:
        print(f"Failed to collect post-cleanup counts: {exc}", file=sys.stderr)
        return 1

    print("Post-cleanup counts:")
    for key in sorted(after):
        print(f"  {key}: {after[key]}")

    print("Derived deletions:")
    for key in ("appearances", "individuals", "mappings", "source_mvrs", "featured_mvrs"):
        before_value = before.get(key, 0)
        after_value = after.get(key, 0)
        print(f"  {key}: {before_value - after_value}")

    if after.get("appearances", 0) != 0 or after.get("individuals", 0) != 0:
        print("Cleanup completed, but target rows remain. Inspect manually.", file=sys.stderr)
        return 2

    print("Cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())