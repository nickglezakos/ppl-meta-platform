# Automation Module

## Introduction

The Automation module provides event-driven trigger/action rules across the platform. Users define **triggers** (conditional rules bound to cameras) and **actions** (reusable side-effect definitions), then link them together. When a camera produces a detection event that satisfies a trigger's conditions, all linked actions execute automatically.

Triggers operate in two evaluation families:

- **Instant triggers** (`demographic`, `ppl_match`) — evaluated in real time as Redis detection events arrive.
- **Search triggers** (`search`, `search_demographic`) — evaluated periodically by a background scheduler that queries the vmeta service.

### How Triggers Work (high level)

The page at `/#/triggers` (labelled **Automation** on the home screen, icon `precision_manufacturing`) is a management UI with two tabs:

1. **Triggers tab** — Rules scoped to one or more cameras. Each trigger carries an AND-list of demographic conditions (or a people-match configuration), a time span, cooldown, active flag, and one or more linked action UUIDs. CRUD, toggle, filter, and paging are handled in [ppl-meta-frontend/lib/widgets/triggers_tab.dart](ppl-meta-frontend/lib/widgets/triggers_tab.dart).
2. **Actions tab** — Reusable action definitions that can be attached to one or more triggers. CRUD is managed via [ppl-meta-media/src/routes/user_trigger_actions.py](ppl-meta-media/src/routes/user_trigger_actions.py) and linked on the trigger model via [ppl-meta-media/src/models/trigger.py](ppl-meta-media/src/models/trigger.py).

Routing is wired from [ppl-meta-frontend/lib/presentation/navigation/app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart), and the screen is implemented in [ppl-meta-frontend/lib/screens/triggers_screen.dart](ppl-meta-frontend/lib/screens/triggers_screen.dart).

### Trigger Modes

| Mode | UI Label | Family | Description |
|------|----------|--------|-------------|
| `demographic` | Instant Demographic | Instant | Evaluates demographic percentage conditions (age ranges, gender ratios, people count) from real-time Redis events. At least one condition is required. |
| `ppl_match` | Instant People Match | Instant | Matches detected faces against a known individual group via the vmeta service. Requires a `ppl_match_group_id`. Similarity threshold and top-k are configurable per trigger. |
| `search` | Search People Match | Search | Periodically queries the vmeta camera-search endpoint across multiple cameras to find matches against an individual group. Requires `search_camera_device_ids`, `ppl_match_group_id`, and `search_interval_seconds` (min 30). |
| `search_demographic` | Search Demographic | Search | Periodically queries the vmeta demographics-search endpoint across multiple cameras, then evaluates demographic conditions against aggregated results. Requires `search_camera_device_ids`, at least one demographic condition, and `search_interval_seconds` (min 30). |

### Runtime Flow

#### Instant Triggers (demographic, ppl_match)

1. The Cameras service detects faces and publishes an event on the `instant-detection` Redis channel — see [ppl-meta-cameras/src/services/instant_detection.py](ppl-meta-cameras/src/services/instant_detection.py).
2. On startup, the Media service launches an `InstantDetectionSubscriber` ([ppl-meta-media/src/main.py](ppl-meta-media/src/main.py)) that listens to the Redis channel ([ppl-meta-media/src/services/redis_subscriber.py](ppl-meta-media/src/services/redis_subscriber.py)).
3. For each incoming message, the subscriber:
   - Deduplicates by `camera_id:timestamp` (tracked set, max 1000 entries).
   - Discards messages older than 10 seconds (freshness check).
   - Queries the DB for all active triggers whose `camera_device_id` matches the event's `camera_id`.
   - Evaluates each trigger: checks cooldown → routes by mode (`demographic` or `ppl_match`) → if conditions pass, updates `last_fired_at`, executes **all linked actions** (iterating `action_uuids`), and logs to `TriggerExecutionLog`.
4. HTTP endpoints for CRUD and explicit evaluation/webhook processing also exist in [ppl-meta-media/src/routes/triggers.py](ppl-meta-media/src/routes/triggers.py).

#### Search Triggers (search, search_demographic)

1. On startup, the Media service launches a `SearchTriggerScheduler` ([ppl-meta-media/src/services/search_trigger_scheduler.py](ppl-meta-media/src/services/search_trigger_scheduler.py)) that polls the DB for active search triggers.
2. Each search trigger is scheduled at its configured `search_interval_seconds` interval.
3. On each tick:
   - **`search` mode:** Calls vmeta `POST /api/v1/individual-groups/{group_id}/camera-search` with the trigger's `search_camera_device_ids` and `tracking_duration` as the lookback window. If matches are found above the similarity threshold, the result is published to the `instant-detection` Redis channel as a synthetic event with `source: "search_trigger"` metadata.
   - **`search_demographic` mode:** Calls vmeta `POST /api/v1/analytics/cameras/demographics-search` with camera device IDs and tracking duration. The vmeta endpoint resolves cameras → videos → individuals → MVR people, aggregates demographics into percentage buckets, and returns the result. The scheduler then publishes the aggregated demographics as a synthetic Redis event for the subscriber to evaluate against the trigger's demographic conditions.
4. The synthetic events are picked up by the `InstantDetectionSubscriber` which evaluates conditions and fires actions as normal.
5. A manual `POST /api/v1/triggers/{uuid}/execute-now` endpoint allows on-demand execution of search triggers, bypassing the interval schedule.

---

## Module Boundaries

| Service | Responsibility |
|---------|---------------|
| **Frontend** (`/#/triggers`) | Trigger and action configuration UX (labelled "Automation" on home screen). Riverpod state management. |
| **Media service** | Trigger persistence (SQLAlchemy), Redis-based evaluation, search trigger scheduling, action dispatch. |
| **Cameras service** | Publishes demographic detection events to Redis. |
| **vmeta service** | Face similarity checks for `ppl_match` triggers (`POST /api/v1/individual-groups/{group_id}/check-duplicates`), camera-search for `search` triggers (`POST /api/v1/individual-groups/{group_id}/camera-search`), and demographics aggregation for `search_demographic` triggers (`POST /api/v1/analytics/cameras/demographics-search`). |
| **Communications service** | Downstream executor for `email`, `webhook`, `alert`, and `log` actions. |
| **Signage service** | Downstream executor for `digital_signage` actions. |

---

## Data Model

### Trigger ([ppl-meta-media/src/models/trigger.py](ppl-meta-media/src/models/trigger.py))

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `uuid` | UUID | auto | Unique identifier, indexed |
| `name` | String(255) | null | Friendly name |
| `description` | String(500) | null | Description |
| `camera_device_id` | String(255) | — | Camera device ID, indexed. For search triggers, auto-generated as `search:{uuid}`. |
| `camera_name` | String(255) | null | Human-friendly camera name |
| `trigger_mode` | String(30) | `"demographic"` | `"demographic"`, `"ppl_match"`, `"search"`, or `"search_demographic"` |
| `demographic_conditions` | Text (JSON) | — | JSON array: `[{"field": "...", "operator": "...", "value": N}]` |
| `time_span` | String(100) | — | Active window, e.g. `"Mon-Fri 09:00-17:00"` or `"any"` |
| `cooldown_seconds` | Integer | `60` | Minimum seconds between firings |
| `is_active` | Boolean | `True` | Active/inactive toggle |
| `last_fired_at` | DateTime(tz) | null | Timestamp of last fire |
| `action_uuid` | UUID FK → user_trigger_actions.uuid | null | Legacy single-action link (ON DELETE SET NULL). Kept for backward compatibility; synced from first element of `action_uuids`. |
| `action_uuids` | Text (JSON) | null | JSON array of action UUIDs assigned to this trigger (multi-action support), e.g. `["uuid1", "uuid2"]` |
| `ppl_match_group_id` | String(255) | null | Target individual group for `ppl_match` and `search` modes |
| `ppl_match_similarity_threshold` | Float | `0.75` | Minimum similarity for `ppl_match` and `search` |
| `ppl_match_top_k` | Integer | `1` | Max top matches to keep |
| `search_camera_device_ids` | Text (JSON) | null | JSON array of camera device IDs for `search` and `search_demographic` modes |
| `search_interval_seconds` | Integer | `300` | How often (in seconds) a search trigger executes. Minimum 30. |
| `tracking_duration` | String(50) | `"10 minutes"` | MVR search time window / lookback window for search triggers |
| `last_match_info` | Text (JSON) | null | Latest `ppl_match` payload |
| `last_matched_at` | DateTime(tz) | null | Last successful match timestamp |

**Relationships:**
- `user_action` → `UserTriggerAction` via `action_uuid` (legacy, single action).
- Multi-action: `action_uuids` stores a JSON array of UUIDs. Routes resolve these to action names via `_resolve_action_names()`. The legacy `action_uuid` is auto-synced to the first entry for backward compatibility.

### UserTriggerAction ([ppl-meta-media/src/models/user_trigger_action.py](ppl-meta-media/src/models/user_trigger_action.py))

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | Integer PK | auto | |
| `uuid` | UUID | auto | |
| `name` | String(255) | — | Action name |
| `description` | Text | null | |
| `action_type` | String(50) | `"alert"` | One of: `alert`, `email`, `webhook`, `log`, `digital_signage` |
| `action_config` | Text (JSON) | null | Type-specific configuration (see Action Types) |
| `is_active` | Boolean | `True` | |
| `created_at` | DateTime(tz) | `now()` | |
| `updated_at` | DateTime(tz) | `now()` | |
| `created_by` | String(255) | null | Creator username/email |

### TriggerExecutionLog ([ppl-meta-media/src/models/trigger_execution_log.py](ppl-meta-media/src/models/trigger_execution_log.py))

Every evaluation (pass or fail) is recorded here for auditing.

| Column | Type | Description |
|--------|------|-------------|
| `trigger_uuid` | UUID | |
| `trigger_id` | Integer FK → triggers.id | ON DELETE SET NULL |
| `trigger_name` | String(255) | |
| `trigger_mode` | String(30) | `"demographic"`, `"ppl_match"`, `"search"`, or `"search_demographic"` |
| `camera_device_id` | String(255) | |
| `source_mvr_uuid` | String(255) | Source identity UUID |
| `matched_group_id` | String(255) | For `ppl_match` and `search` |
| `matched_member_uuid` | String(255) | For `ppl_match` and `search` |
| `similarity_score` | Float | |
| `threshold` | Float | |
| `match_details_json` | Text | Full match JSON |
| `passed` | Boolean | Whether conditions passed |
| `reason` | String(500) | Human-readable explanation |
| `action_executed` | Boolean | Whether action(s) ran |
| `evaluated_at` | DateTime(tz) | |
| `search_cameras_queried` | Text (JSON) | JSON array of camera device IDs queried by search trigger |
| `search_session_uuid` | String(255) | Search session UUID returned by vmeta camera-search |

---

## Demographic Conditions

### Valid Fields

`people_count`, `percent_male`, `percent_female`, `percent_age_0_12`, `percent_age_13_17`, `percent_age_18_24`, `percent_age_25_34`, `percent_age_35_44`, `percent_age_45_54`, `percent_age_55_64`, `percent_age_65_plus`

### Valid Operators

| Operator | Meaning |
|----------|---------|
| `gt` | Greater than (>) |
| `gte` | Greater than or equal (≥) |
| `lt` | Less than (<) |
| `lte` | Less than or equal (≤) |
| `eq` | Equal (=) |

### Evaluation Logic

All conditions are evaluated with **AND** semantics — every condition must pass for the trigger to fire. The `_evaluate_conditions()` method in [redis_subscriber.py](ppl-meta-media/src/services/redis_subscriber.py) extracts the actual value from the demographics dict (or `people_count` directly), casts it to float, and compares per operator. If any single condition fails, the entire trigger fails.

### Validation Rules (Pydantic)

- In `demographic` mode: at least one condition is required; `camera_device_id` is required.
- In `ppl_match` mode: `ppl_match_group_id` is required; `camera_device_id` is required.
- In `search` mode: `search_camera_device_ids` and `ppl_match_group_id` are both required; `search_interval_seconds` must be ≥ 30.
- In `search_demographic` mode: `search_camera_device_ids` is required; at least one demographic condition is required; `search_interval_seconds` must be ≥ 30.

---

## Action Types

| Type | `action_config` Schema | Execution |
|------|----------------------|-----------|
| **`alert`** | `{"message": "...", "severity": "warning\|error\|info", "duration_seconds": 30}` | Logs an audit event via Communications Service with the specified severity. Displayed as an on-screen alert. |
| **`email`** | `{"recipients": ["email@..."], "to": "email1,email2", "cc": [...], "subject": "...", "body": "..."}` | Sends email via Communications Service (`POST /api/v1/email/send`). Subject and body support template variables. |
| **`webhook`** | `{"url": "https://...", "method": "POST", "payload_data": {...}}` | POSTs to the specified URL via Communications Service (`POST /api/v1/webhook/send`). Payload includes trigger and detection metadata. |
| **`log`** | `{"message": "...", "severity": "info", "data": {"category": "...", "tags": [...]}}` | Creates an audit log entry via Communications Service. |
| **`digital_signage`** | `{"device_ids": [...], "playlist_id": "uuid", "transition_mode": "immediate\|after_current\|fade", "fade_duration_ms": 2000}` | Sends a `START` playback command to signage devices to switch playlist. |

### Template Variables (for message/subject/body fields)

`{trigger_name}`, `{trigger_id}`, `{reason}`, `{match_reason}`, `{matched_member_uuid}`, `{matched_member_name}`, `{group_member_number}`, `{similarity_score}`

If no template variables are used and a `ppl_match` result exists, the match reason is auto-appended.

---

## Multi-Action Execution

Each trigger can link to **multiple actions** via the `action_uuids` JSON column (a list of action UUIDs). When a trigger fires:

1. The subscriber reads `action_uuids` (JSON text → list of UUID strings).
2. Falls back to legacy `action_uuid` if `action_uuids` is empty/null.
3. Iterates over all action UUIDs and calls `_execute_trigger_action()` for each, passing `action_uuid_override`.
4. Each action is independently looked up from `UserTriggerAction` and routed to its type-specific handler.
5. If any action fails, others still execute (individual try/except per handler).

On the API layer:
- `action_uuids` (list of UUIDs) is the primary field for create/update.
- `action_uuid` (single UUID) is kept for backward compatibility and auto-synced: setting `action_uuids` sets `action_uuid` to the first element; setting `action_uuid` alone populates `action_uuids` as a single-element array.
- Responses include both `action_uuids` and `action_names` (resolved list of action names).

On the frontend:
- The triggers table shows linked actions as compact chips. Clicking opens a multi-select dialog with checkboxes.
- The create/edit dialog shows an inline chip selector where actions can be added or removed individually.

---

## Cooldown Mechanism

- Default cooldown: **60 seconds** (configurable per trigger via `cooldown_seconds`).
- Before evaluating conditions, the subscriber checks: `now < last_fired_at + timedelta(seconds=cooldown_seconds)`. If true, the trigger is **skipped** and remaining seconds are logged.
- Cooldown is bypassed only if `last_fired_at` is `None` (trigger has never fired).
- Minimum value: 0 (no enforced maximum).

---

## Redis Pub/Sub

**Channel:** `instant-detection`

**Publisher:** Cameras service — [instant_detection.py](ppl-meta-cameras/src/services/instant_detection.py) and [instant_detection_tasks.py](ppl-meta-cameras/src/tasks/instant_detection_tasks.py). Also published synthetically by the `SearchTriggerScheduler` for search trigger results.

**Subscriber:** `InstantDetectionSubscriber` in [redis_subscriber.py](ppl-meta-media/src/services/redis_subscriber.py), started during media service lifespan in [main.py](ppl-meta-media/src/main.py).

**Message format (instant / camera events):**
```json
{
  "camera_id": "usb_camera_0",
  "timestamp": "2026-04-07T12:00:00.000000",
  "people_count": 5,
  "demographics": {
    "percent_male": 60.0,
    "percent_female": 40.0,
    "percent_age_18_24": 20.0
  },
  "source_mvr_uuids": ["uuid1", "uuid2"],
  "metadata": {
    "source_mvr_uuids": ["uuid1", "uuid2"],
    "processing_time": 0.45,
    "total_faces": 5
  }
}
```

**Message format (synthetic / search trigger events):**
```json
{
  "camera_id": "search:<trigger-uuid>",
  "timestamp": "2026-04-08T10:00:00.000000",
  "people_count": 12,
  "demographics": {
    "percent_male": 58.3,
    "percent_female": 41.7,
    "percent_age_25_34": 33.3
  },
  "source": "search_trigger",
  "source_mvr_uuids": [],
  "metadata": {
    "search_cameras": ["usb_camera_0", "rtsp_192.168.1.76_554"],
    "search_session_uuid": "abc-123",
    "trigger_uuid": "<trigger-uuid>"
  }
}
```

---

## API Endpoints

### Triggers — prefix `/api/v1/triggers`

Source: [ppl-meta-media/src/routes/triggers.py](ppl-meta-media/src/routes/triggers.py)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/triggers` | Create a trigger |
| `GET` | `/api/v1/triggers` | List triggers (paginated, filter by `is_active`, `action`) |
| `GET` | `/api/v1/triggers/{uuid}` | Get a single trigger with linked action names |
| `PUT` | `/api/v1/triggers/{uuid}` | Update a trigger (partial update supported) |
| `PATCH` | `/api/v1/triggers/{uuid}/toggle` | Toggle active/inactive |
| `DELETE` | `/api/v1/triggers/{uuid}` | Delete a trigger |
| `POST` | `/api/v1/triggers/{uuid}/execute-now` | Manually execute a search trigger on demand (search and search_demographic modes only) |
| `GET` | `/api/v1/triggers/stats/summary` | Stats: total, active, inactive, by action type |

### User Actions — prefix `/api/v1/user-actions`

Source: [ppl-meta-media/src/routes/user_trigger_actions.py](ppl-meta-media/src/routes/user_trigger_actions.py)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/user-actions/` | Create an action |
| `GET` | `/api/v1/user-actions/` | List actions (paginated, filter by `is_active`, `action_type`) |
| `GET` | `/api/v1/user-actions/{uuid}` | Get a single action |
| `PUT` | `/api/v1/user-actions/{uuid}` | Update an action |
| `PATCH` | `/api/v1/user-actions/{uuid}/toggle` | Toggle active status |
| `DELETE` | `/api/v1/user-actions/{uuid}` | Delete an action |
| `GET` | `/api/v1/user-actions/stats/summary` | Stats: total, active, inactive, by type |

---

## Frontend Structure

### Screen

[ppl-meta-frontend/lib/screens/triggers_screen.dart](ppl-meta-frontend/lib/screens/triggers_screen.dart) — App bar titled "Automation", `TabBarView` with two tabs: Triggers (icon `precision_manufacturing`) and Actions.

### Widgets

| Widget | File | Description |
|--------|------|-------------|
| Triggers tab | [triggers_tab.dart](ppl-meta-frontend/lib/widgets/triggers_tab.dart) | `ConsumerStatefulWidget` (Riverpod). Data table with multi-action chip display per row (click to open multi-select dialog). Create/Edit dialog includes camera selection, mode-specific config cards, and a multi-action inline selector with add/remove chips. Supports all four trigger modes: Instant Demographic, Instant People Match, Search People Match, Search Demographic. |
| Actions tab | [actions_tab.dart](ppl-meta-frontend/lib/widgets/actions_tab.dart) | Two sections: User Actions (CRUD) and System Workflows (read-only, currently disabled). Uses `UserActionService` and `WorkflowActionService`. |
| Demographic config | [demographic_trigger_config.dart](ppl-meta-frontend/lib/widgets/demographic_trigger_config.dart) | Dedicated widget for building demographic conditions with field/operator/value dropdowns, plus signage device and playlist selection. |

### Models

| Model | File | Classes |
|-------|------|---------|
| Trigger | [trigger_model.dart](ppl-meta-frontend/lib/models/trigger_model.dart) | `TriggerModel`, `DemographicCondition`, `TriggerCreateRequest`, `TriggerListResponse` |
| User Action | [user_action_model.dart](ppl-meta-frontend/lib/models/user_action_model.dart) | `UserActionModel`, `UserActionCreateRequest`, `UserActionListResponse`, `UserActionStatsResponse` |

### Services

| Service | File | Notes |
|---------|------|-------|
| TriggerService | [trigger_service.dart](ppl-meta-frontend/lib/services/trigger_service.dart) | HTTP client for all trigger endpoints plus signage device fetching. Uses `Config.gatewayServiceUrl` as base URL. |
| UserActionService | [user_action_service.dart](ppl-meta-frontend/lib/services/user_action_service.dart) | HTTP client for user action CRUD. |

### State Management

Riverpod (`ConsumerStatefulWidget`). Uses `ref.read(apiClientProvider)` for authenticated requests and `ref.read(cameraServiceProvider)` for the camera list.

---

## Environment Variables

| Variable | Default | Used In |
|----------|---------|---------|
| `REDIS_HOST` | `localhost` | redis_subscriber.py, instant_detection.py |
| `REDIS_PORT` | `6379` | redis_subscriber.py, instant_detection.py |
| `REDIS_DB` | `0` | redis_subscriber.py, instant_detection.py |
| `VMETA_SERVICE_URL` | `http://localhost:8008` | redis_subscriber.py (for `ppl_match` duplicate checks) |
| `COMMUNICATIONS_SERVICE_URL` | (from config) | triggers.py, redis_subscriber.py (via `get_config()`) |

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Redis connection failure | Logged as warning; Media service starts without trigger evaluation (`"Redis-based trigger evaluation will be unavailable"`). |
| JSON parse errors | Caught per-message in the listen loop, logged, processing continues. |
| Stale messages | Messages older than 10 seconds are discarded. |
| DB errors | `try/except` with `db.rollback()` in evaluation loop. |
| Action execution failures | Each action handler has individual `try/except`; errors are logged but do not block other triggers. |
| vmeta call failures (`ppl_match`) | Per-source-UUID; non-200 responses logged as warnings; continues with remaining UUIDs. Full exception returns `(False, "error message", None)`. |
| Communications Service failures | Uses `httpx` with timeout; HTTP errors and request errors caught separately; returns `{"success": False, "message": "..."}`. |

---

## Technical Analysis

**Strengths:**
- Clear separation between rule definition (triggers) and action definition (user actions) improves reuse — multiple actions can be assigned to a single trigger.
- Multi-action support allows a single trigger fire to execute several actions in sequence (e.g., send an email _and_ switch signage _and_ log).
- Cooldown and `last_fired_at` provide basic anti-spam control with per-trigger granularity.
- Multi-action-type dispatch supports both signage and communications workflows.
- Execution logs provide full auditability per evaluation (pass and fail).
- Template variable interpolation in messages allows dynamic, context-rich notifications.
- Search triggers extend automation beyond real-time events to periodic cross-camera analysis.
- Legacy `action_uuid` is auto-synced from `action_uuids[0]` for backward compatibility.

**Caveats:**
- Duplicate evaluation paths (Redis + HTTP) increase behavior drift risk if logic diverges.
- Condition/time parsing is functional but not a fully centralized rules engine.
- Deduplication set in the subscriber is bounded (1000 entries) and in-memory only — lost on restart.
- Search trigger scheduler is in-memory; if the Media service restarts, pending schedules reset.
