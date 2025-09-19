"""
PPL Meta Cameras - Orchestrator Service Client
Phase 5: Camera recording completion event publishing
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)


class OrchestratorClient:
    """HTTP client for publishing events to Orchestrator Service."""

    def __init__(self, base_url: str = "http://localhost:8002", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def publish_camera_event(
        self,
        event_type: str,
        camera_device_id: str,
        recording_session_id: str,
        video_file_path: str,
        user_id: str,
        recording_duration_seconds: float,
        file_size_bytes: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish camera recording completion event to Orchestrator."""
        event_data = {
            "event_type": event_type,
            "camera_device_id": camera_device_id,
            "recording_session_id": recording_session_id,
            "video_file_path": video_file_path,
            "user_id": user_id,
            "recording_duration_seconds": recording_duration_seconds,
            "file_size_bytes": file_size_bytes,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        try:
            url = urljoin(self.base_url, "/workflows/camera/events")

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    url,
                    json=event_data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        logger.info(
                            f"✅ Successfully published {event_type} event for camera {camera_device_id}"
                        )
                        return True
                    else:
                        response_text = await response.text()
                        logger.error(
                            f"❌ Failed to publish event: HTTP {response.status} - {response_text}"
                        )
                        return False

        except asyncio.TimeoutError:
            logger.error(
                f"⏰ Timeout publishing {event_type} event for camera {camera_device_id}"
            )
            return False
        except Exception as e:
            logger.error(
                f"💥 Error publishing {event_type} event for camera {camera_device_id}: {e}"
            )
            return False

    async def publish_recording_completed_event(
        self,
        camera_device_id: str,
        recording_result: Dict[str, Any],
        user_id: str,
    ) -> bool:
        """Convenience method for publishing recording completion events."""
        return await self.publish_camera_event(
            event_type="recording_completed",
            camera_device_id=camera_device_id,
            recording_session_id=recording_result.get("recording_id", "unknown"),
            video_file_path=recording_result.get("file_path", ""),
            user_id=user_id,
            recording_duration_seconds=recording_result.get("duration_seconds", 0),
            file_size_bytes=recording_result.get("file_size_bytes", 0),
            metadata={
                "frame_count": recording_result.get("frame_count", 0),
                "collection_id": recording_result.get("collection_id"),
                "stopped_at": recording_result.get("stopped_at"),
            },
        )

    async def health_check(self) -> bool:
        """Check if Orchestrator Service is reachable."""
        try:
            url = urljoin(self.base_url, "/health")

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    return response.status == 200
        except Exception:
            return False
