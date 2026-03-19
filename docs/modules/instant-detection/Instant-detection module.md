# Instant Detection Module

**Module Version**: 3.0  
**Last Updated**: March 19, 2026  
**Status**: Production  
**Breaking Change**: v3.0 decouples instant detection from the recording lifecycle. Detection is now started/stopped independently via a dedicated eye button in the UI.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Data Flow](#data-flow)
5. [API Reference](#api-reference)
6. [Configuration](#configuration)
7. [Database Schema](#database-schema)
8. [Frontend Widget](#frontend-widget)
9. [Celery Workers](#celery-workers)
10. [Redis Integration](#redis-integration)
11. [WebSocket Real-Time Updates](#websocket-real-time-updates)
12. [Trigger Evaluation](#trigger-evaluation)
13. [Identity Resolution](#identity-resolution)
14. [Performance](#performance)
15. [Troubleshooting](#troubleshooting)

---

## Overview

The Instant Detection module provides **real-time face detection feedback** by sampling 3 frames from the camera stream every 5 seconds. It uses the **same detection quality** as the main recording pipeline (Haar + Dlib two-stage detection via Vision Service, person grouping via Orchestrator, age/gender via VMeta) but without persistent database storage — results live in Redis cache with a 5-minute TTL.

### Key Capabilities

- **Non-blocking parallel processing** — Runs in a daemon thread or Celery worker, independent from the main recording pipeline
- **Same detection quality** — Two-stage Haar + Dlib via Vision Service API
- **Person grouping** — Spatial/IoU-based grouping via Orchestrator Service (with local fallback)
- **Age/gender detection** — DeepFace via VMeta Service (one face per person)
- **Identity resolution** — Matches detected faces against MVR identity store via VMeta
- **Demographics aggregation** — Gender/age breakdowns in the same format as MVR counter
- **Redis cache + Pub/Sub** — Cross-process result access and real-time broadcasting
- **Celery background processing** — Offloads heavy detection to workers (with threaded fallback)
- **Webhook push** — Pushes results to Media Service trigger evaluation
- **WebSocket streaming** — Gateway broadcasts results to frontend via Redis → WebSocket bridge
- **Decoupled lifecycle** — Starts/stops independently from recording via dedicated eye button
- **State persistence** — Frontend syncs detection state from backend on mount (survives app restart/refresh)

---

## Architecture

### High-Level System Diagram

```
Camera Stream (USB / RTSP / Mobile / Edge)
     │
     ├──> [RECORDING PIPELINE] Segments → Full processing → Database → MVR
     │
     └──> [INSTANT DETECTION]
              │
              ├─ Queue Worker captures 3 frames (0s, 0.5s, 1.0s)
              │
              ├─ Submit to Celery Task (or threaded fallback)
              │       │
              │       ├─ Vision Service → Face detection (Haar + Dlib)
              │       ├─ Orchestrator Service → Person grouping (spatial/IoU)
              │       ├─ VMeta Service → Age/gender (DeepFace)
              │       └─ VMeta Service → Identity resolution (face similarity)
              │
              ├─ Cache result in Redis (key: instant_detection:{camera_id}, TTL: 300s)
              │
              ├─ Publish to Redis Pub/Sub (channel: instant-detection)
              │       │
              │       └─ Gateway WebSocket Manager
              │               └─ Broadcast to frontend WebSocket clients
              │
              ├─ Push to webhook (Media Service trigger endpoint)
              │
              └─ Evaluate triggers (Media Service /api/v1/triggers/evaluate)
```

### Service Dependencies

| Service | Port | Role |
|---------|------|------|
| **Cameras Service** | 8005 | Frame capture, sampling loop, Celery submission |
| **Vision Service** | 8003 | Face detection (`POST /faces/detect-single-frame`) |
| **Orchestrator Service** | 8002 | Person grouping (`POST /api/v1/person-objects/from-faces`) |
| **VMeta Service** | 8008 | Age/gender (`POST /api/v1/ml/detect-age-gender`), Identity (`POST /api/v1/ml/identify-face`) |
| **Media Service** | 8000 | Trigger evaluation (`POST /api/v1/triggers/evaluate`) |
| **Gateway Service** | 8080 | API proxy + WebSocket bridge |
| **Redis** | 6379 | Cache, Pub/Sub, Celery broker/backend |

---

## Components

### File Inventory

#### Backend — Cameras Service (`ppl-meta-cameras/`)

| File | Purpose |
|------|---------|
| `src/services/instant_detection.py` | Core `InstantDetectionSampler` class (1646 lines) — sampling loop, frame capture, service API calls, processing pipeline, caching, webhook, Redis pub/sub, trigger evaluation, demographics |
| `src/services/instant_detection_sampler.py` | Lightweight sampler for worker integration (137 lines) — processes frames inline within camera worker thread |
| `src/api/v1/endpoints/instant_detection.py` | REST API endpoints (404 lines) — status, results, start, stop, webhook configuration |
| `src/api/v1/routes.py` | Router registration — mounts at prefix `/instant-detection` |
| `src/tasks/instant_detection_tasks.py` | Celery task `instant_detection.process_frames` — background processing, Redis cache, Pub/Sub publish, webhook push |
| `src/models/camera.py` | Database columns: `instant_detection_enabled`, `instant_detection_interval_seconds` |
| `src/services/camera_detection.py` | Recording pipeline — no longer auto-starts/stops instant detection (decoupled) |
| `config/instant_detection.yml` | YAML configuration for sampling, detection, output, threading |

#### Gateway (`ppl-meta-gateway/`)

| File | Purpose |
|------|---------|
| `src/api/v1/router.py` | Proxy routes for instant detection endpoints to Cameras Service |
| `src/api/v1/websockets.py` | WebSocket endpoint + Redis Pub/Sub listener + ConnectionManager |

#### Frontend (`ppl-meta-frontend/`)

| File | Purpose |
|------|---------|
| `lib/widgets/camera/instant_detection_widget.dart` | Flutter widget — polling, demographics display, detection-gated lifecycle |
| `lib/widgets/camera/instant_detection_controls.dart` | Eye button widget — `InstantDetectionControls` (compact) and `StreamInstantDetectionControls` (full) |
| `lib/core/providers/camera_providers.dart` | `CameraInstantDetectionState`, `CameraInstantDetectionNotifier`, `cameraInstantDetectionProvider` |
| `lib/core/services/camera_service.dart` | `startInstantDetection()`, `stopInstantDetection()`, `getInstantDetectionStatus()` methods |

#### Shared (`shared/`)

| File | Purpose |
|------|---------|
| `queue_config.py` | Celery app config + task routing (`instant_detection.process_frames` → `instant_detection_queue`) |
| `redis_pubsub.py` | Redis Pub/Sub helper with `instant-detection` channel |

---

## Data Flow

### 1. User Taps Eye Button → Instant Detection Start

Detection is now triggered independently by the user tapping the eye button (👁) in the camera card or stream page. This calls the backend directly:

```
Frontend (eye button tap)
  → CameraInstantDetectionNotifier.startDetection()
    → CameraService.startInstantDetection(deviceId)
      → POST /api/v1/instant-detection/start/{camera_id}
        → InstantDetectionSampler.start_sampling(camera_id, ...)
```

Recording and detection are **fully independent** — you can run detection without recording, recording without detection, or both simultaneously.

> **Note**: The `camera_detection.py` recording flow no longer auto-starts or auto-stops instant detection. The `enable_instant_detection` and `auto_stop_instant_detection` parameters are deprecated.

### 2. Sampling Loop (Every 5 Seconds)

The `InstantDetectionSampler._sample_loop()` runs in a daemon thread:

1. **Check queue worker status** — verifies the worker is still connected
2. **Capture 3 frames** via `_capture_3_frames_from_queue()`:
   - Frame 0 at `t=0.0s`
   - Frame 1 at `t=0.5s`
   - Frame 2 at `t=1.0s`
3. **Submit to Celery** via `_submit_to_celery()` — non-blocking
4. **Sleep** for remaining interval time
5. **Failure handling** — stops after 3 consecutive failures

### 3. Processing Pipeline (Celery Worker or Threaded Fallback)

The `_process_3_frames()` method orchestrates:

**Step 1 — Face Detection (Vision Service)**
```
POST {vision_url}/faces/detect-single-frame
Content-Type: multipart/form-data (JPEG-encoded frame)

Returns: List of faces with bbox, confidence, embedding, method
```

**Step 2 — Person Grouping (Orchestrator Service)**
```
POST {orchestrator_url}/api/v1/person-objects/from-faces
Body: {
    "session_uuid": "...",
    "face_detections": [...],
    "tolerance_percent": 20.0,     # Camera-specific from DB
    "enable_quality_analysis": true,
    "storage_mode": "memory_only"
}

Returns: person_groups with representative_faces
```

Falls back to local `_simple_spatial_grouping()` (IoU-based) if Orchestrator is unavailable.

**Step 3 — Age/Gender (VMeta Service)**

Called **once per person** on the highest-confidence face:
```
POST {vmeta_url}/api/v1/ml/detect-age-gender
Content-Type: multipart/form-data (JPEG face crop)
Timeout: 2 seconds

Returns: { age_min, age_max, gender, gender_confidence, age_confidence }
```

**Step 4 — Identity Resolution (VMeta Service)**

Called per person to match against MVR identity store:
```
POST {vmeta_url}/api/v1/ml/identify-face
    ?similarity_threshold=0.70
    &dedupe_similarity_threshold=0.55
    &enable_dedupe_reuse=true
    &max_results=1
    &create_if_missing=true
Content-Type: multipart/form-data (JPEG face crop)
Timeout: 2 seconds

Returns: { matched, mvr_people_uuid, similarity_score }
```

**Step 5 — Demographics Aggregation**

Calculates gender/age breakdowns from person objects:
- Gender: male / female / unknown
- Age: young (< 21) / adult (≥ 21) / unknown
- Percentages for each category

### 4. Result Distribution

After processing, results are distributed through multiple channels:

| Channel | Mechanism | Consumer |
|---------|-----------|----------|
| **Redis Cache** | `SETEX instant_detection:{camera_id}` (TTL 300s) | Frontend API endpoint |
| **Redis Pub/Sub** | `PUBLISH instant-detection` | Gateway WebSocket Manager |
| **Webhook** | `POST {webhook_url}` | Media Service triggers |
| **Trigger Evaluation** | `POST {media_url}/api/v1/triggers/evaluate` | Media Service trigger engine |
| **Memory Cache** | In-process dict | Internal hooks via `get_latest_instant_results()` |

---

## API Reference

All endpoints are mounted at `/api/v1/instant-detection/` on the Cameras Service (port 8005) and proxied through the Gateway (port 8080).

### GET /status

Get status of the instant detection system. Includes `current_camera_id` so the frontend can sync detection state on mount (after app restart or page refresh).

**Response:**
```json
{
  "success": true,
  "status": {
    "running": true,
    "thread_alive": true,
    "current_camera_id": "usb_camera_0",
    "cached_results": 2,
    "sampling_interval": 5,
    "temporal_window": 1.0
  }
}
```

### GET /results/{camera_id}

Get latest instant detection results for a specific camera.

Results are fetched from Redis first (cross-process), falling back to in-memory cache. Stale results (> 5 minutes) are automatically cleaned up and return 404.

**Response (200):**
```json
{
  "success": true,
  "camera_id": "usb_camera_0",
  "timestamp": "2026-03-19T10:30:00.000000Z",
  "temporal_window_seconds": 1.0,
  "frames_processed": 3,
  "total_faces_detected": 3,
  "people_count": 2,
  "people_detected": 2,
  "demographics": {
    "total_male": 1,
    "total_female": 1,
    "total_unknown_gender": 0,
    "percent_male": 50.0,
    "percent_female": 50.0,
    "percent_unknown_gender": 0.0,
    "total_young": 0,
    "total_adult": 2,
    "total_unknown_age": 0,
    "percent_young": 0.0,
    "percent_adult": 100.0,
    "percent_unknown_age": 0.0
  },
  "person_objects": [
    {
      "person_id": "uuid",
      "person_object_uuid": "uuid",
      "faces": [
        {
          "face_id": "uuid",
          "frame_index": 0,
          "timestamp": 0.0,
          "bbox": [245, 180, 345, 280],
          "confidence": 0.92,
          "method": "two_stage_haar_dlib",
          "embedding": [0.023, -0.145]
        }
      ],
      "face_count": 3,
      "avg_confidence": 0.94,
      "best_bbox": [285, 190, 385, 290],
      "age_gender": {
        "age_range": "(25-32)",
        "age_confidence": 0.78,
        "gender": "Male",
        "gender_confidence": 0.91
      },
      "mvr_person_uuid": "uuid-if-identity-resolved"
    }
  ],
  "processing_time_seconds": 0.45,
  "detection_method": "vision_service_spatial_grouping",
  "storage": "none",
  "_metadata": {
    "cached_at": 1710840600.0,
    "source": "redis",
    "age_seconds": 2.1
  }
}
```

**Response (404):** No results available — instant detection not started or results expired.

### GET /results

Get latest results for **all** cameras.

**Response:**
```json
{
  "success": true,
  "total_cameras": 2,
  "results": {
    "usb_camera_0": { "..." },
    "edge-camera-1": { "..." }
  }
}
```

### POST /start/{camera_id}

Manually start instant detection for a camera. Verifies the camera exists in the database.

**Response (200):**
```json
{
  "success": true,
  "message": "Instant detection started for camera usb_camera_0",
  "camera_id": "usb_camera_0",
  "sampling_interval": 5,
  "temporal_window": 1.0
}
```

### POST /stop

Stop instant detection sampling globally.

**Response:**
```json
{
  "success": true,
  "message": "Instant detection stopped"
}
```

### POST /stop/{camera_id}

Stop instant detection for a **specific camera**. Only stops if the currently running camera matches the requested `camera_id`. This is the endpoint used by the frontend eye button.

**Response (running for this camera):**
```json
{
  "success": true,
  "message": "Instant detection stopped for usb_camera_0"
}
```

**Response (not running for this camera):**
```json
{
  "success": true,
  "message": "Instant detection was not running for usb_camera_0"
}
```

### POST /webhook/configure

Configure webhook endpoint for pushing results.

**Request Body:**
```json
{
  "url": "http://localhost:8000/api/v1/triggers/instant-detection",
  "enabled": true
}
```

### GET /webhook/status

Returns current webhook configuration and enabled state.

### POST /webhook/enable / POST /webhook/disable

Toggle webhook push without changing the URL.

---

## Configuration

### YAML Configuration (`ppl-meta-cameras/config/instant_detection.yml`)

```yaml
instant_detection:
  enabled: true

  sampling:
    interval_seconds: 5           # Sample every 5 seconds
    frames_per_sample: 3          # Always 3 frames
    temporal_window_seconds: 1.0  # 1 second between first and last frame

  detection:
    method: "two_stage"            # Haar + Dlib (via Vision Service)
    confidence_threshold: 0.5
    similarity_threshold: 0.6     # Person grouping threshold

  age_gender:
    enabled: true                  # Run age/gender on best face per person

  output:
    storage: "memory_only"         # No database writes
    cache_ttl_seconds: 5
    broadcast_method: "cache"      # cache, websocket, or redis

  thread:
    priority: "low"
    daemon: true
    name_prefix: "instant-detect"

services:
  vision: "http://localhost:8003"
  vmeta: "http://localhost:8008"
  orchestrator: "http://localhost:8002"
  cameras: "http://localhost:8005"
```

### Environment Variables (`ppl-meta-cameras/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `INSTANT_DETECTION_WEBHOOK_URL` | — | Webhook endpoint URL |
| `INSTANT_DETECTION_WEBHOOK_ENABLED` | `false` | Enable webhook push |
| `INSTANT_IDENTITY_SIMILARITY_THRESHOLD` | `0.70` | Face identity match threshold |
| `INSTANT_IDENTITY_DEDUPE_SIMILARITY_THRESHOLD` | `0.55` | Deduplication similarity threshold |
| `INSTANT_IDENTITY_MAX_RESULTS` | `1` | Max identity matches returned |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database index |

---

## Database Schema

### Camera Model Columns (SQLAlchemy)

Located in `ppl-meta-cameras/src/models/camera.py`:

```python
# Pipeline Configuration (Instant Detection + Recording Decoupling)
instant_detection_enabled = Column(Boolean, default=True)
recording_pipeline_enabled = Column(Boolean, default=True)
instant_detection_interval_seconds = Column(Integer, default=5)
segment_duration_seconds = Column(Integer, default=30)
```

These per-camera settings store detection configuration. Since v3.0 (decoupling), `instant_detection_enabled` no longer controls auto-start during recording — detection is started/stopped independently via the eye button. The setting is retained for future use (e.g., determining which cameras show the detection controls).

---

## Frontend Widgets

### Eye Button — `InstantDetectionControls` / `StreamInstantDetectionControls`

Located in `ppl-meta-frontend/lib/widgets/camera/instant_detection_controls.dart`.

Two widget variants for toggling instant detection:

| Widget | Location | Style |
|--------|----------|-------|
| `InstantDetectionControls` | Camera card (next to record button) | Compact `IconButton` with eye icon |
| `StreamInstantDetectionControls` | Stream page (next to record button) | `ElevatedButton.icon` with label |

**UI States:**
- **Inactive**: Grey `visibility_off` icon → tap to start detection
- **Active**: Blue `visibility` icon → tap to stop detection
- **Loading**: `CircularProgressIndicator` → action in progress

Both widgets watch `cameraInstantDetectionProvider(cameraId)` and call `toggleDetection()` on tap.

### State Management — `CameraInstantDetectionNotifier`

Located in `ppl-meta-frontend/lib/core/providers/camera_providers.dart`.

```dart
final cameraInstantDetectionProvider = StateNotifierProvider.family<
    CameraInstantDetectionNotifier,
    CameraInstantDetectionState,
    String>((ref, cameraId) { ... });
```

**Key behaviour:**
- **On creation**: Calls `_syncFromBackend()` — fetches `GET /status`, reads `current_camera_id`, sets `isDetecting=true` if the backend is running for **this** camera
- **`startDetection()`**: Calls `POST /instant-detection/start/{camera_id}`, updates state
- **`stopDetection()`**: Calls `POST /instant-detection/stop/{camera_id}`, updates state
- **`toggleDetection()`**: Convenience method that calls start or stop based on current state

**State persistence across app restarts**: The `_syncFromBackend()` call on init means the eye button immediately reflects the real server-side state after refresh. No stale "off" state.

### Results Widget — `InstantDetectionWidget`

Located in `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart`.

#### Lifecycle (v3.0 — Detection-Gated)

```
                    ┌──────────────────────┐
                    │    Widget Mounted     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
              ┌─────│ Watch Detection State │─────┐
              │     └──────────────────────┘     │
              │                                   │
        Not Detecting                       Detecting
              │                                   │
              ▼                                   ▼
  ┌─────────────────────┐           ┌──────────────────────┐
  │ Show: "Start         │           │ Start Lazy Checking   │
  │ detection to see     │           │ (every 10s)           │
  │ live results"        │           └──────────┬───────────┘
  │ No polling.          │                      │
  └─────────────────────┘                      │
                                    Detection results found?
                                         │           │
                                        Yes          No
                                         │           │
                                         ▼           ▼
                              ┌──────────────┐  ┌──────────────────┐
                              │ Start Fast   │  │ Show: "Waiting   │
                              │ Polling      │  │ for detection    │
                              │ (every 5s)   │  │ results..." +    │
                              │              │  │ Check button     │
                              │ Show: "Live: │  └──────────────────┘
                              │ X people"    │
                              │ + demographics│
                              └──────────────┘
```

#### Detection State Gating (Decoupled from Recording)

The widget uses `ref.listen(cameraInstantDetectionProvider)` to detect state changes:
- **Detection starts** (eye button tapped) → begins lazy checking (10s interval)
- **Detection results found** → switches to fast polling (configurable, default 5s)
- **Detection stops/errors** → falls back to lazy checking
- **Detection stopped** (eye button tapped) → stops all polling immediately, clears state

> **v3.0 change**: The widget no longer watches `cameraRecordingProvider`. Recording state has no effect on detection polling.

#### Demographics Display

The widget reads the `demographics` field from the API response and displays:
- **Gender row**: Male count (%), Female count (%), Unknown count (%)
- **Age row**: Young count (< 21, %), Adult count (≥ 21, %), Unknown count (%)

Refresh interval is configurable via `SharedPreferences` key `instant_detection_interval`.

---

## Celery Workers

### Task: `instant_detection.process_frames`

Located in `ppl-meta-cameras/src/tasks/instant_detection_tasks.py`.

```python
@celery_app.task(
    name="instant_detection.process_frames",
    queue="instant_detection_queue",
    time_limit=30,       # Hard limit: 30 seconds
    soft_time_limit=25,  # Soft limit: 25 seconds
    max_retries=2,
    retry_backoff=True
)
def process_instant_detection(camera_id, frames_data, timestamp):
    # 1. Decode base64 frames → numpy arrays
    # 2. Call InstantDetectionSampler._process_frames_sync()
    # 3. Cache result in Redis (SETEX, 300s TTL)
    # 4. Publish to Redis Pub/Sub (instant-detection channel)
    # 5. Push to webhook (if configured)
```

### Queue Routing

Defined in `shared/queue_config.py`:
```python
task_routes = {
    "instant_detection.process_frames": {"queue": "instant_detection_queue"},
}
```

### Fallback (No Celery)

When Celery is unavailable (import error or connection failure), `_submit_to_celery()` falls back to a **background thread** that:
1. Creates a new event loop
2. Runs `_process_3_frames()` synchronously
3. Caches in both memory and Redis
4. Pushes to webhook and Redis Pub/Sub
5. Evaluates triggers

This ensures instant detection works even without a Celery worker running.

---

## Redis Integration

### Cache Key Pattern

```
instant_detection:{camera_id}
```
- **TTL**: 300 seconds (5 minutes)
- **Value**: JSON-serialized detection result
- **Written by**: Celery worker or threaded fallback
- **Read by**: REST API endpoint (`GET /results/{camera_id}`)

### Pub/Sub Channel

```
instant-detection
```

**Message format:**
```json
{
  "camera_id": "usb_camera_0",
  "timestamp": "2026-03-19T10:30:00",
  "people_count": 2,
  "demographics": {
    "total_male": 1, "total_female": 1,
    "percent_male": 50.0, "percent_female": 50.0,
    "total_young": 0, "total_adult": 2,
    "percent_young": 0.0, "percent_adult": 100.0
  },
  "source_mvr_uuids": ["uuid1", "uuid2"],
  "metadata": {
    "source_mvr_uuids": ["uuid1", "uuid2"],
    "processing_time": 0.45,
    "total_faces": 3
  }
}
```

**Publishers**: Celery worker task, threaded fallback in `_publish_to_redis_sync()`  
**Subscribers**: Gateway WebSocket `ConnectionManager._redis_listener()`

---

## WebSocket Real-Time Updates

### Endpoint

```
ws://localhost:8080/api/v1/ws/instant-detection
```

### Connection Manager (`ppl-meta-gateway/src/api/v1/websockets.py`)

The `ConnectionManager` class manages WebSocket connections with auto-scaling:

- **First client connects** → starts Redis Pub/Sub listener on `instant-detection` channel
- **Messages arrive on Redis** → parsed and broadcast to all connected WebSocket clients
- **Last client disconnects** → stops Redis listener (resource cleanup)
- **Ping/pong** → client sends `"ping"`, server responds `"pong"`

### WebSocket Message Format (to frontend)

```json
{
  "type": "instant-detection",
  "data": {
    "camera_id": "usb_camera_0",
    "timestamp": "...",
    "people_count": 2,
    "demographics": { "..." },
    "metadata": { "..." }
  }
}
```

### Polling vs WebSocket Comparison

| Aspect | REST Polling | WebSocket |
|--------|-------------|-----------|
| Latency | Up to 5 seconds | < 100ms |
| Server Load | N cameras × polls/interval | 1 Redis listener |
| Network | Constant traffic | Event-driven only |
| Scalability | O(n²) | O(n) |

> **Note**: The current frontend widget still uses REST polling. WebSocket integration is available but the widget has not been migrated to consume WebSocket messages yet.

---

## Trigger Evaluation

After each detection cycle, results are sent to the Media Service trigger engine:

```
POST http://localhost:8000/api/v1/triggers/evaluate
Timeout: 3 seconds
```

**Payload (CounterDataRequest format):**
```json
{
  "camera_device_id": "usb_camera_0",
  "total_count": 2,
  "gender_distribution": { "male": 1, "female": 1 },
  "age_distribution": { "0-18": 0, "19-30": 1, "31-50": 1 },
  "timestamp": "2026-03-19T10:30:00"
}
```

Age distribution for adults is split across ranges: 50% → 19–30, 30% → 31–50, 20% → 51+.

---

## Identity Resolution

Each detected person's best-confidence face is sent to VMeta for identity matching:

```
POST {vmeta_url}/api/v1/ml/identify-face
    ?similarity_threshold=0.70
    &dedupe_similarity_threshold=0.55
    &enable_dedupe_reuse=true
    &max_results=1
    &create_if_missing=true
```

When a match is found, the `mvr_person_uuid` is attached to both the person object and the face object in the results. These UUIDs are also extracted and included in Redis Pub/Sub messages as `source_mvr_uuids` for downstream matching.

---

## Performance

| Metric | Value |
|--------|-------|
| Frames per iteration | 3 |
| Temporal window | 1.0 second (0.5s spacing) |
| Iteration frequency | Every 5 seconds (configurable) |
| Processing time | 0.4–2.5 seconds (depends on face count) |
| CPU usage | ~5–10% (low priority daemon thread) |
| Redis cache TTL | 300 seconds |
| Celery task time limit | 30 seconds (hard), 25 seconds (soft) |
| Celery max retries | 2 (with exponential backoff) |
| VMeta timeout | 2 seconds per call |
| Webhook timeout | 2 seconds |
| Trigger eval timeout | 3 seconds |
| Max consecutive failures | 3 (then auto-stop) |

### Comparison with Main Recording Pipeline

| Feature | Recording Pipeline | Instant Detection |
|---------|-------------------|-------------------|
| Frames | ~900 per 30s segment | 3 per iteration |
| Frequency | Every 30s (segment) | Every 5s |
| Processing time | 2–3 seconds | 0.4–2.5 seconds |
| Face detection | Vision Service (Haar + Dlib) | **Same** Vision Service |
| Person grouping | Orchestrator Service | **Same** Orchestrator Service |
| Age/gender | VMeta Service (DeepFace) | **Same** VMeta Service |
| Identity resolution | ❌ No | ✅ Yes (VMeta similarity) |
| Database storage | ✅ Yes (MVR records) | ❌ No (Redis cache only) |
| Trigger evaluation | ❌ No | ✅ Yes (real-time) |
| Use case | Permanent records | Real-time feedback |

---

## Troubleshooting

### Eye Button Shows Inactive After App Restart

This should not happen in v3.0 — the `CameraInstantDetectionNotifier` calls `_syncFromBackend()` on mount, which fetches `GET /status` and reads `current_camera_id`. If the button still shows inactive:

1. Check the backend is actually running detection:
   ```bash
   curl http://localhost:8005/api/v1/instant-detection/status
   # Should show: "running": true, "current_camera_id": "your_camera_id"
   ```
2. Check the gateway is proxying the status endpoint:
   ```bash
   curl http://localhost:8080/api/v1/instant-detection/status
   ```
3. Check browser network tab for the status request response.

### Detection Not Starting When Eye Button Is Tapped

1. Check the camera exists in the database:
   ```sql
   SELECT device_id FROM cameras WHERE device_id = 'usb_camera_0';
   ```
2. Check queue worker is connected (detection needs a frame source):
   ```bash
   curl http://localhost:8005/api/v1/instant-detection/status
   ```
3. Manually start via curl to isolate frontend vs backend:
   ```bash
   curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
   ```

### No Results After 15+ Seconds

1. Check Vision Service is running:
   ```bash
   curl http://localhost:8003/health
   ```
2. Check VMeta Service is running:
   ```bash
   curl http://localhost:8008/health
   ```
3. Check Redis is running:
   ```bash
   redis-cli ping
   ```
4. Check Celery worker is running (or threaded fallback will be used):
   ```bash
   celery -A shared.queue_config inspect active
   ```
5. Check Redis cache directly:
   ```bash
   redis-cli GET instant_detection:usb_camera_0
   ```

### Results Are Stale (> 5 minutes)

The API endpoint automatically cleans up stale data. If the timestamp is older than 300 seconds, the key is deleted and 404 is returned. Restart the detection:
```bash
curl -X POST http://localhost:8005/api/v1/instant-detection/stop/usb_camera_0
curl -X POST http://localhost:8005/api/v1/instant-detection/start/usb_camera_0
```

Or tap the eye button off then on in the UI.

### Auto-Stop After 3 Failures

The sampling loop stops automatically after 3 consecutive frame capture failures. This indicates:
- Camera was disconnected
- Queue worker crashed
- No frame source available (recording or streaming not active)

Check camera worker status, ensure a frame source is available, and tap the eye button to restart detection.

### Frontend Polling Continues After Stop

Hot restart the Flutter app:
```bash
cd ppl-meta-frontend && flutter clean && flutter pub get && flutter run -d chrome
```

---

## Singleton Pattern

The `InstantDetectionSampler` is managed as a singleton:

```python
# In instant_detection.py (module-level):
instant_detection_sampler = InstantDetectionSampler()

# In endpoints/instant_detection.py (API-level):
_instant_detection_manager: Optional[InstantDetectionSampler] = None

def get_instant_detection_manager() -> InstantDetectionSampler:
    global _instant_detection_manager
    if _instant_detection_manager is None:
        _instant_detection_manager = InstantDetectionSampler(...)
    return _instant_detection_manager
```

The API-level singleton auto-configures webhook from environment variables on first access.

### Hook Functions (for internal modules)

```python
from src.services.instant_detection import get_latest_instant_results

results = get_latest_instant_results("usb_camera_0")
if results:
    for person in results["person_objects"]:
        age = person["age_gender"]["age_range"]
        gender = person["age_gender"]["gender"]
```

```python
from src.services.instant_detection import get_all_instant_results, is_instant_detection_running

all_results = get_all_instant_results()
running = is_instant_detection_running("usb_camera_0")
```

---

## Worker-Integrated Sampler

A lightweight alternative sampler exists at `src/services/instant_detection_sampler.py` for running detection inline within the camera worker thread (no separate sampling thread needed).

It processes frames on every capture call from the worker but only samples frames according to the interval:
- Collects 3 frames spaced across the sampling window
- When 3 frames are collected, submits to the main `InstantDetectionSampler._submit_to_celery()`
- Provides per-worker stats via `get_stats()`

This avoids the overhead of a separate thread and event loop for each camera.
