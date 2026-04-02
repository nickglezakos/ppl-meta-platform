"""
Individual Routes Data Models
Pydantic models for paginated route point retrieval per individual.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RoutePoint(BaseModel):
    """Single spatial route point captured from a face detection."""

    sequence_number: int = Field(
        ..., description="Detection order within person object"
    )
    timestamp_ms: int = Field(..., description="Milliseconds from video start")
    center_x: float = Field(..., description="X center coordinate (pixels)")
    center_y: float = Field(..., description="Y center coordinate (pixels)")
    velocity_x: float = Field(0.0, description="X velocity (pixels/second)")
    velocity_y: float = Field(0.0, description="Y velocity (pixels/second)")
    velocity_magnitude: float = Field(
        0.0, description="Movement speed (pixels/second)"
    )
    direction_radians: float = Field(
        0.0, description="Movement direction in radians"
    )
    confidence_score: float = Field(
        ..., description="Detection confidence 0–1"
    )
    detection_quality: Optional[str] = Field(
        None, description="excellent/good/fair/poor"
    )
    video_uuid: Optional[str] = Field(None, description="Source video UUID")
    person_object_uuid: Optional[str] = Field(
        None, description="Person object UUID"
    )


class RoutePointWithCamera(RoutePoint):
    """Route point annotated with camera and individual context."""

    camera_id: Optional[str] = Field(
        None, description="Source camera identifier"
    )
    camera_name: Optional[str] = Field(
        None, description="Display name for source camera"
    )
    individual_uuid: Optional[str] = Field(
        None, description="Individual UUID owning the point"
    )


class RouteSummary(BaseModel):
    """Aggregate stats for an individual's route across all videos."""

    total_points: int = Field(
        0, description="Total route points across all pages"
    )
    total_appearances: int = Field(0, description="Total video appearances")
    start_time_ms: Optional[int] = Field(
        None, description="Earliest timestamp_ms seen"
    )
    end_time_ms: Optional[int] = Field(
        None, description="Latest timestamp_ms seen"
    )


class RoutePage(BaseModel):
    """Paging envelope returned with route data."""

    page_index: int = Field(..., description="Zero-based page index requested")
    page_size: int = Field(..., description="Points per page requested")
    total_points: int = Field(..., description="Total route points available")
    has_more: bool = Field(..., description="True when further pages exist")


class RoutePageResponse(BaseModel):
    """Full paginated route response for a single individual."""

    individual_uuid: str
    route_summary: RouteSummary
    page: RoutePage
    points: List[RoutePoint]


class CameraRoutePageResponse(BaseModel):
    """Paginated route response for one individual within one camera."""

    individual_uuid: str
    route_summary: RouteSummary
    page: RoutePage
    points: List[RoutePointWithCamera]


class CameraRoutesGroup(BaseModel):
    """Camera-first grouping envelope containing all relevant individuals."""

    camera_id: str
    camera_name: Optional[str] = None
    total_points_across_individuals: int = 0
    total_appearances_across_individuals: int = 0
    has_more: bool = False
    individuals: List[CameraRoutePageResponse] = Field(default_factory=list)


class RoutesByCameraResponse(BaseModel):
    """Route payload grouped by camera first and then by individual."""

    requested_individual_uuid: str
    cameras: List[CameraRoutesGroup] = Field(default_factory=list)


class CameraRouteMetadata(BaseModel):
    """Metadata-only view for a single camera group."""

    camera_id: str
    camera_name: Optional[str] = None
    total_points: int = 0
    total_appearances: int = 0
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None


class RoutesMetadataByCameraResponse(BaseModel):
    """Metadata-only response grouped by camera."""

    requested_individual_uuid: str
    cameras: List[CameraRouteMetadata] = Field(default_factory=list)


class RouteMetadataResponse(BaseModel):
    """Lightweight metadata-only response (no point payload)."""

    individual_uuid: str
    total_points: int
    total_appearances: int
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    per_video_counts: List[Dict] = Field(
        default_factory=list,
        description="List of {video_uuid, point_count} per source video",
    )
