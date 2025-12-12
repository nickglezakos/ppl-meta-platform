"""
Instant Temporal Detection Module

Provides real-time face detection by sampling 3 frames from the camera stream
every 5 seconds. Uses the SAME detection quality as the main pipeline but
without database storage for instant feedback.

Key Features:
- Non-blocking parallel thread
- Two-stage detection (Haar + Dlib)
- Person objects grouping across 3 frames
- Age/gender detection on best quality face
- Memory-only results (5 second TTL)
- Zero interference with existing pipeline
"""

import threading
import asyncio
import time
import uuid
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging

import cv2
import numpy as np
import aiohttp

logger = logging.getLogger(__name__)


class InstantDetectionSampler:
    """
    Samples 3 frames from camera stream for instant face detection.
    Uses SAME detection quality as main pipeline by calling service APIs.
    
    Key differences from main pipeline:
    - Only 3 frames (vs 90 frames)
    - No database storage
    - Includes age/gender detection (ONE face per person)
    - Results expire after 5 seconds
    - Non-blocking parallel thread
    
    Services used:
    - Vision Service: Face detection (Haar + Dlib)
    - VMeta Service: Age/gender detection (DeepFace)
    """
    
    def __init__(
        self,
        vision_service_url: str = "http://localhost:8003",
        vmeta_service_url: str = "http://localhost:8008",
        orchestrator_service_url: str = "http://localhost:8002",
        sampling_interval: int = 5,
        temporal_window: float = 1.0
    ):
        self._detection_thread = None
        self._running = False
        self.vision_service_url = vision_service_url
        self.vmeta_service_url = vmeta_service_url
        self.orchestrator_service_url = orchestrator_service_url
        self.sampling_interval = sampling_interval
        self.temporal_window = temporal_window
        
        # Results cache (in-memory only)
        self.results_cache: Dict[str, Dict] = {}
        
        logger.info("✅ Instant detection sampler initialized (Vision + VMeta APIs)")
    
    def start_sampling(self, camera_id: str, camera_capture):
        """
        Start parallel frame sampling thread (non-blocking)
        
        Args:
            camera_id: Unique camera identifier
            camera_capture: Shared cv2.VideoCapture object from recording session
        """
        if self._running:
            logger.warning(f"Instant detection already running for camera {camera_id}")
            return
        
        self._running = True
        self._detection_thread = threading.Thread(
            target=self._sample_loop,
            args=(camera_id, camera_capture),
            daemon=True,
            name=f"instant-detection-{camera_id}"
        )
        self._detection_thread.start()
        logger.info(f"🚀 Instant detection sampler started for camera {camera_id} (using shared capture)")
    
    def stop_sampling(self):
        """Stop the sampling thread"""
        self._running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=2)
        logger.info("🛑 Instant detection sampler stopped")
    
    def _sample_loop(self, camera_id: str, camera_capture):
        """
        Main sampling loop - runs every N seconds using shared VideoCapture
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._running:
            try:
                start_time = time.time()
                
                # Capture 3 frames with temporal spacing (using shared capture)
                frames = self._capture_3_frames_shared(camera_capture)
                
                if len(frames) == 3:
                    # Process with SAME quality as main pipeline
                    result = loop.run_until_complete(
                        self._process_3_frames(camera_id, frames)
                    )
                    
                    # Store in memory cache
                    self._cache_result(camera_id, result)
                    
                    # Log success
                    logger.info(
                        f"✅ Instant detection complete: "
                        f"{len(result['person_objects'])} people, "
                        f"{result['total_faces_detected']} faces, "
                        f"{result['processing_time_seconds']:.2f}s"
                    )
                else:
                    logger.warning(f"⚠️ Only captured {len(frames)}/3 frames")
                
                # Wait for next iteration (accounting for processing time)
                elapsed = time.time() - start_time
                sleep_time = max(0, self.sampling_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ Instant detection error: {e}", exc_info=True)
                time.sleep(self.sampling_interval)
    
    def _capture_3_frames_shared(self, cap) -> List[Dict]:
        """
        Capture 3 frames from SHARED camera stream (no new VideoCapture).
        
        Temporal spacing:
        - Frame 0: t=0.0s
        - Frame 1: t=0.5s (temporal_window / 2)
        - Frame 2: t=1.0s (temporal_window)
        
        Total window: 1 second (captures motion context)
        
        Args:
            cap: Shared cv2.VideoCapture object from recording session
        
        Returns:
            List of frame dictionaries with frame, timestamp, and index
        """
        frames = []
        
        try:
            if not cap or not cap.isOpened():
                logger.error("Shared camera capture not available")
                return frames
            
            frame_spacing = self.temporal_window / 2  # 0.5s for 1.0s window
            
            for i in range(3):
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    logger.debug(f"📸 Captured frame {i}: shape={frame.shape}, size={frame.size}")
                    frames.append({
                        "frame": frame.copy(),
                        "timestamp": i * frame_spacing,
                        "frame_index": i
                    })
                    
                    # Wait between frames (except after last frame)
                    if i < 2:
                        time.sleep(frame_spacing)
                else:
                    logger.warning(f"Failed to capture frame {i} from shared capture (ret={ret}, frame={'None' if frame is None else 'exists'})")
                    break
                    
        except Exception as e:
            logger.error(f"Error capturing frames from shared capture: {e}")
        
        return frames
    
    def _capture_3_frames(self, camera_path: str) -> List[Dict]:
        """
        DEPRECATED: Legacy method that opens new VideoCapture.
        Use _capture_3_frames_shared() instead to avoid resource contention.
        
        Kept for backward compatibility only.
        """
        frames = []
        cap = None
        
        try:
            cap = cv2.VideoCapture(camera_path)
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera: {camera_path}")
                return frames
            
            frame_spacing = self.temporal_window / 2  # 0.5s for 1.0s window
            
            for i in range(3):
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    frames.append({
                        "frame": frame.copy(),
                        "timestamp": i * frame_spacing,
                        "frame_index": i
                    })
                    
                    # Wait between frames (except after last frame)
                    if i < 2:
                        time.sleep(frame_spacing)
                else:
                    logger.warning(f"Failed to capture frame {i}")
                    break
                    
        except Exception as e:
            logger.error(f"Error capturing frames: {e}")
        finally:
            if cap:
                cap.release()
        
        return frames
    
    async def _process_3_frames(
        self,
        camera_id: str,
        frames: List[Dict]
    ) -> Dict:
        """
        Process 3 frames using Vision Service APIs.
        
        This reuses existing Vision Service capabilities:
        1. Send 3 frames to Vision Service for face detection (Haar + Dlib)
        2. Send face detections to Vision Service for person grouping (spatial/IoU)
        3. Send best face per person to VMeta Service for age/gender
        
        NO local models needed - NO database storage - results kept in memory only
        """
        start_time = time.time()
        
        # Generate session UUID for this instant detection iteration
        session_uuid = str(uuid.uuid4())
        
        # Step 1: Send frames to Vision Service for face detection
        all_face_detections = []
        
        async with aiohttp.ClientSession() as session:
            for frame_data in frames:
                frame = frame_data["frame"]
                frame_index = frame_data["frame_index"]
                timestamp = frame_data["timestamp"]
                
                # Call Vision Service API for detection
                detections = await self._detect_faces_via_vision_service(
                    session,
                    frame,
                    frame_index,
                    timestamp
                )
                
                all_face_detections.extend(detections)
        
        total_faces = len(all_face_detections)
        
        # Step 2: Group faces into person objects using Vision Service
        # This uses the existing spatial/IoU grouping from Vision Service
        person_objects = await self._create_person_objects_via_vision_service(
            session_uuid,
            all_face_detections
        )
        
        # Step 3: Age/gender detection via VMeta Service
        # Only process ONE face per person (the best quality one)
        async with aiohttp.ClientSession() as session:
            for person in person_objects:
                # Get faces for this person
                person_faces = person.get("faces", [])
                
                if not person_faces:
                    person["age_gender"] = self._default_age_gender()
                    continue
                
                # Find highest confidence face for this person
                best_face = max(
                    person_faces,
                    key=lambda f: f.get("confidence", 0.0)
                )
                
                # Get the frame for this face
                frame_index = best_face.get("frame_index", 0)
                if frame_index < len(frames):
                    # Get age/gender from VMeta Service (DeepFace models)
                    age_gender = await self._get_age_gender_via_vmeta_service(
                        session,
                        frames[frame_index]["frame"],
                        best_face["bbox"]
                    )
                    person["age_gender"] = age_gender
                else:
                    person["age_gender"] = self._default_age_gender()
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "camera_id": camera_id,
            "timestamp": datetime.now().isoformat(),
            "temporal_window_seconds": self.temporal_window,
            "frames_processed": len(frames),
            "total_faces_detected": total_faces,
            "person_objects": person_objects,
            "processing_time_seconds": processing_time,
            "detection_method": "vision_service_spatial_grouping",
            "storage": "none"
        }
    
    async def _detect_faces_via_vision_service(
        self,
        session: aiohttp.ClientSession,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float
    ) -> List[Dict]:
        """
        Detect faces by calling Vision Service API (reuses existing models).
        
        This avoids duplicating model files - Vision Service already has:
        - Haar Cascade classifier
        - Dlib CNN detector
        - Face embedding model
        """
        try:
            # Validate frame
            if frame is None or frame.size == 0:
                logger.warning(f"⚠️ Frame {frame_index} is None or empty")
                return []
            
            logger.debug(f"📸 Frame {frame_index} shape: {frame.shape}, dtype: {frame.dtype}")
            
            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            logger.debug(f"📸 Frame {frame_index} encoded to {len(frame_bytes)} bytes")
            
            # Call Vision Service single-frame detection endpoint
            data = aiohttp.FormData()
            data.add_field(
                'file',
                frame_bytes,
                filename=f'frame_{frame_index}.jpg',
                content_type='image/jpeg'
            )
            
            url = f"{self.vision_service_url}/faces/detect-single-frame"
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    faces_count = len(result.get("faces", []))
                    logger.info(f"🔍 Vision Service returned {faces_count} faces for frame {frame_index}")
                    
                    # Convert Vision Service format to our format
                    detections = []
                    for face in result.get("faces", []):
                        detections.append({
                            "face_id": face.get("face_id", str(uuid.uuid4())),
                            "frame_index": frame_index,
                            "timestamp": timestamp,
                            "bbox": face.get("bbox", [0, 0, 0, 0]),
                            "confidence": face.get("confidence", 0.0),
                            "method": "two_stage_haar_dlib",
                            "embedding": face.get("embedding", [0.0] * 128)
                        })
                    
                    return detections
                else:
                    response_text = await response.text()
                    logger.error(f"Vision Service error: {response.status} - {response_text}")
                    return []
        
        except Exception as e:
            logger.error(f"Error calling Vision Service: {e}")
            return []
    
    async def _get_age_gender_via_vmeta_service(
        self,
        session: aiohttp.ClientSession,
        frame: np.ndarray,
        bbox: List[int]
    ) -> Dict:
        """
        Get age/gender by calling VMeta Service API.
        
        VMeta Service uses DeepFace models for age/gender detection.
        This is called ONCE per person (for the best quality face).
        """
        try:
            # Extract face region
            x1, y1, x2, y2 = bbox
            face_roi = frame[y1:y2, x1:x2]
            
            if face_roi.size == 0:
                return self._default_age_gender()
            
            # Encode face as JPEG
            _, buffer = cv2.imencode('.jpg', face_roi)
            face_bytes = buffer.tobytes()
            
            # Call VMeta Service age/gender endpoint
            data = aiohttp.FormData()
            data.add_field(
                'file',
                face_bytes,
                filename='face.jpg',
                content_type='image/jpeg'
            )
            
            url = f"{self.vmeta_service_url}/api/v1/ml/detect-age-gender"
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Format age range from min/max
                    age_min = result.get("age_min", 0)
                    age_max = result.get("age_max", 100)
                    age_range = f"({age_min}-{age_max})"
                    
                    return {
                        "age_range": age_range,
                        "age_confidence": result.get("age_confidence", 0.0),
                        "gender": result.get("gender", "unknown"),
                        "gender_confidence": result.get("gender_confidence", 0.0)
                    }
                else:
                    logger.error(f"VMeta Service age/gender error: {response.status}")
                    return self._default_age_gender()
        
        except Exception as e:
            logger.error(f"Error getting age/gender from VMeta: {e}")
            return self._default_age_gender()
    
    async def _create_person_objects_via_vision_service(
        self,
        session_uuid: str,
        face_detections: List[Dict]
    ) -> List[Dict]:
        """
        Group faces into person objects using Orchestrator's spatial/IoU grouping.
        
        This uses the same proven grouping algorithm as Enhanced Logic V2 (person-objects pipeline).
        Groups faces across multiple frames based on spatial overlap and IoU.
        """
        if not face_detections:
            return []
        
        try:
            # Use Orchestrator Service (same as Enhanced Logic V2)
            orchestrator_url = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8002")
            
            async with aiohttp.ClientSession() as session:
                url = f"{orchestrator_url}/api/v1/person-objects/from-faces"
                
                payload = {
                    "session_uuid": session_uuid,
                    "face_detections": face_detections,
                    "tolerance_percent": 20.0,  # Same as Enhanced Logic V2
                    "enable_quality_analysis": True,
                    "storage_mode": "memory_only"  # Don't persist instant detection results
                }
                
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract person objects from response
                        person_groups = result.get("person_groups", [])
                        
                        # Convert to simpler format for instant detection
                        person_objects = []
                        for group in person_groups:
                            person_faces = []
                            for face_obj in group.get("representative_faces", []):
                                person_faces.append(face_obj.get("face_data", {}))
                            
                            if person_faces:
                                person_objects.append({
                                    "person_id": group.get("person_uuid", str(uuid.uuid4())),
                                    "faces": person_faces,
                                    "face_count": len(person_faces),
                                    "avg_confidence": sum(f.get("confidence", 0) for f in person_faces) / len(person_faces),
                                    "best_bbox": max(person_faces, key=lambda f: f.get("confidence", 0)).get("bbox", [0,0,0,0])
                                })
                        
                        logger.info(
                            f"Orchestrator grouped {len(face_detections)} faces "
                            f"into {len(person_objects)} person objects"
                        )
                        
                        return person_objects
                    else:
                        response_text = await response.text()
                        logger.warning(
                            f"Orchestrator person grouping returned {response.status}: {response_text[:200]}"
                        )
                        # Fallback: simple spatial grouping locally
                        return self._simple_spatial_grouping(face_detections)
        
        except asyncio.TimeoutError:
            logger.warning("Orchestrator timeout - using simple local grouping")
            return self._simple_spatial_grouping(face_detections)
        except Exception as e:
            logger.warning(f"Orchestrator error: {e} - using simple local grouping")
            return self._simple_spatial_grouping(face_detections)
    
    def _simple_spatial_grouping(
        self,
        face_detections: List[Dict]
    ) -> List[Dict]:
        """
        Simple spatial grouping fallback when Orchestrator is unavailable.
        Groups faces that overlap spatially (within tolerance).
        """
        if not face_detections:
            return []
        
        # Sort by frame index and confidence
        sorted_faces = sorted(
            face_detections,
            key=lambda f: (f.get("frame_index", 0), -f.get("confidence", 0))
        )
        
        person_objects = []
        used_faces = set()
        
        for i, face in enumerate(sorted_faces):
            if i in used_faces:
                continue
            
            # Start new person group
            group_faces = [face]
            used_faces.add(i)
            face_bbox = face.get("bbox", [0, 0, 0, 0])
            
            # Find similar faces in other frames
            for j, other_face in enumerate(sorted_faces):
                if j in used_faces or j <= i:
                    continue
                
                # Check if faces overlap spatially (simple IoU check)
                other_bbox = other_face.get("bbox", [0, 0, 0, 0])
                
                if self._boxes_overlap(face_bbox, other_bbox, tolerance=0.3):
                    group_faces.append(other_face)
                    used_faces.add(j)
            
            # Create person object
            person_objects.append({
                "person_id": str(uuid.uuid4()),
                "faces": group_faces,
                "face_count": len(group_faces),
                "avg_confidence": sum(f.get("confidence", 0) for f in group_faces) / len(group_faces),
                "best_bbox": max(group_faces, key=lambda f: f.get("confidence", 0)).get("bbox", [0,0,0,0])
            })
        
        logger.info(
            f"Simple grouping: {len(face_detections)} faces "
            f"→ {len(person_objects)} person objects"
        )
        
        return person_objects
    
    def _boxes_overlap(self, bbox1: List, bbox2: List, tolerance: float = 0.3) -> bool:
        """Check if two bounding boxes overlap (simple IoU)"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Calculate intersection
        x_left = max(x1_min, x2_min)
        y_top = max(y1_min, y2_min)
        x_right = min(x1_max, x2_max)
        y_bottom = min(y1_max, y2_max)
        
        if x_right < x_left or y_bottom < y_top:
            return False
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union
        bbox1_area = (x1_max - x1_min) * (y1_max - y1_min)
        bbox2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = bbox1_area + bbox2_area - intersection_area
        
        # IoU
        iou = intersection_area / union_area if union_area > 0 else 0
        
        return iou >= tolerance
    
    def _create_fallback_person_objects(
        self,
        face_detections: List[Dict]
    ) -> List[Dict]:
        """
        Fallback: Create one person object per face if Vision Service unavailable.
        """
        return [
            {
                "person_id": str(uuid.uuid4()),
                "faces": [face],
                "face_count": 1,
                "avg_confidence": face.get("confidence", 0.0),
                "best_bbox": face.get("bbox", [0, 0, 0, 0])
            }
            for face in face_detections
        ]
    
    def _default_age_gender(self) -> Dict:
        """Return default age/gender when detection fails"""
        return {
            "age_range": "unknown",
            "age_confidence": 0.0,
            "gender": "unknown",
            "gender_confidence": 0.0
        }
    
    def _cache_result(self, camera_id: str, result: Dict):
        """
        Store result in memory cache.
        
        Results stay in memory until replaced by next iteration.
        This allows other hooks to access the latest instant detection results
        while recording is active.
        """
        self.results_cache[camera_id] = {
            "result": result,
            "cached_at": time.time(),
            "iteration": self.results_cache.get(camera_id, {}).get("iteration", 0) + 1
        }
    
    def get_cached_result(self, camera_id: str) -> Optional[Dict]:
        """
        Retrieve latest cached result for a camera.
        
        Results stay in memory until replaced by next iteration,
        making them available to other hooks during recording.
        
        Returns:
            Latest result dict or None if not found
        """
        cached = self.results_cache.get(camera_id)
        
        if cached:
            return cached["result"]
        
        return None
    
    def get_all_cached_results(self) -> Dict[str, Dict]:
        """
        Get all cached results for all cameras.
        
        Returns:
            Dict mapping camera_id to latest result
        """
        return {
            camera_id: cached["result"]
            for camera_id, cached in self.results_cache.items()
        }
    
    def clear_cache(self, camera_id: Optional[str] = None):
        """
        Clear cached results.
        
        Args:
            camera_id: Specific camera to clear, or None to clear all
        """
        if camera_id:
            if camera_id in self.results_cache:
                del self.results_cache[camera_id]
        else:
            self.results_cache.clear()
    
    def get_status(self) -> Dict:
        """
        Get current status of instant detection sampler
        """
        return {
            "running": self._running,
            "thread_alive": self._detection_thread.is_alive() if self._detection_thread else False,
            "cached_results": len(self.results_cache),
            "sampling_interval": self.sampling_interval,
            "temporal_window": self.temporal_window
        }


# Singleton instance - globally accessible
instant_detection_sampler = InstantDetectionSampler()


# Hook functions for easy access from other modules
def get_latest_instant_results(camera_id: str) -> Optional[Dict]:
    """
    Hook function to get latest instant detection results for a camera.
    
    This is the recommended way for other modules to access instant results.
    Results stay in memory until replaced by next iteration.
    
    Args:
        camera_id: Camera device ID
        
    Returns:
        Latest detection results dict or None if not available
        
    Example:
        ```python
        from src.services.instant_detection import get_latest_instant_results
        
        # In your hook/module:
        results = get_latest_instant_results("usb_camera_0")
        if results:
            for person in results["person_objects"]:
                age = person['age_gender']['age_range']
                gender = person['age_gender']['gender']
                print(f"Detected: {gender}, {age}")
        ```
    """
    return instant_detection_sampler.get_cached_result(camera_id)


def get_all_instant_results() -> Dict[str, Dict]:
    """
    Hook function to get latest instant detection results for all cameras.
    
    Returns:
        Dict mapping camera_id to latest results
        
    Example:
        ```python
        from src.services.instant_detection import get_all_instant_results
        
        # Monitor all cameras:
        all_results = get_all_instant_results()
        for camera_id, results in all_results.items():
            people_count = len(results['person_objects'])
            print(f"{camera_id}: {people_count} people detected")
        ```
    """
    return instant_detection_sampler.get_all_cached_results()


def is_instant_detection_running(camera_id: Optional[str] = None) -> bool:
    """
    Check if instant detection is currently running.
    
    Args:
        camera_id: Specific camera to check, or None to check if system is running
        
    Returns:
        True if instant detection is active
    """
    if camera_id:
        return camera_id in instant_detection_sampler.results_cache
    return instant_detection_sampler._running
