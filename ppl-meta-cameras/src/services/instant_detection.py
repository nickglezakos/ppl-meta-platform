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
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional
from datetime import datetime
import logging

import cv2
import numpy as np
import aiohttp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker — prevents cascading failures to downstream services
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """
    Three-state circuit breaker for outbound service calls.

    States:
      CLOSED    — normal operation, requests pass through
      OPEN      — service is down, requests are rejected immediately
      HALF_OPEN — probing with a single request to check recovery
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, service_name: str, failure_threshold: int = 3,
                 cooldown_seconds: float = 30.0):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and self._last_failure_time is not None:
                if (time.time() - self._last_failure_time) >= self.cooldown_seconds:
                    self._state = self.HALF_OPEN
                    logger.info(
                        f"🔄 Circuit breaker [{self.service_name}]: "
                        f"OPEN → HALF_OPEN (cooldown elapsed, probing...)"
                    )
            return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current_state = self.state
        if current_state == self.CLOSED:
            return True
        if current_state == self.HALF_OPEN:
            return True  # Allow one probe request
        return False  # OPEN — reject

    def record_success(self):
        with self._lock:
            if self._state == self.HALF_OPEN:
                logger.info(
                    f"✅ Circuit breaker [{self.service_name}]: "
                    f"HALF_OPEN → CLOSED (probe succeeded)"
                )
            self._state = self.CLOSED
            self._failure_count = 0

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == self.HALF_OPEN:
                self._state = self.OPEN
                logger.warning(
                    f"⚡ Circuit breaker [{self.service_name}]: "
                    f"HALF_OPEN → OPEN (probe failed, cooling down {self.cooldown_seconds}s)"
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = self.OPEN
                logger.warning(
                    f"⚡ Circuit breaker [{self.service_name}]: "
                    f"CLOSED → OPEN ({self._failure_count} consecutive failures, "
                    f"cooling down {self.cooldown_seconds}s)"
                )


# ---------------------------------------------------------------------------
# Per-camera sampler state — one instance per active camera
# ---------------------------------------------------------------------------

@dataclass
class CameraSamplerState:
    """State for a single camera's instant detection loop."""
    camera_id: str
    thread: Optional[threading.Thread] = None
    running: bool = False
    cycle_counter: int = 0
    storage_multiple: int = 1
    session_duration_minutes: int = 0
    session_started_at: Optional[datetime] = None
    session_uuid: Optional[str] = None
    auth_token: Optional[str] = None
    stagger_offset: float = 0.0


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
        self.vision_service_url = vision_service_url
        self.vmeta_service_url = vmeta_service_url
        self.orchestrator_service_url = orchestrator_service_url
        self.media_service_url = media_service_url
        self.sampling_interval = sampling_interval
        self.temporal_window = temporal_window
        
        # Multi-camera registry — replaces single-camera state
        self._samplers: Dict[str, CameraSamplerState] = {}
        self._lock = threading.RLock()

        # Results cache (in-memory) — already per-camera keyed
        self.results_cache: Dict[str, Dict] = {}
        self._cache_lock = threading.Lock()
        
        # Webhook configuration for pushing results to media service triggers
        self.webhook_enabled = False
        self.webhook_url: Optional[str] = None

        # Multi-camera feature flag (backward compat)
        self._multi_camera_enabled = os.getenv(
            "INSTANT_DETECTION_MULTI_CAMERA_ENABLED", "true"
        ).lower() == "true"

        # --- Concurrency controls (shared across all cameras) ---
        vision_concurrency = int(os.getenv("INSTANT_DETECTION_VISION_CONCURRENCY", "2"))
        vmeta_concurrency = int(os.getenv("INSTANT_DETECTION_VMETA_CONCURRENCY", "3"))
        orchestrator_concurrency = int(os.getenv("INSTANT_DETECTION_ORCHESTRATOR_CONCURRENCY", "2"))
        self._vision_semaphore = threading.Semaphore(vision_concurrency)
        self._vmeta_semaphore = threading.Semaphore(vmeta_concurrency)
        self._orchestrator_semaphore = threading.Semaphore(orchestrator_concurrency)

        # --- Circuit breakers (one per downstream service) ---
        cb_threshold = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
        cb_cooldown = float(os.getenv("CIRCUIT_BREAKER_COOLDOWN_SECONDS", "30"))
        self._vision_circuit = CircuitBreaker("Vision", cb_threshold, cb_cooldown)
        self._vmeta_circuit = CircuitBreaker("VMeta", cb_threshold, cb_cooldown)
        self._orchestrator_circuit = CircuitBreaker("Orchestrator", cb_threshold, cb_cooldown)
        
        logger.info(
            f"✅ Instant detection sampler initialized "
            f"(multi_camera={self._multi_camera_enabled}, "
            f"vision_concurrency={vision_concurrency}, "
            f"vmeta_concurrency={vmeta_concurrency})"
        )
    
    # ------------------------------------------------------------------
    # Backward-compatible properties for code that reads legacy fields
    # ------------------------------------------------------------------

    @property
    def _running(self) -> bool:
        """True if any camera is active."""
        with self._lock:
            return any(s.running for s in self._samplers.values())

    @property
    def _current_camera_id(self) -> Optional[str]:
        """Return the first active camera ID (backward compat)."""
        with self._lock:
            for cam_id, s in self._samplers.items():
                if s.running:
                    return cam_id
            return None

    @property
    def current_session_uuid(self) -> Optional[str]:
        """Return the first active session UUID (backward compat)."""
        with self._lock:
            for s in self._samplers.values():
                if s.running and s.session_uuid:
                    return s.session_uuid
            return None

    @current_session_uuid.setter
    def current_session_uuid(self, value):
        """Set session UUID on the first active camera (backward compat)."""
        with self._lock:
            for s in self._samplers.values():
                if s.running:
                    s.session_uuid = value
                    return

    # ------------------------------------------------------------------
    # Stagger offset calculation
    # ------------------------------------------------------------------

    def _calculate_stagger_offset(self, camera_id: str) -> float:
        """Calculate time offset for this camera to spread cycles over the interval."""
        with self._lock:
            active_count = len(self._samplers) + 1  # +1 for camera being added
        if active_count <= 1:
            return 0.0
        index = hash(camera_id) % active_count
        return (self.sampling_interval / active_count) * index

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_sampling(self, camera_id: str, camera_capture=None):
        """
        Start instant detection for a camera. Multiple cameras can run in parallel
        when INSTANT_DETECTION_MULTI_CAMERA_ENABLED=true.
        """
        with self._lock:
            # If multi-camera is disabled, stop any other running cameras first
            if not self._multi_camera_enabled:
                other_cameras = [
                    cid for cid, s in self._samplers.items()
                    if s.running and cid != camera_id
                ]
                for cid in other_cameras:
                    logger.info(
                        f"🔄 Multi-camera disabled — stopping {cid} "
                        f"before starting {camera_id}"
                    )
                    self._stop_camera_unlocked(cid)

            # Already running for this camera?
            if camera_id in self._samplers:
                existing = self._samplers[camera_id]
                if existing.running and existing.thread and existing.thread.is_alive():
                    logger.warning(
                        f"Instant detection already running for camera {camera_id}"
                    )
                    return
                # Thread died — clean up
                del self._samplers[camera_id]

            state = CameraSamplerState(
                camera_id=camera_id,
                stagger_offset=self._calculate_stagger_offset(camera_id),
            )
            state.running = True
            state.thread = threading.Thread(
                target=self._sample_loop,
                args=(state,),
                daemon=True,
                name=f"instant-detection-{camera_id}",
            )
            self._samplers[camera_id] = state
            state.thread.start()

        logger.info(
            f"🚀 Instant detection started for {camera_id} "
            f"(stagger={state.stagger_offset:.1f}s, "
            f"active_cameras={len(self._samplers)})"
        )

    def stop_sampling(self, camera_id: str = None):
        """Stop one camera (if camera_id given) or all cameras."""
        with self._lock:
            if camera_id:
                self._stop_camera_unlocked(camera_id)
            else:
                # Global stop
                for s in self._samplers.values():
                    s.running = False
                for s in list(self._samplers.values()):
                    if s.thread:
                        s.thread.join(timeout=2)
                self._samplers.clear()
        if camera_id:
            logger.info(f"🛑 Instant detection stopped for {camera_id}")
        else:
            logger.info("🛑 Instant detection stopped (all cameras)")

    def _stop_camera_unlocked(self, camera_id: str):
        """Stop a single camera. Must be called while holding self._lock."""
        state = self._samplers.get(camera_id)
        if state:
            state.running = False
            if state.thread:
                state.thread.join(timeout=2)
            del self._samplers[camera_id]

    def _sample_loop(self, state: CameraSamplerState):
        """
        Per-camera sampling loop — runs every N seconds using queue worker frames.
        Submits frames to Celery for non-blocking processing.
        """
        camera_id = state.camera_id

        # Stagger: delay start so cameras don't all fire at once
        if state.stagger_offset > 0:
            logger.info(
                f"⏱️ Camera {camera_id}: stagger delay {state.stagger_offset:.1f}s"
            )
            time.sleep(state.stagger_offset)

        # Ensure a tracking session exists for persistence.
        # The API endpoint may set session_uuid after start_sampling() returns,
        # but due to a race condition the thread may start before that happens.
        # Wait briefly for external config, then create a session if still missing.
        for _ in range(10):
            if state.session_uuid:
                break
            time.sleep(0.1)

        if not state.session_uuid:
            import requests as _requests
            import jwt as _jwt
            from datetime import timedelta
            new_uuid = str(uuid.uuid4())
            vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
            # Generate service-to-service auth token
            node_secret = os.getenv("NODE_SERVICE_SECRET", "default-secret-key-change-in-production")
            svc_token = _jwt.encode(
                {"sub": "cameras-service", "exp": datetime.utcnow() + timedelta(minutes=30)},
                node_secret,
                algorithm="HS256",
            )
            state.auth_token = svc_token
            headers = {
                "Authorization": f"Bearer {svc_token}",
                "Content-Type": "application/json",
            }
            try:
                resp = _requests.post(
                    f"{vmeta_url}/api/v1/instant-detection/create-session",
                    json={
                        "session_uuid": new_uuid,
                        "camera_id": camera_id,
                        "source_type": "instant_detection",
                        "user_id": "system",
                    },
                    headers=headers,
                    timeout=5,
                )
                if resp.status_code == 200:
                    state.session_uuid = new_uuid
                    state.session_started_at = datetime.utcnow()
                    logger.info(
                        f"✅ [SESSION] Auto-created tracking session for {camera_id}: {new_uuid[:8]}..."
                    )
                else:
                    logger.warning(
                        f"⚠️ [SESSION] VMeta create-session returned {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                logger.warning(
                    f"⚠️ [SESSION] Failed to auto-create tracking session for {camera_id}: {e}"
                )

        consecutive_failures = 0
        max_failures = 3
        
        while state.running:
            try:
                start_time = time.time()
                
                # Check if queue worker is still active
                import asyncio
                from src.services.camera_service_queue import get_camera_service as get_queue_service
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    queue_service = get_queue_service()
                    worker = loop.run_until_complete(queue_service.get_camera_stream(camera_id))
                    
                    if not worker or worker.status.value != 'connected':
                        logger.warning(f"⚠️ Queue worker not connected for {camera_id}, stopping instant detection")
                        state.running = False
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
                    consecutive_failures = 0
                    
                    # --- Persist to database (governed by storage_multiple) ---
                    state.cycle_counter += 1
                    if (
                        state.storage_multiple > 0
                        and state.session_uuid
                        and state.cycle_counter % state.storage_multiple == 0
                    ):
                        self._maybe_persist_cycle(state)
                    
                elif len(frames) == 0:
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
                        state.running = False
                        break
                else:
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
                        state.running = False
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
                    state.running = False
                    break
                
                time.sleep(self.sampling_interval)
        
        state.running = False
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

                    # Resolve person identity against vmeta MVR store
                    identity_match = await self._identify_face_via_vmeta_service(
                        session,
                        frames[array_position]["frame"],
                        best_face["bbox"]
                    )
                    if identity_match.get("matched") and identity_match.get("mvr_people_uuid"):
                        mvr_uuid = identity_match["mvr_people_uuid"]
                        person["mvr_person_uuid"] = mvr_uuid
                        best_face["mvr_person_uuid"] = mvr_uuid
                        logger.info(
                            f"✅ Instant identity resolved: camera={camera_id}, mvr={mvr_uuid}, "
                            f"similarity={identity_match.get('similarity_score', 0.0):.3f}"
                        )
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
            # Circuit breaker check
            if not self._vision_circuit.allow_request():
                logger.debug(f"Vision circuit OPEN — skipping detection for frame {frame_index}")
                return []

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
            
            self._vision_semaphore.acquire()
            try:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        self._vision_circuit.record_success()
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
                        self._vision_circuit.record_failure()
                        response_text = await response.text()
                        logger.error(f"Vision Service error: {response.status} - {response_text}")
                        return []
            finally:
                self._vision_semaphore.release()
        
        except Exception as e:
            self._vision_circuit.record_failure()
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
            # Circuit breaker check
            if not self._vmeta_circuit.allow_request():
                logger.debug("VMeta circuit OPEN — skipping age/gender detection")
                return self._default_age_gender()

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
            
            timeout = aiohttp.ClientTimeout(total=2.0)
            self._vmeta_semaphore.acquire()
            try:
                async with session.post(url, data=data, timeout=timeout) as response:
                    if response.status == 200:
                        self._vmeta_circuit.record_success()
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
                        self._vmeta_circuit.record_failure()
                        response_text = await response.text()
                        logger.error(f"❌ VMeta Service age/gender error: {response.status} - {response_text}")
                        return self._default_age_gender()
            finally:
                self._vmeta_semaphore.release()
        
        except asyncio.TimeoutError:
            self._vmeta_circuit.record_failure()
            logger.warning(f"⏱️ VMeta age/gender timeout (>2s) - returning unknown")
            return self._default_age_gender()
        except Exception as e:
            self._vmeta_circuit.record_failure()
            logger.error(f"Error getting age/gender from VMeta: {e}")
            return self._default_age_gender()

    async def _identify_face_via_vmeta_service(
        self,
        session: aiohttp.ClientSession,
        frame: np.ndarray,
        bbox: List[int]
    ) -> Dict[str, Any]:
        """
        Resolve a face crop to an MVR identity using vmeta similarity lookup.

        Returns:
            {"matched": bool, "mvr_people_uuid": str|None, "similarity_score": float}
        """
        _no_match = {"matched": False, "mvr_people_uuid": None, "similarity_score": 0.0}

        if not self._vmeta_circuit.allow_request():
            logger.debug("VMeta circuit OPEN – skipping identity lookup")
            return _no_match

        try:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            height, width = frame.shape[:2]

            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(x1 + 1, min(x2, width))
            y2 = max(y1 + 1, min(y2, height))

            face_roi = frame[y1:y2, x1:x2]
            if face_roi.size == 0:
                return _no_match

            ok, buffer = cv2.imencode('.jpg', face_roi)
            if not ok:
                return _no_match

            data = aiohttp.FormData()
            data.add_field(
                'file',
                buffer.tobytes(),
                filename='face.jpg',
                content_type='image/jpeg'
            )

            similarity_threshold = float(os.getenv("INSTANT_IDENTITY_SIMILARITY_THRESHOLD", "0.70"))
            dedupe_similarity_threshold = float(os.getenv("INSTANT_IDENTITY_DEDUPE_SIMILARITY_THRESHOLD", "0.55"))
            max_results = int(os.getenv("INSTANT_IDENTITY_MAX_RESULTS", "1"))
            url = (
                f"{self.vmeta_service_url}/api/v1/ml/identify-face"
                f"?similarity_threshold={similarity_threshold}"
                f"&dedupe_similarity_threshold={dedupe_similarity_threshold}"
                f"&enable_dedupe_reuse=true"
                f"&max_results={max_results}"
                f"&create_if_missing=true"
            )

            timeout = aiohttp.ClientTimeout(total=2.0)
            self._vmeta_semaphore.acquire()
            try:
                async with session.post(url, data=data, timeout=timeout) as response:
                    if response.status != 200:
                        self._vmeta_circuit.record_failure()
                        response_text = await response.text()
                        logger.debug(
                            f"Identity lookup failed ({response.status}): {response_text[:200]}"
                        )
                        return _no_match

                    self._vmeta_circuit.record_success()
                    result = await response.json()
                    return {
                        "matched": bool(result.get("matched")),
                        "mvr_people_uuid": result.get("mvr_people_uuid"),
                        "similarity_score": float(result.get("similarity_score", 0.0) or 0.0),
                    }
            finally:
                self._vmeta_semaphore.release()

        except asyncio.TimeoutError:
            self._vmeta_circuit.record_failure()
            logger.debug("Identity lookup timeout (>2s)")
            return _no_match
        except Exception as e:
            self._vmeta_circuit.record_failure()
            logger.debug(f"Identity lookup error: {e}")
            return _no_match
    
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

    def _extract_source_identity_uuids(self, person_objects: List[Dict]) -> List[str]:
        """Extract resolvable identity UUIDs for downstream ppl-match checks."""
        source_ids: List[str] = []

        def _append_if_uuid(raw_value: Any) -> None:
            if not raw_value:
                return
            try:
                normalized = str(uuid.UUID(str(raw_value)))
                if normalized not in source_ids:
                    source_ids.append(normalized)
            except Exception:
                return

        for person in person_objects:
            _append_if_uuid(person.get("mvr_person_uuid"))
            _append_if_uuid(person.get("person_id"))
            _append_if_uuid(person.get("person_object_uuid"))
            _append_if_uuid(person.get("individual_uuid"))

            for face in person.get("faces", []):
                _append_if_uuid(face.get("mvr_person_uuid"))
                _append_if_uuid(face.get("face_id"))
                _append_if_uuid(face.get("person_object_uuid"))
                _append_if_uuid(face.get("individual_uuid"))

        return source_ids
    
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

        if not self._orchestrator_circuit.allow_request():
            logger.debug("Orchestrator circuit OPEN – using local grouping fallback")
            return self._simple_spatial_grouping(face_detections)
        
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

                self._orchestrator_semaphore.acquire()
                try:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            self._orchestrator_circuit.record_success()
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
                                    person_uuid = group.get("person_uuid", str(uuid.uuid4()))
                                    person_objects.append({
                                        "person_id": person_uuid,
                                        "person_object_uuid": person_uuid,
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
                            self._orchestrator_circuit.record_failure()
                            response_text = await response.text()
                            logger.warning(
                                f"Orchestrator person grouping returned {response.status}: {response_text[:200]}"
                            )
                            # Fallback: simple spatial grouping locally
                            return self._simple_spatial_grouping(face_detections)
                finally:
                    self._orchestrator_semaphore.release()
        
        except asyncio.TimeoutError:
            self._orchestrator_circuit.record_failure()
            logger.warning("Orchestrator timeout - using simple local grouping")
            return self._simple_spatial_grouping(face_detections)
        except Exception as e:
            self._orchestrator_circuit.record_failure()
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
            person_uuid = str(uuid.uuid4())
            person_objects.append({
                "person_id": person_uuid,
                "person_object_uuid": person_uuid,
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
        person_objects = []
        for face in face_detections:
            person_uuid = str(uuid.uuid4())
            person_objects.append({
                "person_id": person_uuid,
                "person_object_uuid": person_uuid,
                "faces": [face],
                "face_count": 1,
                "avg_confidence": face.get("confidence", 0.0),
                "best_bbox": face.get("bbox", [0, 0, 0, 0])
            })
        return person_objects
    
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
        with self._cache_lock:
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
    
    # ------------------------------------------------------------------
    # Instant detection persistent storage helpers
    # ------------------------------------------------------------------

    def _maybe_persist_cycle(self, state: 'CameraSamplerState'):
        """Submit a persist task for the latest cached detection result."""
        camera_id = state.camera_id
        try:
            # Check if session needs rotation first
            if self._should_rotate_session(state):
                self._rotate_tracking_session(state)

            # Get the latest result from Redis cache
            import redis as _redis
            import json as _json

            r = _redis.Redis(host="localhost", port=6379, decode_responses=False)
            cached = r.get(f"instant_detection:{camera_id}")
            if not cached:
                return

            result = _json.loads(cached.decode("utf-8"))
            person_objects = result.get("person_objects") or []
            if not person_objects:
                return

            from src.tasks.instant_detection_tasks import persist_instant_detection_results

            persist_instant_detection_results.delay(
                camera_id=camera_id,
                session_uuid=state.session_uuid,
                cycle_timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
                person_objects=person_objects,
                demographics=result.get("demographics", {}),
                auth_token=state.auth_token or "",
            )
            logger.info(
                f"📦 [PERSIST] Queued storage for {camera_id} "
                f"(cycle {state.cycle_counter}, session {state.session_uuid[:8]}...)"
            )
        except Exception as e:
            logger.warning(f"⚠️ [PERSIST] Failed to submit persist task: {e}")

    def _should_rotate_session(self, state: 'CameraSamplerState') -> bool:
        """Check whether the current tracking session duration has been exceeded."""
        if state.session_duration_minutes <= 0:
            return False
        if state.session_started_at is None:
            return False
        elapsed = (datetime.utcnow() - state.session_started_at).total_seconds() / 60
        return elapsed >= state.session_duration_minutes

    def _rotate_tracking_session(self, state: 'CameraSamplerState'):
        """Complete the current session and start a new one."""
        import requests as _requests

        camera_id = state.camera_id
        vmeta_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        headers = {}
        if state.auth_token:
            headers["Authorization"] = f"Bearer {state.auth_token}"

        # Complete current session
        try:
            _requests.post(
                f"{vmeta_url}/api/v1/instant-detection/complete-session/{state.session_uuid}",
                headers=headers,
                timeout=5,
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to complete session on rotation: {e}")

        # Start new session
        new_uuid = str(uuid.uuid4())
        try:
            _requests.post(
                f"{vmeta_url}/api/v1/instant-detection/create-session",
                json={
                    "session_uuid": new_uuid,
                    "camera_id": camera_id,
                    "source_type": "instant_detection",
                    "user_id": "system",
                },
                headers={**headers, "Content-Type": "application/json"},
                timeout=5,
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to create new session on rotation: {e}")

        state.session_uuid = new_uuid
        state.session_started_at = datetime.utcnow()
        logger.info(
            f"🔄 [SESSION] Rotated tracking session for {camera_id} → {new_uuid[:8]}..."
        )

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
            person_objects = result.get("person_objects", [])
            source_mvr_uuids = self._extract_source_identity_uuids(person_objects)
            
            payload = {
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": people_count,
                "demographics": demographics,
                "source_mvr_uuids": source_mvr_uuids,
                "metadata": {
                    "source_mvr_uuids": source_mvr_uuids,
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
            person_objects = result.get("person_objects", [])
            source_mvr_uuids = self._extract_source_identity_uuids(person_objects)
            
            # Prepare payload
            import json
            payload = json.dumps({
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": people_count,
                "demographics": demographics,
                "source_mvr_uuids": source_mvr_uuids,
                "metadata": {
                    "source_mvr_uuids": source_mvr_uuids,
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
            frame_spacing = self.temporal_window / 2  # 0.5s for 1.0s window
            for i, frame_b64 in enumerate(frames_data):
                # Decode base64 to bytes
                frame_bytes = base64.b64decode(frame_b64)
                # Convert to numpy array
                nparr = np.frombuffer(frame_bytes, np.uint8)
                # Decode JPEG to image
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                frames.append({
                    "frame": frame,
                    "frame_index": i,
                    "timestamp": i * frame_spacing,
                })
            
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
            person_objects = result.get("person_objects", [])
            source_mvr_uuids = self._extract_source_identity_uuids(person_objects)
            
            payload = {
                "camera_id": camera_id,
                "timestamp": datetime.utcnow().isoformat(),
                "people_count": people_count,
                "demographics": demographics,
                "source_mvr_uuids": source_mvr_uuids,
                "metadata": {
                    "source_mvr_uuids": source_mvr_uuids,
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
        Get current status of instant detection sampler.

        Returns a per-camera map alongside aggregate information and
        circuit breaker health.
        """
        with self._lock:
            active_cameras = {}
            for cam_id, state in self._samplers.items():
                active_cameras[cam_id] = {
                    "running": state.running,
                    "thread_alive": state.thread.is_alive() if state.thread else False,
                    "cycle_counter": state.cycle_counter,
                    "session_uuid": state.session_uuid,
                    "stagger_offset": state.stagger_offset,
                }

        return {
            "running": self._running,
            "current_camera_id": self._current_camera_id,
            "active_cameras": active_cameras,
            "active_camera_count": len(active_cameras),
            "cached_results": len(self.results_cache),
            "sampling_interval": self.sampling_interval,
            "temporal_window": self.temporal_window,
            "multi_camera_enabled": self._multi_camera_enabled,
            "service_circuits": {
                "vision": self._vision_circuit.state,
                "vmeta": self._vmeta_circuit.state,
                "orchestrator": self._orchestrator_circuit.state,
            },
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
        with instant_detection_sampler._lock:
            state = instant_detection_sampler._samplers.get(camera_id)
            return state is not None and state.running
    return instant_detection_sampler._running
