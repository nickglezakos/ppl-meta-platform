"""
Cross-Video Individual Tracking - Cross-Video Overlap Detection
PPL Meta Platform v2.19.13+

Implements cross-video overlap detection using IoU calculations between
exit/entry rectangles of person objects across consecutive videos.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID
import logging
from dataclasses import dataclass

try:
    from ..models.cross_video_tracking import CrossVideoTrackingConfig
    from .video_sequencing import VideoSequence, VideoInfo
except ImportError:
    from models.cross_video_tracking import CrossVideoTrackingConfig
    from algorithms.video_sequencing import VideoSequence, VideoInfo

logger = logging.getLogger(__name__)


@dataclass
class PersonObjectInfo:
    """Person object information for overlap detection."""
    person_object_uuid: UUID
    video_uuid: UUID
    bbox: List[float]  # [x1, y1, x2, y2]
    timestamp: datetime
    confidence: float
    
    def calculate_area(self) -> float:
        """Calculate bounding box area."""
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])
    
    def calculate_iou(self, other: 'PersonObjectInfo') -> float:
        """Calculate Intersection over Union with another bounding box."""
        # Calculate intersection coordinates
        x1_inter = max(self.bbox[0], other.bbox[0])
        y1_inter = max(self.bbox[1], other.bbox[1])
        x2_inter = min(self.bbox[2], other.bbox[2])
        y2_inter = min(self.bbox[3], other.bbox[3])
        
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


@dataclass
class OverlapGroup:
    """Group of overlapping person objects between consecutive videos."""
    group_id: str
    exit_video_uuid: UUID
    entry_video_uuid: UUID
    exit_person_objects: List[UUID]
    entry_person_objects: List[UUID]
    iou_scores: List[float]
    confidence_score: float
    temporal_gap_seconds: float
    
    def get_all_person_objects(self) -> List[UUID]:
        """Get all person objects in this overlap group."""
        return self.exit_person_objects + self.entry_person_objects
    
    def max_iou_score(self) -> float:
        """Get maximum IoU score in group."""
        return max(self.iou_scores) if self.iou_scores else 0.0
    
    def average_iou_score(self) -> float:
        """Get average IoU score in group."""
        return sum(self.iou_scores) / len(self.iou_scores) if self.iou_scores else 0.0


class CrossVideoOverlapDetector:
    """
    Cross-video overlap detection algorithm.
    
    Finds person objects that overlap between consecutive videos
    using IoU calculations and temporal analysis.
    """
    
    def __init__(self, config: CrossVideoTrackingConfig):
        """Initialize with algorithm configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.CrossVideoOverlapDetector")
    
    def find_overlapping_person_objects(
        self,
        video_sequence: VideoSequence,
        person_objects_data: Dict[UUID, List[Dict[str, Any]]]
    ) -> List[OverlapGroup]:
        """
        Find person objects that overlap between consecutive videos.
        
        Args:
            video_sequence: Sequence of consecutive videos
            person_objects_data: Dict mapping video_uuid to person objects
            
        Returns:
            List of overlap groups found
        """
        self.logger.info(
            f"Finding overlaps in sequence {video_sequence.sequence_id} "
            f"with {len(video_sequence.videos)} videos"
        )
        
        overlap_groups = []
        consecutive_pairs = video_sequence.get_consecutive_pairs()
        
        for i, (exit_video, entry_video) in enumerate(consecutive_pairs):
            self.logger.debug(
                f"Analyzing pair {i+1}/{len(consecutive_pairs)}: "
                f"{exit_video.video_uuid} -> {entry_video.video_uuid}"
            )
            
            # Get person objects for both videos
            exit_objects = person_objects_data.get(exit_video.video_uuid, [])
            entry_objects = person_objects_data.get(entry_video.video_uuid, [])
            
            if not exit_objects or not entry_objects:
                self.logger.debug(
                    f"Skipping pair - no person objects: "
                    f"exit={len(exit_objects)}, entry={len(entry_objects)}"
                )
                continue
            
            # Extract exit and entry rectangles
            exit_rectangles = self._extract_exit_rectangles(
                exit_objects, exit_video
            )
            entry_rectangles = self._extract_entry_rectangles(
                entry_objects, entry_video
            )
            
            # Detect overlaps between rectangles
            pair_overlaps = self._detect_cross_video_overlaps(
                exit_rectangles, entry_rectangles, exit_video, entry_video
            )
            
            overlap_groups.extend(pair_overlaps)
        
        self.logger.info(f"Found {len(overlap_groups)} overlap groups")
        return overlap_groups
    
    def _extract_exit_rectangles(
        self,
        person_objects: List[Dict[str, Any]],
        video: VideoInfo
    ) -> List[PersonObjectInfo]:
        """Extract exit rectangles from person objects."""
        exit_rectangles = []
        
        for person_obj in person_objects:
            try:
                # Get exit bounding box
                exit_bbox = person_obj.get('exit_bbox')
                if not exit_bbox:
                    continue
                
                # Convert to list format
                if isinstance(exit_bbox, dict):
                    bbox = [
                        exit_bbox.get('x1', 0),
                        exit_bbox.get('y1', 0),
                        exit_bbox.get('x2', 0),
                        exit_bbox.get('y2', 0)
                    ]
                elif isinstance(exit_bbox, list) and len(exit_bbox) >= 4:
                    bbox = exit_bbox[:4]
                else:
                    continue
                
                # Create PersonObjectInfo
                person_info = PersonObjectInfo(
                    person_object_uuid=UUID(str(person_obj['person_object_uuid'])),
                    video_uuid=video.video_uuid,
                    bbox=bbox,
                    timestamp=person_obj.get('last_seen_timestamp', video.end_timestamp),
                    confidence=person_obj.get('confidence', 0.0)
                )
                
                exit_rectangles.append(person_info)
                
            except Exception as e:
                self.logger.warning(f"Failed to extract exit rectangle: {e}")
                continue
        
        return exit_rectangles
    
    def _extract_entry_rectangles(
        self,
        person_objects: List[Dict[str, Any]],
        video: VideoInfo
    ) -> List[PersonObjectInfo]:
        """Extract entry rectangles from person objects."""
        entry_rectangles = []
        
        for person_obj in person_objects:
            try:
                # Get entry bounding box
                entry_bbox = person_obj.get('entry_bbox')
                if not entry_bbox:
                    continue
                
                # Convert to list format
                if isinstance(entry_bbox, dict):
                    bbox = [
                        entry_bbox.get('x1', 0),
                        entry_bbox.get('y1', 0),
                        entry_bbox.get('x2', 0),
                        entry_bbox.get('y2', 0)
                    ]
                elif isinstance(entry_bbox, list) and len(entry_bbox) >= 4:
                    bbox = entry_bbox[:4]
                else:
                    continue
                
                # Create PersonObjectInfo
                person_info = PersonObjectInfo(
                    person_object_uuid=UUID(str(person_obj['person_object_uuid'])),
                    video_uuid=video.video_uuid,
                    bbox=bbox,
                    timestamp=person_obj.get('first_seen_timestamp', video.start_timestamp),
                    confidence=person_obj.get('confidence', 0.0)
                )
                
                entry_rectangles.append(person_info)
                
            except Exception as e:
                self.logger.warning(f"Failed to extract entry rectangle: {e}")
                continue
        
        return entry_rectangles
    
    def _detect_cross_video_overlaps(
        self,
        exit_rectangles: List[PersonObjectInfo],
        entry_rectangles: List[PersonObjectInfo],
        exit_video: VideoInfo,
        entry_video: VideoInfo
    ) -> List[OverlapGroup]:
        """Apply IoU calculation between exit and entry rectangles."""
        overlaps = []
        
        # Calculate temporal gap
        temporal_gap = (
            entry_video.start_timestamp - exit_video.end_timestamp
        ).total_seconds()
        
        self.logger.debug(
            f"Analyzing {len(exit_rectangles)} exit vs "
            f"{len(entry_rectangles)} entry rectangles, "
            f"gap: {temporal_gap:.1f}s"
        )
        
        # Find all overlapping pairs
        overlapping_pairs = []
        
        for exit_rect in exit_rectangles:
            for entry_rect in entry_rectangles:
                # Calculate IoU
                iou_score = exit_rect.calculate_iou(entry_rect)
                
                # Check if IoU meets threshold
                if iou_score >= self.config.iou_threshold:
                    # Calculate combined confidence
                    combined_confidence = (
                        exit_rect.confidence + entry_rect.confidence
                    ) / 2
                    
                    # Check if confidence meets threshold
                    if combined_confidence >= self.config.min_overlap_confidence:
                        overlapping_pairs.append({
                            'exit_object': exit_rect,
                            'entry_object': entry_rect,
                            'iou_score': iou_score,
                            'combined_confidence': combined_confidence
                        })
        
        # Group overlapping pairs into overlap groups
        if overlapping_pairs:
            overlaps = self._create_overlap_groups(
                overlapping_pairs, exit_video, entry_video, temporal_gap
            )
        
        self.logger.debug(f"Found {len(overlaps)} overlap groups")
        return overlaps
    
    def _create_overlap_groups(
        self,
        overlapping_pairs: List[Dict[str, Any]],
        exit_video: VideoInfo,
        entry_video: VideoInfo,
        temporal_gap: float
    ) -> List[OverlapGroup]:
        """Create overlap groups from overlapping pairs."""
        # For now, create individual groups for each pair
        # This can be enhanced with Union-Find for complex merging
        groups = []
        
        for i, pair in enumerate(overlapping_pairs):
            group_id = f"overlap_{exit_video.video_uuid}_{entry_video.video_uuid}_{i}"
            
            group = OverlapGroup(
                group_id=group_id,
                exit_video_uuid=exit_video.video_uuid,
                entry_video_uuid=entry_video.video_uuid,
                exit_person_objects=[pair['exit_object'].person_object_uuid],
                entry_person_objects=[pair['entry_object'].person_object_uuid],
                iou_scores=[pair['iou_score']],
                confidence_score=pair['combined_confidence'],
                temporal_gap_seconds=temporal_gap
            )
            
            groups.append(group)
        
        return groups
    
    def analyze_overlap_quality(
        self, overlap_groups: List[OverlapGroup]
    ) -> Dict[str, Any]:
        """Analyze the quality and characteristics of overlap groups."""
        if not overlap_groups:
            return {
                'total_groups': 0,
                'average_iou': 0.0,
                'average_confidence': 0.0,
                'average_temporal_gap': 0.0
            }
        
        # Calculate statistics
        all_iou_scores = []
        all_confidences = []
        all_gaps = []
        
        for group in overlap_groups:
            all_iou_scores.extend(group.iou_scores)
            all_confidences.append(group.confidence_score)
            all_gaps.append(group.temporal_gap_seconds)
        
        return {
            'total_groups': len(overlap_groups),
            'total_overlaps': len(all_iou_scores),
            'average_iou': sum(all_iou_scores) / len(all_iou_scores),
            'max_iou': max(all_iou_scores),
            'min_iou': min(all_iou_scores),
            'average_confidence': sum(all_confidences) / len(all_confidences),
            'max_confidence': max(all_confidences),
            'min_confidence': min(all_confidences),
            'average_temporal_gap': sum(all_gaps) / len(all_gaps),
            'max_temporal_gap': max(all_gaps),
            'min_temporal_gap': min(all_gaps),
            'high_quality_overlaps': len([
                score for score in all_iou_scores if score > 0.7
            ])
        }
    
    def filter_overlaps_by_quality(
        self,
        overlap_groups: List[OverlapGroup],
        min_iou: float = None,
        min_confidence: float = None,
        max_temporal_gap: float = None
    ) -> List[OverlapGroup]:
        """Filter overlap groups by quality criteria."""
        filtered_groups = []
        
        for group in overlap_groups:
            # Check IoU threshold
            if min_iou is not None:
                if group.max_iou_score() < min_iou:
                    continue
            
            # Check confidence threshold
            if min_confidence is not None:
                if group.confidence_score < min_confidence:
                    continue
            
            # Check temporal gap threshold
            if max_temporal_gap is not None:
                if group.temporal_gap_seconds > max_temporal_gap:
                    continue
            
            filtered_groups.append(group)
        
        self.logger.info(
            f"Filtered {len(overlap_groups)} groups to {len(filtered_groups)} "
            f"high-quality groups"
        )
        
        return filtered_groups