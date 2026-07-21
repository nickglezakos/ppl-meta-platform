"""
Instant Detection API Endpoints

Provides REST API endpoints for instant temporal face detection.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, Optional
import logging
import time
import os
import uuid
from datetime import datetime, timedelta

import jwt
import requests as http_requests

from src.services.instant_detection import InstantDetectionSampler
from src.database import get_db
from src.models.camera import Camera, CameraType
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["instant-detection"])

# Global instant detection manager (singleton)
_instant_detection_manager: Optional[InstantDetectionSampler] = None


def get_instant_detection_manager() -> InstantDetectionSampler:
    """Get or create instant detection manager singleton with auto-configured webhook"""
    global _instant_detection_manager
    
    if _instant_detection_manager is None:
        _instant_detection_manager = InstantDetectionSampler(
            vision_service_url="http://localhost:8003",
            sampling_interval=5,
            temporal_window=1.0
        )
        logger.info("✅ Instant detection manager initialized")
        
        # Auto-configure webhook from environment variables
        webhook_url = os.getenv("INSTANT_DETECTION_WEBHOOK_URL")
        webhook_enabled = os.getenv("INSTANT_DETECTION_WEBHOOK_ENABLED", "false").lower() == "true"
        
        if webhook_url and webhook_enabled:
            try:
                _instant_detection_manager.configure_webhook(webhook_url, webhook_enabled)
                logger.info(f"✅ Webhook auto-configured from .env: {webhook_url}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to auto-configure webhook: {e}")
        else:
            logger.info("ℹ️ No webhook configured (set INSTANT_DETECTION_WEBHOOK_URL and INSTANT_DETECTION_WEBHOOK_ENABLED in .env)")
    
    return _instant_detection_manager


@router.get("/status")
async def get_status(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get status of instant detection system
    
    Returns:
        Status information including running state, cached results count
    """
    return {
        "success": True,
        "status": manager.get_status()
    }


@router.get("/results/{camera_id}")
async def get_instant_results(
    camera_id: str,
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get latest instant detection results for a camera.
    
    Results are kept in Redis cache (cross-process) until replaced by next iteration.
    This allows frontend to access instant results while recording is active.
    
    Args:
        camera_id: Camera device ID
        
    Returns:
        Latest detection results or 404 if no results available
    """
    # 🔥 CRITICAL: Check Redis first (Celery workers cache here)
    try:
        import redis
        import json
        
        r = redis.Redis(host='localhost', port=6379, decode_responses=False)
        cache_key = f"instant_detection:{camera_id}"
        cached_bytes = r.get(cache_key)
        
        if cached_bytes:
            result = json.loads(cached_bytes.decode('utf-8'))
            
            # Check if result has a timestamp and if it's too old (> 5 minutes = stale)
            result_timestamp = result.get('timestamp')
            age_seconds = 0
            
            if result_timestamp:
                try:
                    result_time = datetime.fromisoformat(result_timestamp.replace('Z', '+00:00'))
                    age_seconds = (datetime.utcnow().replace(tzinfo=result_time.tzinfo) - result_time).total_seconds()
                    
                    # If older than 5 minutes, consider it stale (match Redis TTL)
                    if age_seconds > 300:
                        logger.info("Redis cache stale for %s (%.1fs old); clearing", camera_id, age_seconds)
                        r.delete(cache_key)  # Clean up stale data
                        raise HTTPException(
                            status_code=404,
                            detail=f"No instant detection results for camera {camera_id}. Start instant detection first."
                        )
                except (TypeError, ValueError):
                    logger.info("Redis cache timestamp invalid for %s; clearing stale result", camera_id)
                    r.delete(cache_key)  # Clean up unparseable data
                    raise HTTPException(
                        status_code=404,
                        detail=f"No instant detection results for camera {camera_id}. Start instant detection first."
                    )
            else:
                # No timestamp = old cached data before we added timestamps
                logger.info("Redis cache missing timestamp for %s; clearing stale result", camera_id)
                r.delete(cache_key)
                raise HTTPException(
                    status_code=404,
                    detail=f"No instant detection results for camera {camera_id}. Start instant detection first."
                )
            
            logger.debug("Retrieved instant detection result from Redis for %s (%.1fs old)", camera_id, age_seconds)
            
            # Add metadata
            result["_metadata"] = {
                "cached_at": time.time(),
                "source": "redis",
                "age_seconds": age_seconds
            }
            
            return result
    except HTTPException:
        raise
    except (redis.RedisError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
        logger.debug("Failed to check Redis cache for %s: %s", camera_id, exc)
    
    # Fallback to in-memory cache (for backward compatibility)
    cached_data = manager.results_cache.get(camera_id)
    
    if cached_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No instant detection results for camera {camera_id}. Start instant detection first."
        )
    
    # Include metadata about when result was cached
    result = cached_data["result"].copy()
    result["_metadata"] = {
        "cached_at": cached_data["cached_at"],
        "iteration": cached_data["iteration"],
        "age_seconds": time.time() - cached_data["cached_at"],
        "source": "memory"
    }
    
    return result


@router.get("/results")
async def get_all_instant_results(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get latest instant detection results for ALL cameras.
    
    Useful for dashboards or monitoring multiple cameras.
    
    Returns:
        Dict mapping camera_id to latest results
    """
    all_results = {}
    
    for camera_id, cached_data in manager.results_cache.items():
        result = cached_data["result"].copy()
        result["_metadata"] = {
            "cached_at": cached_data["cached_at"],
            "iteration": cached_data["iteration"],
            "age_seconds": time.time() - cached_data["cached_at"]
        }
        all_results[camera_id] = result
    
    return {
        "success": True,
        "total_cameras": len(all_results),
        "results": all_results
    }


@router.post("/start/{camera_id}")
async def start_instant_detection(
    camera_id: str,
    db: Session = Depends(get_db),
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Start instant detection for a camera
    
    Args:
        camera_id: Camera device ID
        
    Returns:
        Success status
    """
    # Verify camera exists
    camera = db.query(Camera).filter(Camera.device_id == camera_id).first()
    
    if not camera:
        raise HTTPException(
            status_code=404,
            detail=f"Camera {camera_id} not found"
        )
    
    # Get camera path
    camera_path = camera.connection_string or f"/dev/video{camera.device_index or 0}"

    # For mobile cameras, ensure queue worker is connected before starting sampling.
    # The _sample_loop checks get_camera_stream() on its first iteration and stops
    # immediately if no connected worker is found — this auto-connects it so that
    # instant detection works even when recording is not active.
    if camera.camera_type == CameraType.MOBILE:
        try:
            from src.services.camera_service_queue import get_camera_service
            _queue_service = get_camera_service()
            _worker = await _queue_service.get_camera_stream(camera_id)
            if not _worker:
                logger.info(
                    f"📱 [INSTANT_DETECTION] Auto-connecting queue worker for mobile camera {camera_id}"
                )
                _connected = await _queue_service.connect_camera(camera_id)
                if not _connected:
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            f"Mobile camera {camera_id} is not active. "
                            "Ensure the mobile camera app is streaming frames before starting instant detection."
                        ),
                    )
        except HTTPException:
            raise
        except Exception as _e:
            logger.warning(
                f"⚠️ [INSTANT_DETECTION] Could not auto-connect queue worker for mobile camera {camera_id}: {_e}"
            )

    try:
        # Load per-camera pipeline settings for storage configuration
        storage_multiple = camera.storage_multiple if camera.storage_multiple is not None else 1
        session_duration = camera.tracking_session_duration_minutes if camera.tracking_session_duration_minutes is not None else 0

        # Create tracking session in VMeta for this detection run
        session_uuid = str(uuid.uuid4())
        vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        # Build service-to-service auth token
        internal_service_token = os.getenv(
            "INTERNAL_SERVICE_TOKEN",
            "ppl-meta-internal-service-secret-key-change-in-production",
        )
        svc_headers = {
            "Authorization": f"Bearer {internal_service_token}",
            "Content-Type": "application/json",
            "X-Service-Name": "cameras-service",
        }
        try:
            resp = http_requests.post(
                f"{vmeta_url}/api/v1/instant-detection/create-session",
                json={
                    "session_uuid": session_uuid,
                    "camera_id": camera_id,
                    "source_type": "instant_detection",
                    "user_id": "system",
                },
                headers=svc_headers,
                timeout=5,
            )
            if resp.status_code == 200:
                logger.info(f"✅ Created tracking session {session_uuid[:8]}... for {camera_id}")
            else:
                logger.warning(f"⚠️ VMeta create-session returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"⚠️ Could not create tracking session in VMeta: {e}")

        # Start sampling — the manager creates per-camera state internally
        manager.start_sampling(camera_id, camera_path)

        # Configure per-camera state that was just created
        with manager._lock:
            state = manager._samplers.get(camera_id)
            if state:
                state.session_uuid = session_uuid
                state.session_started_at = datetime.utcnow()
                state.storage_multiple = storage_multiple
                state.session_duration_minutes = session_duration
                state.cycle_counter = 0
                state.auth_token = internal_service_token
        
        return {
            "success": True,
            "message": f"Instant detection started for camera {camera_id}",
            "camera_id": camera_id,
            "sampling_interval": manager.sampling_interval,
            "temporal_window": manager.temporal_window,
            "session_uuid": session_uuid,
            "storage_multiple": storage_multiple,
            "tracking_session_duration_minutes": session_duration,
        }
        
    except Exception as e:
        logger.error(f"Failed to start instant detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start instant detection: {str(e)}"
        )


@router.post("/stop")
async def stop_instant_detection(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Stop instant detection sampling (global stop)
    
    Returns:
        Success status
    """
    try:
        # Complete tracking sessions for all active cameras in VMeta before stopping
        vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        stop_token = os.getenv(
            "INTERNAL_SERVICE_TOKEN",
            "ppl-meta-internal-service-secret-key-change-in-production",
        )
        svc_headers = {
            "Authorization": f"Bearer {stop_token}",
            "Content-Type": "application/json",
            "X-Service-Name": "cameras-service",
        }
        with manager._lock:
            active_states = list(manager._samplers.values())
        for state in active_states:
            if state.session_uuid:
                try:
                    resp = http_requests.post(
                        f"{vmeta_url}/api/v1/instant-detection/complete-session/{state.session_uuid}",
                        headers=svc_headers,
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        logger.info(f"✅ Completed tracking session {state.session_uuid[:8]}... for {state.camera_id}")
                    else:
                        logger.warning(f"⚠️ Complete-session returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not complete tracking session for {state.camera_id}: {e}")

        manager.stop_sampling()
        
        return {
            "success": True,
            "message": "Instant detection stopped"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop instant detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop instant detection: {str(e)}"
        )


@router.post("/stop/{camera_id}")
async def stop_instant_detection_for_camera(
    camera_id: str,
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Stop instant detection for a specific camera.
    Only stops if the currently running camera matches the requested camera_id.
    
    Args:
        camera_id: Camera device ID to stop detection for
        
    Returns:
        Success status
    """
    try:
        with manager._lock:
            state = manager._samplers.get(camera_id)

        if state and state.running:
            # Complete tracking session in VMeta before stopping
            if state.session_uuid:
                vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
                stop_token = os.getenv(
                    "INTERNAL_SERVICE_TOKEN",
                    "ppl-meta-internal-service-secret-key-change-in-production",
                )
                svc_headers = {
                    "Authorization": f"Bearer {stop_token}",
                    "Content-Type": "application/json",
                    "X-Service-Name": "cameras-service",
                }
                try:
                    resp = http_requests.post(
                        f"{vmeta_url}/api/v1/instant-detection/complete-session/{state.session_uuid}",
                        headers=svc_headers,
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        logger.info(f"✅ Completed tracking session {state.session_uuid[:8]}...")
                    else:
                        logger.warning(f"⚠️ Complete-session returned {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not complete tracking session: {e}")

            manager.stop_sampling(camera_id)
            return {
                "success": True,
                "message": f"Instant detection stopped for {camera_id}"
            }
        else:
            return {
                "success": True,
                "message": f"Instant detection was not running for {camera_id}"
            }
    except Exception as e:
        logger.error(f"Failed to stop instant detection for {camera_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop instant detection: {str(e)}"
        )


# Webhook Configuration Models and Endpoints

class WebhookConfig(BaseModel):
    """Webhook configuration for pushing instant detection results"""
    url: HttpUrl
    enabled: bool = True


@router.post("/webhook/configure")
async def configure_webhook(
    config: WebhookConfig,
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Configure webhook for pushing instant detection results to media service.
    
    When enabled, detection results are automatically POSTed to the webhook URL
    every time instant detection completes (default: every 5 seconds).
    
    The webhook receives demographic data in this format:
    ```json
    {
        "camera_id": "usb_camera_0",
        "timestamp": "2025-12-13T10:30:00",
        "people_count": 3,
        "demographics": {
            "percent_male": 67,
            "percent_female": 33,
            "percent_young": 0,
            "percent_adult": 100,
            ...
        },
        "metadata": {
            "processing_time": 2.5,
            "total_faces": 3
        }
    }
    ```
    
    Args:
        config: Webhook configuration (URL and enabled flag)
        
    Returns:
        Success status and configuration
        
    Example:
        ```bash
        curl -X POST 'http://localhost:8005/api/v1/instant-detection/webhook/configure' \\
          -H 'Content-Type: application/json' \\
          -d '{
            "url": "http://localhost:8000/api/v1/triggers/instant-detection",
            "enabled": true
          }'
        ```
    """
    try:
        manager.configure_webhook(str(config.url), config.enabled)
        
        return {
            "success": True,
            "message": "Webhook configured successfully",
            "webhook_url": str(config.url),
            "enabled": config.enabled
        }
        
    except Exception as e:
        logger.error(f"Failed to configure webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to configure webhook: {str(e)}"
        )


@router.get("/webhook/status")
async def get_webhook_status(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Get current webhook configuration status.
    
    Returns:
        Webhook URL, enabled status, and push statistics
    """
    return {
        "success": True,
        "webhook_url": manager.webhook_url,
        "enabled": manager.webhook_enabled,
        "message": "Webhook is active and pushing results" if manager.webhook_enabled else "Webhook is disabled"
    }


@router.post("/webhook/disable")
async def disable_webhook(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Disable webhook push without removing URL configuration.
    
    Results will still be cached locally but not pushed to webhook.
    """
    manager.webhook_enabled = False
    
    return {
        "success": True,
        "message": "Webhook disabled",
        "webhook_url": manager.webhook_url,
        "enabled": False
    }


@router.post("/webhook/enable")
async def enable_webhook(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """
    Enable webhook push using existing URL configuration.
    
    Returns error if webhook URL not configured.
    """
    if not manager.webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Webhook URL not configured. Use /webhook/configure first."
        )
    
    manager.webhook_enabled = True
    
    return {
        "success": True,
        "message": "Webhook enabled",
        "webhook_url": manager.webhook_url,
        "enabled": True
    }
