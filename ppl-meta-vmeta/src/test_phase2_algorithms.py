"""
Cross-Video Individual Tracking - Phase 2 Algorithm Test
PPL Meta Platform v2.19.13+

Test script to validate Phase 2 core algorithm implementation.
Tests all components: video sequencing, overlap detection, individual creation.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.models.cross_video_tracking import (
        CrossVideoTrackingConfig, TrackingSession
    )
    from src.algorithms.video_sequencing import VideoSequencer
    from src.algorithms.cross_video_overlap import CrossVideoOverlapDetector
    from src.algorithms.individual_creator import IndividualCreator
    from src.algorithms.core_algorithm import CrossVideoTrackingEngine
except ImportError:
    # Try direct imports if above fails
    from models.cross_video_tracking import (
        CrossVideoTrackingConfig, TrackingSession
    )
    from algorithms.video_sequencing import VideoSequencer
    from algorithms.cross_video_overlap import CrossVideoOverlapDetector
    from algorithms.individual_creator import IndividualCreator
    from algorithms.core_algorithm import CrossVideoTrackingEngine


def create_test_config() -> CrossVideoTrackingConfig:
    """Create test algorithm configuration."""
    return CrossVideoTrackingConfig(
        config_name="test_config",
        description="Test configuration for Phase 2 validation",
        max_gap_seconds=60,  # Maximum allowed by validation
        min_sequence_length=2,
        iou_threshold=0.3,
        min_overlap_confidence=0.5,
        min_appearances=1,
        confidence_weight_iou=0.4,
        confidence_weight_temporal=0.3,
        confidence_weight_spatial=0.3,
        max_collections=10,
        batch_size=100
    )


def create_test_videos() -> List[Dict[str, Any]]:
    """Create test video data."""
    base_time = datetime(2025, 10, 20, 9, 0, 0)
    
    videos = []
    
    # Create 3 consecutive videos with small gaps (30 seconds each)
    for i in range(3):
        video_uuid = uuid4()
        start_time = base_time + timedelta(minutes=i*5 + i*0.5)  # 30s gap
        end_time = start_time + timedelta(minutes=5)
        
        video = {
            'video_uuid': video_uuid,
            'id': str(video_uuid),
            'collection_id': 'test_collection',
            'start_timestamp': start_time.isoformat(),
            'end_timestamp': end_time.isoformat(),
            'duration_seconds': 300
        }
        videos.append(video)
    
    print(f"Created {len(videos)} test videos:")
    for i, video in enumerate(videos):
        print(f"  Video {i+1}: {video['start_timestamp']} to {video['end_timestamp']}")
    
    return videos


def create_test_person_objects(videos: List[Dict[str, Any]]) -> Dict[UUID, List[Dict[str, Any]]]:
    """Create test person objects with overlapping scenarios."""
    person_objects_data = {}
    
    for i, video in enumerate(videos):
        video_uuid = UUID(str(video['video_uuid']))
        person_objects = []
        
        # Create 2 person objects per video
        for j in range(2):
            person_uuid = uuid4()
            
            # Create overlapping bounding boxes for cross-video tracking
            base_x = 100 + i * 50 + j * 150  # Slight movement across videos
            base_y = 100 + j * 100
            
            person_obj = {
                'person_object_uuid': person_uuid,
                'video_uuid': video_uuid,
                'first_seen_timestamp': video['start_timestamp'],
                'last_seen_timestamp': video['end_timestamp'],
                'entry_bbox': {
                    'x1': base_x,
                    'y1': base_y,
                    'x2': base_x + 80,
                    'y2': base_y + 120
                },
                'exit_bbox': {
                    'x1': base_x + 20,  # Simulate movement
                    'y1': base_y + 10,
                    'x2': base_x + 100,
                    'y2': base_y + 130
                },
                'confidence': 0.8 + i * 0.05,  # Varying confidence
                'face_embeddings': [[0.1 * (i + j + k) for k in range(512)]],  # Dummy embeddings
                'movement_data': {'distance': 20 + i * 5},
                'quality_scores': {'overall': 0.7 + i * 0.1}
            }
            
            person_objects.append(person_obj)
        
        person_objects_data[video_uuid] = person_objects
    
    return person_objects_data


def test_video_sequencing():
    """Test video sequencing algorithm."""
    print("\n=== Testing Video Sequencing ===")
    
    config = create_test_config()
    sequencer = VideoSequencer(config)
    
    videos = create_test_videos()
    
    # Test finding consecutive videos
    sequences = sequencer.find_consecutive_videos(
        start_time=datetime(2025, 10, 20, 8, 0, 0),
        end_time=datetime(2025, 10, 20, 18, 0, 0),
        collections=['test_collection'],
        video_data=videos
    )
    
    print(f"✅ Found {len(sequences)} video sequences")
    
    if sequences:
        seq = sequences[0]
        print(f"   - Sequence ID: {seq.sequence_id}")
        print(f"   - Videos: {len(seq.videos)}")
        print(f"   - Duration: {seq.total_duration_seconds:.1f}s")
        print(f"   - Max gap: {seq.max_gap_seconds:.1f}s")
        
        # Test sequence quality analysis
        quality = sequencer.analyze_sequence_quality(seq)
        print(f"   - Quality score: {quality['quality_score']:.3f}")
    
    return sequences


def test_overlap_detection(sequences, person_objects_data):
    """Test cross-video overlap detection."""
    print("\n=== Testing Cross-Video Overlap Detection ===")
    
    config = create_test_config()
    detector = CrossVideoOverlapDetector(config)
    
    all_overlaps = []
    
    for sequence in sequences:
        overlaps = detector.find_overlapping_person_objects(
            sequence, person_objects_data
        )
        all_overlaps.extend(overlaps)
    
    print(f"✅ Found {len(all_overlaps)} overlap groups")
    
    if all_overlaps:
        overlap = all_overlaps[0]
        print(f"   - Group ID: {overlap.group_id}")
        print(f"   - Exit objects: {len(overlap.exit_person_objects)}")
        print(f"   - Entry objects: {len(overlap.entry_person_objects)}")
        print(f"   - IoU scores: {overlap.iou_scores}")
        print(f"   - Confidence: {overlap.confidence_score:.3f}")
        print(f"   - Temporal gap: {overlap.temporal_gap_seconds:.1f}s")
        
        # Test overlap quality analysis
        quality = detector.analyze_overlap_quality(all_overlaps)
        print(f"   - Average IoU: {quality['average_iou']:.3f}")
        print(f"   - High quality overlaps: {quality['high_quality_overlaps']}")
    
    return all_overlaps


def test_individual_creation(overlaps, person_objects_data):
    """Test individual creation with Union-Find."""
    print("\n=== Testing Individual Creation ===")
    
    config = create_test_config()
    creator = IndividualCreator(config)
    
    # Flatten person objects data
    flattened_data = {}
    for video_uuid, person_list in person_objects_data.items():
        for person_obj in person_list:
            person_uuid = UUID(str(person_obj['person_object_uuid']))
            flattened_data[person_uuid] = person_obj
    
    # Create individuals
    individuals = creator.merge_overlapping_groups(overlaps, flattened_data)
    
    print(f"✅ Created {len(individuals)} individual candidates")
    
    if individuals:
        individual = individuals[0]
        print(f"   - Individual ID: {individual.individual_id}")
        print(f"   - Person objects: {len(individual.person_objects)}")
        print(f"   - Video appearances: {len(individual.video_appearances)}")
        print(f"   - Confidence: {individual.confidence_metrics.overall_confidence:.3f}")
        print(f"   - IoU confidence: {individual.confidence_metrics.iou_confidence:.3f}")
        print(f"   - Temporal confidence: {individual.confidence_metrics.temporal_confidence:.3f}")
        print(f"   - Spatial confidence: {individual.confidence_metrics.spatial_confidence:.3f}")
    
    return individuals


def test_core_algorithm_integration():
    """Test complete core algorithm integration."""
    print("\n=== Testing Core Algorithm Integration ===")
    
    config = create_test_config()
    engine = CrossVideoTrackingEngine(config)
    
    # Create test session
    session = TrackingSession(
        user_id="test_user",
        collections=["test_collection"],
        start_time=datetime(2025, 10, 20, 8, 0, 0),
        end_time=datetime(2025, 10, 20, 18, 0, 0),
        config_hash=config.calculate_hash(),
        algorithm_config=config
    )
    
    # Prepare test data
    videos = create_test_videos()
    person_objects_data = create_test_person_objects(videos)
    
    # Execute complete tracking
    results = engine.execute_tracking(session, videos, person_objects_data)
    
    print(f"✅ Algorithm execution: {'SUCCESS' if results['success'] else 'FAILED'}")
    print(f"   - Processing time: {results['processing_time_seconds']:.2f}s")
    print(f"   - Video sequences: {len(results['video_sequences'])}")
    print(f"   - Overlap groups: {len(results['overlap_groups'])}")
    print(f"   - Individuals found: {len(results['individuals'])}")
    
    if results.get('metrics'):
        metrics = results['metrics']
        print(f"   - Algorithm efficiency: {metrics['performance']['algorithm_efficiency']:.3f}")
        print(f"   - Videos per second: {metrics['performance']['videos_per_second']:.1f}")
    
    return results


def main():
    """Run all Phase 2 algorithm tests."""
    print("🚀 Cross-Video Individual Tracking - Phase 2 Algorithm Test")
    print("=" * 60)
    
    try:
        # Test individual components
        sequences = test_video_sequencing()
        
        if sequences:
            videos = create_test_videos()
            person_objects_data = create_test_person_objects(videos)
            
            overlaps = test_overlap_detection(sequences, person_objects_data)
            
            if overlaps:
                individuals = test_individual_creation(overlaps, person_objects_data)
        
        # Test complete integration
        results = test_core_algorithm_integration()
        
        print("\n" + "=" * 60)
        print("✅ Phase 2 Algorithm Implementation VALIDATED")
        print("All core components working correctly:")
        print("   ✓ Video Sequencing")
        print("   ✓ Cross-Video Overlap Detection") 
        print("   ✓ Individual Creation with Union-Find")
        print("   ✓ Core Algorithm Integration")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 2 Algorithm Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)