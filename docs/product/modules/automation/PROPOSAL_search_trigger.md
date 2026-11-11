# Proposal: Search Trigger Type

## Summary

Add a third trigger mode — `search` — that periodically queries **already-recorded camera data** via the existing vmeta `camera-search` endpoint, then publishes the results to the `instant-detection` Redis channel so the existing `InstantDetectionSubscriber` evaluates them using the same `demographic_conditions` or `ppl_match` criteria as the other trigger modes.

This proposal requires **no new camera endpoints** and **no new frame-capture logic**. It builds entirely on infrastructure that already exists:

| Existing asset | How search triggers use it |
|---|---|
| `POST /api/v1/individual-groups/{group_id}/camera-search` (vmeta) | Multi-camera MVR search against recorded collections — already supports `camera_ids[]`, time ranges, confidence thresholds, and returns demographics + matched individuals. |
| `GET /api/v1/media/collections/by-camera/{device_id}` (media) | Every camera already has a `MediaCollection`. Recorded videos are stored there. The camera-search endpoint resolves collections internally. |
| `Trigger.tracking_duration` (default `"10 minutes"`) | Already on the trigger model, stored but never consumed by runtime code. Search triggers use it as the lookback window. |
| `search_members_in_cameras()` (vmeta service) | Already handles multi-camera search with result merging and `mvr_person_uuid` deduplication. |
| `instant-detection` Redis channel + `InstantDetectionSubscriber` | Search results are published here in the standard event format; the existing subscriber evaluates conditions, checks cooldowns, fires actions, and logs — zero duplication. |

---

## Motivation

Current trigger modes are reactive: they fire only when the instant detection sampler is running on a camera and publishing events to Redis. This creates gaps:

1. **Searches over recorded data** — Instant detection only sees the current moment. A search trigger queries the camera's recorded collection over a configurable time window (`tracking_duration`), catching people who passed through during the lookback period.
2. **Multi-camera aggregate rules** — Existing triggers are scoped to a single `camera_device_id`. A search trigger can query multiple cameras' collections in one call and evaluate the merged results.
3. **Configurable frequency** — Instant detection runs every ~5 seconds. Some use cases (hourly occupancy checks, shift-change monitoring, periodic security sweeps) need coarser intervals without the overhead of continuous processing.
4. **No dependency on live sampling** — Instant detection requires the camera sampling thread to be running. A search trigger works against recorded data, so the camera only needs to be recording — not actively running the instant detection sampler.

---

## Design

### New Trigger Mode: `search`

Add `"search"` as a valid value for `Trigger.trigger_mode` alongside `"demographic"` and `"ppl_match"`.

### New Fields on the Trigger Model

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `search_camera_device_ids` | Text (JSON) | null | JSON array of camera device IDs to search — the user picks whichever cameras they want. Required when `trigger_mode = "search"`. |
| `search_interval_seconds` | Integer | `300` | How often the search executes (in seconds). Minimum: 30. |

### Existing Fields Now Consumed at Runtime

| Field | Already exists | How search triggers use it |
|-------|---------------|---------------------------|
| `tracking_duration` | Yes — `String(50)`, default `"10 minutes"` | **Lookback window.** Each search execution queries `[now - tracking_duration, now]`. For example, `"10 minutes"` means the search looks at the last 10 minutes of recorded data on each camera. |
| `demographic_conditions` | Yes | Evaluated against the demographics returned by the camera-search endpoint. |
| `ppl_match_group_id` | Yes | Passed as the `group_id` in the camera-search call. The vmeta endpoint already searches all group members against the camera collections. |
| `ppl_match_similarity_threshold` | Yes | Passed as `confidence_threshold` to the camera-search call. |
| `ppl_match_top_k` | Yes | Used to limit the matched individuals returned. |

**No separate evaluation mode or aggregation mode fields.** The search trigger reuses the same condition fields already on the Trigger model. The user picks cameras, sets an interval, and configures whichever criteria they want — exactly the same as the other trigger modes.

### Validation Rules

- When `trigger_mode = "search"`:
  - `search_camera_device_ids` must be a non-empty array of valid camera device IDs.
  - `search_interval_seconds` must be ≥ 30.
  - `ppl_match_group_id` is required — the camera-search endpoint needs a group to search against. Demographic conditions are optional and evaluated on the returned demographics.
- `camera_device_id` (the existing single-camera field) is **not required** for search triggers — `search_camera_device_ids` replaces it.

### Search Result Format

Each search execution transforms the vmeta camera-search response into the standard instant detection event format and **publishes it to the `instant-detection` Redis channel**:

```json
{
  "camera_id": "search:<trigger_uuid>",
  "timestamp": "2026-04-07T12:00:00.000000",
  "people_count": 12,
  "demographics": {
    "percent_male": 58.3,
    "percent_female": 41.7,
    "percent_age_0_12": 0.0,
    "percent_age_13_17": 8.3,
    "percent_age_18_24": 25.0,
    "percent_age_25_34": 33.3,
    "percent_age_35_44": 16.7,
    "percent_age_45_54": 8.3,
    "percent_age_55_64": 8.3,
    "percent_age_65_plus": 0.0
  },
  "source_mvr_uuids": ["uuid1", "uuid2", "uuid3"],
  "source": "search_trigger",
  "metadata": {
    "trigger_uuid": "<trigger_uuid>",
    "group_id": "<group_id>",
    "search_cameras": ["usb_camera_0", "rtsp_192.168.1.76_554"],
    "tracking_duration": "10 minutes",
    "time_range": ["2026-04-07T11:50:00Z", "2026-04-07T12:00:00Z"],
    "members_found": 4,
    "total_group_members": 10,
    "search_session_uuid": "<uuid>",
    "processing_time": 2.35
  }
}
```

**Mapping from camera-search response:**

| Camera-search field | Maps to |
|---|---|
| `matched_individuals[].mvr_person_uuid` | `source_mvr_uuids[]` |
| count of unique `matched_individuals` | `people_count` |
| `matched_individuals[].demographics` (aggregated) | `demographics` |
| `members_found` | `metadata.members_found` |
| `search_session_uuid` | `metadata.search_session_uuid` |

The `camera_id` is set to `search:<trigger_uuid>` so the existing subscriber matches it to the correct search trigger. The vmeta endpoint already handles multi-camera merging and `mvr_person_uuid` deduplication internally via `search_members_in_cameras()`.

---

## Execution Architecture

### Scheduler Component: `SearchTriggerScheduler`

A new class in `ppl-meta-media/src/services/search_trigger_scheduler.py`, following the same async loop pattern as `RecordingScheduler` in the Cameras service.

```
┌─────────────────────────────────────────────────────────────────┐
│  Media Service (startup)                                        │
│                                                                 │
│  lifespan():                                                    │
│    InstantDetectionSubscriber.start()   ← existing              │
│    SearchTriggerScheduler.start()       ← new                   │
└─────────────────────────────────────────────────────────────────┘

SearchTriggerScheduler._scheduler_loop():
  while running:
    1. Query DB: all active triggers where trigger_mode = "search"
    2. For each trigger, check: now >= last_fired_at + search_interval_seconds
       (or last_fired_at is None)
    3. If due → submit search task (Celery or inline async)
    4. Sleep(check_interval)  # e.g. 10 seconds
```

### Search Execution Flow (Redis-based)

```
SearchTriggerScheduler (Media service)
  │
  ├─ For each due search trigger:
  │   │
  │   ├─ Compute time window:
  │   │     end_time   = now
  │   │     start_time = now - parse(tracking_duration)
  │   │
  │   ├─ Call vmeta: POST /api/v1/individual-groups/{group_id}/camera-search
  │   │   {
  │   │     "camera_ids": trigger.search_camera_device_ids,
  │   │     "start_time": start_time,
  │   │     "end_time": end_time,
  │   │     "confidence_threshold": trigger.ppl_match_similarity_threshold
  │   │   }
  │   │
  │   ├─ Transform response → standard instant detection event format:
  │   │   ├─ Extract source_mvr_uuids from matched_individuals
  │   │   ├─ Aggregate demographics from matched individuals
  │   │   └─ Set camera_id = "search:<trigger_uuid>"
  │   │
  │   └─ Publish event to Redis "instant-detection" channel
  │
  └─ Sleep(check_interval)

InstantDetectionSubscriber (existing, already running)
  │
  ├─ Receives message from "instant-detection" channel
  ├─ Sees camera_id = "search:<trigger_uuid>"
  ├─ Queries active triggers matching that camera_id
  ├─ Evaluates using same pipeline:
  │   ├─ demographic_conditions → _evaluate_conditions()
  │   └─ ppl_match_* fields    → _evaluate_ppl_match()
  ├─ On pass: update last_fired_at, execute linked action, log
  └─ On fail: log with passed=False
```

This keeps the evaluation logic in **one place** (the existing subscriber) and means search triggers get cooldown checking, execution logging, and action dispatch for free.

### What the Scheduler Calls (existing endpoints — no new camera/vmeta endpoints needed)

**vmeta:** `POST /api/v1/individual-groups/{group_id}/camera-search`

Already implemented in `individual_groups.py`. Request:

| Parameter | Type | Source on Trigger |
|-----------|------|-------------------|
| `camera_ids` | `List[str]` | `search_camera_device_ids` |
| `start_time` | `datetime` | `now - parse(tracking_duration)` |
| `end_time` | `datetime` | `now` |
| `confidence_threshold` | `float` | `ppl_match_similarity_threshold` (default 0.5) |

Response (`GroupCameraSearchResponse`): `group_id`, `group_name`, `camera_ids`, `total_group_members`, `members_found`, `matched_individuals[]` (each with `individual_uuid`, `mvr_person_uuid`, `total_appearances`, `first_seen`, `last_seen`, `confidence_score`, `demographics`, `appearances`), `search_session_uuid`.

The vmeta endpoint internally:
1. Gets group members → normalizes through `mvr_merge_hierarchy` to super-individuals.
2. Gets video UUIDs from media service via `GET /api/v1/media/search?collection={camera_id}&start_time=...&end_time=...`.
3. Gets MVR people from those videos → normalizes camera MVR UUIDs.
4. Performs direct UUID matching (set intersection) + embedding similarity (top-3 per member × top-3 per camera, cosine).
5. For multi-camera: iterates over camera IDs, merges results by `mvr_person_uuid`.

### Demographics Aggregation from Search Results

The camera-search response includes per-individual demographics (age range, gender). The scheduler aggregates these into the standard percentages:

1. Collect unique `matched_individuals` (already deduplicated by vmeta for multi-camera).
2. `people_count` = count of unique individuals.
3. Map each individual's `demographics.gender` → `percent_male` / `percent_female`.
4. Map each individual's `demographics.age_range` (e.g. `"(25-35)"`) → granular age buckets (`percent_age_25_34`, etc.).
5. Calculate percentages from counts.

---

## Schema Changes

### Trigger Model Additions

```python
# In ppl-meta-media/src/models/trigger.py

search_camera_device_ids = Column(Text, nullable=True)       # JSON array
search_interval_seconds = Column(Integer, default=300)
```

Only two new columns. `tracking_duration` already exists and is finally consumed at runtime.

### Pydantic Schema Additions

```python
# In ppl-meta-media/src/schemas/trigger.py

class TriggerCreate(BaseModel):
    # ... existing fields ...
    trigger_mode: str = "demographic"  # "demographic" | "ppl_match" | "search"

    # Search-specific fields
    search_camera_device_ids: Optional[List[str]] = None
    search_interval_seconds: Optional[int] = Field(default=300, ge=30)

    @model_validator(mode="after")
    def validate_search_mode(self): 
        if self.trigger_mode == "search":
            if not self.search_camera_device_ids:
                raise ValueError("search_camera_device_ids required for search mode")
            if not self.ppl_match_group_id:
                raise ValueError(
                    "search mode requires ppl_match_group_id "
                    "(the group to search against camera collections)"
                )
        return self
```

### TriggerExecutionLog Additions

```python
# Additional field for search trigger audit trail
search_cameras_queried = Column(Text, nullable=True)   # JSON array of camera IDs queried
search_session_uuid = Column(String(255), nullable=True)  # vmeta search session ID for traceability
```

### Alembic Migration

A single migration adds `search_camera_device_ids` and `search_interval_seconds` to `triggers`, and `search_cameras_queried` and `search_session_uuid` to `trigger_execution_logs`. All nullable with defaults — fully backward-compatible.

---

## API Changes

### Existing Trigger Endpoints (backward-compatible)

All existing CRUD endpoints (`POST /api/v1/triggers`, `GET`, `PUT`, `DELETE`, toggle, stats) continue to work. The new fields are optional and only validated when `trigger_mode = "search"`.

### New Endpoints

| Method | Path | Service | Purpose |
|--------|------|---------|---------|
| `POST` | `/api/v1/triggers/{uuid}/execute-now` | Media | Manually execute a search trigger immediately, bypassing the schedule. Useful for testing. |

No new endpoints on Cameras or vmeta — the scheduler calls the existing `camera-search` endpoint directly.

### Stats Endpoint Extension

`GET /api/v1/triggers/stats/summary` gains a `by_mode` breakdown including `search` count.

---

## Frontend Changes

### Triggers Tab

The create/edit dialog gains a third mode option in the trigger mode selector:

1. **Mode selector** — Radio group: `Demographic`, `People Match`, `Search` (new).
2. **When "Search" is selected**, show:
   - **Individual Group selector** — Dropdown of available individual groups (required — this is the group whose members will be searched against camera recordings). Populated from the existing individual groups API.
   - **Camera multi-select** — Checkbox list of available cameras. The user picks whichever cameras they want — one, several, or all. Populated from `cameraServiceProvider`.
   - **Search interval** — Numeric input with unit selector (seconds/minutes/hours). Minimum 30 seconds.
   - **Tracking duration** — How far back to search in camera recordings (e.g. "10 minutes", "1 hour"). Uses the existing `tracking_duration` field.
   - **Similarity threshold** — Slider (0.0–1.0, default 0.75). Uses the existing `ppl_match_similarity_threshold` field.
3. **Condition panel** — Optionally, demographic conditions can be added. These are evaluated on the aggregated demographics of the matched individuals. For example: "fire if more than 3 people from group X were seen" (`people_count gt 3`) or "fire if over 50% of matched individuals are male" (`percent_male gt 50`).

### Actions Tab

No changes — actions are type-agnostic and work with any trigger mode.

### Models

`TriggerModel` in `trigger_model.dart` gains `search_camera_device_ids` and `search_interval_seconds`. `TriggerCreateRequest` serialization is extended.

---

## Configuration & Environment Variables

| Variable | Default | Service | Description |
|----------|---------|---------|-------------|
| `SEARCH_TRIGGER_CHECK_INTERVAL` | `10` | Media | How often the scheduler checks for due search triggers (seconds). |
| `SEARCH_TRIGGER_MAX_CONCURRENT` | `3` | Media | Max concurrent search executions to limit resource usage. |
| `SEARCH_TRIGGER_TIMEOUT` | `60` | Media | HTTP timeout for calling the vmeta camera-search endpoint (seconds). Higher than other timeouts because camera-search can process many videos. |
| `VMETA_SERVICE_URL` | `http://localhost:8008` | Media | Base URL for the vmeta service (already exists). |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | `localhost` / `6379` / `0` | Media | Redis connection for publishing search results (same as existing subscriber config). |

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| vmeta service unreachable | Logged as error, trigger skipped for this interval. Retried on next interval. |
| vmeta returns no matches | Normal case — event published with `people_count: 0`, empty demographics. Trigger conditions likely fail, logged with `passed=False`. |
| Camera has no collection / no recorded data | vmeta handles this internally — returns 0 matches for that camera. |
| `tracking_duration` parse failure | Logged as error. Falls back to default `"10 minutes"`. |
| Search takes longer than interval | Next execution is skipped (no overlap). Logged as warning. |
| DB error during evaluation | `try/except` with `db.rollback()`, same as existing triggers. |
| Stale trigger data (trigger deleted mid-search) | Check trigger still exists and is active before publishing to Redis. |

---

## Implementation Plan

### Phase 1 — Backend Core

1. Add `search_camera_device_ids` and `search_interval_seconds` columns to `Trigger` model + Alembic migration.
2. Update Pydantic schemas with validation for `trigger_mode = "search"`.
3. Implement `SearchTriggerScheduler` in `ppl-meta-media/src/services/search_trigger_scheduler.py`:
   - Async loop checking for due search triggers.
   - Calls vmeta `camera-search` endpoint with `camera_ids`, time window from `tracking_duration`, and `confidence_threshold`.
   - Transforms `GroupCameraSearchResponse` → standard instant detection event format.
   - Publishes to Redis `instant-detection` channel.
4. Wire scheduler startup in Media service lifespan.
5. Extend `TriggerExecutionLog` with `search_cameras_queried` and `search_session_uuid`.

### Phase 2 — Evaluation & API

6. Update `InstantDetectionSubscriber` trigger query to also match `search:<trigger_uuid>` camera IDs (minor WHERE clause change).
7. Implement `tracking_duration` parser (e.g. `"10 minutes"` → `timedelta(minutes=10)`).
8. Implement demographics aggregation from `matched_individuals[].demographics` → standard percentage format.
9. Add `POST /api/v1/triggers/{uuid}/execute-now` endpoint.
10. Update stats endpoint.

### Phase 3 — Frontend

11. Extend trigger mode selector with `Search` option.
12. Build multi-camera selector component.
13. Add search-specific configuration fields (interval, tracking duration, group selector, threshold).
14. Update `TriggerModel` and `TriggerCreateRequest`.

### Phase 4 — Testing & Hardening

15. Unit tests for demographics aggregation (age range mapping, percentage calculation).
16. Unit tests for scheduler timing and overlap prevention.
17. Integration test: end-to-end search trigger → vmeta camera-search → Redis → subscriber → action execution.
18. Test with cameras that have no recorded data (should gracefully return 0 matches).

---

## Backward Compatibility

- Only two new model columns (`search_camera_device_ids`, `search_interval_seconds`), both nullable with defaults — existing triggers are unaffected.
- `tracking_duration` already exists on all triggers; search mode is the first to consume it at runtime.
- Existing `demographic` and `ppl_match` triggers continue to operate via Redis pub/sub unchanged.
- The `SearchTriggerScheduler` only processes triggers where `trigger_mode = "search"`.
- The `instant-detection` Redis channel is reused — the existing subscriber handles search results with a minor query update to match `search:<trigger_uuid>` camera IDs.
- No new endpoints on Cameras or vmeta services.
- Frontend mode selector defaults to `Demographic` — existing UX unchanged unless user explicitly selects `Search`.
