# Analytics Module

> **Route:** `http://localhost:3000/#/analytics`  
> **Screen class:** `AnalyticsScreen` in `ppl-meta-frontend/lib/screens/analytics_screen.dart`  
> **Backend:** `ppl-meta-gateway/src/api/v1/analytics.py`

---

## 1. Overview

The Analytics module is the MVR (Multi-Video Recognition) people detection insights dashboard. It aggregates data from camera collections to show who was detected, when, and where — with demographic breakdowns and behavioral patterns.

The dashboard supports two **data sources**, selectable via a filter:

- **Video Recording** (default) — Data from the recording pipeline: video segments → Vision → Orchestrator → VMeta tracking sessions. Fetched via the Media service collection iteration path.
- **Instant Detection** — Data from instant detection: live frames → Vision → Orchestrator → VMeta identity resolution → persisted sessions. Fetched directly from VMeta's `tracking-sessions/summary` endpoint.

Both paths produce identical response structures so all dashboard widgets (charts, tables, metrics) render without modification regardless of the selected source.

The screen is organized into five dashboard levels, each backed by a dedicated API endpoint:

| Level | Section | Endpoint | Description |
|-------|---------|----------|-------------|
| L1 | Basic Metrics | `/api/v1/analytics/summary` | Total people, active collections, videos, demographics |
| L1.5 | MVR Quality | `/api/v1/analytics/mvr-quality-metrics` | Tracking sessions quality, data completeness |
| L2 | Time Trends | `/api/v1/analytics/time-series` | Hourly/daily people-count line charts |
| L3 | Demographics | `/api/v1/analytics/demographics` | Gender and age pie charts, per-camera breakdowns |
| L4 | Behavioral | `/api/v1/analytics/behavioral` | Weekly heatmap, peak hours, visit frequency |

There is also a supporting endpoint for the filter UI:

| Endpoint | Purpose |
|----------|---------|
| `/api/v1/analytics/cameras` | Populates the collection checkbox list in the filter dialog |

---

## 2. Architecture

```
┌─────────────────────────────────────────────┐
│        Analytics Screen (Flutter/Dart)       │
│  AnalyticsScreen → ConsumerStatefulWidget    │
│  Uses Riverpod for dependency injection      │
└───────────┬──────────────┬──────────────────┘
            │              │
   ┌────────▼────────┐ ┌──▼─────────────────┐
   │ MediaApiClient   │ │ AnalyticsApiClient  │
   │ (5 methods)      │ │ (1 method)          │
   └────────┬─────────┘ └──┬─────────────────┘
            │               │
            └───────┬───────┘
                    ▼
         Gateway Service (:8080)
         ppl-meta-gateway/src/api/v1/analytics.py
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
   Media Service  Gateway Proxy  VMeta Service
     (:8000)       (:8080)        (:8008)
   collections   mvr-count     quality-metrics
                 per-camera    mvr-people/search
                               tracking-sessions/summary
```

### Data path by source type

| Source | Data path | Used by |
|--------|-----------|--------|
| **Recording** (default) | Gateway → Media (collections) → Camera MVR counter → VMeta (per-video) | summary, time-series, demographics, behavioral |
| **Instant Detection** | Gateway → VMeta `/tracking-sessions/summary` (direct query) | summary, time-series, demographics, behavioral |
| **Both paths** | Gateway → VMeta `/mvr/quality-metrics` with `source_type` filter | mvr-quality-metrics |

When the data source is `instant_detection`, the gateway bypasses the Media service collection iteration entirely and instead calls VMeta's tracking-sessions/summary endpoint directly, which queries the `tracking_sessions` and `individuals` tables filtered by `source_type = 'instant_detection'`.

### Service dependencies

- **Media Service** (`localhost:8000`): Source of truth for collections. The gateway fetches `GET /api/v1/media/collections` to enumerate all collections and their metadata (UUID, name, video count). Used only in the **recording** data path.
- **Gateway Proxy** (`localhost:8080`): The cached camera MVR count endpoint `GET /api/v1/cameras/{collection_id}/mvr-count` provides per-collection people counts with demographics. Results have a 10-minute cache TTL. Used only in the **recording** data path.
- **VMeta Service** (`localhost:8008`): Provides quality metrics (`/api/v1/mvr/quality-metrics` and `/api/v1/individuals/quality-metrics`), MVR people search by videos (`/api/v1/mvr-people/search/by-videos`), detailed individual data for behavioral analysis, and the **tracking-sessions/summary** endpoint for instant detection analytics.

---

## 3. Frontend Data Flow

### 3.1 Initialization and loading

When the screen mounts, `initState()` calls `_loadAnalytics()`, which executes a sequential waterfall of API calls:

```
_loadAnalytics()
  ├─ 1. getCamerasList()          → populates filter dropdown (_cameras)
  ├─ 2. getAnalyticsSummary()     → _analyticsSummary (L1)
  ├─ 3. getMvrQualityMetrics()    → _mvrQualityMetrics (L1.5)
  ├─ 4. getTimeBasedAnalytics()   → _timeSeriesData (L2)
  ├─ 5. getDemographicsBreakdown()→ _demographicsData (L3)
  └─ 6. getBehavioralAnalytics()  → _behavioralData (L4)
```

Each call after the summary (step 2) is wrapped in its own try/catch so that a failure in one level does not prevent other levels from rendering. Only the summary failure (step 2) is treated as a page-level error that shows the error state.

### 3.2 State management

```dart
// Filter state
String _dataSource                   // 'recording' (default) or 'instant_detection'
String _timeFilter             // 'today', 'last_hour', 'last_3_hours', 'last_week', 'last_month', 'custom'
List<String> _selectedCollectionIds  // empty = all collections
List<String> _selectedGenders        // empty = all ('male', 'female')
List<String> _selectedAgeGroups      // empty = all ('young', 'adult', 'elderly')
DateTime? _startDate, _endDate       // only used when _timeFilter == 'custom'
bool _autoRefresh                    // 10-minute auto-refresh toggle

// Data state
AnalyticsSummary? _analyticsSummary
MvrQualityMetrics? _mvrQualityMetrics
Map<String, dynamic>? _timeSeriesData
Map<String, dynamic>? _demographicsData
Map<String, dynamic>? _behavioralData
List<Map<String, dynamic>> _cameras
```

### 3.3 Filter dialog

The `_FilterDialog` is a `StatefulWidget` dialog with five filter sections:

1. **Data Source** — Two choice chips: "Video Recording" (blue, default) and "Instant Detection" (orange). This is the most fundamental filter — it determines the data pipeline all other filters operate on.
2. **Time Range** — Choice chips: Today, Last Hour, Last 3 Hours, Last Week, Last Month, Custom Range. Custom shows date+time pickers.
3. **Collections** — Multi-select checkbox list populated from `/analytics/cameras`. ID extraction uses UUID-first priority: `camera['uuid'] ?? camera['id'] ?? camera['device_id'] ?? camera['collection_name'] ?? camera['name']`.
4. **Demographics** — Gender filter chips (Male, Female) and age group filter chips (Young 0–25, Adult 26–65, Elderly 65+).
5. **Auto-refresh** — Toggle for automatic 10-minute refresh.

When "Instant Detection" is selected, an orange chip appears in the filter bar below the app bar with a delete (×) button that resets back to the recording source.

On "Apply", the dialog returns a result map (including `dataSource`) and `_loadAnalytics()` re-runs with the new filter values passed as query parameters to each endpoint.

---

## 4. API Endpoints (Backend)

All endpoints live in the gateway router at `/api/v1/analytics/...` and require JWT authentication via `get_current_user`.

### 4.1 `GET /analytics/cameras`

Returns all collections from the Media service for the filter dropdown.

**Request:** No parameters (aside from auth).

**Internal flow:**
1. Calls `GET http://localhost:8000/api/v1/media/collections?limit=1000`.
2. Transforms each collection into: `{ id, uuid, name, collection_name, video_count }`.
3. `id` is resolved via `_get_collection_identifier()` (UUID-first priority).

**Response:** Array of collection metadata objects.

---

### 4.2 `GET /analytics/summary`

Aggregated MVR people detection summary across collections.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `camera_ids` | string | null | Comma-separated collection IDs (also accepts `collection_ids` alias) |
| `time_filter` | string | `"today"` | Time period |
| `force_refresh` | bool | false | Bypass cache |
| `start_date` | string | null | ISO 8601 (for custom range) |
| `end_date` | string | null | ISO 8601 (for custom range) |
| `genders` | string | null | Comma-separated: `male,female` |
| `age_groups` | string | null | Comma-separated: `young,adult,elderly` |
| `source_type` | string | null | `recording_pipeline` or `instant_detection`. Null defaults to recording. |

**Internal flow (recording — default):**
1. If `camera_ids` provided, splits into list. Otherwise fetches all collections from Media service.
2. For each collection, calls `GET http://localhost:8080/api/v1/cameras/{collection_id}/mvr-count` with `time_filter` and optional custom date range.
3. Aggregates: total people (with demographic filtering via `_filter_demographics_count`), active collections (>0 detections), total videos, gender/age demographics.
4. Computes percentage breakdowns for gender and age.

**Internal flow (instant_detection):**
1. Calls VMeta `GET http://localhost:8008/api/v1/tracking-sessions/summary` with `source_type=instant_detection`, `start_time`, `end_time`, and optional `camera_device_ids`.
2. Applies demographic filters to the returned summary data.
3. Returns session_count as `total_people`, active cameras from VMeta's camera breakdown, and demographic percentages.
4. The response shape is identical to the recording path — the frontend renders it the same way.

**Response structure:**
```json
{
  "total_people": 42,
  "active_cameras": 3,
  "total_videos": 120,
  "last_detection": null,
  "time_filter": "today",
  "demographics": {
    "gender": { "male": 25, "female": 17, "male_percentage": 59.5, "female_percentage": 40.5 },
    "age": { "young": 10, "adult": 28, "elderly": 4, "young_percentage": 23.8, ... }
  },
  "camera_breakdown": [
    { "camera_id": "uuid-...", "camera_name": "Lobby", "count": 20, "video_count": 50, "demographics": {...} }
  ],
  "generated_at": "2026-03-19T12:00:00Z",
  "cached": false
}
```

**Note:** The `collection_ids` query parameter has `alias="camera_ids"` in FastAPI, so the backend accepts both parameter names on the wire. The frontend currently sends `camera_ids`.

---

### 4.3 `GET /analytics/time-series`

Time-bucketed people counts for line chart visualization.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `camera_ids` | string | null | Comma-separated collection IDs |
| `time_filter` | string | `"today"` | Time period |
| `interval` | string | `"hour"` | `hour` or `day` (auto-selected based on range) |
| `start_date` / `end_date` | string | null | For custom range |
| `source_type` | string | null | `recording_pipeline` or `instant_detection`. Null defaults to recording. |

**Internal flow (recording — default):**
1. Determines date range from `time_filter`. Auto-selects interval: `hour` for ≤3 days, `day` for longer.
2. Creates empty time buckets (hourly or daily) spanning the range.
3. Fetches MVR count per collection via the cached camera counter endpoint.
4. Aggregates counts into the most recent time bucket (simplified approach — production would use per-timestamp data from the database).
5. Computes peak count, peak time, and average.

**Internal flow (instant_detection):**
1. Calls VMeta `GET /tracking-sessions/summary` with `source_type=instant_detection`.
2. Determines date range and interval from `time_filter`.
3. Creates empty time buckets and distributes the session count across the range.
4. Computes peak count, peak time, and average.

**Response structure:**
```json
{
  "time_filter": "today",
  "interval": "hour",
  "start_time": "2026-03-19T00:00:00",
  "end_time": "2026-03-19T14:30:00",
  "data_points": [
    { "timestamp": "2026-03-19T00:00:00", "count": 0, "video_count": 0 },
    { "timestamp": "2026-03-19T01:00:00", "count": 0, "video_count": 0 },
    ...
  ],
  "peak_count": 42,
  "peak_time": "2026-03-19T14:00:00",
  "average_count": 3.5,
  "total_count": 42
}
```

**Limitation:** The current implementation places all aggregated counts into the last time bucket rather than distributing them across actual detection timestamps. This is acknowledged as a simplification for the initial version.

---

### 4.4 `GET /analytics/demographics`

Detailed gender and age demographic breakdowns with per-camera detail.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `camera_ids` | string | null | Comma-separated collection IDs |
| `time_filter` | string | `"today"` | Time period |
| `start_date` / `end_date` | string | null | For custom range |
| `genders` | string | null | Gender filter |
| `age_groups` | string | null | Age group filter |
| `source_type` | string | null | `recording_pipeline` or `instant_detection`. Null defaults to recording. |

**Internal flow (recording — default):**
1. Fetches all collections from Media service.
2. Filters to matching collections using `_collection_matches_selected_ids()` (UUID-first multi-key matching).
3. For each collection, calls `GET /api/v1/cameras/{camera_id}/mvr-count` to get demographics.
4. Applies demographic filters by zeroing out non-selected gender/age counts.
5. Aggregates totals and builds a demographic matrix (gender × age), using independence assumption for cross-tabulation estimates.
6. Produces per-camera breakdown with absolute counts and percentages.

**Internal flow (instant_detection):**
1. Calls VMeta `GET /tracking-sessions/summary` with `source_type=instant_detection`.
2. Extracts gender/age distributions from the returned demographics object.
3. Applies demographic filters (zeros out non-selected categories).
4. Builds the demographic matrix and per-camera breakdown from VMeta's camera_breakdown data.

**Response structure:**
```json
{
  "time_filter": "today",
  "total_people": 42,
  "gender_distribution": {
    "male": 25, "female": 17, "unknown": 0,
    "male_percentage": 59.5, "female_percentage": 40.5, "unknown_percentage": 0.0
  },
  "age_distribution": {
    "young": 10, "adult": 28, "middle_aged": 0, "elderly": 4, "unknown": 0,
    "young_percentage": 23.8, ...
  },
  "demographic_matrix": {
    "male": { "young": 6, "adult": 17, "middle_aged": 0, "elderly": 2, "unknown": 0 },
    "female": { "young": 4, "adult": 11, ... },
    "unknown": { ... }
  },
  "camera_breakdown": [
    { "camera_id": "uuid-...", "camera_name": "Lobby", "total_people": 20, "gender": {...}, "age": {...} }
  ],
  "generated_at": "2026-03-19T12:00:00Z"
}
```

**Note on the demographic matrix:** Since the MVR counter endpoint returns marginal counts (total_male, total_young, etc.) but not cross-tabulations (male AND young), the matrix is estimated by assuming gender and age are independent: `count(g, a) = total * P(g) * P(a)`.

---

### 4.5 `GET /analytics/behavioral`

Behavioral pattern analysis: activity heatmaps, peak times, visit frequency, camera comparisons.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `camera_ids` | string | null | Comma-separated collection IDs |
| `time_filter` | string | `"last_week"` | Time period (default is wider for behavioral) |
| `start_date` / `end_date` | string | null | For custom range |
| `genders` | string | null | Gender filter |
| `age_groups` | string | null | Age group filter |
| `source_type` | string | null | `recording_pipeline` or `instant_detection`. Null defaults to recording. |

**Internal flow (recording — default):**

This is the most complex endpoint. Unlike other endpoints that use the cached MVR counter, behavioral analytics drills into individual MVR person appearances:

1. Fetches all collections from Media service and applies collection filter.
2. For each collection **that has `camera_device_id`** (collections without this field are skipped):
   a. Gets the collection's videos via `GET http://localhost:8000/api/v1/media/search?collection_id={uuid}&page_size=500`.
   b. Sends video UUIDs to VMeta: `POST http://localhost:8008/api/v1/mvr-people/search/by-videos` with `video_uuids`, `start_time`, `end_time`.
   c. Iterates over each MVR person's `appearances` array, extracting `start_timestamp` from each appearance.
   d. Applies per-person demographic filtering (gender/age_group matching).
   e. Buckets each appearance into hourly_activity (0–23), daily_activity (Mon–Sun), and weekly_heatmap (day × hour).
3. Computes peak hours (top 5), peak days (top 3), camera comparison (top 5 by total).
4. Visit frequency is currently a fixed-ratio simulation: 60% new, 30% returning, 10% frequent.

**Response structure:**
```json
{
  "time_filter": "last_week",
  "total_detections": 156,
  "active_cameras": 3,
  "weekly_heatmap": {
    "Monday": { "0": 0, "1": 0, ..., "14": 12, ..., "23": 0 },
    "Tuesday": { ... },
    ...
  },
  "hourly_activity": { "0": 2, "1": 0, ..., "14": 25, ... },
  "daily_activity": { "Monday": 30, "Tuesday": 28, ... },
  "peak_hours": [
    { "hour": 14, "count": 25, "time_label": "14:00 - 15:00" }
  ],
  "peak_days": [
    { "day": "Monday", "count": 30 }
  ],
  "camera_comparison": [
    { "camera_id": "Lobby Camera", "total_people": 80 }
  ],
  "visit_frequency": {
    "new_visitors": 94,
    "returning_visitors": 47,
    "frequent_visitors": 15
  },
  "generated_at": "2026-03-19T12:00:00Z"
}
```

**Important:** Collections without `camera_device_id` are silently skipped. This means recently-added or orphaned collections may produce no behavioral data even if they have video content.

**Internal flow (instant_detection):**
1. Calls VMeta `GET /tracking-sessions/summary` with `source_type=instant_detection`.
2. Builds a weekly heatmap, hourly activity, and daily activity distribution from the returned session data.
3. Computes peak hours, peak days, and camera comparison from VMeta's camera_breakdown.
4. Visit frequency uses the same fixed-ratio simulation as the recording path.

---

### 4.6 `GET /analytics/quality-metrics` (legacy)

Average face quality metrics from individual objects (not MVR objects). This is the older quality endpoint.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `camera_ids` | string | null | Comma-separated collection IDs |
| `time_filter` | string | `"today"` | Time period |
| `start_date` / `end_date` | string | null | For custom range |

**Internal flow:**
1. Fetches collections from Media service, applies filter.
2. For each collection, queries VMeta: `GET http://localhost:8008/api/v1/individuals/quality-metrics?collection_name={name}&start_time=...&end_time=...`.
3. Aggregates weighted average quality across collections.
4. Sorts collections by quality (descending).
5. Assigns a quality grade via `_get_quality_grade()`: ≥0.8 Excellent, ≥0.6 Good, ≥0.4 Fair, ≥0.2 Poor, <0.2 Very Poor.

---

### 4.7 `GET /analytics/mvr-quality-metrics` (recommended)

Quality metrics following the MVR → Individual data tree. This is the recommended endpoint for the dashboard.

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `camera_ids` | string | null | Comma-separated collection IDs |
| `collection_name` | string | null | Single collection name filter |
| `time_filter` | string | `"today"` | Time period |
| `start_date` / `end_date` | string | null | For custom range |
| `source_type` | string | null | `recording_pipeline` or `instant_detection`. Passed through to VMeta's quality-metrics endpoint. |

**Internal flow:**

When `camera_ids` is provided:
1. Fetches collections from Media service.
2. Matches selected IDs to collection names using `_collection_matches_selected_ids()`.
3. For each matched collection name, queries VMeta: `GET http://localhost:8008/api/v1/mvr/quality-metrics?collection_name={name}&start_time=...&end_time=...`.
4. Aggregates across collections: tracking sessions, individuals, MVR people, videos processed, quality with/without data.
5. Computes weighted average quality and data completeness percentage.

When no filter is provided:
- Calls VMeta quality endpoint with `collection_name=all` for global metrics.

When `collection_name` is provided (single collection mode):
- Calls VMeta quality endpoint with that specific collection name.

**Response structure:**
```json
{
  "time_filter": "today",
  "collection_name": null,
  "tracking_sessions_count": 5,
  "total_individuals": 42,
  "total_mvr_people": 38,
  "total_videos_processed": 120,
  "mvr_with_quality": 35,
  "mvr_without_quality": 3,
  "average_quality": 0.72,
  "min_quality": 0.31,
  "max_quality": 0.95,
  "quality_std_dev": 0.15,
  "quality_grade": "Good",
  "data_completeness": {
    "total": 38,
    "with_data": 35,
    "without_data": 3,
    "percentage": 92.11
  },
  "start_time": "2026-03-19T00:00:00+00:00",
  "end_time": "2026-03-19T14:30:00+00:00",
  "data_source": "MVR → Individual tree (recommended)",
  "generated_at": "2026-03-19T14:30:00+00:00"
}
```

---

## 5. Frontend API Clients

Two API clients provide access to the analytics backend:

### 5.1 `MediaApiClient`

Located in `ppl-meta-frontend/lib/services/media_api_client.dart`. Uses `ApiClient` (Dio-based) with base URL `http://localhost:8080`.

| Method | Endpoint | Sends filter as |
|--------|----------|----------------|
| `getCamerasList()` | `GET /api/v1/analytics/cameras` | _(none)_ |
| `getAnalyticsSummary()` | `GET /api/v1/analytics/summary` | `camera_ids` |
| `getTimeBasedAnalytics()` | `GET /api/v1/analytics/time-series` | `camera_ids` |
| `getDemographicsBreakdown()` | `GET /api/v1/analytics/demographics` | `camera_ids` |
| `getBehavioralAnalytics()` | `GET /api/v1/analytics/behavioral` | `camera_ids` |

All methods send:
- `time_filter` — always
- `camera_ids` — comma-joined selected collection IDs (when filter active)
- `start_date` / `end_date` — when custom range
- `genders` / `age_groups` — comma-joined demographic filters (where applicable)
- `source_type` — sent as `source_type` query parameter when `dataSource` is not `'recording'` (i.e., only sent for instant detection)

### 5.2 `AnalyticsApiClient`

Located in `ppl-meta-frontend/lib/services/analytics_api_client.dart`. Dedicated client for quality metrics.

| Method | Endpoint | Sends filter as |
|--------|----------|----------------|
| `getMvrQualityMetrics()` | `GET /api/v1/analytics/mvr-quality-metrics` | `camera_ids`, `collection_name`, `genders`, `age_groups`, `source_type` |

---

## 6. Data Models

Located in `ppl-meta-frontend/lib/models/analytics_models.dart`.

### `AnalyticsSummary`

The Level 1 data model parsed from `/analytics/summary`.

| Field | Type | Description |
|-------|------|-------------|
| `totalPeople` | int | Aggregate people count across all queried collections |
| `activeCameras` | int | Collections with at least one detection |
| `totalVideos` | int | Total videos analyzed across collections |
| `lastDetection` | DateTime? | Most recent detection timestamp |
| `timeFilter` | String | Applied time filter value |
| `demographics` | Demographics? | Aggregate gender/age breakdown |
| `cameraBreakdown` | List\<CameraAnalytics\> | Per-collection detail |
| `generatedAt` | DateTime | Response generation timestamp |
| `cached` | bool | Whether result came from cache |

### `Demographics`

| Field | Type |
|-------|------|
| `maleCount`, `femaleCount` | int |
| `youngCount`, `adultCount`, `elderlyCount` | int |
| `malePercentage`, `femalePercentage` | double |
| `youngPercentage`, `adultPercentage`, `elderlyPercentage` | double |
| `totalCount` (getter) | `maleCount + femaleCount` |

### `CameraAnalytics`

Per-collection analytics detail within the summary.

| Field | Type |
|-------|------|
| `cameraId` | String |
| `cameraName` | String? |
| `peopleCount` | int |
| `videoCount` | int |
| `demographics` | Demographics? |
| `lastDetection` | DateTime? |
| `cached` | bool |

### `MvrQualityMetrics`

The Level 1.5 MVR quality data model.

| Field | Type | Description |
|-------|------|-------------|
| `trackingSessionsCount` | int | Number of tracking sessions |
| `totalIndividuals` | int | Total unique individuals found |
| `totalMvrPeople` | int | People with MVR data |
| `totalVideosProcessed` | int | Videos analyzed |
| `mvrWithQuality` | int | MVR entries with quality scores |
| `mvrWithoutQuality` | int | MVR entries missing quality |
| `averageQuality` | double? | Mean quality score (0.0–1.0) |
| `minQuality`, `maxQuality` | double? | Quality range |
| `qualityStdDev` | double? | Quality standard deviation |
| `qualityGrade` | String? | Excellent / Good / Fair / Poor / Very Poor |
| `dataCompleteness` | DataCompleteness | Quality data coverage |
| `hasQualityData` (getter) | bool | `mvrWithQuality > 0` |

### `DataCompleteness`

| Field | Type |
|-------|------|
| `total` | int |
| `withData` | int |
| `withoutData` | int |
| `percentage` | double |

### `TimeSeriesDataPoint`

| Field | Type |
|-------|------|
| `timestamp` | DateTime |
| `count` | int |
| `demographics` | Demographics? |

### `TimeBasedAnalytics`

| Field | Type |
|-------|------|
| `timeFilter` | String |
| `dataPoints` | List\<TimeSeriesDataPoint\> |
| `peakCount` | int |
| `peakTime` | DateTime? |
| `averageCount` | double |
| `generatedAt` | DateTime |

---

## 7. UI Layout

The dashboard renders as a scrollable column with pull-to-refresh (`RefreshIndicator`):

```
┌────────────────────────────────────┐
│ CustomAppBar [Refresh] [Filters]   │
├────────────────────────────────────┤
│ Filter Bar (active filters + chip) │
│ [Instant Detection ×] ← orange    │
│   (only shown when active)         │
├────────────────────────────────────┤
│ L1: Basic Metrics                  │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ │People│ │Active│ │Sessns│ │Qualit│
│ │ 42   │ │  3   │ │  15  │ │ Good │
│ └──────┘ └──────┘ └──────┘ └──────┘
├────────────────────────────────────┤
│ L1.5: MVR Quality Metrics          │
│ Tracking sessions, avg quality,    │
│ data completeness %                │
├────────────────────────────────────┤
│ L2: Time-Based Trends              │
│ ┌────────────────────────────────┐ │
│ │  📈 Line chart (fl_chart)      │ │
│ │  hourly or daily data points   │ │
│ └────────────────────────────────┘ │
│ Peak: 14:00 (25)  Avg: 3.5        │
├────────────────────────────────────┤
│ L3: Demographics                   │
│ ┌──────────────┐ ┌──────────────┐  │
│ │ 🥧 Gender    │ │ 🥧 Age       │  │
│ │ Male  59.5%  │ │ Adult  66.7% │  │
│ │ Female 40.5% │ │ Young  23.8% │  │
│ └──────────────┘ │ Elderly 9.5% │  │
│                  └──────────────┘  │
├────────────────────────────────────┤
│ L4: Behavioral Insights            │
│ ┌────────────────────────────────┐ │
│ │ Weekly Heatmap (24h × 7days)   │ │
│ └────────────────────────────────┘ │
│ Peak Hours   Visit Frequency       │
│ 14:00 (25)   New: 60%             │
│ 10:00 (18)   Returning: 30%       │
│              Frequent: 10%         │
│                                    │
│ Camera Comparison (bar chart)      │
└────────────────────────────────────┘
```

**Responsive breakpoints:**
- Mobile: vertical layout, 2-column metric grids
- Tablet/Desktop: horizontal layouts, 4-column metric grids

### Charts and visualizations

| Component | Library | Data source |
|-----------|---------|-------------|
| Time-series line chart | `fl_chart` | `_timeSeriesData.data_points` |
| Gender pie chart | `fl_chart` | `_demographicsData.gender_distribution` |
| Age pie chart | `fl_chart` | `_demographicsData.age_distribution` |
| Weekly heatmap | Custom grid widget | `_behavioralData.weekly_heatmap` (7×24 matrix) |
| Camera comparison bar chart | `fl_chart` | `_behavioralData.camera_comparison` |

### Contextual labels

When the data source is switched to "Instant Detection", certain labels adapt:

| Widget | Recording label | Instant Detection label |
|--------|----------------|------------------------|
| Summary card (L1) | "Videos Analyzed" with movie icon | "Sessions" with visibility icon |
| MVR Quality section (L1.5) | "Videos" with movie icon | "Sessions" with visibility icon |

---

## 8. Filtering Mechanism

### How filtering flows end-to-end

1. **User opens filter dialog** → selects data source, time range, collections, demographics → presses "Apply".
2. **UI extracts collection IDs** using UUID-first priority: `camera['uuid'] ?? camera['id'] ?? camera['device_id'] ?? camera['collection_name'] ?? camera['name']`.
3. **`_loadAnalytics()` re-runs** → each API client method receives the filter values and serializes them as query parameters.
4. **Gateway receives `camera_ids`** → splits comma-separated string into a list.
5. **Gateway resolves collections**: fetches all collections from Media service, then applies `_collection_matches_selected_ids()` which does multi-key matching — comparing the incoming IDs against each collection's `uuid`, `collection_uuid`, `camera_uuid`, `id`, `collection_name`, `name`, `camera_device_id`, and `device_id` fields.
6. **Filtered data** is computed only for matching collections.

### Data source filtering

The `source_type` parameter controls which data pipeline is queried:

1. **Frontend** stores `_dataSource` (`'recording'` or `'instant_detection'`). When not `'recording'`, each API client method adds `source_type` to the query parameters.
2. **Gateway** normalizes the parameter via `_normalize_source_type()`: `null`/`'recording'`/`'recording_pipeline'` → `'recording_pipeline'`; `'instant_detection'` → `'instant_detection'`.
3. **Gateway branches**: If the effective source is `instant_detection`, the endpoint returns early by calling a dedicated helper (e.g., `_get_instant_detection_summary()`) that queries VMeta's `/tracking-sessions/summary` directly. Otherwise, the existing Media-service-based collection iteration runs.
4. **VMeta** filters its SQL queries with `WHERE source_type = $N` on the `tracking_sessions` table. The quality metrics endpoint also accepts `source_type` and filters `individual_mvr_mapping.link_method` accordingly.

### Collection identifier resolution

The gateway uses a UUID-first approach for stable identification:

```python
def _get_collection_identifier(collection: Dict) -> Optional[str]:
    for key in ("uuid", "collection_uuid", "camera_uuid", "id", "collection_name", "name"):
        value = collection.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None
```

For filter matching, `_get_collection_filter_keys()` builds a set of ALL non-empty identifiers from a collection, and incoming filter IDs are checked for intersection with that set. This accommodates clients that might send UUIDs, names, or device IDs.

### Demographic filtering

When demographic filters are active:
- **Summary** uses `_filter_demographics_count()` which estimates intersection assuming gender/age independence: if both gender and age filters are set, `filtered_count = age_count × (gender_count / total_count)`.
- **Demographics** zeros out non-selected categories at the per-camera level before aggregating.
- **Behavioral** applies per-person filtering by checking each MVR person's `gender` and `age_group` fields before processing their appearances.
- **MVR Quality** passes `genders`, `age_groups`, and `source_type` through to the AnalyticsApiClient → VMeta quality endpoint. VMeta's quality-metrics endpoint filters tracking sessions and individual mappings by `source_type`.

---

## 9. Export Feature

The screen supports Excel export via the `excel` package:

1. User clicks Export → selects "Excel Spreadsheet".
2. `_exportToExcel()` creates a workbook with:
   - **Summary sheet**: Report metadata, total people, active cameras, total videos, time filter, demographics overview.
   - **Demographics sheet**: Gender and age distribution tables.
   - **Collection Breakdown sheet**: Per-camera metrics table.
3. On web: triggers browser download via `PlatformFileDownload`.
4. On mobile/desktop: saves to `path_provider`'s temporary directory and opens share sheet via `share_plus`.

---

## 10. Caching Strategy

Analytics data is not cached at the gateway analytics level. Instead, caching leverages the existing camera MVR counter endpoint:

- `GET /api/v1/cameras/{collection_id}/mvr-count` has **10-minute Redis cache TTL**.
- The summary, time-series, demographics, and quality endpoints all query this cached counter (in recording mode), so repeated analytics page loads within the cache window are fast.
- Force-refresh is supported at the summary level (`force_refresh=true`), which passes through to the counter endpoint.
- **Instant detection path**: The VMeta `tracking-sessions/summary` endpoint is not cached at the gateway level. Each request queries VMeta's PostgreSQL database directly. Caching for this path can be added in a future iteration if needed.

---

## 11. Known Limitations

1. **Time-series bucketing**: The time-series endpoint places all aggregated counts into the most recent time bucket rather than distributing detections across their actual timestamps. This produces a flat chart with a single spike at the end.

2. **Visit frequency is simulated**: The behavioral endpoint returns fixed ratios (60/30/10%) for new/returning/frequent visitors rather than tracking actual face re-identification across sessions.

3. **Behavioral skips collections without `camera_device_id`**: Collections lacking this field produce no behavioral data, even if they contain videos with MVR data.

4. **Demographic matrix is estimated**: Cross-tabulations (e.g., "young males") are computed assuming independence between gender and age, which may not reflect actual distributions.

5. **Sequential endpoint calls**: `_loadAnalytics()` calls all 6 endpoints sequentially. Parallelizing these calls would reduce total load time.

6. **No combined data source view**: A "Both" option (showing recording + instant detection data together) is intentionally excluded. The same physical person may appear in both data sources if both pipelines run simultaneously, which would inflate totals. This requires cross-source MVR deduplication logic that is not yet implemented.

7. **Instant detection time-series is approximate**: The instant detection time-series distributes session counts across time buckets rather than using per-detection timestamps. This produces a less granular chart compared to the recording path.

8. **Instant detection behavioral data is simplified**: The behavioral endpoint for instant detection uses the aggregate VMeta summary rather than drilling into individual appearances, so the weekly heatmap and hourly activity are derived from session-level data rather than per-person appearance timestamps.

---

## 12. File Inventory

| File | Purpose |
|------|---------|
| `ppl-meta-frontend/lib/screens/analytics_screen.dart` | Main UI screen (2916 lines): dashboard layout, all section builders, filter dialog, export |
| `ppl-meta-frontend/lib/services/media_api_client.dart` | API client: `getCamerasList`, `getAnalyticsSummary`, `getTimeBasedAnalytics`, `getDemographicsBreakdown`, `getBehavioralAnalytics` |
| `ppl-meta-frontend/lib/services/analytics_api_client.dart` | API client: `getMvrQualityMetrics` |
| `ppl-meta-frontend/lib/models/analytics_models.dart` | Dart models: `AnalyticsSummary`, `Demographics`, `CameraAnalytics`, `MvrQualityMetrics`, `DataCompleteness`, `TimeSeriesDataPoint`, `TimeBasedAnalytics`, `AnalyticsExportData` |
| `ppl-meta-gateway/src/api/v1/analytics.py` | Backend: 7 route handlers, 10 helper functions incl. instant detection helpers (~1900 lines) |
| `ppl-meta-vmeta/src/api/v1/tracking_sessions_summary.py` | VMeta endpoint: `GET /tracking-sessions/summary` — aggregated tracking session data for instant detection analytics |
| `ppl-meta-vmeta/src/api/v1/quality_metrics.py` | VMeta endpoint: quality metrics with `source_type` filtering |
