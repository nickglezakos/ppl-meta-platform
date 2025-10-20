"""
Cross-Video Individual Tracking - Video Sequencing Algorithm
PPL Meta Platform v2.19.13+

Implements temporal video sequencing logic to find consecutive videos
and group them by temporal proximity for cross-video tracking.

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
except ImportError:
    from models.cross_video_tracking import CrossVideoTrackingConfig

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Simple video information for sequencing."""
    video_uuid: UUID
    collection_id: str
    start_timestamp: datetime
    end_timestamp: datetime
    duration_seconds: float
    
    def __post_init__(self):
        """Validate video info after creation."""
        if self.end_timestamp <= self.start_timestamp:
            raise ValueError("end_timestamp must be after start_timestamp")


@dataclass
class VideoSequence:
    """Sequence of temporally consecutive videos."""
    sequence_id: str
    videos: List[VideoInfo]
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    max_gap_seconds: float
    
    def get_consecutive_pairs(self) -> List[tuple[VideoInfo, VideoInfo]]:
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


class VideoSequencer:
    """
    Video sequencing algorithm for cross-video tracking.
    
    Finds temporally consecutive video sequences and groups videos
    by temporal proximity for efficient cross-video analysis.
    """
    
    def __init__(self, config: CrossVideoTrackingConfig):
        """Initialize with algorithm configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.VideoSequencer")
    
    def find_consecutive_videos(
        self,
        start_time: datetime,
        end_time: datetime,
        collections: List[str],
        video_data: List[Dict[str, Any]]
    ) -> List[VideoSequence]:
        """
        Find temporally consecutive video sequences.
        
        Args:
            start_time: Analysis time range start
            end_time: Analysis time range end
            collections: Collection IDs to process
            video_data: List of video metadata dictionaries
            
        Returns:
            List of video sequences found
        """
        self.logger.info(
            f"Finding consecutive videos: {len(video_data)} videos, "
            f"collections: {collections}, "
            f"time range: {start_time} to {end_time}"
        )
        
        # Convert to VideoInfo objects and filter
        videos = self._prepare_video_info(
            video_data, collections, start_time, end_time
        )
        
        if not videos:
            self.logger.warning("No videos found in specified criteria")
            return []
        
        # Sort videos by start timestamp
        videos.sort(key=lambda v: v.start_timestamp)
        
        # Group videos into sequences
        sequences = self._group_videos_into_sequences(videos)
        
        self.logger.info(f"Found {len(sequences)} video sequences")
        return sequences
    
    def _prepare_video_info(
        self,
        video_data: List[Dict[str, Any]],
        collections: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[VideoInfo]:
        """Convert and filter video data to VideoInfo objects."""
        videos = []
        
        for data in video_data:
            try:
                # Extract video information
                video_uuid = UUID(str(data.get('video_uuid', data.get('id'))))
                collection_id = data.get('collection_id', '')
                video_start = self._parse_timestamp(data.get('start_timestamp'))
                video_end = self._parse_timestamp(data.get('end_timestamp'))
                
                # Filter by collection if specified
                if collections and collection_id not in collections:
                    continue
                
                # Filter by time range
                if not self._video_overlaps_timerange(
                    video_start, video_end, start_time, end_time
                ):
                    continue
                
                # Calculate duration
                duration = (video_end - video_start).total_seconds()
                
                # Create VideoInfo object
                video_info = VideoInfo(
                    video_uuid=video_uuid,
                    collection_id=collection_id,
                    start_timestamp=video_start,
                    end_timestamp=video_end,
                    duration_seconds=duration
                )
                
                videos.append(video_info)
                
            except Exception as e:
                self.logger.warning(f"Failed to process video data: {e}")
                continue
        
        return videos
    
    def _parse_timestamp(self, timestamp_value: Any) -> datetime:
        """Parse various timestamp formats to datetime."""
        if isinstance(timestamp_value, datetime):
            return timestamp_value
        elif isinstance(timestamp_value, str):
            # Try ISO format first
            try:
                return datetime.fromisoformat(
                    timestamp_value.replace('Z', '+00:00')
                )
            except ValueError:
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        return datetime.strptime(timestamp_value, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Unable to parse timestamp: {timestamp_value}")
        else:
            raise ValueError(f"Invalid timestamp type: {type(timestamp_value)}")
    
    def _video_overlaps_timerange(
        self,
        video_start: datetime,
        video_end: datetime,
        range_start: datetime,
        range_end: datetime
    ) -> bool:
        """Check if video overlaps with specified time range."""
        return not (video_end <= range_start or video_start >= range_end)
    
    def _group_videos_into_sequences(
        self, videos: List[VideoInfo]
    ) -> List[VideoSequence]:
        """Group videos by temporal proximity."""
        if not videos:
            return []
        
        sequences = []
        current_sequence = [videos[0]]
        
        for i in range(1, len(videos)):
            current_video = videos[i]
            previous_video = videos[i - 1]
            
            # Calculate gap between videos
            gap_seconds = (
                current_video.start_timestamp - 
                previous_video.end_timestamp
            ).total_seconds()
            
            # Check if videos are consecutive
            if gap_seconds <= self.config.max_gap_seconds:
                # Add to current sequence
                current_sequence.append(current_video)
            else:
                # Start new sequence if current one meets minimum length
                if len(current_sequence) >= self.config.min_sequence_length:
                    sequences.append(
                        self._create_video_sequence(current_sequence)
                    )
                
                # Start new sequence with current video
                current_sequence = [current_video]
        
        # Add final sequence if it meets minimum length
        if len(current_sequence) >= self.config.min_sequence_length:
            sequences.append(self._create_video_sequence(current_sequence))
        
        return sequences
    
    def _create_video_sequence(
        self, videos: List[VideoInfo]
    ) -> VideoSequence:
        """Create VideoSequence object from video list."""
        if not videos:
            raise ValueError("Cannot create sequence from empty video list")
        
        # Calculate sequence properties
        start_time = min(v.start_timestamp for v in videos)
        end_time = max(v.end_timestamp for v in videos)
        total_duration = sum(v.duration_seconds for v in videos)
        
        # Calculate maximum gap
        max_gap = 0.0
        for i in range(1, len(videos)):
            gap = (
                videos[i].start_timestamp - 
                videos[i-1].end_timestamp
            ).total_seconds()
            max_gap = max(max_gap, gap)
        
        # Generate sequence ID
        sequence_id = f"seq_{videos[0].video_uuid}_{len(videos)}"
        
        return VideoSequence(
            sequence_id=sequence_id,
            videos=videos,
            start_time=start_time,
            end_time=end_time,
            total_duration_seconds=total_duration,
            max_gap_seconds=max_gap
        )
    
    def analyze_sequence_quality(
        self, sequence: VideoSequence
    ) -> Dict[str, Any]:
        """Analyze the quality and characteristics of a video sequence."""
        gaps = sequence.calculate_gaps()
        
        return {
            'sequence_id': sequence.sequence_id,
            'video_count': len(sequence.videos),
            'total_duration_minutes': sequence.total_duration_seconds / 60,
            'span_duration_minutes': (
                sequence.end_time - sequence.start_time
            ).total_seconds() / 60,
            'average_gap_seconds': sum(gaps) / len(gaps) if gaps else 0,
            'max_gap_seconds': max(gaps) if gaps else 0,
            'min_gap_seconds': min(gaps) if gaps else 0,
            'collections_covered': list(
                set(v.collection_id for v in sequence.videos)
            ),
            'quality_score': self._calculate_sequence_quality_score(sequence)
        }
    
    def _calculate_sequence_quality_score(
        self, sequence: VideoSequence
    ) -> float:
        """Calculate quality score for a video sequence."""
        # Base score from sequence length
        length_score = min(len(sequence.videos) / 10, 1.0)
        
        # Gap penalty (lower gaps = higher score)
        gaps = sequence.calculate_gaps()
        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            gap_score = max(0, 1.0 - (avg_gap / self.config.max_gap_seconds))
        else:
            gap_score = 1.0
        
        # Duration score (longer videos = higher score)
        avg_duration = sequence.total_duration_seconds / len(sequence.videos)
        duration_score = min(avg_duration / 300, 1.0)  # 5 minutes = 1.0
        
        # Weighted average
        return (length_score * 0.4 + gap_score * 0.4 + duration_score * 0.2)
    
    def get_sequence_statistics(
        self, sequences: List[VideoSequence]
    ) -> Dict[str, Any]:
        """Get comprehensive statistics about video sequences."""
        if not sequences:
            return {
                'total_sequences': 0,
                'total_videos': 0,
                'average_sequence_length': 0,
                'total_duration_hours': 0
            }
        
        total_videos = sum(len(seq.videos) for seq in sequences)
        total_duration = sum(seq.total_duration_seconds for seq in sequences)
        
        return {
            'total_sequences': len(sequences),
            'total_videos': total_videos,
            'average_sequence_length': total_videos / len(sequences),
            'max_sequence_length': max(len(seq.videos) for seq in sequences),
            'min_sequence_length': min(len(seq.videos) for seq in sequences),
            'total_duration_hours': total_duration / 3600,
            'average_sequence_duration_minutes': (
                total_duration / len(sequences) / 60
            ),
            'collections_covered': list(set(
                v.collection_id 
                for seq in sequences 
                for v in seq.videos
            ))
        }