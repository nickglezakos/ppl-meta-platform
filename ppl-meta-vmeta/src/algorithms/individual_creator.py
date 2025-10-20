"""
Cross-Video Individual Tracking - Union-Find Algorithm
PPL Meta Platform v2.19.13+

Implements Union-Find algorithm for merging overlapping person objects
into unified individuals with confidence scoring and identity management.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging
from dataclasses import dataclass

try:
    from ..models.cross_video_tracking import CrossVideoTrackingConfig
    from .cross_video_overlap import OverlapGroup
except ImportError:
    from models.cross_video_tracking import CrossVideoTrackingConfig
    from algorithms.cross_video_overlap import OverlapGroup

logger = logging.getLogger(__name__)


class UnionFind:
    """
    Union-Find (Disjoint Set Union) data structure.
    
    Efficiently groups overlapping person objects into connected components
    representing unique individuals across videos.
    """
    
    def __init__(self):
        """Initialize empty Union-Find structure."""
        self.parent: Dict[UUID, UUID] = {}
        self.rank: Dict[UUID, int] = {}
        self.component_size: Dict[UUID, int] = {}
    
    def find(self, x: UUID) -> UUID:
        """Find root with path compression."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
            self.component_size[x] = 1
            return x
        
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        
        return self.parent[x]
    
    def union(self, x: UUID, y: UUID) -> bool:
        """Union by rank. Returns True if union was performed."""
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return False  # Already in same component
        
        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            root_x, root_y = root_y, root_x
        
        self.parent[root_y] = root_x
        self.component_size[root_x] += self.component_size[root_y]
        
        if self.rank[root_x] == self.rank[root_y]:
            self.rank[root_x] += 1
        
        return True
    
    def get_connected_components(self) -> Dict[UUID, List[UUID]]:
        """Get all connected components."""
        components: Dict[UUID, List[UUID]] = {}
        
        for node in self.parent:
            root = self.find(node)
            if root not in components:
                components[root] = []
            components[root].append(node)
        
        return components
    
    def get_component_size(self, x: UUID) -> int:
        """Get size of component containing x."""
        root = self.find(x)
        return self.component_size[root]
    
    def are_connected(self, x: UUID, y: UUID) -> bool:
        """Check if two nodes are in the same component."""
        return self.find(x) == self.find(y)


@dataclass
class ConfidenceMetrics:
    """Confidence calculation metrics for individual creation."""
    iou_confidence: float
    temporal_confidence: float
    spatial_confidence: float
    overall_confidence: float
    
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


@dataclass
class IndividualCandidate:
    """Candidate individual with associated person objects."""
    individual_id: str
    person_objects: List[UUID]
    video_appearances: List[Dict[str, Any]]
    confidence_metrics: ConfidenceMetrics
    spatial_signature: Dict[str, Any]
    temporal_signature: Dict[str, Any]
    creation_timestamp: datetime


class IndividualCreator:
    """
    Individual creator using Union-Find algorithm.
    
    Merges overlapping person objects into unified individuals
    with comprehensive confidence scoring.
    """
    
    def __init__(self, config: CrossVideoTrackingConfig):
        """Initialize with algorithm configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.IndividualCreator")
    
    def merge_overlapping_groups(
        self,
        overlap_groups: List[OverlapGroup],
        person_objects_data: Dict[UUID, Dict[str, Any]]
    ) -> List[IndividualCandidate]:
        """
        Merge overlapping person objects into individuals.
        
        Args:
            overlap_groups: Detected overlap groups
            person_objects_data: Complete person object data
            
        Returns:
            List of individual candidates
        """
        self.logger.info(
            f"Merging {len(overlap_groups)} overlap groups into individuals"
        )
        
        # Initialize Union-Find structure
        union_find = UnionFind()
        
        # Process overlap groups to build connections
        self._build_connections(overlap_groups, union_find)
        
        # Get connected components (individual candidates)
        components = union_find.get_connected_components()
        
        # Create individual candidates from components
        individuals = self._create_individuals_from_components(
            components, overlap_groups, person_objects_data
        )
        
        self.logger.info(f"Created {len(individuals)} individual candidates")
        return individuals
    
    def _build_connections(
        self,
        overlap_groups: List[OverlapGroup],
        union_find: UnionFind
    ) -> None:
        """Build connections between person objects using Union-Find."""
        for group in overlap_groups:
            # Get all person objects in the overlap group
            all_objects = group.get_all_person_objects()
            
            # Connect all objects in the group
            for i in range(len(all_objects)):
                for j in range(i + 1, len(all_objects)):
                    union_find.union(all_objects[i], all_objects[j])
                    
                    self.logger.debug(
                        f"Connected {all_objects[i]} and {all_objects[j]} "
                        f"in group {group.group_id}"
                    )
    
    def _create_individuals_from_components(
        self,
        components: Dict[UUID, List[UUID]],
        overlap_groups: List[OverlapGroup],
        person_objects_data: Dict[UUID, Dict[str, Any]]
    ) -> List[IndividualCandidate]:
        """Create individual candidates from connected components."""
        individuals = []
        
        for i, (root, person_objects) in enumerate(components.items()):
            # Filter by minimum appearances
            if len(person_objects) < self.config.min_appearances:
                self.logger.debug(
                    f"Skipping component with {len(person_objects)} objects "
                    f"(min required: {self.config.min_appearances})"
                )
                continue
            
            # Create individual from component
            individual = self._create_individual_from_person_objects(
                person_objects, overlap_groups, person_objects_data, i + 1
            )
            
            if individual:
                individuals.append(individual)
        
        return individuals
    
    def _create_individual_from_person_objects(
        self,
        person_objects: List[UUID],
        overlap_groups: List[OverlapGroup],
        person_objects_data: Dict[UUID, Dict[str, Any]],
        individual_number: int
    ) -> Optional[IndividualCandidate]:
        """Create unified individual identity from person objects."""
        try:
            # Generate individual ID
            individual_id = f"individual_{individual_number:03d}"
            
            # Create video appearances
            video_appearances = []
            for person_uuid in person_objects:
                person_data = person_objects_data.get(person_uuid)
                if person_data:
                    appearance = {
                        'video_uuid': person_data.get('video_uuid'),
                        'person_object_uuid': person_uuid,
                        'start_timestamp': person_data.get('first_seen_timestamp'),
                        'end_timestamp': person_data.get('last_seen_timestamp'),
                        'entry_bbox': person_data.get('entry_bbox'),
                        'exit_bbox': person_data.get('exit_bbox'),
                        'confidence': person_data.get('confidence', 0.0)
                    }
                    video_appearances.append(appearance)
            
            # Calculate confidence metrics
            confidence_metrics = self._calculate_individual_confidence(
                person_objects, overlap_groups, person_objects_data
            )
            
            # Create spatial and temporal signatures
            spatial_signature = self._create_spatial_signature(
                video_appearances
            )
            temporal_signature = self._create_temporal_signature(
                video_appearances
            )
            
            return IndividualCandidate(
                individual_id=individual_id,
                person_objects=person_objects,
                video_appearances=video_appearances,
                confidence_metrics=confidence_metrics,
                spatial_signature=spatial_signature,
                temporal_signature=temporal_signature,
                creation_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to create individual from {len(person_objects)} "
                f"person objects: {e}"
            )
            return None
    
    def _calculate_individual_confidence(
        self,
        person_objects: List[UUID],
        overlap_groups: List[OverlapGroup],
        person_objects_data: Dict[UUID, Dict[str, Any]]
    ) -> ConfidenceMetrics:
        """Calculate overall confidence for individual."""
        # Find overlap groups involving these person objects
        relevant_groups = []
        person_object_set = set(person_objects)
        
        for group in overlap_groups:
            group_objects = set(group.get_all_person_objects())
            if group_objects.intersection(person_object_set):
                relevant_groups.append(group)
        
        # Calculate IoU confidence
        iou_confidence = self._calculate_iou_confidence(relevant_groups)
        
        # Calculate temporal confidence
        temporal_confidence = self._calculate_temporal_confidence(
            person_objects, person_objects_data
        )
        
        # Calculate spatial confidence
        spatial_confidence = self._calculate_spatial_confidence(
            person_objects, person_objects_data
        )
        
        # Calculate weighted overall confidence
        overall_confidence = (
            iou_confidence * self.config.confidence_weight_iou +
            temporal_confidence * self.config.confidence_weight_temporal +
            spatial_confidence * self.config.confidence_weight_spatial
        )
        
        return ConfidenceMetrics(
            iou_confidence=iou_confidence,
            temporal_confidence=temporal_confidence,
            spatial_confidence=spatial_confidence,
            overall_confidence=overall_confidence
        )
    
    def _calculate_iou_confidence(
        self, overlap_groups: List[OverlapGroup]
    ) -> float:
        """Calculate IoU-based confidence."""
        if not overlap_groups:
            return 0.0
        
        # Average IoU scores across all relevant groups
        all_iou_scores = []
        for group in overlap_groups:
            all_iou_scores.extend(group.iou_scores)
        
        if not all_iou_scores:
            return 0.0
        
        return sum(all_iou_scores) / len(all_iou_scores)
    
    def _calculate_temporal_confidence(
        self,
        person_objects: List[UUID],
        person_objects_data: Dict[UUID, Dict[str, Any]]
    ) -> float:
        """Calculate temporal consistency confidence."""
        timestamps = []
        
        for person_uuid in person_objects:
            person_data = person_objects_data.get(person_uuid)
            if person_data:
                start_time = person_data.get('first_seen_timestamp')
                end_time = person_data.get('last_seen_timestamp')
                if start_time and end_time:
                    timestamps.extend([start_time, end_time])
        
        if len(timestamps) < 2:
            return 0.0
        
        timestamps.sort()
        
        # Calculate temporal consistency (lower gaps = higher confidence)
        total_span = (timestamps[-1] - timestamps[0]).total_seconds()
        if total_span == 0:
            return 1.0
        
        # Penalize large gaps relative to total span
        max_gap = 0
        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i-1]).total_seconds()
            max_gap = max(max_gap, gap)
        
        gap_ratio = max_gap / total_span
        return max(0.0, 1.0 - gap_ratio)
    
    def _calculate_spatial_confidence(
        self,
        person_objects: List[UUID],
        person_objects_data: Dict[UUID, Dict[str, Any]]
    ) -> float:
        """Calculate spatial consistency confidence."""
        # Extract all bounding box centers
        centers = []
        
        for person_uuid in person_objects:
            person_data = person_objects_data.get(person_uuid)
            if person_data:
                for bbox_type in ['entry_bbox', 'exit_bbox']:
                    bbox = person_data.get(bbox_type)
                    if bbox:
                        if isinstance(bbox, dict):
                            center_x = (bbox.get('x1', 0) + bbox.get('x2', 0)) / 2
                            center_y = (bbox.get('y1', 0) + bbox.get('y2', 0)) / 2
                        elif isinstance(bbox, list) and len(bbox) >= 4:
                            center_x = (bbox[0] + bbox[2]) / 2
                            center_y = (bbox[1] + bbox[3]) / 2
                        else:
                            continue
                        
                        centers.append((center_x, center_y))
        
        if len(centers) < 2:
            return 0.0
        
        # Calculate spatial consistency (lower variance = higher confidence)
        center_x_values = [c[0] for c in centers]
        center_y_values = [c[1] for c in centers]
        
        # Calculate coefficient of variation
        def coefficient_of_variation(values):
            if not values:
                return 1.0
            mean_val = sum(values) / len(values)
            if mean_val == 0:
                return 0.0
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            return std_dev / mean_val
        
        cv_x = coefficient_of_variation(center_x_values)
        cv_y = coefficient_of_variation(center_y_values)
        
        # Convert to confidence score (lower CV = higher confidence)
        spatial_consistency = 1.0 / (1.0 + (cv_x + cv_y) / 2)
        
        return spatial_consistency
    
    def _create_spatial_signature(
        self, video_appearances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create characteristic spatial patterns."""
        if not video_appearances:
            return {}
        
        # Extract spatial features
        bbox_areas = []
        center_positions = []
        
        for appearance in video_appearances:
            for bbox_type in ['entry_bbox', 'exit_bbox']:
                bbox = appearance.get(bbox_type)
                if bbox:
                    if isinstance(bbox, dict):
                        area = (bbox.get('x2', 0) - bbox.get('x1', 0)) * \
                               (bbox.get('y2', 0) - bbox.get('y1', 0))
                        center_x = (bbox.get('x1', 0) + bbox.get('x2', 0)) / 2
                        center_y = (bbox.get('y1', 0) + bbox.get('y2', 0)) / 2
                    elif isinstance(bbox, list) and len(bbox) >= 4:
                        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                        center_x = (bbox[0] + bbox[2]) / 2
                        center_y = (bbox[1] + bbox[3]) / 2
                    else:
                        continue
                    
                    bbox_areas.append(area)
                    center_positions.append((center_x, center_y))
        
        signature = {
            'total_appearances': len(video_appearances),
            'average_bbox_area': sum(bbox_areas) / len(bbox_areas) if bbox_areas else 0,
            'position_variance': self._calculate_position_variance(center_positions)
        }
        
        return signature
    
    def _create_temporal_signature(
        self, video_appearances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create movement and timing patterns."""
        if not video_appearances:
            return {}
        
        # Extract temporal features
        durations = []
        timestamps = []
        
        for appearance in video_appearances:
            start_time = appearance.get('start_timestamp')
            end_time = appearance.get('end_timestamp')
            
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                durations.append(duration)
                timestamps.extend([start_time, end_time])
        
        if timestamps:
            timestamps.sort()
            total_span = (timestamps[-1] - timestamps[0]).total_seconds()
        else:
            total_span = 0
        
        signature = {
            'total_duration_seconds': sum(durations),
            'average_appearance_duration': sum(durations) / len(durations) if durations else 0,
            'time_span_seconds': total_span,
            'appearance_frequency': len(video_appearances) / (total_span / 3600) if total_span > 0 else 0
        }
        
        return signature
    
    def _calculate_position_variance(
        self, positions: List[tuple[float, float]]
    ) -> Dict[str, float]:
        """Calculate position variance statistics."""
        if not positions:
            return {'x_variance': 0.0, 'y_variance': 0.0}
        
        x_values = [pos[0] for pos in positions]
        y_values = [pos[1] for pos in positions]
        
        def variance(values):
            if not values:
                return 0.0
            mean_val = sum(values) / len(values)
            return sum((x - mean_val) ** 2 for x in values) / len(values)
        
        return {
            'x_variance': variance(x_values),
            'y_variance': variance(y_values)
        }