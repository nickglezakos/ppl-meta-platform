"""
Cross-Video Individual Tracking - Algorithm-Specific Models
PPL Meta Platform v2.19.13+

Supplementary models for the cross-video tracking algorithms that extend
the core models with algorithm-specific data structures.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from .cross_video_tracking import BoundingBox, Individual


# =============================================
# VIDEO AND SEQUENCE MODELS
# =============================================

class Video(BaseModel):
    """
    Video model for algorithm processing.
    
    Simplified video representation containing only the data needed
    for cross-video tracking algorithms.
    """
    
    video_uuid: UUID = Field(description="Unique video identifier")
    collection_id: str = Field(description="Collection this video belongs to")
    start_timestamp: datetime = Field(description="Video recording start time")
    end_timestamp: datetime = Field(description="Video recording end time")
    duration_seconds: float = Field(
        ge=0.0, description="Video duration in seconds"
    )
    person_objects: List['PersonObject'] = Field(
        description="Detected person objects in video"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional video metadata"
    )
    
    @validator('end_timestamp')
    def end_after_start(cls, v, values):
        """Ensure end timestamp is after start timestamp."""
        if 'start_timestamp' in values and v <= values['start_timestamp']:
            raise ValueError('end_timestamp must be after start_timestamp')
        return v
    
    def duration_seconds_calculated(self) -> float:
        """Calculate duration from timestamps."""
        return (self.end_timestamp - self.start_timestamp).total_seconds()
    
    def get_exit_rectangles(self) -> List[Dict[str, Any]]:
        """Get exit rectangles for cross-video tracking."""
        exit_rects = []
        for person in self.person_objects:
            if person.exit_bbox:
                exit_rects.append({
                    'person_object_uuid': person.person_object_uuid,
                    'bbox': person.exit_bbox,
                    'timestamp': person.last_seen_timestamp,
                    'confidence': person.confidence,
                    'video_uuid': self.video_uuid
                })
        return exit_rects
    
    def get_entry_rectangles(self) -> List[Dict[str, Any]]:
        """Get entry rectangles for cross-video tracking."""
        entry_rects = []
        for person in self.person_objects:
            if person.entry_bbox:
                entry_rects.append({
                    'person_object_uuid': person.person_object_uuid,
                    'bbox': person.entry_bbox,
                    'timestamp': person.first_seen_timestamp,
                    'confidence': person.confidence,
                    'video_uuid': self.video_uuid
                })
        return entry_rects


class PersonObject(BaseModel):
    """
    Person object model for algorithm processing.
    
    Represents a detected person in a single video with all necessary
    data for cross-video tracking algorithms.
    """
    
    person_object_uuid: UUID = Field(
        description="Unique person object identifier"
    )
    video_uuid: UUID = Field(description="Video this person appears in")
    first_seen_timestamp: datetime = Field(
        description="First detection timestamp"
    )
    last_seen_timestamp: datetime = Field(
        description="Last detection timestamp"
    )
    entry_bbox: Optional[BoundingBox] = Field(description="Entry bounding box")
    exit_bbox: Optional[BoundingBox] = Field(description="Exit bounding box")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Overall detection confidence"
    )
    face_embeddings: Optional[List[List[float]]] = Field(
        default=None, description="Face embeddings for similarity"
    )
    movement_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Movement pattern data"
    )
    quality_scores: Optional[Dict[str, float]] = Field(
        default=None, description="Quality metrics"
    )
    
    @validator('last_seen_timestamp')
    def last_after_first(cls, v, values):
        """Ensure last seen is after first seen."""
        if ('first_seen_timestamp' in values and 
            v < values['first_seen_timestamp']):
            raise ValueError(
                'last_seen_timestamp must be after first_seen_timestamp'
            )
        return v
    
    def duration_seconds(self) -> float:
        """Calculate duration in video."""
        return (
            self.last_seen_timestamp - self.first_seen_timestamp
        ).total_seconds()
    
    def get_center_point(
        self, bbox_type: str = 'entry'
    ) -> Optional[tuple[float, float]]:
        """Get center point of entry or exit bbox."""
        bbox = self.entry_bbox if bbox_type == 'entry' else self.exit_bbox
        if bbox:
            return ((bbox.x1 + bbox.x2) / 2, (bbox.y1 + bbox.y2) / 2)
        return None


class VideoSequence(BaseModel):
    """
    Sequence of temporally consecutive videos.
    
    Represents videos that are close enough in time to potentially
    track individuals across them.
    """
    
    sequence_id: str = Field(description="Unique sequence identifier")
    videos: List[Video] = Field(description="Videos in temporal order")
    start_time: datetime = Field(description="Sequence start time")
    end_time: datetime = Field(description="Sequence end time")
    total_duration_seconds: float = Field(ge=0.0, description="Total sequence duration")
    max_gap_seconds: float = Field(ge=0.0, description="Maximum gap between videos")
    
    @validator('videos')
    def videos_not_empty(cls, v):
        """Ensure sequence has videos."""
        if not v:
            raise ValueError('VideoSequence must contain at least one video')
        return v
    
    @validator('end_time')
    def end_after_start(cls, v, values):
        """Ensure end time is after start time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    def get_consecutive_video_pairs(self) -> List[tuple[Video, Video]]:
        """Get pairs of consecutive videos in sequence."""
        pairs = []
        for i in range(len(self.videos) - 1):
            pairs.append((self.videos[i], self.videos[i + 1]))
        return pairs
    
    def calculate_gaps(self) -> List[float]:
        """Calculate gaps between consecutive videos in seconds."""
        gaps = []
        for i in range(len(self.videos) - 1):
            current_end = self.videos[i].end_timestamp
            next_start = self.videos[i + 1].start_timestamp
            gap = (next_start - current_end).total_seconds()
            gaps.append(gap)
        return gaps
    
    def total_person_objects(self) -> int:
        """Get total person objects across all videos."""
        return sum(len(video.person_objects) for video in self.videos)


# =============================================
# OVERLAP AND TRACKING MODELS
# =============================================

class OverlapGroup(BaseModel):
    """
    Group of overlapping person objects between consecutive videos.
    
    Represents person objects that overlap spatially and temporally
    across video boundaries.
    """
    
    group_id: str = Field(description="Unique overlap group identifier")
    exit_video_uuid: UUID = Field(description="Video where person exits")
    entry_video_uuid: UUID = Field(description="Video where person enters")
    exit_person_objects: List[UUID] = Field(description="Person objects in exit video")
    entry_person_objects: List[UUID] = Field(description="Person objects in entry video")
    iou_scores: List[float] = Field(description="IoU scores for overlaps")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall overlap confidence")
    temporal_gap_seconds: float = Field(ge=0.0, description="Time gap between videos")
    
    def get_all_person_objects(self) -> List[UUID]:
        """Get all person objects in this overlap group."""
        return self.exit_person_objects + self.entry_person_objects
    
    def max_iou_score(self) -> float:
        """Get maximum IoU score in group."""
        return max(self.iou_scores) if self.iou_scores else 0.0
    
    def average_iou_score(self) -> float:
        """Get average IoU score in group."""
        return sum(self.iou_scores) / len(self.iou_scores) if self.iou_scores else 0.0


class ConfidenceMetrics(BaseModel):
    """
    Confidence calculation metrics for individual creation.
    
    Contains the various confidence components used in creating
    unified individual identities.
    """
    
    iou_confidence: float = Field(ge=0.0, le=1.0, description="IoU-based confidence")
    temporal_confidence: float = Field(ge=0.0, le=1.0, description="Temporal consistency confidence")
    spatial_confidence: float = Field(ge=0.0, le=1.0, description="Spatial consistency confidence")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Weighted overall confidence")
    
    def calculate_weighted_confidence(
        self,
        iou_weight: float,
        temporal_weight: float,
        spatial_weight: float
    ) -> float:
        """Calculate weighted confidence score."""
        return (
            self.iou_confidence * iou_weight +
            self.temporal_confidence * temporal_weight +
            self.spatial_confidence * spatial_weight
        )


# =============================================
# ALGORITHM RESULT MODELS
# =============================================

class CrossVideoTrackingResult(BaseModel):
    """
    Complete result from cross-video tracking algorithm.
    
    Contains all individuals identified across video sequences
    with detailed tracking information.
    """
    
    session_uuid: UUID = Field(description="Session that generated this result")
    video_sequences: List[VideoSequence] = Field(description="Processed video sequences")
    individuals: List[Individual] = Field(description="Identified individuals")
    overlap_groups: List[OverlapGroup] = Field(description="Detected overlap groups")
    processing_metrics: Dict[str, Any] = Field(description="Algorithm performance metrics")
    created_at: datetime = Field(description="Result creation timestamp")
    
    def total_videos_processed(self) -> int:
        """Get total number of videos processed."""
        return sum(len(seq.videos) for seq in self.video_sequences)
    
    def total_person_objects_processed(self) -> int:
        """Get total person objects processed."""
        return sum(seq.total_person_objects() for seq in self.video_sequences)
    
    def individuals_by_confidence(self, min_confidence: float = 0.0) -> List[Individual]:
        """Get individuals filtered by minimum confidence."""
        return [ind for ind in self.individuals if ind.confidence_score >= min_confidence]


# =============================================
# MODEL REGISTRY
# =============================================

# Update forward references
Video.model_rebuild()
PersonObject.model_rebuild()

# Export all models
__all__ = [
    # Video Models
    'Video',
    'PersonObject',
    'VideoSequence',
    
    # Overlap Models
    'OverlapGroup',
    'ConfidenceMetrics',
    
    # Result Models
    'CrossVideoTrackingResult'
]