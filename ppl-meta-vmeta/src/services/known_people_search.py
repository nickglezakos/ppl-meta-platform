"""
Read-only search for known MVR people across recorded video and/or instant
detection logs. Unlike group camera-search, this never inserts merge hierarchy
rows.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

import httpx
import numpy as np

logger = logging.getLogger(__name__)

NORMALIZE_MVR_SQL = """
    WITH input_mvr AS (
        SELECT unnest($1::text[]::uuid[]) AS mvr_uuid
    ),
    normalized AS (
        SELECT im.mvr_uuid
        FROM input_mvr im
        WHERE NOT EXISTS (
            SELECT 1 FROM mvr_merge_hierarchy mh
            WHERE mh.merged_mvr_uuid = im.mvr_uuid
        )
        UNION
        SELECT mh.super_individual_uuid AS mvr_uuid
        FROM input_mvr im
        INNER JOIN mvr_merge_hierarchy mh ON mh.merged_mvr_uuid = im.mvr_uuid
    )
    SELECT DISTINCT mvr_uuid FROM normalized
"""

TOP_EMBEDDINGS_SQL = """
    WITH super_individual_hierarchy AS (
        SELECT mvr_people_uuid, face_quality, face_embedding, created_at,
               'super_individual' as source
        FROM mvr_people
        WHERE mvr_people_uuid = $1
          AND COALESCE(is_archived, FALSE) = FALSE
        UNION
        SELECT mp.mvr_people_uuid, mp.face_quality, mp.face_embedding,
               mp.created_at, 'merged_child' as source
        FROM mvr_people mp
        JOIN mvr_merge_hierarchy mh ON mh.merged_mvr_uuid = mp.mvr_people_uuid
        WHERE mh.super_individual_uuid = $1
          AND COALESCE(mp.is_archived, FALSE) = FALSE
    )
    SELECT mvr_people_uuid, face_embedding, face_quality, source
    FROM super_individual_hierarchy
    WHERE face_embedding IS NOT NULL
      AND (face_quality IS NULL OR face_quality >= 0.6)
    ORDER BY face_quality DESC NULLS LAST, created_at DESC
    LIMIT 3
"""


def _parse_pgvector(embedding_str: Any) -> np.ndarray:
    if isinstance(embedding_str, (list, tuple)):
        return np.array([float(x) for x in embedding_str], dtype=float)
    if isinstance(embedding_str, np.ndarray):
        return embedding_str.astype(float)
    text = str(embedding_str).strip()
    if text.startswith("["):
        text = text.strip("[]")
    values = [float(x) for x in text.split(",") if x.strip()]
    return np.array(values, dtype=float)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _auth_headers(auth_token: Optional[str]) -> Dict[str, str]:
    if not auth_token:
        return {}
    token = auth_token.replace("Bearer ", "").strip() if auth_token.startswith("Bearer ") else auth_token
    return {"Authorization": f"Bearer {token}"}


class KnownPeopleSearchService:
    def __init__(self, pool, media_service_url: Optional[str] = None):
        self.pool = pool
        self.media_service_url = (
            media_service_url
            or os.getenv("MEDIA_SERVICE_URL", "http://ppl-meta-media:8000")
        )

    async def search(
        self,
        mvr_people_uuids: List[str],
        sources: List[str],
        start_time: datetime,
        end_time: datetime,
        camera_ids: Optional[List[str]] = None,
        camera_device_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.6,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_uuid = f"known_people_search_{uuid4()}"
        known_uuids = [u.strip() for u in mvr_people_uuids if u and str(u).strip()]
        if not known_uuids:
            return self._empty_response(
                session_uuid, start_time, end_time, sources, known_uuids, []
            )

        start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

        normalized, unsearchable, known_embeddings = await self._prepare_known(
            known_uuids
        )
        matched_by_known: Dict[str, Dict[str, Any]] = {
            uid: {
                "mvr_people_uuid": uid,
                "appearances": [],
                "instant_mvrs": [],
                "best_similarity": 0.0,
                "data_sources": set(),
            }
            for uid in normalized
        }

        want_recording = "recording" in sources
        want_instant = "instant_detection" in sources

        if want_recording and known_embeddings:
            await self._search_recording(
                matched_by_known=matched_by_known,
                known_embeddings=known_embeddings,
                camera_ids=camera_ids or [],
                start_time=start_naive,
                end_time=end_naive,
                similarity_threshold=similarity_threshold,
                auth_token=auth_token,
            )

        if want_instant and known_embeddings:
            await self._search_instant(
                matched_by_known=matched_by_known,
                known_embeddings=known_embeddings,
                camera_device_ids=camera_device_ids or [],
                start_time=start_time,
                end_time=end_time,
                similarity_threshold=similarity_threshold,
                auth_token=auth_token,
            )

        matched_people = []
        for uid, bucket in matched_by_known.items():
            if not bucket["appearances"] and not bucket["instant_mvrs"]:
                continue
            matched_people.append(
                {
                    "mvr_people_uuid": uid,
                    "appearances": bucket["appearances"],
                    "instant_mvrs": bucket["instant_mvrs"],
                    "best_similarity": bucket["best_similarity"],
                    "data_sources": sorted(bucket["data_sources"]),
                    "total_appearances": len(bucket["appearances"]),
                }
            )

        return {
            "search_session_uuid": session_uuid,
            "search_window": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            "sources": sources,
            "requested_mvr_people_uuids": known_uuids,
            "normalized_mvr_people_uuids": sorted(normalized),
            "unsearchable_mvr_uuids": unsearchable,
            "members_found": len(matched_people),
            "matched_people": matched_people,
        }

    def _empty_response(
        self,
        session_uuid: str,
        start_time: datetime,
        end_time: datetime,
        sources: List[str],
        known_uuids: List[str],
        unsearchable: List[str],
    ) -> Dict[str, Any]:
        return {
            "search_session_uuid": session_uuid,
            "search_window": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            "sources": sources,
            "requested_mvr_people_uuids": known_uuids,
            "normalized_mvr_people_uuids": [],
            "unsearchable_mvr_uuids": unsearchable,
            "members_found": 0,
            "matched_people": [],
        }

    async def _prepare_known(
        self, known_uuids: List[str]
    ) -> Tuple[Set[str], List[str], Dict[str, List[Tuple[np.ndarray, float]]]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(NORMALIZE_MVR_SQL, known_uuids)
            normalized = {str(r["mvr_uuid"]) for r in rows}

            known_embeddings: Dict[str, List[Tuple[np.ndarray, float]]] = {}
            unsearchable: List[str] = []
            for uid in normalized:
                emb_rows = await conn.fetch(TOP_EMBEDDINGS_SQL, UUID(uid))
                if not emb_rows:
                    unsearchable.append(uid)
                    continue
                embeddings = []
                for row in emb_rows:
                    try:
                        emb = _parse_pgvector(row["face_embedding"])
                        embeddings.append((emb, float(row["face_quality"] or 0.0)))
                    except Exception as e:
                        logger.warning("Failed to parse embedding for %s: %s", uid, e)
                if embeddings:
                    known_embeddings[uid] = embeddings
                else:
                    unsearchable.append(uid)

        return normalized, unsearchable, known_embeddings

    async def _fetch_videos_for_camera(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: datetime,
        auth_token: Optional[str],
    ) -> List[str]:
        video_uuids: List[str] = []
        page = 1
        page_size = 500
        headers = _auth_headers(auth_token)
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                params = {
                    "collection": camera_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "page_size": page_size,
                    "page": page,
                }
                try:
                    response = await client.get(
                        f"{self.media_service_url}/api/v1/media/search",
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    logger.error(
                        "Media search failed for camera %s page %s: %s",
                        camera_id,
                        page,
                        e,
                    )
                    break

                batch: List[Any]
                if isinstance(data, list):
                    batch = data
                elif isinstance(data, dict):
                    batch = data.get("items") or data.get("results") or data.get("media") or []
                else:
                    batch = []

                for video in batch:
                    uid = video.get("uuid") if isinstance(video, dict) else None
                    if uid:
                        video_uuids.append(str(uid))

                if len(batch) < page_size:
                    break
                page += 1
                if page > 50:
                    break
        return video_uuids

    async def _search_recording(
        self,
        matched_by_known: Dict[str, Dict[str, Any]],
        known_embeddings: Dict[str, List[Tuple[np.ndarray, float]]],
        camera_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        similarity_threshold: float,
        auth_token: Optional[str],
    ) -> None:
        cameras = camera_ids if camera_ids else [None]
        for camera_id in cameras:
            video_uuids: Optional[List[str]] = None
            if camera_id:
                video_uuids = await self._fetch_videos_for_camera(
                    camera_id, start_time, end_time, auth_token
                )
                if not video_uuids:
                    continue

            async with self.pool.acquire() as conn:
                if video_uuids:
                    mvr_rows = await conn.fetch(
                        """
                        SELECT DISTINCT mvr_people_uuid
                        FROM individual_mvr_mapping
                        WHERE individual_uuid IN (
                            SELECT DISTINCT individual_uuid
                            FROM individual_video_appearances
                            WHERE video_uuid = ANY($1::uuid[])
                              AND start_timestamp < $3
                              AND end_timestamp > $2
                        )
                        """,
                        video_uuids,
                        start_time,
                        end_time,
                    )
                else:
                    mvr_rows = await conn.fetch(
                        """
                        SELECT DISTINCT imm.mvr_people_uuid
                        FROM individual_mvr_mapping imm
                        JOIN individual_video_appearances iva
                          ON imm.individual_uuid = iva.individual_uuid
                        WHERE iva.start_timestamp < $2
                          AND iva.end_timestamp > $1
                        """,
                        start_time,
                        end_time,
                    )

                search_raw = [str(r["mvr_people_uuid"]) for r in mvr_rows]
                if not search_raw:
                    continue

                norm_rows = await conn.fetch(NORMALIZE_MVR_SQL, search_raw)
                search_mvr_uuids = {str(r["mvr_uuid"]) for r in norm_rows}

                # Direct UUID intersection
                member_set = set(known_embeddings.keys())
                direct = member_set.intersection(search_mvr_uuids)
                member_to_camera: Dict[str, Dict[str, float]] = defaultdict(dict)
                for uid in direct:
                    member_to_camera[uid][uid] = 1.0

                camera_embeddings: Dict[str, List[Tuple[np.ndarray, float]]] = {}
                for cam_uuid in search_mvr_uuids:
                    rows = await conn.fetch(TOP_EMBEDDINGS_SQL, UUID(cam_uuid))
                    embeddings = []
                    for row in rows:
                        try:
                            embeddings.append(
                                (
                                    _parse_pgvector(row["face_embedding"]),
                                    float(row["face_quality"] or 0.0),
                                )
                            )
                        except Exception:
                            continue
                    if embeddings:
                        camera_embeddings[cam_uuid] = embeddings

                for member_uuid, member_embs in known_embeddings.items():
                    for cam_uuid, cam_embs in camera_embeddings.items():
                        best = 0.0
                        for memb, _ in member_embs:
                            for camb, _ in cam_embs:
                                score = _cosine(memb, camb)
                                if score > best:
                                    best = score
                        if best >= similarity_threshold:
                            member_to_camera[member_uuid][cam_uuid] = best

                if not member_to_camera:
                    continue

                matched_camera_mvrs = set()
                for cams in member_to_camera.values():
                    matched_camera_mvrs.update(cams.keys())

                # Expand to hierarchy children for appearance lookup
                all_mvr = set(matched_camera_mvrs)
                if matched_camera_mvrs:
                    child_rows = await conn.fetch(
                        """
                        SELECT merged_mvr_uuid
                        FROM mvr_merge_hierarchy
                        WHERE super_individual_uuid = ANY($1::uuid[])
                        """,
                        list(matched_camera_mvrs),
                    )
                    all_mvr.update(str(r["merged_mvr_uuid"]) for r in child_rows)

                ind_rows = await conn.fetch(
                    """
                    SELECT individual_uuid, mvr_people_uuid
                    FROM individual_mvr_mapping
                    WHERE mvr_people_uuid = ANY($1::uuid[])
                    """,
                    list(all_mvr),
                )
                individual_uuids = [str(r["individual_uuid"]) for r in ind_rows]
                individual_to_mvr = {
                    str(r["individual_uuid"]): str(r["mvr_people_uuid"]) for r in ind_rows
                }
                if not individual_uuids:
                    continue

                if video_uuids:
                    appearance_rows = await conn.fetch(
                        """
                        SELECT individual_uuid, video_uuid, person_object_uuid,
                               start_timestamp, end_timestamp, confidence
                        FROM individual_video_appearances
                        WHERE individual_uuid = ANY($1::uuid[])
                          AND video_uuid = ANY($2::uuid[])
                          AND start_timestamp < $4
                          AND end_timestamp > $3
                        ORDER BY individual_uuid, start_timestamp ASC
                        """,
                        individual_uuids,
                        video_uuids,
                        start_time,
                        end_time,
                    )
                else:
                    appearance_rows = await conn.fetch(
                        """
                        SELECT individual_uuid, video_uuid, person_object_uuid,
                               start_timestamp, end_timestamp, confidence
                        FROM individual_video_appearances
                        WHERE individual_uuid = ANY($1::uuid[])
                          AND start_timestamp < $3
                          AND end_timestamp > $2
                        ORDER BY individual_uuid, start_timestamp ASC
                        """,
                        individual_uuids,
                        start_time,
                        end_time,
                    )

                # Map camera MVR -> known member (prefer highest similarity)
                camera_to_known: Dict[str, Tuple[str, float]] = {}
                for known_uid, cams in member_to_camera.items():
                    for cam_uid, score in cams.items():
                        prev = camera_to_known.get(cam_uid)
                        if prev is None or score > prev[1]:
                            camera_to_known[cam_uid] = (known_uid, score)

                # Also map children to their super for camera_to_known
                if matched_camera_mvrs:
                    child_map_rows = await conn.fetch(
                        """
                        SELECT merged_mvr_uuid, super_individual_uuid
                        FROM mvr_merge_hierarchy
                        WHERE super_individual_uuid = ANY($1::uuid[])
                           OR merged_mvr_uuid = ANY($1::uuid[])
                        """,
                        list(matched_camera_mvrs),
                    )
                    for row in child_map_rows:
                        child = str(row["merged_mvr_uuid"])
                        super_uid = str(row["super_individual_uuid"])
                        if child not in camera_to_known and super_uid in camera_to_known:
                            camera_to_known[child] = camera_to_known[super_uid]
                        if super_uid not in camera_to_known and child in camera_to_known:
                            camera_to_known[super_uid] = camera_to_known[child]

                for row in appearance_rows:
                    ind_uuid = str(row["individual_uuid"])
                    mvr_uuid = individual_to_mvr.get(ind_uuid)
                    if not mvr_uuid:
                        continue
                    mapping = camera_to_known.get(mvr_uuid)
                    if not mapping:
                        # try normalized
                        continue
                    known_uid, score = mapping
                    bucket = matched_by_known.get(known_uid)
                    if not bucket:
                        continue
                    bucket["appearances"].append(
                        {
                            "individual_uuid": ind_uuid,
                            "video_uuid": str(row["video_uuid"]),
                            "person_object_uuid": str(row["person_object_uuid"]),
                            "timestamp": row["start_timestamp"].isoformat(),
                            "end_timestamp": row["end_timestamp"].isoformat()
                            if row["end_timestamp"]
                            else row["start_timestamp"].isoformat(),
                            "confidence": float(row["confidence"] or score),
                            "camera_id": camera_id,
                            "data_source": "recording",
                        }
                    )
                    bucket["data_sources"].add("recording")
                    if score > bucket["best_similarity"]:
                        bucket["best_similarity"] = score

    async def _fetch_instant_logs(
        self,
        camera_device_id: Optional[str],
        start_time: datetime,
        end_time: datetime,
        auth_token: Optional[str],
    ) -> List[Dict[str, Any]]:
        headers = _auth_headers(auth_token)
        logs: List[Dict[str, Any]] = []
        offset = 0
        limit = 500
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                params: Dict[str, Any] = {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "limit": limit,
                    "offset": offset,
                }
                if camera_device_id:
                    params["camera_device_id"] = camera_device_id
                try:
                    response = await client.get(
                        f"{self.media_service_url}/api/v1/instant-detection-logs",
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    logger.error(
                        "Instant logs fetch failed camera=%s offset=%s: %s",
                        camera_device_id,
                        offset,
                        e,
                    )
                    break

                batch: List[Any]
                if isinstance(data, list):
                    batch = data
                elif isinstance(data, dict):
                    batch = (
                        data.get("logs")
                        or data.get("items")
                        or data.get("results")
                        or []
                    )
                else:
                    batch = []

                for item in batch:
                    if isinstance(item, dict):
                        logs.append(item)

                if len(batch) < limit:
                    break
                offset += limit
                if offset > 10000:
                    break
        return logs

    def _extract_instant_candidates(
        self, log: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        payload = log.get("payload_json") or log.get("payload") or {}
        if isinstance(payload, str):
            import json

            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}

        log_id = log.get("id") or log.get("log_id")
        camera_device_id = log.get("camera_device_id") or payload.get("camera_id")
        flush_start = log.get("flush_started_at") or log.get("started_at")
        flush_end = log.get("flush_ended_at") or log.get("ended_at")

        candidates: List[Dict[str, Any]] = []
        instant_mvrs = payload.get("instant_mvrs") or []
        for record in instant_mvrs:
            if not isinstance(record, dict):
                continue
            emb = record.get("face_embedding")
            if not emb:
                continue
            enriched = dict(record)
            enriched.setdefault("log_id", log_id)
            enriched.setdefault("camera_id", camera_device_id)
            enriched.setdefault("camera_device_id", camera_device_id)
            enriched.setdefault("flush_started_at", flush_start)
            enriched.setdefault("flush_ended_at", flush_end)
            candidates.append(enriched)

        # Also consider hierarchical merge members that may hold embeddings
        merge = payload.get("hierarchical_merge") or {}
        groups = merge.get("merge_groups") or []
        for group in groups:
            if not isinstance(group, dict):
                continue
            for member in group.get("members") or []:
                if not isinstance(member, dict):
                    continue
                emb = member.get("face_embedding")
                if not emb:
                    continue
                enriched = dict(member)
                enriched.setdefault("log_id", log_id)
                enriched.setdefault("camera_id", camera_device_id)
                enriched.setdefault("camera_device_id", camera_device_id)
                enriched.setdefault("flush_started_at", flush_start)
                enriched.setdefault("flush_ended_at", flush_end)
                candidates.append(enriched)

        return candidates

    async def _search_instant(
        self,
        matched_by_known: Dict[str, Dict[str, Any]],
        known_embeddings: Dict[str, List[Tuple[np.ndarray, float]]],
        camera_device_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        similarity_threshold: float,
        auth_token: Optional[str],
    ) -> None:
        devices = camera_device_ids if camera_device_ids else [None]
        for device_id in devices:
            logs = await self._fetch_instant_logs(
                device_id, start_time, end_time, auth_token
            )
            for log in logs:
                for record in self._extract_instant_candidates(log):
                    try:
                        cand_emb = _parse_pgvector(record.get("face_embedding"))
                    except Exception:
                        continue

                    best_known = None
                    best_score = 0.0
                    for known_uid, known_embs in known_embeddings.items():
                        for known_emb, _ in known_embs:
                            score = _cosine(known_emb, cand_emb)
                            if score > best_score:
                                best_score = score
                                best_known = known_uid

                    if best_known is None or best_score < similarity_threshold:
                        continue

                    bucket = matched_by_known.get(best_known)
                    if not bucket:
                        continue

                    log_id = record.get("log_id")
                    video_uuid = (
                        f"instant_log_{log_id}"
                        if log_id is not None
                        else "instant_log_unknown"
                    )
                    ts = (
                        record.get("flush_started_at")
                        or record.get("first_seen")
                        or start_time.isoformat()
                    )
                    if hasattr(ts, "isoformat"):
                        ts = ts.isoformat()

                    person_object_uuid = str(
                        record.get("person_object_uuid")
                        or record.get("instant_mvr_uuid")
                        or uuid4()
                    )
                    individual_uuid = str(
                        record.get("instant_mvr_uuid")
                        or record.get("individual_uuid")
                        or person_object_uuid
                    )

                    bucket["appearances"].append(
                        {
                            "individual_uuid": individual_uuid,
                            "video_uuid": video_uuid,
                            "person_object_uuid": person_object_uuid,
                            "timestamp": ts,
                            "end_timestamp": ts,
                            "confidence": best_score,
                            "camera_id": record.get("camera_device_id")
                            or record.get("camera_id")
                            or device_id,
                            "data_source": "instant_detection",
                            "log_id": log_id,
                        }
                    )
                    instant_payload = dict(record)
                    instant_payload["matched_mvr_people_uuid"] = best_known
                    instant_payload["match_similarity"] = best_score
                    bucket["instant_mvrs"].append(instant_payload)
                    bucket["data_sources"].add("instant_detection")
                    if best_score > bucket["best_similarity"]:
                        bucket["best_similarity"] = best_score
