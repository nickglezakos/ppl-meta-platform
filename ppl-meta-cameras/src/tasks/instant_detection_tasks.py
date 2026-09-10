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

# Add parent directory to path to import shared
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from shared.queue_config import celery_app, redis_client

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


def _batch_queue_key(camera_id: str) -> str:
    return f"instant_detection_batch:{camera_id}"


def _batch_oldest_key(camera_id: str) -> str:
    return f"{_batch_queue_key(camera_id)}:oldest_ts"


def _batch_lock_key(camera_id: str) -> str:
    return f"{_batch_queue_key(camera_id)}:flush_lock"


def _queue_batch_item(camera_id: str, payload: Dict[str, Any]) -> int:
    queue_key = _batch_queue_key(camera_id)
    oldest_key = _batch_oldest_key(camera_id)
    pipe = redis_client.pipeline()
    pipe.rpush(queue_key, json.dumps(payload))
    pipe.setnx(oldest_key, payload["cycle_timestamp"])
    result = pipe.execute()
    return int(result[0])


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
    oldest_key = _batch_oldest_key(camera_id)
    redis_client.ltrim(queue_key, count, -1)
    next_item = redis_client.lindex(queue_key, 0)
    if next_item:
        try:
            parsed = json.loads(next_item)
            redis_client.set(oldest_key, parsed.get("cycle_timestamp", datetime.utcnow().isoformat() + "Z"))
        except json.JSONDecodeError:
            redis_client.delete(oldest_key)
    else:
        redis_client.delete(oldest_key)


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
    time_limit=30,  # 30 seconds max
    soft_time_limit=25
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
                r = redis.Redis(host='localhost', port=6379, decode_responses=False)
                cache_key = f"instant_detection:{camera_id}"
                # Store with 5 minute TTL
                r.setex(cache_key, 300, json.dumps(result))
                logger.info(f"📦 [CELERY] Cached result in Redis for {camera_id} at {result['timestamp']} - frontend API can now access it")
            except Exception as e:
                logger.error(f"❌ [CELERY] Failed to cache in Redis: {e}")
                # Fallback to instance cache (won't work cross-process but better than nothing)
                detector._cache_result(camera_id, result)
            
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

    try:
        if not _should_flush_batch(camera_id):
            return {"success": True, "camera_id": camera_id, "skipped": "flush_not_due"}

        items = _load_batch_items(camera_id, INSTANT_DETECTION_BATCH_FLUSH_COUNT)
        if not items:
            return {"success": True, "camera_id": camera_id, "flushed": 0}

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
        return {"success": False, "camera_id": camera_id, "status": resp.status_code}

    except Exception as e:
        logger.error(f"❌ [CELERY] Persist batch flush failed for {camera_id}: {e}")
        return {"success": False, "camera_id": camera_id, "error": str(e)}
    finally:
        redis_client.delete(lock_key)
