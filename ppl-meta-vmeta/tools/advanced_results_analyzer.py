"""
Cross-Video Individual Tracking - Advanced Results Analysis Module
PPL Meta Platform v2.19.13+

Advanced analysis capabilities for individual profiles, movement patterns,
statistical validation, and comprehensive result visualization.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import statistics

@dataclass
class IndividualProfile:
    """Comprehensive individual profile with movement and temporal analysis."""
    individual_id: str
    individual_uuid: str
    confidence_score: float
    total_appearances: int
    total_videos: int
    first_seen: datetime
    last_seen: datetime
    collections_visited: List[str]
    video_appearances: List[Dict[str, Any]]
    spatial_signature: Dict[str, Any]
    temporal_signature: Dict[str, Any]
    movement_patterns: Dict[str, Any]
    quality_metrics: Dict[str, float]

@dataclass
class MovementPattern:
    """Movement pattern analysis for an individual."""
    individual_id: str
    total_distance: float
    average_speed: float
    movement_entropy: float
    spatial_coverage: float
    temporal_consistency: float
    hotspots: List[Dict[str, Any]]
    trajectory_segments: List[Dict[str, Any]]

@dataclass
class StatisticalValidation:
    """Statistical validation results for tracking accuracy."""
    total_individuals: int
    confidence_distribution: Dict[str, int]
    temporal_distribution: Dict[str, int]
    spatial_distribution: Dict[str, int]
    quality_scores: Dict[str, float]
    validation_metrics: Dict[str, float]
    anomaly_detection: Dict[str, List[str]]


class AdvancedResultsAnalyzer:
    """
    Advanced analysis engine for cross-video tracking results.
    
    Provides comprehensive individual profiling, movement pattern analysis,
    statistical validation, and visualization capabilities.
    """
    
    def __init__(self):
        """Initialize the advanced analyzer."""
        self.individuals: List[IndividualProfile] = []
        self.movement_patterns: List[MovementPattern] = []
        self.validation_results: Optional[StatisticalValidation] = None
    
    def analyze_tracking_results(
        self, 
        tracking_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of tracking results.
        
        Args:
            tracking_results: Raw tracking results from session
            
        Returns:
            Comprehensive analysis results
        """
        try:
            # Extract individuals data
            individuals_data = tracking_results.get('individuals', [])
            video_sequences = tracking_results.get('video_sequences', [])
            
            if not individuals_data:
                return {
                    'status': 'no_data',
                    'message': 'No individuals found in results'
                }
            
            # Analyze individual profiles
            self.individuals = self._analyze_individual_profiles(individuals_data)
            
            # Analyze movement patterns
            self.movement_patterns = self._analyze_movement_patterns(
                self.individuals, video_sequences
            )
            
            # Perform statistical validation
            self.validation_results = self._perform_statistical_validation(
                self.individuals
            )
            
            # Generate comprehensive analysis
            analysis_results = {
                'analysis_timestamp': datetime.now().isoformat(),
                'summary': self._generate_summary(),
                'individual_profiles': [self._profile_to_dict(p) for p in self.individuals],
                'movement_patterns': [self._movement_to_dict(m) for m in self.movement_patterns],
                'statistical_validation': self._validation_to_dict(self.validation_results),
                'insights': self._generate_insights(),
                'recommendations': self._generate_recommendations()
            }
            
            return analysis_results
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Analysis failed: {str(e)}'
            }
    
    def _analyze_individual_profiles(
        self, 
        individuals_data: List[Dict[str, Any]]
    ) -> List[IndividualProfile]:
        """Analyze individual profiles with comprehensive metrics."""
        profiles = []
        
        for individual_data in individuals_data:
            try:
                # Extract basic information
                individual_id = individual_data.get('individual_id', 'Unknown')
                individual_uuid = individual_data.get('individual_uuid', '')
                confidence_score = individual_data.get('confidence_score', 0.0)
                
                # Extract appearance data
                appearances = individual_data.get('video_appearances', [])
                if not appearances:
                    continue
                
                # Calculate temporal metrics
                timestamps = []
                for appearance in appearances:
                    start_time = appearance.get('start_timestamp')
                    end_time = appearance.get('end_timestamp')
                    if start_time:
                        if isinstance(start_time, str):
                            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        timestamps.append(start_time)
                    if end_time:
                        if isinstance(end_time, str):
                            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        timestamps.append(end_time)
                
                if not timestamps:
                    continue
                
                first_seen = min(timestamps)
                last_seen = max(timestamps)
                
                # Extract spatial information
                collections = set()
                videos = set()
                for appearance in appearances:
                    if 'collection' in appearance:
                        collections.add(appearance['collection'])
                    if 'video_uuid' in appearance:
                        videos.add(appearance['video_uuid'])
                
                # Calculate movement patterns
                movement_patterns = self._calculate_movement_patterns(appearances)
                
                # Calculate quality metrics
                quality_metrics = self._calculate_quality_metrics(appearances)
                
                # Create profile
                profile = IndividualProfile(
                    individual_id=individual_id,
                    individual_uuid=individual_uuid,
                    confidence_score=confidence_score,
                    total_appearances=len(appearances),
                    total_videos=len(videos),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    collections_visited=list(collections),
                    video_appearances=appearances,
                    spatial_signature=individual_data.get('spatial_signature', {}),
                    temporal_signature=individual_data.get('temporal_signature', {}),
                    movement_patterns=movement_patterns,
                    quality_metrics=quality_metrics
                )
                
                profiles.append(profile)
                
            except Exception as e:
                print(f"Error analyzing individual {individual_data.get('individual_id', 'Unknown')}: {e}")
                continue
        
        return profiles
    
    def _calculate_movement_patterns(
        self, 
        appearances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate movement patterns from appearance data."""
        if len(appearances) < 2:
            return {
                'total_distance': 0.0,
                'average_speed': 0.0,
                'movement_entropy': 0.0,
                'spatial_coverage': 0.0
            }
        
        # Sort appearances by time
        sorted_appearances = sorted(
            appearances,
            key=lambda x: x.get('start_timestamp', '1970-01-01T00:00:00Z')
        )
        
        # Calculate distances between consecutive appearances
        distances = []
        time_intervals = []
        
        for i in range(len(sorted_appearances) - 1):
            curr = sorted_appearances[i]
            next_app = sorted_appearances[i + 1]
            
            # Calculate spatial distance (simplified using bounding box centers)
            curr_bbox = curr.get('entry_bbox') or curr.get('average_bbox')
            next_bbox = next_app.get('entry_bbox') or next_app.get('average_bbox')
            
            if curr_bbox and next_bbox and len(curr_bbox) >= 4 and len(next_bbox) >= 4:
                # Calculate center points
                curr_center = (curr_bbox[0] + curr_bbox[2]/2, curr_bbox[1] + curr_bbox[3]/2)
                next_center = (next_bbox[0] + next_bbox[2]/2, next_bbox[1] + next_bbox[3]/2)
                
                # Euclidean distance
                distance = math.sqrt(
                    (next_center[0] - curr_center[0])**2 + 
                    (next_center[1] - curr_center[1])**2
                )
                distances.append(distance)
                
                # Time interval
                curr_time = curr.get('end_timestamp') or curr.get('start_timestamp')
                next_time = next_app.get('start_timestamp')
                
                if curr_time and next_time:
                    if isinstance(curr_time, str):
                        curr_time = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))
                    if isinstance(next_time, str):
                        next_time = datetime.fromisoformat(next_time.replace('Z', '+00:00'))
                    
                    time_diff = (next_time - curr_time).total_seconds()
                    if time_diff > 0:
                        time_intervals.append(time_diff)
        
        # Calculate metrics
        total_distance = sum(distances) if distances else 0.0
        average_speed = (
            sum(d/t for d, t in zip(distances, time_intervals) if t > 0) / len(distances)
            if distances and time_intervals else 0.0
        )
        
        # Movement entropy (measure of movement randomness)
        movement_entropy = self._calculate_movement_entropy(distances)
        
        # Spatial coverage (normalized area covered)
        spatial_coverage = self._calculate_spatial_coverage(appearances)
        
        return {
            'total_distance': total_distance,
            'average_speed': average_speed,
            'movement_entropy': movement_entropy,
            'spatial_coverage': spatial_coverage,
            'appearance_count': len(appearances),
            'distance_distribution': {
                'min': min(distances) if distances else 0.0,
                'max': max(distances) if distances else 0.0,
                'mean': statistics.mean(distances) if distances else 0.0,
                'std': statistics.stdev(distances) if len(distances) > 1 else 0.0
            }
        }
    
    def _calculate_movement_entropy(self, distances: List[float]) -> float:
        """Calculate movement entropy as a measure of movement randomness."""
        if not distances or len(distances) < 2:
            return 0.0
        
        # Discretize distances into bins
        max_dist = max(distances)
        if max_dist == 0:
            return 0.0
        
        bins = 10
        bin_size = max_dist / bins
        
        # Count occurrences in each bin
        bin_counts = [0] * bins
        for dist in distances:
            bin_idx = min(int(dist / bin_size), bins - 1)
            bin_counts[bin_idx] += 1
        
        # Calculate entropy
        total = len(distances)
        entropy = 0.0
        for count in bin_counts:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        return entropy
    
    def _calculate_spatial_coverage(self, appearances: List[Dict[str, Any]]) -> float:
        """Calculate normalized spatial coverage area."""
        if not appearances:
            return 0.0
        
        # Extract all bounding boxes
        bboxes = []
        for appearance in appearances:
            for bbox_key in ['entry_bbox', 'exit_bbox', 'average_bbox']:
                bbox = appearance.get(bbox_key)
                if bbox and len(bbox) >= 4:
                    bboxes.append(bbox)
        
        if not bboxes:
            return 0.0
        
        # Calculate bounding rectangle of all appearances
        min_x = min(bbox[0] for bbox in bboxes)
        min_y = min(bbox[1] for bbox in bboxes)
        max_x = max(bbox[0] + bbox[2] for bbox in bboxes)
        max_y = max(bbox[1] + bbox[3] for bbox in bboxes)
        
        # Calculate coverage area (normalized to 0-1)
        coverage_area = (max_x - min_x) * (max_y - min_y)
        
        # Normalize by assumed frame size (assuming 1920x1080)
        normalized_coverage = coverage_area / (1920 * 1080)
        
        return min(normalized_coverage, 1.0)
    
    def _calculate_quality_metrics(
        self, 
        appearances: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate quality metrics for individual appearances."""
        confidence_scores = []
        quality_scores = []
        face_quality_scores = []
        
        for appearance in appearances:
            if 'confidence' in appearance:
                confidence_scores.append(appearance['confidence'])
            if 'quality_score' in appearance:
                quality_scores.append(appearance['quality_score'])
            if 'face_quality' in appearance:
                face_quality_scores.append(appearance['face_quality'])
        
        return {
            'average_confidence': statistics.mean(confidence_scores) if confidence_scores else 0.0,
            'min_confidence': min(confidence_scores) if confidence_scores else 0.0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0.0,
            'confidence_std': statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0,
            'average_quality': statistics.mean(quality_scores) if quality_scores else 0.0,
            'average_face_quality': statistics.mean(face_quality_scores) if face_quality_scores else 0.0,
            'quality_consistency': (
                1.0 - (statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0)
            )
        }
    
    def _analyze_movement_patterns(
        self,
        profiles: List[IndividualProfile],
        video_sequences: List[Dict[str, Any]]
    ) -> List[MovementPattern]:
        """Analyze detailed movement patterns for all individuals."""
        patterns = []
        
        for profile in profiles:
            try:
                # Calculate comprehensive movement metrics
                movement_data = profile.movement_patterns
                
                # Identify hotspots (areas of frequent appearance)
                hotspots = self._identify_hotspots(profile.video_appearances)
                
                # Analyze trajectory segments
                trajectory_segments = self._analyze_trajectory_segments(
                    profile.video_appearances
                )
                
                # Calculate movement entropy and consistency
                movement_entropy = movement_data.get('movement_entropy', 0.0)
                temporal_consistency = self._calculate_temporal_consistency(
                    profile.video_appearances
                )
                
                pattern = MovementPattern(
                    individual_id=profile.individual_id,
                    total_distance=movement_data.get('total_distance', 0.0),
                    average_speed=movement_data.get('average_speed', 0.0),
                    movement_entropy=movement_entropy,
                    spatial_coverage=movement_data.get('spatial_coverage', 0.0),
                    temporal_consistency=temporal_consistency,
                    hotspots=hotspots,
                    trajectory_segments=trajectory_segments
                )
                
                patterns.append(pattern)
                
            except Exception as e:
                print(f"Error analyzing movement for {profile.individual_id}: {e}")
                continue
        
        return patterns
    
    def _identify_hotspots(
        self, 
        appearances: List[Dict[str, Any]], 
        radius: float = 50.0
    ) -> List[Dict[str, Any]]:
        """Identify spatial hotspots where individual frequently appears."""
        if len(appearances) < 3:
            return []
        
        # Extract center points
        points = []
        for appearance in appearances:
            bbox = (appearance.get('entry_bbox') or 
                   appearance.get('exit_bbox') or 
                   appearance.get('average_bbox'))
            if bbox and len(bbox) >= 4:
                center = (bbox[0] + bbox[2]/2, bbox[1] + bbox[3]/2)
                points.append({
                    'x': center[0],
                    'y': center[1],
                    'timestamp': appearance.get('start_timestamp'),
                    'video_uuid': appearance.get('video_uuid')
                })
        
        if len(points) < 3:
            return []
        
        # Cluster points to find hotspots
        hotspots = []
        visited = set()
        
        for i, point in enumerate(points):
            if i in visited:
                continue
            
            # Find nearby points
            cluster = [point]
            for j, other_point in enumerate(points):
                if j != i and j not in visited:
                    distance = math.sqrt(
                        (point['x'] - other_point['x'])**2 + 
                        (point['y'] - other_point['y'])**2
                    )
                    if distance <= radius:
                        cluster.append(other_point)
                        visited.add(j)
            
            # Create hotspot if cluster is significant
            if len(cluster) >= 2:
                center_x = statistics.mean(p['x'] for p in cluster)
                center_y = statistics.mean(p['y'] for p in cluster)
                
                hotspot = {
                    'center': {'x': center_x, 'y': center_y},
                    'appearance_count': len(cluster),
                    'radius': radius,
                    'frequency': len(cluster) / len(appearances),
                    'videos_involved': list(set(p['video_uuid'] for p in cluster if p.get('video_uuid')))
                }
                hotspots.append(hotspot)
            
            visited.add(i)
        
        # Sort by frequency
        return sorted(hotspots, key=lambda h: h['frequency'], reverse=True)
    
    def _analyze_trajectory_segments(
        self, 
        appearances: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze individual trajectory segments between appearances."""
        if len(appearances) < 2:
            return []
        
        # Sort by timestamp
        sorted_appearances = sorted(
            appearances,
            key=lambda x: x.get('start_timestamp', '1970-01-01T00:00:00Z')
        )
        
        segments = []
        for i in range(len(sorted_appearances) - 1):
            curr = sorted_appearances[i]
            next_app = sorted_appearances[i + 1]
            
            # Calculate segment metrics
            curr_bbox = curr.get('exit_bbox') or curr.get('average_bbox')
            next_bbox = next_app.get('entry_bbox') or next_app.get('average_bbox')
            
            if curr_bbox and next_bbox and len(curr_bbox) >= 4 and len(next_bbox) >= 4:
                curr_center = (curr_bbox[0] + curr_bbox[2]/2, curr_bbox[1] + curr_bbox[3]/2)
                next_center = (next_bbox[0] + next_bbox[2]/2, next_bbox[1] + next_bbox[3]/2)
                
                distance = math.sqrt(
                    (next_center[0] - curr_center[0])**2 + 
                    (next_center[1] - curr_center[1])**2
                )
                
                # Calculate direction
                direction = math.atan2(
                    next_center[1] - curr_center[1],
                    next_center[0] - curr_center[0]
                )
                
                # Time calculation
                curr_time = curr.get('end_timestamp') or curr.get('start_timestamp')
                next_time = next_app.get('start_timestamp')
                
                time_gap = 0.0
                if curr_time and next_time:
                    if isinstance(curr_time, str):
                        curr_time = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))
                    if isinstance(next_time, str):
                        next_time = datetime.fromisoformat(next_time.replace('Z', '+00:00'))
                    time_gap = (next_time - curr_time).total_seconds()
                
                segment = {
                    'segment_id': i + 1,
                    'start_video': curr.get('video_uuid'),
                    'end_video': next_app.get('video_uuid'),
                    'distance': distance,
                    'direction_radians': direction,
                    'direction_degrees': math.degrees(direction),
                    'time_gap_seconds': time_gap,
                    'speed': distance / time_gap if time_gap > 0 else 0.0,
                    'start_point': curr_center,
                    'end_point': next_center
                }
                
                segments.append(segment)
        
        return segments
    
    def _calculate_temporal_consistency(
        self, 
        appearances: List[Dict[str, Any]]
    ) -> float:
        """Calculate temporal consistency of appearances."""
        if len(appearances) < 2:
            return 1.0
        
        # Extract timestamps
        timestamps = []
        for appearance in appearances:
            start_time = appearance.get('start_timestamp')
            if start_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                timestamps.append(start_time)
        
        if len(timestamps) < 2:
            return 1.0
        
        # Sort timestamps
        timestamps.sort()
        
        # Calculate intervals between appearances
        intervals = []
        for i in range(len(timestamps) - 1):
            interval = (timestamps[i + 1] - timestamps[i]).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return 1.0
        
        # Calculate consistency as inverse of coefficient of variation
        mean_interval = statistics.mean(intervals)
        if mean_interval == 0:
            return 1.0
        
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0.0
        coefficient_of_variation = std_interval / mean_interval
        
        # Convert to consistency score (0-1, higher is more consistent)
        consistency = 1.0 / (1.0 + coefficient_of_variation)
        
        return consistency
    
    def _perform_statistical_validation(
        self, 
        profiles: List[IndividualProfile]
    ) -> StatisticalValidation:
        """Perform comprehensive statistical validation of tracking results."""
        if not profiles:
            return StatisticalValidation(
                total_individuals=0,
                confidence_distribution={},
                temporal_distribution={},
                spatial_distribution={},
                quality_scores={},
                validation_metrics={},
                anomaly_detection={}
            )
        
        # Confidence distribution
        confidence_scores = [p.confidence_score for p in profiles]
        confidence_distribution = self._create_distribution(confidence_scores, 'confidence')
        
        # Temporal distribution (by hour of day)
        temporal_distribution = self._analyze_temporal_distribution(profiles)
        
        # Spatial distribution (by collection)
        spatial_distribution = self._analyze_spatial_distribution(profiles)
        
        # Quality scores
        quality_scores = self._calculate_aggregate_quality_scores(profiles)
        
        # Validation metrics
        validation_metrics = self._calculate_validation_metrics(profiles)
        
        # Anomaly detection
        anomaly_detection = self._detect_anomalies(profiles)
        
        return StatisticalValidation(
            total_individuals=len(profiles),
            confidence_distribution=confidence_distribution,
            temporal_distribution=temporal_distribution,
            spatial_distribution=spatial_distribution,
            quality_scores=quality_scores,
            validation_metrics=validation_metrics,
            anomaly_detection=anomaly_detection
        )
    
    def _create_distribution(
        self, 
        values: List[float], 
        name: str, 
        bins: int = 10
    ) -> Dict[str, int]:
        """Create distribution histogram of values."""
        if not values:
            return {}
        
        min_val = min(values)
        max_val = max(values)
        
        if min_val == max_val:
            return {f"{min_val:.2f}": len(values)}
        
        bin_size = (max_val - min_val) / bins
        distribution = {}
        
        for i in range(bins):
            bin_start = min_val + i * bin_size
            bin_end = min_val + (i + 1) * bin_size
            bin_label = f"{bin_start:.2f}-{bin_end:.2f}"
            
            count = sum(1 for v in values if bin_start <= v < bin_end)
            if i == bins - 1:  # Include max value in last bin
                count = sum(1 for v in values if bin_start <= v <= bin_end)
            
            distribution[bin_label] = count
        
        return distribution
    
    def _analyze_temporal_distribution(
        self, 
        profiles: List[IndividualProfile]
    ) -> Dict[str, int]:
        """Analyze temporal distribution of individual appearances."""
        hour_counts = defaultdict(int)
        
        for profile in profiles:
            for appearance in profile.video_appearances:
                timestamp = appearance.get('start_timestamp')
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour = timestamp.hour
                    hour_counts[f"{hour:02d}:00"] += 1
        
        return dict(hour_counts)
    
    def _analyze_spatial_distribution(
        self, 
        profiles: List[IndividualProfile]
    ) -> Dict[str, int]:
        """Analyze spatial distribution by collections."""
        collection_counts = defaultdict(int)
        
        for profile in profiles:
            for collection in profile.collections_visited:
                collection_counts[collection] += 1
        
        return dict(collection_counts)
    
    def _calculate_aggregate_quality_scores(
        self, 
        profiles: List[IndividualProfile]
    ) -> Dict[str, float]:
        """Calculate aggregate quality scores across all individuals."""
        all_confidence = []
        all_quality = []
        all_face_quality = []
        all_consistency = []
        
        for profile in profiles:
            quality_metrics = profile.quality_metrics
            all_confidence.append(quality_metrics.get('average_confidence', 0.0))
            all_quality.append(quality_metrics.get('average_quality', 0.0))
            all_face_quality.append(quality_metrics.get('average_face_quality', 0.0))
            all_consistency.append(quality_metrics.get('quality_consistency', 0.0))
        
        return {
            'overall_confidence': statistics.mean(all_confidence) if all_confidence else 0.0,
            'overall_quality': statistics.mean(all_quality) if all_quality else 0.0,
            'overall_face_quality': statistics.mean(all_face_quality) if all_face_quality else 0.0,
            'overall_consistency': statistics.mean(all_consistency) if all_consistency else 0.0,
            'confidence_std': statistics.stdev(all_confidence) if len(all_confidence) > 1 else 0.0
        }
    
    def _calculate_validation_metrics(
        self, 
        profiles: List[IndividualProfile]
    ) -> Dict[str, float]:
        """Calculate validation metrics for tracking quality assessment."""
        if not profiles:
            return {}
        
        # Individual-level metrics
        appearance_counts = [p.total_appearances for p in profiles]
        video_counts = [p.total_videos for p in profiles]
        confidence_scores = [p.confidence_score for p in profiles]
        
        # Movement metrics
        movement_metrics = []
        for profile in profiles:
            movement_data = profile.movement_patterns
            movement_metrics.append({
                'distance': movement_data.get('total_distance', 0.0),
                'speed': movement_data.get('average_speed', 0.0),
                'entropy': movement_data.get('movement_entropy', 0.0),
                'coverage': movement_data.get('spatial_coverage', 0.0)
            })
        
        # Calculate validation scores
        validation_metrics = {
            'average_appearances_per_individual': statistics.mean(appearance_counts),
            'average_videos_per_individual': statistics.mean(video_counts),
            'individual_confidence_score': statistics.mean(confidence_scores),
            'tracking_completeness': sum(v > 1 for v in video_counts) / len(video_counts),
            'movement_diversity': statistics.mean(m['entropy'] for m in movement_metrics),
            'spatial_coverage_score': statistics.mean(m['coverage'] for m in movement_metrics),
            'tracking_consistency': statistics.mean(
                p.quality_metrics.get('quality_consistency', 0.0) for p in profiles
            )
        }
        
        return validation_metrics
    
    def _detect_anomalies(self, profiles: List[IndividualProfile]) -> Dict[str, List[str]]:
        """Detect potential anomalies in tracking results."""
        anomalies = {
            'low_confidence_individuals': [],
            'excessive_movement_individuals': [],
            'single_appearance_individuals': [],
            'temporal_anomalies': [],
            'spatial_anomalies': []
        }
        
        # Calculate thresholds
        confidence_scores = [p.confidence_score for p in profiles]
        movement_distances = [
            p.movement_patterns.get('total_distance', 0.0) for p in profiles
        ]
        
        if confidence_scores:
            low_confidence_threshold = statistics.mean(confidence_scores) - 2 * (
                statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0
            )
        else:
            low_confidence_threshold = 0.3
        
        if movement_distances:
            high_movement_threshold = statistics.mean(movement_distances) + 2 * (
                statistics.stdev(movement_distances) if len(movement_distances) > 1 else 0.0
            )
        else:
            high_movement_threshold = 1000.0
        
        # Detect anomalies
        for profile in profiles:
            # Low confidence
            if profile.confidence_score < low_confidence_threshold:
                anomalies['low_confidence_individuals'].append(profile.individual_id)
            
            # Excessive movement
            movement_distance = profile.movement_patterns.get('total_distance', 0.0)
            if movement_distance > high_movement_threshold:
                anomalies['excessive_movement_individuals'].append(profile.individual_id)
            
            # Single appearance
            if profile.total_appearances == 1:
                anomalies['single_appearance_individuals'].append(profile.individual_id)
            
            # Temporal anomalies (very short or very long durations)
            duration = (profile.last_seen - profile.first_seen).total_seconds()
            if duration < 5:  # Less than 5 seconds
                anomalies['temporal_anomalies'].append(
                    f"{profile.individual_id}: Very short duration ({duration:.1f}s)"
                )
            elif duration > 24 * 3600:  # More than 24 hours
                anomalies['temporal_anomalies'].append(
                    f"{profile.individual_id}: Very long duration ({duration/3600:.1f}h)"
                )
            
            # Spatial anomalies (too many collections for short time)
            if len(profile.collections_visited) > 3 and duration < 3600:  # 3+ collections in <1 hour
                anomalies['spatial_anomalies'].append(
                    f"{profile.individual_id}: {len(profile.collections_visited)} collections in {duration/60:.1f}min"
                )
        
        return anomalies
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics of the analysis."""
        if not self.individuals:
            return {'status': 'no_data'}
        
        return {
            'total_individuals': len(self.individuals),
            'total_appearances': sum(p.total_appearances for p in self.individuals),
            'unique_videos': len(set().union(
                *[set(str(app.get('video_uuid', '')) for app in p.video_appearances) 
                  for p in self.individuals]
            )),
            'unique_collections': len(set().union(
                *[set(p.collections_visited) for p in self.individuals]
            )),
            'average_confidence': statistics.mean(p.confidence_score for p in self.individuals),
            'time_span': {
                'start': min(p.first_seen for p in self.individuals).isoformat(),
                'end': max(p.last_seen for p in self.individuals).isoformat(),
                'duration_hours': (
                    max(p.last_seen for p in self.individuals) - 
                    min(p.first_seen for p in self.individuals)
                ).total_seconds() / 3600
            }
        }
    
    def _generate_insights(self) -> List[str]:
        """Generate insights from the analysis."""
        insights = []
        
        if not self.individuals:
            return ["No individuals found for analysis"]
        
        # Confidence insights
        avg_confidence = statistics.mean(p.confidence_score for p in self.individuals)
        if avg_confidence > 0.8:
            insights.append(f"High overall confidence ({avg_confidence:.2f}) indicates reliable tracking")
        elif avg_confidence < 0.5:
            insights.append(f"Low overall confidence ({avg_confidence:.2f}) suggests challenging conditions")
        
        # Movement insights
        mobile_individuals = sum(
            1 for p in self.individuals 
            if p.movement_patterns.get('total_distance', 0) > 100
        )
        if mobile_individuals > len(self.individuals) * 0.7:
            insights.append(f"{mobile_individuals} individuals show significant movement patterns")
        
        # Temporal insights
        multi_video_individuals = sum(1 for p in self.individuals if p.total_videos > 1)
        if multi_video_individuals > 0:
            cross_video_rate = multi_video_individuals / len(self.individuals) * 100
            insights.append(f"{cross_video_rate:.1f}% of individuals appear across multiple videos")
        
        # Collection insights
        multi_collection_individuals = sum(
            1 for p in self.individuals if len(p.collections_visited) > 1
        )
        if multi_collection_individuals > 0:
            insights.append(f"{multi_collection_individuals} individuals visited multiple collections")
        
        # Quality insights
        if self.validation_results:
            quality_scores = self.validation_results.quality_scores
            overall_quality = quality_scores.get('overall_quality', 0.0)
            if overall_quality > 0.8:
                insights.append("High quality tracking with consistent detections")
            elif overall_quality < 0.6:
                insights.append("Quality concerns detected - review detection parameters")
        
        return insights
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        if not self.individuals:
            return ["Run tracking algorithm to generate recommendations"]
        
        # Confidence recommendations
        low_confidence_count = sum(1 for p in self.individuals if p.confidence_score < 0.6)
        if low_confidence_count > len(self.individuals) * 0.3:
            recommendations.append(
                "Consider adjusting confidence thresholds or reviewing detection quality"
            )
        
        # Movement recommendations
        high_movement_count = sum(
            1 for p in self.individuals 
            if p.movement_patterns.get('movement_entropy', 0) > 2.0
        )
        if high_movement_count > 0:
            recommendations.append(
                "Review individuals with high movement entropy for potential tracking errors"
            )
        
        # Cache recommendations
        if hasattr(self, 'cache_hit_rate'):
            if self.cache_hit_rate < 0.3:
                recommendations.append("Low cache hit rate - consider optimizing cache parameters")
            elif self.cache_hit_rate > 0.8:
                recommendations.append("Excellent cache performance - current settings optimal")
        
        # Temporal recommendations
        single_appearance_count = sum(1 for p in self.individuals if p.total_appearances == 1)
        if single_appearance_count > len(self.individuals) * 0.5:
            recommendations.append(
                "High number of single-appearance individuals - review minimum appearance thresholds"
            )
        
        # Quality recommendations
        if self.validation_results and self.validation_results.validation_metrics:
            consistency = self.validation_results.validation_metrics.get('tracking_consistency', 0.0)
            if consistency < 0.7:
                recommendations.append("Low tracking consistency - review algorithm parameters")
        
        return recommendations
    
    # Helper methods for data conversion
    def _profile_to_dict(self, profile: IndividualProfile) -> Dict[str, Any]:
        """Convert IndividualProfile to dictionary."""
        return {
            'individual_id': profile.individual_id,
            'individual_uuid': profile.individual_uuid,
            'confidence_score': profile.confidence_score,
            'total_appearances': profile.total_appearances,
            'total_videos': profile.total_videos,
            'first_seen': profile.first_seen.isoformat(),
            'last_seen': profile.last_seen.isoformat(),
            'duration_seconds': (profile.last_seen - profile.first_seen).total_seconds(),
            'collections_visited': profile.collections_visited,
            'movement_patterns': profile.movement_patterns,
            'quality_metrics': profile.quality_metrics,
            'spatial_signature': profile.spatial_signature,
            'temporal_signature': profile.temporal_signature
        }
    
    def _movement_to_dict(self, movement: MovementPattern) -> Dict[str, Any]:
        """Convert MovementPattern to dictionary."""
        return {
            'individual_id': movement.individual_id,
            'total_distance': movement.total_distance,
            'average_speed': movement.average_speed,
            'movement_entropy': movement.movement_entropy,
            'spatial_coverage': movement.spatial_coverage,
            'temporal_consistency': movement.temporal_consistency,
            'hotspots': movement.hotspots,
            'trajectory_segments': movement.trajectory_segments
        }
    
    def _validation_to_dict(self, validation: StatisticalValidation) -> Dict[str, Any]:
        """Convert StatisticalValidation to dictionary."""
        return {
            'total_individuals': validation.total_individuals,
            'confidence_distribution': validation.confidence_distribution,
            'temporal_distribution': validation.temporal_distribution,
            'spatial_distribution': validation.spatial_distribution,
            'quality_scores': validation.quality_scores,
            'validation_metrics': validation.validation_metrics,
            'anomaly_detection': validation.anomaly_detection
        }