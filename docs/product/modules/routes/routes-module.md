# Routes Module

## Purpose

This document analyzes how route data is fetched for the Routes tab in the cross-video individual analysis screen.

The main screen involved is:
- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

The route-fetch pipeline spans three layers:
- Flutter UI state and paging orchestration
- Flutter API client request construction
- vmeta backend route endpoints and repository aggregation

## High-Level Flow

1. Cross-video analysis is opened with a `CrossVideoAnalysisContext`.
2. The context carries `sessionData`, including `search_parameters`.
3. The Routes tab calls `_fetchCrossVideoRoutesData()`.
4. The screen resolves one or more source individual UUIDs for each aggregated analysis entry.
5. For each source UUID, the frontend first fetches route metadata grouped by camera.
6. Metadata is filtered to the original search scope before camera chips are registered.
7. The frontend then bootstraps the first visible page of route points per camera.
8. When the user presses Load More, the next page is fetched only for the selected camera.
9. Route points are normalized, deduplicated, and grouped by display individual.
10. The UI renders only the currently selected camera chip.

## Frontend Entry Point

The core logic is in:
- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

Relevant methods:
- `_fetchCrossVideoRoutesData()`
- `_fetchCrossVideoRoutesDataInternal()`
- `_getRouteSearchParams()`
- `_getRouteSearchStartTimeMs()`
- `_getRouteSearchEndTimeMs()`
- `_hasRouteSearchScopeFilter()`
- `_isCameraInSearchScope()`
- `_registerCameraMetadata()`
- `_bootstrapRoutePagesForSource()`
- `_appendCameraGroupedRoutePage()`
- `_buildSelectedCameraPersonGroups()`
- `_loadMoreCrossVideoRoutes()`

### Single-flight protection

`_fetchCrossVideoRoutesData()` uses `_crossVideoRoutesFetchInFlight` to prevent duplicate concurrent fetches caused by repeated widget rebuilds.

That is important because the screen uses async UI rebuild patterns, and without single-flight protection the first page could be appended more than once.

## Search Scope Source

The route module does not invent its own filters. It derives scope from `crossVideoContext.sessionData`.

There are two main origins for this context.

### Camera search flow

Camera search is initiated from:
- `ppl-meta-frontend/lib/widgets/individual_groups/camera_search_dialog.dart`
- `ppl-meta-frontend/lib/screens/individual_groups_screen.dart`

The camera search dialog returns:
- `camera_ids`: collection names, used by the group-camera-search API
- `camera_uuids`: collection UUIDs, used by route filtering
- `camera_names`
- `start_time`
- `end_time`

`individual_groups_screen.dart` forwards those values into `search_parameters` inside the `CrossVideoAnalysisContext`.

### Collection-based cross-video flow

Collection-driven cross-video analysis arrives with top-level session values such as:
- `collection_id`
- `collection_ids`
- `search_parameters`

This matters because the Routes tab must respect both camera-based searches and collection-based searches.

## Frontend Request Sequence

### 1. Metadata request by camera

For each source individual UUID, `_fetchCrossVideoRoutesDataInternal()` calls:
- `IndividualGroupsApiClient.getIndividualRoutesMetadataByCamera()`

Request path:
- `/api/v1/individuals/{individual_uuid}/routes/metadata/by-camera`

Query parameters potentially sent:
- `start_time_ms`
- `end_time_ms`
- optionally `camera_id`

Current cross-video route bootstrap sends time filters but not a single camera filter at this stage. Instead, it fetches grouped metadata and then filters it in Flutter using `_isCameraInSearchScope()`.

This metadata response is used to:
- populate camera chips
n- store total points per camera/source
- initialize `has_more`
- map camera IDs to display names

### 2. First page bootstrap

After metadata registration, `_bootstrapRoutePagesForSource()` loads route points.

There are two modes:

#### Known candidate camera IDs

If metadata has already established candidate cameras for the source individual, the method iterates those cameras and calls:
- `IndividualGroupsApiClient.getIndividualRoutesByCamera()`

with:
- `cameraId`
- `pageIndex`
- `pageSize`
- `startTimeMs`
- `endTimeMs`

Request path:
- `/api/v1/individuals/{individual_uuid}/routes/by-camera`

This is the normal path once metadata has been filtered and registered.

#### Fallback path

If no candidate cameras are known yet, the method makes a grouped call without `cameraId`, but still with:
- `pageIndex = 0`
- `pageSize = _routePageSize`
- `startTimeMs`
- `endTimeMs`

Because the backend may still return multiple camera groups in that response, `_appendCameraGroupedRoutePage()` acts as the final frontend guard and drops any camera group outside the original search scope.

### 3. Load more

When the user requests more points for a selected camera, `_loadMoreCrossVideoRoutes(cameraId)`:
- checks `_routeHasMoreByCameraSource`
- increments the page index per source individual
- calls `getIndividualRoutesByCamera()` with that `cameraId`
- preserves `startTimeMs` and `endTimeMs`

This means pagination is performed per camera and per source individual, not globally across the whole screen.

## Frontend State Model

The screen tracks route state using several maps keyed by camera ID and source individual UUID.

Main structures:
- `_routePointsByCamera`
- `_routePageIndexByCameraSource`
- `_routeHasMoreByCameraSource`
- `_routeTotalPointsByCameraSource`
- `_routeDisplayIndividualByCameraSource`
- `_routeCameraNamesById`
- `_routeDisplayPersonIdByUuid`
- `_loadedRouteSourceIndividuals`

Important behavior:
- `_routePageSize = 100`
- selected camera lives in `_selectedRouteCameraId`
- route point deduplication uses `_routePointKey()`
- camera selection in the UI only changes which grouped state is rendered; it does not refetch everything unless more pages are requested

## Camera Scope Enforcement

The camera-scope bug that existed previously was not primarily a backend bug.

The backend already supported:
- `camera_id`
- `start_time_ms`
- `end_time_ms`

The main issue was identifier mismatch in the frontend.

### What went wrong before

The route endpoints return camera grouping as:
- `camera_id = collection UUID`
- `camera_name = collection name`

But camera-search UI originally stored only collection names in `camera_ids`.

That produced a mismatch:
- search scope held names such as `USB Camera 04`
- route payload grouped by UUID
- simple ID equality checks failed

Also, collection-based searches could carry `collection_id` or `collection_ids` at top-level session data rather than inside `search_parameters`.

### Current fix

The frontend now handles both UUIDs and names.

`_hasRouteSearchScopeFilter()` checks whether the original cross-video session was scoped by:
- `collection_id`
- `collection_ids`
- `camera_uuids`
- `camera_ids`
- `camera_id`

`_isCameraInSearchScope(cameraId, cameraName)` accepts a route camera group if any stored scope value matches either:
- the backend `camera_id` (UUID), or
- the backend `camera_name`

This function is applied in two places:
- when filtering metadata cameras before registration
- inside `_appendCameraGroupedRoutePage()` before any route group is stored

That second guard is critical because even if the request is conceptually scoped, the backend response may still contain multiple camera groups in some call paths.

## Backend API Layer

The FastAPI route handlers live in:
- `ppl-meta-vmeta/src/api/routes/individual_routes.py`

Relevant endpoints:
- `GET /{individual_uuid}/routes/by-camera`
- `GET /{individual_uuid}/routes/metadata`
- `GET /{individual_uuid}/routes/metadata/by-camera`

### Backend request contract

`/{individual_uuid}/routes/by-camera` accepts:
- `page_index`
- `page_size`
- `camera_id`
- `start_time_ms`
- `end_time_ms`

It delegates to:
- `repo.get_individual_routes_by_camera_paged()`

`/{individual_uuid}/routes/metadata/by-camera` accepts:
- `camera_id`
- `start_time_ms`
- `end_time_ms`

It delegates to:
- `repo.get_individual_routes_metadata_by_camera()`

The backend therefore already supports the required route filters.

## Backend Repository Layer

Repository logic lives in:
- `ppl-meta-vmeta/src/database/mvr_repository.py`

Important functions:
- `_fetch_route_source_rows()`
- `_resolve_route_camera_ids()`
- `_build_route_dataset()`
- `_appearance_to_route_point()`
- `get_individual_routes_by_camera_paged()`
- `get_individual_routes_metadata_by_camera()`

### 1. Raw route row fetch

`_fetch_route_source_rows()` reads from `individual_video_appearances` and applies:
- individual UUID scope
- `start_time_ms`
- `end_time_ms`

The SQL orders by `iva.start_timestamp ASC`, which becomes the basis for route point sequencing.

### 2. Camera resolution

`_build_route_dataset()` does not directly join camera metadata from the appearance rows.

Instead, it:
- fetches raw route rows
- collects video UUIDs
- calls `_resolve_route_camera_ids()`

`_resolve_route_camera_ids()` calls the media service search endpoint and maps each `video_uuid` to:
- collection UUID
- collection name

That becomes:
- `camera_id`
- `camera_name`

This is why route grouping in the frontend is collection-oriented rather than raw video-oriented.

### 3. Route point construction

`_appearance_to_route_point()` converts each appearance row into a route point.

Coordinate extraction order:
1. representative face bbox from known payload shapes
2. fallback to `entry_bbox`
3. fallback to `exit_bbox`

The center point becomes:
- `center_x`
- `center_y`

This is the logic that fixed the earlier issue where route points were rendering at `0,0`.

### 4. Grouped paging

`get_individual_routes_by_camera_paged()`:
- builds the full filtered route dataset for the individual
- groups rows by `camera_id`
- optionally filters by the requested `camera_id`
- pages within each camera group
- returns `has_more`, `total_points`, and `points`

This means paging is camera-local, not global.

### 5. Camera metadata

`get_individual_routes_metadata_by_camera()`:
- builds the same filtered route dataset
- groups by `camera_id`
- returns counts and time bounds per camera
- does not return point payloads

That makes it suitable for camera-chip initialization.

## Why the Backend Was Not the Primary Bug

The backend was already able to enforce:
- camera filtering when `camera_id` is sent
- time filtering when `start_time_ms` and `end_time_ms` are sent

The real failures were in how the frontend:
- stored search scope identifiers
- translated search context into route requests
- filtered grouped responses before state registration

In particular:
- camera search stored names, while route grouping used collection UUIDs
- route fetch initially omitted time filters from some calls
- grouped responses could still contain out-of-scope cameras unless Flutter explicitly discarded them

## Current Effective Behavior

After the recent fixes, the effective behavior is:

- Time range from the original cross-video search is forwarded to route metadata fetches, first-page fetches, and load-more fetches.
- Camera scope is enforced both when metadata is registered and when grouped route payloads are appended.
- Camera search now stores UUIDs and names so route grouping can be matched correctly.
- Collection-based cross-video analysis is also respected through top-level `collection_id` or `collection_ids` session values.
- Duplicate page-0 appends are blocked by single-flight fetch control and route-point deduplication.

## Known Design Characteristics

These are not necessarily bugs, but they are important for future work.

### 1. Metadata fetch is broader than final display

The metadata-by-camera request is not always sent with `camera_id`. The frontend can intentionally fetch broader grouped metadata and then narrow it client-side.

That works, but it means the frontend remains responsible for guarding against out-of-scope groups.

### 2. Camera identity is collection identity

The route module treats a camera as the media collection associated with a video, not necessarily a lower-level hardware camera identifier.

That design is consistent with the current media-service mapping, but it should be kept in mind if physical camera IDs and collection IDs diverge further.

### 3. Fallback depends on media service enrichment

If media lookup fails, `_resolve_route_camera_ids()` falls back to using `video_uuid` as both ID and name.

That can degrade grouping semantics and may affect scope matching if the search context expects collection identifiers.

## File Index

Frontend:
- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- `ppl-meta-frontend/lib/services/individual_groups_api_client.dart`
- `ppl-meta-frontend/lib/screens/individual_groups_screen.dart`
- `ppl-meta-frontend/lib/widgets/individual_groups/camera_search_dialog.dart`

Backend:
- `ppl-meta-vmeta/src/api/routes/individual_routes.py`
- `ppl-meta-vmeta/src/database/mvr_repository.py`

## Short Conclusion

The cross-video Routes tab is a hybrid client/server flow.

The backend provides correctly filtered, camera-grouped and time-filtered route data when given the right parameters. The frontend is responsible for:
- deriving route scope from cross-video session context
- converting that scope into API parameters
- enforcing scope again when grouped route payloads are registered
- paging and deduplicating route points per camera/source individual

That client-side scope enforcement is the part that recently required the most fixes.