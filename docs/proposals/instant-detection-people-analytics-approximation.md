# Instant Detection Peopple Analytics Apporximation

**Proposal Version**: 1.0  
**Date**: May 10, 2026  
**Status**: Draft  
**Author**: Engineering  

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current Stored Data](#current-stored-data)
3. [Goal](#goal)
4. [Proposed Endpoint](#proposed-endpoint)
5. [Approximation Algorithm](#approximation-algorithm)
6. [Data Model Used By The Algorithm](#data-model-used-by-the-algorithm)
7. [Response Shape](#response-shape)
8. [Durable Batching Design](#durable-batching-design)
9. [Implementation Plan](#implementation-plan)
10. [Risks and Limitations](#risks-and-limitations)
11. [Testing From The Database](#testing-from-the-database)
12. [Acceptance Criteria](#acceptance-criteria)

---

## Problem Statement

Instant detection now persists normalized records into the VMeta schema, but there is no API that answers the analytics question:

"Approximately how many unique people did a camera see via instant detection over a given time range?"

This is not the same as counting persisted rows:

- `individual_video_appearances` can contain repeated sightings of the same real-world person across adjacent instant-detection cycles.
- `individuals` created by instant detection are useful identity records, but they do not by themselves collapse near-duplicate sightings that should be treated as one approximate visitor for analytics.
- Instant detection persistence stores limited per-sighting geometry, so approximation must work from the data that is actually stored today rather than from the original in-memory frame payload.

The result should be an approximation endpoint intended for analytics and reporting, not for identity-grade person tracking.

---

## Current Stored Data

The current persistence flow writes the following instant-detection artefacts:

- `tracking_sessions`
  - `source_type = 'instant_detection'`
  - `camera_device_id`
  - `started_at`, `completed_at`
- `individuals`
  - `individual_uuid`
  - `source_type = 'instant_detection'`
  - `gender_estimate`
  - `age_estimate`
  - `first_seen`, `last_seen`
- `individual_video_appearances`
  - `individual_uuid`
  - `person_object_uuid`
  - `start_timestamp`, `end_timestamp`
  - `confidence`, `quality_score`
  - `source_session_uuid`
  - `representative_faces` JSON
- `individual_mvr_mapping`
  - optional link to `mvr_people_uuid`
  - `link_method = 'instant_detection'`

Important constraint: the persisted `representative_faces` JSON currently stores only bounding box and confidence for the best face. It does not store full face embeddings, the full per-frame bbox history, or the complete MVR object.

Example of what is effectively available per appearance:

```json
{
  "bbox": [245, 180, 345, 280],
  "confidence": 0.92
}
```

That means the approximation endpoint must operate primarily on:

- timestamp proximity
- bbox center proximity
- bbox size similarity
- optional MVR link reuse when present
- persisted age and gender estimates

---

## Goal

Provide an endpoint that, for a camera and time range:

1. Loads persisted instant-detection sightings from the database.
2. Groups nearby sightings that likely represent the same real-world person.
3. Returns an approximate unique-people count.
4. Returns grouped person summaries suitable for analytics.
5. Derives group demographics as:
   - age = average age of grouped members
   - gender = dominant gender of grouped members

The endpoint should explicitly communicate that the result is approximate and heuristic.

---

## Proposed Endpoint

### Route

```http
GET /api/v1/instant-detection/approx-people
```

Recommended home: VMeta service, because the required data already lives in the VMeta database and the endpoint is analytical rather than camera-control oriented.

The Gateway may proxy it later if frontend exposure is needed.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `camera_id` | string | Yes | Camera device identifier stored in `tracking_sessions.camera_device_id` |
| `start_time` | ISO datetime | Yes | Inclusive lower bound |
| `end_time` | ISO datetime | Yes | Inclusive upper bound |
| `time_window_seconds` | integer | No | Max allowed timestamp gap for grouping, default `12` |
| `center_distance_px` | integer | No | Max bbox-center distance in pixels, default `120` |
| `size_ratio_tolerance` | float | No | Allowed relative face-size difference, default `0.35` |
| `min_confidence` | float | No | Ignore weak sightings below this confidence, default `0.50` |
| `use_mvr_hint` | boolean | No | When true, prefer grouping records sharing the same `mvr_people_uuid`, default `true` |
| `include_members` | boolean | No | Whether to include the underlying grouped appearance members, default `false` |

### Example Request

```http
GET /api/v1/instant-detection/approx-people?camera_id=usb_camera_04&start_time=2026-05-10T09:00:00Z&end_time=2026-05-10T11:00:00Z
```

---

## Approximation Algorithm

### Overview

The endpoint should load all instant-detection appearances for the requested camera and time range, sort them by timestamp, then cluster them into approximate people using the following evidence:

1. timestamp proximity
2. bbox center proximity
3. face size similarity
4. optional exact MVR identity match as a strong hint

This is a greedy temporal-spatial clustering pass, not a full tracking model.

### Input Record Shape

Each persisted sighting is normalized into this working structure:

```json
{
  "individual_uuid": "...",
  "person_object_uuid": "...",
  "mvr_people_uuid": "... or null",
  "timestamp": "2026-05-10T09:15:02Z",
  "confidence": 0.91,
  "age_estimate": 31,
  "gender_estimate": "Male",
  "bbox": [245, 180, 345, 280]
}
```

Derived geometry:

- `width = x2 - x1`
- `height = y2 - y1`
- `area = width * height`
- `center_x = (x1 + x2) / 2`
- `center_y = (y1 + y2) / 2`

### Grouping Rules

Two sightings should be considered eligible for the same approximate person when all of the following are true:

1. `abs(timestamp_a - timestamp_b) <= time_window_seconds`
2. Euclidean distance between bbox centers is `<= center_distance_px`
3. Relative face-size difference is within `size_ratio_tolerance`

Recommended size comparison:

```text
size_delta = abs(area_a - area_b) / max(area_a, area_b)
```

And the pair is eligible when:

```text
size_delta <= size_ratio_tolerance
```

### MVR-Assisted Rule

If `use_mvr_hint = true` and two sightings share the same non-null `mvr_people_uuid`, then grouping may accept a wider temporal window, for example:

- `time_window_seconds * 3`

But spatial checks should still be applied so that the endpoint does not over-collapse unrelated detections simply because the identity system reused an MVR record.

### Greedy Clustering Strategy

Recommended first version:

1. Sort candidate sightings by timestamp ascending.
2. Iterate sighting by sighting.
3. Attempt to place the sighting into the most recent compatible cluster.
4. If multiple clusters are compatible, choose the one with the lowest weighted distance score.
5. If no compatible cluster exists, start a new cluster.

Suggested score:

```text
score =
    time_gap_seconds / time_window_seconds
  + center_distance / center_distance_px
  + size_delta / size_ratio_tolerance
```

Lower score is better.

### Group Demographics

For each cluster, produce analytics fields as follows.

#### Approximate Age

Use the arithmetic mean of all non-null member `age_estimate` values.

```text
group_age = round(avg(member.age_estimate))
```

If there are no non-null member ages, return `null`.

#### Approximate Gender

Use the dominant gender among non-null member `gender_estimate` values.

Rules:

1. Normalize values to `male`, `female`, `unknown`.
2. Count frequency per normalized gender.
3. Choose the highest-frequency label.
4. If there is a tie, choose the label with higher summed confidence if available.
5. If still tied or no gender values exist, return `unknown`.

### Group Representative Geometry

For the grouped person result, use:

- first seen = min member timestamp
- last seen = max member timestamp
- representative bbox = bbox from the highest-confidence member
- average bbox area = mean member area
- detection count = number of grouped sightings

---

## Data Model Used By The Algorithm

### Proposed SQL Source Query

```sql
SELECT
    ts.camera_device_id,
    iva.source_session_uuid,
    iva.individual_uuid,
    iva.person_object_uuid,
    iva.start_timestamp,
    iva.end_timestamp,
    iva.confidence,
    iva.quality_score,
    iva.representative_faces,
    i.age_estimate,
    i.gender_estimate,
    imm.mvr_people_uuid
FROM individual_video_appearances iva
JOIN tracking_sessions ts
  ON ts.session_uuid = iva.source_session_uuid
JOIN individuals i
  ON i.individual_uuid = iva.individual_uuid
LEFT JOIN individual_mvr_mapping imm
  ON imm.individual_uuid = iva.individual_uuid
WHERE ts.source_type = 'instant_detection'
  AND i.source_type = 'instant_detection'
  AND ts.camera_device_id = $1
  AND iva.start_timestamp >= $2
  AND iva.start_timestamp <= $3
ORDER BY iva.start_timestamp ASC;
```

### Notes

- `tracking_sessions.camera_device_id` is the authoritative camera filter.
- `individual_video_appearances.representative_faces` supplies bbox data.
- `individuals.age_estimate` and `individuals.gender_estimate` supply demographics.
- `individual_mvr_mapping.mvr_people_uuid` is optional and should be treated as a hint rather than the sole merge key.

---

## Response Shape

```json
{
  "success": true,
  "camera_id": "usb_camera_04",
  "start_time": "2026-05-10T09:00:00Z",
  "end_time": "2026-05-10T11:00:00Z",
  "approx_unique_people": 7,
  "total_sightings": 23,
  "parameters": {
    "time_window_seconds": 12,
    "center_distance_px": 120,
    "size_ratio_tolerance": 0.35,
    "min_confidence": 0.5,
    "use_mvr_hint": true
  },
  "people": [
    {
      "approx_person_id": "approx_001",
      "first_seen": "2026-05-10T09:03:10Z",
      "last_seen": "2026-05-10T09:03:18Z",
      "detection_count": 3,
      "age": 29,
      "gender": "male",
      "representative_bbox": [244, 180, 343, 278],
      "avg_face_area": 10120.7,
      "mvr_people_uuid": "optional-if-consistent",
      "member_person_object_uuids": [
        "...",
        "...",
        "..."
      ]
    }
  ]
}
```

Response notes:

- `approx_unique_people` is the count of final clusters.
- `total_sightings` is the raw number of persisted instant-detection appearances considered.
- `mvr_people_uuid` should only be surfaced at group level when every member shares the same non-null MVR UUID.

---

## Durable Batching Design

### Why batching is needed

The current flow can enqueue a persistence task on every eligible instant-detection cycle:

```python
persist_instant_detection_results.delay(
    camera_id=camera_id,
    session_uuid=state.session_uuid,
    cycle_timestamp=result.get("timestamp", ...),
    person_objects=person_objects,
    demographics=result.get("demographics", {}),
    auth_token=state.auth_token or "",
)
```

That is acceptable at low camera counts, but it does not scale cleanly when many cameras run at a 5-second interval. The write load grows linearly with:

- number of active cameras
- persistence frequency (`storage_multiple`)
- number of people detected per cycle

Because the approximation endpoint is analytics-oriented, we should not treat each Celery task execution as the final write boundary. We should instead buffer results durably and flush them in batches.

### Design goals

The batching design must:

1. remain durable across worker restarts
2. preserve the full instant-detection analytics payload, including age and gender
3. reduce write amplification on the main normalized analytics tables
4. keep the frontend real-time counter unchanged
5. support replay and recovery if the downstream VMeta write path fails

### Non-goal

Do not buffer only in Celery worker memory. Worker RAM is not durable and should not be the system of record for results that may be needed later for analytics.

### Recommended architecture

Use a two-stage durable write path:

1. **Realtime path** — unchanged
   - Cameras service continues to compute live `person_objects` and `demographics`
   - Results continue to be cached in Redis and served to the frontend counter immediately
2. **Durable batch path** — new
   - Each eligible detection cycle writes a compact raw payload to a durable batch buffer
   - A periodic flusher drains the buffer and writes batches to VMeta in one transaction or a small number of transactions

### Recommended durable buffer

Use Redis as the first durable buffer, not Celery worker memory.

Per camera, store each eligible cycle as an append-only batch item in a Redis list or stream:

```text
instant_detection_batch:{camera_id}
```

Each item represents one persisted instant-detection cycle.

Redis is preferred over worker memory because:

- it survives worker process restarts
- it is already part of the instant-detection architecture
- it supports time-based and count-based flushing
- it allows a separate flusher worker to own the final database writes

If stronger operational guarantees are needed later, the same contract can be moved to a Postgres staging table without changing the analytics endpoint shape.

### Batch item payload

Each durable batch item should preserve both the current result data and the age/gender data already present in realtime results.

Recommended payload:

```json
{
  "camera_id": "usb_camera_04",
  "tracking_session_uuid": "...",
  "cycle_timestamp": "2026-05-10T09:15:02Z",
  "people_count": 2,
  "demographics": {
    "total_male": 1,
    "total_female": 1,
    "total_unknown_gender": 0,
    "percent_male": 50.0,
    "percent_female": 50.0,
    "total_young": 0,
    "total_adult": 2,
    "total_unknown_age": 0,
    "percent_young": 0.0,
    "percent_adult": 100.0
  },
  "person_objects": [
    {
      "person_object_uuid": "...",
      "mvr_person_uuid": "...",
      "avg_confidence": 0.94,
      "face_count": 3,
      "best_face": {
        "bbox": [245, 180, 345, 280],
        "confidence": 0.92
      },
      "age_gender": {
        "age_min": 25,
        "age_max": 32,
        "age_confidence": 0.78,
        "gender": "Male",
        "gender_confidence": 0.91
      }
    }
  ]
}
```

This is the critical point: the durable batch payload must carry the per-person `age_gender` block and the top-level `demographics` block exactly because the live frontend counter already depends on those values and analytics consumers will need them later.

### Flush policy

Flush to VMeta when any of these conditions is met:

1. **Count threshold** — for example every 10 cycle payloads per camera
2. **Time threshold** — for example every 30 seconds per camera
3. **Session boundary** — when instant detection stops for a camera
4. **Session rotation** — when `tracking_session_duration_minutes` rolls over

This produces a predictable upper bound on write delay without requiring a database write every 5 seconds.

### Flush worker responsibilities

The flusher should:

1. read a batch of cycle payloads from the durable Redis buffer
2. merge them into a single persistence request or a small number of requests
3. write all rows in one transaction on the VMeta side
4. acknowledge and remove the batch items only after a successful write
5. leave the items in Redis for retry if the write fails

### VMeta-side write model

Instead of writing each cycle independently to `tracking_sessions`, `individuals`, and `individual_video_appearances`, the flusher should write:

1. one tracking-session update per camera batch
2. one insert per new appearance record
3. one upsert per individual aggregate record
4. one upsert per individual-to-MVR link
5. optional insertion into a new raw batch table for audit and replay

### Recommended schema addition

Add a new raw staging table that preserves the exact durable batch payload before normalized fan-out:

```sql
CREATE TABLE instant_detection_cycle_batches (
    batch_uuid UUID PRIMARY KEY,
    camera_id VARCHAR(100) NOT NULL,
    tracking_session_uuid UUID NOT NULL,
    cycle_timestamp TIMESTAMP NOT NULL,
    source_payload JSONB NOT NULL,
    people_count INTEGER NOT NULL,
    flushed_to_analytics BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    flushed_at TIMESTAMP NULL
);
```

Why this helps:

- preserves the full raw cycle payload, including age/gender and demographics
- allows replay if normalized writes fail or schema changes later
- gives analytics a durable source of truth closer to the real-time result stream
- decouples ingestion durability from the normalized reporting model

### Age and gender handling in the batch design

Age and gender must be preserved in two forms:

1. **Per-person form**
   - stored inside each raw cycle payload under `person_objects[*].age_gender`
   - used later for grouped-person approximation
2. **Per-cycle aggregated form**
   - stored inside each raw cycle payload under `demographics`
   - used for real-time counters, trend charts, and coarse analytics

Recommended normalized mapping after flush:

- `person_objects[*].age_gender.age_min` and `age_max` become either:
  - explicit fields on a raw sightings table, or
  - derived `age_estimate = round((age_min + age_max) / 2)` on the normalized individual/appearance row
- `person_objects[*].age_gender.gender` becomes a normalized persisted gender estimate field
- top-level `demographics` remains stored in the raw JSON payload so cycle-level summaries are preserved without recomputation

### Why this is better than Celery-memory batching

Batching in worker RAM would lose the exact age/gender results if:

- a worker is restarted
- a deploy happens mid-batch
- a task crashes after consuming but before flushing

Batching in Redis or a staging table keeps the exact per-cycle demographics and per-person age/gender values durable until the final write succeeds.

### Interaction with the approximation endpoint

The approximation endpoint should ultimately read from normalized persisted rows, but the durable batch design gives a safer migration path:

1. short term: continue approximation from normalized rows where available
2. medium term: if normalized age/gender columns are missing, backfill them from raw durable batch payloads
3. long term: keep raw payloads available for re-aggregation, auditing, and improved clustering algorithms

### Operational defaults

Recommended first defaults:

| Setting | Default | Reason |
|---------|---------|--------|
| `storage_multiple` | `1` | preserve current behavior for eligibility |
| `batch_flush_count` | `10` cycles | small enough for low latency |
| `batch_flush_seconds` | `30` seconds | bounded delay |
| `batch_max_retry_attempts` | `5` | resilient but finite |
| `raw_batch_retention_days` | `14` | enough for debugging and replay |

### Rollout plan

1. keep current live frontend counter unchanged
2. add durable raw cycle buffering in Redis
3. add a flusher task that writes raw batch rows plus normalized rows
4. add persisted age/gender columns where needed on the analytics side
5. switch the approximation endpoint to prefer normalized persisted age/gender and fall back to raw batch payloads if needed

---

## Implementation Plan

### 1. New VMeta analytics endpoint

Add a new route in the VMeta service, for example:

- `ppl-meta-vmeta/src/api/v1/instant_detection_analytics.py`

The handler should:

1. validate request parameters
2. execute the source query
3. parse `representative_faces`
4. normalize rows into working sightings
5. run the clustering pass
6. return grouped analytics output

### 2. Repository helper

Add a repository method that loads persisted instant-detection appearances by camera and time range.

This keeps SQL isolated and makes the algorithm testable separately from the API.

### 3. Pure service-layer clustering function

Add a service module, for example:

- `ppl-meta-vmeta/src/services/instant_detection_approximation.py`

Core functions:

- `load_candidate_sightings(...)`
- `normalize_bbox(...)`
- `is_compatible(existing_cluster, sighting, params)`
- `score_candidate_cluster(existing_cluster, sighting, params)`
- `cluster_sightings(...)`
- `summarize_cluster(...)`

### 4. Gateway proxy

Optional for first release. If frontend access is needed immediately, add a Gateway proxy route after the VMeta endpoint is stable.

### 5. Observability

Log these fields for each request:

- camera_id
- time range
- total input sightings
- resulting cluster count
- percentage collapse ratio
- parameter set used

This is important because the endpoint is heuristic and will need tuning against live data.

### 6. Durable batch ingestion

Add a new durable buffering step before normalized VMeta writes:

- Cameras service writes eligible cycle payloads to Redis batch buffers
- A dedicated flusher task drains Redis and writes raw batch rows plus normalized analytics rows
- Age/gender and top-level demographics are preserved in the raw batch payload

### 7. Persisted demographic compatibility

Because age/gender exists today in live instant-detection results but may not exist yet in the deployed analytics schema, the rollout should explicitly include:

- schema changes for persisted age/gender fields, or
- fallback reads from durable raw batch payload JSON until those columns exist

---

## Risks and Limitations

### 1. No full bbox history

Only one representative bbox is persisted per appearance. That limits motion-based grouping quality.

Impact:

- approximation can merge too aggressively when two people stand near each other
- approximation can split one person if face size changes sharply between cycles

### 2. No persisted embedding for instant-detection approximation

The current persisted path does not store a reusable face embedding for these appearance rows. That means the approximation cannot use cosine similarity or vector-based merge scoring.

### 3. Existing MVR reuse can over-merge

If the identity layer incorrectly reused an MVR person, blindly trusting `mvr_people_uuid` would over-collapse sightings. That is why MVR should be a hint, not a hard rule.

### 4. Raw-payload retention cost

Keeping durable raw cycle payloads with person-level age/gender and demographics increases Redis and database storage usage.

Mitigation:

- enforce retention windows
- compress payloads if needed
- keep only the minimal geometry and demographic fields required for replay

### 5. Camera movement changes geometry

If the camera moved or zoom changed during the time range, bbox-center and size heuristics will be less reliable.

### 6. This is analytics-grade, not identity-grade

The endpoint should be labelled as approximate in both API naming and UI wording.

---

## Testing From The Database

The goal of testing is to confirm that the approximation can be evaluated directly from persisted VMeta data for a recent instant-detection camera such as `USB 04` or `UBS 04`.

### Step 1. Find the recent instant-detection cameras

Run this query first to discover the exact stored camera identifier and confirm recent data exists:

```sql
SELECT
    camera_device_id,
    COUNT(*) AS session_count,
    MIN(started_at) AS first_seen,
    MAX(completed_at) AS last_seen
FROM tracking_sessions
WHERE source_type = 'instant_detection'
  AND started_at >= NOW() - INTERVAL '7 days'
GROUP BY camera_device_id
ORDER BY last_seen DESC NULLS LAST;
```

If the camera is referred to as `USB 04` in operations, use the returned `camera_device_id` that corresponds to that camera. If the exact ID is unknown, narrow it with:

```sql
SELECT DISTINCT camera_device_id
FROM tracking_sessions
WHERE source_type = 'instant_detection'
  AND camera_device_id ILIKE '%04%'
ORDER BY camera_device_id;
```

### Step 2. Inspect raw persisted sightings for that camera

Replace `usb_camera_04` with the discovered value.

```sql
SELECT
    iva.start_timestamp,
    iva.person_object_uuid,
    iva.confidence,
    i.age_estimate,
    i.gender_estimate,
    imm.mvr_people_uuid,
    iva.representative_faces
FROM individual_video_appearances iva
JOIN tracking_sessions ts
  ON ts.session_uuid = iva.source_session_uuid
JOIN individuals i
  ON i.individual_uuid = iva.individual_uuid
LEFT JOIN individual_mvr_mapping imm
  ON imm.individual_uuid = iva.individual_uuid
WHERE ts.source_type = 'instant_detection'
  AND ts.camera_device_id = 'usb_camera_04'
  AND iva.start_timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY iva.start_timestamp DESC
LIMIT 100;
```

This confirms the approximation endpoint has the minimum required source data:

- timestamp
- representative bbox
- age estimate
- gender estimate
- optional MVR UUID

### Step 3. Run a database-only approximation smoke test

This query does not implement the full application clustering logic, but it is useful for proving the concept directly in SQL by binning close timestamps and similar face sizes.

```sql
WITH raw AS (
    SELECT
        ts.camera_device_id,
        iva.person_object_uuid,
        iva.start_timestamp,
        iva.confidence,
        i.age_estimate,
        LOWER(COALESCE(i.gender_estimate, 'unknown')) AS gender_estimate,
        imm.mvr_people_uuid,
        ((iva.representative_faces::jsonb -> 0 -> 'bbox' ->> 0)::float) AS x1,
        ((iva.representative_faces::jsonb -> 0 -> 'bbox' ->> 1)::float) AS y1,
        ((iva.representative_faces::jsonb -> 0 -> 'bbox' ->> 2)::float) AS x2,
        ((iva.representative_faces::jsonb -> 0 -> 'bbox' ->> 3)::float) AS y2
    FROM individual_video_appearances iva
    JOIN tracking_sessions ts
      ON ts.session_uuid = iva.source_session_uuid
    JOIN individuals i
      ON i.individual_uuid = iva.individual_uuid
    LEFT JOIN individual_mvr_mapping imm
      ON imm.individual_uuid = iva.individual_uuid
    WHERE ts.source_type = 'instant_detection'
      AND ts.camera_device_id = 'usb_camera_04'
      AND iva.start_timestamp >= NOW() - INTERVAL '2 hours'
      AND iva.representative_faces IS NOT NULL
), enriched AS (
    SELECT
        *,
        (x2 - x1) AS face_width,
        (y2 - y1) AS face_height,
        ((x1 + x2) / 2.0) AS center_x,
        ((y1 + y2) / 2.0) AS center_y,
        ((x2 - x1) * (y2 - y1)) AS face_area,
        FLOOR(EXTRACT(EPOCH FROM start_timestamp) / 12) AS time_bucket
    FROM raw
), grouped AS (
    SELECT
        camera_device_id,
        time_bucket,
        COALESCE(mvr_people_uuid::text, 'no-mvr') AS mvr_bucket,
        ROUND(center_x / 120.0) AS center_x_bucket,
        ROUND(center_y / 120.0) AS center_y_bucket,
        ROUND(face_area / 5000.0) AS face_area_bucket,
        COUNT(*) AS detection_count,
        ROUND(AVG(age_estimate)) FILTER (WHERE age_estimate IS NOT NULL) AS avg_age,
        MODE() WITHIN GROUP (ORDER BY gender_estimate) AS dominant_gender,
        MIN(start_timestamp) AS first_seen,
        MAX(start_timestamp) AS last_seen
    FROM enriched
    GROUP BY
        camera_device_id,
        time_bucket,
        COALESCE(mvr_people_uuid::text, 'no-mvr'),
        ROUND(center_x / 120.0),
        ROUND(center_y / 120.0),
        ROUND(face_area / 5000.0)
)
SELECT *
FROM grouped
ORDER BY first_seen DESC;
```

What this smoke test gives you:

- an approximate grouped count directly from SQL
- average age per approximate person-group
- dominant gender per approximate person-group
- a quick way to compare SQL grouping against the future API output

What it does not give you:

- the full greedy compatibility scoring proposed for the service implementation
- optimal clustering across bucket boundaries

### Step 4. Expected API-vs-database validation

For a chosen camera and time range:

1. run the raw-sightings query
2. run the SQL smoke-test grouping
3. call the proposed API endpoint with the same range
4. compare:
   - raw sighting count
   - approximate unique count
   - first/last seen windows
   - average ages
   - dominant genders

Success means the API output is explainable from persisted rows and reasonably aligned with the SQL smoke-test approximation.

---

## Acceptance Criteria

1. A new endpoint returns approximate unique-people analytics for instant detection by camera and time range.
2. The endpoint operates only on currently persisted instant-detection database records.
3. Grouping uses timestamp proximity, bbox center proximity, and bbox size similarity.
4. Age for a grouped person is the average of member ages.
5. Gender for a grouped person is the dominant gender among members.
6. The response returns both raw sighting count and approximate grouped count.
7. The result can be reproduced approximately from SQL against a recent camera such as USB 04.
8. The endpoint is documented as approximate and heuristic, not exact identity resolution.
9. The durable batching design preserves per-person `age_gender` and per-cycle `demographics` without relying on Celery worker memory.
10. The durable batching design supports replay and recovery after flusher or worker failure.
