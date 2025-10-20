"""
Cross-Video Individual Tracking - Core Algorithm Integration
PPL Meta Platform v2.19.13+

Integrates all Phase 2 components into cohesive cross-video tracking pipeline.
Main entry point for executing complete cross-video individual tracking.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging
import time

try:
    from ..models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        TrackingSession,
        Individual,
        VideoAppearance,
        BoundingBox
    )
    from .video_sequencing import VideoSequencer, VideoSequence
    from .cross_video_overlap import CrossVideoOverlapDetector, OverlapGroup
    from .individual_creator import IndividualCreator, IndividualCandidate
except ImportError:
    from models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        TrackingSession,
        Individual,
        VideoAppearance,
        BoundingBox
    )
    from algorithms.video_sequencing import VideoSequencer, VideoSequence
    from algorithms.cross_video_overlap import CrossVideoOverlapDetector, OverlapGroup
    from algorithms.individual_creator import IndividualCreator, IndividualCandidate

logger = logging.getLogger(__name__)


class CrossVideoTrackingEngine:
    """
    Main cross-video individual tracking algorithm engine.
    
    Orchestrates the complete pipeline from video sequences to
    identified individuals with comprehensive tracking results.
    """
    
    def __init__(self, config: CrossVideoTrackingConfig):
        """Initialize with algorithm configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.CrossVideoTrackingEngine")
        
        # Initialize algorithm components
        self.video_sequencer = VideoSequencer(config)
        self.overlap_detector = CrossVideoOverlapDetector(config)
        self.individual_creator = IndividualCreator(config)
    
    def execute_tracking(
        self,
        session: TrackingSession,
        video_data: List[Dict[str, Any]],
        person_objects_data: Dict[UUID, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Execute complete cross-video tracking algorithm.
        
        Args:
            session: Tracking session configuration
            video_data: List of video metadata
            person_objects_data: Dict mapping video_uuid to person objects
            
        Returns:
            Complete tracking results with individuals and metrics
        """
        start_time = time.time()
        
        self.logger.info(
            f"Starting cross-video tracking for session {session.session_uuid}"
        )
        self.logger.info(
            f"Processing {len(video_data)} videos, "
            f"{len(person_objects_data)} videos with person objects"
        )
        
        try:
            # Phase 1: Video Sequencing
            self.logger.info("Phase 1: Finding video sequences")
            video_sequences = self._find_video_sequences(session, video_data)
            
            if not video_sequences:
                self.logger.warning("No video sequences found")
                return self._create_empty_result(session, start_time)
            
            # Phase 2: Cross-Video Overlap Detection
            self.logger.info("Phase 2: Detecting cross-video overlaps")
            all_overlap_groups = self._detect_overlaps(
                video_sequences, person_objects_data
            )
            
            # Phase 3: Individual Creation
            self.logger.info("Phase 3: Creating individuals from overlaps")
            individuals = self._create_individuals(
                all_overlap_groups, person_objects_data
            )
            
            # Phase 4: Results Assembly
            self.logger.info("Phase 4: Assembling results")
            results = self._assemble_results(
                session, video_sequences, all_overlap_groups, 
                individuals, start_time
            )
            
            processing_time = time.time() - start_time
            self.logger.info(
                f"Cross-video tracking completed in {processing_time:.2f}s, "
                f"found {len(individuals)} individuals"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cross-video tracking failed: {e}")
            return self._create_error_result(session, str(e), start_time)
    
    def _find_video_sequences(
        self,
        session: TrackingSession,
        video_data: List[Dict[str, Any]]
    ) -> List[VideoSequence]:
        """Find temporally consecutive video sequences."""
        try:
            sequences = self.video_sequencer.find_consecutive_videos(
                start_time=session.start_time,
                end_time=session.end_time,
                collections=session.collections,
                video_data=video_data
            )
            
            # Log sequence statistics
            stats = self.video_sequencer.get_sequence_statistics(sequences)
            self.logger.info(
                f"Found {stats['total_sequences']} sequences with "
                f"{stats['total_videos']} total videos"
            )
            
            return sequences
            
        except Exception as e:
            self.logger.error(f"Video sequencing failed: {e}")
            return []
    
    def _detect_overlaps(
        self,
        video_sequences: List[VideoSequence],
        person_objects_data: Dict[UUID, List[Dict[str, Any]]]
    ) -> List[OverlapGroup]:
        """Detect cross-video overlaps across all sequences."""
        all_overlap_groups = []
        
        for i, sequence in enumerate(video_sequences):
            self.logger.debug(
                f"Processing sequence {i+1}/{len(video_sequences)}: "
                f"{sequence.sequence_id}"
            )
            
            try:
                sequence_overlaps = self.overlap_detector.find_overlapping_person_objects(
                    sequence, person_objects_data
                )
                
                all_overlap_groups.extend(sequence_overlaps)
                
            except Exception as e:
                self.logger.error(
                    f"Overlap detection failed for sequence {sequence.sequence_id}: {e}"
                )
                continue
        
        # Analyze overlap quality
        overlap_stats = self.overlap_detector.analyze_overlap_quality(all_overlap_groups)
        self.logger.info(
            f"Found {overlap_stats['total_groups']} overlap groups "
            f"with average IoU {overlap_stats.get('average_iou', 0):.3f}"
        )
        
        return all_overlap_groups
    
    def _create_individuals(
        self,
        overlap_groups: List[OverlapGroup],
        person_objects_data: Dict[UUID, List[Dict[str, Any]]]
    ) -> List[IndividualCandidate]:
        """Create individuals from overlap groups."""
        try:
            # Flatten person objects data for easier access
            flattened_data = {}
            for video_uuid, person_list in person_objects_data.items():
                for person_obj in person_list:
                    person_uuid = UUID(str(person_obj['person_object_uuid']))
                    flattened_data[person_uuid] = person_obj
            
            # Create individuals using Union-Find
            individuals = self.individual_creator.merge_overlapping_groups(
                overlap_groups, flattened_data
            )
            
            # Filter by minimum appearances
            filtered_individuals = [
                ind for ind in individuals 
                if len(ind.person_objects) >= self.config.min_appearances
            ]
            
            self.logger.info(
                f"Created {len(individuals)} individuals, "
                f"{len(filtered_individuals)} meet minimum appearance criteria"
            )
            
            return filtered_individuals
            
        except Exception as e:
            self.logger.error(f"Individual creation failed: {e}")
            return []
    
    def _assemble_results(
        self,
        session: TrackingSession,
        video_sequences: List[VideoSequence],
        overlap_groups: List[OverlapGroup],
        individuals: List[IndividualCandidate],
        start_time: float
    ) -> Dict[str, Any]:
        """Assemble complete tracking results."""
        processing_time = time.time() - start_time
        
        # Convert individuals to standard format
        converted_individuals = []
        for individual in individuals:
            converted_individual = self._convert_individual_candidate(individual)
            if converted_individual:
                converted_individuals.append(converted_individual)
        
        # Calculate comprehensive metrics
        metrics = self._calculate_metrics(
            video_sequences, overlap_groups, individuals, processing_time
        )
        
        # Assemble final results
        results = {
            'session_uuid': str(session.session_uuid),
            'success': True,
            'processing_time_seconds': processing_time,
            'video_sequences': [self._sequence_to_dict(seq) for seq in video_sequences],
            'overlap_groups': [self._overlap_group_to_dict(group) for group in overlap_groups],
            'individuals': converted_individuals,
            'metrics': metrics,
            'algorithm_config': session.algorithm_config.dict(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        return results
    
    def _convert_individual_candidate(
        self, candidate: IndividualCandidate
    ) -> Optional[Dict[str, Any]]:
        """Convert IndividualCandidate to standard Individual format."""
        try:
            # Convert video appearances
            video_appearances = []
            for appearance in candidate.video_appearances:
                video_appearance = VideoAppearance(
                    video_uuid=UUID(str(appearance['video_uuid'])),
                    person_object_uuid=UUID(str(appearance['person_object_uuid'])),
                    start_timestamp=appearance['start_timestamp'],
                    end_timestamp=appearance['end_timestamp'],
                    entry_bbox=self._convert_bbox(appearance.get('entry_bbox')),
                    exit_bbox=self._convert_bbox(appearance.get('exit_bbox')),
                    confidence=appearance.get('confidence', 0.0)
                )
                video_appearances.append(video_appearance)
            
            # Create Individual object
            individual = Individual(
                individual_id=candidate.individual_id,
                person_objects=candidate.person_objects,
                video_appearances=video_appearances,
                spatial_signature=candidate.spatial_signature,
                temporal_signature=candidate.temporal_signature,
                confidence_score=candidate.confidence_metrics.overall_confidence,
                creation_timestamp=candidate.creation_timestamp,
                last_updated=candidate.creation_timestamp
            )
            
            return individual.dict()
            
        except Exception as e:
            self.logger.error(f"Failed to convert individual candidate: {e}")
            return None
    
    def _convert_bbox(self, bbox_data: Any) -> Optional[BoundingBox]:
        """Convert various bbox formats to BoundingBox."""
        if not bbox_data:
            return None
        
        try:
            if isinstance(bbox_data, dict):
                return BoundingBox(
                    x1=bbox_data.get('x1', 0),
                    y1=bbox_data.get('y1', 0),
                    x2=bbox_data.get('x2', 0),
                    y2=bbox_data.get('y2', 0)
                )
            elif isinstance(bbox_data, list) and len(bbox_data) >= 4:
                return BoundingBox(
                    x1=bbox_data[0],
                    y1=bbox_data[1],
                    x2=bbox_data[2],
                    y2=bbox_data[3]
                )
            else:
                return None
        except Exception:
            return None
    
    def _calculate_metrics(
        self,
        video_sequences: List[VideoSequence],
        overlap_groups: List[OverlapGroup],
        individuals: List[IndividualCandidate],
        processing_time: float
    ) -> Dict[str, Any]:
        """Calculate comprehensive algorithm performance metrics."""
        # Video sequence metrics
        total_videos = sum(len(seq.videos) for seq in video_sequences)
        
        # Overlap metrics
        total_overlaps = len(overlap_groups)
        avg_iou = 0.0
        if overlap_groups:
            all_iou_scores = []
            for group in overlap_groups:
                all_iou_scores.extend(group.iou_scores)
            avg_iou = sum(all_iou_scores) / len(all_iou_scores) if all_iou_scores else 0.0
        
        # Individual metrics
        total_individuals = len(individuals)
        avg_confidence = 0.0
        if individuals:
            confidences = [ind.confidence_metrics.overall_confidence for ind in individuals]
            avg_confidence = sum(confidences) / len(confidences)
        
        # Processing metrics
        videos_per_second = total_videos / processing_time if processing_time > 0 else 0
        
        return {
            'video_sequences': {
                'total_sequences': len(video_sequences),
                'total_videos': total_videos,
                'average_sequence_length': total_videos / len(video_sequences) if video_sequences else 0
            },
            'overlaps': {
                'total_overlap_groups': total_overlaps,
                'average_iou_score': avg_iou,
                'overlaps_per_video': total_overlaps / total_videos if total_videos > 0 else 0
            },
            'individuals': {
                'total_individuals': total_individuals,
                'average_confidence': avg_confidence,
                'individuals_per_video': total_individuals / total_videos if total_videos > 0 else 0
            },
            'performance': {
                'processing_time_seconds': processing_time,
                'videos_per_second': videos_per_second,
                'algorithm_efficiency': self._calculate_efficiency_score(
                    total_videos, total_overlaps, total_individuals, processing_time
                )
            }
        }
    
    def _calculate_efficiency_score(
        self,
        total_videos: int,
        total_overlaps: int,
        total_individuals: int,
        processing_time: float
    ) -> float:
        """Calculate overall algorithm efficiency score."""
        if total_videos == 0 or processing_time == 0:
            return 0.0
        
        # Base efficiency from processing speed
        speed_score = min(total_videos / processing_time / 10, 1.0)  # 10 videos/sec = 1.0
        
        # Overlap detection effectiveness
        overlap_score = min(total_overlaps / total_videos, 1.0) if total_videos > 0 else 0
        
        # Individual identification effectiveness
        individual_score = min(total_individuals / (total_videos / 5), 1.0) if total_videos > 0 else 0
        
        # Weighted average
        return (speed_score * 0.4 + overlap_score * 0.3 + individual_score * 0.3)
    
    def _sequence_to_dict(self, sequence: VideoSequence) -> Dict[str, Any]:
        """Convert VideoSequence to dictionary."""
        return {
            'sequence_id': sequence.sequence_id,
            'video_count': len(sequence.videos),
            'start_time': sequence.start_time.isoformat(),
            'end_time': sequence.end_time.isoformat(),
            'total_duration_seconds': sequence.total_duration_seconds,
            'max_gap_seconds': sequence.max_gap_seconds,
            'video_uuids': [str(video.video_uuid) for video in sequence.videos]
        }
    
    def _overlap_group_to_dict(self, group: OverlapGroup) -> Dict[str, Any]:
        """Convert OverlapGroup to dictionary."""
        return {
            'group_id': group.group_id,
            'exit_video_uuid': str(group.exit_video_uuid),
            'entry_video_uuid': str(group.entry_video_uuid),
            'exit_person_objects': [str(uuid) for uuid in group.exit_person_objects],
            'entry_person_objects': [str(uuid) for uuid in group.entry_person_objects],
            'iou_scores': group.iou_scores,
            'confidence_score': group.confidence_score,
            'temporal_gap_seconds': group.temporal_gap_seconds
        }
    
    def _create_empty_result(
        self, session: TrackingSession, start_time: float
    ) -> Dict[str, Any]:
        """Create empty result for cases with no data."""
        processing_time = time.time() - start_time
        
        return {
            'session_uuid': str(session.session_uuid),
            'success': True,
            'processing_time_seconds': processing_time,
            'video_sequences': [],
            'overlap_groups': [],
            'individuals': [],
            'metrics': {
                'video_sequences': {'total_sequences': 0, 'total_videos': 0, 'average_sequence_length': 0},
                'overlaps': {'total_overlap_groups': 0, 'average_iou_score': 0.0, 'overlaps_per_video': 0},
                'individuals': {'total_individuals': 0, 'average_confidence': 0.0, 'individuals_per_video': 0},
                'performance': {
                    'processing_time_seconds': processing_time,
                    'videos_per_second': 0.0,
                    'algorithm_efficiency': 0.0
                }
            },
            'algorithm_config': session.algorithm_config.dict(),
            'created_at': datetime.utcnow().isoformat(),
            'message': 'No video sequences found for tracking'
        }
    
    def _create_error_result(
        self, session: TrackingSession, error_message: str, start_time: float
    ) -> Dict[str, Any]:
        """Create error result for failed executions."""
        processing_time = time.time() - start_time
        
        return {
            'session_uuid': str(session.session_uuid),
            'success': False,
            'processing_time_seconds': processing_time,
            'error_message': error_message,
            'algorithm_config': session.algorithm_config.dict(),
            'created_at': datetime.utcnow().isoformat()
        }