"""
Route Aggregation Service
PPL Meta Platform - vmeta Service

Provides route aggregation and chronological sorting functionality
for cross-video individual tracking. Combines route points from
multiple video appearances into a unified chronological sequence.

Created: October 28, 2025
Author: PPL Meta Platform Team
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def aggregate_routes_chronologically(
    person_objects: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Aggregate routes from all person objects in chronological order.
    
    Combines route points from multiple person objects (video appearances)
    into a single chronological sequence sorted by timestamp. Each route
    point retains its video UUID for context.
    
    Args:
        person_objects: List of person object dicts with route data
        
    Returns:
        List of route points sorted by timestamp with structure:
        [
            {
                "x": float,
                "y": float,
                "timestamp": str (ISO format),
                "video_uuid": str,
                "confidence": float
            },
            ...
        ]
        
    Example:
        >>> person_objects = [
        ...     {
        ...         "video_uuid": "video-1",
        ...         "routes": [
        ...             {"x": 100, "y": 200, "timestamp": "2025-10-19T13:05:05Z"}
        ...         ]
        ...     },
        ...     {
        ...         "video_uuid": "video-2",
        ...         "routes": [
        ...             {"x": 150, "y": 180, "timestamp": "2025-10-19T13:14:10Z"}
        ...         ]
        ...     }
        ... ]
        >>> chronological = aggregate_routes_chronologically(person_objects)
        >>> len(chronological)
        2
    """
    all_routes = []
    
    for person_obj in person_objects:
        video_uuid = person_obj.get("video_uuid")
        routes = person_obj.get("routes", [])
        
        if not video_uuid:
            logger.warning("Person object missing video_uuid, skipping routes")
            continue
        
        for route_point in routes:
            # Add video context to each route point
            route_with_context = {
                "x": route_point.get("x"),
                "y": route_point.get("y"),
                "timestamp": route_point.get("timestamp"),
                "video_uuid": video_uuid,
                "confidence": route_point.get("confidence", 1.0)
            }
            
            # Validate required fields
            if None in (route_with_context["x"],
                       route_with_context["y"],
                       route_with_context["timestamp"]):
                logger.warning(
                    "Route point missing required fields, skipping"
                )
                continue
            
            all_routes.append(route_with_context)
    
    # Sort by timestamp
    try:
        all_routes.sort(
            key=lambda r: datetime.fromisoformat(
                r["timestamp"].replace('Z', '+00:00')
            )
        )
    except (ValueError, TypeError) as e:
        logger.error("Error sorting routes by timestamp: %s", e)
        # Return unsorted if sorting fails
        pass
    
    logger.info(
        "Aggregated %d route points from %d person objects",
        len(all_routes),
        len(person_objects)
    )
    
    # Calculate velocities for route points
    all_routes_with_velocity = calculate_route_velocities(all_routes)
    
    return all_routes_with_velocity


def calculate_statistics(
    person_objects: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate aggregate statistics for all person objects.
    
    Computes summary statistics including total faces, route points,
    average quality metrics, and video span.
    
    Args:
        person_objects: List of person object dictionaries
        
    Returns:
        Dictionary with aggregate statistics:
        {
            "total_person_objects": int,
            "total_faces": int,
            "total_route_points": int,
            "average_quality_score": float,
            "videos_spanned": int,
            "time_span_seconds": float or None
        }
        
    Example:
        >>> stats = calculate_statistics(person_objects)
        >>> print(f"Total faces: {stats['total_faces']}")
        >>> print(f"Average quality: {stats['average_quality_score']:.2f}")
    """
    if not person_objects:
        return {
            "total_person_objects": 0,
            "total_faces": 0,
            "total_route_points": 0,
            "average_quality_score": 0.0,
            "videos_spanned": 0,
            "time_span_seconds": None
        }
    
    # Import quality calculation here to avoid circular imports
    from .quality_selector import calculate_quality_score
    
    total_faces = sum(obj.get("face_count", 0) for obj in person_objects)
    total_routes = sum(len(obj.get("routes", [])) for obj in person_objects)
    
    # Calculate average quality score
    quality_scores = [
        calculate_quality_score(obj) for obj in person_objects
    ]
    avg_quality = (
        sum(quality_scores) / len(quality_scores)
        if quality_scores else 0.0
    )
    
    # Get unique video UUIDs
    unique_videos = set(
        obj.get("video_uuid")
        for obj in person_objects
        if obj.get("video_uuid")
    )
    
    # Calculate time span if timestamps available
    time_span = calculate_time_span(person_objects)
    
    statistics = {
        "total_person_objects": len(person_objects),
        "total_faces": total_faces,
        "total_route_points": total_routes,
        "average_quality_score": avg_quality,
        "videos_spanned": len(unique_videos),
        "time_span_seconds": time_span
    }
    
    logger.info(
        "Calculated statistics: %d objects, %d faces, %d routes, "
        "avg_quality=%.3f",
        statistics["total_person_objects"],
        statistics["total_faces"],
        statistics["total_route_points"],
        statistics["average_quality_score"]
    )
    
    return statistics


def calculate_time_span(
    person_objects: List[Dict[str, Any]]
) -> float | None:
    """
    Calculate time span across all person objects.
    
    Determines the total time duration from the earliest timestamp
    to the latest timestamp across all person objects.
    
    Args:
        person_objects: List of person object dictionaries
        
    Returns:
        Time span in seconds, or None if timestamps unavailable
        
    Example:
        >>> span = calculate_time_span(person_objects)
        >>> if span:
        ...     print(f"Individual tracked for {span/60:.1f} minutes")
    """
    timestamps = []
    
    for obj in person_objects:
        # Try to get timestamp from object
        if "timestamp" in obj:
            timestamps.append(obj["timestamp"])
        
        # Also check route points for timestamps
        routes = obj.get("routes", [])
        for route in routes:
            if "timestamp" in route:
                timestamps.append(route["timestamp"])
    
    if len(timestamps) < 2:
        return None
    
    try:
        # Parse all timestamps
        dt_timestamps = [
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
            for ts in timestamps
        ]
        
        earliest = min(dt_timestamps)
        latest = max(dt_timestamps)
        
        time_span_seconds = (latest - earliest).total_seconds()
        
        return time_span_seconds
        
    except (ValueError, TypeError) as e:
        logger.error("Error calculating time span: %s", e)
        return None


def group_routes_by_video(
    chronological_routes: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group chronological routes by video UUID.
    
    Organizes route points into groups by their source video while
    maintaining chronological order within each group.
    
    Args:
        chronological_routes: List of route points with video_uuid
        
    Returns:
        Dictionary mapping video_uuid to list of route points:
        {
            "video-uuid-1": [route1, route2, ...],
            "video-uuid-2": [route3, route4, ...],
            ...
        }
        
    Example:
        >>> routes = [
        ...     {"x": 100, "y": 200, "video_uuid": "v1", "timestamp": "..."},
        ...     {"x": 150, "y": 180, "video_uuid": "v2", "timestamp": "..."}
        ... ]
        >>> grouped = group_routes_by_video(routes)
        >>> len(grouped["v1"])
        1
    """
    grouped = {}
    
    for route in chronological_routes:
        video_uuid = route.get("video_uuid")
        if not video_uuid:
            continue
        
        if video_uuid not in grouped:
            grouped[video_uuid] = []
        
        grouped[video_uuid].append(route)
    
    logger.debug(
        "Grouped %d routes into %d videos",
        len(chronological_routes),
        len(grouped)
    )
    
    return grouped


def calculate_route_velocities(
    chronological_routes: List[Dict[str, Any]],
    max_points_threshold: int = 100,
    normalize_by_resolution: tuple = (1920, 1080)
) -> List[Dict[str, Any]]:
    """
    Calculate normalized pixel velocity for each route point.
    
    Computes velocity between consecutive route points using normalized
    pixel coordinates. If route has more points than threshold, samples
    evenly to avoid over-calculation.
    
    Args:
        chronological_routes: List of route points sorted by time
        max_points_threshold: Maximum points to process (default: 100)
        normalize_by_resolution: Video resolution for normalization (width, height)
        
    Returns:
        List of route points with added 'velocity' field (normalized pixels/second)
        
    Example:
        >>> routes_with_velocity = calculate_route_velocities(routes)
        >>> avg_velocity = sum(r['velocity'] for r in routes_with_velocity if r.get('velocity')) / len(routes_with_velocity)
    """
    if len(chronological_routes) < 2:
        return chronological_routes
    
    # Sample routes if above threshold
    routes_to_process = chronological_routes
    if len(chronological_routes) > max_points_threshold:
        # Calculate sampling step
        step = len(chronological_routes) // max_points_threshold
        routes_to_process = chronological_routes[::step]
        logger.info(
            f"Sampling {len(routes_to_process)} points from {len(chronological_routes)} "
            f"(threshold: {max_points_threshold})"
        )
    
    width, height = normalize_by_resolution
    routes_with_velocity = []
    
    for i, route in enumerate(routes_to_process):
        route_copy = route.copy()
        
        if i == 0:
            # First point has no velocity
            route_copy['velocity'] = None
        else:
            prev = routes_to_process[i - 1]
            
            try:
                # Normalize coordinates (0-1 range)
                x1_norm = prev['x'] / width
                y1_norm = prev['y'] / height
                x2_norm = route['x'] / width
                y2_norm = route['y'] / height
                
                # Calculate normalized distance
                dx = x2_norm - x1_norm
                dy = y2_norm - y1_norm
                distance_normalized = (dx ** 2 + dy ** 2) ** 0.5
                
                # Calculate time difference
                t1 = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(route['timestamp'].replace('Z', '+00:00'))
                time_diff_seconds = (t2 - t1).total_seconds()
                
                # Calculate velocity (normalized pixels per second)
                if time_diff_seconds > 0:
                    velocity = distance_normalized / time_diff_seconds
                    route_copy['velocity'] = round(velocity, 6)
                else:
                    route_copy['velocity'] = 0.0
                    
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Error calculating velocity for route point: {e}")
                route_copy['velocity'] = None
        
        routes_with_velocity.append(route_copy)
    
    # Calculate average velocity for logging
    velocities = [r['velocity'] for r in routes_with_velocity if r.get('velocity') is not None]
    if velocities:
        avg_velocity = sum(velocities) / len(velocities)
        logger.info(
            f"Calculated velocities for {len(routes_with_velocity)} points. "
            f"Average velocity: {avg_velocity:.6f} normalized px/s"
        )
    
    return routes_with_velocity


def calculate_movement_statistics(
    chronological_routes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate movement statistics from route points.
    
    Analyzes route points to compute movement metrics such as
    total distance traveled, average speed, and movement patterns.
    
    Args:
        chronological_routes: List of route points sorted by time
        
    Returns:
        Dictionary with movement statistics:
        {
            "total_distance_pixels": float,
            "average_speed_pixels_per_second": float or None,
            "direction_changes": int,
            "stationary_percentage": float
        }
        
    Example:
        >>> movement_stats = calculate_movement_statistics(routes)
        >>> print(f"Distance: {movement_stats['total_distance_pixels']:.0f}px")
    """
    if len(chronological_routes) < 2:
        return {
            "total_distance_pixels": 0.0,
            "average_speed_pixels_per_second": None,
            "direction_changes": 0,
            "stationary_percentage": 0.0
        }
    
    total_distance = 0.0
    stationary_count = 0
    movement_threshold = 5.0  # pixels
    
    for i in range(1, len(chronological_routes)):
        prev = chronological_routes[i - 1]
        curr = chronological_routes[i]
        
        # Calculate Euclidean distance
        dx = curr["x"] - prev["x"]
        dy = curr["y"] - prev["y"]
        distance = (dx ** 2 + dy ** 2) ** 0.5
        
        total_distance += distance
        
        if distance < movement_threshold:
            stationary_count += 1
    
    # Calculate average speed if timestamps available
    avg_speed = None
    try:
        start_time = datetime.fromisoformat(
            chronological_routes[0]["timestamp"].replace('Z', '+00:00')
        )
        end_time = datetime.fromisoformat(
            chronological_routes[-1]["timestamp"].replace('Z', '+00:00')
        )
        duration = (end_time - start_time).total_seconds()
        
        if duration > 0:
            avg_speed = total_distance / duration
    except (ValueError, TypeError, KeyError):
        pass
    
    stationary_pct = (
        (stationary_count / (len(chronological_routes) - 1)) * 100
        if len(chronological_routes) > 1 else 0.0
    )
    
    return {
        "total_distance_pixels": total_distance,
        "average_speed_pixels_per_second": avg_speed,
        "direction_changes": 0,  # TODO: Implement direction change detection
        "stationary_percentage": stationary_pct
    }
