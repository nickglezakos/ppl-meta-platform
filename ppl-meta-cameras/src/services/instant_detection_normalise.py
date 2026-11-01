"""
Instant Detection span normalisation worker.

Loads immutable Media flush logs for a fixed calendar span, merges people the
same way Instant log search does, and upserts derived results under Media
`/instant-detection-logs/normalised/...` without rewriting raw logs.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from src.services.instant_detection_flush import _hierarchical_merge

logger = logging.getLogger(__name__)

DEFAULT_SPAN_SECONDS = int(os.getenv("INSTANT_NORMALISATION_SPAN_SECONDS", "300"))
DEFAULT_MERGE_THRESHOLD = float(
    os.getenv("INSTANT_NORMALISATION_MERGE_THRESHOLD", "0.70")
)
DEFAULT_ENABLED = os.getenv("INSTANT_NORMALISATION_ENABLED", "true").lower() == "true"


def resolve_camera_normalise_settings(camera_device_id: str) -> Dict[str, Any]:
    """
    Load per-camera normalisation settings; fall back to env defaults.
    Returns {enabled, span_seconds, merge_threshold}.
    """
    enabled = DEFAULT_ENABLED
    span_seconds = DEFAULT_SPAN_SECONDS
    merge_threshold = DEFAULT_MERGE_THRESHOLD
    try:
        from src.database import SessionLocal
        from src.models.camera import Camera

        db = SessionLocal()
        try:
            camera = (
                db.query(Camera)
                .filter(Camera.device_id == camera_device_id)
                .first()
            )
            if camera is not None:
                if getattr(camera, "normalise_enabled", None) is not None:
                    enabled = bool(camera.normalise_enabled)
                raw_span = getattr(camera, "normalise_span_seconds", None)
                if raw_span is not None:
                    span_seconds = max(60, min(3600, int(raw_span)))
                raw_thr = getattr(camera, "normalise_merge_threshold", None)
                if raw_thr is not None:
                    merge_threshold = max(0.30, min(0.95, float(raw_thr)))
        finally:
            db.close()
    except Exception as exc:
        logger.warning(
            "resolve_camera_normalise_settings(%s) failed: %s — using env defaults",
            camera_device_id,
            exc,
        )
    return {
        "enabled": enabled,
        "span_seconds": int(span_seconds),
        "merge_threshold": float(merge_threshold),
    }


def _media_base() -> str:
    return os.getenv("MEDIA_SERVICE_URL", "http://localhost:8000").rstrip("/")

def _auth_headers(auth_token: Optional[str]) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = (
            auth_token
            if auth_token.startswith("Bearer ")
            else f"Bearer {auth_token}"
        )
    return headers


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def floor_span_start(dt: datetime, span_seconds: int = DEFAULT_SPAN_SECONDS) -> datetime:
    utc = _as_utc(dt)
    span_seconds = max(1, int(span_seconds))
    epoch = int(utc.timestamp())
    floored = epoch - (epoch % span_seconds)
    return datetime.fromtimestamp(floored, tz=timezone.utc)


def span_window(
    span_start: datetime, span_seconds: int = DEFAULT_SPAN_SECONDS
) -> Tuple[datetime, datetime]:
    start = _as_utc(span_start)
    end = start + timedelta(seconds=max(1, int(span_seconds)))
    return start, end


def iter_span_starts_for_window(
    window_start: datetime,
    window_end: datetime,
    span_seconds: int = DEFAULT_SPAN_SECONDS,
) -> List[datetime]:
    """Calendar spans that overlap [window_start, window_end]."""
    span_seconds = max(1, int(span_seconds))
    start = _as_utc(window_start)
    end = _as_utc(window_end)
    if end < start:
        start, end = end, start
    cursor = floor_span_start(start, span_seconds)
    # Walk back one bucket if flush started mid-span before floored cursor
    if cursor > start:
        cursor = cursor - timedelta(seconds=span_seconds)
    starts: List[datetime] = []
    while cursor < end:
        span_end = cursor + timedelta(seconds=span_seconds)
        if span_end > start and cursor < end:
            starts.append(cursor)
        cursor = span_end
    return starts


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return _as_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except Exception:
        return None


def _mvr_uid(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in (
            "instant_mvr_uuid",
            "mvr_people_uuid",
            "super_individual_uuid",
            "uuid",
            "id",
        ):
            raw = value.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
        return None
    text = str(value).strip()
    return text or None


def _quality(record: Dict[str, Any]) -> float:
    try:
        return float(record.get("quality_score") or record.get("face_quality") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _index_instant_mvrs(raw: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        uid = _mvr_uid(item)
        if not uid:
            continue
        out[uid] = dict(item)
    return out


def _annotate_individual(
    record: Dict[str, Any],
    log: Dict[str, Any],
    *,
    uid: str,
    member_uuids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    out = dict(record)
    out["instant_mvr_uuid"] = uid
    out["mvr_people_uuid"] = out.get("mvr_people_uuid") or uid
    out["flush_log_id"] = log.get("id")
    out["flush_started_at"] = log.get("flush_started_at")
    out["flush_ended_at"] = log.get("flush_ended_at")
    out["camera_id"] = (
        out.get("camera_id") or log.get("camera_device_id") or out.get("camera_device_id")
    )
    out["camera_device_id"] = log.get("camera_device_id") or out.get("camera_device_id")
    out["source"] = "flush_individual"
    if member_uuids:
        out["flush_member_uuids"] = list(member_uuids)
    return out


def collect_flush_body_persons(logs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect body_persons from flush log payloads, preferring longest trajectories."""
    collected: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for log in logs:
        payload = log.get("payload_json") or {}
        if not isinstance(payload, dict):
            continue
        camera_id = str(
            log.get("camera_device_id") or payload.get("camera_id") or ""
        ).strip()
        for person in payload.get("body_persons") or []:
            if not isinstance(person, dict):
                continue
            pid = str(
                person.get("body_person_id")
                or person.get("mvr_people_body_uuid")
                or ""
            ).strip()
            if not pid:
                pid = f"body-flush-{log.get('id')}-{len(collected)}"
            enriched = dict(person)
            enriched["identity_modality"] = "body"
            if camera_id and not enriched.get("camera_id"):
                enriched["camera_id"] = camera_id
            if not enriched.get("flush_log_id"):
                enriched["flush_log_id"] = log.get("id")
            existing = by_id.get(pid)
            if existing is None:
                by_id[pid] = enriched
                collected.append(enriched)
                continue
            if len(enriched.get("route_points") or []) > len(
                existing.get("route_points") or []
            ) or len(enriched.get("bbox_trajectory") or []) > len(
                existing.get("bbox_trajectory") or []
            ):
                idx = collected.index(existing)
                by_id[pid] = enriched
                collected[idx] = enriched
    return collected


def collect_flush_individuals(logs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mirror FE `_collectFlushIndividuals`: merge winners → person_groups → raw mvrs."""
    collected: List[Dict[str, Any]] = []
    seen: set = set()

    for log in logs:
        payload = log.get("payload_json") or {}
        if not isinstance(payload, dict):
            continue
        mvr_by_id = _index_instant_mvrs(payload.get("instant_mvrs"))
        merge = payload.get("hierarchical_merge")
        merge_groups = merge.get("merge_groups") if isinstance(merge, dict) else None

        if isinstance(merge_groups, list) and merge_groups:
            for idx, raw_group in enumerate(merge_groups):
                if not isinstance(raw_group, dict):
                    continue
                group = dict(raw_group)
                super_uid = (
                    _mvr_uid(group.get("super_individual_uuid"))
                    or _mvr_uid(group.get("group_id"))
                    or f"flush-{log.get('id')}-mg-{idx}"
                )
                if super_uid in seen:
                    continue
                members = group.get("members") or group.get("mvr_uuids") or []
                member_uuids: List[str] = []
                winner: Optional[Dict[str, Any]] = None
                if isinstance(members, list):
                    for member in members:
                        uid = _mvr_uid(member)
                        if not uid:
                            continue
                        member_uuids.append(uid)
                        if isinstance(member, dict) and uid == super_uid:
                            winner = dict(member)
                for extra in group.get("merged_mvr_uuids") or []:
                    uid = _mvr_uid(extra)
                    if uid and uid not in member_uuids:
                        member_uuids.append(uid)
                if super_uid not in member_uuids:
                    member_uuids.insert(0, super_uid)

                winner = winner or mvr_by_id.get(super_uid)
                if winner is None and isinstance(members, list):
                    for member in members:
                        if isinstance(member, dict) and member.get("face_embedding") is not None:
                            winner = dict(member)
                            break
                if winner is None and mvr_by_id:
                    winner = dict(max(mvr_by_id.values(), key=_quality))
                if winner is None:
                    winner = {"instant_mvr_uuid": super_uid}

                if winner.get("face_embedding") is None and isinstance(members, list):
                    best_q = -1.0
                    for member in members:
                        if not isinstance(member, dict) or member.get("face_embedding") is None:
                            continue
                        q = _quality(member)
                        if q > best_q:
                            best_q = q
                            winner = dict(member)

                demographics = group.get("demographics")
                if isinstance(demographics, dict) and winner.get("age_gender") is None:
                    winner["age_gender"] = dict(demographics)
                for motion_key in (
                    "speed_mps",
                    "gait_band",
                    "motion_class",
                    "motion_confidence",
                    "average_route_velocity",
                    "speed_samples",
                    "movement_tracking",
                ):
                    if winner.get(motion_key) is None and group.get(motion_key) is not None:
                        winner[motion_key] = group.get(motion_key)

                seen.add(super_uid)
                collected.append(
                    _annotate_individual(
                        winner, log, uid=super_uid, member_uuids=member_uuids
                    )
                )
            continue

        person_groups = payload.get("person_groups")
        if isinstance(person_groups, list) and person_groups:
            for idx, raw_group in enumerate(person_groups):
                if not isinstance(raw_group, dict):
                    continue
                group = dict(raw_group)
                linked: List[str] = []
                for link in group.get("instant_mvr_uuids") or []:
                    uid = _mvr_uid(link)
                    if uid:
                        linked.append(uid)
                member_mvrs = [mvr_by_id[u] for u in linked if u in mvr_by_id]
                best = max(member_mvrs, key=_quality) if member_mvrs else None
                if best is None and mvr_by_id:
                    best = dict(max(mvr_by_id.values(), key=_quality))
                pid = (
                    _mvr_uid(group.get("person_object_uuid"))
                    or (linked[0] if linked else None)
                    or f"flush-{log.get('id')}-pg-{idx}"
                )
                if pid in seen:
                    continue
                record = dict(best or group)
                for motion_key in (
                    "speed_mps",
                    "gait_band",
                    "motion_class",
                    "motion_confidence",
                    "average_route_velocity",
                    "speed_samples",
                    "movement_tracking",
                ):
                    if record.get(motion_key) is None and group.get(motion_key) is not None:
                        record[motion_key] = group.get(motion_key)
                seen.add(pid)
                collected.append(
                    _annotate_individual(record, log, uid=pid, member_uuids=linked)
                )
            continue

        for uid, mvr in mvr_by_id.items():
            if uid in seen:
                continue
            seen.add(uid)
            collected.append(_annotate_individual(dict(mvr), log, uid=uid))

    return collected


def _fetch_flush_logs(
    camera_device_id: str,
    *,
    start_time: datetime,
    end_time: datetime,
    auth_token: Optional[str],
    limit: int = 500,
) -> List[Dict[str, Any]]:
    params = {
        "camera_device_id": camera_device_id,
        "start_time": _as_utc(start_time).isoformat(),
        "end_time": _as_utc(end_time).isoformat(),
        "limit": limit,
        "offset": 0,
    }
    resp = requests.get(
        f"{_media_base()}/api/v1/instant-detection-logs",
        params=params,
        headers=_auth_headers(auth_token),
        timeout=30,
    )
    if resp.status_code != 200:
        logger.warning(
            "normalise: list flush logs failed %s %s",
            resp.status_code,
            resp.text[:200],
        )
        return []
    data = resp.json()
    return data if isinstance(data, list) else []


def _upsert_normalised_span(body: Dict[str, Any], auth_token: Optional[str]) -> Optional[int]:
    resp = requests.put(
        f"{_media_base()}/api/v1/instant-detection-logs/normalised/spans",
        json=body,
        headers=_auth_headers(auth_token),
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        logger.error(
            "normalise: upsert failed %s %s",
            resp.status_code,
            resp.text[:300],
        )
        return None
    return (resp.json() or {}).get("id")


def _build_merged_individuals(
    source_individuals: List[Dict[str, Any]],
    merge_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    by_id = {_mvr_uid(m) or "": dict(m) for m in source_individuals}
    by_id.pop("", None)
    merged: List[Dict[str, Any]] = []
    seen: set = set()
    groups = merge_result.get("merge_groups") or []
    if isinstance(groups, list) and groups:
        for idx, raw_group in enumerate(groups):
            if not isinstance(raw_group, dict):
                continue
            group = dict(raw_group)
            members_raw = group.get("members") or group.get("mvr_uuids") or []
            member_uuids: List[str] = []
            member_records: List[Dict[str, Any]] = []
            if isinstance(members_raw, list):
                for member in members_raw:
                    uid = _mvr_uid(member)
                    if not uid:
                        continue
                    member_uuids.append(uid)
                    if isinstance(member, dict) and member.get("face_embedding") is not None:
                        member_records.append(dict(member))
                    elif uid in by_id:
                        member_records.append(dict(by_id[uid]))
            super_uid = (
                _mvr_uid(group.get("super_individual_uuid"))
                or (member_uuids[0] if member_uuids else None)
                or f"norm-{idx}"
            )
            winner = by_id.get(super_uid)
            if winner is None and member_records:
                winner = max(member_records, key=_quality)
            if winner is None:
                winner = {"instant_mvr_uuid": super_uid}
            else:
                winner = dict(winner)
            for motion_key in (
                "speed_mps",
                "gait_band",
                "motion_class",
                "motion_confidence",
                "average_route_velocity",
                "speed_samples",
                "movement_tracking",
                "demographics",
                "age_gender",
            ):
                if winner.get(motion_key) is None and group.get(motion_key) is not None:
                    winner[motion_key] = group.get(motion_key)
            demographics = group.get("demographics")
            if isinstance(demographics, dict) and winner.get("age_gender") is None:
                winner["age_gender"] = dict(demographics)
            winner["instant_mvr_uuid"] = super_uid
            winner["mvr_people_uuid"] = winner.get("mvr_people_uuid") or super_uid
            winner["flush_member_uuids"] = member_uuids
            winner["source"] = "normalised_individual"
            seen.add(super_uid)
            for uid in member_uuids:
                seen.add(uid)
            merged.append(winner)
        return merged

    supers = merge_result.get("super_individuals") or []
    if isinstance(supers, list) and supers:
        for sid in supers:
            uid = _mvr_uid(sid)
            if not uid or uid in seen:
                continue
            record = dict(by_id.get(uid) or {"instant_mvr_uuid": uid})
            record["instant_mvr_uuid"] = uid
            record["source"] = "normalised_individual"
            seen.add(uid)
            merged.append(record)
        return merged

    for uid, record in by_id.items():
        if uid in seen:
            continue
        out = dict(record)
        out["source"] = "normalised_individual"
        merged.append(out)
    return merged


def normalize_instant_detection_span(
    camera_device_id: str,
    span_start: datetime,
    *,
    merge_threshold: float = DEFAULT_MERGE_THRESHOLD,
    span_seconds: int = DEFAULT_SPAN_SECONDS,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load raw logs overlapping the span, merge people, upsert derived Media row.
    """
    start, end = span_window(span_start, span_seconds)
    logs = _fetch_flush_logs(
        camera_device_id,
        start_time=start,
        end_time=end - timedelta(microseconds=1),
        auth_token=auth_token,
    )
    # Keep only logs whose flush window overlaps [start, end)
    filtered: List[Dict[str, Any]] = []
    source_ids: List[Any] = []
    for log in logs:
        flush_start = _parse_dt(log.get("flush_started_at"))
        flush_end = _parse_dt(log.get("flush_ended_at")) or flush_start
        if flush_start is None:
            continue
        if flush_end is None:
            flush_end = flush_start
        if flush_end < start or flush_start >= end:
            continue
        filtered.append(log)
        if log.get("id") is not None:
            source_ids.append(log.get("id"))

    source_individuals = collect_flush_individuals(filtered)
    merge_result = _hierarchical_merge(
        source_individuals,
        threshold=float(merge_threshold),
        auth_token=auth_token,
    )
    individuals = _build_merged_individuals(source_individuals, merge_result)
    body_persons = collect_flush_body_persons(filtered)
    computed_at = datetime.now(timezone.utc)
    body = {
        "camera_device_id": camera_device_id,
        "span_start": start.isoformat(),
        "span_end": end.isoformat(),
        "span_seconds": int(span_seconds),
        "merge_threshold": float(merge_threshold),
        "people_count": len(individuals),
        "source_log_ids": source_ids,
        "computed_at": computed_at.isoformat(),
        "payload_json": {
            "individuals": individuals,
            "source_individuals": source_individuals,
            "hierarchical_merge": merge_result,
            "body_persons": body_persons,
            "source_log_count": len(filtered),
        },
    }
    row_id = _upsert_normalised_span(body, auth_token)
    return {
        "success": bool(row_id is not None),
        "id": row_id,
        "camera_device_id": camera_device_id,
        "span_start": start.isoformat(),
        "span_end": end.isoformat(),
        "people_count": len(individuals),
        "source_log_ids": source_ids,
        "source_individual_count": len(source_individuals),
    }


def enqueue_normalise_spans_for_flush_window(
    camera_device_id: str,
    *,
    flush_started_at: Optional[datetime],
    flush_ended_at: Optional[datetime],
    auth_token: Optional[str] = None,
    merge_threshold: float = DEFAULT_MERGE_THRESHOLD,
    span_seconds: int = DEFAULT_SPAN_SECONDS,
) -> Dict[str, Any]:
    """Enqueue Celery normalisation for every calendar span touched by a flush."""
    now = datetime.now(timezone.utc)
    start = _as_utc(flush_started_at or now)
    end = _as_utc(flush_ended_at or start)
    starts = iter_span_starts_for_window(start, end, span_seconds)
    queued: List[str] = []
    try:
        from src.tasks.instant_detection_tasks import normalize_instant_detection_span_task

        for span_start in starts:
            normalize_instant_detection_span_task.delay(
                camera_id=camera_device_id,
                span_start_iso=span_start.isoformat(),
                merge_threshold=float(merge_threshold),
                span_seconds=int(span_seconds),
                auth_token=auth_token or "",
            )
            queued.append(span_start.isoformat())
    except Exception as exc:
        logger.warning(
            "normalise enqueue failed for %s: %s — running sync",
            camera_device_id,
            exc,
        )
        results = []
        for span_start in starts:
            results.append(
                normalize_instant_detection_span(
                    camera_device_id,
                    span_start,
                    merge_threshold=merge_threshold,
                    span_seconds=span_seconds,
                    auth_token=auth_token,
                )
            )
        return {
            "queued": False,
            "span_starts": [s.isoformat() for s in starts],
            "results": results,
        }
    return {"queued": True, "span_starts": queued}


def recompute_normalised_range(
    camera_device_id: str,
    *,
    start_time: datetime,
    end_time: datetime,
    merge_threshold: float = DEFAULT_MERGE_THRESHOLD,
    span_seconds: int = DEFAULT_SPAN_SECONDS,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    starts = iter_span_starts_for_window(start_time, end_time, span_seconds)
    return enqueue_normalise_spans_for_flush_window(
        camera_device_id,
        flush_started_at=start_time,
        flush_ended_at=end_time,
        auth_token=auth_token,
        merge_threshold=merge_threshold,
        span_seconds=span_seconds,
    ) | {"span_count": len(starts)}
