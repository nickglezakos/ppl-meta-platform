"""
Cross-Video Individual Tracking Algorithms Package
PPL Meta Platform v2.19.13+

Phase 2: Core Algorithm Implementation
- Video Sequencing: Temporal grouping of consecutive videos
- Cross-Video Overlap Detection: IoU-based overlap identification  
- Individual Creation: Union-Find merging with confidence scoring
- Core Algorithm Integration: Complete pipeline orchestration

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from .video_sequencing import VideoSequencer, VideoSequence, VideoInfo
from .cross_video_overlap import (
    CrossVideoOverlapDetector,
    OverlapGroup,
    PersonObjectInfo
)
from .individual_creator import (
    IndividualCreator,
    UnionFind,
    IndividualCandidate,
    ConfidenceMetrics
)
from .core_algorithm import CrossVideoTrackingEngine

__all__ = [
    # Video Sequencing
    'VideoSequencer',
    'VideoSequence', 
    'VideoInfo',
    
    # Cross-Video Overlap Detection
    'CrossVideoOverlapDetector',
    'OverlapGroup',
    'PersonObjectInfo',
    
    # Individual Creation
    'IndividualCreator',
    'UnionFind',
    'IndividualCandidate',
    'ConfidenceMetrics',
    
    # Core Algorithm Integration
    'CrossVideoTrackingEngine'
]

# Algorithm version
__version__ = "2.19.13+phase2"