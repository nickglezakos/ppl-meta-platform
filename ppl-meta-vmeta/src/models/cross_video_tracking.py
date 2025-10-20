"""
Cross-Video Individual Tracking - Core Data Models
PPL Meta Platform v2.19.13+

This module contains the core Pydantic models for cross-video individual tracking,
including tracking sessions, individuals, and algorithm configurations.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import hashlib
import json


# =============================================
# ENUMS FOR STATUS AND TYPES
# =============================================

class SessionStatus(str, Enum):
    """Tracking session status enumeration."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ProcessingStatus(str, Enum):
    """Video processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class ProcessingType(str, Enum):
    """Individual processing type enumeration."""
    NEW = "new"
    CACHED = "cached"
    MERGED = "merged"
    EXTENDED = "extended"


# =============================================
# ALGORITHM CONFIGURATION
# =============================================

class CrossVideoTrackingConfig(BaseModel):
    """
    Configuration parameters for cross-video individual tracking algorithm.
    
    This model defines all tunable parameters that affect algorithm behavior,
    accuracy, and performance characteristics.
    """
    
    # Configuration metadata
    config_name: str = Field(description="Configuration name identifier")
    description: Optional[str] = Field(default=None, description="Configuration description")
    is_default: bool = Field(default=False, description="Whether this is the default configuration")
    
    # Temporal Parameters
    max_gap_seconds: int = Field(
        default=3,
        ge=1,
        le=60,
        description="Maximum allowed gap between consecutive videos (seconds)"
    )
    min_sequence_length: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Minimum number of videos in sequence for analysis"
    )
    
    # Spatial Parameters
    iou_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Rectangle overlap threshold (Intersection over Union)"
    )
    min_overlap_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for overlap acceptance"
    )
    
    # Individual Parameters
    min_appearances: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Minimum video appearances required for individual"
    )
    confidence_weight_iou: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for IoU score in confidence calculation"
    )
    confidence_weight_temporal: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for temporal continuity in confidence"
    )
    confidence_weight_spatial: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for spatial consistency in confidence"
    )
    
    # Collection Parameters
    max_collections: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum collections to process simultaneously"
    )
    batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Video processing batch size"
    )
    
    @root_validator(skip_on_failure=True)
    def validate_confidence_weights(cls, values):
        """Ensure confidence weights sum to approximately 1.0."""
        iou_weight = values.get('confidence_weight_iou', 0)
        temporal_weight = values.get('confidence_weight_temporal', 0)
        spatial_weight = values.get('confidence_weight_spatial', 0)
        
        total_weight = iou_weight + temporal_weight + spatial_weight
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point variance
            raise ValueError(f"Confidence weights must sum to 1.0, got {total_weight}")
        
        return values
    
    def calculate_hash(self) -> str:
        """Calculate hash of configuration for cache matching."""
        # Create deterministic dict for hashing
        config_dict = {
            'max_gap_seconds': self.max_gap_seconds,
            'min_sequence_length': self.min_sequence_length,
            'iou_threshold': self.iou_threshold,
            'min_overlap_confidence': self.min_overlap_confidence,
            'min_appearances': self.min_appearances,
            'confidence_weight_iou': self.confidence_weight_iou,
            'confidence_weight_temporal': self.confidence_weight_temporal,
            'confidence_weight_spatial': self.confidence_weight_spatial,
            'max_collections': self.max_collections,
            'batch_size': self.batch_size
        }
        
        # Create deterministic JSON string
        config_json = json.dumps(config_dict, sort_keys=True)
        
        # Return first 32 characters of SHA-256 hash
        return hashlib.sha256(config_json.encode()).hexdigest()[:32]
    
    def get_hash(self) -> str:
        """Get hash of configuration for compatibility."""
        return self.calculate_hash()
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "max_gap_seconds": 3,
                "min_sequence_length": 2,
                "iou_threshold": 0.3,
                "min_overlap_confidence": 0.5,
                "min_appearances": 1,
                "confidence_weight_iou": 0.4,
                "confidence_weight_temporal": 0.3,
                "confidence_weight_spatial": 0.3,
                "max_collections": 10,
                "batch_size": 100
            }
        }


# =============================================
# VIDEO AND SPATIAL DATA MODELS
# =============================================

class BoundingBox(BaseModel):
    """Bounding box coordinates in [x1, y1, x2, y2] format."""
    
    x1: float = Field(description="Left coordinate")
    y1: float = Field(description="Top coordinate") 
    x2: float = Field(description="Right coordinate")
    y2: float = Field(description="Bottom coordinate")
    
    @validator('x2')
    def x2_greater_than_x1(cls, v, values):
        """Ensure x2 > x1."""
        if 'x1' in values and v <= values['x1']:
            raise ValueError('x2 must be greater than x1')
        return v
    
    @validator('y2')
    def y2_greater_than_y1(cls, v, values):
        """Ensure y2 > y1."""
        if 'y1' in values and v <= values['y1']:
            raise ValueError('y2 must be greater than y1')
        return v
    
    def to_array(self) -> List[float]:
        """Convert to array format for database storage."""
        return [self.x1, self.y1, self.x2, self.y2]
    
    @classmethod
    def from_array(cls, bbox_array: List[float]) -> 'BoundingBox':
        """Create from array format."""
        if len(bbox_array) != 4:
            raise ValueError("Bounding box array must have exactly 4 elements")
        return cls(x1=bbox_array[0], y1=bbox_array[1], x2=bbox_array[2], y2=bbox_array[3])
    
    def calculate_area(self) -> float:
        """Calculate bounding box area."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)
    
    def calculate_iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union with another bounding box."""
        # Calculate intersection coordinates
        x1_inter = max(self.x1, other.x1)
        y1_inter = max(self.y1, other.y1)
        x2_inter = min(self.x2, other.x2)
        y2_inter = min(self.y2, other.y2)
        
        # Check if there's an intersection
        if x1_inter >= x2_inter or y1_inter >= y2_inter:
            return 0.0
        
        # Calculate intersection area
        intersection_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # Calculate union area
        self_area = self.calculate_area()
        other_area = other.calculate_area()
        union_area = self_area + other_area - intersection_area
        
        # Return IoU
        return intersection_area / union_area if union_area > 0 else 0.0


class VideoAppearance(BaseModel):
    """Individual appearance in a specific video."""
    
    video_uuid: UUID = Field(description="Video identifier")
    person_object_uuid: UUID = Field(description="Person object identifier")
    start_timestamp: datetime = Field(description="First appearance timestamp")
    end_timestamp: datetime = Field(description="Last appearance timestamp")
    entry_bbox: Optional[BoundingBox] = Field(description="First face rectangle in video")
    exit_bbox: Optional[BoundingBox] = Field(description="Last face rectangle in video")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for this appearance"
    )
    representative_faces: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Best quality faces from this video"
    )
    movement_pattern: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Spatial movement within video"
    )
    
    @validator('end_timestamp')
    def end_after_start(cls, v, values):
        """Ensure end timestamp is after start timestamp."""
        if 'start_timestamp' in values and v < values['start_timestamp']:
            raise ValueError('end_timestamp must be after start_timestamp')
        return v
    
    def duration_seconds(self) -> float:
        """Calculate appearance duration in seconds."""
        return (self.end_timestamp - self.start_timestamp).total_seconds()
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "video_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "person_object_uuid": "987fcdeb-51a2-43d1-9f12-123456789abc",
                "start_timestamp": "2025-10-20T09:15:30",
                "end_timestamp": "2025-10-20T09:18:45",
                "entry_bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150},
                "exit_bbox": {"x1": 180, "y1": 60, "x2": 280, "y2": 160},
                "confidence": 0.87
            }
        }


# =============================================
# INDIVIDUAL MODEL
# =============================================

class Individual(BaseModel):
    """
    Core individual identity object spanning multiple videos.
    
    Represents a unique person identified across multiple video appearances
    with associated confidence metrics and movement patterns.
    """
    
    individual_uuid: UUID = Field(default_factory=uuid4, description="Unique identifier")
    individual_id: str = Field(description="Human-readable ID (e.g., individual_001)")
    person_objects: List[UUID] = Field(description="Person object UUIDs for this individual")
    video_appearances: List[VideoAppearance] = Field(description="Temporal video sequence")
    spatial_signature: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Characteristic spatial patterns"
    )
    temporal_signature: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Movement and timing patterns"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall matching confidence"
    )
    creation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('video_appearances')
    def appearances_not_empty(cls, v):
        """Ensure individual has at least one appearance."""
        if not v:
            raise ValueError('Individual must have at least one video appearance')
        return v
    
    @validator('person_objects')
    def person_objects_match_appearances(cls, v, values):
        """Ensure person objects match video appearances."""
        if 'video_appearances' in values:
            appearance_objects = {app.person_object_uuid for app in values['video_appearances']}
            person_object_set = set(v)
            if appearance_objects != person_object_set:
                raise ValueError('Person objects must match video appearance objects')
        return v
    
    def total_appearances(self) -> int:
        """Get total number of video appearances."""
        return len(self.video_appearances)
    
    def total_duration_seconds(self) -> float:
        """Calculate total duration across all appearances."""
        return sum(app.duration_seconds() for app in self.video_appearances)
    
    def get_time_span(self) -> Optional[tuple[datetime, datetime]]:
        """Get overall time span from first to last appearance."""
        if not self.video_appearances:
            return None
        
        start_times = [app.start_timestamp for app in self.video_appearances]
        end_times = [app.end_timestamp for app in self.video_appearances]
        
        return (min(start_times), max(end_times))
    
    def get_videos(self) -> List[UUID]:
        """Get list of unique video UUIDs."""
        return list(set(app.video_uuid for app in self.video_appearances))
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "individual_uuid": "123e4567-e89b-12d3-a456-426614174000",
                "individual_id": "individual_001",
                "person_objects": ["987fcdeb-51a2-43d1-9f12-123456789abc"],
                "video_appearances": [
                    {
                        "video_uuid": "456e7890-e89b-12d3-a456-426614174111",
                        "person_object_uuid": "987fcdeb-51a2-43d1-9f12-123456789abc",
                        "start_timestamp": "2025-10-20T09:15:30",
                        "end_timestamp": "2025-10-20T09:18:45",
                        "confidence": 0.87
                    }
                ],
                "confidence_score": 0.92,
                "creation_timestamp": "2025-10-20T10:30:00",
                "last_updated": "2025-10-20T10:30:00"
            }
        }


# =============================================
# TRACKING SESSION MODEL
# =============================================

class TrackingSession(BaseModel):
    """
    User-initiated cross-video tracking execution session.
    
    Represents a complete algorithm execution with configuration,
    progress tracking, and result metrics.
    """
    
    session_uuid: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    user_id: str = Field(description="User who initiated the session")
    collections: List[str] = Field(description="Collection IDs to process")
    start_time: datetime = Field(description="Time range start")
    end_time: datetime = Field(description="Time range end")
    status: SessionStatus = Field(default=SessionStatus.INITIALIZED, description="Current status")
    config_hash: str = Field(description="Algorithm configuration hash")
    algorithm_config: CrossVideoTrackingConfig = Field(description="Algorithm parameters")
    
    # Processing state
    total_videos: int = Field(default=0, ge=0, description="Total videos in scope")
    processed_videos: int = Field(default=0, ge=0, description="Videos successfully processed")
    failed_videos: List[str] = Field(default_factory=list, description="Video UUIDs that failed")
    
    # Results
    individuals_found: int = Field(default=0, ge=0, description="Number of individuals identified")
    person_objects_processed: int = Field(default=0, ge=0, description="Total person objects analyzed")
    cache_hits: int = Field(default=0, ge=0, description="Number of videos using cached results")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None, description="Processing start time")
    completed_at: Optional[datetime] = Field(default=None, description="Processing completion time")
    processing_time_seconds: Optional[float] = Field(default=None, ge=0.0, description="Total processing time")
    
    @validator('end_time')
    def end_after_start(cls, v, values):
        """Ensure end_time is after start_time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @validator('processed_videos')
    def processed_within_total(cls, v, values):
        """Ensure processed videos doesn't exceed total."""
        if 'total_videos' in values and v > values['total_videos']:
            raise ValueError('processed_videos cannot exceed total_videos')
        return v
    
    @validator('cache_hits')
    def cache_hits_within_total(cls, v, values):
        """Ensure cache hits doesn't exceed total videos."""
        if 'total_videos' in values and v > values['total_videos']:
            raise ValueError('cache_hits cannot exceed total_videos')
        return v
    
    @validator('completed_at')
    def completed_after_started(cls, v, values):
        """Ensure completion is after start."""
        if v is not None and 'started_at' in values and values['started_at'] is not None:
            if v < values['started_at']:
                raise ValueError('completed_at must be after started_at')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_status_consistency(cls, values):
        """Validate status consistency with timing fields."""
        status = values.get('status')
        started_at = values.get('started_at')
        completed_at = values.get('completed_at')
        
        if status in [SessionStatus.RUNNING, SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.PARTIAL]:
            if started_at is None:
                raise ValueError(f'started_at required for status {status}')
        
        if status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.PARTIAL]:
            if completed_at is None:
                raise ValueError(f'completed_at required for status {status}')
        
        return values
    
    def calculate_progress_percentage(self) -> float:
        """Calculate processing progress as percentage."""
        if self.total_videos == 0:
            return 0.0
        return (self.processed_videos / self.total_videos) * 100.0
    
    def calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_videos == 0:
            return 0.0
        return (self.cache_hits / self.total_videos) * 100.0
    
    def calculate_processing_rate(self) -> Optional[float]:
        """Calculate videos per second processing rate."""
        if self.processing_time_seconds is None or self.processing_time_seconds == 0:
            return None
        return self.total_videos / self.processing_time_seconds
    
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status in [SessionStatus.INITIALIZED, SessionStatus.RUNNING]
    
    def is_completed(self) -> bool:
        """Check if session is completed (successfully or with errors)."""
        return self.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.PARTIAL]
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        schema_extra = {
            "example": {
                "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user123",
                "collections": ["warehouse_cameras", "entrance_cameras"],
                "start_time": "2025-10-20T09:00:00",
                "end_time": "2025-10-20T17:00:00",
                "status": "completed",
                "config_hash": "abc123def456",
                "algorithm_config": {
                    "max_gap_seconds": 3,
                    "iou_threshold": 0.3,
                    "min_overlap_confidence": 0.5
                },
                "total_videos": 45,
                "processed_videos": 45,
                "individuals_found": 12,
                "cache_hits": 18,
                "processing_time_seconds": 23.45
            }
        }


# =============================================
# PROCESSING STATE MODELS
# =============================================

class VideoProcessingState(BaseModel):
    """Tracks processing state for individual videos."""
    
    video_uuid: UUID = Field(description="Video identifier")
    session_uuid: UUID = Field(description="Session that processed this video")
    processing_status: ProcessingStatus = Field(description="Current processing status")
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    person_objects_count: int = Field(default=0, ge=0, description="Person objects found")
    processing_time_ms: float = Field(default=0.0, ge=0.0, description="Processing time in milliseconds")
    cache_source_session: Optional[UUID] = Field(default=None, description="Source session for cached results")
    error_message: Optional[str] = Field(default=None, description="Error details if failed")
    
    def is_completed(self) -> bool:
        """Check if processing is completed."""
        return self.processing_status in [ProcessingStatus.COMPLETED, ProcessingStatus.CACHED]
    
    def is_failed(self) -> bool:
        """Check if processing failed."""
        return self.processing_status == ProcessingStatus.FAILED
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class CachedResult(BaseModel):
    """Cached processing results for efficient reuse."""
    
    cache_key: str = Field(description="Hash of (video_uuid, config_hash)")
    video_uuid: UUID = Field(description="Video identifier")
    session_uuid: UUID = Field(description="Original session that created this cache")
    config_hash: str = Field(description="Hash of algorithm configuration")
    person_objects: List[Dict[str, Any]] = Field(description="Extracted person objects")
    processing_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")
    
    def update_access(self) -> None:
        """Update access timestamp and increment count."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class SessionIndividual(BaseModel):
    """Relationship between sessions and individuals."""
    
    session_uuid: UUID = Field(description="Session identifier")
    individual_uuid: UUID = Field(description="Individual identifier")
    processing_type: ProcessingType = Field(description="How individual was processed")
    confidence_contribution: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Contribution to overall individual confidence"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


# =============================================
# ALGORITHM CONFIGURATION MANAGEMENT
# =============================================

class AlgorithmConfiguration(BaseModel):
    """Stored algorithm configuration preset."""
    
    config_name: str = Field(description="Configuration name/identifier")
    description: Optional[str] = Field(default=None, description="Configuration description")
    config: CrossVideoTrackingConfig = Field(description="Algorithm configuration")
    is_default: bool = Field(default=False, description="Whether this is the default config")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "config_name": "default",
                "description": "Default cross-video tracking configuration",
                "config": {
                    "max_gap_seconds": 3,
                    "iou_threshold": 0.3,
                    "min_overlap_confidence": 0.5
                },
                "is_default": True
            }
        }


# =============================================
# UTILITY FUNCTIONS
# =============================================

def generate_cache_key(video_uuid: UUID, config_hash: str) -> str:
    """Generate cache key from video UUID and config hash."""
    combined = f"{video_uuid}{config_hash}"
    return hashlib.sha256(combined.encode()).hexdigest()


def validate_collections(collections: List[str]) -> bool:
    """Validate collection names format."""
    if not collections:
        return False
    
    for collection in collections:
        if not collection or not collection.strip():
            return False
        if len(collection) > 100:  # Reasonable limit
            return False
    
    return True


# =============================================
# MODEL REGISTRY
# =============================================

# Export all models for easy importing
__all__ = [
    # Enums
    'SessionStatus',
    'ProcessingStatus', 
    'ProcessingType',
    
    # Core Models
    'CrossVideoTrackingConfig',
    'BoundingBox',
    'VideoAppearance',
    'Individual',
    'TrackingSession',
    
    # Processing Models
    'VideoProcessingState',
    'CachedResult',
    'SessionIndividual',
    
    # Configuration Models
    'AlgorithmConfiguration',
    
    # Utility Functions
    'generate_cache_key',
    'validate_collections'
]