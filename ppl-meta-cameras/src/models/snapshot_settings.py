"""Snapshot settings models for enhanced snapshot capture."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class SnapshotFormat(str, Enum):
    """Supported snapshot formats."""

    JPEG = "JPEG"
    PNG = "PNG"
    BMP = "BMP"


class SnapshotResolution(BaseModel):
    """Resolution settings for snapshot capture."""

    width: int = Field(..., ge=1, le=7680, description="Width in pixels")
    height: int = Field(..., ge=1, le=4320, description="Height in pixels")

    @validator("width", "height")
    def validate_resolution(cls, v):
        """Validate resolution values."""
        if v % 2 != 0:
            # Ensure even numbers for video encoding compatibility
            v = v + 1 if v < 7680 else v - 1
        return v


class SnapshotSettings(BaseModel):
    """Enhanced snapshot capture settings."""

    resolution: Optional[str] = Field(
        default="max",
        description="Resolution: 'max', 'stream', or 'WIDTHxHEIGHT' format",
    )
    quality: int = Field(
        default=95, ge=70, le=100, description="JPEG quality (70-100%)"
    )
    format: SnapshotFormat = Field(
        default=SnapshotFormat.JPEG, description="Image format"
    )
    save_to_file: bool = Field(
        default=True, description="Save snapshot to server file system"
    )
    filename: Optional[str] = Field(
        default=None, description="Custom filename (auto-generated if not provided)"
    )

    @validator("resolution")
    def validate_resolution_format(cls, v):
        """Validate resolution format."""
        if v in ["max", "stream"]:
            return v

        # Check for WIDTHxHEIGHT format
        if "x" in v:
            try:
                width, height = v.split("x")
                width, height = int(width), int(height)
                if 1 <= width <= 7680 and 1 <= height <= 4320:
                    return f"{width}x{height}"
            except (ValueError, IndexError):
                pass

        raise ValueError("Resolution must be 'max', 'stream', or 'WIDTHxHEIGHT' format")


class CameraCapabilities(BaseModel):
    """Camera capabilities including supported resolutions."""

    device_id: str
    max_resolution: SnapshotResolution
    supported_resolutions: list[SnapshotResolution]
    supports_formats: list[SnapshotFormat]
    current_stream_resolution: Optional[SnapshotResolution] = None

    class Config:
        use_enum_values = True


class EnhancedSnapshotResult(BaseModel):
    """Enhanced snapshot capture result with metadata."""

    device_id: str
    filename: str
    file_size_bytes: int
    resolution: SnapshotResolution
    format: SnapshotFormat
    quality: int
    timestamp: float
    captured_at: str
    base64_image: str
    download_url: str
    metadata: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True
