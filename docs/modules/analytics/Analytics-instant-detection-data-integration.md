# Analytics: Instant Detection Data Integration

**Version**: 1.0  
**Date**: March 19, 2026  
**Status**: Draft  
**Depends on**: [MVR People Persistent Storage for Instant Detection](../../proposals/mvr-people-persistent-storage-for-instant-detection.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Current Analytics Data Path](#current-analytics-data-path)
3. [Design: Data Source Filter](#design-data-source-filter)
4. [Frontend Changes](#frontend-changes)
5. [Backend Changes](#backend-changes)
6. [Widget Behaviour per Data Source](#widget-behaviour-per-data-source)
7. [Edge Cases](#edge-cases)
8. [Implementation Plan](#implementation-plan)

---

## 1. Overview

Once the [MVR People Persistent Storage proposal](../../proposals/mvr-people-persistent-storage-for-instant-detection.md) is implemented, instant detection results are stored as first-class `tracking_sessions`, `individuals`, `individual_video_appearances`, and `mvr_people` records — structurally identical to the recording pipeline data, distinguished only by the `source_type` column (`'recording_pipeline'` vs `'instant_detection'`).

This document analyses how to present that data in the existing analytics dashboard (`http://localhost:3000/#/analytics`) by adding a **single new filter** — **Data Source** — to the existing filter dialog. All five dashboard levels (Summary, MVR Quality, Time Series, Demographics, Behavioral) continue to use their existing widgets, models, and response structures. Only the underlying data source changes based on the filter selection.

### Principle

> **One filter, same widgets, different source.** The analytics screen layout, widget code, and data models require zero changes. The filter dialog gains one new section. Every API call gains one new query parameter. Every backend query gains one new WHERE clause.

---

## 2. Current Analytics Data Path

Each analytics endpoint follows the same pattern today:

```
Filter Dialog  →  Frontend API client  →  Gateway endpoint  →  Data source  →  Response
```

The data sources are:

| Endpoint | Current data source | How data is fetched |
|---|---|---|
| `/analytics/summary` | MVR counter (per collection) | Gateway calls `/cameras/{id}/mvr-count` for each collection, which queries Media (videos) → VMeta (MVR count by videos) |
| `/analytics/time-series` | MVR counter (per collection) | Same as summary, bucketed into time intervals |
| `/analytics/demographics` | MVR counter (per collection) | Same as summary, demographics broken out per camera |
| `/analytics/behavioral` | MVR people search (per video) | Gateway queries Media (videos) → VMeta (`/mvr-people/search/by-videos`) → individual appearances |
| `/analytics/mvr-quality-metrics` | Tracking sessions + MVR people | Gateway queries VMeta (`/mvr/quality-metrics`) → `tracking_sessions` table + `mvr_people` table |
| `/analytics/cameras` | Collections from Media service | Unchanged — not affected by source type |

### Key observation

All endpoints ultimately derive their data from two VMeta tables:

1. **`tracking_sessions`** — session counts, individuals found, unique MVR people count, date ranges
2. **`mvr_people`** — face quality, demographics, appearance counts

Both tables gain the `source_type` column in the storage proposal. Filtering by `source_type` at the VMeta query level is sufficient to switch the entire analytics dashboard between recording pipeline data and instant detection data.

---

## 3. Design: Data Source Filter

### Filter values

| Value | Label in UI | `source_type` sent to backend | Description |
|---|---|---|---|
| `recording` | **Video Recording** | `recording_pipeline` | Data from the recording pipeline: video segments → Vision → Orchestrator → VMeta tracking sessions. **This is the default.** |
| `instant_detection` | **Instant Detection** | `instant_detection` | Data from instant detection: live frames → Vision → Orchestrator → VMeta identity resolution → persisted sessions. |

### Default: `recording`

The default selection is **Video Recording**. This preserves the current analytics behaviour — users see exactly the same data they see today. The analytics dashboard only shows instant detection data when the user explicitly selects it via the filter dialog.

### Why not "Both"?

A combined view (recording + instant detection) is intentionally excluded from the initial implementation for two reasons:

1. **Double-counting risk**: If both pipelines run simultaneously on the same camera, the same physical person appears in both data sources. A combined view would inflate totals unless MVR-level deduplication is applied. This deduplication requires cross-source MVR matching logic that is not yet implemented.

2. **Clarity**: Users need to understand what they are looking at. Recording data has different temporal characteristics (30-second segments, post-processed) than instant detection data (5-second cycles, real-time). Mixing them produces ambiguous time-series and behavioral patterns.

A "Both (deduplicated)" option can be added in a future iteration once cross-source MVR deduplication is implemented in the gateway.

---

## 4. Frontend Changes

### 4.1 Filter dialog — new section

A new **Data Source** section is added to the `_FilterDialog` widget, positioned **above** the existing Time Range section (it is the most fundamental filter — it determines what all other filters operate on):

```dart
// New state variable in _FilterDialog
String _dataSource = 'recording'; // Default

// In the filter dialog body, before the Time Range section:
Column(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    Text('Data Source', style: TextStyle(
      fontSize: 16, fontWeight: FontWeight.w600,
    )),
    const SizedBox(height: 8),
    Wrap(
      spacing: 8,
      children: [
        ChoiceChip(
          label: const Text('Video Recording'),
          selected: _dataSource == 'recording',
          onSelected: (_) => setState(() => _dataSource = 'recording'),
          selectedColor: Colors.blue.shade100,
          avatar: _dataSource == 'recording'
              ? const Icon(Icons.videocam, size: 18)
              : const Icon(Icons.videocam_outlined, size: 18),
        ),
        ChoiceChip(
          label: const Text('Instant Detection'),
          selected: _dataSource == 'instant_detection',
          onSelected: (_) => setState(() => _dataSource = 'instant_detection'),
          selectedColor: Colors.orange.shade100,
          avatar: _dataSource == 'instant_detection'
              ? const Icon(Icons.visibility, size: 18)
              : const Icon(Icons.visibility_outlined, size: 18),
        ),
      ],
    ),
    const SizedBox(height: 4),
    Text(
      _dataSource == 'recording'
          ? 'Analytics from video recording sessions (default)'
          : 'Analytics from real-time instant detection sessions',
      style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
    ),
  ],
),
```

### 4.2 Filter dialog return value

The dialog result map gains one new key:

```dart
// Updated return value from _FilterDialog
{
  'dataSource': String,           // NEW — 'recording' or 'instant_detection'
  'timeFilter': String,
  'collectionIds': List<String>,
  'genders': List<String>,
  'ageGroups': List<String>,
  'autoRefresh': bool,
  'startDate': DateTime?,
  'endDate': DateTime?,
}
```

### 4.3 Analytics screen state

One new state variable in `_AnalyticsScreenState`:

```dart
String _dataSource = 'recording'; // Default — recording pipeline data
```

Updated in `_applyFilters()` when the filter dialog returns:

```dart
void _applyFilters(Map<String, dynamic> filters) {
  setState(() {
    _dataSource = filters['dataSource'] as String? ?? 'recording';
    _timeFilter = filters['timeFilter'] as String;
    _selectedCollectionIds = filters['collectionIds'] as List<String>;
    // ... existing filter assignments ...
  });
  _loadAnalytics();
}
```

### 4.4 Active filter bar indicator

The existing filter bar (the row below the app bar showing active filters) gains a chip for the data source when it is not the default:

```dart
// In the active filter bar, only shown when _dataSource != 'recording'
if (_dataSource == 'instant_detection')
  Chip(
    label: const Text('Instant Detection'),
    avatar: const Icon(Icons.visibility, size: 16),
    backgroundColor: Colors.orange.shade100,
    deleteIcon: const Icon(Icons.close, size: 16),
    onDeleted: () {
      setState(() => _dataSource = 'recording');
      _loadAnalytics();
    },
  ),
```

This gives the user clear visual feedback that they are viewing instant detection data, and a one-tap way to reset to the default.

### 4.5 API client changes

Every analytics method in `MediaApiClient` and `AnalyticsApiClient` gains one new optional parameter:

```dart
Future<ApiResponse<Map<String, dynamic>>> getAnalyticsSummary({
  String timeFilter = 'today',
  List<String>? cameraIds,
  bool forceRefresh = false,
  DateTime? startDate,
  DateTime? endDate,
  List<String>? genders,
  List<String>? ageGroups,
  String? dataSource,           // NEW — 'recording' or 'instant_detection'
}) async {
  final queryParams = <String, dynamic>{
    'time_filter': timeFilter,
    'force_refresh': forceRefresh,
  };
  
  // NEW — only send when not default
  if (dataSource != null && dataSource != 'recording') {
    queryParams['source_type'] = dataSource;
  }
  
  // ... existing parameter handling ...
}
```

The same pattern applies to `getTimeBasedAnalytics()`, `getDemographicsBreakdown()`, `getBehavioralAnalytics()`, and `getMvrQualityMetrics()`.

**Query parameter name**: `source_type` — matches the database column name for consistency.

**Default omission**: When the value is `'recording'` (the default), the parameter is not sent. This means existing backend code continues to work without changes during a rolling deployment — the absence of `source_type` implicitly means recording pipeline data.

### 4.6 Analytics screen — passing the filter to API calls

In `_loadAnalytics()`, every API call receives the new parameter:

```dart
Future<void> _loadAnalytics() async {
  // 1. Cameras list — unchanged (not affected by source type)
  await _loadCamerasList();
  
  // 2. Summary
  final summaryResponse = await _mediaApiClient.getAnalyticsSummary(
    timeFilter: _timeFilter,
    cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
    startDate: _startDate,
    endDate: _endDate,
    genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
    ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
    dataSource: _dataSource,           // NEW
  );
  
  // 3. MVR Quality
  final qualityResponse = await _analyticsApiClient.getMvrQualityMetrics(
    timeFilter: _timeFilter,
    cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
    startDate: _startDate,
    endDate: _endDate,
    dataSource: _dataSource,           // NEW
  );
  
  // 4. Time Series
  final timeSeriesResponse = await _mediaApiClient.getTimeBasedAnalytics(
    timeFilter: _timeFilter,
    cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
    startDate: _startDate,
    endDate: _endDate,
    dataSource: _dataSource,           // NEW
  );
  
  // 5. Demographics
  final demographicsResponse = await _mediaApiClient.getDemographicsBreakdown(
    timeFilter: _timeFilter,
    cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
    startDate: _startDate,
    endDate: _endDate,
    genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
    ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
    dataSource: _dataSource,           // NEW
  );
  
  // 6. Behavioral
  final behavioralResponse = await _mediaApiClient.getBehavioralAnalytics(
    timeFilter: _timeFilter,
    cameraIds: _selectedCollectionIds.isNotEmpty ? _selectedCollectionIds : null,
    startDate: _startDate,
    endDate: _endDate,
    genders: _selectedGenders.isNotEmpty ? _selectedGenders : null,
    ageGroups: _selectedAgeGroups.isNotEmpty ? _selectedAgeGroups : null,
    dataSource: _dataSource,           // NEW
  );
}
```

### 4.7 No model changes

The `AnalyticsSummary`, `MvrQualityMetrics`, `TimeBasedAnalytics`, `Demographics`, and `CameraAnalytics` models remain identical. The response shape from each endpoint does not change — only the underlying rows queried change.

---

## 5. Backend Changes

### 5.1 New query parameter on all analytics endpoints

Every analytics endpoint in the gateway (`ppl-meta-gateway/src/api/v1/analytics.py`) gains one optional parameter:

```python
@router.get("/analytics/summary")
async def get_analytics_summary(
    # ... existing parameters ...
    source_type: Optional[str] = Query(
        None,
        description="Data source filter: 'recording_pipeline' or 'instant_detection'. "
                    "When omitted, defaults to 'recording_pipeline'."
    ),
    current_user: dict = Depends(get_current_user)
):
    # Normalize: absent or 'recording' → 'recording_pipeline'
    effective_source = _normalize_source_type(source_type)
    # ... pass effective_source to all downstream calls ...
```

Helper:

```python
def _normalize_source_type(source_type: Optional[str]) -> str:
    """Normalize source_type parameter to database column value."""
    if source_type in (None, 'recording', 'recording_pipeline'):
        return 'recording_pipeline'
    if source_type in ('instant_detection',):
        return 'instant_detection'
    return 'recording_pipeline'  # Safe default
```

### 5.2 Summary endpoint — source-aware MVR counting

The summary endpoint currently calls the cached MVR counter (`/cameras/{id}/mvr-count`) for each collection. This endpoint queries videos via Media → then VMR count-by-videos via VMeta.

For instant detection data, there are no videos to search by. Instead the endpoint needs to query VMeta tracking sessions directly. Two approaches:

**Approach A — New VMeta endpoint (recommended)**:

Add a new VMeta endpoint: `GET /api/v1/tracking-sessions/summary`:

```python
@router.get("/tracking-sessions/summary")
async def get_tracking_session_summary(
    source_type: str = Query("recording_pipeline"),
    camera_device_id: Optional[str] = Query(None),
    start_time: str = Query(...),
    end_time: str = Query(...),
):
    """
    Aggregate individuals and MVR people from tracking sessions,
    filtered by source_type and optional camera.
    """
```

This endpoint runs one SQL query:

```sql
SELECT
    COUNT(DISTINCT ts.session_uuid) AS session_count,
    SUM(ts.individuals_found) AS total_individuals,
    SUM(ts.unique_mvr_people_count) AS total_mvr_people
FROM tracking_sessions ts
WHERE ts.source_type = $1
  AND ts.created_at >= $2
  AND ts.created_at <= $3
  AND ($4::text IS NULL OR ts.camera_device_id = $4)
  AND ts.status = 'completed'
```

And a companion demographics query over the individuals linked to those sessions:

```sql
SELECT
    COUNT(*) FILTER (WHERE i.demographics->>'gender' = 'Male') AS total_male,
    COUNT(*) FILTER (WHERE i.demographics->>'gender' = 'Female') AS total_female,
    COUNT(*) FILTER (WHERE (i.demographics->>'age_min')::int < 21) AS total_young,
    COUNT(*) FILTER (WHERE (i.demographics->>'age_min')::int >= 21) AS total_adult,
    COUNT(*) FILTER (WHERE (i.demographics->>'age_min')::int >= 65) AS total_elderly
FROM individuals i
JOIN tracking_sessions ts ON i.session_uuid = ts.session_uuid
WHERE ts.source_type = $1
  AND ts.created_at >= $2
  AND ts.created_at <= $3
  AND ($4::text IS NULL OR ts.camera_device_id = $4)
  AND ts.status = 'completed'
```

**Gateway integration**:

The summary endpoint branches based on `source_type`:

```python
if effective_source == 'recording_pipeline':
    # Existing path — iterate collections, call /cameras/{id}/mvr-count
    ...
elif effective_source == 'instant_detection':
    # New path — call VMeta tracking-sessions/summary per camera
    for camera in cameras:
        result = await vmeta_client.get(
            "/api/v1/tracking-sessions/summary",
            params={
                "source_type": "instant_detection",
                "camera_device_id": camera.get("device_id"),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }
        )
        # Aggregate into same response shape as existing summary
```

The response structure is identical — `total_people`, `active_cameras`, `demographics`, `camera_breakdown` — all populated from the tracking session summary instead of the MVR counter.

**Approach B — Extend existing counter**: Add `source_type` param to the cached MVR counter endpoint so it can filter tracking sessions instead of videos. This is more invasive and conflates two different query paths in one endpoint.

**Recommendation**: Approach A. A dedicated VMeta endpoint keeps concerns separate and is easier to test.

### 5.3 Time-series endpoint — source-aware time bucketing

For recording data, the current implementation buckets MVR counts into hourly/daily slots (simplified — all counts go into last bucket).

For instant detection data, the time-series endpoint can produce accurate distribution because instant detection tracking sessions have continuous timestamps:

```sql
SELECT
    date_trunc($1, i.created_at) AS bucket,
    COUNT(DISTINCT i.individual_uuid) AS count
FROM individuals i
JOIN tracking_sessions ts ON i.session_uuid = ts.session_uuid
WHERE ts.source_type = 'instant_detection'
  AND ts.created_at >= $2
  AND ts.created_at <= $3
GROUP BY bucket
ORDER BY bucket
```

Where `$1` is `'hour'` or `'day'` depending on the interval parameter.

This is a significant improvement over the recording pipeline time-series (which currently puts all counts in the last bucket). Instant detection data enables proper temporal distribution.

### 5.4 Demographics endpoint — source-aware demographics

Same pattern. When `source_type = 'instant_detection'`:

- Query `individuals` joined to `tracking_sessions WHERE source_type = 'instant_detection'`
- Extract gender/age demographics from the individual records
- Build the same response shape (gender_distribution, age_distribution, demographic_matrix, camera_breakdown)

The demographics response structure is unchanged. Only the SQL WHERE clause gains `AND ts.source_type = $source_type`.

### 5.5 Behavioral endpoint — source-aware appearances

The behavioral endpoint currently queries individual video appearances via MVR people search. For instant detection:

- Query `individual_video_appearances` joined through `individuals` → `tracking_sessions WHERE source_type = 'instant_detection'`
- Each appearance has a `start_timestamp` that can be bucketed into hourly_activity, daily_activity, and weekly_heatmap
- Peak hours and peak days are computed the same way
- Camera comparison uses `tracking_sessions.camera_device_id`

Because instant detection produces high-frequency appearance records (every 5 × storage_multiple seconds), the behavioral data will be richer and more accurately distributed than recording pipeline data.

### 5.6 MVR quality metrics endpoint — source-aware sessions

The VMeta `/mvr/quality-metrics` endpoint already queries `tracking_sessions`. Adding source_type filtering requires one change to the SQL:

**Current query:**
```sql
SELECT session_uuid, individuals_found, unique_mvr_people_count, ...
FROM tracking_sessions
WHERE created_at >= $1 AND created_at <= $2
  AND status = 'completed'
```

**Updated query:**
```sql
SELECT session_uuid, individuals_found, unique_mvr_people_count, ...
FROM tracking_sessions
WHERE created_at >= $1 AND created_at <= $2
  AND status = 'completed'
  AND ($3::text IS NULL OR source_type = $3)
```

When `source_type` is not provided, the `$3::text IS NULL` clause is true and all sessions are included (backward compatible). When `'instant_detection'` is provided, only instant detection sessions are counted.

The gateway passes the parameter through:

```python
# In get_mvr_quality_metrics():
params = {
    "start_time": start_time.isoformat(),
    "end_time": end_time.isoformat(),
    "collection_name": collection_name,
}
if effective_source != 'recording_pipeline':
    params["source_type"] = effective_source
```

### 5.7 Cameras list endpoint — unchanged

The `/analytics/cameras` endpoint returns collections from the Media service. This is not affected by source type — both recording and instant detection can operate on the same cameras/collections. The filter dialog continues to show all collections regardless of which data source is selected.

---

## 6. Widget Behaviour per Data Source

All five dashboard levels use the same widgets, same models, same rendering logic. The table below shows what the user sees when switching between data sources:

### L1: Basic Metrics (Summary)

| Metric | Recording (default) | Instant Detection |
|--------|:--:|:--:|
| **Total People** | MVR people count from video processing | MVR people count from instant detection sessions |
| **Active Cameras** | Collections with detections from video processing | Cameras with instant detection sessions in time range |
| **Total Videos** | Count of processed video segments | `0` (instant detection produces no videos — display as "N/A" or "—") |
| **Last Detection** | Latest video processing timestamp | Latest instant detection cycle timestamp |
| **Demographics** | Gender/age from video MVR counter | Gender/age from instant detection individuals |
| **Camera Breakdown** | Per-collection detail | Per-camera detail (via `camera_device_id`) |

**Note on "Total Videos"**: This metric is meaningless for instant detection. Two options:
- Display `0` (the value returned by the backend)
- Display "N/A" or replace the label with "Detection Cycles" showing the count of persisted cycles

Recommendation: Display a context-appropriate label. When `_dataSource == 'instant_detection'`, the summary card widget can show "Detection Cycles" instead of "Total Videos", using the `tracking_sessions_count` from the quality metrics endpoint as the value. This is a minor frontend-only change in the summary card builder:

```dart
// In the summary metrics row:
_buildMetricCard(
  title: _dataSource == 'instant_detection' ? 'Sessions' : 'Videos',
  value: _dataSource == 'instant_detection'
      ? '${_mvrQualityMetrics?.trackingSessionsCount ?? 0}'
      : '${_analyticsSummary?.totalVideos ?? 0}',
  icon: _dataSource == 'instant_detection'
      ? Icons.visibility
      : Icons.video_library,
),
```

### L1.5: MVR Quality Metrics

| Metric | Recording | Instant Detection |
|--------|:--:|:--:|
| **Tracking Sessions** | Count from recording sessions | Count from instant detection sessions |
| **Total Individuals** | Individuals from video processing | Individuals from instant detection |
| **Total MVR People** | MVR people count | MVR people count (includes promoted isolateds) |
| **Videos Processed** | Video count | `0` — same display consideration as above |
| **Quality Scores** | Face quality from MVR pipeline | Face quality from instant detection MVR entries |

### L2: Time Trends (Time Series)

| Aspect | Recording | Instant Detection |
|--------|:--:|:--:|
| **Temporal resolution** | Coarse — currently all in last bucket (known limitation) | Fine — individual appearances have precise timestamps, enabling accurate hourly/daily distribution |
| **Chart shape** | Flat with spike at end (limitation) | Smooth curve reflecting actual detection patterns |
| **Peak detection** | Approximate | Accurate — based on real appearance timestamps |

This is an area where instant detection data produces **better analytics** than the current recording pipeline implementation.

### L3: Demographics

| Aspect | Recording | Instant Detection |
|--------|:--:|:--:|
| **Gender/Age data** | From MVR counter demographics | From individual records linked to instant detection sessions |
| **Per-camera breakdown** | Per collection | Per camera (via `camera_device_id` on tracking sessions) |
| **Demographic matrix** | Estimated via independence assumption | Same approach — marginal counts available |

### L4: Behavioral

| Aspect | Recording | Instant Detection |
|--------|:--:|:--:|
| **Weekly heatmap** | From individual appearances (video-based) | From individual appearances (frame-based, higher frequency) |
| **Peak hours/days** | Derived from video timestamps | Derived from detection cycle timestamps (more granular) |
| **Visit frequency** | Currently simulated (60/30/10 fixed ratio) | Still simulated — same limitation applies |
| **Camera comparison** | By collection | By camera device |

---

## 7. Edge Cases

### 7.1 No instant detection data

When the user selects "Instant Detection" but no sessions exist (e.g., detection was never run with persistence enabled), all endpoints return zeros. The dashboard handles this gracefully already — it shows empty states with "No data available" messages. No special handling needed.

### 7.2 Simultaneously running pipelines

If both recording and instant detection are running on the same camera, the same physical person will have:
- An MVR entry from the recording pipeline (via `process_single_media_for_mvr`)
- Potentially the **same** MVR entry referenced from instant detection (if `identify-face` matched it)
- Or a **different** MVR entry if the embeddings diverge (128-dim Vision → 512-dim FaceNet conversion is non-deterministic at boundary similarity scores)

When viewing recording data, the user sees recording-sourced counts. When viewing instant detection data, the user sees detection-sourced counts. There is no cross-contamination because `source_type` on `tracking_sessions` and `individuals` cleanly separates them.

### 7.3 Custom date ranges

The custom date range picker works identically for both data sources. The backend applies the same `start_time`/`end_time` parameters when querying tracking sessions, regardless of source type.

### 7.4 Collection filter interaction

Collections are camera-based. Instant detection sessions have `camera_device_id`. If the user selects "Instant Detection" and filters to specific collections, the backend maps collection IDs to camera device IDs for the VMeta query. Collections with no associated camera device ID return zero results (same as the current behavioral endpoint, which already skips collections without `camera_device_id`).

### 7.5 Filter persistence

The data source selection should persist with the same mechanism as other filters — stored in the screen state and passed back/forth through the filter dialog. It does **not** persist across page navigations or app restarts (same as existing filters). On every fresh visit to the analytics page, the default is "Video Recording".

### 7.6 Auto-refresh with source filter

The 10-minute auto-refresh timer uses the current filter state, including `_dataSource`. When auto-refresh fires, it reloads all data with the active data source selection — no special handling needed.

---

## 8. Implementation Plan

### Phase 1: Backend — VMeta source-aware queries

- [ ] Add optional `source_type` parameter to VMeta `/mvr/quality-metrics` endpoint
- [ ] Add `AND source_type = $N` clause to `tracking_sessions` query (NULL-safe for backward compat)
- [ ] Add `AND source_type = $N` clause to `mvr_people` query
- [ ] Create new VMeta endpoint `GET /api/v1/tracking-sessions/summary` for aggregated session counts with demographics, filtered by `source_type` and `camera_device_id`
- [ ] Test: existing calls without `source_type` return same results as before

### Phase 2: Backend — Gateway routing

- [ ] Add `source_type` query parameter to all 5 analytics endpoints (summary, time-series, demographics, behavioral, mvr-quality-metrics)
- [ ] Add `_normalize_source_type()` helper
- [ ] Summary endpoint: branch on `source_type` — recording path (existing) vs instant detection path (new VMeta endpoint)
- [ ] Time-series endpoint: for instant detection, query individual appearances bucketed by time
- [ ] Demographics endpoint: for instant detection, query individuals by session source type
- [ ] Behavioral endpoint: for instant detection, query appearances through session source type
- [ ] MVR quality endpoint: pass `source_type` through to VMeta
- [ ] Cache key: include `source_type` in the Redis cache key to avoid cross-contamination between data sources

### Phase 3: Frontend — filter dialog

- [ ] Add `_dataSource` state variable to `_FilterDialog` (default: `'recording'`)
- [ ] Add Data Source section with two `ChoiceChip` widgets (Video Recording, Instant Detection)
- [ ] Add `'dataSource'` key to filter dialog return map
- [ ] Add `_dataSource` state variable to `_AnalyticsScreenState`
- [ ] Read `dataSource` from filter result in `_applyFilters()`
- [ ] Add active filter chip for instant detection in the filter bar

### Phase 4: Frontend — API client integration

- [ ] Add `dataSource` parameter to `MediaApiClient.getAnalyticsSummary()`
- [ ] Add `dataSource` parameter to `MediaApiClient.getTimeBasedAnalytics()`
- [ ] Add `dataSource` parameter to `MediaApiClient.getDemographicsBreakdown()`
- [ ] Add `dataSource` parameter to `MediaApiClient.getBehavioralAnalytics()`
- [ ] Add `dataSource` parameter to `AnalyticsApiClient.getMvrQualityMetrics()`
- [ ] Pass `_dataSource` from `_loadAnalytics()` to all API calls
- [ ] Only send `source_type` query param when value is not `'recording'` (backward compat)

### Phase 5: Frontend — contextual labels

- [ ] Summary card: show "Sessions" instead of "Videos" when data source is instant detection
- [ ] Summary card: use `Icons.visibility` instead of `Icons.video_library` for instant detection
- [ ] Optional: add a subtle banner or subtitle under the AppBar indicating the active data source

---

## Appendix: Parameter Flow Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                    Filter Dialog                                  │
│                                                                  │
│  ○ Video Recording (default)    ● Instant Detection              │
│                                                                  │
│  Time Range: [Today ▾]   Collections: [All ▾]                   │
│  Gender: [All]           Age: [All]                              │
│  Auto-refresh: [ON]                                              │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼ returns { dataSource: 'instant_detection', ... }
┌─────────────────────────┴────────────────────────────────────────┐
│              AnalyticsScreen._loadAnalytics()                     │
│                                                                  │
│  _dataSource = 'instant_detection'                               │
│  Passes to all 5 API calls                                       │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼ source_type=instant_detection (query param)
┌─────────────────────────┴────────────────────────────────────────┐
│              Gateway /api/v1/analytics/*                          │
│                                                                  │
│  effective_source = 'instant_detection'                           │
│                                                                  │
│  /summary       → VMeta /tracking-sessions/summary               │
│  /time-series   → VMeta individual appearances bucketed          │
│  /demographics  → VMeta individuals by session source            │
│  /behavioral    → VMeta appearances by session source            │
│  /quality       → VMeta /mvr/quality-metrics?source_type=...     │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼ WHERE source_type = 'instant_detection'
┌─────────────────────────┴────────────────────────────────────────┐
│              VMeta Database                                       │
│                                                                  │
│  tracking_sessions  WHERE source_type = 'instant_detection'      │
│  individuals        WHERE source_type = 'instant_detection'      │
│  mvr_people         (via individual_mvr_mapping link)             │
│                                                                  │
│  Same tables, same schema, same response shape                   │
└──────────────────────────────────────────────────────────────────┘
```
