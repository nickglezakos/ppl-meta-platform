"""Celery tasks for stream operations reconciliation and recovery scaffolding."""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path to import shared
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from shared.queue_config import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in Celery task context."""
    return asyncio.run(coro)


@celery_app.task(
    name="stream_operations.reconcile_camera",
    queue="instant_detection_queue",
    time_limit=30,
    soft_time_limit=20,
)
def reconcile_camera(camera_id: str) -> Dict[str, Any]:
    """Reconcile stream operations state for a single camera."""
    logger.info("[STREAM-OPS] reconcile_camera started for %s", camera_id)
    from src.services.stream_operations_state import get_stream_operations_state_service

    service = get_stream_operations_state_service()
    result = _run_async(service.reconcile_camera_state(camera_id))
    return {
        "success": True,
        "camera_id": camera_id,
        "result": result,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@celery_app.task(
    name="stream_operations.reconcile_all",
    queue="instant_detection_queue",
    time_limit=120,
    soft_time_limit=90,
)
def reconcile_all(camera_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Reconcile stream operations state for all tracked cameras or provided subset."""
    from src.services.stream_operations_state import get_stream_operations_state_service

    service = get_stream_operations_state_service()
    tracked_ids: List[str]
    if camera_ids:
        tracked_ids = camera_ids
    else:
        tracked_ids = _run_async(service.list_tracked_camera_ids())

    reports: List[Dict[str, Any]] = []
    updated = 0
    for camera_id in tracked_ids:
        result = _run_async(service.reconcile_camera_state(camera_id))
        if result.get("status") == "updated":
            updated += 1
        reports.append(result)

    return {
        "success": True,
        "total": len(reports),
        "updated": updated,
        "reports": reports,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
