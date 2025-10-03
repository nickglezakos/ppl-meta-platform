#!/usr/bin/env python3
"""
PPL Thread Worker - Celery worker for automatic PPL Thread triggering
Handles asynchronous PPL Thread workflow triggers after face detection completion
"""

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import httpx
from celery import Celery

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Redis/Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery("ppl_thread_worker", broker=REDIS_URL, backend=REDIS_URL)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
)

# Service endpoints
VISION_SERVICE_URL = os.getenv("VISION_SERVICE_URL", "http://localhost:8003")
NODE_SERVICE_URL = os.getenv("NODE_SERVICE_URL", "http://localhost:8001")


@app.task(name="trigger_ppl_thread", bind=True, max_retries=3)
def trigger_ppl_thread_task(
    self,
    media_id: str,
    total_faces: int,
    workflow_id: str,
    trigger_reason: str = "automatic_queue_trigger",
) -> Dict[str, Any]:
    """
    Celery task to trigger PPL Thread workflow after face detection completion.

    This runs asynchronously in a separate worker process and provides:
    - Reliable triggering with retry logic
    - Proper error handling and logging
    - Decoupling from the Media Service workflow

    Args:
        media_id: UUID of the media to process
        total_faces: Number of faces detected
        workflow_id: Source face detection workflow ID
        trigger_reason: Reason for triggering (for logging/debugging)

    Returns:
        Dict with success status and response data
    """
    try:
        logger.info(f"🚀 QUEUE TRIGGER: Starting PPL Thread for media {media_id}")
        logger.info(f"📊 QUEUE TRIGGER: {total_faces} faces, workflow {workflow_id}")

        # Step 1: Get authentication token
        auth_token = _get_auth_token()
        if not auth_token:
            raise Exception("Failed to get authentication token")

        # Step 2: Trigger PPL Thread workflow
        result = _trigger_ppl_thread_api(
            media_id, total_faces, workflow_id, auth_token, trigger_reason
        )

        if result.get("success"):
            logger.info(
                f"✅ QUEUE TRIGGER: Successfully triggered PPL Thread for {media_id}"
            )
            return result
        else:
            # Retry on failure
            logger.warning(
                f"⚠️ QUEUE TRIGGER: Failed attempt {self.request.retries + 1} for {media_id}"
            )
            if self.request.retries < self.max_retries:
                raise self.retry(
                    countdown=60 * (2**self.request.retries)
                )  # Exponential backoff
            else:
                logger.error(f"❌ QUEUE TRIGGER: Max retries exceeded for {media_id}")
                return result

    except Exception as e:
        logger.error(f"❌ QUEUE TRIGGER: Exception for {media_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2**self.request.retries), exc=e)
        else:
            return {"success": False, "error": str(e), "media_id": media_id}


def _get_auth_token() -> Optional[str]:
    """Get authentication token from Node Service"""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{NODE_SERVICE_URL}/api/v1/users/login",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data="username=fresh.user@example.com&password=NewPassword234!",
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                logger.error(f"Auth failed: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"Auth error: {e}")
        return None


def _trigger_ppl_thread_api(
    media_id: str,
    total_faces: int,
    workflow_id: str,
    auth_token: str,
    trigger_reason: str,
) -> Dict[str, Any]:
    """Call Vision Service to trigger PPL Thread workflow"""
    try:
        # Primary endpoint payload
        primary_payload = {
            "media_id": media_id,
            "total_faces": str(total_faces),  # String format as required by API
            "trigger_reason": f"{trigger_reason}_from_workflow_{workflow_id}",
            "session_uuid": f"queue-session-{workflow_id}",
            "source_workflow_id": workflow_id,
        }

        with httpx.Client(timeout=30.0) as client:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            }

            # Try primary PPL Thread trigger endpoint
            logger.info(f"🎯 QUEUE TRIGGER: Calling primary endpoint for {media_id}")
            response = client.post(
                f"{VISION_SERVICE_URL}/api/v1/person-objects/workflow/trigger",
                json=primary_payload,
                headers=headers,
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ PRIMARY SUCCESS: {result}")
                return {
                    "success": True,
                    "method": "primary",
                    "response": result,
                    "media_id": media_id,
                }
            else:
                logger.warning(
                    f"⚠️ PRIMARY FAILED: {response.status_code} - {response.text}"
                )

                # Try fallback endpoint
                logger.info(
                    f"🔄 QUEUE TRIGGER: Trying fallback endpoint for {media_id}"
                )
                fallback_payload = {
                    "media_ids": media_id,  # Single string for fallback
                    "workflow_type": "ppl_thread_automatic",
                    "session_uuid": f"queue-session-{workflow_id}",
                }

                fallback_response = client.post(
                    f"{VISION_SERVICE_URL}/api/v1/person-objects/workflows/start",
                    json=fallback_payload,
                    headers=headers,
                )

                if fallback_response.status_code == 200:
                    result = fallback_response.json()
                    logger.info(f"✅ FALLBACK SUCCESS: {result}")
                    return {
                        "success": True,
                        "method": "fallback",
                        "response": result,
                        "media_id": media_id,
                    }
                else:
                    logger.error(
                        f"❌ FALLBACK FAILED: {fallback_response.status_code} - {fallback_response.text}"
                    )
                    return {
                        "success": False,
                        "error": f"Both endpoints failed. Primary: {response.status_code}, Fallback: {fallback_response.status_code}",
                        "media_id": media_id,
                    }

    except Exception as e:
        logger.error(f"API call error: {e}")
        return {"success": False, "error": str(e), "media_id": media_id}


@app.task(name="health_check")
def health_check_task() -> Dict[str, Any]:
    """Health check task for monitoring worker status"""
    return {
        "status": "healthy",
        "worker": "ppl_thread_worker",
        "timestamp": str(app.now()),
    }


if __name__ == "__main__":
    # Run as worker
    logger.info("🔧 Starting PPL Thread Worker...")
    app.worker_main(["worker", "--loglevel=info", "--concurrency=2"])
