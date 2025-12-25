"""
Celery tasks for instant detection processing
Runs detection in background workers to avoid blocking the main FastAPI service
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List

import redis
import sys
from pathlib import Path
from celery import Task

# Add parent directory to path to import shared
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from shared.queue_config import celery_app, redis_client

logger = logging.getLogger(__name__)


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
        
        payload = json.dumps({
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "people_count": people_count,
            "demographics": demographics,
            "metadata": {
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
        
        payload = {
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "people_count": people_count,
            "demographics": demographics,
            "metadata": {
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
