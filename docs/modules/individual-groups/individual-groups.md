# individual groups module

## Introduction

### How Individual Groups Work (high level)
- The page at /#/individual-groups is a dedicated management UI for group collections of known individuals, wired from [ppl-meta-frontend/lib/presentation/navigation/app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart#L263-L271) and implemented in [ppl-meta-frontend/lib/screens/individual_groups_screen.dart](ppl-meta-frontend/lib/screens/individual_groups_screen.dart#L20-L30).
- The list screen supports search, visibility filtering, grid/list view toggle, pull-to-refresh, and group creation; it fetches groups from `/api/v1/individual-groups` and creates groups via the same resource, see [ppl-meta-frontend/lib/screens/individual_groups_screen.dart](ppl-meta-frontend/lib/screens/individual_groups_screen.dart#L45-L93) and [ppl-meta-frontend/lib/services/individual_groups_api_client.dart](ppl-meta-frontend/lib/services/individual_groups_api_client.dart#L29-L94).
- Group detail is accessed via `/individual-groups/:groupId` and focuses on member management and analysis workflows (edit group, add/remove members, naming, selection, cross-video analysis launch), see [ppl-meta-frontend/lib/presentation/navigation/app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart#L268-L276) and [ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart](ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart#L27-L76).

### Runtime Flow
- Frontend calls vmeta endpoints through `IndividualGroupsApiClient` for CRUD, membership operations, camera search, duplicate detection, and member merge (`/api/v1/individual-groups/*`), see [ppl-meta-frontend/lib/services/individual_groups_api_client.dart](ppl-meta-frontend/lib/services/individual_groups_api_client.dart#L29-L477).
- Vmeta exposes REST routes for group lifecycle, membership, individual-to-group lookup, bulk operations, camera search, duplicate checks, and merge flow, see [ppl-meta-vmeta/src/api/routes/individual_groups.py](ppl-meta-vmeta/src/api/routes/individual_groups.py#L35-L646).
- `IndividualGroupsManager` is the orchestration layer: it persists groups/memberships in vmeta DB, executes camera/member search, and performs duplicate + merge workflows against person/MVR data, see [ppl-meta-vmeta/src/services/individual_groups_manager.py](ppl-meta-vmeta/src/services/individual_groups_manager.py#L33-L1882).

## Current implementation (concise)

### Module boundaries
- Frontend (`/individual-groups`, `/individual-groups/:groupId`) owns group UX and member interaction.
- Vmeta API owns Individual Groups endpoints and business orchestration.
- Vmeta DB stores groups, memberships, metadata, and lookup state.
- Cross-video/person analysis screens consume selected group members as downstream workflows.

### Data model summary
- Group core fields: `id`, `name`, `description`, `created_by`, `visibility`, `tags`, `member_ids`, `member_count`, `cover_individual_id`, `metadata`.
- Membership is represented as a junction entity (`group_id` <-> `individual_id`) with audit fields (`added_by`, `added_at`, optional `notes`).
- API contracts include camera search (`camera_id`/`camera_ids`, time window, confidence threshold) and merge/duplicate models for de-duplication.

### Execution paths
- Primary management path: list/create group -> open detail -> add/remove/update members -> run analysis from selected members.
- Search path: group + camera/time window -> vmeta camera-search endpoint -> matched group members + appearance summary.
- Hygiene path: duplicate check -> explicit merge request -> super-individual membership update.

### Technical analysis (concise)
- Strength: clear CRUD + membership API surface with explicit pagination/filtering semantics.
- Strength: separation of list/detail UI keeps the primary workflow straightforward.
- Strength: integrated camera search and merge operations reduce manual reconciliation effort.
- Caveat: manager service is broad (large responsibility surface), which can increase maintenance complexity.
- Caveat: several advanced actions are available but can feel distributed across dialogs/endpoints rather than a single guided flow.
