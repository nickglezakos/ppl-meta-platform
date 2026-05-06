"""
Repair legacy individual_video_appearances.person_object_uuid values.

This script fixes only rows that can be matched deterministically to a
persisted Vision person object for the same media UUID.

Matching strategy:
1. Read VMeta appearance rows that have representative_faces and whose current
   person_object_uuid does not exist in Vision person_objects.
2. Resolve the corresponding Vision session via face_detection_sessions.media_uuid.
3. Compare the appearance representative face frame/center against persisted
   Vision route data (all_faces_route_data) and representative_faces.
4. Repair only rows with a single confident candidate.

Usage:
  python3 repair_appearance_person_object_uuids.py --dry-run
  python3 repair_appearance_person_object_uuids.py --apply
  python3 repair_appearance_person_object_uuids.py --dry-run --limit 100
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


VMETA_DB = os.getenv(
    "VMETA_DB",
    "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta",
)
VISION_DB = os.getenv(
    "VISION_DB",
    "postgresql://postgres:localdevpass@localhost:5432/ppl_vision_db",
)

PRIMARY_CENTER_TOLERANCE = 2.0
SECONDARY_DISTANCE_TOLERANCE = 15.0


@dataclass
class AppearanceRow:
    individual_uuid: str
    video_uuid: str
    person_object_uuid: str
    representative_faces: Any


@dataclass
class VisionCandidate:
    media_uuid: str
    person_id: str
    representative_faces: Any
    all_faces_route_data: Any


def run_psql_json(connection_string: str, query: str) -> Any:
    command = [
        "psql",
        connection_string,
        "-X",
        "-q",
        "-t",
        "-A",
        "-c",
        query,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "psql query failed")
    output = result.stdout.strip()
    if not output:
        return None
    return json.loads(output)


def run_psql_exec(connection_string: str, query: str) -> None:
    command = ["psql", connection_string, "-X", "-q", "-c", query]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "psql execution failed")


def parse_json_payload(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return json.loads(stripped)
        except (TypeError, ValueError):
            return None
    return None


def append_face_ref(
    refs: List[Tuple[Optional[int], Optional[float], Optional[float]]],
    payload: Any,
) -> None:
    if not isinstance(payload, dict):
        return
    face_data = payload.get("face_data") or payload
    frame_number = None
    center_x = None
    center_y = None
    try:
        if face_data.get("frame_number") is not None:
            frame_number = int(face_data.get("frame_number"))
    except (TypeError, ValueError):
        frame_number = None
    try:
        if face_data.get("center_x") is not None:
            center_x = float(face_data.get("center_x"))
            center_y = float(face_data.get("center_y") or 0.0)
    except (TypeError, ValueError):
        center_x = None
        center_y = None
    if frame_number is not None or center_x is not None:
        refs.append((frame_number, center_x, center_y))


def extract_face_refs(representative_faces: Any) -> List[Tuple[Optional[int], Optional[float], Optional[float]]]:
    representative_faces = parse_json_payload(representative_faces)
    refs: List[Tuple[Optional[int], Optional[float], Optional[float]]] = []
    if isinstance(representative_faces, list):
        for face in representative_faces:
            append_face_ref(refs, face)
    elif isinstance(representative_faces, dict):
        faces = representative_faces.get("faces") or []
        if isinstance(faces, list):
            for face in faces:
                append_face_ref(refs, face)
    return refs


def iter_route_points(candidate: VisionCandidate) -> Iterable[Dict[str, Any]]:
    route_data = parse_json_payload(candidate.all_faces_route_data)
    if isinstance(route_data, list):
        for point in route_data:
            if isinstance(point, dict):
                yield point

    representative_faces = parse_json_payload(candidate.representative_faces)
    if isinstance(representative_faces, list):
        for face in representative_faces:
            if isinstance(face, dict):
                yield face.get("face_data") or face


def candidate_score(
    refs: Sequence[Tuple[Optional[int], Optional[float], Optional[float]]],
    candidate: VisionCandidate,
) -> Optional[Tuple[int, float]]:
    best_secondary = float("inf")
    primary_hits = 0
    for ref_frame, ref_x, ref_y in refs:
        for route_point in iter_route_points(candidate):
            route_frame = route_point.get("frame_number")
            try:
                route_frame = int(route_frame) if route_frame is not None else None
            except (TypeError, ValueError):
                route_frame = None
            try:
                route_x = float(
                    route_point.get("center_x", route_point.get("position", {}).get("x", 0.0))
                )
                route_y = float(
                    route_point.get("center_y", route_point.get("position", {}).get("y", 0.0))
                )
            except (TypeError, ValueError, AttributeError):
                continue

            if ref_frame is not None and route_frame == ref_frame and ref_x is not None:
                if abs(route_x - ref_x) <= PRIMARY_CENTER_TOLERANCE:
                    primary_hits += 1

            if ref_x is not None and ref_y is not None:
                distance = math.sqrt((route_x - ref_x) ** 2 + (route_y - ref_y) ** 2)
                if distance < best_secondary:
                    best_secondary = distance

    if primary_hits > 0:
        return (primary_hits, 0.0)
    if best_secondary < SECONDARY_DISTANCE_TOLERANCE:
        return (0, best_secondary)
    return None


def choose_candidate(
    refs: Sequence[Tuple[Optional[int], Optional[float], Optional[float]]],
    candidates: Sequence[VisionCandidate],
) -> Tuple[Optional[VisionCandidate], str]:
    scored: List[Tuple[VisionCandidate, Tuple[int, float]]] = []
    for candidate in candidates:
        score = candidate_score(refs, candidate)
        if score is not None:
            scored.append((candidate, score))

    if not scored:
        return None, "no_match"

    scored.sort(key=lambda item: (-item[1][0], item[1][1], item[0].person_id))
    best_candidate, best_score = scored[0]
    tied = [item for item in scored if item[1] == best_score]
    if len(tied) > 1:
        return None, "ambiguous"
    return best_candidate, "matched"


def load_appearance_rows(limit: Optional[int]) -> List[AppearanceRow]:
    limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""
    query = f"""
    SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
    FROM (
        SELECT
            individual_uuid::text AS individual_uuid,
            video_uuid::text AS video_uuid,
            person_object_uuid::text AS person_object_uuid,
            representative_faces
        FROM individual_video_appearances
        WHERE representative_faces IS NOT NULL
        ORDER BY created_at ASC NULLS LAST, start_timestamp ASC
        {limit_sql}
    ) t;
    """
    rows = run_psql_json(VMETA_DB, query) or []
    return [AppearanceRow(**row) for row in rows]


def load_vision_candidates(media_uuids: Sequence[str]) -> Dict[str, List[VisionCandidate]]:
    if not media_uuids:
        return {}
    media_list = ",".join(f"'{media_uuid}'" for media_uuid in sorted(set(media_uuids)))
    query = f"""
    SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)
    FROM (
        SELECT
            fds.media_uuid::text AS media_uuid,
            po.person_id::text AS person_id,
            po.representative_faces,
            po.all_faces_route_data
        FROM person_objects po
        JOIN face_detection_sessions fds
          ON fds.session_uuid = po.session_uuid
        WHERE fds.media_uuid IN ({media_list})
    ) t;
    """
    rows = run_psql_json(VISION_DB, query) or []
    grouped: Dict[str, List[VisionCandidate]] = defaultdict(list)
    for row in rows:
        candidate = VisionCandidate(**row)
        grouped[candidate.media_uuid].append(candidate)
    return grouped


def load_all_vision_person_ids() -> set[str]:
    query = "SELECT COALESCE(json_agg(person_id::text), '[]'::json) FROM person_objects;"
    rows = run_psql_json(VISION_DB, query) or []
    return set(rows)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def apply_repairs(repairs: Sequence[Tuple[AppearanceRow, VisionCandidate]]) -> int:
    updated = 0
    for appearance, candidate in repairs:
        query = f"""
        UPDATE individual_video_appearances
        SET person_object_uuid = {sql_literal(candidate.person_id)}::uuid
        WHERE individual_uuid = {sql_literal(appearance.individual_uuid)}::uuid
          AND video_uuid = {sql_literal(appearance.video_uuid)}::uuid
          AND person_object_uuid = {sql_literal(appearance.person_object_uuid)}::uuid;
        """
        run_psql_exec(VMETA_DB, query)
        updated += 1
    return updated


def build_report(limit: Optional[int], apply: bool) -> int:
    rows = load_appearance_rows(limit)
    all_vision_person_ids = load_all_vision_person_ids()

    candidate_rows = [
        row for row in rows if row.person_object_uuid not in all_vision_person_ids
    ]
    media_candidates = load_vision_candidates([row.video_uuid for row in candidate_rows])

    stats = defaultdict(int)
    repairs: List[Tuple[AppearanceRow, VisionCandidate]] = []
    samples: List[Dict[str, str]] = []

    for row in candidate_rows:
        stats["candidate_rows"] += 1
        refs = extract_face_refs(row.representative_faces)
        if not refs:
            stats["missing_face_refs"] += 1
            continue

        candidates = media_candidates.get(row.video_uuid, [])
        if not candidates:
            stats["no_vision_candidates_for_media"] += 1
            continue

        candidate, reason = choose_candidate(refs, candidates)
        if candidate is None:
            stats[reason] += 1
            continue

        stats["repairable"] += 1
        repairs.append((row, candidate))
        if len(samples) < 10:
            samples.append(
                {
                    "video_uuid": row.video_uuid,
                    "individual_uuid": row.individual_uuid,
                    "old_person_object_uuid": row.person_object_uuid,
                    "new_person_id": candidate.person_id,
                }
            )

    print(json.dumps(
        {
            "dry_run": not apply,
            "limit": limit,
            "rows_with_representative_faces": len(rows),
            "rows_missing_direct_vision_match": len(candidate_rows),
            "stats": dict(sorted(stats.items())),
            "sample_repairs": samples,
        },
        indent=2,
    ))

    if apply and repairs:
        updated = apply_repairs(repairs)
        print(json.dumps({"applied_updates": updated}, indent=2))
        return updated
    return 0


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        build_report(limit=args.limit, apply=args.apply)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))