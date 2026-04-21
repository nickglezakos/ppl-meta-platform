# individual groups module

## Introduction

### How Individual Groups Work (high level)
- The page at /#/individual-groups is a dedicated management UI for group collections of known individuals, wired from [ppl-meta-frontend/lib/presentation/navigation/app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart#L263-L271) and implemented in [ppl-meta-frontend/lib/screens/individual_groups_screen.dart](ppl-meta-frontend/lib/screens/individual_groups_screen.dart#L20-L30).
- The list screen supports search, visibility filtering, grid/list view toggle, pull-to-refresh, and group creation; it fetches groups from `/api/v1/individual-groups` and creates groups via the same resource, see [ppl-meta-frontend/lib/screens/individual_groups_screen.dart](ppl-meta-frontend/lib/screens/individual_groups_screen.dart#L45-L93) and [ppl-meta-frontend/lib/services/individual_groups_api_client.dart](ppl-meta-frontend/lib/services/individual_groups_api_client.dart#L29-L94).
- Group detail is accessed via `/individual-groups/:groupId` and focuses on member management and analysis workflows (edit group, add/remove members, naming, selection, cross-video analysis launch), see [ppl-meta-frontend/lib/presentation/navigation/app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart#L268-L276) and [ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart](ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart#L27-L76).
- In group detail, each member card shows a numbered label (`Group Member NN`) sourced from `group_member_number` (with UI fallback to index order), and also shows any user-defined member name when available (otherwise short ID fallback), see [ppl-meta-frontend/lib/models/individual_group_models.dart](ppl-meta-frontend/lib/models/individual_group_models.dart) and [ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart](ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart).

### Runtime Flow
- Frontend calls vmeta endpoints through `IndividualGroupsApiClient` for CRUD, membership operations, camera search, duplicate detection, and member merge (`/api/v1/individual-groups/*`), see [ppl-meta-frontend/lib/services/individual_groups_api_client.dart](ppl-meta-frontend/lib/services/individual_groups_api_client.dart#L29-L477).
- Vmeta exposes REST routes for group lifecycle, membership, individual-to-group lookup, bulk operations, camera search, duplicate checks, and merge flow, see [ppl-meta-vmeta/src/api/routes/individual_groups.py](ppl-meta-vmeta/src/api/routes/individual_groups.py#L35-L646).
- `IndividualGroupsManager` is the orchestration layer: it persists groups/memberships in vmeta DB, executes camera/member search, and performs duplicate + merge workflows against person/MVR data, see [ppl-meta-vmeta/src/services/individual_groups_manager.py](ppl-meta-vmeta/src/services/individual_groups_manager.py#L33-L1882).
- Member naming and numbering are resolved as part of member listing: backend returns `group_member_number` plus latest resolved person `name` metadata (`name_updated_at`, `name_updated_by`), and frontend renders these values in the member grid and detail dialogs.

## Current implementation (concise)

### Module boundaries
- Frontend (`/individual-groups`, `/individual-groups/:groupId`) owns group UX and member interaction.
- Vmeta API owns Individual Groups endpoints and business orchestration.
- Vmeta DB stores groups, memberships, metadata, and lookup state.
- Cross-video/person analysis screens consume selected group members as downstream workflows.

### Data model summary
- Group core fields: `id`, `name`, `description`, `created_by`, `visibility`, `tags`, `member_ids`, `member_count`, `cover_individual_id`, `metadata`.
- Membership is represented as a junction entity (`group_id` <-> `individual_id`) with audit fields (`added_by`, `added_at`, optional `notes`).
- Member presentation fields include `group_member_number` (display numbering in group context) and user-defined naming fields `name`, `name_updated_at`, `name_updated_by`.
- API contracts include camera search (`camera_id`/`camera_ids`, time window, confidence threshold) and merge/duplicate models for de-duplication.

### API example (member numbering + user-defined name)
- Endpoint: `GET /api/v1/individual-groups/{groupId}/members?skip=0&limit=50`
- Relevant response fields used by UI:

```json
{
	"members": [
		{
			"id": "7a7b5e90-5e53-4d59-9bca-2c66cb9ac4f1",
			"mvr_person_uuid": "7a7b5e90-5e53-4d59-9bca-2c66cb9ac4f1",
			"group_member_number": 3,
			"name": "John Doe",
			"name_updated_at": "2026-02-27T10:14:33Z",
			"name_updated_by": "admin@ppl-meta.local",
			"total_appearances": 0,
			"last_seen": null,
			"group_count": 1,
			"confidence_score": 0.0
		}
	],
	"total": 1,
	"skip": 0,
	"limit": 50
}
```

- UI mapping behavior: show `Group Member 03` from `group_member_number`; show `name` when present; otherwise show short member ID fallback.

- Example variant when no user-defined name exists:

```json
{
	"members": [
		{
			"id": "a9ff51fe-4d3a-45c7-b8f9-8e886ea0f26a",
			"mvr_person_uuid": "a9ff51fe-4d3a-45c7-b8f9-8e886ea0f26a",
			"group_member_number": 4,
			"name": null,
			"name_updated_at": null,
			"name_updated_by": null,
			"total_appearances": 0,
			"last_seen": null,
			"group_count": 1,
			"confidence_score": 0.0
		}
	],
	"total": 1,
	"skip": 0,
	"limit": 50
}
```

- UI fallback in this case: show `Group Member 04` and render `ID: a9ff51fe...` in the member subtitle.

### Execution paths
- Primary management path: list/create group -> open detail -> add/remove/update members -> run analysis from selected members.
- Member identity path: list members -> display `Group Member NN` numbering -> display user-defined member name if set -> fallback to short member ID when no name exists.
- Search path: group + camera/time window -> vmeta camera-search endpoint -> matched group members + appearance summary.
- Hygiene path: duplicate check -> explicit merge request -> super-individual membership update.

### Routes tab lazy loading

When a user opens the `PersonObjectsDetailScreen` for an individual that originated from the individual-groups flow, the **Routes** tab loads route points on demand rather than all at once. This section describes the full pipeline.

#### Step 1 — Metadata fetch
`_fetchCrossVideoRoutesDataInternal()` calls `GET /api/v1/individuals/{uuid}/routes/metadata/by-camera` once per individual to retrieve the `total_points` count per camera. No time filter is applied; the complete detection history is used. The response populates `_routeTotalPointsByCameraSource` and `_routeHasMoreByCameraSource`.

#### Step 2 — Bootstrap (page 0 only)
`_bootstrapRoutePagesForSource()` iterates the candidate camera IDs from the metadata response. For each camera with `total_points > 0` it fires **exactly one** request:

```
GET /api/v1/individuals/{uuid}/routes/by-camera?camera_id=…&page_index=0&page_size=100
```

Only page 0 is fetched during bootstrap. The `has_more` flag returned by the backend determines whether the "Load more routes" button is shown. No loop over page indexes is performed.

#### Step 3 — Backend dataset caching
`MVRRepository.get_individual_routes_by_camera_paged()` calls `_build_route_dataset()` internally. That method:
1. Queries `individual_video_appearances` joined to `tracking_sessions` for camera identity.
2. Calls `_resolve_route_camera_ids()` to map video UUIDs → collection UUIDs (camera IDs).
3. Calls `_expand_with_orchestrator_route_points()` — one HTTP call per distinct video UUID — to expand each appearance into per-frame route points.

The result is **cached in-process** for 5 minutes (keyed by `individual_uuid + auth_header_hash + time_window`). All subsequent page requests for the same individual within the TTL return from cache instantly, avoiding repeated DB queries and orchestrator HTTP calls.

#### Step 4 — Load more (user-triggered)
The "Load more routes" button is rendered when `_cameraHasMoreRoutes(selectedCameraId)` returns `true`. Pressing it calls `_loadMoreCrossVideoRoutes()`, which increments `_routePageIndexByCameraSource` and fires the next page request:

```
GET /api/v1/individuals/{uuid}/routes/by-camera?camera_id=…&page_index=N&page_size=100
```

The backend slices the cached dataset at `page_start = N * 100` and returns `has_more = (page_end < total_points)`. Returned points are appended to `_routePointsByCamera` and the button disappears once `has_more` is false.

#### Key files
| Layer | File | Relevant symbols |
|---|---|---|
| Flutter UI | [ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart](ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart) | `_fetchCrossVideoRoutesDataInternal`, `_bootstrapRoutePagesForSource`, `_appendCameraGroupedRoutePage`, `_loadMoreCrossVideoRoutes` |
| Backend repository | [ppl-meta-vmeta/src/database/mvr_repository.py](ppl-meta-vmeta/src/database/mvr_repository.py) | `get_individual_routes_by_camera_paged`, `_build_route_dataset`, `_route_dataset_cache`, `_expand_with_orchestrator_route_points` |

#### Design constraints
- `_routePageSize` is fixed at `100` in the Flutter client.
- The backend caps `page_size` at `2000` as a safety limit.
- The in-process cache is per-process (not shared across uvicorn workers). Each worker maintains its own cache; the first request to a fresh worker will still pay the full build cost.
- Cache TTL is 5 minutes (`_ROUTE_CACHE_TTL_S = 300.0`). Stale entries are evicted lazily on the next call to `_build_route_dataset`.

### Technical analysis (concise)
- Strength: clear CRUD + membership API surface with explicit pagination/filtering semantics.
- Strength: separation of list/detail UI keeps the primary workflow straightforward.
- Strength: integrated camera search and merge operations reduce manual reconciliation effort.
- Caveat: manager service is broad (large responsibility surface), which can increase maintenance complexity.
- Caveat: several advanced actions are available but can feel distributed across dialogs/endpoints rather than a single guided flow.
