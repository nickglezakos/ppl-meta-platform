"""
Route Data Builder Utility

Builds route/movement data for MVR people from person objects.
Handles both photo (single-point) and video (multi-point) route data.

Author: PPL Meta Platform
Date: November 29, 2025
Version: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional
import math

logger = logging.getLogger(__name__)

# Route sampling threshold
ROUTE_SAMPLING_THRESHOLD = 100


def build_route_data_for_photo(
    person_object: Dict[str, Any],
    confidence: float = 0.9
) -> Dict[str, Any]:
    """
    Build single-point route data for a photo.
    
    Photos have no temporal dimension, so route data consists of a single
    point at the face center with timestamp=0.0 and zero velocity.
    
    Args:
        person_object: Person object with bounding box
        confidence: Detection confidence
        
    Returns:
        Dict with route data structure
        
    Example person_object:
    {
        "person_object_uuid": "...",
        "bbox": [x, y, width, height],
        "confidence": 0.94
    }
    """
    bbox = person_object.get('bbox', [0, 0, 0, 0])
    
    # Calculate face center from bounding box
    x, y, width, height = bbox[0], bbox[1], bbox[2], bbox[3]
    center_x = x + width / 2.0
    center_y = y + height / 2.0
    
    # Create single route point
    route_point = {
        "center_x": center_x,
        "center_y": center_y,
        "timestamp": 0.0,
        "frame_number": 0,
        "velocity_x": 0.0,
        "velocity_y": 0.0,
        "confidence": confidence
    }
    
    route_data = {
        "route_points": [route_point],
        "total_detections": 1,
        "sampled_points": 1,
        "movement_duration": 0.0,
        "average_velocity": 0.0
    }
    
    logger.debug(
        f"Built photo route data: center=({center_x:.1f}, {center_y:.1f})"
    )
    
    return route_data


def calculate_velocities(
    route_points: List[Dict[str, Any]],
    video_width: int = 1920,
    video_height: int = 1080
) -> List[float]:
    """
    Calculate normalized velocities between consecutive route points.
    
    Args:
        route_points: List of route points with center_x, center_y, timestamp
        video_width: Video resolution width (for normalization)
        video_height: Video resolution height (for normalization)
        
    Returns:
        List of velocity values (normalized px/s)
    """
    velocities = []
    
    for i in range(1, len(route_points)):
        prev = route_points[i - 1]
        curr = route_points[i]
        
        # Normalize coordinates
        x1_norm = prev['center_x'] / video_width
        y1_norm = prev['center_y'] / video_height
        x2_norm = curr['center_x'] / video_width
        y2_norm = curr['center_y'] / video_height
        
        # Calculate distance
        dx = x2_norm - x1_norm
        dy = y2_norm - y1_norm
        distance_normalized = math.sqrt(dx**2 + dy**2)
        
        # Time difference
        time_diff = curr['timestamp'] - prev['timestamp']
        
        if time_diff > 0:
            velocity = distance_normalized / time_diff
            velocities.append(velocity)
        else:
            velocities.append(0.0)
    
    return velocities


def sample_route_points(
    route_points: List[Dict[str, Any]],
    threshold: int = ROUTE_SAMPLING_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Sample route points using uniform interval algorithm.
    
    Always preserves first and last points.
    
    Args:
        route_points: Full list of route points
        threshold: Maximum points to return (default: 100)
        
    Returns:
        Sampled route points
    """
    if len(route_points) <= threshold:
        return route_points
    
    # Calculate sampling interval
    interval = math.ceil(len(route_points) / threshold)
    
    sampled = []
    
    # Always include first point
    sampled.append(route_points[0])
    
    # Sample intermediate points
    for i in range(interval, len(route_points) - 1, interval):
        sampled.append(route_points[i])
    
    # Always include last point
    if route_points[-1] not in sampled:
        sampled.append(route_points[-1])
    
    logger.debug(
        f"Sampled route points: {len(route_points)} → {len(sampled)} "
        f"(interval={interval})"
    )
    
    return sampled


def build_route_data_for_video(
    person_objects: List[Dict[str, Any]],
    video_width: int = 1920,
    video_height: int = 1080
) -> Dict[str, Any]:
    """
    Build multi-point route data for a video.
    
    Videos have temporal movement tracking with multiple route points
    captured over the video duration. Includes velocity calculation
    and optional sampling if points exceed threshold.
    
    Args:
        person_objects: List of person objects with route_points or tracking data
        video_width: Video resolution width
        video_height: Video resolution height
        
    Returns:
        Dict with route data structure
        
    Example person_objects:
    [
        {
            "person_object_uuid": "...",
            "movement_tracking": {
                "route_points": [
                    {
                        "center_x": 450.2,
                        "center_y": 320.8,
                        "timestamp": 13.333333,
                        "frame_number": 400,
                        "confidence": 0.93
                    },
                    ...
                ]
            }
        }
    ]
    """
    # Extract route points from person objects
    all_route_points = []
    
    for person_obj in person_objects:
        # Check for movement_tracking structure
        movement = person_obj.get('movement_tracking', {})
        points = movement.get('route_points', [])
        
        if not points:
            # Try alternate structure (flat route_points)
            points = person_obj.get('route_points', [])
        
        all_route_points.extend(points)
    
    if not all_route_points:
        logger.warning("No route points found for video, returning empty route data")
        return {
            "route_points": [],
            "total_detections": 0,
            "sampled_points": 0,
            "movement_duration": 0.0,
            "average_velocity": 0.0
        }
    
    # Sort by timestamp
    all_route_points.sort(key=lambda p: p.get('timestamp', 0))
    
    # Calculate velocities
    velocities = calculate_velocities(
        all_route_points,
        video_width=video_width,
        video_height=video_height
    )
    
    average_velocity = sum(velocities) / len(velocities) if velocities else 0.0
    
    # Add velocity fields to route points
    for i, point in enumerate(all_route_points):
        if i == 0:
            point['velocity_x'] = 0.0
            point['velocity_y'] = 0.0
        else:
            prev = all_route_points[i - 1]
            time_diff = point['timestamp'] - prev['timestamp']
            
            if time_diff > 0:
                point['velocity_x'] = (point['center_x'] - prev['center_x']) / time_diff
                point['velocity_y'] = (point['center_y'] - prev['center_y']) / time_diff
            else:
                point['velocity_x'] = 0.0
                point['velocity_y'] = 0.0
    
    # Apply sampling if needed
    total_detections = len(all_route_points)
    sampled_points = all_route_points
    
    if total_detections > ROUTE_SAMPLING_THRESHOLD:
        sampled_points = sample_route_points(
            all_route_points,
            threshold=ROUTE_SAMPLING_THRESHOLD
        )
    
    # Calculate movement duration
    movement_duration = 0.0
    if len(all_route_points) > 1:
        movement_duration = (
            all_route_points[-1]['timestamp'] - all_route_points[0]['timestamp']
        )
    
    route_data = {
        "route_points": sampled_points,
        "total_detections": total_detections,
        "sampled_points": len(sampled_points),
        "movement_duration": movement_duration,
        "average_velocity": average_velocity
    }
    
    logger.debug(
        f"Built video route data: {total_detections} points "
        f"(sampled to {len(sampled_points)}), "
        f"duration={movement_duration:.1f}s, "
        f"avg_velocity={average_velocity:.4f}"
    )
    
    return route_data


def build_route_data(
    media_type: str,
    person_objects: List[Dict[str, Any]],
    video_width: int = 1920,
    video_height: int = 1080,
    include_route: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Build route data based on media type (photo or video).
    
    Args:
        media_type: "photo" or "video"
        person_objects: List of person objects
        video_width: Video/photo resolution width
        video_height: Video/photo resolution height
        include_route: Whether to include route data
        
    Returns:
        Route data dict or None if not requested
    """
    if not include_route:
        return None
    
    if not person_objects:
        logger.warning("No person objects provided for route data")
        return None
    
    if media_type == 'photo':
        # Use first person object for single-point route
        return build_route_data_for_photo(
            person_objects[0],
            confidence=person_objects[0].get('confidence', 0.9)
        )
    
    elif media_type == 'video':
        # Build multi-point route from all person objects
        return build_route_data_for_video(
            person_objects,
            video_width=video_width,
            video_height=video_height
        )
    
    else:
        logger.error(f"Unknown media type: {media_type}")
        return None
