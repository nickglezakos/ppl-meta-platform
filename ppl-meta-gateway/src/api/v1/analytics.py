"""
Analytics endpoints for MVR people detection insights.

Aggregates camera MVR count data to provide analytics dashboard metrics.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
import httpx

from fastapi import APIRouter, Depends, Query, Request, HTTPException

from core.auth import get_current_user
from core.redis_client import cache_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Service URLs
CAMERAS_SERVICE_URL = "http://localhost:8005"
MEDIA_SERVICE_URL = "http://localhost:8000"
VMETA_SERVICE_URL = "http://localhost:8008"


def _normalize_source_type(source_type: Optional[str]) -> str:
    """Normalize source_type parameter to database column value."""
    if source_type in (None, "recording", "recording_pipeline"):
        return "recording_pipeline"
    if source_type in ("instant_detection",):
        return "instant_detection"
    return "recording_pipeline"  # Safe default


def _parse_time_filter(
    time_filter: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    """
    Parse time filter string into start and end datetime range.
    
    When time_filter is 'custom', start_date and end_date must be provided as ISO 8601 strings.
    
    Args:
        time_filter: One of 'today', 'last_hour', 'last_3_hours', 'last_week', 'last_month', 'custom'
        start_date: ISO 8601 datetime string (required when time_filter='custom')
        end_date: ISO 8601 datetime string (required when time_filter='custom')
    
    Returns:
        Tuple of (start_time, end_time)
    """
    now = datetime.now()
    
    if time_filter == "custom":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required when time_filter is 'custom'")
        start_time = datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=None)
        end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None)
        return start_time, end_time
    elif time_filter == "today":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif time_filter == "last_hour":
        start_time = now - timedelta(hours=1)
        end_time = now
    elif time_filter == "last_3_hours":
        start_time = now - timedelta(hours=3)
        end_time = now
    elif time_filter == "last_week":
        start_time = now - timedelta(days=7)
        end_time = now
    elif time_filter == "last_month":
        start_time = now - timedelta(days=30)
        end_time = now
    else:
        raise ValueError(
            f"Invalid time_filter: {time_filter}. "
            f"Must be one of: today, last_hour, last_3_hours, last_week, last_month, custom"
        )
    
    return start_time, end_time


def _get_collection_identifier(collection: Dict) -> Optional[str]:
    """Return stable collection identifier (UUID-first)."""
    for key in ("uuid", "collection_uuid", "camera_uuid", "id", "collection_name", "name"):
        value = collection.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _get_collection_display_name(collection: Dict) -> str:
    """Return collection display name for UI/debug output."""
    return (
        str(collection.get("collection_name") or "").strip()
        or str(collection.get("name") or "").strip()
        or _get_collection_identifier(collection)
        or "Unknown Collection"
    )


def _get_collection_filter_keys(collection: Dict) -> Set[str]:
    """Return all acceptable identifiers for matching incoming filter values."""
    keys: Set[str] = set()
    for key in (
        "uuid",
        "collection_uuid",
        "camera_uuid",
        "id",
        "collection_name",
        "name",
        "camera_device_id",
        "device_id",
    ):
        value = collection.get(key)
        if value is not None and str(value).strip():
            keys.add(str(value).strip())
    return keys


def _collection_matches_selected_ids(collection: Dict, selected_ids: List[str]) -> bool:
    if not selected_ids:
        return True
    selected = {str(value).strip() for value in selected_ids if str(value).strip()}
    if not selected:
        return True
    return bool(_get_collection_filter_keys(collection).intersection(selected))


def _filter_demographics_count(
    demographics_data: Dict,
    total_count: int,
    selected_genders: Optional[List[str]],
    selected_age_groups: Optional[List[str]],
) -> int:
    """
    Recompute people count based on selected gender/age filters.
    
    When filters are active, returns only the count of people matching ALL active filter criteria.
    Uses the demographic breakdown from the MVR counter response.
    
    Args:
        demographics_data: Demographics dict with total_male, total_female, total_young, etc.
        total_count: Original unfiltered count
        selected_genders: List of genders to include (e.g. ['male']) or None for all
        selected_age_groups: List of age groups to include (e.g. ['young', 'adult']) or None for all
        
    Returns:
        Filtered count
    """
    if not demographics_data:
        return total_count
    
    has_gender_filter = selected_genders and len(selected_genders) > 0
    has_age_filter = selected_age_groups and len(selected_age_groups) > 0
    
    if not has_gender_filter and not has_age_filter:
        return total_count
    
    # Compute gender-filtered count
    if has_gender_filter:
        gender_count = 0
        for g in selected_genders:
            gender_count += demographics_data.get(f"total_{g}", 0)
    else:
        gender_count = total_count
    
    # Compute age-filtered count
    if has_age_filter:
        age_count = 0
        for a in selected_age_groups:
            age_count += demographics_data.get(f"total_{a}", 0)
    else:
        age_count = total_count
    
    # When both filters are present, estimate intersection using proportions
    # (assumes independence between gender and age distributions)
    if has_gender_filter and has_age_filter and total_count > 0:
        gender_ratio = gender_count / total_count
        return int(age_count * gender_ratio)
    elif has_gender_filter:
        return gender_count
    else:
        return age_count


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def _parse_csv_query_values(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or None


def _extract_quality_scores_from_entity(entity: Dict[str, Any]) -> List[float]:
    scores: List[float] = []

    for key in ("quality_score", "face_quality"):
        value = entity.get(key)
        if value is None:
            continue
        try:
            scores.append(float(value))
        except (TypeError, ValueError):
            pass

    quality_metrics = entity.get("quality_metrics") or {}
    if isinstance(quality_metrics, dict):
        for key in ("average_quality", "average_quality_score"):
            value = quality_metrics.get(key)
            if value is None:
                continue
            try:
                scores.append(float(value))
            except (TypeError, ValueError):
                pass

    representative_faces = entity.get("representative_faces") or []
    if isinstance(representative_faces, list):
        for face in representative_faces:
            if not isinstance(face, dict):
                continue
            for key in ("quality_score", "face_quality"):
                value = face.get(key)
                if value is None:
                    continue
                try:
                    scores.append(float(value))
                except (TypeError, ValueError):
                    pass

    deduped_scores: List[float] = []
    for score in scores:
        if score not in deduped_scores:
            deduped_scores.append(score)
    return deduped_scores


def _build_quality_metrics_from_dataset(dataset: Dict[str, Any], time_filter: str) -> Dict[str, Any]:
    mvr_people = [person for person in dataset.get("mvr_people", []) if isinstance(person, dict)]
    quality_scores: List[float] = []
    total_individuals = 0
    mvr_with_quality = 0

    for person in mvr_people:
        merged_people = [
            merged_person
            for merged_person in (person.get("merged_mvr_people") or [])
            if isinstance(merged_person, dict)
        ]
        total_individuals += len(merged_people) if merged_people else 1

        person_scores = _extract_quality_scores_from_entity(person)
        for merged_person in merged_people:
            person_scores.extend(_extract_quality_scores_from_entity(merged_person))

        if person_scores:
            mvr_with_quality += 1
            quality_scores.extend(person_scores)

    total_mvr_people = len(mvr_people)
    mvr_without_quality = max(total_mvr_people - mvr_with_quality, 0)
    average_quality = (
        sum(quality_scores) / len(quality_scores) if quality_scores else None
    )

    quality_std_dev = None
    if quality_scores and len(quality_scores) > 1 and average_quality is not None:
        variance = sum((score - average_quality) ** 2 for score in quality_scores) / len(quality_scores)
        quality_std_dev = variance ** 0.5

    completeness_total = mvr_with_quality + mvr_without_quality
    completeness_percentage = (
        round((mvr_with_quality / completeness_total) * 100, 2)
        if completeness_total > 0
        else 0.0
    )

    return {
        "time_filter": time_filter,
        "collection_name": None,
        "tracking_sessions_count": 1 if dataset.get("search_session_uuid") else 0,
        "total_individuals": total_individuals,
        "total_mvr_people": total_mvr_people,
        "total_videos_processed": len(dataset.get("video_uuids", [])),
        "mvr_with_quality": mvr_with_quality,
        "mvr_without_quality": mvr_without_quality,
        "average_quality": average_quality,
        "min_quality": min(quality_scores) if quality_scores else None,
        "max_quality": max(quality_scores) if quality_scores else None,
        "quality_std_dev": quality_std_dev,
        "data_completeness": {
            "total": completeness_total,
            "with_data": mvr_with_quality,
            "without_data": mvr_without_quality,
            "percentage": completeness_percentage,
        },
        "start_time": dataset.get("start_time").isoformat() if dataset.get("start_time") else None,
        "end_time": dataset.get("end_time").isoformat() if dataset.get("end_time") else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_person_demographics(person: Dict[str, Any]) -> Dict[str, Any]:
    demographics: Dict[str, Any] = {}

    for key in ("demographics", "aggregate_demographics"):
        candidate = person.get(key)
        if isinstance(candidate, dict):
            demographics.update({k: v for k, v in candidate.items() if v is not None})

    direct_fallbacks = {
        "gender": person.get("gender") or person.get("gender_estimate") or person.get("estimated_gender"),
        "age_group": person.get("age_group"),
        "age_min": person.get("age_min"),
        "age_max": person.get("age_max"),
        "age_mean": person.get("age_mean"),
    }
    for key, value in direct_fallbacks.items():
        if demographics.get(key) is None and value is not None:
            demographics[key] = value

    estimated_age = person.get("estimated_age")
    if estimated_age is not None:
        estimated_age_text = str(estimated_age).strip()
        if demographics.get("age_group") is None and estimated_age_text:
            demographics["age_group"] = estimated_age_text.lower()

        if (
            demographics.get("age_mean") is None
            and demographics.get("age_min") is None
            and demographics.get("age_max") is None
            and "-" in estimated_age_text
        ):
            age_parts = [part.strip() for part in estimated_age_text.split("-", 1)]
            try:
                age_min = float(age_parts[0])
                age_max = float(age_parts[1])
            except (TypeError, ValueError):
                pass
            else:
                demographics["age_min"] = age_min
                demographics["age_max"] = age_max
                demographics["age_mean"] = (age_min + age_max) / 2.0

    merged_people = person.get("merged_mvr_people") or []
    if isinstance(merged_people, list) and merged_people:
        gender_votes: Dict[str, int] = defaultdict(int)
        age_means: List[float] = []

        for merged_person in merged_people:
            if not isinstance(merged_person, dict):
                continue

            merged_gender = str(
                merged_person.get("gender")
                or merged_person.get("gender_estimate")
                or merged_person.get("estimated_gender")
                or ""
            ).strip().lower()
            if merged_gender in {"male", "female"}:
                gender_votes[merged_gender] += 1

            merged_age_mean = merged_person.get("age_mean")
            merged_age_min = merged_person.get("age_min")
            merged_age_max = merged_person.get("age_max")
            if merged_age_mean is not None:
                try:
                    age_means.append(float(merged_age_mean))
                except (TypeError, ValueError):
                    pass
            elif merged_age_min is not None and merged_age_max is not None:
                try:
                    age_means.append((float(merged_age_min) + float(merged_age_max)) / 2.0)
                except (TypeError, ValueError):
                    pass

        if demographics.get("gender") is None and gender_votes:
            demographics["gender"] = max(gender_votes.items(), key=lambda item: item[1])[0]

        if demographics.get("age_mean") is None and age_means:
            demographics["age_mean"] = sum(age_means) / len(age_means)

    return demographics


def _resolve_gender(person: Dict[str, Any]) -> str:
    demographics = _extract_person_demographics(person)
    gender = str(
        demographics.get("gender")
        or demographics.get("gender_label")
        or person.get("gender")
        or person.get("gender_estimate")
        or person.get("estimated_gender")
        or "unknown"
    ).strip().lower()
    if gender in {"m", "man", "male"}:
        return "male"
    if gender in {"f", "woman", "female"}:
        return "female"
    if gender in {"male", "female"}:
        return gender
    return "unknown"


def _resolve_age_group(person: Dict[str, Any]) -> str:
    demographics = _extract_person_demographics(person)
    explicit_age_group = str(
        demographics.get("age_group")
        or person.get("age_group")
        or ""
    ).strip().lower()
    if explicit_age_group in {"child", "teen", "minor"}:
        return "young"
    if explicit_age_group in {"young_adult", "young-adult"}:
        return "adult"
    if explicit_age_group in {"young", "adult", "middle_aged", "elderly", "senior", "older_adult", "older-adult"}:
        if explicit_age_group in {"senior", "older_adult", "older-adult"}:
            return "elderly"
        return explicit_age_group

    age_min = demographics.get("age_min")
    age_max = demographics.get("age_max")
    age_mean = demographics.get("age_mean")
    if age_min is None and age_max is None:
        age_min = person.get("age_min")
        age_max = person.get("age_max")

    try:
        if age_mean is not None:
            average_age = float(age_mean)
        elif age_min is not None and age_max is not None:
            average_age = (float(age_min) + float(age_max)) / 2.0
        else:
            return "unknown"
    except (TypeError, ValueError):
        return "unknown"

    if average_age < 18:
        return "young"
    if average_age < 35:
        return "adult"
    if average_age < 55:
        return "middle_aged"
    return "elderly"


def _matches_person_filters(
    person: Dict[str, Any],
    selected_genders: Optional[List[str]],
    selected_age_groups: Optional[List[str]],
) -> bool:
    if selected_genders and _resolve_gender(person) not in selected_genders:
        return False
    if selected_age_groups and _resolve_age_group(person) not in selected_age_groups:
        return False
    return True


def _extract_person_event_timestamps(
    person: Dict[str, Any],
    video_details_by_uuid: Dict[str, Dict[str, Any]],
) -> List[Tuple[datetime, str]]:
    timestamps: List[Tuple[datetime, str]] = []

    for appearance in person.get("appearances", []) or []:
        if not isinstance(appearance, dict):
            continue

        video_uuid = str(appearance.get("video_uuid") or "").strip()
        timestamp = _parse_iso_datetime(appearance.get("start_timestamp") or appearance.get("end_timestamp"))

        if timestamp is None and video_uuid:
            video_meta = video_details_by_uuid.get(video_uuid, {})
            timestamp = video_meta.get("media_timestamp")

        if timestamp is not None:
            timestamps.append((timestamp, video_uuid))

    if timestamps:
        return timestamps

    source_video_uuid = str(person.get("source_media_uuid") or "").strip()
    if source_video_uuid:
        video_meta = video_details_by_uuid.get(source_video_uuid, {})
        fallback_timestamp = video_meta.get("media_timestamp")
        if fallback_timestamp is not None:
            return [(fallback_timestamp, source_video_uuid)]

    return []


async def _fetch_target_collections(
    auth_token: str,
    selected_collection_ids: Optional[List[str]],
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"limit": 1000},
        )

    if response.status_code != 200:
        logger.error("Failed to fetch collections from Media service: %s", response.status_code)
        raise HTTPException(status_code=500, detail="Failed to fetch collections")

    collections = response.json()
    if selected_collection_ids:
        collections = [
            collection
            for collection in collections
            if _collection_matches_selected_ids(collection, selected_collection_ids)
        ]

    return collections


async def _build_recording_pipeline_search_dataset(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    explicit_video_uuids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    selected_collection_ids = _parse_csv_query_values(collection_ids)
    explicit_video_uuids = list(dict.fromkeys(explicit_video_uuids or []))

    if explicit_video_uuids:
        collections = await _fetch_target_collections(auth_token, selected_collection_ids)
        logger.info(
            "Analytics explicit UUID setup: time_filter=%s selected_collection_ids=%s matched_collections=%s explicit_video_count=%s start=%s end=%s",
            time_filter,
            selected_collection_ids,
            [
                {
                    "id": _get_collection_identifier(collection),
                    "name": _get_collection_display_name(collection),
                }
                for collection in collections
            ],
            len(explicit_video_uuids),
            start_time.isoformat(),
            end_time.isoformat(),
        )
    else:
        collections = await _fetch_target_collections(auth_token, selected_collection_ids)
    logger.info(
        "Analytics merged search setup: time_filter=%s selected_collection_ids=%s matched_collections=%s start=%s end=%s",
        time_filter,
        selected_collection_ids,
        [
            {
                "id": _get_collection_identifier(collection),
                "name": _get_collection_display_name(collection),
            }
            for collection in collections
        ],
        start_time.isoformat(),
        end_time.isoformat(),
    )

    if not collections and not explicit_video_uuids:
        return {
            "start_time": start_time,
            "end_time": end_time,
            "collections": [],
            "video_uuids": [],
            "video_details": [],
            "video_details_by_uuid": {},
            "mvr_people": [],
            "search_session_uuid": None,
        }

    video_uuids: List[str] = []
    video_details: List[Dict[str, Any]] = []
    video_details_by_uuid: Dict[str, Dict[str, Any]] = {}
    camera_ids: List[str] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        if explicit_video_uuids:
            collections_by_id: Dict[str, Dict[str, Any]] = {}
            selected_collection_lookup: Dict[str, Dict[str, Any]] = {}
            for collection in collections:
                collection_identifier = _get_collection_identifier(collection)
                if collection_identifier:
                    selected_collection_lookup[collection_identifier] = collection

            for video_uuid in explicit_video_uuids:
                media_response = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/{video_uuid}",
                    headers={"Authorization": f"Bearer {auth_token}"},
                )

                if media_response.status_code != 200:
                    logger.warning(
                        "Failed to fetch media details for explicit video %s: %s",
                        video_uuid,
                        media_response.status_code,
                    )
                    continue

                media = media_response.json()
                media_collections = [
                    collection for collection in (media.get("collections") or []) if isinstance(collection, dict)
                ]
                primary_collection: Dict[str, Any] = {}

                if selected_collection_lookup:
                    for media_collection in media_collections:
                        matched_selected_collection = next(
                            (
                                collection
                                for collection in selected_collection_lookup.values()
                                if _collection_matches_selected_ids(
                                    collection,
                                    [
                                        value
                                        for value in (
                                            str(media_collection.get("uuid") or "").strip(),
                                            str(media_collection.get("name") or "").strip(),
                                            str(media_collection.get("id") or "").strip(),
                                        )
                                        if value
                                    ],
                                )
                            ),
                            None,
                        )
                        if matched_selected_collection:
                            primary_collection = matched_selected_collection
                            break

                if not primary_collection and media_collections:
                    primary_collection = media_collections[0]

                collection_identifier = (
                    str(primary_collection.get("name") or "").strip()
                    or _get_collection_identifier(primary_collection)
                    or str(media.get("camera_device_id") or "").strip()
                    or video_uuid
                )
                collection_name = (
                    str(primary_collection.get("name") or "").strip()
                    or _get_collection_display_name(primary_collection)
                    if primary_collection
                    else collection_identifier
                )
                media_timestamp = _parse_iso_datetime(
                    media.get("start_timestamp")
                    or media.get("created_at")
                    or media.get("media_timestamp")
                )

                if collection_identifier not in collections_by_id:
                    collections_by_id[collection_identifier] = {
                        **primary_collection,
                        "id": collection_identifier,
                        "uuid": primary_collection.get("uuid") or collection_identifier,
                        "name": collection_name,
                    }

                camera_ids.append(collection_identifier)
                video_uuids.append(video_uuid)
                video_details.append({
                    "video_uuid": video_uuid,
                    "camera_id": collection_identifier,
                    "media_timestamp": media_timestamp.isoformat() if media_timestamp else None,
                })
                video_details_by_uuid[video_uuid] = {
                    "video_uuid": video_uuid,
                    "camera_id": collection_identifier,
                    "camera_name": collection_name,
                    "media_timestamp": media_timestamp,
                }

            collections = list(collections_by_id.values())
            logger.info(
                "Analytics explicit UUID fetch: resolved_videos=%s resolved_cameras=%s sample_video_uuids=%s",
                len(video_uuids),
                len(collections),
                video_uuids[:10],
            )
        else:
            for collection in collections:
                collection_identifier = _get_collection_identifier(collection)
                collection_name = _get_collection_display_name(collection)
                collection_uuid = collection.get("uuid") or collection.get("collection_uuid") or collection_identifier

                if not collection_identifier or not collection_uuid:
                    continue

                camera_ids.append(collection_identifier)

                videos_response = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/search",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    params={
                        "collection_id": collection_uuid,
                        "page_size": 500,
                        "start_date": start_time.isoformat(),
                        "end_date": end_time.isoformat(),
                    },
                )

                if videos_response.status_code != 200:
                    logger.warning(
                        "Failed to fetch videos for collection %s: %s",
                        collection_identifier,
                        videos_response.status_code,
                    )
                    continue

                collection_videos = videos_response.json()
                logger.info(
                    "Analytics collection video fetch: collection_id=%s collection_name=%s collection_uuid=%s video_count=%s",
                    collection_identifier,
                    collection_name,
                    collection_uuid,
                    len(collection_videos),
                )

                for video in collection_videos:
                    video_uuid = str(video.get("uuid") or "").strip()
                    if not video_uuid or video_uuid in video_details_by_uuid:
                        continue

                    media_timestamp = _parse_iso_datetime(
                        video.get("created_at")
                        or video.get("media_timestamp")
                        or video.get("uploaded_at")
                    )
                    details = {
                        "video_uuid": video_uuid,
                        "camera_id": collection_identifier,
                        "camera_name": collection_name,
                        "media_timestamp": media_timestamp,
                    }
                    video_uuids.append(video_uuid)
                    video_details.append({
                        "video_uuid": video_uuid,
                        "camera_id": collection_identifier,
                        "media_timestamp": media_timestamp.isoformat() if media_timestamp else None,
                    })
                    video_details_by_uuid[video_uuid] = details

        if not video_uuids:
            return {
                "start_time": start_time,
                "end_time": end_time,
                "collections": collections,
                "video_uuids": [],
                "video_details": [],
                "video_details_by_uuid": {},
                "mvr_people": [],
                "search_session_uuid": None,
            }

        search_response = await client.post(
            f"{VMETA_SERVICE_URL}/api/v1/mvr-people/search/by-videos/persisted-merge-session",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "camera_ids": sorted(set(camera_ids)),
                "video_uuids": video_uuids,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": 500,
                "ignore_existing_session": True,
                "video_details": video_details,
            },
        )
        logger.info(
            "Analytics merged search request: camera_ids=%s total_videos=%s sample_video_uuids=%s",
            sorted(set(camera_ids)),
            len(video_uuids),
            video_uuids[:10],
        )

    if search_response.status_code != 200:
        logger.error(
            "Merged analytics MVR search failed: status=%s body=%s",
            search_response.status_code,
            search_response.text[:500],
        )
        raise HTTPException(status_code=500, detail="Failed to execute analytics MVR search")

    search_data = search_response.json()
    result_payload = search_data.get("result_payload") or {}
    mvr_people = result_payload.get("mvr_people") or []

    return {
        "start_time": start_time,
        "end_time": end_time,
        "collections": collections,
        "video_uuids": video_uuids,
        "video_details": video_details,
        "video_details_by_uuid": video_details_by_uuid,
        "mvr_people": [person for person in mvr_people if isinstance(person, dict)],
        "search_session_uuid": search_data.get("search_session_uuid"),
    }


def _filter_people_for_analytics(
    dataset: Dict[str, Any],
    selected_genders: Optional[List[str]],
    selected_age_groups: Optional[List[str]],
) -> List[Dict[str, Any]]:
    return [
        person
        for person in dataset.get("mvr_people", [])
        if _matches_person_filters(person, selected_genders, selected_age_groups)
    ]


def _build_summary_from_search(
    dataset: Dict[str, Any],
    filtered_people: List[Dict[str, Any]],
    time_filter: str,
) -> Dict[str, Any]:
    total_people = len(filtered_people)
    total_videos = len(dataset.get("video_uuids", []))
    video_details_by_uuid = dataset.get("video_details_by_uuid", {})
    camera_breakdown: Dict[str, Dict[str, Any]] = {}
    gender_counts = {"male": 0, "female": 0, "unknown": 0}
    age_counts = {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0}
    last_detection: Optional[datetime] = None

    for person in filtered_people:
        gender_counts[_resolve_gender(person)] += 1
        age_counts[_resolve_age_group(person)] += 1

        seen_cameras: Set[str] = set()
        for timestamp, video_uuid in _extract_person_event_timestamps(person, video_details_by_uuid):
            if last_detection is None or timestamp > last_detection:
                last_detection = timestamp

            camera_meta = video_details_by_uuid.get(video_uuid, {})
            camera_id = camera_meta.get("camera_id") or "unknown"
            camera_name = camera_meta.get("camera_name") or camera_id
            if camera_id in seen_cameras:
                continue
            seen_cameras.add(camera_id)

            bucket = camera_breakdown.setdefault(
                camera_id,
                {
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "count": 0,
                    "video_count": 0,
                    "demographics": None,
                    "last_detection": None,
                    "cached": False,
                },
            )
            bucket["count"] += 1
            bucket["last_detection"] = max(
                filter(None, [bucket.get("last_detection"), timestamp.isoformat()]),
                default=timestamp.isoformat(),
            )

    videos_per_camera: Dict[str, int] = defaultdict(int)
    for video_meta in video_details_by_uuid.values():
        camera_id = video_meta.get("camera_id")
        if camera_id:
            videos_per_camera[camera_id] += 1
    for camera_id, count in videos_per_camera.items():
        if camera_id in camera_breakdown:
            camera_breakdown[camera_id]["video_count"] = count

    total_gender = sum(gender_counts.values())
    known_age_total = sum(age_counts.values())

    return {
        "total_people": total_people,
        "active_cameras": len(camera_breakdown),
        "total_videos": total_videos,
        "last_detection": last_detection.isoformat() + "Z" if last_detection else None,
        "time_filter": time_filter,
        "demographics": {
            "gender": {
                "male": gender_counts["male"],
                "female": gender_counts["female"],
                "male_percentage": round((gender_counts["male"] / total_gender * 100) if total_gender else 0, 1),
                "female_percentage": round((gender_counts["female"] / total_gender * 100) if total_gender else 0, 1),
            },
            "age": {
                "young": age_counts["young"],
                "adult": age_counts["adult"],
                "middle_aged": age_counts["middle_aged"],
                "elderly": age_counts["elderly"],
                "young_percentage": round((age_counts["young"] / known_age_total * 100) if known_age_total else 0, 1),
                "adult_percentage": round((age_counts["adult"] / known_age_total * 100) if known_age_total else 0, 1),
                "middle_aged_percentage": round((age_counts["middle_aged"] / known_age_total * 100) if known_age_total else 0, 1),
                "elderly_percentage": round((age_counts["elderly"] / known_age_total * 100) if known_age_total else 0, 1),
            },
        },
        "camera_breakdown": list(camera_breakdown.values()),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cached": False,
        "search_session_uuid": dataset.get("search_session_uuid"),
    }


def _build_time_series_from_search(
    dataset: Dict[str, Any],
    filtered_people: List[Dict[str, Any]],
    time_filter: str,
    interval: str,
) -> Dict[str, Any]:
    start_time = dataset["start_time"]
    end_time = dataset["end_time"]
    video_details_by_uuid = dataset.get("video_details_by_uuid", {})

    if interval == "hour":
        total_hours = int((end_time - start_time).total_seconds() / 3600) + 1
        time_buckets = {
            (start_time + timedelta(hours=index)).strftime("%Y-%m-%d %H:00"): {
                "timestamp": (start_time + timedelta(hours=index)).isoformat(),
                "count": 0,
                "video_count": 0,
            }
            for index in range(total_hours)
        }
    else:
        total_days = (end_time.date() - start_time.date()).days + 1
        time_buckets = {
            (start_time + timedelta(days=index)).strftime("%Y-%m-%d"): {
                "timestamp": (start_time + timedelta(days=index)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
                "count": 0,
                "video_count": 0,
            }
            for index in range(total_days)
        }

    seen_videos_by_bucket: Dict[str, Set[str]] = defaultdict(set)

    for person in filtered_people:
        seen_buckets: Set[str] = set()
        for timestamp, video_uuid in _extract_person_event_timestamps(person, video_details_by_uuid):
            bucket_key = timestamp.strftime("%Y-%m-%d %H:00") if interval == "hour" else timestamp.strftime("%Y-%m-%d")
            bucket = time_buckets.get(bucket_key)
            if bucket is None:
                continue

            if bucket_key not in seen_buckets:
                bucket["count"] += 1
                seen_buckets.add(bucket_key)

            if video_uuid and video_uuid not in seen_videos_by_bucket[bucket_key]:
                seen_videos_by_bucket[bucket_key].add(video_uuid)
                bucket["video_count"] += 1

    data_points = list(time_buckets.values())
    counts = [point["count"] for point in data_points]
    total_count = sum(counts)
    peak_count = max(counts) if counts else 0
    peak_time = next((point["timestamp"] for point in data_points if point["count"] == peak_count), None)
    average_count = total_count / len(data_points) if data_points else 0.0

    return {
        "time_filter": time_filter,
        "interval": interval,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data_points": data_points,
        "peak_count": peak_count,
        "peak_time": peak_time,
        "average_count": round(average_count, 2),
        "total_count": total_count,
        "search_session_uuid": dataset.get("search_session_uuid"),
    }


def _build_demographics_from_search(
    dataset: Dict[str, Any],
    filtered_people: List[Dict[str, Any]],
    time_filter: str,
) -> Dict[str, Any]:
    video_details_by_uuid = dataset.get("video_details_by_uuid", {})
    gender_counts = {"male": 0, "female": 0, "unknown": 0}
    age_counts = {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0}
    demographic_matrix = {
        "male": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
        "female": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
        "unknown": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
    }
    camera_breakdown: Dict[str, Dict[str, Any]] = {}

    for person in filtered_people:
        gender = _resolve_gender(person)
        age_group = _resolve_age_group(person)
        gender_counts[gender] += 1
        age_counts[age_group] += 1
        demographic_matrix[gender][age_group] += 1

        seen_cameras: Set[str] = set()
        for _, video_uuid in _extract_person_event_timestamps(person, video_details_by_uuid):
            camera_meta = video_details_by_uuid.get(video_uuid, {})
            camera_id = camera_meta.get("camera_id") or "unknown"
            camera_name = camera_meta.get("camera_name") or camera_id
            if camera_id in seen_cameras:
                continue
            seen_cameras.add(camera_id)
            bucket = camera_breakdown.setdefault(
                camera_id,
                {
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "total_people": 0,
                    "gender": {"male": 0, "female": 0, "unknown": 0},
                    "age": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
                },
            )
            bucket["total_people"] += 1
            bucket["gender"][gender] += 1
            bucket["age"][age_group] += 1

    total_people = len(filtered_people)
    total_age_people = sum(age_counts.values())

    for camera in camera_breakdown.values():
        total_camera_people = camera["total_people"]
        camera["gender"]["male_percentage"] = round((camera["gender"]["male"] / total_camera_people * 100) if total_camera_people else 0, 1)
        camera["gender"]["female_percentage"] = round((camera["gender"]["female"] / total_camera_people * 100) if total_camera_people else 0, 1)
        camera["age"]["young_percentage"] = round((camera["age"]["young"] / total_camera_people * 100) if total_camera_people else 0, 1)
        camera["age"]["adult_percentage"] = round((camera["age"]["adult"] / total_camera_people * 100) if total_camera_people else 0, 1)
        camera["age"]["middle_aged_percentage"] = round((camera["age"]["middle_aged"] / total_camera_people * 100) if total_camera_people else 0, 1)
        camera["age"]["elderly_percentage"] = round((camera["age"]["elderly"] / total_camera_people * 100) if total_camera_people else 0, 1)

    return {
        "time_filter": time_filter,
        "total_people": total_people,
        "gender_distribution": {
            "male": gender_counts["male"],
            "female": gender_counts["female"],
            "unknown": gender_counts["unknown"],
            "male_percentage": round((gender_counts["male"] / total_people * 100) if total_people else 0, 1),
            "female_percentage": round((gender_counts["female"] / total_people * 100) if total_people else 0, 1),
            "unknown_percentage": round((gender_counts["unknown"] / total_people * 100) if total_people else 0, 1),
        },
        "age_distribution": {
            "young": age_counts["young"],
            "adult": age_counts["adult"],
            "middle_aged": age_counts["middle_aged"],
            "elderly": age_counts["elderly"],
            "unknown": age_counts["unknown"],
            "young_percentage": round((age_counts["young"] / total_age_people * 100) if total_age_people else 0, 1),
            "adult_percentage": round((age_counts["adult"] / total_age_people * 100) if total_age_people else 0, 1),
            "middle_aged_percentage": round((age_counts["middle_aged"] / total_age_people * 100) if total_age_people else 0, 1),
            "elderly_percentage": round((age_counts["elderly"] / total_age_people * 100) if total_age_people else 0, 1),
            "unknown_percentage": round((age_counts["unknown"] / total_age_people * 100) if total_age_people else 0, 1),
        },
        "demographic_matrix": demographic_matrix,
        "camera_breakdown": list(camera_breakdown.values()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "search_session_uuid": dataset.get("search_session_uuid"),
    }


def _build_behavioral_from_search(
    dataset: Dict[str, Any],
    filtered_people: List[Dict[str, Any]],
    time_filter: str,
) -> Dict[str, Any]:
    video_details_by_uuid = dataset.get("video_details_by_uuid", {})
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hourly_activity = {hour: 0 for hour in range(24)}
    daily_activity = {day: 0 for day in days_of_week}
    weekly_heatmap = {day: {hour: 0 for hour in range(24)} for day in days_of_week}
    camera_totals: Dict[str, Dict[str, Any]] = {}
    appearances_by_person: Dict[str, int] = defaultdict(int)

    for person in filtered_people:
        person_identifier = str(person.get("mvr_people_uuid") or person.get("person_uuid") or id(person))
        seen_cameras: Set[str] = set()
        seen_hours: Set[int] = set()
        seen_days: Set[str] = set()
        seen_heatmap_cells: Set[Tuple[str, int]] = set()
        for timestamp, video_uuid in _extract_person_event_timestamps(person, video_details_by_uuid):
            hour = timestamp.hour
            day_name = days_of_week[timestamp.weekday()]

            if hour not in seen_hours:
                hourly_activity[hour] += 1
                seen_hours.add(hour)

            if day_name not in seen_days:
                daily_activity[day_name] += 1
                seen_days.add(day_name)

            heatmap_cell = (day_name, hour)
            if heatmap_cell not in seen_heatmap_cells:
                weekly_heatmap[day_name][hour] += 1
                seen_heatmap_cells.add(heatmap_cell)

            appearances_by_person[person_identifier] += 1

            camera_meta = video_details_by_uuid.get(video_uuid, {})
            camera_id = camera_meta.get("camera_id") or "unknown"
            camera_name = camera_meta.get("camera_name") or camera_id
            if camera_id in seen_cameras:
                continue
            seen_cameras.add(camera_id)
            bucket = camera_totals.setdefault(
                camera_id,
                {"camera_id": camera_id, "camera_name": camera_name, "total_people": 0},
            )
            bucket["total_people"] += 1

    hourly_totals = sorted(hourly_activity.items(), key=lambda item: item[1], reverse=True)
    peak_hours = [
        {
            "hour": hour,
            "count": count,
            "time_label": f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00",
        }
        for hour, count in hourly_totals[:5]
        if count > 0
    ]
    daily_totals = sorted(daily_activity.items(), key=lambda item: item[1], reverse=True)
    peak_days = [{"day": day, "count": count} for day, count in daily_totals[:3] if count > 0]
    camera_comparison = sorted(
        list(camera_totals.values()),
        key=lambda item: item["total_people"],
        reverse=True,
    )[:5]

    new_visitors = sum(1 for count in appearances_by_person.values() if count == 1)
    returning_visitors = sum(1 for count in appearances_by_person.values() if count == 2)
    frequent_visitors = sum(1 for count in appearances_by_person.values() if count >= 3)
    total_detections = sum(bucket["total_people"] for bucket in camera_totals.values())

    return {
        "time_filter": time_filter,
        "total_detections": total_detections,
        "active_cameras": len(camera_totals),
        "weekly_heatmap": weekly_heatmap,
        "hourly_activity": hourly_activity,
        "daily_activity": daily_activity,
        "peak_hours": peak_hours,
        "peak_days": peak_days,
        "camera_comparison": camera_comparison,
        "visit_frequency": {
            "new_visitors": new_visitors,
            "returning_visitors": returning_visitors,
            "frequent_visitors": frequent_visitors,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "search_session_uuid": dataset.get("search_session_uuid"),
    }


async def _get_instant_detection_summary(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    genders: Optional[str],
    age_groups: Optional[str],
) -> Dict:
    """Fetch analytics summary from VMeta tracking-sessions/summary for instant detection data."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        logger.error(f"Invalid time filter for instant detection summary: {e}")
        return _empty_summary(time_filter, error=str(e))

    # Determine camera device IDs to query
    camera_device_ids: Optional[str] = None
    if collection_ids:
        camera_device_ids = collection_ids  # Pass through comma-separated
    else:
        # Get all collections from Media to discover camera_device_ids
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    params={"limit": 1000},
                )
                if resp.status_code == 200:
                    collections = resp.json()
                    device_ids = []
                    for col in collections:
                        did = col.get("camera_device_id") or col.get("device_id")
                        if did:
                            device_ids.append(str(did))
                    if device_ids:
                        camera_device_ids = ",".join(device_ids)
        except Exception as e:
            logger.warning(f"Could not fetch collections for instant detection summary: {e}")

    # Call VMeta tracking-sessions/summary
    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if camera_device_ids:
        params["camera_device_ids"] = camera_device_ids

    logger.info(f"📊 Instant detection summary: calling VMeta tracking-sessions/summary with params={params}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta tracking-sessions/summary returned {resp.status_code}: {resp.text[:300]}")
                return _empty_summary(time_filter, error=f"VMeta returned {resp.status_code}")

            data = resp.json()
    except Exception as e:
        logger.error(f"Error calling VMeta tracking-sessions/summary: {e}")
        return _empty_summary(time_filter, error=str(e))

    # Parse demographic filters
    selected_genders = [g.strip() for g in genders.split(",") if g.strip()] if genders else None
    selected_age_groups = [a.strip() for a in age_groups.split(",") if a.strip()] if age_groups else None

    # Build demographics from VMeta response
    vmeta_demographics = data.get("demographics", {})
    gender_male = vmeta_demographics.get("total_male", 0)
    gender_female = vmeta_demographics.get("total_female", 0)
    age_young = vmeta_demographics.get("total_young", 0)
    age_adult = vmeta_demographics.get("total_adult", 0)
    age_elderly = vmeta_demographics.get("total_elderly", 0)

    total_people = data.get("total_individuals", 0) or data.get("total_mvr_people", 0)

    # Apply demographic filters
    if selected_genders:
        if "male" not in selected_genders:
            gender_male = 0
        if "female" not in selected_genders:
            gender_female = 0
    if selected_age_groups:
        if "young" not in selected_age_groups:
            age_young = 0
        if "adult" not in selected_age_groups:
            age_adult = 0
        if "elderly" not in selected_age_groups:
            age_elderly = 0

    if selected_genders or selected_age_groups:
        total_people = _filter_demographics_count(
            vmeta_demographics, total_people, selected_genders, selected_age_groups
        )

    total_gender = gender_male + gender_female
    total_age = age_young + age_adult + age_elderly

    demographics = {
        "gender": {
            "male": gender_male,
            "female": gender_female,
            "male_percentage": round((gender_male / total_gender * 100) if total_gender > 0 else 0, 1),
            "female_percentage": round((gender_female / total_gender * 100) if total_gender > 0 else 0, 1),
        },
        "age": {
            "young": age_young,
            "adult": age_adult,
            "elderly": age_elderly,
            "young_percentage": round((age_young / total_age * 100) if total_age > 0 else 0, 1),
            "adult_percentage": round((age_adult / total_age * 100) if total_age > 0 else 0, 1),
            "elderly_percentage": round((age_elderly / total_age * 100) if total_age > 0 else 0, 1),
        },
    }

    # Build camera breakdown
    camera_breakdown = []
    for cam in data.get("camera_breakdown", []):
        camera_breakdown.append({
            "camera_id": cam.get("camera_device_id", ""),
            "camera_name": cam.get("camera_device_id", ""),
            "count": cam.get("individuals", 0) or cam.get("mvr_people", 0),
            "video_count": 0,  # Not applicable for instant detection
            "demographics": None,
            "last_detection": cam.get("last_detection"),
            "cached": False,
        })

    active_cameras = data.get("active_cameras", 0)

    logger.info(
        f"✅ Instant detection summary: {total_people} people, "
        f"{active_cameras} cameras, {data.get('session_count', 0)} sessions"
    )

    return {
        "total_people": total_people,
        "active_cameras": active_cameras,
        "total_videos": 0,  # Instant detection doesn't produce videos
        "last_detection": data.get("last_detection"),
        "time_filter": time_filter,
        "demographics": demographics,
        "camera_breakdown": camera_breakdown,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cached": False,
        "source_type": "instant_detection",
    }


def _empty_summary(time_filter: str, error: Optional[str] = None) -> Dict:
    """Return an empty analytics summary response."""
    result = {
        "total_people": 0,
        "active_cameras": 0,
        "total_videos": 0,
        "last_detection": None,
        "time_filter": time_filter,
        "demographics": {
            "gender": {"male": 0, "female": 0, "male_percentage": 0.0, "female_percentage": 0.0},
            "age": {"young": 0, "adult": 0, "elderly": 0, "young_percentage": 0.0, "adult_percentage": 0.0, "elderly_percentage": 0.0},
        },
        "camera_breakdown": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cached": False,
    }
    if error:
        result["error"] = error
    return result


@router.get(
    "/analytics/summary",
    summary="Get aggregated analytics summary",
    description="Aggregate MVR people detection data across multiple collections with demographic breakdowns",
)
async def get_analytics_summary(
    request: Request,
    time_filter: str = Query("today", description="Time period filter: today, last_hour, last_3_hours, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    video_uuids: Optional[str] = Query(None, description="Comma-separated explicit video UUIDs"),
    force_refresh: bool = Query(False, description="Bypass cache and get live data"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    genders: Optional[str] = Query(None, description="Comma-separated gender filter: male,female"),
    age_groups: Optional[str] = Query(None, description="Comma-separated age group filter: young,adult,elderly"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'. Default: recording_pipeline"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get aggregated analytics summary across collections.
    """

    _ = force_refresh, current_user

    try:
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        effective_source = _normalize_source_type(source_type)

        if effective_source == "instant_detection":
            return await _get_instant_detection_summary(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                start_date=start_date,
                end_date=end_date,
                genders=genders,
                age_groups=age_groups,
            )

        selected_genders = [g.strip().lower() for g in genders.split(",") if g.strip()] if genders else None
        selected_age_groups = [a.strip().lower() for a in age_groups.split(",") if a.strip()] if age_groups else None
        dataset = await _build_recording_pipeline_search_dataset(
            auth_token,
            time_filter,
            collection_ids,
            start_date,
            end_date,
            explicit_video_uuids=_parse_csv_query_values(video_uuids),
        )
        filtered_people = _filter_people_for_analytics(dataset, selected_genders, selected_age_groups)
        return _build_summary_from_search(dataset, filtered_people, time_filter)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to compute analytics summary: %s", e, exc_info=True)
        return _empty_summary(time_filter, error=str(e))


# ────────────────────────────────────────────────────────────────────
# Instant detection helper functions
# ────────────────────────────────────────────────────────────────────

async def _get_instant_detection_time_series(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    interval: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict:
    """Fetch time-series data from VMeta tracking-sessions/summary for instant detection."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        return {
            "time_filter": time_filter, "interval": interval,
            "start_time": None, "end_time": None,
            "data_points": [], "peak_count": 0, "peak_time": None,
            "average_count": 0.0, "total_count": 0, "error": str(e),
        }

    # Auto-select interval based on range
    range_hours = (end_time - start_time).total_seconds() / 3600
    if range_hours <= 72:
        interval = "hour"
    else:
        interval = "day"

    # Build camera_device_ids
    camera_device_ids = collection_ids  # Pass through if provided

    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if camera_device_ids:
        params["camera_device_ids"] = camera_device_ids

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta tracking-sessions/summary for time-series returned {resp.status_code}")
                data = {}
            else:
                data = resp.json()
    except Exception as e:
        logger.error(f"Error calling VMeta for instant detection time-series: {e}")
        data = {}

    total_count = data.get("total_mvr_people", 0)

    # Build time buckets and distribute count into the most recent bucket
    # (Same simplified approach as recording pipeline; VMeta doesn't provide per-bucket data yet)
    time_buckets = {}
    if interval == "hour":
        total_hours = max(1, int((end_time - start_time).total_seconds() / 3600) + 1)
        for i in range(total_hours):
            bucket_time = start_time + timedelta(hours=i)
            time_buckets[bucket_time.strftime("%Y-%m-%d %H:00")] = {
                "timestamp": bucket_time.isoformat(),
                "count": 0,
                "video_count": 0,
            }
    else:
        total_days = max(1, (end_time - start_time).days + 1)
        for i in range(total_days):
            bucket_time = start_time + timedelta(days=i)
            time_buckets[bucket_time.strftime("%Y-%m-%d")] = {
                "timestamp": bucket_time.replace(hour=0, minute=0, second=0).isoformat(),
                "count": 0,
                "video_count": 0,
            }

    if time_buckets and total_count > 0:
        last_bucket_key = list(time_buckets.keys())[-1]
        time_buckets[last_bucket_key]["count"] = total_count

    data_points = list(time_buckets.values())
    counts = [dp["count"] for dp in data_points]
    peak_count = max(counts) if counts else 0
    average_count = sum(counts) / len(counts) if counts else 0.0
    peak_time = None
    for dp in data_points:
        if dp["count"] == peak_count:
            peak_time = dp["timestamp"]
            break

    return {
        "time_filter": time_filter,
        "interval": interval,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data_points": data_points,
        "peak_count": peak_count,
        "peak_time": peak_time,
        "average_count": round(average_count, 2),
        "total_count": total_count,
        "source_type": "instant_detection",
    }


async def _get_instant_detection_demographics(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    genders: Optional[str],
    age_groups: Optional[str],
) -> Dict:
    """Fetch demographics from VMeta tracking-sessions/summary for instant detection."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if collection_ids:
        params["camera_device_ids"] = collection_ids

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta returned {resp.status_code} for instant detection demographics")
                raise HTTPException(status_code=500, detail="Failed to fetch instant detection demographics")
            data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching instant detection demographics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    vmeta_demo = data.get("demographics", {})
    total_male = vmeta_demo.get("total_male", 0)
    total_female = vmeta_demo.get("total_female", 0)
    total_unknown_gender = 0
    total_young = vmeta_demo.get("total_young", 0)
    total_adult = vmeta_demo.get("total_adult", 0)
    total_middle_aged = 0
    total_elderly = vmeta_demo.get("total_elderly", 0)
    total_unknown_age = 0

    # Apply filters
    selected_genders = [g.strip() for g in genders.split(",") if g.strip()] if genders else None
    selected_age_groups = [a.strip() for a in age_groups.split(",") if a.strip()] if age_groups else None

    if selected_genders:
        if "male" not in selected_genders:
            total_male = 0
        if "female" not in selected_genders:
            total_female = 0
    if selected_age_groups:
        if "young" not in selected_age_groups:
            total_young = 0
        if "adult" not in selected_age_groups:
            total_adult = 0
        if "elderly" not in selected_age_groups:
            total_elderly = 0

    total_people = total_male + total_female + total_unknown_gender

    male_pct = round((total_male / total_people * 100) if total_people > 0 else 0, 1)
    female_pct = round((total_female / total_people * 100) if total_people > 0 else 0, 1)

    total_age_people = total_young + total_adult + total_middle_aged + total_elderly + total_unknown_age
    young_pct = round((total_young / total_age_people * 100) if total_age_people > 0 else 0, 1)
    adult_pct = round((total_adult / total_age_people * 100) if total_age_people > 0 else 0, 1)
    elderly_pct = round((total_elderly / total_age_people * 100) if total_age_people > 0 else 0, 1)

    # Build per-camera breakdown from VMeta camera_breakdown
    camera_demographics = []
    for cam in data.get("camera_breakdown", []):
        cam_id = cam.get("camera_device_id", "")
        cam_people = cam.get("total_mvr_people", 0)
        if cam_people > 0:
            camera_demographics.append({
                "camera_id": cam_id,
                "camera_name": cam_id,
                "total_people": cam_people,
                "gender": {"male": 0, "female": 0, "unknown": 0, "male_percentage": 0.0, "female_percentage": 0.0},
                "age": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0,
                        "young_percentage": 0.0, "adult_percentage": 0.0, "middle_aged_percentage": 0.0, "elderly_percentage": 0.0},
            })

    return {
        "time_filter": time_filter,
        "total_people": total_people,
        "gender_distribution": {
            "male": total_male, "female": total_female, "unknown": total_unknown_gender,
            "male_percentage": male_pct, "female_percentage": female_pct, "unknown_percentage": 0.0,
        },
        "age_distribution": {
            "young": total_young, "adult": total_adult, "middle_aged": total_middle_aged,
            "elderly": total_elderly, "unknown": total_unknown_age,
            "young_percentage": young_pct, "adult_percentage": adult_pct,
            "middle_aged_percentage": 0.0, "elderly_percentage": elderly_pct, "unknown_percentage": 0.0,
        },
        "demographic_matrix": {
            "male": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
            "female": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
            "unknown": {"young": 0, "adult": 0, "middle_aged": 0, "elderly": 0, "unknown": 0},
        },
        "camera_breakdown": camera_demographics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "instant_detection",
    }


async def _get_instant_detection_behavioral(
    auth_token: str,
    time_filter: str,
    collection_ids: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    genders: Optional[str],
    age_groups: Optional[str],
) -> Dict:
    """Fetch behavioral analytics from VMeta tracking-sessions/summary for instant detection."""
    try:
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    params = {
        "source_type": "instant_detection",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if collection_ids:
        params["camera_device_ids"] = collection_ids

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{VMETA_SERVICE_URL}/api/v1/tracking-sessions/summary",
                headers={"Authorization": f"Bearer {auth_token}"},
                params=params,
            )
            if resp.status_code != 200:
                logger.error(f"VMeta returned {resp.status_code} for instant detection behavioral")
                raise HTTPException(status_code=500, detail="Failed to fetch instant detection behavioral data")
            data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching instant detection behavioral: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    total_people = data.get("total_mvr_people", 0)

    # Initialize behavioral structures
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly_heatmap = {day: {hour: 0 for hour in range(24)} for day in days_of_week}
    daily_activity = {day: 0 for day in days_of_week}
    hourly_activity = {hour: 0 for hour in range(24)}

    # Distribute total_people into current time slot (simplified — same as recording path)
    if total_people > 0:
        now = datetime.utcnow()
        current_hour = now.hour
        current_day = days_of_week[now.weekday()]
        hourly_activity[current_hour] = total_people
        daily_activity[current_day] = total_people
        weekly_heatmap[current_day][current_hour] = total_people

    # Build camera comparison from camera_breakdown
    camera_comparison = []
    for cam in data.get("camera_breakdown", []):
        cam_id = cam.get("camera_device_id", "")
        cam_count = cam.get("total_mvr_people", 0)
        if cam_count > 0:
            camera_comparison.append({"camera_id": cam_id, "total_people": cam_count})
    camera_comparison.sort(key=lambda x: x["total_people"], reverse=True)

    peak_hours = sorted(
        [{"hour": h, "count": c, "time_label": f"{h:02d}:00 - {(h + 1) % 24:02d}:00"}
         for h, c in hourly_activity.items() if c > 0],
        key=lambda x: x["count"], reverse=True,
    )[:5]

    peak_days = sorted(
        [{"day": d, "count": c} for d, c in daily_activity.items() if c > 0],
        key=lambda x: x["count"], reverse=True,
    )[:3]

    visit_frequency = {
        "new_visitors": int(total_people * 0.6),
        "returning_visitors": int(total_people * 0.3),
        "frequent_visitors": int(total_people * 0.1),
    }

    return {
        "time_filter": time_filter,
        "total_detections": total_people,
        "active_cameras": len(camera_comparison),
        "weekly_heatmap": weekly_heatmap,
        "hourly_activity": hourly_activity,
        "daily_activity": daily_activity,
        "peak_hours": peak_hours,
        "peak_days": peak_days,
        "camera_comparison": camera_comparison[:5],
        "visit_frequency": visit_frequency,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "instant_detection",
    }


@router.get(
    "/analytics/cameras",
    summary="Get list of collections for analytics filtering",
    description="Returns list of all camera collections from Media service with basic metadata for analytics filter dropdown",
)
async def get_cameras_list(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> List[Dict]:
    """
    Get list of all collections for analytics filtering.
    
    Fetches collections from Media service (where videos are stored) instead of Cameras service.
    This ensures we only show collections that have actual video data.
    
    Returns collection metadata including:
    - id: Collection name (unique identifier)
    - name: Display name
    - collection_name: Collection identifier
    
    Args:
        request: FastAPI request object to extract auth headers
        current_user: Authenticated user from JWT token
        
    Returns:
        List of collection metadata dictionaries
    """
    try:
        # Extract auth token from request headers
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        # Get collections from Media service (where videos/collections are actually stored)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1000}  # Get all collections
            )
            
            if response.status_code == 200:
                collections = response.json()
                
                # Transform to match frontend expectations
                result = []
                seen_collection_ids: Set[str] = set()
                for collection in collections:
                    stable_collection_id = (
                        str(collection.get("collection_name") or "").strip()
                        or str(collection.get("name") or "").strip()
                        or _get_collection_identifier(collection)
                    )
                    collection_id = _get_collection_identifier(collection)
                    collection_name = _get_collection_display_name(collection)
                    if stable_collection_id and stable_collection_id not in seen_collection_ids:
                        seen_collection_ids.add(stable_collection_id)
                        result.append({
                            "id": stable_collection_id,
                            "uuid": str(collection.get("uuid")) if collection.get("uuid") is not None else collection_id,
                            "name": collection_name,
                            "collection_name": str(collection.get("collection_name") or stable_collection_id),
                            "video_count": collection.get("video_count", 0),
                        })
                
                logger.info(f"✅ Returning {len(result)} collections from Media service")
                return result
            else:
                logger.error(f"Failed to get collections from Media service: {response.status_code} - {response.text}")
                return []
        
    except Exception as e:
        logger.error(f"❌ Failed to get collections list: {e}", exc_info=True)
        return []


@router.get(
    "/analytics/time-series",
    summary="Get time-series analytics with hourly/daily trends",
    description="Returns time-based analytics showing people count trends over time with hourly or daily granularity",
)
async def get_time_series_analytics(
    request: Request,
    time_filter: str = Query("today", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs", alias="camera_ids"),
    video_uuids: Optional[str] = Query(None, description="Comma-separated explicit video UUIDs"),
    interval: str = Query("hour", description="Data interval: hour, day"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get time-series analytics with trend data.
    
    Returns people count data points over time for visualization in charts.
    Supports hourly intervals (for today/last 3 days) and daily intervals (for week/month).
    
    Args:
        time_filter: Time period (today, last_3_days, last_week, last_month)
        collection_ids: Optional comma-separated collection IDs
        interval: Data granularity (hour or day)
        current_user: Authenticated user from JWT token
        
    Returns:
        Time series data with data points, peak information, and averages
    """
    _ = current_user

    try:
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        effective_source = _normalize_source_type(source_type)

        if effective_source == "instant_detection":
            return await _get_instant_detection_time_series(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )

        dataset = await _build_recording_pipeline_search_dataset(
            auth_token,
            time_filter,
            collection_ids,
            start_date,
            end_date,
            explicit_video_uuids=_parse_csv_query_values(video_uuids),
        )
        return _build_time_series_from_search(dataset, dataset.get("mvr_people", []), time_filter, interval)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get time-series analytics: %s", e, exc_info=True)
        return {
            "time_filter": time_filter,
            "interval": interval,
            "start_time": None,
            "end_time": None,
            "data_points": [],
            "peak_count": 0,
            "peak_time": None,
            "average_count": 0.0,
            "total_count": 0,
            "error": str(e),
        }


@router.get(
    "/analytics/demographics",
    summary="Get demographics breakdown analytics",
    description="Returns detailed demographic distribution data (gender, age) across cameras for Level 3 analytics",
)
async def get_demographics_breakdown(
    request: Request,
    time_filter: str = Query("today", description="Time filter: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs", alias="camera_ids"),
    video_uuids: Optional[str] = Query(None, description="Comma-separated explicit video UUIDs"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    genders: Optional[str] = Query(None, description="Comma-separated gender filter: male,female"),
    age_groups: Optional[str] = Query(None, description="Comma-separated age group filter: young,adult,elderly"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get detailed demographic breakdowns (Level 3 Analytics).
    
    Returns:
        - Gender distribution (male, female, unknown counts and percentages)
        - Age distribution (young, adult, middle_aged, elderly counts and percentages)
        - Combined demographic matrix (gender x age breakdown)
        - Per-camera demographic breakdown
    """
    _ = current_user

    try:
        auth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        effective_source = _normalize_source_type(source_type)

        if effective_source == "instant_detection":
            return await _get_instant_detection_demographics(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                start_date=start_date,
                end_date=end_date,
                genders=genders,
                age_groups=age_groups,
            )

        selected_genders = [g.strip().lower() for g in genders.split(",") if g.strip()] if genders else None
        selected_age_groups = [a.strip().lower() for a in age_groups.split(",") if a.strip()] if age_groups else None
        dataset = await _build_recording_pipeline_search_dataset(
            auth_token,
            time_filter,
            collection_ids,
            start_date,
            end_date,
            explicit_video_uuids=_parse_csv_query_values(video_uuids),
        )
        filtered_people = _filter_people_for_analytics(dataset, selected_genders, selected_age_groups)
        return _build_demographics_from_search(dataset, filtered_people, time_filter)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_demographics_breakdown: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch demographics: {str(e)}") from e


@router.get(
    "/analytics/behavioral",
    summary="Get behavioral analytics insights",
    description="Analyze behavioral patterns including visit frequency, weekly heatmaps, and peak activity times",
)
async def get_behavioral_analytics(
    request: Request,
    time_filter: str = Query("last_week", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    video_uuids: Optional[str] = Query(None, description="Comma-separated explicit video UUIDs"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    genders: Optional[str] = Query(None, description="Comma-separated gender filter (male,female)"),
    age_groups: Optional[str] = Query(None, description="Comma-separated age groups (young,adult,middle_aged,elderly)"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get behavioral analytics including:
    - Visit frequency distribution (new, returning, frequent)
    - Weekly activity heatmap (day of week x hour of day)
    - Peak activity times
    - Camera comparison metrics
    
    Args:
        time_filter: Time period for analysis
        collection_ids: Optional comma-separated collection IDs
        current_user: Authenticated user from JWT token
        
    Returns:
        Behavioral analytics data with heatmaps and frequency patterns
    """
    _ = current_user

    try:
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        effective_source = _normalize_source_type(source_type)

        if effective_source == "instant_detection":
            return await _get_instant_detection_behavioral(
                auth_token=auth_token,
                time_filter=time_filter,
                collection_ids=collection_ids,
                start_date=start_date,
                end_date=end_date,
                genders=genders,
                age_groups=age_groups,
            )

        selected_genders = [g.strip().lower() for g in genders.split(",") if g.strip()] if genders else None
        selected_age_groups = [a.strip().lower() for a in age_groups.split(",") if a.strip()] if age_groups else None
        dataset = await _build_recording_pipeline_search_dataset(
            auth_token,
            time_filter,
            collection_ids,
            start_date,
            end_date,
            explicit_video_uuids=_parse_csv_query_values(video_uuids),
        )
        filtered_people = _filter_people_for_analytics(dataset, selected_genders, selected_age_groups)
        return _build_behavioral_from_search(dataset, filtered_people, time_filter)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_behavioral_analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch behavioral analytics: {str(e)}") from e


@router.get(
    "/analytics/quality-metrics",
    summary="Get average face quality metrics by collection",
    description="Returns average image quality from individual objects (not MVR objects) for camera/collection(s)",
)
async def get_quality_metrics(
    request: Request,
    time_filter: str = Query("today", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs (null = all collections)", alias="camera_ids"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get average face quality metrics from individual objects filtered by collection.
    
    **Data Source:** Calculates quality from individual_video_appearances (individual objects, NOT MVR objects)
    
    **Returns:**
    - overall_average_quality: Average quality across ALL filtered collections combined
    - collection_breakdown: Array of per-collection quality metrics, each containing:
      - collection_name: Name of the collection/camera
      - average_quality: Average quality for THIS collection only
      - individual_count: Number of individuals in this collection
      - min_quality, max_quality, quality_std_dev: Distribution statistics
    - Quality distribution statistics across all collections
    
    **Multi-Collection Behavior:**
    When multiple collections are filtered, returns:
    1. Overall average quality aggregated across all collections (weighted by individual count)
    2. Separate average quality for each individual collection in the breakdown array
    
    Args:
        request: FastAPI request object to extract auth headers
        time_filter: Time period for filtering individuals
        collection_ids: Optional comma-separated collection IDs (null = all collections)
        current_user: Authenticated user from JWT token
        
    Returns:
        Dict containing:
        - overall_average_quality: Weighted average across all filtered collections
        - collection_breakdown: Per-collection metrics array
        - total_individuals: Total count across all collections
        - active_collections: Number of collections with data
    """
    try:
        logger.info(f"📊 Fetching quality metrics (time_filter: {time_filter}, collections: {collection_ids})")
        
        # Extract auth token from request headers
        auth_header = request.headers.get("authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""
        
        # Parse time filter
        start_time, end_time = _parse_time_filter(time_filter, start_date, end_date)
        
        # Parse collection IDs
        selected_collection_ids = None
        if collection_ids:
            selected_collection_ids = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]
            logger.info(f"📋 Quality metrics filtering by collection_ids: {selected_collection_ids}")
        else:
            logger.info(f"📋 Quality metrics fetching ALL collections (no filter provided)")
        
        # Get collections list from Media service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1000}
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch collections list: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch collections")
            
            all_cameras = response.json()
            logger.info(f"📊 Got {len(all_cameras)} total collections from Media service")
        
        # Filter cameras if specific ones requested
        if selected_collection_ids:
            before_filter = len(all_cameras)
            all_cameras = [
                cam for cam in all_cameras
                if _collection_matches_selected_ids(cam, selected_collection_ids)
            ]
            logger.info(f"🔍 Filtered {before_filter} collections down to {len(all_cameras)} matching filter")
            if len(all_cameras) > 0:
                logger.info(f"✅ Matched collections: [{', '.join(_get_collection_identifier(cam) or 'unknown' for cam in all_cameras)}]")
            else:
                logger.warning(
                    f"⚠️  NO collections matched filter! Available collections: "
                    f"{[_get_collection_identifier(cam) or _get_collection_display_name(cam) for cam in response.json()[:5]]}"
                )
        else:
            logger.info(f"📊 Processing all {len(all_cameras)} collections (no filter)")
        
        # Query vmeta service for quality metrics per collection
        collection_quality_data = []
        total_individuals = 0
        overall_quality_sum = 0.0
        overall_quality_count = 0
        
        VMETA_SERVICE_URL = "http://localhost:8008"
        
        for idx, camera in enumerate(all_cameras, 1):
            collection_name = camera.get("collection_name") or camera.get("name")
            if not collection_name:
                logger.warning(f"⚠️  Skipping camera #{idx} - no collection_name or name field")
                continue
            
            logger.info(f"📡 [{idx}/{len(all_cameras)}] Fetching quality metrics for: {collection_name}")
            
            try:
                # Query vmeta service for quality metrics
                async with httpx.AsyncClient(timeout=30.0) as client:
                    vmeta_url = f"{VMETA_SERVICE_URL}/api/v1/individuals/quality-metrics"
                    response = await client.get(
                        vmeta_url,
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={
                            "collection_name": collection_name,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat()
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        avg_quality = data.get("average_quality", 0.0)
                        individual_count = data.get("individual_count", 0)
                        
                        if individual_count > 0:
                            collection_quality_data.append({
                                "collection_name": collection_name,
                                "average_quality": round(avg_quality, 2),
                                "individual_count": individual_count,
                                "min_quality": round(data.get("min_quality", 0.0), 2),
                                "max_quality": round(data.get("max_quality", 0.0), 2),
                                "quality_std_dev": round(data.get("quality_std_dev", 0.0), 2)
                            })
                            
                            total_individuals += individual_count
                            overall_quality_sum += avg_quality * individual_count
                            overall_quality_count += individual_count
                            
                            logger.info(f"   ✅ {collection_name}: avg={avg_quality:.2f}, count={individual_count}")
                        else:
                            logger.info(f"   ⚠️  {collection_name}: No individuals found in time range")
                    
                    elif response.status_code == 404:
                        logger.info(f"   ⚠️  {collection_name}: No data in vmeta")
                    else:
                        logger.warning(f"   ❌ {collection_name}: vmeta returned {response.status_code}")
            
            except httpx.TimeoutException:
                logger.warning(f"   ⏱️  {collection_name}: Request timeout")
            except Exception as e:
                logger.error(f"   ❌ {collection_name}: Error - {e}")
        
        # Calculate overall average
        overall_average_quality = 0.0
        if overall_quality_count > 0:
            overall_average_quality = overall_quality_sum / overall_quality_count
        
        # Sort collections by average quality (descending)
        collection_quality_data.sort(key=lambda x: x["average_quality"], reverse=True)
        
        logger.info(f"✅ Quality metrics aggregation complete: {total_individuals} individuals across {len(collection_quality_data)} collections")
        
        return {
            "time_filter": time_filter,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_individuals": total_individuals,
            "active_collections": len(collection_quality_data),
            "overall_average_quality": round(overall_average_quality, 2),
            "collection_breakdown": collection_quality_data,
            "quality_grade": _get_quality_grade(overall_average_quality),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error in get_quality_metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality metrics: {str(e)}")


def _get_quality_grade(quality: float) -> str:
    """Get quality grade label based on quality score (0-1 scale)."""
    if quality >= 0.8:
        return "Excellent"
    elif quality >= 0.6:
        return "Good"
    elif quality >= 0.4:
        return "Fair"
    elif quality >= 0.2:
        return "Poor"
    else:
        return "Very Poor"


@router.get(
    "/analytics/mvr-quality-metrics",
    summary="Get quality metrics via MVR data tree (RECOMMENDED)",
    description="Returns quality metrics by following MVR -> Individual data hierarchy. Includes all successfully processed data even if representative_faces extraction failed.",
)
async def get_mvr_quality_metrics(
    request: Request,
    time_filter: str = Query("today", description="Time period: today, last_3_days, last_week, last_month, custom"),
    collection_name: Optional[str] = Query(None, description="Collection name filter (null = aggregate all)"),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs", alias="camera_ids"),
    video_uuids: Optional[str] = Query(None, description="Comma-separated explicit video UUIDs"),
    start_date: Optional[str] = Query(None, description="ISO 8601 start datetime (required when time_filter=custom)"),
    end_date: Optional[str] = Query(None, description="ISO 8601 end datetime (required when time_filter=custom)"),
    source_type: Optional[str] = Query(None, description="Data source: 'recording_pipeline' or 'instant_detection'"),
    current_user: dict = Depends(get_current_user),
) -> Dict:
    """
    Get quality metrics following MVR -> Individual data tree.
    
    **This is the RECOMMENDED endpoint** as it uses the correct data access pattern:
    1. Queries tracking sessions for collection + timeframe
    2. Gets individuals and MVR people counts from tracking sessions
    3. Extracts representative_faces from individuals where available
    4. Returns accurate counts matching batch processing results
    
    **Advantages over /analytics/quality-metrics:**
    - Includes ALL successfully processed individuals (not just those with representative_faces)
    - Uses tracking session metadata for accurate counts
    - Shows data completeness (individuals with vs without quality data)
    - Matches continuous pipeline results (individuals_found, unique_mvr_people_count)
    
    **Returns:**
    - total_individuals: Total individuals from tracking sessions
    - total_mvr_people: Total MVR people from tracking sessions  
    - tracking_sessions_count: Number of completed tracking sessions
    - average_quality: Average quality from available representative_faces
    - data_completeness: Percentage of individuals with quality data
    
    Args:
        request: FastAPI request object
        time_filter: Time period filter
        collection_name: Optional collection name filter
        current_user: Authenticated user
        
    Returns:
        Comprehensive quality metrics following MVR data tree
    """
    try:
        explicit_video_uuid_list = _parse_csv_query_values(video_uuids)

        # Get time range based on filter
        if time_filter == "custom" and start_date and end_date:
            start_time = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end_time = datetime.now(timezone.utc)
            if time_filter == "today":
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == "last_3_days":
                start_time = end_time - timedelta(days=3)
            elif time_filter == "last_week":
                start_time = end_time - timedelta(days=7)
            elif time_filter == "last_month":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        logger.info(
            f"📊 MVR Quality Metrics (time_filter: {time_filter}, collection: {collection_name or 'ALL'}, camera_ids: {collection_ids or 'none'})"
        )
        
        effective_source = _normalize_source_type(source_type)

        if explicit_video_uuid_list and effective_source == "recording_pipeline":
            auth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
            dataset = await _build_recording_pipeline_search_dataset(
                auth_token,
                time_filter,
                collection_ids,
                start_date,
                end_date,
                explicit_video_uuids=explicit_video_uuid_list,
            )
            metrics = _build_quality_metrics_from_dataset(dataset, time_filter)
            metrics["quality_grade"] = _get_quality_grade(metrics.get("average_quality") or 0.0)
            metrics["generated_at"] = datetime.now(timezone.utc).isoformat()
            metrics["data_source"] = "MVR search by explicit video UUIDs"
            return metrics
        
        vmeta_url = f"{VMETA_SERVICE_URL}/api/v1/mvr/quality-metrics"
        headers = {"Authorization": request.headers.get("Authorization")}

        async def _fetch_vmeta_quality(target_collection_name: Optional[str]) -> Dict:
            params = {
                "collection_name": target_collection_name or "all",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }
            if effective_source != "recording_pipeline":
                params["source_type"] = effective_source
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(vmeta_url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

        metrics: Dict
        if collection_ids:
            selected_ids = [cid.strip() for cid in collection_ids.split(",") if cid.strip()]

            async with httpx.AsyncClient(timeout=30.0) as client:
                collections_response = await client.get(
                    f"{MEDIA_SERVICE_URL}/api/v1/media/collections",
                    headers={"Authorization": request.headers.get("Authorization")},
                    params={"limit": 1000},
                )

            if collections_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch collections for MVR quality filtering")

            all_collections = collections_response.json()
            matched_collections = [
                cam for cam in all_collections
                if _collection_matches_selected_ids(cam, selected_ids)
            ]

            matched_collection_names = list({
                str(cam.get("collection_name") or cam.get("name"))
                for cam in matched_collections
                if cam.get("collection_name") or cam.get("name")
            })

            if not matched_collection_names:
                metrics = {
                    "time_filter": time_filter,
                    "collection_name": None,
                    "tracking_sessions_count": 0,
                    "total_individuals": 0,
                    "total_mvr_people": 0,
                    "total_videos_processed": 0,
                    "mvr_with_quality": 0,
                    "mvr_without_quality": 0,
                    "average_quality": None,
                    "min_quality": None,
                    "max_quality": None,
                    "quality_std_dev": None,
                    "data_completeness": {
                        "total": 0,
                        "with_data": 0,
                        "without_data": 0,
                        "percentage": 0.0,
                    },
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                per_collection_metrics = [
                    await _fetch_vmeta_quality(name)
                    for name in matched_collection_names
                ]

                total_tracking_sessions = sum(int(m.get("tracking_sessions_count", 0) or 0) for m in per_collection_metrics)
                total_individuals = sum(int(m.get("total_individuals", 0) or 0) for m in per_collection_metrics)
                total_mvr_people = sum(int(m.get("total_mvr_people", 0) or 0) for m in per_collection_metrics)
                total_videos_processed = sum(int(m.get("total_videos_processed", 0) or 0) for m in per_collection_metrics)
                mvr_with_quality = sum(int(m.get("mvr_with_quality", 0) or 0) for m in per_collection_metrics)
                mvr_without_quality = sum(int(m.get("mvr_without_quality", 0) or 0) for m in per_collection_metrics)

                quality_weight = mvr_with_quality
                weighted_quality_sum = sum(
                    (float(m.get("average_quality", 0.0) or 0.0) * int(m.get("mvr_with_quality", 0) or 0))
                    for m in per_collection_metrics
                )
                average_quality = (weighted_quality_sum / quality_weight) if quality_weight > 0 else None

                min_quality_values = [m.get("min_quality") for m in per_collection_metrics if m.get("min_quality") is not None]
                max_quality_values = [m.get("max_quality") for m in per_collection_metrics if m.get("max_quality") is not None]
                std_weighted_sum = sum(
                    (float(m.get("quality_std_dev", 0.0) or 0.0) * int(m.get("mvr_with_quality", 0) or 0))
                    for m in per_collection_metrics
                )
                quality_std_dev = (std_weighted_sum / quality_weight) if quality_weight > 0 else None

                completeness_total = mvr_with_quality + mvr_without_quality
                completeness_percentage = round((mvr_with_quality / completeness_total) * 100, 2) if completeness_total > 0 else 0.0

                metrics = {
                    "time_filter": time_filter,
                    "collection_name": None,
                    "tracking_sessions_count": total_tracking_sessions,
                    "total_individuals": total_individuals,
                    "total_mvr_people": total_mvr_people,
                    "total_videos_processed": total_videos_processed,
                    "mvr_with_quality": mvr_with_quality,
                    "mvr_without_quality": mvr_without_quality,
                    "average_quality": average_quality,
                    "min_quality": min(min_quality_values) if min_quality_values else None,
                    "max_quality": max(max_quality_values) if max_quality_values else None,
                    "quality_std_dev": quality_std_dev,
                    "data_completeness": {
                        "total": completeness_total,
                        "with_data": mvr_with_quality,
                        "without_data": mvr_without_quality,
                        "percentage": completeness_percentage,
                    },
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
        else:
            metrics = await _fetch_vmeta_quality(collection_name)
        
        logger.info(f"✅ MVR Quality Metrics: {metrics.get('total_individuals')} individuals, "
                   f"{metrics.get('total_mvr_people')} MVR people, "
                   f"quality: {metrics.get('average_quality', 0):.3f}")
        
        # Add quality grade and timestamp
        metrics["quality_grade"] = _get_quality_grade(metrics.get("average_quality", 0))
        metrics["time_filter"] = time_filter
        metrics["generated_at"] = datetime.now(timezone.utc).isoformat()
        metrics["data_source"] = "MVR -> Individual tree (recommended)"
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error in get_mvr_quality_metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch MVR quality metrics: {str(e)}")
