"""
Celery tasks for instant detection processing
Runs detection in background workers to avoid blocking the main FastAPI service
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis
import sys
from pathlib import Path
from celery import Task

from src.shared.queue_config import celery_app, redis_client

# Ensure stream operations tasks are registered in the same Celery worker process.
from src.tasks import stream_operations_tasks as _stream_operations_tasks  # noqa: F401

LEGACY_MEDIA_TRIGGER_WEBHOOK_SUFFIX = "/api/v1/triggers/instant-detection"


def _is_legacy_media_trigger_webhook(url: str | None) -> bool:
    if not url:
        return False
    return url.rstrip("/").endswith(LEGACY_MEDIA_TRIGGER_WEBHOOK_SUFFIX)

logger = logging.getLogger(__name__)


INSTANT_DETECTION_BATCH_FLUSH_COUNT = int(
    os.getenv("INSTANT_DETECTION_BATCH_FLUSH_COUNT", "10")
)
INSTANT_DETECTION_BATCH_FLUSH_SECONDS = int(
    os.getenv("INSTANT_DETECTION_BATCH_FLUSH_SECONDS", "30")
)
# Near-real-time only: cycles older than this are dropped, never persisted as live.
INSTANT_DETECTION_BATCH_MAX_AGE_SECONDS = int(
    os.getenv("INSTANT_DETECTION_BATCH_MAX_AGE_SECONDS", "120")
)
INSTANT_DETECTION_BATCH_MAX_LEN = int(
    os.getenv("INSTANT_DETECTION_BATCH_MAX_LEN", "30")
)


def _batch_queue_key(camera_id: str) -> str:
    return f"instant_detection_batch:{camera_id}"


def _batch_oldest_key(camera_id: str) -> str:
    return f"{_batch_queue_key(camera_id)}:oldest_ts"


def _batch_lock_key(camera_id: str) -> str:
    return f"{_batch_queue_key(camera_id)}:flush_lock"


def parse_cycle_timestamp(raw: Any) -> Optional[datetime]:
    """Parse a cycle_timestamp string to aware UTC datetime, or None."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def cycle_age_seconds(
    cycle_timestamp: Any,
    *,
    now: Optional[datetime] = None,
) -> Optional[float]:
    """Age in seconds of a cycle_timestamp, or None if unparseable."""
    parsed = parse_cycle_timestamp(cycle_timestamp)
    if parsed is None:
        return None
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (current - parsed).total_seconds()


def is_cycle_over_max_age(
    cycle_timestamp: Any,
    *,
    max_age_seconds: Optional[int] = None,
    now: Optional[datetime] = None,
) -> bool:
    """True when the cycle is missing/unparseable or older than the max age."""
    limit = (
        INSTANT_DETECTION_BATCH_MAX_AGE_SECONDS
        if max_age_seconds is None
        else max_age_seconds
    )
    age = cycle_age_seconds(cycle_timestamp, now=now)
    if age is None:
        return True
    return age > limit


def _refresh_oldest_ts(camera_id: str) -> None:
    queue_key = _batch_queue_key(camera_id)
    oldest_key = _batch_oldest_key(camera_id)
    next_item = redis_client.lindex(queue_key, 0)
    if not next_item:
        redis_client.delete(oldest_key)
        return
    try:
        parsed = json.loads(next_item)
        ts = parsed.get("cycle_timestamp") or datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        redis_client.set(oldest_key, ts)
    except json.JSONDecodeError:
        redis_client.delete(oldest_key)


def _drop_stale_batch_items(
    camera_id: str,
    *,
    reason: str = "over_age",
    now: Optional[datetime] = None,
) -> int:
    """
    Remove over-age (or malformed) items from the head of the batch queue.

    Returns the number of items dropped.
    """
    queue_key = _batch_queue_key(camera_id)
    dropped = 0
    oldest_dropped_ts: Optional[str] = None
    current = now or datetime.now(timezone.utc)

    while True:
        head = redis_client.lindex(queue_key, 0)
        if not head:
            break
        try:
            parsed = json.loads(head)
        except json.JSONDecodeError:
            redis_client.lpop(queue_key)
            dropped += 1
            continue

        cycle_ts = parsed.get("cycle_timestamp")
        if not is_cycle_over_max_age(cycle_ts, now=current):
            break

        if oldest_dropped_ts is None and cycle_ts is not None:
            oldest_dropped_ts = str(cycle_ts)
        redis_client.lpop(queue_key)
        dropped += 1

    if dropped:
        _refresh_oldest_ts(camera_id)
        logger.warning(
            "🗑️ [CELERY] Dropped stale instant batch items camera_id=%s dropped=%s "
            "oldest_ts=%s reason=%s max_age_seconds=%s",
            camera_id,
            dropped,
            oldest_dropped_ts,
            reason,
            INSTANT_DETECTION_BATCH_MAX_AGE_SECONDS,
        )
    return dropped


def _cap_batch_queue_length(camera_id: str) -> int:
    """Keep only the newest MAX_LEN items. Returns number dropped."""
    queue_key = _batch_queue_key(camera_id)
    length = int(redis_client.llen(queue_key) or 0)
    if length <= INSTANT_DETECTION_BATCH_MAX_LEN:
        return 0

    dropped = length - INSTANT_DETECTION_BATCH_MAX_LEN
    oldest_raw = redis_client.lindex(queue_key, 0)
    oldest_ts = None
    if oldest_raw:
        try:
            oldest_ts = json.loads(oldest_raw).get("cycle_timestamp")
        except json.JSONDecodeError:
            oldest_ts = None

    # Keep the newest MAX_LEN entries (tail of the list).
    redis_client.ltrim(queue_key, -INSTANT_DETECTION_BATCH_MAX_LEN, -1)
    _refresh_oldest_ts(camera_id)
    logger.warning(
        "🗑️ [CELERY] Capped instant batch queue camera_id=%s dropped=%s "
        "oldest_ts=%s reason=over_len max_len=%s",
        camera_id,
        dropped,
        oldest_ts,
        INSTANT_DETECTION_BATCH_MAX_LEN,
    )
    return dropped


def _queue_batch_item(camera_id: str, payload: Dict[str, Any]) -> int:
    queue_key = _batch_queue_key(camera_id)
    oldest_key = _batch_oldest_key(camera_id)

    if is_cycle_over_max_age(payload.get("cycle_timestamp")):
        logger.warning(
            "🗑️ [CELERY] Refusing over-age instant batch enqueue camera_id=%s "
            "cycle_timestamp=%s reason=over_age max_age_seconds=%s",
            camera_id,
            payload.get("cycle_timestamp"),
            INSTANT_DETECTION_BATCH_MAX_AGE_SECONDS,
        )
        _drop_stale_batch_items(camera_id, reason="over_age")
        _cap_batch_queue_length(camera_id)
        return int(redis_client.llen(queue_key) or 0)

    pipe = redis_client.pipeline()
    pipe.rpush(queue_key, json.dumps(payload))
    pipe.setnx(oldest_key, payload["cycle_timestamp"])
    result = pipe.execute()
    _drop_stale_batch_items(camera_id, reason="over_age")
    _cap_batch_queue_length(camera_id)
    return int(redis_client.llen(queue_key) or result[0])


def _should_flush_batch(camera_id: str) -> bool:
    queue_key = _batch_queue_key(camera_id)
    oldest_key = _batch_oldest_key(camera_id)
    queue_length = redis_client.llen(queue_key)
    if queue_length >= INSTANT_DETECTION_BATCH_FLUSH_COUNT:
        return True

    oldest_ts = redis_client.get(oldest_key)
    if not oldest_ts:
        return False

    try:
        oldest_dt = datetime.fromisoformat(oldest_ts.replace("Z", "+00:00"))
        if oldest_dt.tzinfo is None:
            oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - oldest_dt).total_seconds()
        return age_seconds >= INSTANT_DETECTION_BATCH_FLUSH_SECONDS
    except ValueError:
        return True


def _load_batch_items(camera_id: str, limit: int) -> List[Dict[str, Any]]:
    raw_items = redis_client.lrange(_batch_queue_key(camera_id), 0, limit - 1)
    items: List[Dict[str, Any]] = []
    for raw_item in raw_items:
        try:
            items.append(json.loads(raw_item))
        except json.JSONDecodeError:
            logger.warning("⚠️ [CELERY] Skipping malformed instant batch item for %s", camera_id)
    return items


def _trim_batch_items(camera_id: str, count: int) -> None:
    queue_key = _batch_queue_key(camera_id)
    redis_client.ltrim(queue_key, count, -1)
    _refresh_oldest_ts(camera_id)


def _drop_failed_flush_if_stale(camera_id: str, attempted: int) -> int:
    """
    After a persist failure, drop the head batch when its oldest cycle is over max age.

    Fresh failures stay queued for retry; weeks-old backlog is discarded.
    """
    dropped_stale = _drop_stale_batch_items(camera_id, reason="persist_fail_stale")
    if attempted <= 0:
        return dropped_stale

    head = redis_client.lindex(_batch_queue_key(camera_id), 0)
    if not head:
        return dropped_stale

    try:
        parsed = json.loads(head)
    except json.JSONDecodeError:
        redis_client.lpop(_batch_queue_key(camera_id))
        _refresh_oldest_ts(camera_id)
        return dropped_stale + 1

    if not is_cycle_over_max_age(parsed.get("cycle_timestamp")):
        return dropped_stale

    _trim_batch_items(camera_id, attempted)
    logger.warning(
        "🗑️ [CELERY] Dropped failed persist batch after max age camera_id=%s "
        "dropped=%s oldest_ts=%s reason=persist_fail_stale",
        camera_id,
        attempted,
        parsed.get("cycle_timestamp"),
    )
    return dropped_stale + attempted


def _extract_source_identity_uuids(person_objects: List[Dict[str, Any]]) -> List[str]:
    """Extract resolvable identity UUIDs from detection person objects."""
    source_ids: List[str] = []

    def _append_if_uuid(raw_value: Any) -> None:
        if not raw_value:
            return
        try:
            normalized = str(UUID(str(raw_value)))
            if normalized not in source_ids:
                source_ids.append(normalized)
        except Exception:
            return

    for person in person_objects or []:
        if not isinstance(person, dict):
            continue
        _append_if_uuid(person.get("mvr_person_uuid"))
        _append_if_uuid(person.get("person_object_uuid"))
        _append_if_uuid(person.get("individual_uuid"))
        _append_if_uuid(person.get("source_mvr_uuid"))

        for face in person.get("faces", []) or []:
            if not isinstance(face, dict):
                continue
            _append_if_uuid(face.get("mvr_person_uuid"))
            _append_if_uuid(face.get("person_object_uuid"))
            _append_if_uuid(face.get("individual_uuid"))
            _append_if_uuid(face.get("source_mvr_uuid"))

    return source_ids


BODY_POSTURE_HISTORY_MAX = 4
BODY_POSTURE_HISTORY_TTL_SECONDS = 300


def _body_posture_history_key(camera_id: str) -> str:
    return f"instant_body_posture:{camera_id}"


def summarize_body_persons(body_persons: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Compact body-person rows for pub/sub and posture history."""
    summary: List[Dict[str, Any]] = []
    for person in body_persons or []:
        if not isinstance(person, dict):
            continue
        summary.append(
            {
                "body_person_id": person.get("body_person_id"),
                "average_bbox": person.get("average_bbox"),
                "posture": person.get("posture"),
                "posture_confidence": person.get("posture_confidence"),
                "detection_count": person.get("detection_count"),
            }
        )
    return summary


def push_body_posture_history(
    camera_id: str,
    *,
    timestamp: str,
    body_persons: Optional[List[Dict[str, Any]]],
    redis_conn: Optional[Any] = None,
) -> None:
    """
    Append one instant-body cycle to Redis list instant_body_posture:{camera_id}.

    Keeps the last BODY_POSTURE_HISTORY_MAX entries and refreshes TTL.
    """
    summary = summarize_body_persons(body_persons)
    if not summary:
        return
    client = redis_conn or redis_client
    key = _body_posture_history_key(camera_id)
    payload = json.dumps(
        {
            "timestamp": timestamp,
            "camera_id": camera_id,
            "body_persons": summary,
        }
    )
    pipe = client.pipeline()
    pipe.rpush(key, payload)
    pipe.ltrim(key, -BODY_POSTURE_HISTORY_MAX, -1)
    pipe.expire(key, BODY_POSTURE_HISTORY_TTL_SECONDS)
    pipe.execute()


LEFT_OBJECT_HISTORY_MAX = 24
LEFT_OBJECT_HISTORY_TTL_SECONDS = 600


def _left_object_history_key(camera_id: str) -> str:
    return f"instant_left_objects:{camera_id}"


def summarize_objects(objects: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Compact object detections for pub/sub and left_object history."""
    summary: List[Dict[str, Any]] = []
    for det in objects or []:
        if not isinstance(det, dict):
            continue
        bbox = det.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            try:
                bbox = [float(v) for v in bbox[:4]]
            except (TypeError, ValueError):
                bbox = None
        else:
            bbox = None
        summary.append(
            {
                "class_label": det.get("class_label"),
                "class_id": det.get("class_id"),
                "bbox": bbox,
                "confidence": det.get("confidence"),
                "frame_number": det.get("frame_number"),
            }
        )
    return summary


def push_left_object_history(
    camera_id: str,
    *,
    timestamp: str,
    objects: Optional[List[Dict[str, Any]]],
    redis_conn: Optional[Any] = None,
) -> None:
    """Append one object-detection cycle to Redis list instant_left_objects:{camera_id}."""
    summary = summarize_objects(objects)
    client = redis_conn or redis_client
    key = _left_object_history_key(camera_id)
    payload = json.dumps(
        {
            "timestamp": timestamp,
            "camera_id": camera_id,
            "objects": summary,
        }
    )
    pipe = client.pipeline()
    pipe.rpush(key, payload)
    pipe.ltrim(key, -LEFT_OBJECT_HISTORY_MAX, -1)
    pipe.expire(key, LEFT_OBJECT_HISTORY_TTL_SECONDS)
    pipe.execute()


VEHICLE_HISTORY_MAX = 24
VEHICLE_HISTORY_TTL_SECONDS = 600


def _vehicle_history_key(camera_id: str) -> str:
    return f"instant_vehicles:{camera_id}"


def summarize_vehicles(vehicles: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Compact vehicle detections for pub/sub and vehicle_plate history."""
    summary: List[Dict[str, Any]] = []
    for det in vehicles or []:
        if not isinstance(det, dict):
            continue
        bbox = det.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            try:
                bbox = [float(v) for v in bbox[:4]]
            except (TypeError, ValueError):
                bbox = None
        else:
            bbox = None
        plate_bbox = det.get("plate_bbox")
        if isinstance(plate_bbox, (list, tuple)) and len(plate_bbox) >= 4:
            try:
                plate_bbox = [float(v) for v in plate_bbox[:4]]
            except (TypeError, ValueError):
                plate_bbox = None
        else:
            plate_bbox = None
        summary.append(
            {
                "class_label": det.get("class_label"),
                "class_id": det.get("class_id"),
                "bbox": bbox,
                "confidence": det.get("confidence"),
                "frame_number": det.get("frame_number"),
                "plate_text": det.get("plate_text"),
                "plate_confidence": det.get("plate_confidence"),
                "plate_bbox": plate_bbox,
                "plate_ocr_attempted": det.get("plate_ocr_attempted"),
            }
        )
    return summary


def push_vehicle_history(
    camera_id: str,
    *,
    timestamp: str,
    vehicles: Optional[List[Dict[str, Any]]],
    redis_conn: Optional[Any] = None,
) -> None:
    """Append one vehicle-detection cycle to Redis list instant_vehicles:{camera_id}."""
    summary = summarize_vehicles(vehicles)
    client = redis_conn or redis_client
    key = _vehicle_history_key(camera_id)
    payload = json.dumps(
        {
            "timestamp": timestamp,
            "camera_id": camera_id,
            "vehicles": summary,
        }
    )
    pipe = client.pipeline()
    pipe.rpush(key, payload)
    pipe.ltrim(key, -VEHICLE_HISTORY_MAX, -1)
    pipe.expire(key, VEHICLE_HISTORY_TTL_SECONDS)
    pipe.execute()


class InstantDetectionTask(Task):
    """Base task for instant detection with error handling"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 2, 'countdown': 1}
    retry_backoff = True


@celery_app.task(
    bind=True,
    base=InstantDetectionTask,
    name="instant_detection.process_frames",
    queue="instant_detection_queue",
    # Age/gender may need ~45s on cold DeepFace CPU; keep headroom for cache write.
    time_limit=120,
    soft_time_limit=100
)
def process_instant_detection(
    self,
    camera_id: str,
    frames_data: List[str],  # Base64 encoded frames
    timestamp: str
) -> Dict:
    """
    Process instant detection frames in background worker.
    
    Args:
        camera_id: Camera identifier
        frames_data: List of base64 encoded frames (typically 3)
        timestamp: ISO timestamp of detection
        
    Returns:
        Detection results dictionary
    """
    logger.info(f"🎬 [CELERY] Processing instant detection for {camera_id}")
    
    try:
        # Import here to avoid circular dependencies
        from src.services.instant_detection import InstantDetectionSampler
        
        # Create detector instance (lightweight, no state)
        detector = InstantDetectionSampler()
        
        # Process frames
        result = detector._process_frames_sync(camera_id, frames_data)
        
        if result:
            # Add timestamp to result
            from datetime import datetime
            result["timestamp"] = datetime.utcnow().isoformat() + 'Z'
            
            # 🔥 CRITICAL: Cache result in Redis so frontend API can access it
            # (Can't use instance cache since Celery worker and FastAPI are separate processes)
            try:
                import redis
                r = redis.Redis(host=__import__('os').getenv('REDIS_HOST','redis'), port=int(__import__('os').getenv('REDIS_PORT','6379')), decode_responses=False)
                cache_key = f"instant_detection:{camera_id}"
                # Store with 5 minute TTL
                r.setex(cache_key, 300, json.dumps(result))
                logger.info(f"📦 [CELERY] Cached result in Redis for {camera_id} at {result['timestamp']} - frontend API can now access it")
            except Exception as e:
                logger.error(f"❌ [CELERY] Failed to cache in Redis: {e}")
                # Fallback to instance cache (won't work cross-process but better than nothing)
                detector._cache_result(camera_id, result)

            # Buffer cycle faces / InstantMvrs for Y-window flush (no DB yet)
            try:
                from src.services.instant_detection_flush import push_cycle_to_flush_buffer

                buf_len = push_cycle_to_flush_buffer(
                    camera_id,
                    cycle_id=result.get("cycle_id") or result.get("timestamp"),
                    timestamp=result.get("timestamp"),
                    face_detections=result.get("face_detections_for_flush") or [],
                    person_objects=result.get("person_objects") or [],
                    instant_mvrs=result.get("instant_mvrs") or [],
                )
                # Threshold flush from the worker (in case sampler Y-counter missed
                # a stop / restart before cycle_counter % Y).
                flush_y = int(
                    os.getenv("INSTANT_DETECTION_FLUSH_INTERVAL_CYCLES", "12") or 12
                )
                flush_y = max(1, flush_y)
                if buf_len >= flush_y:
                    flush_instant_detection_y_window.delay(
                        camera_id=camera_id,
                        session_uuid=result.get("cycle_id"),
                        auth_token=os.getenv("INTERNAL_SERVICE_TOKEN", ""),
                        flush_interval_cycles=flush_y,
                    )
                    logger.info(
                        "📦 [CELERY] Buffer hit Y=%s for %s (len=%s) — queued flush",
                        flush_y,
                        camera_id,
                        buf_len,
                    )
            except Exception as buf_exc:
                logger.warning(
                    "⚠️ [CELERY] Failed to push flush buffer for %s: %s",
                    camera_id,
                    buf_exc,
                )
            
            # Publish to Redis Pub/Sub
            _publish_to_redis(camera_id, result)
            
            # Push to webhook if configured
            _push_to_webhook(camera_id, result)
            
            logger.info(
                f"✅ [CELERY] Instant detection complete: {camera_id} "
                f"- {result.get('people_count', 0)} people"
            )
            
            return {
                "success": True,
                "camera_id": camera_id,
                "people_count": result.get("people_count", 0),
                "processing_time": result.get("processing_time_seconds", 0)
            }
        else:
            logger.warning(f"⚠️ [CELERY] No detection result for {camera_id}")
            return {"success": False, "camera_id": camera_id, "error": "No result"}
            
    except Exception as e:
        logger.error(f"❌ [CELERY] Instant detection failed: {e}", exc_info=True)
        # Re-raise to trigger retry
        raise


def _publish_to_redis(camera_id: str, result: Dict):
    """Publish instant detection results to Redis Pub/Sub"""
    try:
        demographics = result.get("demographics", {})
        people_count = result.get("people_count", 0)
        body_persons = result.get("body_persons") or []
        body_count = result.get("body_count")
        if body_count is None:
            body_count = len(body_persons)
        objects = result.get("objects") or []
        object_count = result.get("object_count")
        if object_count is None:
            object_count = len(objects)
        source_mvr_uuids = _extract_source_identity_uuids(result.get("person_objects") or [])
        instant_mvrs = result.get("instant_mvrs") or []
        # Compact source embeddings for Vprofile (Redis-only; no DB resolve)
        source_embeddings = []
        for mvr in instant_mvrs:
            emb = mvr.get("face_embedding")
            if not emb:
                continue
            source_embeddings.append(
                {
                    "instant_mvr_uuid": mvr.get("instant_mvr_uuid")
                    or mvr.get("mvr_people_uuid"),
                    "face_embedding": emb,
                    "person_object_uuid": mvr.get("person_object_uuid"),
                }
            )
            uid = mvr.get("instant_mvr_uuid") or mvr.get("mvr_people_uuid")
            if uid and uid not in source_mvr_uuids:
                source_mvr_uuids.append(uid)
        body_summary = summarize_body_persons(body_persons)
        object_summary = summarize_objects(objects)
        vehicles = result.get("vehicles") or []
        vehicle_count = result.get("vehicle_count")
        if vehicle_count is None:
            vehicle_count = len(vehicles)
        vehicle_summary = summarize_vehicles(vehicles)
        ts = result.get("timestamp") or datetime.utcnow().isoformat()

        try:
            push_body_posture_history(
                camera_id,
                timestamp=ts,
                body_persons=body_persons,
            )
        except Exception as hist_exc:
            logger.warning(
                "⚠️ [CELERY] body posture history push failed for %s: %s",
                camera_id,
                hist_exc,
            )
        try:
            push_left_object_history(
                camera_id,
                timestamp=ts,
                objects=objects,
            )
        except Exception as hist_exc:
            logger.warning(
                "⚠️ [CELERY] left object history push failed for %s: %s",
                camera_id,
                hist_exc,
            )
        try:
            push_vehicle_history(
                camera_id,
                timestamp=ts,
                vehicles=vehicles,
            )
        except Exception as hist_exc:
            logger.warning(
                "⚠️ [CELERY] vehicle history push failed for %s: %s",
                camera_id,
                hist_exc,
            )
        
        payload = json.dumps({
            "camera_id": camera_id,
            "timestamp": ts,
            "people_count": people_count,
            "body_count": body_count,
            "body_persons": body_summary,
            "object_count": object_count,
            "objects": object_summary,
            "vehicle_count": vehicle_count,
            "vehicles": vehicle_summary,
            "demographics": demographics,
            "source_mvr_uuids": source_mvr_uuids,
            "source_embeddings": source_embeddings,
            "instant_mvrs": [
                {
                    "instant_mvr_uuid": m.get("instant_mvr_uuid"),
                    "face_embedding": m.get("face_embedding"),
                    "person_object_uuid": m.get("person_object_uuid"),
                    "age_gender": m.get("age_gender"),
                }
                for m in instant_mvrs
            ],
            "velocity": result.get("velocity") or {
                "crowd_mps": result.get("crowd_velocity_mps"),
                "max_mps": result.get("max_person_speed_mps"),
                "valid_count": result.get("crowd_person_count", 0),
                "people": [],
            },
            "metadata": {
                "source_mvr_uuids": source_mvr_uuids,
                "processing_time": result.get("processing_time_seconds", 0),
                "total_faces": result.get("total_faces_detected", 0),
                "body_count": body_count,
                "object_count": object_count,
                "vehicle_count": vehicle_count,
            }
        })
        
        subscriber_count = redis_client.publish("instant-detection", payload)
        logger.info(
            f"✅ [CELERY] Redis Pub/Sub: {camera_id} → {subscriber_count} subscribers "
            f"(people={people_count}, bodies={body_count}, objects={object_count}, vehicles={vehicle_count})"
        )
        
    except Exception as e:
        logger.error(f"❌ [CELERY] Redis publish error: {e}")


def _push_to_webhook(camera_id: str, result: Dict):
    """Push instant detection results to webhook endpoint"""
    webhook_url = os.getenv("INSTANT_DETECTION_WEBHOOK_URL")
    webhook_enabled = os.getenv("INSTANT_DETECTION_WEBHOOK_ENABLED", "false").lower() == "true"
    
    if not webhook_enabled or not webhook_url:
        return
    if _is_legacy_media_trigger_webhook(webhook_url):
        logger.info(
            "ℹ️ [CELERY] Legacy Media trigger webhook suppressed: %s. Redis instant-detection subscriber is authoritative for trigger execution.",
            webhook_url,
        )
        return
    
    try:
        import requests
        
        demographics = result.get("demographics", {})
        people_count = result.get("people_count", 0)
        body_count = result.get("body_count")
        if body_count is None:
            body_count = len(result.get("body_persons") or [])
        source_mvr_uuids = _extract_source_identity_uuids(result.get("person_objects") or [])
        
        payload = {
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "people_count": people_count,
            "body_count": body_count,
            "demographics": demographics,
            "source_mvr_uuids": source_mvr_uuids,
            "metadata": {
                "source_mvr_uuids": source_mvr_uuids,
                "processing_time": result.get("processing_time_seconds", 0),
                "total_faces": result.get("total_faces_detected", 0),
                "body_count": body_count,
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=2)
        
        if response.status_code == 200:
            logger.info(f"✅ [CELERY] Webhook SUCCESS: {camera_id}")
        else:
            logger.warning(
                f"⚠️ [CELERY] Webhook returned {response.status_code}: {camera_id}"
            )
            
    except requests.Timeout:
        logger.warning(f"⚠️ [CELERY] Webhook timeout (2s): {camera_id}")
    except Exception as e:
        logger.error(f"❌ [CELERY] Webhook push error: {e}")


@celery_app.task(
    name="instant_detection.health_check",
    queue="instant_detection_queue"
)
def health_check() -> Dict:
    """Health check task for monitoring worker status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": "instant_detection"
    }


@celery_app.task(
    name="instant_detection.flush_y_window",
    queue="instant_detection_queue",
    time_limit=180,
    soft_time_limit=150,
    max_retries=1,
    retry_backoff=True,
    acks_late=True,
)
def flush_instant_detection_y_window(
    camera_id: str,
    session_uuid: Optional[str] = None,
    auth_token: str = "",
    frames_per_cycle: int = 3,
    flush_interval_cycles: int = 12,
    merge_threshold: float = 0.60,
) -> Dict:
    """
    Y-window flush: Vision re-group + contamination, hierarchical MVR merge,
    write Media instant_detection_logs only (no gallery identify).
    """
    from src.services.instant_detection_flush import run_y_window_flush

    logger.info(
        "📦 [CELERY] Y-window flush starting for %s (Y=%s threshold=%.2f)",
        camera_id,
        flush_interval_cycles,
        merge_threshold,
    )
    result = run_y_window_flush(
        camera_id,
        session_uuid=session_uuid,
        auth_token=auth_token or None,
        frames_per_cycle=frames_per_cycle,
        flush_interval_cycles=flush_interval_cycles,
        merge_threshold=merge_threshold,
    )
    logger.info("📦 [CELERY] Y-window flush done for %s: %s", camera_id, result)
    return result


@celery_app.task(
    name="instant_detection.persist_results",
    queue="instant_detection_queue",
    time_limit=15,
    soft_time_limit=12,
    max_retries=1,
    retry_backoff=True,
    acks_late=True,
)
def persist_instant_detection_results(
    camera_id: str,
    session_uuid: str,
    cycle_timestamp: str,
    person_objects: List[Dict[str, Any]],
    demographics: Dict[str, Any],
    auth_token: str,
    body_persons: Optional[List[Dict[str, Any]]] = None,
    crowd_velocity_mps: Optional[float] = None,
    max_person_speed_mps: Optional[float] = None,
    crowd_person_count: Optional[int] = None,
) -> Dict:
    """
    Buffer instant detection results for batched VMeta flush.

    Face person_objects and body_persons share the same Redis queue.
    Called asynchronously after the main detection result has been
    cached and broadcast. Never blocks the detection loop.
    """
    payload = {
        "session_uuid": session_uuid,
        "camera_id": camera_id,
        "cycle_timestamp": cycle_timestamp,
        "person_objects": person_objects or [],
        "body_persons": body_persons or [],
        "demographics": demographics,
        "auth_token": auth_token,
        "crowd_velocity_mps": crowd_velocity_mps,
        "max_person_speed_mps": max_person_speed_mps,
        "crowd_person_count": crowd_person_count,
    }

    queue_length = _queue_batch_item(camera_id, payload)
    logger.info(
        "📦 [CELERY] Buffered instant detection batch item for %s (queue_length=%s)",
        camera_id,
        queue_length,
    )

    if _should_flush_batch(camera_id):
        flush_instant_detection_batch.delay(camera_id)
    else:
        flush_instant_detection_batch.apply_async(
            args=[camera_id],
            countdown=INSTANT_DETECTION_BATCH_FLUSH_SECONDS,
        )

    return {
        "success": True,
        "camera_id": camera_id,
        "buffered": True,
        "queue_length": queue_length,
    }


@celery_app.task(
    name="instant_detection.flush_persist_batch",
    queue="instant_detection_queue",
    time_limit=30,
    soft_time_limit=25,
    max_retries=1,
    retry_backoff=True,
    acks_late=True,
)
def flush_instant_detection_batch(camera_id: str) -> Dict:
    import requests as http_requests
    import jwt as _jwt
    from datetime import timedelta

    queue_key = _batch_queue_key(camera_id)
    lock_key = _batch_lock_key(camera_id)
    lock_acquired = redis_client.set(lock_key, "1", nx=True, ex=60)
    if not lock_acquired:
        return {"success": True, "camera_id": camera_id, "skipped": "flush_locked"}

    attempted = 0
    try:
        _drop_stale_batch_items(camera_id, reason="over_age")

        if not _should_flush_batch(camera_id):
            return {"success": True, "camera_id": camera_id, "skipped": "flush_not_due"}

        items = _load_batch_items(camera_id, INSTANT_DETECTION_BATCH_FLUSH_COUNT)
        if not items:
            return {"success": True, "camera_id": camera_id, "flushed": 0}

        # FIFO: drop any over-age heads already handled; skip leftover stale rows.
        items = [
            item
            for item in items
            if not is_cycle_over_max_age(item.get("cycle_timestamp"))
        ]
        if not items:
            _drop_stale_batch_items(camera_id, reason="over_age")
            return {"success": True, "camera_id": camera_id, "flushed": 0, "dropped_stale": True}

        attempted = len(items)

        vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        endpoint = f"{vmeta_url}/api/v1/instant-detection/persist-batch"

        internal_service_token = os.getenv(
            "INTERNAL_SERVICE_TOKEN",
            "ppl-meta-internal-service-secret-key-change-in-production",
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {internal_service_token}",
            "X-Service-Name": "cameras-service",
        }

        batch_payload = {
            "items": [
                {
                    "session_uuid": item["session_uuid"],
                    "camera_id": item["camera_id"],
                    "cycle_timestamp": item["cycle_timestamp"],
                    "person_objects": item.get("person_objects", []),
                    "body_persons": item.get("body_persons", []),
                    "demographics": item.get("demographics", {}),
                    "crowd_velocity_mps": item.get("crowd_velocity_mps"),
                    "max_person_speed_mps": item.get("max_person_speed_mps"),
                    "crowd_person_count": item.get("crowd_person_count"),
                }
                for item in items
            ]
        }

        resp = http_requests.post(endpoint, json=batch_payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            _trim_batch_items(camera_id, len(items))
            remaining = redis_client.llen(queue_key)
            logger.info(
                "✅ [CELERY] Flushed %s instant detection items for %s (remaining=%s)",
                len(items),
                camera_id,
                remaining,
            )
            if remaining > 0:
                flush_instant_detection_batch.apply_async(
                    args=[camera_id],
                    countdown=INSTANT_DETECTION_BATCH_FLUSH_SECONDS,
                )
            return {"success": True, "camera_id": camera_id, "flushed": len(items), **data}

        logger.warning(
            "⚠️ [CELERY] VMeta persist-batch returned %s for %s: %s",
            resp.status_code,
            camera_id,
            resp.text[:200],
        )
        dropped = _drop_failed_flush_if_stale(camera_id, attempted)
        return {
            "success": False,
            "camera_id": camera_id,
            "status": resp.status_code,
            "dropped_stale": dropped,
        }

    except Exception as e:
        logger.error(f"❌ [CELERY] Persist batch flush failed for {camera_id}: {e}")
        dropped = _drop_failed_flush_if_stale(camera_id, attempted)
        return {
            "success": False,
            "camera_id": camera_id,
            "error": str(e),
            "dropped_stale": dropped,
        }
    finally:
        redis_client.delete(lock_key)
