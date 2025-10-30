"""
Orchestrator Service HTTP Client
PPL Meta Platform - vmeta Service

Provides HTTP client functionality for fetching person object data
from the Orchestrator service. Used for cross-video individual analysis
to retrieve detailed face data, routes, and quality metrics.

Created: October 28, 2025
Author: PPL Meta Platform Team
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Orchestrator service base URL (can be overridden via environment variable)
ORCHESTRATOR_BASE_URL = "http://localhost:8002"


async def fetch_person_object_from_orchestrator(
    video_uuid: str,
    person_uuid: str,
    auth_token: Optional[str] = None,
    orchestrator_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch person object data from Orchestrator service.
    
    Makes an HTTP GET request to the Orchestrator's person-objects endpoint
    to retrieve complete person object data including faces, routes, and
    quality metrics for a specific video.
    
    Args:
        video_uuid: UUID of the video containing the person object
        person_uuid: UUID of the specific person object to fetch
        auth_token: Optional Bearer token for authentication (format: "Bearer <token>")
        orchestrator_url: Optional custom Orchestrator base URL
        
    Returns:
        Dictionary containing person object data with the following structure:
        {
            "person_uuid": str,
            "video_uuid": str,
            "person_id": str,
            "face_count": int,
            "faces": List[Dict],  # Face data with bbox, confidence, quality_metrics
            "routes": List[Dict],  # Route points with x, y, timestamp
            "quality_metrics": Dict,  # average_sharpness, average_brightness, average_confidence
            "timestamp": str  # ISO format datetime of first appearance
        }
        
        Returns None if:
        - HTTP request fails
        - Response status is not 200
        - Person object not found in response
        - Response format is invalid
        
    Raises:
        Does not raise exceptions - returns None on error and logs the issue
        
    Example:
        >>> person_obj = await fetch_person_object_from_orchestrator(
        ...     video_uuid="7b462847-cd1f-441a-8bd9-aaed6643b7cb",
        ...     person_uuid="uuid-123",
        ...     auth_token="Bearer eyJ..."
        ... )
        >>> if person_obj:
        ...     print(f"Found {person_obj['face_count']} faces")
    """
    base_url = orchestrator_url or ORCHESTRATOR_BASE_URL
    
    try:
        headers = {}
        if auth_token:
            # Ensure token has Bearer prefix
            if not auth_token.startswith("Bearer "):
                headers["Authorization"] = f"Bearer {auth_token}"
            else:
                headers["Authorization"] = auth_token
        
        logger.info(f"Fetching person object from Orchestrator: video={video_uuid}, person={person_uuid}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/person-objects/{video_uuid}",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.warning(
                    f"Orchestrator returned status {response.status_code} for video {video_uuid}"
                )
                return None
            
            data = response.json()
            
            # Validate response structure
            if not data.get("success") or data.get("status") != "completed":
                logger.warning(
                    f"Orchestrator response not successful or not completed for video {video_uuid}"
                )
                return None
            
            # Find the specific person object by UUID in person_groups
            person_groups = data.get("person_groups", [])
            for group in person_groups:
                if group.get("person_uuid") == person_uuid:
                    # Extract and structure the data
                    person_obj = {
                        "person_uuid": person_uuid,
                        "video_uuid": video_uuid,
                        "person_id": group.get("person_id", "unknown"),
                        "face_count": group.get("face_count", 0),
                        "faces": group.get("all_faces", []),
                        "routes": extract_routes(group),
                        "quality_metrics": group.get("quality_metrics", {}),
                        "timestamp": group.get("first_seen", datetime.utcnow().isoformat())
                    }
                    
                    logger.info(
                        f"Successfully fetched person object: {person_uuid} from video {video_uuid} "
                        f"({person_obj['face_count']} faces, {len(person_obj['routes'])} route points)"
                    )
                    
                    return person_obj
            
            logger.warning(
                f"Person object {person_uuid} not found in Orchestrator response for video {video_uuid}"
            )
            return None
            
    except httpx.TimeoutException:
        logger.error(
            f"Timeout fetching person object from Orchestrator: video={video_uuid}, person={person_uuid}"
        )
        return None
    except httpx.HTTPError as e:
        logger.error(
            f"HTTP error fetching person object from Orchestrator: {e}, "
            f"video={video_uuid}, person={person_uuid}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error fetching person object from Orchestrator: {e}, "
            f"video={video_uuid}, person={person_uuid}"
        )
        return None


def extract_routes(person_group: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract route points from person group data.
    
    Parses the movement_tracking data from Orchestrator's person_group
    response and extracts route points with coordinates and timestamps.
    
    Args:
        person_group: Person group dictionary from Orchestrator response
        
    Returns:
        List of route point dictionaries with structure:
        [
            {
                "x": float,
                "y": float,
                "timestamp": str (ISO format),
                "confidence": float (default 1.0)
            },
            ...
        ]
        
        Returns empty list if no route data available.
        
    Example:
        >>> person_group = {
        ...     "movement_tracking": {
        ...         "route_points": [
        ...             {"x": 100.5, "y": 200.3, "timestamp": "2025-10-19T13:05:05Z"},
        ...             {"x": 150.2, "y": 180.7, "timestamp": "2025-10-19T13:05:10Z"}
        ...         ]
        ...     }
        ... }
        >>> routes = extract_routes(person_group)
        >>> len(routes)
        2
    """
    movement_tracking = person_group.get("movement_tracking", {})
    route_points = movement_tracking.get("route_points", [])
    
    # Ensure all route points have required fields
    processed_routes = []
    for route in route_points:
        if "x" in route and "y" in route:
            processed_route = {
                "x": route["x"],
                "y": route["y"],
                "timestamp": route.get("timestamp", datetime.utcnow().isoformat()),
                "confidence": route.get("confidence", 1.0)
            }
            processed_routes.append(processed_route)
    
    return processed_routes


async def fetch_multiple_person_objects(
    video_person_pairs: List[tuple[str, str]],
    auth_token: Optional[str] = None,
    orchestrator_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch multiple person objects in parallel.
    
    Efficiently fetches person object data for multiple video/person UUID pairs
    using async parallel requests. Failed requests are logged but don't prevent
    successful fetches from being returned.
    
    Args:
        video_person_pairs: List of (video_uuid, person_uuid) tuples
        auth_token: Optional Bearer token for authentication
        orchestrator_url: Optional custom Orchestrator base URL
        
    Returns:
        List of person object dictionaries (only successful fetches)
        
    Example:
        >>> pairs = [
        ...     ("video-1", "person-1"),
        ...     ("video-2", "person-2"),
        ... ]
        >>> objects = await fetch_multiple_person_objects(pairs, auth_token="Bearer ...")
        >>> print(f"Fetched {len(objects)} person objects")
    """
    import asyncio
    
    tasks = [
        fetch_person_object_from_orchestrator(
            video_uuid=video_uuid,
            person_uuid=person_uuid,
            auth_token=auth_token,
            orchestrator_url=orchestrator_url
        )
        for video_uuid, person_uuid in video_person_pairs
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None values and exceptions
    person_objects = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Exception in parallel fetch: {result}")
        elif result is not None:
            person_objects.append(result)
    
    logger.info(
        f"Fetched {len(person_objects)} person objects out of {len(video_person_pairs)} requests"
    )
    
    return person_objects
