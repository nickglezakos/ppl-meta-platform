"""
Simple Instant Detection Sampler for Worker Integration

This module provides a lightweight sampler that processes frames
directly within the camera worker thread. It samples frames
periodically and submits them to the detection pipeline.
"""

import time
import logging
from typing import Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class InstantDetectionSampler:
    """
    Lightweight detection sampler that runs inside camera worker.
    
    Processes frames on-demand without blocking the worker thread.
    Submits frames to detection service when sampling interval reached.
    """
    
    def __init__(self, device_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize sampler.
        
        Args:
            device_id: Camera device ID
            config: Optional configuration (sampling_interval, etc.)
        """
        self.device_id = device_id
        self.config = config or {}
        self.sampling_interval = self.config.get('sampling_interval', 5)  # seconds
        
        # State tracking
        self.last_sample_time = 0.0
        self.frames_processed = 0
        self.frames_sampled = 0
        self.sampled_frames = []  # Buffer for 3 frames
        self.last_frame_time = 0.0
        
        logger.info(f"✅ Instant detection sampler initialized for {device_id} (interval: {self.sampling_interval}s)")
    
    def process_frame(self, frame: np.ndarray, frame_number: int):
        """
        Process a frame from the worker's capture loop.
        
        This is called for EVERY frame captured by the worker,
        but only samples frames according to the sampling interval.
        
        Args:
            frame: Frame to potentially sample
            frame_number: Frame number from worker
        """
        self.frames_processed += 1
        current_time = time.time()
        
        # Check if we should sample this frame
        time_since_last_sample = current_time - self.last_sample_time
        
        if time_since_last_sample >= self.sampling_interval:
            # Time to start a new sample batch
            self.sampled_frames = []
            self.last_sample_time = current_time
            logger.debug(f"🔍 Starting new detection sample for {self.device_id}")
        
        # Collect 3 frames over the sampling window (e.g., 5 seconds)
        # Frame 0: t=0s, Frame 1: t=2.5s, Frame 2: t=5s
        if len(self.sampled_frames) < 3:
            frame_in_window = len(self.sampled_frames)
            expected_time = self.last_sample_time + (frame_in_window * self.sampling_interval / 2)
            
            # Only sample if we're close to the expected time
            if abs(current_time - expected_time) < 0.5:  # 500ms tolerance
                self.sampled_frames.append({
                    'frame': frame.copy(),
                    'timestamp': current_time,
                    'frame_number': frame_number,
                    'index': frame_in_window
                })
                self.frames_sampled += 1
                logger.debug(f"🔍 Sampled frame {frame_in_window}/3 for {self.device_id}")
                
                # If we have 3 frames, submit to detection
                if len(self.sampled_frames) == 3:
                    self._submit_for_detection()
    
    def _submit_for_detection(self):
        """Submit the 3 sampled frames to detection service."""
        try:
            logger.info(f"📤 Submitting 3 frames for instant detection: {self.device_id}")
            
            # Import here to avoid circular imports
            from src.services.instant_detection import instant_detection_sampler
            
            # Use the service instance directly
            detection_service = instant_detection_sampler
            
            # Submit frames to Celery for processing (non-blocking)
            # The old detection service expects frames with specific structure
            frames_for_detection = [
                {
                    'frame': frame_data['frame'],
                    'timestamp': frame_data['timestamp'],
                    'frame_index': frame_data.get('frame_number', idx),
                    'source': 'instant_detection'
                }
                for idx, frame_data in enumerate(self.sampled_frames)
            ]
            
            detection_service._submit_to_celery(
                self.device_id,
                frames_for_detection
            )
            
            logger.info(f"✅ Submitted instant detection batch for {self.device_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to submit detection for {self.device_id}: {e}")
    
    def stop(self):
        """Stop the sampler and cleanup."""
        logger.info(f"🛑 Stopping instant detection sampler for {self.device_id}")
        self.sampled_frames = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sampler statistics."""
        return {
            'device_id': self.device_id,
            'frames_processed': self.frames_processed,
            'frames_sampled': self.frames_sampled,
            'last_sample_time': self.last_sample_time,
            'sampling_interval': self.sampling_interval
        }
