# MVR People Persistent Storage for Instant Detection

**Proposal Version**: 1.0  
**Date**: March 19, 2026  
**Status**: Draft  
**Author**: Engineering  

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current Behaviour](#current-behaviour)
3. [Goal](#goal)
4. [Data Gap Analysis](#data-gap-analysis)
5. [Proposed Approach](#proposed-approach)
6. [Database Changes](#database-changes)
7. [Backend Changes](#backend-changes)
8. [Frontend Impact](#frontend-impact)
9. [Migration Strategy](#migration-strategy)
10. [Risks and Mitigations](#risks-and-mitigations)
11. [Alternatives Considered](#alternatives-considered)
12. [Implementation Plan](#implementation-plan)

---

## 1. Problem Statement

Instant detection processes 3 frames every 5 seconds, runs the full detection pipeline (Vision → Orchestrator → VMeta age/gender → VMeta identity resolution), and **discards the structured results**. The only persistent artefact is an isolated MVR record created opportunistically by the `identify-face` endpoint when `create_if_missing=true` — but this record:

- Has **no linked Individual** (`featured_individual_uuid = NULL`)
- Has **no video appearance records** (`individual_video_appearances`)
- Has **no tracking session context** (no `tracking_sessions` row)
- Has **no individual-MVR mapping** (`individual_mvr_mapping`)
- Is flagged as `is_isolated = TRUE` and treated as a second-class citizen by analytics and cross-video tracking

The person objects, bounding boxes, frame timestamps, demographic data, and grouping relationships produced during each detection cycle are cached in Redis (5-minute TTL) and then lost.

This means:

- **Analytics gaps**: The analytics module counts MVR people from the recording pipeline. Instant detection data is invisible to analytics — people detected only via instant detection are not reflected in summary, demographics, behavioral, or time-series analytics.
- **No audit trail**: There is no record of when a person was detected by instant detection, which camera saw them, or how many times they appeared.
- **Broken identity graph**: Isolated MVR entries cannot participate in cross-video merging, hierarchical identity resolution, or individual-group assignment because they have no individual or appearance chain.
- **Lost behavioral data**: Appearance timestamps, bounding boxes, and movement patterns — data already computed — are discarded, eliminating the possibility of heatmap, peak-hour, or visit-frequency analysis from instant detection.

---

## 2. Current Behaviour

### Recording pipeline (reference)

```
Camera → Segments → Vision → Orchestrator → VMeta
                                                │
                           ┌────────────────────┘
                           ▼
                    tracking_sessions        (session metadata)
                           │
                    individuals              (cross-video identities)
                           │
                    individual_video_appearances  (per-video detail)
                           │
                    individual_mvr_mapping   (individual ↔ MVR link)
                           │
                    mvr_people               (aggregated identity)
```

All five tables are populated. The MVR record has `is_isolated = FALSE`, `featured_individual_uuid` pointing to an Individual, and full appearance history.

### Instant detection (current)

```
Camera → 3 Frames → Vision → Orchestrator → VMeta age/gender → VMeta identify-face
                                                                        │
                                                              ┌─────────┘
                                                              ▼
                                                     mvr_people (isolated)
                                                        is_isolated = TRUE
                                                        featured_individual_uuid = NULL
                                                        No individual
                                                        No appearance
                                                        No tracking session
                                                        No mapping
```

Only one table is populated — and only when the person is not already matched to an existing MVR entry. If a match is found (`similarity_score ≥ 0.70`), **nothing is written at all**.

### What instant detection already produces but discards

Each detection cycle yields a rich result structure:

| Data | Available in result | Currently persisted |
|------|:------------------:|:-------------------:|
| Person objects with UUIDs | ✅ | ❌ |
| Face bounding boxes (per frame) | ✅ | ❌ |
| Face confidence scores | ✅ | ❌ |
| Face embeddings (128-dim from Vision) | ✅ | ❌ |
| Detection method | ✅ | ❌ |
| Age/gender per person | ✅ | Partial (only via isolated MVR) |
| MVR person UUID (matched or created) | ✅ | Partial (only on creation) |
| Camera ID + timestamp | ✅ | ❌ |
| People count + demographics | ✅ | ❌ |

---

## 3. Goal

Store instant detection results in the existing database schema so that:

1. Each detection cycle creates a lightweight **tracking session** with source = instant detection.
2. Each detected person is stored as an **individual** with at least one **video appearance** record.
3. Individuals are linked to **MVR people** through the standard **individual_mvr_mapping**, enabling them to participate in analytics, cross-video merging, and identity groups.
4. The analytics module can query instant detection data alongside recording pipeline data seamlessly.
5. The storage overhead is minimal and does not slow down the detection cycle.
6. A configurable **storage multiple** (default `1`) controls how often results are persisted — at multiple `1` every cycle is stored, at `2` every other cycle, at `N` every Nth cycle.
7. A configurable **tracking session duration** (default `0` = unlimited) controls how long a single tracking session runs before a new one is created, enabling time-bounded analytics windows.
8. Both settings are configurable **per camera** in the pipeline settings screen at `http://localhost:3000/#/cameras`.

---

## 4. Data Gap Analysis

### What existing schema fields map to instant detection data

| Schema field | Recording pipeline source | Instant detection equivalent |
|---|---|---|
| `tracking_sessions.collections` | Collection names | `[camera_id]` (single camera) |
| `tracking_sessions.total_videos` | Processed video count | `0` (no videos — frame-based) |
| `tracking_sessions.individuals_found` | Cross-video individuals | Person count from detection cycle |
| `individuals.person_objects` | Orchestrator person object UUIDs | `[person_object_uuid]` from grouping |
| `individuals.appearance_features` | 512-dim FaceNet embedding | Available (128-dim from Vision, or 512-dim if re-extracted via MVR ML) |
| `individual_video_appearances.video_uuid` | Video UUID from media service | **No video UUID** — frames are ephemeral |
| `individual_video_appearances.start_timestamp` / `end_timestamp` | Video timestamps | Detection cycle timestamp (start = end for a single instant) |
| `individual_video_appearances.representative_faces` | Best quality faces JSONB | Best face from person object |
| `individual_mvr_mapping.link_method` | `'auto_create'` or `'auto_merge'` | Needs new value: `'instant_detection'` |

### Schema gaps

1. **No video UUID**: Instant detection does not produce video segments. `individual_video_appearances.video_uuid` is `NOT NULL`. We need a way to store frame-based appearances without a real video UUID.

2. **Embedding dimensionality**: Vision service produces 128-dim embeddings. The `individuals.appearance_features` and `mvr_people.face_embedding` columns are `VECTOR(512)` (FaceNet). Instant detection identity resolution already calls VMeta's `identify-face` endpoint which internally generates 512-dim embeddings — but these are not returned to the caller.

3. **Tracking session semantics**: A recording tracking session covers many videos over a date range. An instant detection "session" is a single 1-second window producing 3 frames. Storing one tracking session per detection cycle would produce ~17,000 rows per camera per day.

4. **Source type markers**: No column currently distinguishes instant detection data from recording pipeline data in `tracking_sessions` or `individuals`.

---

## 5. Proposed Approach

### Design principles

- **Reuse existing tables** — no new tables. Add minimal columns where needed.
- **Batch tracking sessions** — one session per configurable time window, not one per cycle.
- **Configurable storage frequency** — a **storage multiple** controls how often detection results are persisted to the database, independently of the detection cycle itself.
- **Asynchronous storage** — persist after caching and broadcasting; never block the detection loop.
- **Lightweight writes** — insert only what is needed for analytics and identity. Skip data that is only useful for real-time display (bounding boxes, frame indices).

### Per-camera configuration

Two new settings are added to the **camera pipeline settings** (accessible via the tune icon on each camera card at `http://localhost:3000/#/cameras`):

| Setting | Key | Default | Range | Description |
|---------|-----|---------|-------|-------------|
| **Storage multiple** | `storage_multiple` | `1` | 1–12 | How many detection cycles to wait between database writes. `1` = persist every cycle (every 5 s with default interval), `2` = every other cycle (every 10 s), `3` = every third cycle (every 15 s), etc. The effective storage interval in seconds is `storage_multiple × instant_detection_interval_seconds`. |
| **Tracking session duration** | `tracking_session_duration_minutes` | `0` (unlimited) | 0–480 | Maximum duration of a single tracking session in minutes. `0` means the session runs for the entire detection run (eye button on → off). When a non-zero value is set, the current tracking session is automatically completed and a new one started after the specified duration elapses. This allows breaking long detection runs into time-bounded sessions for analytics granularity. |

Both settings are stored per camera alongside the existing pipeline settings (`instant_detection_enabled`, `recording_pipeline_enabled`, `instant_detection_interval_seconds`, `segment_duration_seconds`) and are read by the Cameras service when instant detection starts.

**Examples:**

| Interval (s) | Storage multiple | Effective storage interval | Session duration | Behaviour |
|:---:|:---:|:---:|:---:|---|
| 5 | 1 | 5 s | 0 (unlimited) | Write every cycle, one session per run |
| 5 | 2 | 10 s | 0 (unlimited) | Write every other cycle, one session per run |
| 5 | 6 | 30 s | 60 min | Write every 30 s, new session every hour |
| 10 | 3 | 30 s | 30 min | Write every 30 s, new session every 30 min |

### Architecture overview

```
Instant Detection Cycle (every N seconds)
   │
   ├─ [existing] Cache in Redis + Pub/Sub + Triggers     ← every cycle
   │
   ├─ Increment cycle counter
   │
   └─ cycle_counter % storage_multiple == 0 ?
        │
        ├─ YES → [NEW] Submit storage task to Celery      ← every Nth cycle
        │          │
        │          ▼
        │     Celery Task: instant_detection.persist_results
        │          │
        │          ├─ Upsert tracking session (per time window)
        │          ├─ Create Individual (or match existing via MVR link)
        │          ├─ Create individual_video_appearance (synthetic)
        │          ├─ Create/update individual_mvr_mapping
        │          └─ Update MVR record statistics (total_appearances, last_seen)
        │
        └─ NO  → Skip storage (result still cached in Redis for frontend)
```

### Session batching

Rather than creating a tracking session per cycle, sessions are batched by a configurable **tracking session duration**:

- **On eye button start**: Create `tracking_sessions` row with `status = 'running'`, `source_type = 'instant_detection'`.
- **On each persisted cycle** (governed by `storage_multiple`): Increment `individuals_found`, `person_objects_processed`; update `completed_at`.
- **On session duration elapsed** (if `tracking_session_duration_minutes > 0`): Complete the current session (`status = 'completed'`), immediately create a new one. This happens transparently — the detection loop is never interrupted.
- **On eye button stop**: Complete the current session.

With the default `tracking_session_duration_minutes = 0`, this produces **one session per detection run** (eye on → off), resulting in ~1–5 sessions per camera per day. With a non-zero duration (e.g., 60 minutes), an 8-hour run produces 8 sessions, giving finer-grained analytics time windows.

### Virtual media UUID for frame-based appearances

Since `individual_video_appearances.video_uuid` is `NOT NULL`, we generate a **deterministic synthetic UUID** per detection cycle:

```python
import uuid
synthetic_video_uuid = uuid.uuid5(
    uuid.NAMESPACE_URL,
    f"instant-detection:{camera_id}:{cycle_timestamp_iso}"
)
```

This is stable (same inputs produce the same UUID), collision-free across cameras and timestamps, and clearly identifiable (UUID v5). An alternative is to add a `source_type` column to `individual_video_appearances` and make `video_uuid` nullable — but the synthetic UUID approach requires zero schema changes to this table.

### Individual reuse via MVR identity

When `identify-face` returns `matched=True` with an existing `mvr_people_uuid`:

1. Look up the **featured individual** from `mvr_people.featured_individual_uuid`.
2. If it exists, create an `individual_video_appearance` linked to that individual (the same person was seen again).
3. If `featured_individual_uuid IS NULL` (older isolated MVR), create a new Individual and backfill the link.

When `identify-face` returns `created_new=True`:

1. Create a new Individual record.
2. The isolated MVR was already created by `identify-face`. Link it via `individual_mvr_mapping` and set `featured_individual_uuid`.

When `identify-face` returns `matched=True` but the existing MVR has no individual (legacy isolated data):

1. Create a new Individual.
2. Link to the existing MVR via `individual_mvr_mapping`.
3. Update `mvr_people.featured_individual_uuid`.

---

## 6. Database Changes

### 6.1 New columns on `tracking_sessions`

```sql
-- Migration: Add instant detection source tracking
ALTER TABLE tracking_sessions 
ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'recording_pipeline'
    CHECK (source_type IN ('recording_pipeline', 'instant_detection'));

ALTER TABLE tracking_sessions
ADD COLUMN camera_device_id VARCHAR(100);

-- Index for filtering by source type
CREATE INDEX idx_tracking_sessions_source_type ON tracking_sessions(source_type);
CREATE INDEX idx_tracking_sessions_camera_device ON tracking_sessions(camera_device_id);
```

### 6.2 New column on `individuals`

```sql
-- Migration: Add source type to individuals
ALTER TABLE individuals
ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'recording_pipeline'
    CHECK (source_type IN ('recording_pipeline', 'instant_detection'));

CREATE INDEX idx_individuals_source_type ON individuals(source_type);
```

### 6.3 New link method value on `individual_mvr_mapping`

```sql
-- Migration: Allow instant_detection as link method
ALTER TABLE individual_mvr_mapping
DROP CONSTRAINT IF EXISTS individual_mvr_mapping_link_method_check;

ALTER TABLE individual_mvr_mapping
ADD CONSTRAINT individual_mvr_mapping_link_method_check
CHECK (link_method IN ('auto_create', 'auto_merge', 'manual_link', 'batch_import', 'instant_detection'));
```

### 6.4 No changes to `mvr_people`

The `mvr_people` table already supports instant detection data via `is_isolated` and `source_media_uuid`. When an individual is linked, `is_isolated` can be flipped to `FALSE` and `featured_individual_uuid` populated — making the MVR a first-class citizen.

### 6.5 No changes to `individual_video_appearances`

The synthetic video UUID approach avoids schema changes here.

---

## 7. Backend Changes

### 7.1 New Celery task: `instant_detection.persist_results`

Location: `ppl-meta-cameras/src/tasks/instant_detection_tasks.py`

```python
@celery_app.task(
    name="instant_detection.persist_results",
    queue="instant_detection_queue",
    time_limit=15,
    soft_time_limit=12,
    max_retries=1,
    retry_backoff=True,
    acks_late=True
)
def persist_instant_detection_results(
    camera_id: str,
    session_uuid: str,
    cycle_timestamp: str,
    person_objects: list,
    demographics: dict,
    auth_token: str
):
    """
    Persist instant detection results to VMeta database.
    
    Called asynchronously after the main detection result has been
    cached and broadcast. Never blocks the detection loop.
    """
    # 1. Update tracking session metrics
    # 2. For each person object:
    #    a. Determine MVR link (from mvr_person_uuid in result)
    #    b. Find or create Individual
    #    c. Insert individual_video_appearance
    #    d. Insert/update individual_mvr_mapping
    #    e. Update MVR statistics
```

### 7.2 New VMeta endpoint: `POST /api/v1/instant-detection/persist`

Location: `ppl-meta-vmeta/src/api/v1/instant_detection_storage.py`

This endpoint receives the processed person objects from the Celery task and handles all database writes in a single transaction:

```python
@router.post("/instant-detection/persist")
async def persist_instant_detection(
    request: InstantDetectionPersistRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Persist instant detection results to database.
    
    Request body:
    {
        "session_uuid": "uuid",
        "camera_id": "usb_camera_0",
        "camera_collection_name": "Home Camera Collection",
        "cycle_timestamp": "2026-03-19T10:30:00Z",
        "person_objects": [
            {
                "person_object_uuid": "uuid",
                "mvr_person_uuid": "uuid-or-null",
                "mvr_created_new": true,
                "face_count": 3,
                "avg_confidence": 0.94,
                "best_face": {
                    "bbox": [245, 180, 345, 280],
                    "confidence": 0.92,
                    "embedding": [128-dim]
                },
                "age_gender": {
                    "age_range": "(25-32)",
                    "age_min": 25,
                    "age_max": 32,
                    "age_confidence": 0.78,
                    "gender": "Male",
                    "gender_confidence": 0.91
                }
            }
        ],
        "demographics": { ... }
    }
    
    Returns:
    {
        "stored_individuals": 2,
        "new_individuals_created": 1,
        "existing_individuals_updated": 1,
        "mvr_records_promoted": 1,
        "appearances_created": 2
    }
    """
```

**Processing logic per person object:**

```
For each person_object in request:
    │
    ├─ Has mvr_person_uuid?
    │      │
    │      ├─ YES (matched or just created)
    │      │     │
    │      │     ├─ MVR has featured_individual_uuid?
    │      │     │      │
    │      │     │      ├─ YES → Reuse that Individual
    │      │     │      │         Create appearance record
    │      │     │      │         Update Individual stats (total_appearances, last_seen)
    │      │     │      │
    │      │     │      └─ NO (legacy isolated MVR)
    │      │     │              Create new Individual
    │      │     │              Link via individual_mvr_mapping
    │      │     │              Update MVR: set featured_individual_uuid, is_isolated=FALSE
    │      │     │              Create appearance record
    │      │     │
    │      │     └─ mvr_created_new = TRUE?
    │      │            Create new Individual
    │      │            Link via individual_mvr_mapping (link_method='instant_detection')
    │      │            Update MVR: set featured_individual_uuid, is_isolated=FALSE
    │      │            Create appearance record
    │      │
    │      └─ NO (identity resolution failed or skipped)
    │              Create new Individual (unlinked)
    │              Create appearance record
    │              Log warning — this person has no MVR identity
    │
    └─ Create individual_video_appearance with:
         video_uuid = uuid5("instant-detection:{camera_id}:{timestamp}")
         person_object_uuid = person_object.person_object_uuid
         start_timestamp = end_timestamp = cycle_timestamp
         confidence = avg_confidence
         representative_faces = [best_face]
```

### 7.3 Storage multiple and cycle counting

The `InstantDetectionSampler` maintains a `_cycle_counter` that increments on every detection cycle. The persist task is only submitted when `_cycle_counter % storage_multiple == 0`:

```python
# In InstantDetectionSampler.__init__:
self._cycle_counter = 0
self._storage_multiple = pipeline_settings.get('storage_multiple', 1)
self._session_duration_minutes = pipeline_settings.get('tracking_session_duration_minutes', 0)
self._session_started_at = None

# After result distribution:
self._cycle_counter += 1

if self._storage_multiple > 0 and self._cycle_counter % self._storage_multiple == 0:
    # Check if session needs rotation
    if self._should_rotate_session():
        await self._rotate_tracking_session()
    
    persist_instant_detection_results.delay(
        camera_id=camera_id,
        session_uuid=self.current_session_uuid,
        cycle_timestamp=result["timestamp"],
        person_objects=result["person_objects"],
        demographics=result["demographics"],
        auth_token=self._auth_token
    )

def _should_rotate_session(self) -> bool:
    """Check if the current tracking session duration has been exceeded."""
    if self._session_duration_minutes <= 0:
        return False  # Unlimited — never rotate
    if self._session_started_at is None:
        return False
    elapsed = (datetime.utcnow() - self._session_started_at).total_seconds() / 60
    return elapsed >= self._session_duration_minutes

async def _rotate_tracking_session(self):
    """Complete the current session and start a new one."""
    await vmeta_client.complete_tracking_session(
        session_uuid=self.current_session_uuid
    )
    self.current_session_uuid = str(uuid.uuid4())
    self._session_started_at = datetime.utcnow()
    await vmeta_client.create_tracking_session(
        session_uuid=self.current_session_uuid,
        camera_id=self._camera_id,
        source_type='instant_detection'
    )
```

### 7.4 Tracking session lifecycle

**Start detection** — `POST /instant-detection/start/{camera_id}`:

Add to the existing start handler:
```python
# Load per-camera pipeline settings
pipeline_settings = await camera_service.get_pipeline_settings(camera_id)

# Create tracking session for this detection run
session_uuid = str(uuid.uuid4())
await vmeta_client.create_tracking_session(
    session_uuid=session_uuid,
    camera_id=camera_id,
    source_type='instant_detection'
)
# Store state in sampler
sampler.current_session_uuid = session_uuid
sampler._session_started_at = datetime.utcnow()
sampler._storage_multiple = pipeline_settings.get('storage_multiple', 1)
sampler._session_duration_minutes = pipeline_settings.get('tracking_session_duration_minutes', 0)
sampler._cycle_counter = 0
```

**Each persisted cycle** — pass `session_uuid` to the persist task (only on cycles where `cycle_counter % storage_multiple == 0`).

**Session rotation** — when `tracking_session_duration_minutes > 0` and the duration elapses, the current session is completed and a new one created automatically (see `_rotate_tracking_session` above).

**Stop detection** — `POST /instant-detection/stop/{camera_id}`:

Add to the existing stop handler:
```python
await vmeta_client.complete_tracking_session(
    session_uuid=sampler.current_session_uuid
)
```

### 7.5 Integration point in existing code

In `instant_detection.py` — after the existing result distribution (Redis cache, Pub/Sub, webhook, triggers), add the storage-multiple–gated persistence:

```python
# [EXISTING] Cache result
self._cache_result(camera_id, result)

# [EXISTING] Publish to Redis Pub/Sub
self._publish_to_redis_sync(camera_id, result)

# [EXISTING] Evaluate triggers
self._evaluate_triggers_sync(camera_id, result)

# [NEW] Persist to database (async, non-blocking, governed by storage_multiple)
self._cycle_counter += 1
if self._storage_multiple > 0 and self._cycle_counter % self._storage_multiple == 0:
    try:
        # Rotate session if duration exceeded
        if self._should_rotate_session():
            await self._rotate_tracking_session()
        
        persist_instant_detection_results.delay(
            camera_id=camera_id,
            session_uuid=self.current_session_uuid,
            cycle_timestamp=result["timestamp"],
            person_objects=result["person_objects"],
            demographics=result["demographics"],
            auth_token=self._auth_token
        )
    except Exception as e:
        logger.warning(f"Failed to submit persistence task: {e}")
        # Non-critical — detection continues without storage
```

The same addition applies to the Celery worker fallback path in `_submit_to_celery()`.

---

## 8. Frontend Changes

### 8.1 Pipeline settings screen — new controls

The camera pipeline settings screen (`CameraPipelineSettingsScreen`) at `http://localhost:3000/#/cameras` already exposes per-camera settings for `instant_detection_interval_seconds` and `segment_duration_seconds`. Two new controls are added in the same screen:

**Storage Multiple** — integer slider (1–12, default 1):

```dart
// New state variable
late int _storageMultiple;

// In _loadSettings():
_storageMultiple = pipelineSettings['storage_multiple'] as int? ?? 1;

// In build(), under the existing instant detection interval slider:
Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    const Text('Storage Multiple',
        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
    const SizedBox(height: 4),
    Text(
      'Persist detection results to database every '
      '${_storageMultiple * _instantDetectionInterval} seconds '
      '(${_storageMultiple}× detection interval)',
      style: const TextStyle(fontSize: 14, color: Colors.grey),
    ),
    Slider(
      value: _storageMultiple.toDouble(),
      min: 1,
      max: 12,
      divisions: 11,
      label: '${_storageMultiple}× ($_storageMultiple * $_instantDetectionInterval}s)',
      onChanged: (v) => setState(() => _storageMultiple = v.round()),
    ),
  ],
),
```

**Tracking Session Duration** — integer slider (0–480 minutes, default 0):

```dart
late int _trackingSessionDurationMinutes;

// In _loadSettings():
_trackingSessionDurationMinutes = pipelineSettings['tracking_session_duration_minutes'] as int? ?? 0;

// In build():
Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    const Text('Tracking Session Duration',
        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
    const SizedBox(height: 4),
    Text(
      _trackingSessionDurationMinutes == 0
          ? 'Unlimited — one session per detection run'
          : 'New tracking session every $_trackingSessionDurationMinutes minutes',
      style: const TextStyle(fontSize: 14, color: Colors.grey),
    ),
    Slider(
      value: _trackingSessionDurationMinutes.toDouble(),
      min: 0,
      max: 480,
      divisions: 16,  // 0, 30, 60, 90, ... 480
      label: _trackingSessionDurationMinutes == 0
          ? 'Unlimited'
          : '${_trackingSessionDurationMinutes} min',
      onChanged: (v) => setState(() => _trackingSessionDurationMinutes = v.round()),
    ),
  ],
),
```

Both values are sent via `updatePipelineSettings()` alongside the existing fields.

### 8.2 Model changes

The `CameraPipelineSettings` model and `Camera` model gain two new fields:

```dart
// In CameraPipelineSettings:
final int storageMultiple;            // default 1
final int trackingSessionDurationMinutes;  // default 0 (unlimited)

// In Camera:
final int storageMultiple;
final int trackingSessionDurationMinutes;
```

JSON keys: `storage_multiple`, `tracking_session_duration_minutes`.

### 8.3 Service layer

`CameraService.updatePipelineSettings()` gains two new parameters:

```dart
Future<Map<String, dynamic>> updatePipelineSettings(
  String deviceId, {
  required bool instantDetectionEnabled,
  required bool recordingPipelineEnabled,
  required int instantDetectionIntervalSeconds,
  required int segmentDurationSeconds,
  required int storageMultiple,               // NEW
  required int trackingSessionDurationMinutes, // NEW
}) async { ... }
```

### 8.4 Analytics integration (optional enhancement)

Once instant detection data is persisted, the analytics module can include it. The gateway analytics endpoints already query `tracking_sessions` and `individuals`. Three optional improvements:

1. **Include instant detection in analytics counters**: The summary, demographics, and behavioral endpoints could include `source_type = 'instant_detection'` data. This requires no frontend changes — the UI will show higher totals automatically.

2. **Source type filter in analytics**: Add an optional toggle in the filter dialog: "Include instant detection data" (default: true). This would pass a `source_types` query param to the backend, allowing users to view recording-only or combined analytics.

3. **Individual detail view**: Individuals created from instant detection could show a badge: "Detected via instant detection" alongside their appearance history.

---

## 9. Migration Strategy

### Phase 1: Schema migration (non-breaking)

1. Apply the three ALTER TABLE migrations (new columns with defaults).
2. Existing rows get `source_type = 'recording_pipeline'` via DEFAULT.
3. All existing queries continue to work unchanged — no WHERE clause filtering on `source_type` is needed initially.

### Phase 2: Backend deployment

1. Deploy the new Celery task and VMeta persist endpoint.
2. Update instant detection start/stop handlers to manage tracking sessions.
3. Add the `persist_instant_detection_results.delay()` call to the detection pipeline.
4. Monitor for any performance impact on the 5-second cycle.

### Phase 3: Backfill isolated MVR entries (optional)

Existing isolated MVR records (created by previous instant detection runs) can be optionally backfilled:

```sql
-- Count isolated MVR entries without individuals
SELECT COUNT(*) FROM mvr_people 
WHERE is_isolated = TRUE AND featured_individual_uuid IS NULL;
```

A one-time migration script could:
1. For each isolated MVR, create an Individual with `source_type = 'instant_detection'`.
2. Create an `individual_mvr_mapping` with `link_method = 'instant_detection'`.
3. Set `featured_individual_uuid` and flip `is_isolated = FALSE`.

This is optional — new detections will be correctly stored going forward regardless.

### Phase 4: Analytics integration

Update analytics gateway endpoints to include `source_type = 'instant_detection'` data in their aggregation queries.

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Storage slows detection cycle** | Low | High | Persist task is fully async via Celery. The detection loop submits and moves on. Even if the task queue backs up, detection continues at 5-second intervals. |
| **Database write volume** | Medium | Medium | With default `storage_multiple=1` at 5-second intervals with ~2 people: ~24 appearances/hour/camera. With `storage_multiple=6`: ~4 appearances/hour/camera. The storage multiple gives operators direct control over write volume. With 5 cameras running 8 hours at default settings, that's ~960 appearances per day — comparable to the recording pipeline and manageable for PostgreSQL. |
| **Duplicate individuals** | Medium | Low | If the same person is seen in consecutive cycles (every 5 seconds), they will match the same MVR entry and reuse the same Individual — no duplication. The `individual_video_appearances` table will have multiple rows with different timestamps, which is correct (it's an appearance log). |
| **Embedding dimensionality mismatch** | Low | Low | Vision returns 128-dim embeddings; the schema uses 512-dim. The persist endpoint does not need to store the Vision embedding — identity resolution via `identify-face` already handles the 512-dim embedding internally. If we need to store `appearance_features` on the Individual, we can either zero-pad or call VMeta's ML processor. Initial implementation can leave `appearance_features` NULL for instant detection individuals. |
| **Synthetic video UUID collisions** | Very Low | Low | UUID v5 is deterministic and namespaced. Two cameras at the exact same millisecond would still differ because `camera_id` is part of the input. |
| **Network partition to VMeta** | Low | Medium | If VMeta is unreachable, the persist task fails silently (max 1 retry). Results are still cached in Redis for the frontend. The next successful cycle will store its data normally. No data corruption occurs. |
| **Analytics double-counting** | Medium | Medium | If both the recording pipeline and instant detection are running simultaneously on the same camera, the same person could be counted in both. Mitigation: analytics queries can deduplicate by `mvr_people_uuid` across source types, only counting each MVR person once. |

---

## 11. Alternatives Considered

### Alternative A: Dedicated `instant_detection_results` table

Create a new flat table storing one row per detection cycle with JSON blobs for person objects and demographics.

**Pros:**
- Simple — one INSERT per cycle
- No changes to existing tables
- Easy to query for instant detection history

**Cons:**
- Does not integrate with analytics (separate query paths needed)
- MVR people remain isolated — no identity graph benefits
- Duplicates the Individual/Appearance data model
- Cannot participate in cross-video merging or individual groups

**Verdict:** Rejected. The primary value of storage is integration with the existing identity and analytics systems. A standalone table would be a data silo.

### Alternative B: Use existing `process-media` endpoint

Submit instant detection results to `/api/v1/mvr-people/process-media` as if they were video results.

**Pros:**
- Reuses existing processing pipeline entirely
- Full MVR creation and merging happens automatically

**Cons:**
- `process-media` expects video UUIDs and full segment data
- It runs expensive re-processing (FaceNet, clustering) that was already done
- It's synchronous and heavy — not suitable for a 5-second cycle
- Significant adaptation required to accept frame-based input

**Verdict:** Rejected. Too heavy and wrong abstraction level. The ML processing has already been done during the detection cycle.

### Alternative C: Store only in Redis with longer TTL

Extend Redis TTL from 5 minutes to 24 hours and build analytics queries directly on Redis.

**Pros:**
- No database changes
- Very fast writes

**Cons:**
- Redis is not a durable store — data is lost on restart
- No SQL querying for analytics aggregation
- No identity graph integration
- Memory consumption grows unbounded

**Verdict:** Rejected. Not suitable for persistent analytics data.

### Alternative D: Write directly from the Cameras service to VMeta DB

Skip the API layer and have the Cameras service write directly to the VMeta PostgreSQL database.

**Pros:**
- Lowest latency
- No network hop for persistence

**Cons:**
- Violates service boundary (Cameras service should not know VMeta's schema)
- Tight coupling makes schema changes risky
- Bypasses VMeta's business logic (merge checking, dedup)
- Connection pool management across services

**Verdict:** Rejected. Breaks microservice architecture.

---

## 12. Implementation Plan

### Milestone 1: Schema migration
- [ ] Write SQL migration for `tracking_sessions.source_type` and `tracking_sessions.camera_device_id`
- [ ] Write SQL migration for `individuals.source_type`
- [ ] Write SQL migration for `individual_mvr_mapping.link_method` expanded CHECK
- [ ] Test migrations against development database
- [ ] Verify existing queries are not broken (all defaults are backward-compatible)

### Milestone 2: VMeta persist endpoint
- [ ] Create Pydantic request/response models for `InstantDetectionPersistRequest`
- [ ] Implement `POST /api/v1/instant-detection/persist` in VMeta
- [ ] Individual find-or-create logic with MVR linking
- [ ] Synthetic video UUID generation
- [ ] Appearance record creation
- [ ] Tracking session update logic
- [ ] Unit tests for all code paths (matched MVR, new MVR, legacy isolated MVR, no MVR)

### Milestone 3: Frontend — pipeline settings UI
- [ ] Add `storageMultiple` and `trackingSessionDurationMinutes` fields to `CameraPipelineSettings` model
- [ ] Add `storageMultiple` and `trackingSessionDurationMinutes` fields to `Camera` model
- [ ] Add Storage Multiple slider to `CameraPipelineSettingsScreen`
- [ ] Add Tracking Session Duration slider to `CameraPipelineSettingsScreen`
- [ ] Update `CameraService.updatePipelineSettings()` to send new fields
- [ ] Validate slider ranges (storage multiple 1–12, session duration 0–480)

### Milestone 4: Cameras service integration
- [ ] Read `storage_multiple` and `tracking_session_duration_minutes` from pipeline settings on detection start
- [ ] Add `_cycle_counter` and storage-multiple gating logic
- [ ] Add tracking session creation on detection start
- [ ] Add tracking session rotation when duration elapses
- [ ] Add tracking session completion on detection stop
- [ ] Create `persist_instant_detection_results` Celery task
- [ ] Wire task submission into `_process_3_frames()` result distribution
- [ ] Wire task submission into Celery worker fallback path
- [ ] Verify detection cycle timing is not impacted (benchmark loop)

### Milestone 5: Analytics integration
- [ ] Update gateway analytics endpoints to include `source_type = 'instant_detection'` tracking sessions
- [ ] Deduplicate MVR people counts across source types
- [ ] Optional: add source type filter to analytics filter dialog

### Milestone 6: Backfill and cleanup
- [ ] Write backfill script for existing isolated MVR entries
- [ ] Document the new data flow in the Instant Detection module docs
- [ ] Update the Analytics module docs

---

## Appendix A: Volume Estimates

**Assumptions:**
- 3 cameras running instant detection
- 8 hours/day active detection
- Average 2 people per cycle
- 5-second cycle interval

### With `storage_multiple = 1` (default — persist every cycle)

| Metric | Per camera/day | Total/day (3 cameras) | Total/month |
|--------|---------------|----------------------|-------------|
| Detection cycles | 5,760 | 17,280 | ~518,000 |
| **Persisted cycles** | **5,760** | **17,280** | **~518,000** |
| Tracking sessions (unlimited duration) | ~2 | ~6 | ~180 |
| Individual appearances (rows) | ~11,520 | ~34,560 | ~1,037,000 |
| Unique individuals (via MVR dedup) | ~50–200 | ~150–600 | ~4,500–18,000 |
| MVR records (new) | ~10–50 | ~30–150 | ~900–4,500 |

### With `storage_multiple = 6` (persist every 30 seconds)

| Metric | Per camera/day | Total/day (3 cameras) | Total/month |
|--------|---------------|----------------------|-------------|
| Detection cycles | 5,760 | 17,280 | ~518,000 |
| **Persisted cycles** | **960** | **2,880** | **~86,400** |
| Tracking sessions (60 min duration) | ~8 | ~24 | ~720 |
| Individual appearances (rows) | ~1,920 | ~5,760 | ~172,800 |
| Unique individuals (via MVR dedup) | ~50–200 | ~150–600 | ~4,500–18,000 |
| MVR records (new) | ~10–50 | ~30–150 | ~900–4,500 |

### With `storage_multiple = 12` (persist every 60 seconds)

| Metric | Per camera/day | Total/day (3 cameras) | Total/month |
|--------|---------------|----------------------|-------------|
| Detection cycles | 5,760 | 17,280 | ~518,000 |
| **Persisted cycles** | **480** | **1,440** | **~43,200** |
| Tracking sessions (60 min duration) | ~8 | ~24 | ~720 |
| Individual appearances (rows) | ~960 | ~2,880 | ~86,400 |
| Unique individuals (via MVR dedup) | ~50–200 | ~150–600 | ~4,500–18,000 |
| MVR records (new) | ~10–50 | ~30–150 | ~900–4,500 |

Note: Unique individuals and MVR records are unaffected by `storage_multiple` — the same people are detected regardless; only the number of logged appearances changes.

The appearance table is the highest-volume table. At default settings (~1M rows/month for 3 cameras) PostgreSQL handles this comfortably; standard BRIN or B-tree indexes on `start_timestamp` keep queries fast. Increasing `storage_multiple` to 6 reduces this to ~173K rows/month — a 6× reduction. A retention policy (e.g., drop appearances older than 90 days) can cap growth further.

---

## Appendix B: Sequence Diagram

```
Eye Button (Start)          Cameras Service               VMeta Service
     │                           │                              │
     │  POST /start/{cam}        │                              │
     ├──────────────────────────►│                              │
     │                           │  POST /tracking-sessions     │
     │                           ├─────────────────────────────►│
     │                           │  ◄── session_uuid ──────────┤
     │                           │                              │
     │                           │ ┌─── detection loop ─────┐  │
     │                           │ │                         │  │
     │                           │ │ Capture 3 frames        │  │
     │                           │ │ Vision → detect faces   │  │
     │                           │ │ Orchestrator → group    │  │
     │                           │ │ VMeta → age/gender      │  │
     │                           │ │ VMeta → identify-face   │  │
     │                           │ │                         │  │
     │                           │ │ Cache in Redis ✅        │  │  ← every cycle
     │                           │ │ Pub/Sub broadcast ✅     │  │  ← every cycle
     │                           │ │ Trigger evaluate ✅      │  │  ← every cycle
     │                           │ │                         │  │
     │                           │ │ cycle++ % multiple == 0? │  │
     │                           │ │   YES → Celery task ────┼──┤  ← every Nth cycle
     │                           │ │  persist_results.delay() │  │
     │                           │ │                         │  │  POST /instant-detection/persist
     │                           │ │                         │  ├──────────────────────────────────►
     │                           │ │                         │  │  Upsert individual
     │                           │ │                         │  │  Create appearance
     │                           │ │                         │  │  Link MVR mapping
     │                           │ │                         │  │  Update session stats
     │                           │ │  (check session rotate)  │  │  (rotate session if duration met)
     │                           │ │                         │  │◄── { stored: 2 } ─────────────────
     │                           │ │   NO → skip storage     │  │
     │                           │ │                         │  │
     │                           │ └─── repeat every Ns ────┘  │
     │                           │                              │
Eye Button (Stop)               │                              │
     │  POST /stop/{cam}        │                              │
     ├──────────────────────────►│                              │
     │                           │  PATCH /tracking-sessions    │
     │                           ├─────────────────────────────►│
     │                           │   status=completed           │
     │                           │  ◄── OK ────────────────────┤
```
