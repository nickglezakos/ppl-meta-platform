"""
Celery tasks for instant detection processing
Runs detection in background workers to avoid blocking the main FastAPI service
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

import redis
import sys
from pathlib import Path
from celery import Task

# Add parent directory to path to import shared
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from shared.queue_config import celery_app, redis_client

logger = logging.getLogger(__name__)


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
        source_mvr_uuids = _extract_source_identity_uuids(result.get("person_objects") or [])
        
        payload = json.dumps({
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "people_count": people_count,
            "demographics": demographics,
            "source_mvr_uuids": source_mvr_uuids,
            "metadata": {
                "source_mvr_uuids": source_mvr_uuids,
                "processing_time": result.get("processing_time_seconds", 0),
                "total_faces": result.get("total_faces_detected", 0)
            }
        })
        
        subscriber_count = redis_client.publish("instant-detection", payload)
        logger.info(
            f"✅ [CELERY] Redis Pub/Sub: {camera_id} → {subscriber_count} subscribers"
        )
        
    except Exception as e:
        logger.error(f"❌ [CELERY] Redis publish error: {e}")


def _push_to_webhook(camera_id: str, result: Dict):
    """Push instant detection results to webhook endpoint"""
    webhook_url = os.getenv("INSTANT_DETECTION_WEBHOOK_URL")
    webhook_enabled = os.getenv("INSTANT_DETECTION_WEBHOOK_ENABLED", "false").lower() == "true"
    
    if not webhook_enabled or not webhook_url:
        return
    
    try:
        import requests
        
        demographics = result.get("demographics", {})
        people_count = result.get("people_count", 0)
        source_mvr_uuids = _extract_source_identity_uuids(result.get("person_objects") or [])
        
        payload = {
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "people_count": people_count,
            "demographics": demographics,
            "source_mvr_uuids": source_mvr_uuids,
            "metadata": {
                "source_mvr_uuids": source_mvr_uuids,
                "processing_time": result.get("processing_time_seconds", 0),
                "total_faces": result.get("total_faces_detected", 0)
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
) -> Dict:
    """
    Persist instant detection results to VMeta database.

    Called asynchronously after the main detection result has been
    cached and broadcast.  Never blocks the detection loop.
    """
    import requests as http_requests

    vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
    endpoint = f"{vmeta_url}/api/v1/instant-detection/persist"

    payload = {
        "session_uuid": session_uuid,
        "camera_id": camera_id,
        "cycle_timestamp": cycle_timestamp,
        "person_objects": person_objects,
        "demographics": demographics,
    }

    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        resp = http_requests.post(endpoint, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                f"✅ [CELERY] Persisted instant detection for {camera_id}: "
                f"{data.get('stored_individuals', 0)} individuals, "
                f"{data.get('appearances_created', 0)} appearances"
            )
            return {"success": True, "camera_id": camera_id, **data}
        else:
            logger.warning(
                f"⚠️ [CELERY] VMeta persist returned {resp.status_code}: {resp.text[:200]}"
            )
            return {"success": False, "camera_id": camera_id, "status": resp.status_code}
    except Exception as e:
        logger.error(f"❌ [CELERY] Persist task failed for {camera_id}: {e}")
        return {"success": False, "camera_id": camera_id, "error": str(e)}
