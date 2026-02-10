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
        media_service_url: str = "http://localhost:8000",
        sampling_interval: int = 5,
        temporal_window: float = 1.0
    ):
        self._detection_thread = None
        self._running = False
        self._current_camera_id: Optional[str] = None  # Track which camera is being sampled
        self._current_capture = None  # Track current VideoCapture object
        self.vision_service_url = vision_service_url
        self.vmeta_service_url = vmeta_service_url
        self.orchestrator_service_url = orchestrator_service_url
        self.media_service_url = media_service_url
        self.sampling_interval = sampling_interval
        self.temporal_window = temporal_window
        
        # Results cache (in-memory only)
        self.results_cache: Dict[str, Dict] = {}
        
        # Webhook configuration for pushing results to media service triggers
        self.webhook_enabled = False
        self.webhook_url: Optional[str] = None
        
        logger.info("✅ Instant detection sampler initialized (Vision + VMeta APIs)")
    
    def start_sampling(self, camera_id: str, camera_capture):
        """
        Start parallel frame sampling thread (non-blocking)
        
        Args:
            camera_id: Unique camera identifier
            camera_capture: Legacy parameter (can be None) - we now use queue workers
        """
        # Check if we need to restart due to camera change
        camera_changed = self._current_camera_id != camera_id
        
        if camera_changed and self._running:
            logger.info(
                f"🔄 Camera changed (was: {self._current_camera_id}, now: {camera_id}) - "
                f"restarting instant detection"
            )
            self.stop_sampling()
        
        # Check if thread is still running (even if _running flag says otherwise)
        if self._running and self._detection_thread and self._detection_thread.is_alive():
            logger.warning(f"Instant detection already running for camera {camera_id}")
            return
        
        # If thread exists but is not alive, ensure clean state
        if self._detection_thread and not self._detection_thread.is_alive():
            logger.info(f"🔄 Cleaning up previous thread state for camera {camera_id}")
            self._running = False
            self._detection_thread = None
        
        # Store current camera (we now use queue workers, not capture object)
        self._current_camera_id = camera_id
        self._current_capture = None  # Not used anymore
        
        self._running = True
        self._detection_thread = threading.Thread(
            target=self._sample_loop,
            args=(camera_id, None),  # Pass None for capture - use queue worker
            daemon=True,
            name=f"instant-detection-{camera_id}"
        )
        self._detection_thread.start()
        logger.info(f"🚀 Instant detection sampler started for camera {camera_id} (using queue worker)")
    
    def stop_sampling(self):
        """Stop the sampling thread"""
        self._running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=2)
        
        # Clear camera tracking on stop
        self._current_camera_id = None
        self._current_capture = None
        
        logger.info("🛑 Instant detection sampler stopped")
    
    def _sample_loop(self, camera_id: str, camera_capture):
        """
        Main sampling loop - runs every N seconds using queue worker frames.
        Now submits frames to Celery for non-blocking processing.
        """
        consecutive_failures = 0
        max_failures = 3  # Stop after 3 consecutive failures
        
        while self._running:
            try:
                start_time = time.time()
                
                # Check if queue worker is still active
                # Import here to avoid circular dependency
                import asyncio
                from src.services.camera_service_queue import get_camera_service as get_queue_service
                
                # Run async check in a new event loop (we're in a thread)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    queue_service = get_queue_service()
                    worker = loop.run_until_complete(queue_service.get_camera_stream(camera_id))
                    
                    if not worker or worker.status.value != 'connected':
                        logger.warning(f"⚠️ Queue worker not connected for {camera_id}, stopping instant detection")
                        self._running = False
                        break
                finally:
                    loop.close()
                
                # Capture 3 frames from queue worker
                frames = self._capture_3_frames_from_queue(camera_id)
                
                if len(frames) == 3:
                    # Submit to Celery for background processing (non-blocking)
                    self._submit_to_celery(camera_id, frames)
                    
                    logger.info(
                        f"📤 [INSTANT] Submitted {camera_id} to Celery for processing "
                        f"({len(frames)} frames)"
                    )
                    consecutive_failures = 0  # Reset failure counter on success
                    
                elif len(frames) == 0:
                    # No frames captured at all - likely camera disconnected or stopped
                    consecutive_failures += 1
                    logger.warning(
                        f"⚠️ Failed to capture any frames for {camera_id} "
                        f"(failure {consecutive_failures}/{max_failures})"
                    )
                    
                    if consecutive_failures >= max_failures:
                        logger.error(
                            f"❌ Too many consecutive failures ({consecutive_failures}), "
                            f"stopping instant detection for {camera_id}"
                        )
                        self._running = False
                        break
                else:
                    # Partial frames captured
                    consecutive_failures += 1
                    logger.warning(
                        f"⚠️ Only captured {len(frames)}/3 frames for {camera_id} "
                        f"(failure {consecutive_failures}/{max_failures})"
                    )
                    
                    if consecutive_failures >= max_failures:
                        logger.error(
                            f"❌ Too many consecutive failures ({consecutive_failures}), "
                            f"stopping instant detection for {camera_id}"
                        )
                        self._running = False
                        break
                
                # Wait for next iteration (accounting for processing time)
                elapsed = time.time() - start_time
                sleep_time = max(0, self.sampling_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(
                    f"❌ Instant detection error for {camera_id}: {e} "
                    f"(failure {consecutive_failures}/{max_failures})", 
                    exc_info=True
                )
                
                if consecutive_failures >= max_failures:
                    logger.error(
                        f"❌ Too many consecutive errors ({consecutive_failures}), "
                        f"stopping instant detection for {camera_id}"
                    )
                    self._running = False
                    break
                
                time.sleep(self.sampling_interval)
        
        logger.info(f"🛑 Instant detection sample loop exited for {camera_id}")
    
    def _capture_3_frames_from_queue(self, camera_id: str) -> List[Dict]:
        """
        Capture 3 frames from queue worker buffer (non-blocking, no contention).
        
        Temporal spacing:
        - Frame 0: t=0.0s
        - Frame 1: t=0.5s (temporal_window / 2)
        - Frame 2: t=1.0s (temporal_window)
        
        Total window: 1 second (captures motion context)
        
        Args:
            camera_id: Camera device ID
        
        Returns:
            List of frame dictionaries with frame, timestamp, and index
        """
        frames = []
        
        try:
            import asyncio
            from src.services.camera_service_queue import get_camera_service as get_queue_service
            
            frame_spacing = self.temporal_window / 2  # 0.5s for 1.0s window
            
            for i in range(3):
                # Read frame from queue worker (non-blocking)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    queue_service = get_queue_service()
                    frame = loop.run_until_complete(queue_service.get_latest_frame(camera_id))
                finally:
                    loop.close()
                
                if frame is not None:
                    logger.debug(f"📸 [INSTANT-DETECT] Frame {i} from queue worker for {camera_id}")
                    frames.append({
                        "frame": frame.copy(),
                        "timestamp": i * frame_spacing,
                        "frame_index": i
                    })
                    
                    # Wait between frames (except after last frame)
                    if i < 2:
                        time.sleep(frame_spacing)
                else:
                    logger.warning(f"Failed to capture frame {i} from queue worker")
                    break
                    
        except Exception as e:
            logger.error(f"Error capturing frames from queue worker: {e}")
        
        return frames
    
    def _capture_3_frames_shared(self, camera_id: str, cap) -> List[Dict]:
        """
        Capture 3 frames from SHARED camera stream (no new VideoCapture).
        
        Temporal spacing:
        - Frame 0: t=0.0s
        - Frame 1: t=0.5s (temporal_window / 2)
        - Frame 2: t=1.0s (temporal_window)
        
        Total window: 1 second (captures motion context)
        
        Args:
            camera_id: Camera device ID (needed to access frame buffer for RTSP)
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
                # ✅ READ FROM FRAME BUFFER if available (RTSP cameras)
                from src.services.camera_detection import camera_service
                
                if camera_id in camera_service.frame_buffers:
                    ret, frame = camera_service.frame_buffers[camera_id]
                    logger.debug(f"📸 [INSTANT-DETECT] Frame {i} from BUFFER for {camera_id}")
                else:
                    # USB cameras read directly
                    ret, frame = cap.read()
                    logger.debug(f"📸 [INSTANT-DETECT] Frame {i} from DIRECT READ for {camera_id}")
                
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
        # NOTE: Do NOT release cap here - it's a SHARED capture from recording loop
        # The recording loop owns and will release the capture when recording ends
        
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
        
        logger.info(f"🚀🚀🚀 [_process_3_frames] STARTING instant detection for camera {camera_id} with {len(frames)} frames")
        
        # Generate session UUID for this instant detection iteration
        session_uuid = str(uuid.uuid4())
        
        # Step 1: Send frames to Vision Service for face detection
        all_face_detections = []
        frame_index_map = {}  # Map Vision Service frame_index to our frames array position
        
        async with aiohttp.ClientSession() as session:
            for array_position, frame_data in enumerate(frames):
                frame = frame_data["frame"]
                frame_index = frame_data["frame_index"]
                timestamp = frame_data["timestamp"]
                
                # Store mapping from Vision's frame_index to our array position
                frame_index_map[frame_index] = array_position
                
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
            all_face_detections,
            camera_id
        )
        
        # Step 3: Age/gender detection via VMeta Service
        # Only process ONE face per person (the best quality one)
        logger.info(f"🧬 Step 3: Starting age/gender detection for {len(person_objects)} people")
        logger.info(f"📊 DEBUG: frames array length = {len(frames)}")
        
        async with aiohttp.ClientSession() as session:
            for person in person_objects:
                # Get faces for this person
                person_faces = person.get("faces", [])
                
                if not person_faces:
                    logger.warning(f"⚠️ Person has no faces, using default age/gender")
                    person["age_gender"] = self._default_age_gender()
                    continue
                
                # Find highest confidence face for this person
                best_face = max(
                    person_faces,
                    key=lambda f: f.get("confidence", 0.0)
                )
                
                # Get the frame for this face
                frame_index_from_vision = best_face.get("frame_index", 0)
                array_position = frame_index_map.get(frame_index_from_vision, 0)
                
                logger.info(f"📊 DEBUG: Processing person with frame_index_from_vision={frame_index_from_vision}, mapped to array_position={array_position}, frames length={len(frames)}")
                
                if array_position < len(frames):
                    # Get age/gender from VMeta Service (DeepFace models)
                    logger.info(f"🎯 Calling VMeta for person with face at array position {array_position} (original frame {frame_index_from_vision})")
                    age_gender = await self._get_age_gender_via_vmeta_service(
                        session,
                        frames[array_position]["frame"],
                        best_face["bbox"]
                    )
                    person["age_gender"] = age_gender
                else:
                    logger.error(f"❌ SKIP VMeta: array_position {array_position} >= len(frames) {len(frames)}")
                    person["age_gender"] = self._default_age_gender()
        
        processing_time = time.time() - start_time
        
        # Step 4: Calculate demographics aggregation (same format as MVR counter)
        demographics = self._calculate_demographics(person_objects)
        
        logger.info(f"✅ Instant detection complete: {len(person_objects)} people, {total_faces} faces, demographics: {demographics}")
        
        return {
            "success": True,
            "camera_id": camera_id,
            "timestamp": datetime.now().isoformat(),
            "temporal_window_seconds": self.temporal_window,
            "frames_processed": len(frames),
            "total_faces_detected": total_faces,
            "people_count": len(person_objects),  # FIXED: Use people_count for trigger evaluation
            "people_detected": len(person_objects),  # Keep for backward compatibility
            "demographics": demographics,  # NEW: Gender/age breakdown
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
            
            logger.info(f"🔍 Calling VMeta age/gender endpoint: {url}")
            
            # Add 2-second timeout to prevent blocking
            timeout = aiohttp.ClientTimeout(total=2.0)
            async with session.post(url, data=data, timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(f"✅ VMeta age/gender response: {result}")
                    logger.info(f"📊 Response details - age_min: {result.get('age_min')}, age_max: {result.get('age_max')}, gender: {result.get('gender')}, gender_conf: {result.get('gender_confidence')}")
                    
                    # Format age range from min/max
                    age_min = result.get("age_min", 0)
                    age_max = result.get("age_max", 100)
                    age_range = f"({age_min}-{age_max})"
                    
                    age_gender_result = {
                        "age_range": age_range,
                        "age_confidence": result.get("age_confidence", 0.0),
                        "gender": result.get("gender", "unknown"),
                        "gender_confidence": result.get("gender_confidence", 0.0)
                    }
                    
                    logger.info(f"📊 Formatted age/gender: {age_gender_result}")
                    
                    return age_gender_result
                else:
                    response_text = await response.text()
                    logger.error(f"❌ VMeta Service age/gender error: {response.status} - {response_text}")
                    return self._default_age_gender()
        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ VMeta age/gender timeout (>2s) - returning unknown")
            return self._default_age_gender()
        except Exception as e:
            logger.error(f"Error getting age/gender from VMeta: {e}")
            return self._default_age_gender()
    
    def _calculate_demographics(self, person_objects: List[Dict]) -> Dict:
        """
        Calculate demographics aggregation from person objects.
        
        Returns same format as MVR people counter:
        - total_male, total_female, percent_male, percent_female
        - total_young (<21), total_adult (>=21), percent_young, percent_adult
        
        Uses the exact same method as continuous pipeline (VMeta's DeepFace results).
        """
        total_people = len(person_objects)
        
        if total_people == 0:
            return {
                "total_male": 0,
                "total_female": 0,
                "total_unknown_gender": 0,
                "percent_male": 0.0,
                "percent_female": 0.0,
                "percent_unknown_gender": 0.0,
                "total_young": 0,
                "total_adult": 0,
                "total_unknown_age": 0,
                "percent_young": 0.0,
                "percent_adult": 0.0,
                "percent_unknown_age": 0.0
            }
        
        # Count by gender
        male_count = 0
        female_count = 0
        unknown_gender_count = 0
        
        # Count by age (young = <21, adult = >=21)
        young_count = 0
        adult_count = 0
        unknown_age_count = 0
        
        for person in person_objects:
            age_gender = person.get("age_gender", {})
            
            # Count gender
            gender = age_gender.get("gender", "unknown").lower()
            if gender == "male":
                male_count += 1
            elif gender == "female":
                female_count += 1
            else:
                unknown_gender_count += 1
            
            # Count age (parse age_range like "(25-35)")
            age_range = age_gender.get("age_range", "(0-100)")
            try:
                # Extract min age from range "(25-35)" -> 25
                age_min_str = age_range.strip("()").split("-")[0]
                age_min = int(age_min_str)
                
                if age_min < 21:
                    young_count += 1
                else:
                    adult_count += 1
            except (ValueError, IndexError):
                unknown_age_count += 1
        
        # Calculate percentages
        percent_male = round((male_count / total_people) * 100, 1)
        percent_female = round((female_count / total_people) * 100, 1)
        percent_unknown_gender = round((unknown_gender_count / total_people) * 100, 1)
        
        percent_young = round((young_count / total_people) * 100, 1)
        percent_adult = round((adult_count / total_people) * 100, 1)
        percent_unknown_age = round((unknown_age_count / total_people) * 100, 1)
        
        return {
            "total_male": male_count,
            "total_female": female_count,
            "total_unknown_gender": unknown_gender_count,
            "percent_male": percent_male,
            "percent_female": percent_female,
            "percent_unknown_gender": percent_unknown_gender,
            "total_young": young_count,
            "total_adult": adult_count,
            "total_unknown_age": unknown_age_count,
            "percent_young": percent_young,
            "percent_adult": percent_adult,
            "percent_unknown_age": percent_unknown_age
        }
    
    async def _create_person_objects_via_vision_service(
        self,
        session_uuid: str,
        face_detections: List[Dict],
        camera_id: str = None
    ) -> List[Dict]:
        """
        Group faces into person objects using Orchestrator's spatial/IoU grouping.
        
        This uses the same proven grouping algorithm as Enhanced Logic V2 (person-objects pipeline).
        Groups faces across multiple frames based on spatial overlap and IoU.
        """
        if not face_detections:
            return []
        
        # Get camera-specific tolerance setting
        tolerance_percent = await self._get_camera_tolerance(camera_id) if camera_id else 20.0
        
        try:
            # Use Orchestrator Service (same as Enhanced Logic V2)
            orchestrator_url = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8002")
            
            async with aiohttp.ClientSession() as session:
                url = f"{orchestrator_url}/api/v1/person-objects/from-faces"
                
                payload = {
                    "session_uuid": session_uuid,
                    "face_detections": face_detections,
                    "tolerance_percent": tolerance_percent,
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
    
    async def _get_camera_tolerance(self, camera_id: str) -> float:
        """Get camera-specific tolerance_percent setting from database."""
        try:
            from src.database import SessionLocal
            from src.models.camera_settings import CameraSettings
            
            db = SessionLocal()
            try:
                # Get camera settings for this camera (use first user's settings as default)
                settings = db.query(CameraSettings).filter(
                    CameraSettings.camera_device_id == camera_id
                ).first()
                
                if settings and hasattr(settings, 'tolerance_percent'):
                    tolerance = float(settings.tolerance_percent)
                    logger.debug(f"Using camera {camera_id} tolerance: {tolerance}%")
                    return tolerance
                else:
                    logger.debug(f"No settings found for camera {camera_id}, using default 20%")
                    return 20.0
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error fetching camera tolerance for {camera_id}: {e}, using default 20%")
            return 20.0
    
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
    
    def _submit_to_celery(self, camera_id: str, frames: List[Dict]):
        """
        Submit frames to Celery for background processing (non-blocking).
        
        This prevents instant detection from blocking the main FastAPI service.
        Celery workers process frames independently and publish results to Redis.
        
        Args:
            camera_id: Camera identifier
            frames: List of 3 frame dictionaries
        """
        result = None
        celery_success = False
        
        try:
            from src.tasks.instant_detection_tasks import process_instant_detection
            import base64
            
            # Convert frames to base64 for JSON serialization
            frames_data = []
            for frame_dict in frames:
                frame = frame_dict["frame"]
                # Encode frame as JPEG then base64
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                frames_data.append(frame_b64)
            
            # Submit task (returns immediately, doesn't block)
            task = process_instant_detection.delay(
                camera_id=camera_id,
                frames_data=frames_data,
                timestamp=datetime.utcnow().isoformat()
            )
            
            logger.debug(f"✅ [CELERY] Task submitted: {task.id} for {camera_id}")
            celery_success = True
            
        except (ImportError, Exception) as e:
            # 🚀 CRITICAL: Fallback MUST be non-blocking to prevent camera worker freeze
            # Run synchronous processing in separate thread
            logger.warning(f"⚠️ [CELERY] Not available ({type(e).__name__}: {e}) - using threaded fallback")
            
            def _process_in_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(self._process_3_frames(camera_id, frames))
                    
                    # Add timestamp to result
                    from datetime import datetime
                    result["timestamp"] = datetime.utcnow().isoformat() + 'Z'
                    
                    # Cache in memory (instance cache)
                    self._cache_result(camera_id, result)
                    
                    # 🔥 CRITICAL: Also cache in Redis for cross-process access
                    try:
                        import redis
                        import json
                        r = redis.Redis(host='localhost', port=6379, decode_responses=False)
                        cache_key = f"instant_detection:{camera_id}"
                        r.setex(cache_key, 300, json.dumps(result))  # 5 min TTL
                        logger.info(f"✅ [THREAD] Cached in both memory and Redis for {camera_id} at {result['timestamp']}")
                    except Exception as redis_error:
                        logger.warning(f"⚠️ [THREAD] Redis cache failed, using memory only: {redis_error}")
                    
                    loop.close()
                    
                    # Push to webhook and Redis pub/sub from thread
                    if result and self.webhook_enabled and self.webhook_url:
                        self._push_to_webhook_sync(camera_id, result)
                    if result:
                        self._publish_to_redis_sync(camera_id, result)
                        # Evaluate triggers after publishing to Redis
                        self._evaluate_triggers_sync(camera_id, result)
                        
                except Exception as sync_error:
                    logger.error(f"❌ [THREAD] Fallback processing failed: {sync_error}", exc_info=True)
            
            # Start processing in background thread (non-blocking)
            import threading
            thread = threading.Thread(target=_process_in_thread, daemon=True)
            thread.start()
            logger.debug(f"✅ [THREAD] Started background processing for {camera_id}")
            return  # Return immediately, don't block
        
        # Push to webhook if enabled (non-blocking) - only if we have result from sync processing
        if result and self.webhook_enabled and self.webhook_url:
            logger.info(f"📤 Pushing to webhook: {self.webhook_url}")
            try:
                # Use threading instead of asyncio since we're in a sync context
                import threading
                thread = threading.Thread(
                    target=self._push_to_webhook_sync,
                    args=(camera_id, result),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                logger.error(f"❌ Failed to start webhook thread: {e}")
        
        # Publish to Redis Pub/Sub for real-time subscribers (non-blocking) - only if we have result
        if result:
            try:
                import threading
                thread = threading.Thread(
                    target=self._publish_to_redis_sync,
                    args=(camera_id, result),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                logger.error(f"❌ Failed to start Redis publish thread: {e}")
        
        # Evaluate triggers after detection (non-blocking)
        if result:
            try:
                import threading
                thread = threading.Thread(
                    target=self._evaluate_triggers_sync,
                    args=(camera_id, result),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                logger.error(f"❌ Failed to start trigger evaluation thread: {e}")
    
    def _push_to_webhook_sync(self, camera_id: str, result: Dict):
        """
        Push instant detection results to webhook endpoint (synchronous version for threading).
        
        This runs in a separate thread to avoid blocking the detection loop.
        Short timeout (2s) ensures detection continues even if webhook is slow/down.
        
        Args:
            camera_id: Camera identifier
            result: Detection result dictionary
        """
        import requests
        
        if not self.webhook_url:
            return
        
        try:
            # Extract demographic summary
            demographics = result.get("demographics", {})
            people_count = result.get("people_count", 0)
            
            payload = {
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": people_count,
                "demographics": demographics,
                "metadata": {
                    "processing_time": result.get("processing_time_seconds", 0),
                    "total_faces": result.get("total_faces_detected", 0)
                }
            }
            
            logger.info(f"📤 Sending webhook POST to {self.webhook_url}")
            logger.info(f"   Payload: people_count={people_count}, demographics={demographics}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=2
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Webhook SUCCESS: {camera_id} - {response.json()}")
            else:
                logger.warning(
                    f"⚠️ Webhook returned {response.status_code}: {camera_id} - {response.text}"
                )
        
        except requests.Timeout:
            logger.warning(f"⚠️ Webhook timeout (2s): {camera_id}")
        except Exception as e:
            logger.error(f"❌ Webhook push error: {e}", exc_info=True)
    
    def _publish_to_redis_sync(self, camera_id: str, result: Dict):
        """
        Publish instant detection results to Redis Pub/Sub (synchronous version for threading).
        
        This runs in a separate thread to avoid blocking the detection loop.
        Publishes to 'instant-detection' channel for all subscribers (triggers, UI, analytics).
        
        Args:
            camera_id: Camera identifier
            result: Detection result dictionary
        """
        try:
            import redis
            import os
            
            # Get Redis connection from environment or use default
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_db = int(os.getenv("REDIS_DB", 0))
            
            # Create Redis client
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            
            # Extract demographic summary
            demographics = result.get("demographics", {})
            people_count = result.get("people_count", 0)
            
            # Prepare payload
            import json
            payload = json.dumps({
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": people_count,
                "demographics": demographics,
                "metadata": {
                    "processing_time": result.get("processing_time_seconds", 0),
                    "total_faces": result.get("total_faces_detected", 0)
                }
            })
            
            # Publish to Redis channel
            subscriber_count = redis_client.publish("instant-detection", payload)
            
            logger.info(
                f"✅ Redis Pub/Sub: {camera_id} → {subscriber_count} subscribers "
                f"(people={people_count})"
            )
            
            redis_client.close()
            
        except redis.ConnectionError:
            logger.warning(f"⚠️ Redis connection failed (instant detection pub/sub)")
        except Exception as e:
            logger.error(f"❌ Redis publish error: {e}")
    
    def _evaluate_triggers_sync(self, camera_id: str, result: Dict):
        """
        Evaluate triggers against instant detection results (synchronous version for threading).
        
        Calls Media Service trigger evaluation endpoint to check if any active triggers
        should execute actions based on the demographic data.
        
        Args:
            camera_id: Camera identifier
            result: Detection result dictionary with demographics
        """
        try:
            import requests
            
            # Extract demographic data
            demographics = result.get("demographics", {})
            people_count = result.get("people_count", 0)
            
            # Prepare payload in CounterDataRequest format expected by trigger evaluation
            # Convert instant detection format to counter data format
            gender_distribution = {}
            if demographics.get("total_male", 0) > 0:
                gender_distribution["male"] = demographics["total_male"]
            if demographics.get("total_female", 0) > 0:
                gender_distribution["female"] = demographics["total_female"]
            
            # Map age demographics to age distribution (simplified mapping)
            age_distribution = {}
            young = demographics.get("total_young", 0)
            adult = demographics.get("total_adult", 0)
            if young > 0:
                age_distribution["0-18"] = young
            if adult > 0:
                age_distribution["19-30"] = int(adult * 0.5)  # Split adults across age ranges
                age_distribution["31-50"] = int(adult * 0.3)
                age_distribution["51+"] = int(adult * 0.2)
            
            payload = {
                "camera_device_id": camera_id,
                "total_count": people_count,
                "gender_distribution": gender_distribution if gender_distribution else None,
                "age_distribution": age_distribution if age_distribution else None,
                "timestamp": result.get("timestamp", datetime.utcnow().isoformat())
            }
            
            trigger_url = f"{self.media_service_url}/api/v1/triggers/evaluate"
            
            logger.info(
                f"🎯 Evaluating triggers for {camera_id}: "
                f"people_count={people_count}, demographics={demographics}"
            )
            
            response = requests.post(
                trigger_url,
                json=payload,
                timeout=3
            )
            
            if response.status_code == 200:
                result_data = response.json()
                triggered = result_data.get("triggered_actions", [])
                if triggered:
                    logger.info(
                        f"✅ Triggers evaluated: {len(triggered)} action(s) triggered for {camera_id}"
                    )
                else:
                    logger.debug(f"✅ Triggers evaluated: No actions triggered for {camera_id}")
            else:
                logger.warning(
                    f"⚠️ Trigger evaluation returned {response.status_code}: {response.text}"
                )
        
        except requests.Timeout:
            logger.warning(f"⚠️ Trigger evaluation timeout (3s): {camera_id}")
        except Exception as e:
            logger.error(f"❌ Trigger evaluation error: {e}", exc_info=True)
    
    def _process_frames_sync(self, camera_id: str, frames_data: List[str]) -> Optional[Dict]:
        """
        Synchronous version of frame processing for Celery workers.
        
        This method is called by Celery workers (not the main FastAPI service).
        It performs the same processing as _process_3_frames but synchronously.
        
        Args:
            camera_id: Camera identifier
            frames_data: List of 3 base64-encoded JPEG frames
        
        Returns:
            Detection result dictionary or None if processing fails
        """
        try:
            import base64
            import numpy as np
            
            # Decode base64 frames back to numpy arrays
            frames = []
            for frame_b64 in frames_data:
                # Decode base64 to bytes
                frame_bytes = base64.b64decode(frame_b64)
                # Convert to numpy array
                nparr = np.frombuffer(frame_bytes, np.uint8)
                # Decode JPEG to image
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                frames.append({"frame": frame})
            
            if len(frames) != 3:
                logger.error(f"❌ [CELERY] Expected 3 frames, got {len(frames)}")
                return None
            
            # Use existing async processing but wrap in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._process_3_frames(camera_id, frames))
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ [CELERY] Sync processing failed: {e}", exc_info=True)
            return None
    
    async def _push_to_webhook(self, camera_id: str, result: Dict):
        """
        Push instant detection results to webhook endpoint (media service triggers).
        
        This is a fire-and-forget async operation that doesn't block detection.
        Short timeout (2s) ensures detection continues even if webhook is slow/down.
        
        Args:
            camera_id: Camera identifier
            result: Detection result dictionary
        """
        if not self.webhook_url:
            return
        
        try:
            # Extract demographic summary
            demographics = result.get("demographics", {})
            people_count = result.get("people_count", 0)
            
            payload = {
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": people_count,
                "demographics": demographics,
                "metadata": {
                    "processing_time": result.get("processing_time_seconds", 0),
                    "total_faces": result.get("total_faces_detected", 0)
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        logger.debug(f"✅ Pushed instant detection to webhook: {camera_id}")
                    else:
                        logger.warning(
                            f"⚠️ Webhook returned {response.status}: {camera_id}"
                        )
        
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Webhook timeout (2s): {camera_id}")
        except Exception as e:
            logger.error(f"❌ Webhook push error: {e}")
    
    def configure_webhook(self, url: str, enabled: bool = True):
        """
        Configure webhook for pushing instant detection results.
        
        Args:
            url: Webhook endpoint URL (typically media service trigger endpoint)
            enabled: Whether webhook push is enabled
        """
        self.webhook_url = url
        self.webhook_enabled = enabled
        logger.info(f"✅ Webhook configured: {url} (enabled={enabled})")
    
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
