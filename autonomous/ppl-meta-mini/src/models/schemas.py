"""
Pydantic models for PPL Meta Mini API schemas.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FaceDetectionData(BaseModel):
    """Face detection data point."""

    Frame_Number: int = Field(..., description="Frame number in video")
    Face_ID: str = Field(..., description="Unique face identifier")
    Position_X: float = Field(..., description="X coordinate of face")
    Position_Y: float = Field(..., description="Y coordinate of face")


class GroupingRequest(BaseModel):
    """Request for face grouping operation."""

    face_data: List[FaceDetectionData] = Field(
        ..., description="List of face detection data points"
    )
    max_faces_per_frame: int = Field(2, description="Maximum allowed faces per frame")
    proximity_threshold: float = Field(
        50.0, description="Y-coordinate proximity threshold for grouping"
    )


class GroupStatistics(BaseModel):
    """Statistics about grouping operation."""

    original_unique_faces: int
    merged_groups_count: int
    total_detections: int
    frames_processed: int


class GroupingResponse(BaseModel):
    """Response from face grouping operation."""

    original_groups: int = Field(..., description="Number of original groups")
    merged_groups: int = Field(..., description="Number of merged groups")
    group_tracking: List[Dict[str, Any]] = Field(
        ..., description="Group tracking information"
    )
    statistics: GroupStatistics = Field(..., description="Grouping statistics")
    regrouped_data: List[Dict[str, Any]] = Field(..., description="Regrouped face data")


class VisualizationRequest(BaseModel):
    """Request for visualization generation."""

    face_data: List[FaceDetectionData] = Field(
        ..., description="Face detection data to visualize"
    )
    visualization_type: str = Field(
        "3d_trajectory",
        description="Type of visualization (3d_trajectory, 2d_scatter, timeline)",
    )
    x_axis: str = Field("Position_X", description="X-axis data field")
    y_axis: str = Field("Position_Y", description="Y-axis data field")
    z_axis: str = Field("Frame_Number", description="Z-axis data field")
    reverse_z: bool = Field(False, description="Reverse Z-axis order")


class VisualizationResponse(BaseModel):
    """Response from visualization generation."""

    visualization_type: str
    html_content: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]
