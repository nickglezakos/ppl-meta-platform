# Route Paging Proposal

## Background

Current behavior: route data for individuals (per camera / per appearance) may include many points. When route data is heavy, server response can be large and user experience can lag (slow response, delayed rendering, browsers hang, memory pressure).

Goal: support progressive route loading and optional full-load action, delivering low-latency interaction for normal cases while making complete data available on demand.

## Requirements

1. Server-side route data must be pageable (offset/limit or cursor-based) per individual/camera search.
2. Client should render initial portion of route immediately; optionally request additional pages lazily or by user action.
3. API should provide route metadata (total points, total segments, packet size heuristics) to drive UI controls.
4. Manual ‘Load more’ control for route points (per route path, combined paths for a super-individual group).
5. No break in existing search API contract; introduce optional query parameters so existing clients continue to work.

## Data model

- `route_point`: { timestamp, x, y, camera_id, video_uuid, person_object_uuid }
- `route_page`: { points: [], page_index, page_size, total_points, has_more }
- `route_summary`: { total_points, total_appearances, start_time, end_time }

## API design

### 1. GET /api/v1/individuals/{individual_uuid}/routes

Query params
- `camera_id` (optional)
- `start_time` (optional)
- `end_time` (optional)
- `page_size` (optional, default 500)
- `page_index` (optional, default 0)
- `cursor` (optional, if cursor-based)
- `include_route` (optional, default true; if false returns metadata only)
- `include_appearances` (optional, default true)

Response
```json
{
  "individual_uuid": "...",
  "route_summary": {
    "total_points": 14392,
    "total_appearances": 28,
    "start_time": "2026-03-30T10:00:00Z",
    "end_time": "2026-03-30T12:15:00Z"
  },
  "page": {
    "page_index": 0,
    "page_size": 500,
    "total_points": 14392,
    "has_more": true
  },
  "points": [ ... ]
}
```

### 2. GET /api/v1/individuals/{individual_uuid}/routes/metadata

(optional) returns only summary values for total points, coverage envelopes, per-camera point counts.

## Paging strategy

- Default `page_size` to 500 (tunable by config); server responds with fewer when segment end reached.
- `page_index` increment to load more pages.
- For low-latency, first page is returned immediately while background fetch can prefetch next pages.
- Add `max_points` API parameter for clients requiring smaller first-page payload.

## Super-individual route considerations

- For merged super-individuals, the client gets combined route pages with `super_individual_uuid` as key.
- Store/return `mvr_source` (original child MVR) with each point so UI can highlight branch.

## UI/UX flow 

1. **Search initiated** — User selects group, cameras, and time range and triggers the analysis.
2. **Immediate skeleton render** — UI shows individual cards with summary data (name, thumbnail, total appearances count) as soon as the metadata response arrives, before route points load.
3. **First page rendered** — Page 0 route points (up to `page_size`) are fetched and drawn on the map/floor plan automatically. A progress indicator shows "Showing X of Y route points".
4. **Incremental prefetch** — While the user reviews the first page, the client silently prefetches page 1 in the background and queues it for display.
5. **Load more control** — When the user clicks the "Load more route points" button on a specific individual card, the next buffered page is painted onto the route and the following page is prefetched.
6. **Per-camera breakdown** — Each camera segment is rendered as a distinct colour/layer so the user can identify camera transitions. Load-more acts per-individual across all cameras.
7. **Load all action** — A "Load all remaining routes" button (visible when `has_more: true`) triggers sequential fetch of all remaining pages and renders them in batches of `page_size` until `has_more: false`. A progress bar shows `loaded / total` points.
8. **Error handling** — If a page fetch fails, the existing rendered route remains visible. A retry control appears inline on the individual card without disrupting other individuals.
9. **Completed state** — When all pages are loaded, the progress indicator is replaced by the final "X total route points across Y cameras" summary label.

## Performance thresholds (recommended starting values)

| Setting | Value | Notes |
|---|---|---|
| Default `page_size` | 500 points | ~50 KB per page at typical coordinate payload size |
| First-page target latency | < 800 ms | Drives skeleton to route render transition |
| Background prefetch trigger | On first-page render complete | Never blocks initial render |
| Auto-load all threshold | <= 3 remaining pages | Trigger silent full-load automatically when remainder is small |
| Hard max points per request | 2000 | Server cap to prevent memory pressure on mobile clients |

## Implementation notes

- The `cursor`-based variant is preferred over `page_index` for large datasets where rows shift between requests (new data arriving during a long session). Cursor encodes the last `(timestamp, person_object_uuid)` seen.
- For the group camera search endpoint (`search_members_in_cameras`), route paging applies per `matched_individual` entry in the response. The `appearances` list is already the full set; paging applies only to point-level route coordinates within each appearance.
- Flutter client should use a `RoutePageController` per individual that manages page state, buffering, and progressive paint calls to the map widget.
- Gateway service should forward `page_size`, `page_index`, and `cursor` transparently to vmeta without transformation.
 
---

## Architecture Clarification: Camera-First Grouping

### Current Issue
The initial implementation groups routes by individual UUID only, ignoring the camera source. This creates problems:

1. **For merged (super-individual) analyses**, route points from the same person across different cameras are aggregated without distinction
2. **Pagination becomes ambiguous**: should "load more" fetch from one camera or try to balance across multiple cameras?
3. **UI cannot show camera transitions**: critical for understanding cross-camera tracking paths
4. **Analytics and reporting are conflated**: cannot separately analyze per-camera behavior

### Correct Architecture: Camera-First, Individual-Second

```
Route Data Hierarchy
├── Camera ID (Source)
│   ├── Individual UUID A
│   │   └── Route Points (paginated per-camera)
│   ├── Individual UUID B
│   │   └── Route Points (paginated per-camera)
│   └── Individual UUID C
│       └── Route Points (paginated per-camera)
├── Camera ID (Source)
│   ├── Individual UUID X
│   │   └── Route Points (paginated per-camera)
│   └── Individual UUID Y
│       └── Route Points (paginated per-camera)
```

### Key Changes to Design

1. **API response includes camera grouping**:
   ```json
   {
     "super_individual_uuid": "...",
     "routes_by_camera": {
       "camera-uuid-1": {
         "camera_id": "camera-uuid-1",
         "camera_name": "Entrance A",
         "individuals": [
           {
             "individual_uuid": "...",
             "route_summary": {...},
             "page": {...},
             "points": [...]
           }
         ],
         "total_points_across_individuals": 3500,
         "has_more": true
       },
       "camera-uuid-2": {...}
     }
   }
   ```

2. **Pagination is per-camera per-individual**: Each camera/individual pair maintains independent pagination state

3. **UI renders with camera toggles**:
   - Top-level camera selector buttons
   - Selected camera shows all individuals with routes from that camera
   - "Load more" button is per-camera (loads next page for all individuals in that camera)
   - Optional: "Load all" aggregates remaining pages from all cameras for the individual

4. **Route points include camera context**:
   ```json
   {
     "timestamp": "2026-03-30T10:00:00Z",
     "x": 100.5,
     "y": 200.3,
     "camera_id": "camera-uuid-1",
     "video_uuid": "video-1",
     "person_object_uuid": "obj-uuid",
     "individual_uuid": "individual-uuid",
     "appearance_index": 0
   }
   ```

---

## Database Schema Analysis

### Current State
- Table: `person_routes` — stores individual route points
  - Columns: `id`, `timestamp`, `x`, `y`, `camera_id`, `video_uuid`, `person_object_uuid`, `individual_uuid`
  - Indexes: likely on `individual_uuid`, `camera_id`, `timestamp`

- Table: `individual_video_appearances` — links individuals to videos/cameras
  - Columns: `id`, `individual_uuid`, `video_uuid`, `camera_id`, `start_time`, `end_time`, `appearance_count`

### Proposed Optimizations

**Index Strategy** (for performance):
```sql
-- Existing (verify presence):
CREATE INDEX idx_person_routes_individual_uuid ON person_routes(individual_uuid);
CREATE INDEX idx_person_routes_camera_id ON person_routes(camera_id);

-- Add (for camera-first pagination):
CREATE INDEX idx_person_routes_camera_individual_timestamp 
  ON person_routes(camera_id, individual_uuid, timestamp);

-- Add (for cursor-based paging):
CREATE INDEX idx_person_routes_timestamp_person_object 
  ON person_routes(timestamp, person_object_uuid, individual_uuid);
```

**Query Analytics** (pre-implementation):
- Analyze table size: `SELECT pg_size_pretty(pg_total_relation_size('person_routes'));`
- Check point distribution: `SELECT camera_id, COUNT(*) as point_count FROM person_routes GROUP BY camera_id;`
- Find heavy individuals: `SELECT individual_uuid, COUNT(*) as point_count FROM person_routes GROUP BY individual_uuid ORDER BY point_count DESC LIMIT 10;`
- Identify index usage: `SELECT * FROM pg_stat_user_indexes WHERE relname = 'person_routes';`

---

## Development Tasks

### Phase 1: Backend (vmeta service)

#### Task 1.1: Database Query Layer
- **File**: `/ppl-meta-vmeta/src/database/mvr_repository.py`
- **Work**:
  - Add new method: `async def get_routes_by_camera_paged(individual_uuid, camera_id, page_index, page_size, start_time, end_time) -> RoutesPageByCameraResponse`
  - Refactor existing `get_individual_routes_paged()` to be a wrapper that calls per-camera grouped version
  - Add cursor-based variant: `async def get_routes_by_camera_cursor(..., cursor: Optional[str]) -> RoutesPageByCameraResponse`
  - Implement cursor encoding: `def encode_cursor(timestamp: datetime, person_object_uuid: str) -> str`
  - Add query helper: `_build_routes_query_per_camera_individual(individual_uuid, camera_id, ...)`
- **Acceptance Criteria**:
  - Queries return camera-grouped responses with independent pagination per camera/individual
  - Cursor-based pagination correctly resumes at last row
  - Performance acceptable (< 200ms for 500-point page on typical DB)

#### Task 1.2: API Response Models
- **File**: `/ppl-meta-vmeta/src/api/models/individual_routes.py`
- **Work**:
  - Add model: `RoutePointWithCamera` (includes `camera_id`, `camera_name`)
  - Add model: `IndividualRoutesInCamera` (individual + points + pagination state within a camera)
  - Add model: `RoutesPageByCameraResponse` (groups individuals by camera, includes per-camera metadata)
  - Extend existing: `RoutePageResponse` to optionally include camera grouping
- **Acceptance Criteria**:
  - All models serialize/deserialize without errors
  - OpenAPI schema correctly represents nested structure

#### Task 1.3: API Endpoint Update
- **File**: `/ppl-meta-vmeta/src/api/routes/individual_routes.py`
- **Work**:
  - Add new handler: `GET /api/v1/individuals/{individual_uuid}/routes/by-camera`
  - Add query params: `camera_id` (optional), `page_index`, `page_size`, `cursor`
  - Implement logic to fetch routes grouped by camera
  - Maintain backward compatibility: existing endpoint (`/individuals/{uuid}/routes`) continues to work but optionally returns camera grouping
  - Add response header: `X-Pagination-Cursor` for cursor-based clients
- **Acceptance Criteria**:
  - Endpoint returns 200 with camera-grouped data
  - Single camera filter works: `?camera_id=uuid&page_index=0`
  - Cursor parameter resumes pagination: `?cursor=<encoded_cursor>&page_index=0`
  - Backward-compatible behavior when camera grouping not requested

### Phase 2: Gateway Service

#### Task 2.1: Proxy Routes to New Endpoint
- **File**: `/ppl-meta-gateway/src/api/v1/router.py`
- **Work**:
  - Add proxy handler: `GET /api/v1/individuals/{individual_uuid}/routes/by-camera`
  - Forward all query parameters and pagination controls
  - Ensure authentication is enforced
- **Acceptance Criteria**:
  - Route accessible via gateway
  - Auth token required
  - Proxy parameters correctly forwarded to vmeta

### Phase 3: Frontend (Flutter)

#### Task 3.1: State Management Refactor
- **File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- **Work**:
  - Refactor route state from `_routePointsByIndividual` to:
    ```dart
    _routePointsByCamera: Map<String, Map<String, RoutePageData>>
    // Structure: camera_id -> individual_uuid -> RoutePageData
    
    _routePageIndexByCamera: Map<String, Map<String, int>>
    // Structure: camera_id -> individual_uuid -> current_page_index
    
    _routeHasMoreByCamera: Map<String, Map<String, bool>>
    // Structure: camera_id -> individual_uuid -> has_more_flag
    
    _selectedCameraId: String? // Currently viewed camera
    _cameraList: List<String> // Available camera IDs from analysis
    ```
  - Define `RoutePageData` model with fields: `points`, `pageIndex`, `pageSize`, `totalPoints`, `hasMore`, `cursor`
- **Acceptance Criteria**:
  - State correctly tracks camera/individual pairs
  - Serialization to/from provider state works
  - No memory leaks when switching cameras

#### Task 3.2: Camera Selection UI
- **File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart` (routes tab section)
- **Work**:
  - Add horizontal camera button row at top of routes tab
  - Buttons display: camera name + point count (e.g., "Entrance A (1250 pts)")
  - Selected button highlighted, unselected buttons muted
  - Implement camera toggle: `void _selectCamera(String cameraId)`
  - Implement: `void _refreshRoutesForSelectedCamera()`
- **Acceptance Criteria**:
  - Camera buttons render correctly
  - Clicking camera button switches displayed routes
  - Route data refetches for new camera

#### Task 3.3: Route Fetching (Camera-Grouped)
- **File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- **Work**:
  - Rename: `_fetchCrossVideoRoutesData()` → `_fetchCrossVideoRoutesByCamera()`
  - New logic:
    1. Fetch metadata for all cameras first
    2. For each camera, fetch routes for all individuals in parallel
    3. Populate `_routePointsByCamera` structure
    4. Auto-select first non-empty camera
  - Implement: `Future<void> _fetchRoutesForCamera(String cameraId, [int pageIndex = 0])`
  - Implement: `Future<void> _loadMoreRoutesForCamera(String cameraId)`
- **Acceptance Criteria**:
  - All camera routes fetched and grouped correctly
  - Pagination state per camera maintained
  - Errors in one camera don't block others

#### Task 3.4: Route Rendering (Camera-Specific)
- **File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- **Work**:
  - Update `_buildRoutesTab()` to:
    - Show camera selector buttons
    - Render only routes for selected camera
    - Show per-camera summary: "X individuals with Y route points from Camera Z"
    - Display "Load more" button per-camera
  - Implement: `Widget _buildCameraButtons()`
  - Implement: `Widget _buildRoutesForCamera(String cameraId)`
  - Implement: `void _onLoadMoreForCamera()`
- **Acceptance Criteria**:
  - Only selected camera's routes visible
  - Load-more button fetches next page for that camera
  - UI updates reactively when pagination state changes

### Phase 4: Data Aggregation & Analytics

#### Task 4.1: Cross-Camera Analysis Helpers
- **File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- **Work**:
  - Add method: `int _getTotalRoutePointsAllCameras()` — aggregates points across all cameras
  - Add method: `int _getTotalIndividualsWithRoutes()` — counts unique individuals with any route data
  - Add method: `List<String> _getCameraIdsWithRoutes()` — returns sorted list of cameras with non-empty route data
  - Add method: `Map<String, int> _getPointsPerCamera()` — returns point count per camera
- **Acceptance Criteria**:
  - Helpers return correct aggregations
  - Used in summary labels and analytics cards

#### Task 4.2: Export/Reporting
- **File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart` + new export module
- **Work**:
  - Add method: `Map<String, dynamic> _exportRoutesAsJson()` — exports all routes grouped by camera/individual
  - Add method: `Future<void> _exportRoutesAsCsv()` — exports as CSV with columns: camera, individual, timestamp, x, y
  - Implement download functionality
- **Acceptance Criteria**:
  - Export formats are valid and usable
  - Large exports don't block UI

---

## Analysis & Research Tasks

### R1: Performance Baseline
- **Goal**: Establish current query performance for different data volumes
- **Work**:
  - Run queries on staging DB for representative datasets:
    - Small individual: 50 points total
    - Medium individual: 500 points total
    - Heavy individual: 5000+ points total
  - Measure query time for:
    - Single-camera routes (cold cache)
    - Multi-camera routes (cold cache)
    - Cursor-based resume (hot cache)
  - Document baseline latencies
- **Deliverable**: Performance baseline report with recommendations for `page_size` tuning

### R2: Cursor Implementation Options
- **Goal**: Decide between offset-based vs. cursor-based pagination
- **Work**:
  - Research cursor encoding strategies:
    - Timestamp + person_object_uuid (recommended)
    - Row ID + offset hybrid
  - Evaluate compatibility with real-time route data (new points arriving during session)
  - Test cursor robustness when underlying data changes
- **Deliverable**: Decision document + cursor encoding implementation guide

### R3: Memory Usage Analysis
- **Goal**: Quantify memory impact of loading large route pages
- **Work**:
  - Load page sizes: 500, 1000, 2000 points
  - Measure app memory before/after for Flutter client
  - Identify point at which memory pressure causes UI jank
  - Recommend hard `max_page_size` limit
- **Deliverable**: Memory profile report + recommended limits

### R4: Database Index Impact
- **Goal**: Validate index improvements
- **Work**:
  - Benchmark queries with/without proposed indexes
  - Measure query time improvement for:
    - Single-camera/individual pagination
    - Cursor-based resume
  - Estimate index storage overhead
- **Deliverable**: Index effectiveness report + final index creation script

### R5: API Versioning Strategy
- **Goal**: Ensure backward compatibility
- **Work**:
  - Document contract guarantees for existing `/individuals/{uuid}/routes` endpoint
  - Identify clients currently using this endpoint
  - Plan deprecation timeline if changes are breaking
  - Design migration path for camera-grouped clients
- **Deliverable**: API versioning plan + migration guide for clients

---

## Migration Strategy

### Phase 1: Non-Breaking Addition (Week 1–2)
1. Deploy new backend query layer (repository methods) — fully isolated, no existing callers changed
2. Deploy new API endpoint `/individuals/{uuid}/routes/by-camera` alongside existing endpoint
3. Existing clients continue using old endpoint, new clients use new endpoint

### Phase 2: Frontend Migration (Week 2–4)
1. Update Flutter frontend to use new camera-grouped endpoint
2. Implement camera selector UI
3. Test with staging data
4. QA and user testing of new routes tab design

### Phase 3: Full Rollout (Week 4+)
1. Deploy updated frontend
2. Monitor for regressions
3. Optionally deprecate old endpoint after settling-in period

### Rollback Plan
- Old endpoint remains functional indefinitely
- Frontend can be rolled back to previous version if critical issues arise
- Database schema remains unchanged (backward compatible)

---

## Testing Strategy

### Unit Tests (Backend)

#### Test Set 1: Repository Layer
- **File**: `/ppl-meta-vmeta/tests/test_mvr_repository.py`
- **Cases**:
  - `test_get_routes_by_camera_paged_single_camera_few_points` — fixture with 10 points, expect page 0
  - `test_get_routes_by_camera_paged_multiple_individuals` — 2 individuals, 1 camera, expect grouped response
  - `test_get_routes_by_camera_paged_multiple_cameras` — 3 cameras, 2 individuals each, expect per-camera grouping
  - `test_get_routes_by_camera_paged_respects_page_size` — request 100 points, verify exactly 100 returned (not fewer)
  - `test_get_routes_by_camera_paged_cursor_resume` — fetch page 0, encode cursor, resume with cursor, verify continuity
  - `test_get_routes_by_camera_paged_missing_table` — if `person_routes` doesn't exist, expect empty response
  - `test_query_performance_budget` — 1000-point query must complete in < 200ms

#### Test Set 2: API Models
- **File**: `/ppl-meta-vmeta/tests/test_models_routes.py`
- **Cases**:
  - `test_route_point_with_camera_serialization` — JSON round-trip
  - `test_routes_page_by_camera_response_nested_structure` — verify nested camera/individual grouping
  - `test_cursor_encoding_decoding` — encode/decode cursor, verify round-trip correctness

#### Test Set 3: API Handlers
- **File**: `/ppl-meta-vmeta/tests/test_routes_handlers.py`
- **Cases**:
  - `test_get_individual_routes_by_camera_requires_auth` — no token → 401
  - `test_get_individual_routes_by_camera_invalid_uuid` — malformed UUID → 400
  - `test_get_individual_routes_by_camera_single_camera_filter` — `?camera_id=X` → only that camera
  - `test_get_individual_routes_by_camera_pagination` — `?page_index=0` → page 0; `?page_index=1` → page 1
  - `test_get_individual_routes_by_camera_cursor_param` — cursor-based pagination works

### Integration Tests (Backend–Database)

#### Test Set 4: End-to-End Backend
- **File**: `/ppl-meta-vmeta/tests/test_integration_routes.py`
- **Cases**:
  - Setup: Create individuals, cameras, video appearances, route points in test DB
  - `test_routes_endpoint_returns_multi_camera_grouped_data` — GET to endpoint, validate response structure
  - `test_routes_endpoint_multi_individual_single_camera` — 2 individuals, 1 camera → returns both
  - `test_routes_endpoint_single_individual_multi_camera` — 1 individual, 3 cameras → returns camera grouping
  - `test_routes_endpoint_pagination_across_pages` — fetch 3 pages sequentially, verify continuity

### Integration Tests (Backend–Gateway)

#### Test Set 5: Gateway Proxy
- **File**: `/ppl-meta-gateway/tests/test_routes_proxy.py`
- **Cases**:
  - `test_gateway_routes_by_camera_proxy_authenticated` — gateway requires auth
  - `test_gateway_routes_by_camera_proxy_forwards_params` — query params forwarded to vmeta
  - `test_gateway_routes_by_camera_proxy_error_handling` — vmeta 500 → gateway 500 (not 200)

### Frontend Tests (Flutter)

#### Test Set 6: State Management
- **File**: `/ppl-meta-frontend/test/screens/person_objects_detail_screen_routes_test.dart`
- **Cases**:
  - `test_route_selection_controller_camera_selection` — selecting camera updates state
  - `test_route_selection_controller_pagination_per_camera` — page index independent per camera
  - `test_route_selection_controller_cursor_encoding` — cursor state preserved across app restart

#### Test Set 7: UI Widgets (Mocked API)
- **File**: `/ppl-meta-frontend/test/screens/person_objects_detail_screen_routes_ui_test.dart`
- **Cases**:
  - `test_routes_tab_camera_buttons_render` — camera selector buttons appear
  - `test_routes_tab_clicking_camera_updates_display` — clicking button updates displayed routes
  - `test_routes_tab_load_more_button_disabled_when_no_more` — button hidden when `has_more: false`
  - `test_routes_tab_load_more_button_fetches_next_page` — clicking button increments `page_index`

#### Test Set 8: E2E with Real Backend (Staging)
- **File**: `/ppl-meta-frontend/test_e2e/routes_e2e_test.dart`
- **Cases**:
  - Setup on staging: Create cross-video analysis with 3 cameras, 2 individuals
  - `test_e2e_routes_tab_loads_and_renders_all_cameras` — all cameras visible on load
  - `test_e2e_routes_tab_switch_camera_refetches_data` — switching camera refetches
  - `test_e2e_routes_tab_pagination_across_pages` — load all pages, verify expected point count

### Performance Tests

#### Test Set 9: Load Testing
- **File**: `/ppl-meta-vmeta/tests/test_performance_routes.py`
- **Cases**:
  - Simulate 10 concurrent requests for large route pages (2000 points)
  - Measure query time, memory, connection pool saturation
  - Verify response time < 800ms SLA even under load

---

## Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Query performance regression | Medium | High | Pre-implementation performance baseline (R1); load testing before rollout |
| Memory pressure on mobile clients | Medium | High | Implement hard `max_page_size` limit (R3); recommend breaking large loads into smaller pages |
| Database index bloat | Low | Medium | Analyze index overhead (R4); consider partitioning if needed |
| Backward incompatibility breaking existing clients | Low | High | Maintain old endpoint indefinitely; version API (R5); migrate clients gradually |
| Cursor encoding bugs in real-time data scenario | Medium | Medium | Implement robust cursor tests (Test Set 3); validate against live data (R2) |
| UI jank during large page renders | Medium | High | Implement incremental painting (batch render every 100 points); test on low-end devices |
| Null pointer crashes when camera data missing | Low | Medium | Comprehensive null-safety testing; add defensive guards in state management |

---

## Success Criteria

- ✅ All development tasks completed
- ✅ All unit, integration, and E2E tests passing
- ✅ Performance meets SLA: first page < 800ms, pagination < 200ms
- ✅ Routes rendered correctly per-camera with camera toggles
- ✅ Load-more pagination works per-camera
- ✅ No memory issues on iOS/Android with 2000-point pages
- ✅ Zero regression in existing routes functionality
- ✅ API versioning plan communicated and agreed
- ✅ User acceptance testing completed successfully
