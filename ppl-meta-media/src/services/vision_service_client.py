"""
PPL Meta Media Service - Vision Service Client
Phase 6: Enhanced integration for bulk face detection result sharing
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class VisionServiceClient:
    """
    HTTP client for sending processed face detection results to Vision Service.

    This client enables Media Service to send bulk face detection results
    to Vision Service for storage, analytics, and cross-video processing.
    """

    def __init__(self, base_url: str = "http://localhost:8003"):
        """Initialize Vision Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def health_check(self) -> Dict[str, Any]:
        """Check Vision Service health."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"status": "healthy", "data": data}
                    else:
                        return {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status}",
                        }
        except Exception as e:
            logger.error(f"Vision Service health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def send_bulk_face_detection_results(
        self,
        workflow_id: str,
        results: List[Dict[str, Any]],
        source_service: str = "ppl-meta-media",
    ) -> Dict[str, Any]:
        """
        Send bulk face detection results to Vision Service for storage.

        Args:
            workflow_id: Identifier for the workflow that generated results
            results: List of media results with face detection data
            source_service: Name of the source service (default: ppl-meta-media)

        Returns:
            Response from Vision Service with storage summary
        """
        try:
            # Format results for Vision Service bulk storage endpoint
            formatted_results = []
            for result in results:
                formatted_result = {
                    "media_id": result.get("media_id"),
                    "frame_number": result.get("frame_number"),
                    "timestamp": result.get("timestamp"),
                    "detections": [],
                    "processing_metadata": result.get("metadata", {}),
                }

                # Convert detections to Vision Service format
                for detection in result.get("detections", []):
                    formatted_detection = {
                        "bbox": detection.get("bbox", []),
                        "confidence": detection.get("confidence", 0.0),
                        "method": detection.get("method", "unknown"),
                    }
                    formatted_result["detections"].append(formatted_detection)

                formatted_results.append(formatted_result)

            payload = {
                "workflow_id": workflow_id,
                "results": formatted_results,
                "source_service": source_service,
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/faces/bulk-store", json=payload
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        logger.info(
                            f"Successfully sent {len(formatted_results)} "
                            f"results to Vision Service for workflow {workflow_id}"
                        )
                        return {
                            "success": True,
                            "vision_service_response": response_data,
                        }
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Vision Service rejected bulk results: "
                            f"HTTP {response.status} - {error_text}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                        }

        except asyncio.TimeoutError:
            logger.error(f"Timeout sending bulk results to Vision Service")
            return {
                "success": False,
                "error": "Timeout communicating with Vision Service",
            }

        except Exception as e:
            logger.error(f"Failed to send bulk results to Vision Service: {e}")
            return {"success": False, "error": str(e)}

    async def send_bulk_face_detection_results_with_sessions(
        self,
        workflow_id: str,
        results: List[Dict[str, Any]],
        source_service: str = "ppl-meta-media",
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send bulk face detection results to Vision Service with session tracking.

        This method uses the session-aware Vision Service endpoint that:
        1. Creates face detection sessions automatically
        2. Stores faces with session UUIDs
        3. Auto-triggers PPL Thread workflow for person objects processing

        Args:
            workflow_id: Identifier for the workflow that generated results
            results: List of media results with face detection data
            source_service: Name of the source service (default: ppl-meta-media)
            authorization: JWT token for authentication (Bearer token)

        Returns:
            Response from Vision Service with session tracking summary
        """
        try:
            # 🎯 FIX: Group results by media_id since each media needs its own session
            media_results = {}
            for result in results:
                media_id = result.get("media_id")
                if media_id not in media_results:
                    media_results[media_id] = {
                        "faces_by_frame": {},
                        "total_frames": 0,
                        "metadata": result.get("metadata", {}),
                    }

                # Add detections to frames structure expected by Vision Service
                frame_number = str(result.get("frame_number", 0))
                if frame_number not in media_results[media_id]["faces_by_frame"]:
                    media_results[media_id]["faces_by_frame"][frame_number] = []

                for detection in result.get("detections", []):
                    face_data = {
                        "bbox": detection.get("bbox", []),
                        "confidence": detection.get("confidence", 0.0),
                        "method": detection.get("method", "two_stage"),
                        "timestamp": result.get("timestamp", 0.0),
                    }
                    media_results[media_id]["faces_by_frame"][frame_number].append(
                        face_data
                    )

                media_results[media_id]["total_frames"] = max(
                    media_results[media_id]["total_frames"], int(frame_number) + 1
                )

            successful_media = 0
            total_faces_stored = 0
            session_uuids = []

            # Process each media item with session-aware endpoint
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                for media_id, media_data in media_results.items():
                    try:
                        # 🎯 KEY FIX: Use session-aware endpoint instead of raw bulk storage
                        endpoint_url = f"{self.base_url}/faces/media/{media_id}/bulk"

                        payload = {
                            "faces_by_frame": media_data["faces_by_frame"],
                            "total_frames": media_data["total_frames"],
                            "workflow_id": workflow_id,
                            "source_service": source_service,
                            "metadata": media_data["metadata"],
                        }

                        # 🔒 Add authorization header if provided
                        headers = {}
                        if authorization:
                            headers["Authorization"] = f"Bearer {authorization}"
                            logger.info(
                                f"🔐 AUTH: Sending to Vision Service WITH auth "
                                f"(media {media_id})"
                            )
                        else:
                            logger.warning(
                                f"⚠️ AUTH: Sending to Vision Service WITHOUT auth "
                                f"(media {media_id})"
                            )

                        logger.info(
                            f"🎯 SESSION-AWARE: Sending "
                            f"{len(media_data['faces_by_frame'])} frames "
                            f"for media {media_id}"
                        )

                        async with session.post(
                            endpoint_url, json=payload, headers=headers
                        ) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                successful_media += 1
                                faces_stored = response_data.get("stored_faces", 0)
                                total_faces_stored += faces_stored
                                session_uuid = response_data.get("session_uuid", "N/A")
                                session_uuids.append(session_uuid)

                                logger.info(
                                    f"✅ SESSION-AWARE: Media {media_id} processed successfully - "
                                    f"{faces_stored} faces stored with session {session_uuid} "
                                    f"(PPL Thread auto-triggered: {response_data.get('ppl_thread_triggered', False)})"
                                )
                            else:
                                error_text = await response.text()
                                logger.error(
                                    f"❌ SESSION-AWARE: Failed for media {media_id}: "
                                    f"HTTP {response.status} - {error_text}"
                                )
                    except Exception as e:
                        logger.error(
                            f"❌ SESSION-AWARE: Exception processing media {media_id}: {e}"
                        )
                        continue

            return {
                "success": True,
                "session_aware_processing": True,
                "workflow_id": workflow_id,
                "media_processed": successful_media,
                "total_media_items": len(media_results),
                "total_faces_stored": total_faces_stored,
                "session_uuids": session_uuids,
                "message": f"Successfully processed {successful_media}/{len(media_results)} media items with session tracking and auto PPL Thread trigger",
            }

        except asyncio.TimeoutError:
            logger.error(f"❌ SESSION-AWARE: Timeout sending results to Vision Service")
            return {
                "success": False,
                "error": "Timeout communicating with Vision Service",
            }
        except Exception as e:
            logger.error(
                f"❌ SESSION-AWARE: Error sending results to Vision Service: {e}"
            )
            return {"success": False, "error": str(e)}

    async def get_workflow_analytics(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get analytics data for a specific workflow from Vision Service.

        Args:
            workflow_id: The workflow identifier

        Returns:
            Analytics data from Vision Service
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/analytics/workflow/{workflow_id}"
                ) as response:
                    if response.status == 200:
                        analytics_data = await response.json()
                        return {"success": True, "analytics": analytics_data}
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                        }

        except Exception as e:
            logger.error(f"Failed to get workflow analytics: {e}")
            return {"success": False, "error": str(e)}

    async def get_media_face_data(
        self, media_id: str, confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get stored face detection data for a specific media item.

        Args:
            media_id: The media identifier
            confidence_threshold: Minimum confidence threshold for faces

        Returns:
            Face detection data from Vision Service
        """
        try:
            params = {"confidence_threshold": confidence_threshold}

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/faces/media/{media_id}", params=params
                ) as response:
                    if response.status == 200:
                        face_data = await response.json()
                        return {"success": True, "face_data": face_data}
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                        }

        except Exception as e:
            logger.error(f"Failed to get media face data: {e}")
            return {"success": False, "error": str(e)}

    async def check_existing_faces(self, media_id: str) -> Dict[str, Any]:
        """
        Check if Vision Service already has face detection results for a media file.

        This method helps prevent duplicate processing by checking for existing
        face detection data before starting new processing workflows.

        Args:
            media_id: The media UUID to check

        Returns:
            Dictionary with has_existing_faces (bool) and face_count (int)
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/faces/media/{media_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        face_count = data.get("total_faces", 0)
                        has_faces = data.get("has_stored_faces", False)
                        return {
                            "has_existing_faces": has_faces and face_count > 0,
                            "face_count": face_count,
                            "success": True,
                        }
                    elif response.status == 404:
                        # No faces found - this is normal for new media
                        return {
                            "has_existing_faces": False,
                            "face_count": 0,
                            "success": True,
                        }
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"Failed to check existing faces for {media_id}: "
                            f"HTTP {response.status}: {error_text}"
                        )
                        return {
                            "has_existing_faces": False,
                            "face_count": 0,
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                        }

        except Exception as e:
            logger.error(f"Failed to check existing faces for {media_id}: {e}")
            return {
                "has_existing_faces": False,
                "face_count": 0,
                "success": False,
                "error": str(e),
            }
