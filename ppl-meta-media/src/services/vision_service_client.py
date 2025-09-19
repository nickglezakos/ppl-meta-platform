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
