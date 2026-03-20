# Parallel Instant Detection Proposal

**Author**: PPL Meta Engineering  
**Date**: March 20, 2026  
**Status**: Proposal  
**Target Version**: v3.2  
**Affects**: Cameras Service, Gateway, Frontend

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture (Singleton)](#current-architecture-singleton)
3. [Proposed Architecture (Multi-Camera Manager)](#proposed-architecture-multi-camera-manager)
4. [Recommended Mitigation Techniques](#recommended-mitigation-techniques)
   - [4.1 Staggered Scheduling](#41-staggered-scheduling)
   - [4.2 Celery Concurrency Limits](#42-celery-concurrency-limits)
   - [4.3 Concurrency Semaphore](#43-concurrency-semaphore)
   - [4.4 Circuit Breaker](#44-circuit-breaker)
5. [Implementation Plan](#implementation-plan)
   - [Phase 1: Sampler Refactoring](#phase-1-sampler-refactoring)
   - [Phase 2: Staggered Scheduling](#phase-2-staggered-scheduling)
   - [Phase 3: Concurrency Semaphore](#phase-3-concurrency-semaphore)
   - [Phase 4: Circuit Breaker](#phase-4-circuit-breaker)
   - [Phase 5: API & Frontend Updates](#phase-5-api--frontend-updates)
6. [Resource Impact Analysis](#resource-impact-analysis)
7. [Backward Compatibility](#backward-compatibility)
8. [Testing Strategy](#testing-strategy)
9. [Rollout Plan](#rollout-plan)

---

## Executive Summary

The instant detection system currently uses a singleton `InstantDetectionSampler` that supports **one camera at a time**. Starting detection on a second camera silently stops the first. This proposal refactors the singleton into a multi-camera manager and introduces four complementary mitigation techniques to prevent downstream service saturation:

1. **Staggered scheduling** — offset detection cycles across cameras to spread load over time
2. **Celery concurrency limits** — cap parallel Celery task execution via worker configuration
3. **Concurrency semaphore** — limit simultaneous outbound service calls in the threaded fallback path
4. **Circuit breaker** — temporarily stop calling services that are failing, with auto-recovery

These techniques are ordered by priority and implementation complexity. Together they ensure stable multi-camera detection without overwhelming Vision, VMeta, or Orchestrator services.

---

## Current Architecture (Singleton)

### Single-Camera State

The `InstantDetectionSampler` class (`ppl-meta-cameras/src/services/instant_detection.py`) holds global state for one camera:

```python
# __init__ (lines 60-84)
self._detection_thread = None              # One daemon thread
self._running = False                       # One running flag
self._current_camera_id: Optional[str] = None  # One camera ID
self._cycle_counter: int = 0               # One counter (for storage_multiple)
self._storage_multiple: int = 1            # One storage config
self._session_duration_minutes: int = 0    # One session duration
self._session_started_at: Optional[datetime] = None  # One session timer
self.current_session_uuid: Optional[str] = None      # One session UUID
```

### Forced Camera Switch

When `start_sampling()` is called for a different camera, it stops the current one:

```python
# start_sampling (lines 93-95)
camera_changed = self._current_camera_id != camera_id
if camera_changed and self._running:
    self.stop_sampling()  # Kill existing detection thread
```

### What's Already Per-Camera

Despite the singleton sampler, the infrastructure downstream is already multi-camera ready:

| Component | Per-Camera? | Evidence |
|-----------|-------------|----------|
| Redis cache keys | Yes | `instant_detection:{camera_id}` |
| Redis Pub/Sub messages | Yes | Payload includes `camera_id` |
| Celery tasks | Yes | `camera_id` is a task parameter |
| REST endpoints | Yes | `/start/{camera_id}`, `/stop/{camera_id}`, `/results/{camera_id}` |
| Frontend providers | Yes | `cameraInstantDetectionProvider` uses `.family` pattern |
| Eye button widgets | Yes | Each camera card has its own controls |
| Webhook payloads | Yes | `camera_device_id` in trigger evaluation |
| Persistent storage | Yes | `camera_device_id` column in `tracking_sessions` |

**Conclusion**: The refactoring is contained to the sampler class, the API status endpoint, and the frontend sync logic.

---

## Proposed Architecture (Multi-Camera Manager)

### Per-Camera Sampler State

Replace single-camera fields with a per-camera registry:

```python
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
    stagger_offset: float = 0.0  # Seconds to offset this camera's cycle
```

### Manager Class

The `InstantDetectionSampler` becomes a manager of per-camera states:

```python
class InstantDetectionSampler:
    def __init__(self, ...):
        # Replace single-camera fields with registry
        self._samplers: Dict[str, CameraSamplerState] = {}
        self._lock = threading.RLock()  # Thread-safe access

        # Shared resources (unchanged)
        self.results_cache: Dict[str, Dict] = {}
        self.vision_service_url = vision_service_url
        self.vmeta_service_url = vmeta_service_url
        # ... other service URLs, webhook config, etc.

        # Concurrency controls (new)
        self._vision_semaphore = threading.Semaphore(2)
        self._vmeta_semaphore = threading.Semaphore(3)
        self._vision_circuit = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
        self._vmeta_circuit = CircuitBreaker(failure_threshold=3, cooldown_seconds=30)
```

### Lifecycle Methods

```python
def start_sampling(self, camera_id: str, camera_capture=None):
    with self._lock:
        if camera_id in self._samplers and self._samplers[camera_id].running:
            return  # Already running for this camera

        state = CameraSamplerState(
            camera_id=camera_id,
            stagger_offset=self._calculate_stagger_offset(camera_id),
        )
        state.running = True
        state.thread = threading.Thread(
            target=self._sample_loop,
            args=(state,),
            daemon=True,
            name=f"instant-detection-{camera_id}"
        )
        self._samplers[camera_id] = state
        state.thread.start()

def stop_sampling(self, camera_id: str = None):
    with self._lock:
        if camera_id:
            # Stop one camera
            if camera_id in self._samplers:
                self._samplers[camera_id].running = False
                self._samplers[camera_id].thread.join(timeout=2)
                del self._samplers[camera_id]
        else:
            # Stop all cameras
            for state in self._samplers.values():
                state.running = False
            for state in self._samplers.values():
                state.thread.join(timeout=2)
            self._samplers.clear()

def get_status(self) -> Dict:
    with self._lock:
        return {
            "running": len(self._samplers) > 0,
            "active_cameras": {
                cam_id: {
                    "thread_alive": state.thread.is_alive() if state.thread else False,
                    "cycle_counter": state.cycle_counter,
                    "session_uuid": state.session_uuid,
                    "effective_interval": self._effective_interval(),
                }
                for cam_id, state in self._samplers.items()
            },
            "active_camera_count": len(self._samplers),
            "sampling_interval": self.sampling_interval,
            "effective_interval": self._effective_interval(),
            "temporal_window": self.temporal_window,
        }
```

---

## Recommended Mitigation Techniques

### 4.1 Staggered Scheduling

**Problem**: K cameras all firing their 5-second cycle at the same wall-clock instant creates a burst of `K × (3 + 2N)` simultaneous requests to downstream services.

**Solution**: Offset each camera's sampling loop start by `interval / active_count`:

```python
def _calculate_stagger_offset(self, camera_id: str) -> float:
    """Calculate time offset for this camera to stagger cycles."""
    with self._lock:
        active_count = len(self._samplers) + 1  # +1 for the camera being added
    # Distribute evenly across the sampling interval
    index = hash(camera_id) % active_count
    return (self.sampling_interval / active_count) * index

def _sample_loop(self, state: CameraSamplerState):
    """Per-camera sampling loop with stagger offset."""

    # Initial stagger delay — spread cameras across the interval
    if state.stagger_offset > 0:
        logger.info(
            f"⏱️ Camera {state.camera_id}: stagger offset {state.stagger_offset:.1f}s"
        )
        time.sleep(state.stagger_offset)

    consecutive_failures = 0

    while state.running:
        cycle_start = time.time()
        try:
            frames = self._capture_3_frames_from_queue(state.camera_id)
            if frames:
                self._submit_to_celery(state.camera_id, frames)
                consecutive_failures = 0

                # Per-camera persistence check
                state.cycle_counter += 1
                if (state.storage_multiple > 0
                        and state.cycle_counter % state.storage_multiple == 0):
                    self._maybe_persist_cycle(state)
            else:
                consecutive_failures += 1
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Detection cycle failed for {state.camera_id}: {e}")

        if consecutive_failures >= 3:
            logger.warning(f"3 consecutive failures for {state.camera_id} — stopping")
            break

        # Sleep for remaining interval
        elapsed = time.time() - cycle_start
        sleep_time = max(0, self._effective_interval() - elapsed)
        time.sleep(sleep_time)

    state.running = False
```

**Impact on request pattern with 5 cameras at 5s interval**:

```
Without stagger (burst):
  t=0.0s: cam0 + cam1 + cam2 + cam3 + cam4  → 15 Vision calls at once
  t=5.0s: cam0 + cam1 + cam2 + cam3 + cam4  → 15 Vision calls at once

With stagger (distributed):
  t=0.0s: cam0  → 3 Vision calls
  t=1.0s: cam1  → 3 Vision calls
  t=2.0s: cam2  → 3 Vision calls
  t=3.0s: cam3  → 3 Vision calls
  t=4.0s: cam4  → 3 Vision calls
  t=5.0s: cam0  → 3 Vision calls (next cycle)
```

**Complexity**: Trivial. One sleep at thread start, hash-based index.

---

### 4.2 Celery Concurrency Limits

**Problem**: The Celery worker processes tasks as fast as they arrive. With K cameras, `instant_detection_queue` receives K tasks every interval, each spawning multiple outbound service calls.

**Solution**: Limit Celery worker process concurrency via startup configuration:

```bash
# Start the instant detection worker with max 3 concurrent tasks
celery -A shared.queue_config worker \
    -Q instant_detection_queue \
    --concurrency=3 \
    --max-tasks-per-child=100 \
    -n instant_detection_worker@%h
```

**How it works**: Even if 10 cameras submit tasks, only 3 execute simultaneously. The remaining 7 queue in Redis and are processed as slots free up. Since instant detection results are ephemeral (5-minute Redis TTL), slight delays are invisible to users.

**Configuration in `shared/queue_config.py`**:

```python
# Add to celery_app.conf.update (existing file)
celery_app.conf.update(
    # ... existing config ...
    worker_concurrency=3,  # Default concurrency for instant detection worker
)
```

**Alternative — per-queue concurrency via task rate limiting**:

```python
# In instant_detection_tasks.py
@celery_app.task(
    name="instant_detection.process_frames",
    queue="instant_detection_queue",
    rate_limit="6/m",  # Max 6 tasks per minute (1 every 10s)
    time_limit=30,
    soft_time_limit=25
)
```

**Complexity**: Configuration-only. No code changes required.

**Limitation**: Only applies when Celery is available. The threaded fallback path (used when Celery is down) needs the concurrency semaphore (section 4.3).

---

### 4.3 Concurrency Semaphore

**Problem**: In the threaded fallback path (no Celery), each camera thread calls Vision and VMeta directly. Without coordination, all threads can hit services simultaneously.

**Solution**: Shared semaphores that limit concurrent outbound calls per service:

```python
class InstantDetectionSampler:
    def __init__(self, ...):
        # ...
        # Concurrency semaphores — shared across all camera threads
        self._vision_semaphore = threading.Semaphore(
            int(os.getenv("INSTANT_DETECTION_VISION_CONCURRENCY", "2"))
        )
        self._vmeta_semaphore = threading.Semaphore(
            int(os.getenv("INSTANT_DETECTION_VMETA_CONCURRENCY", "3"))
        )
```

**Usage in the detection pipeline (async path)**:

```python
async def _detect_faces_via_vision_service(self, session, frame, frame_index, timestamp):
    """Face detection with semaphore-gated access to Vision Service."""
    # Acquire semaphore (blocking — waits if max concurrent calls reached)
    self._vision_semaphore.acquire()
    try:
        url = f"{self.vision_service_url}/faces/detect-single-frame"
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        async with session.post(url, data=data) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("faces", [])
            return []
    finally:
        self._vision_semaphore.release()

async def _get_age_gender_via_vmeta_service(self, session, frame, bbox):
    """Age/gender detection with semaphore-gated access to VMeta Service."""
    self._vmeta_semaphore.acquire()
    try:
        url = f"{self.vmeta_service_url}/api/v1/ml/detect-age-gender"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with session.post(url, data=data, timeout=timeout) as response:
            if response.status == 200:
                return await response.json()
            return {}
    finally:
        self._vmeta_semaphore.release()

async def _identify_face_via_vmeta_service(self, session, frame, bbox):
    """Identity resolution with semaphore-gated access to VMeta Service."""
    self._vmeta_semaphore.acquire()
    try:
        url = f"{self.vmeta_service_url}/api/v1/ml/identify-face"
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with session.post(url, data=data, timeout=timeout) as response:
            if response.status == 200:
                return await response.json()
            return {"matched": False}
    finally:
        self._vmeta_semaphore.release()
```

**Semaphore sizing guideline**:

| Service | Recommended Limit | Rationale |
|---------|-------------------|-----------|
| Vision | 2 | Heavy GPU-bound processing; each call processes a full frame |
| VMeta (age/gender) | 3 | Lighter DeepFace model; single face crop per call |
| VMeta (identity) | 3 | Shared with age/gender; face embedding comparison |
| Orchestrator | 2 | CPU-bound IoU grouping; fast but memory-intensive |

**Configurable via environment variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `INSTANT_DETECTION_VISION_CONCURRENCY` | `2` | Max concurrent Vision API calls |
| `INSTANT_DETECTION_VMETA_CONCURRENCY` | `3` | Max concurrent VMeta API calls |
| `INSTANT_DETECTION_ORCHESTRATOR_CONCURRENCY` | `2` | Max concurrent Orchestrator calls |

**Complexity**: ~20 lines. Wrap each outbound call in `acquire()`/`release()`.

---

### 4.4 Circuit Breaker

**Problem**: When a downstream service goes down or becomes extremely slow, every camera's detection cycle blocks on the timeout (2–3s per call). With 5 cameras and 3 Vision calls each, that's 15 × 3s = 45 seconds of wasted blocking per interval, plus cascading delays.

**Solution**: A circuit breaker that detects consecutive failures and temporarily stops calling the failing service, with automatic recovery probing:

```python
class CircuitBreaker:
    """
    Three-state circuit breaker for outbound service calls.

    States:
      CLOSED    — normal operation, requests pass through
      OPEN      — service is down, requests are rejected immediately
      HALF_OPEN — probing with a single request to check recovery

    Transitions:
      CLOSED → OPEN:       after `failure_threshold` consecutive failures
      OPEN → HALF_OPEN:    after `cooldown_seconds` have elapsed
      HALF_OPEN → CLOSED:  if the probe request succeeds
      HALF_OPEN → OPEN:    if the probe request fails (reset cooldown timer)
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
            if self._state == self.OPEN:
                # Check if cooldown has elapsed → transition to HALF_OPEN
                if (time.time() - self._last_failure_time) >= self.cooldown_seconds:
                    self._state = self.HALF_OPEN
                    logger.info(
                        f"🔄 Circuit breaker [{self.service_name}]: "
                        f"OPEN → HALF_OPEN (cooldown elapsed, probing...)"
                    )
            return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current_state = self.state  # Triggers OPEN → HALF_OPEN check
        if current_state == self.CLOSED:
            return True
        if current_state == self.HALF_OPEN:
            return True  # Allow one probe request
        return False  # OPEN — reject

    def record_success(self):
        """Record a successful request. Resets failure counter."""
        with self._lock:
            if self._state == self.HALF_OPEN:
                logger.info(
                    f"✅ Circuit breaker [{self.service_name}]: "
                    f"HALF_OPEN → CLOSED (probe succeeded)"
                )
            self._state = self.CLOSED
            self._failure_count = 0

    def record_failure(self):
        """Record a failed request. May trip the circuit."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == self.HALF_OPEN:
                # Probe failed — back to OPEN
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
```

**Integration with detection pipeline**:

```python
class InstantDetectionSampler:
    def __init__(self, ...):
        # ...
        self._vision_circuit = CircuitBreaker("Vision", failure_threshold=3, cooldown_seconds=30)
        self._vmeta_circuit = CircuitBreaker("VMeta", failure_threshold=3, cooldown_seconds=30)
        self._orchestrator_circuit = CircuitBreaker("Orchestrator", failure_threshold=3, cooldown_seconds=30)

    async def _detect_faces_via_vision_service(self, session, frame, frame_index, timestamp):
        if not self._vision_circuit.allow_request():
            logger.debug(f"Vision circuit OPEN — skipping detection for frame {frame_index}")
            return []

        self._vision_semaphore.acquire()
        try:
            url = f"{self.vision_service_url}/faces/detect-single-frame"
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    self._vision_circuit.record_success()
                    result = await response.json()
                    return result.get("faces", [])
                else:
                    self._vision_circuit.record_failure()
                    return []
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self._vision_circuit.record_failure()
            logger.warning(f"Vision Service call failed: {e}")
            return []
        finally:
            self._vision_semaphore.release()
```

**Circuit breaker state diagram**:

```
                 success
            ┌───────────────┐
            │               │
            ▼               │
        ┌────────┐    ┌───────────┐
   ────►│ CLOSED │    │ HALF_OPEN │
        └────┬───┘    └─────┬─────┘
             │              │
             │ N failures   │ failure
             ▼              ▼
        ┌─────────────────────┐
        │        OPEN         │
        │  (reject requests)  │
        │                     │
        │  after cooldown_s → │──► HALF_OPEN
        └─────────────────────┘
```

**Configuration**:

| Variable | Default | Description |
|----------|---------|-------------|
| `CIRCUIT_BREAKER_VISION_THRESHOLD` | `3` | Failures before tripping Vision circuit |
| `CIRCUIT_BREAKER_VMETA_THRESHOLD` | `3` | Failures before tripping VMeta circuit |
| `CIRCUIT_BREAKER_COOLDOWN_SECONDS` | `30` | Seconds before probing a tripped service |

**Complexity**: ~50 lines for the `CircuitBreaker` class + ~5 lines per service call site (check + record).

---

## Implementation Plan

### Phase 1: Sampler Refactoring

**Goal**: Convert the singleton from single-camera to multi-camera manager.

**Files changed**:

| File | Changes |
|------|---------|
| `ppl-meta-cameras/src/services/instant_detection.py` | Add `CameraSamplerState` dataclass; replace single-camera fields with `_samplers` dict; add `threading.RLock`; update `start_sampling()`, `stop_sampling()`, `get_status()`, `_sample_loop()`, `_maybe_persist_cycle()`, session rotation |
| `ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py` | Update `POST /stop/{camera_id}` to stop only that camera; update `POST /stop` to stop all; update `GET /status` response |

**Key changes in `instant_detection.py`**:

1. **Replace instance variables** — Move `_detection_thread`, `_running`, `_current_camera_id`, `_cycle_counter`, `_storage_multiple`, `_session_duration_minutes`, `_session_started_at`, `current_session_uuid`, `_auth_token` into `CameraSamplerState`.

2. **`start_sampling(camera_id)`** — Creates a new `CameraSamplerState`, adds it to `_samplers[camera_id]`, starts a dedicated thread. No longer stops other cameras.

3. **`stop_sampling(camera_id=None)`** — If `camera_id` is given, stops only that camera's thread and removes from registry. If `None`, stops all.

4. **`_sample_loop(state: CameraSamplerState)`** — Receives its own state object. Reads `state.running`, increments `state.cycle_counter`, checks `state.storage_multiple`. No shared mutable state between cameras.

5. **`get_status()`** — Returns a dict of per-camera statuses plus aggregate info.

6. **Thread safety** — All access to `_samplers` goes through `self._lock`. The `results_cache` dict gets its own `_cache_lock`.

**Endpoint changes in `instant_detection.py` (endpoints)**:

```python
# Updated GET /status response
{
    "success": True,
    "status": {
        "running": True,                    # Any camera active?
        "active_camera_count": 3,
        "active_cameras": {
            "usb_camera_0": {
                "thread_alive": True,
                "cycle_counter": 42,
                "session_uuid": "...",
                "effective_interval": 5
            },
            "rtsp_camera_1": { ... },
            "mobile_camera_2": { ... }
        },
        "sampling_interval": 5,             # Base interval
        "effective_interval": 5,            # May differ with adaptive scaling
        "temporal_window": 1.0
    }
}
```

**Backward compatibility**: The `current_camera_id` field is removed from the status response. Any frontend code that reads `status.current_camera_id` must migrate to checking `status.active_cameras[cameraId]`. See Phase 5.

---

### Phase 2: Staggered Scheduling

**Goal**: Spread camera detection cycles across time to avoid request bursts.

**Files changed**:

| File | Changes |
|------|---------|
| `ppl-meta-cameras/src/services/instant_detection.py` | Add `_calculate_stagger_offset()` method; add initial sleep in `_sample_loop()` |

**Implementation** (see section 4.1 for code):

1. When `start_sampling()` creates a new `CameraSamplerState`, compute `stagger_offset = (interval / active_count) * index`.
2. The `_sample_loop()` sleeps for `stagger_offset` seconds before entering the main loop.
3. The offset is deterministic per camera (hash-based) so restarts produce the same distribution.

**Recalculation**: When a new camera starts or stops, existing cameras keep their current offset (no mid-loop disruption). The offset only affects the initial delay on thread start.

---

### Phase 3: Concurrency Semaphore

**Goal**: Cap simultaneous outbound service calls in the threaded fallback path.

**Files changed**:

| File | Changes |
|------|---------|
| `ppl-meta-cameras/src/services/instant_detection.py` | Add semaphore instances to `__init__`; wrap Vision, VMeta, Orchestrator calls with acquire/release |

**Implementation** (see section 4.3 for code):

1. Create `threading.Semaphore` instances in `__init__` with configurable limits.
2. Wrap each `_detect_faces_via_vision_service()`, `_get_age_gender_via_vmeta_service()`, `_identify_face_via_vmeta_service()`, and `_create_person_objects_via_vision_service()` call with semaphore acquire/release in a try/finally block.

**Note**: When Celery is handling the processing, the semaphore is not needed — Celery worker concurrency (Phase 2) serves the same role. The semaphore is specifically for the threaded fallback path where frames are processed in-process.

---

### Phase 4: Circuit Breaker

**Goal**: Stop calling failing services to prevent cascading timeouts.

**Files changed**:

| File | Changes |
|------|---------|
| `ppl-meta-cameras/src/services/instant_detection.py` | Add `CircuitBreaker` class (~50 lines); add circuit breaker instances to `__init__`; check `allow_request()` before each service call; call `record_success()`/`record_failure()` after each call |

**Implementation** (see section 4.4 for code):

1. Define `CircuitBreaker` class (can live in the same file or in a shared utility).
2. Create one circuit breaker per downstream service in `__init__`.
3. Before each outbound call: check `allow_request()`. If `False`, skip the call and return an empty/default result.
4. After each call: `record_success()` or `record_failure()` based on response status or exception.

**Graceful degradation when a circuit is open**:

| Circuit Open | Detection Behavior |
|-------------|-------------------|
| Vision | Skip face detection entirely — return 0 faces. Detection cycle produces no results (cache not updated). |
| Orchestrator | Fall back to local `_simple_spatial_grouping()` (already implemented). No degradation in results. |
| VMeta (age/gender) | Skip demographics — person objects have `age_range: "unknown"`, `gender: "unknown"`. Faces still detected. |
| VMeta (identity) | Skip identity resolution — `mvr_person_uuid: null`. Faces and demographics still work. |

**Circuit status exposed in API**:

```python
# Add to GET /status response
"service_circuits": {
    "vision": "closed",       # Normal
    "vmeta": "open",          # Service is down — skipping calls
    "orchestrator": "closed"  # Normal
}
```

---

### Phase 5: API & Frontend Updates

**Goal**: Update status API and frontend to work with multi-camera detection.

**Files changed**:

| File | Changes |
|------|---------|
| `ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py` | `GET /status` returns per-camera map; `POST /start/{camera_id}` no longer stops other cameras; `POST /stop/{camera_id}` stops only that camera |
| `ppl-meta-frontend/lib/core/providers/camera_providers.dart` | `_syncFromBackend()` checks `active_cameras` map instead of `current_camera_id` |
| `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart` | (Optional) Display effective interval if adaptive scaling is enabled |
| `ppl-meta-frontend/lib/widgets/camera/instant_detection_controls.dart` | (Optional) Update tooltip to show interval |
| `ppl-meta-frontend/lib/presentation/widgets/settings/camera_settings_section.dart` | (Optional) Add info text about adaptive behavior |

**Frontend `_syncFromBackend()` migration**:

```dart
// BEFORE (single camera)
final status = response['status'];
final activeCameraId = status['current_camera_id'] as String?;
if (activeCameraId == state.cameraId) {
  state = state.copyWith(isDetecting: true);
}

// AFTER (multi camera)
final status = response['status'];
final activeCameras = status['active_cameras'] as Map<String, dynamic>? ?? {};
if (activeCameras.containsKey(state.cameraId)) {
  state = state.copyWith(isDetecting: true);
}
```

**Optional UI enhancements**:

1. **Effective interval display** — When adaptive scaling is active, show `"Detecting every ~7s (3 cameras active)"` near the detection results widget.
2. **Settings info text** — Below the interval slider: `"This is the base interval for a single camera. When multiple cameras are active, the interval may increase automatically."`
3. **Circuit breaker status** — Show a subtle warning icon on the eye button if a downstream service circuit is open (indicating degraded detection quality).

---

## Resource Impact Analysis

### Per-Camera Resource Cost

| Resource | Per Camera Per Cycle | Notes |
|----------|---------------------|-------|
| Memory | ~20 MB | 3 JPEG frames in buffer + decoded numpy arrays |
| CPU (capture) | Negligible | Queue read, not camera I/O |
| CPU (encode) | ~5 ms | JPEG encoding for 3 frames |
| Network (Vision) | 3 HTTP POST requests | ~200 KB per frame (JPEG) |
| Network (VMeta) | 1–N POST requests per person | ~10 KB per face crop |
| Network (Orchestrator) | 1 POST request | ~5 KB JSON payload |
| Thread | 1 daemon thread | Low overhead |
| Redis | 1 SETEX + 1 PUBLISH per cycle | Negligible |

### Scaling Projections

| Active Cameras | Threads | Vision Calls/Interval | VMeta Calls/Interval* | Memory |
|----------------|---------|----------------------|----------------------|--------|
| 1 | 1 | 3 | ~2–4 | ~20 MB |
| 3 | 3 | 9 | ~6–12 | ~60 MB |
| 5 | 5 | 15 | ~10–20 | ~100 MB |
| 10 | 10 | 30 | ~20–40 | ~200 MB |

*Assumes 1–2 people detected per camera on average.

### Service Capacity (estimated)

| Service | Estimated Throughput | Safe Concurrent Calls |
|---------|---------------------|----------------------|
| Vision (face detection) | ~10 req/s on CPU, ~50 req/s on GPU | 2–3 |
| VMeta (age/gender) | ~20 req/s | 3–5 |
| VMeta (identity) | ~15 req/s | 3–5 |
| Orchestrator (grouping) | ~30 req/s | 5+ |

With staggered scheduling + semaphore(2) for Vision, a 5-camera deployment produces ~3 Vision calls per second — well within capacity.

### Worst-Case Scenario (All Mitigations Active)

10 cameras, Vision running on CPU:

1. **Stagger**: 10 cameras × 5s interval → each camera fires 1s apart. Max 3 Vision calls at any moment.
2. **Semaphore(2)**: Even if stagger drifts, at most 2 Vision calls execute simultaneously.
3. **Circuit breaker**: If Vision can't keep up and starts timing out, circuit opens after 3 failures. All cameras skip detection for 30s, then one probe tests recovery.
4. **Celery concurrency(3)**: Worker processes at most 3 detection tasks at a time; rest queue in Redis.

**Result**: Vision never sees more than 2–3 concurrent requests. VMeta never sees more than 3. Orchestrator handles the load easily.

---

## Backward Compatibility

### API Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| `GET /status` — `current_camera_id` removed | Frontend `_syncFromBackend()` | Check `active_cameras` map instead |
| `POST /start/{camera_id}` — no longer stops other cameras | Behavior change (desired) | No migration needed |
| `POST /stop` — now stops ALL cameras | Was already global stop | No change |
| `POST /stop/{camera_id}` — only stops that camera | Was: checked if current matches | Now: removes from registry |

### Deprecation Period (Optional)

To ease migration, the status endpoint can include both the old and new fields for one release:

```json
{
    "status": {
        "current_camera_id": "usb_camera_0",           // DEPRECATED — first active camera
        "active_cameras": { "usb_camera_0": { ... } },  // NEW
        "active_camera_count": 1                         // NEW
    }
}
```

Remove `current_camera_id` in v3.3.

---

## Testing Strategy

### Unit Tests

| Test | Validates |
|------|-----------|
| Start camera A, verify A is in `_samplers` | Basic start |
| Start camera A then B, verify both in `_samplers` | Multi-camera start |
| Stop camera A, verify A removed, B still running | Per-camera stop |
| Stop all, verify `_samplers` is empty | Global stop |
| Start same camera twice, verify only one thread | Idempotent start |
| Stagger offsets are different for different camera IDs | Stagger calculation |
| Semaphore blocks when limit reached | Concurrency limit |
| Circuit breaker transitions: CLOSED → OPEN → HALF_OPEN → CLOSED | Circuit states |
| Circuit breaker rejects requests when OPEN | Request blocking |

### Integration Tests

| Test | Validates |
|------|-----------|
| Start 3 cameras, run 2 cycles each, verify Redis has 3 separate cache keys | End-to-end multi-camera |
| Start 3 cameras, stop 1, verify remaining 2 produce results | Partial stop |
| Kill Vision Service, verify circuit opens, cameras skip detection | Circuit breaker integration |
| Restart Vision Service, verify circuit closes after probe | Auto-recovery |
| `GET /status` returns all active cameras | API contract |
| Frontend eye buttons reflect correct per-camera state | Frontend sync |

### Load Tests

| Test | Validates |
|------|-----------|
| 5 cameras, stagger enabled, measure Vision Service request rate | Stagger effectiveness |
| 5 cameras, stagger disabled, measure Vision Service request rate | Baseline (burst pattern) |
| 10 cameras with semaphore(2), measure max concurrent Vision calls | Semaphore effectiveness |
| Gradually add cameras 1→10, measure response time degradation | Scalability curve |

---

## Rollout Plan

### Stage 1: Internal Testing

- Deploy with feature flag `INSTANT_DETECTION_MULTI_CAMERA_ENABLED=false` (default).
- When flag is `false`, `start_sampling()` stops existing cameras first (current behavior).
- When flag is `true`, cameras run in parallel with all mitigations active.
- Test internally with 2–3 cameras.

### Stage 2: Limited Release

- Enable flag for selected deployments.
- Monitor Vision/VMeta service response times, error rates, and circuit breaker state via logs.
- Tune semaphore limits and circuit breaker thresholds based on observed performance.

### Stage 3: General Availability

- Remove feature flag. Multi-camera is the default.
- Remove deprecated `current_camera_id` from status API (v3.3).
- Document recommended camera limits per deployment tier:
  - **Raspberry Pi**: 1–2 cameras
  - **Standard server (CPU)**: 3–5 cameras
  - **GPU-equipped server**: 5–10 cameras
