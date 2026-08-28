# Digital Signage Module

> **Route:** `http://localhost:3000/#/signage`  
> **Screen class:** `SignageManagementScreen` in `ppl-meta-frontend/lib/screens/signage_management_screen.dart`  
> **Backend:** `ppl-meta-media/src/api/v1/signage.py`  
> **Player app:** `ppl-meta-signage-simple-player`

---

## 1. Overview

The Digital Signage module is the playlist distribution and remote playback control system for screen-based content delivery across the platform. It lets operators assemble playlists from Media collections, discover registered signage players, push playlists to one or more devices, and control playback remotely.

The module has three cooperating parts:

- **Management UI** - Flutter web/desktop screen used by operators to create playlists, inspect devices, trigger sync jobs, and send playback commands.
- **Signage backend** - Media-service API layer that persists playlists, stores device metadata, tracks sync history, and proxies playback control to devices.
- **Simple Player app** - A dedicated Flutter player that runs on signage hardware, registers with Discovery, exposes local status/history endpoints, and renders full-screen video playback.

At a high level, the module solves four jobs:

- Build a reusable **video list** from one or more media collections.
- Discover and track **signage devices** that can receive content.
- **Synchronize** a selected list to target devices.
- **Control playback** remotely after a list has been deployed.

The management screen is organized into three tabs:

| Tab | Purpose | Primary backend surface |
| --- | ------- | ----------------------- |
| Playlists | Create, search, edit, duplicate, and delete playlists | `/api/v1/signage/video-lists` |
| Devices | View discovered signage devices and inspect online status | Discovery service + player-local status endpoints |
| Control | Start, pause, resume, stop, and skip playback | `/api/v1/signage/playback/control` |

Unlike analytics, the Digital Signage module is not a read-only dashboard. It is an operational control surface that combines persistent configuration with live device orchestration.

---

## 2. Architecture

```text
┌──────────────────────────────────────────────────────┐
│     Signage Management Screen (Flutter / Dart)      │
│   SignageManagementScreen + SignageProvider         │
│   Tabs: Playlists / Devices / Control               │
└───────────────┬───────────────────────┬──────────────┘
                │                       │
        ┌───────▼────────┐      ┌──────▼─────────────────┐
        │ SignageApiClient│      │ DiscoveryServiceClient │
        │ gateway/media   │      │ finds signage players  │
        └───────┬─────────┘      └──────────┬─────────────┘
                │                           │
                ▼                           ▼
      Media Service (:8000)         Discovery Service (:8006)
      /api/v1/signage/...           /api/v1/services...
                │                           │
                │                           ▼
                │                signage-simple-* edge services
                │                           │
                └──────────────┬────────────┘
                               ▼
                  Signage Simple Player device
                  local HTTP API + video playback
```

### Control planes

| Plane | Responsibility | Source of truth |
| ----- | -------------- | --------------- |
| Playlist plane | Persist video lists and list items | Media service database |
| Device registry plane | Registered signage device records | Media service `signage_devices` table |
| Discovery plane | Find live player endpoints and heartbeat freshness | Discovery service |
| Playback plane | Actual current status, health, and history on a device | Player-local HTTP API |
| Sync plane | Push a playlist to one or more players and record outcomes | Media service sync services + ETL worker |

### Main runtime flow

1. The operator opens `/signage`.
2. `SignageManagementScreen` loads playlists and devices in `initState()`.
3. Playlists come from the media-service signage router.
4. Devices are discovered from the Discovery service as `edge` services whose names start with `signage-simple-`.
5. Device status and history are fetched directly from each player's own HTTP endpoint using the discovered host and port.
6. Sync and playback commands go back through the media-service signage API, which then communicates with the target device.

---

## 3. Frontend Data Flow

### 3.1 Initialization and loading

When the screen mounts, `initState()` triggers two initial loads through the provider:

```text
initState()
  ├─ loadVideoLists()
  └─ loadDevices()
```

The screen uses a `TabController` with three tabs:

- `Playlists`
- `Devices`
- `Control`

A refresh icon in the app bar calls `_refreshAll`, which reloads both datasets.

### 3.2 State management

`SignageProvider` owns the operational state used by the screen:

```dart
// Playlist state
List<VideoList> _videoLists
VideoList? _selectedVideoList
bool _isLoadingLists
String? _listsError
int _totalListsCount
int _currentPage

// Device state
List<SignageDevice> _devices
SignageDevice? _selectedDevice
bool _isLoadingDevices
String? _devicesError
Map<String, PlaybackStatus> _deviceStatuses

// Sync state
Map<String, SyncResult> _syncResults
bool _isSyncing
String? _syncError

// Playback state
bool _isControllingPlayback
String? _playbackError
```

### 3.3 Device endpoint resolution

A key implementation detail is that the frontend does not get live playback status from the media-service signage router. Instead it:

1. Discovers `edge` services through `DiscoveryServiceClient`.
2. Filters them to services whose names start with `signage-simple-`.
3. Caches `http://{host}:{port}` per discovered device UUID.
4. Calls the player directly for:
   - `/api/v1/status`
   - `/health`
   - `/api/v1/history`

This means the Devices tab depends on both discovery freshness and player availability.

### 3.4 Playlist management flow

Playlist operations follow a standard CRUD cycle:

```text
User action
  ├─ provider method
  ├─ SignageApiClient request
  ├─ Media service /api/v1/signage/video-lists...
  └─ provider updates local state for UI refresh
```

When a playlist is created:

1. The UI sends `name`, optional `description`, `collection_ids`, `video_order`, `loop_mode`, and `transition_duration`.
2. The backend validates that the referenced collections exist and belong to the current user.
3. Collection UUIDs are translated to internal database IDs.
4. Videos are aggregated from the selected collections into ordered `VideoListItem` rows.
5. Cached playlist statistics are updated: `video_count` and `total_duration_ms`.

### 3.5 Sync flow

> ⚠️ **STALE / OUTDATED — superseded by recent changes.** This section predates the
> reworked Playlists UX (the ⋮ **"Sync to Devices"** menu action). See the current flow
> documented below, and issue `SYNC-1` in the tracked issues doc (`docs/video-order-issues.md`).

Sync is initiated from the management UI but recorded and executed by backend services:

```text
syncVideoListToDevices()
  ├─ POST /api/v1/signage/etl/sync
  ├─ SignageSyncService.sync_video_list_to_device(...)
  ├─ target player receives playlist payload / asset sync
  └─ VideoListSyncHistory updated with status and counters
```

There are two sync modes:

- `full` - push all playlist content
- `incremental` - push only changes since the last successful sync

The ETL worker also supports queued batch jobs for syncing multiple lists and/or multiple devices.

#### 3.5.1 CURRENT flow (post-refactor) — ⋮ "Sync to Devices"

> ✅ **Fixed (SYNC-1).** Section updated to the current, working behavior.

1. User taps the three-dot menu on a playlist card → **"Sync to Devices"** → `_handlePlaylistAction('sync', playlist)` (signage_management_screen.dart).
2. `_showSyncDialog(playlist)` opens an `AlertDialog` listing the provider's `onlineDevices`, each in a **functional** `CheckboxListTile` (default all selected; the user can check/uncheck which devices to target).
3. Tapping **Sync** (disabled if nothing is selected) calls `signageProvider.syncVideoListToDevices(videoListId, selectedDeviceIds)` → `POST /api/v1/signage/etl/sync` with a `SyncRequest` (`video_list_id`, `target_devices` = the selected devices, `sync_mode=incremental`, `force_update=false`).
4. **Backend** (`POST /etl/sync`): resolves the list's UUID → int DB id, then enqueues a **single batch job** via `get_batch_sync_manager().sync_list_to_devices(...)` covering **all** requested devices (not just the first). Returns `202 SyncResponse` (`sync_job_id`, `status=pending`, `target_device_count = len(target_devices)`).
5. The ETL worker processes the job (retries + concurrency) and syncs the playlist to every target device, recording per-device `VideoListSyncHistory`.
6. Provider stores result under `_syncResults[syncJobId]`, returns `true`; the dialog pops and a SnackBar shows "Sync started successfully (N devices)".


### 3.6 Playback control flow

Playback control uses backend-mediated commands:

```text
User presses Start / Pause / Resume / Stop / Next / Previous
  ├─ SignageProvider
  ├─ SignageApiClient.controlPlayback()
  ├─ POST /api/v1/signage/playback/control
  ├─ SignagePlaybackService.control_playback(...)
  └─ device endpoint executes command
```

The provider deliberately avoids forcing an immediate status refresh after control actions. The code assumes the device will publish fresh state through its normal heartbeat and status surfaces.

---

## 4. API Endpoints (Backend)

All management endpoints live under the media-service router at `/api/v1/signage/...`. Most require authenticated access through `get_current_user`.

### 4.1 `POST /signage/video-lists`

Create a new playlist from one or more media collections.

**Request body:**

| Field | Type | Description |
| ----- | ---- | ----------- |
| `name` | string | Playlist name |
| `description` | string? | Optional description |
| `collection_ids` | string[] | Collection UUIDs to aggregate |
| `video_order` | object[]? | Optional manual ordering |
| `loop_mode` | enum | `continuous`, `once`, `shuffle`, `repeat_one` |
| `transition_duration` | int | Transition duration in ms |

**Internal flow:**

1. Validates collection UUIDs against collections owned by the current user.
2. Creates a `VideoList` row.
3. Adds ordered `VideoListItem` rows from the selected collections.
4. Updates cached stats and returns the new playlist.

### 4.2 `GET /signage/video-lists`

Paginated listing of the user's playlists.

**Parameters:**

| Param | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `page` | int | `1` | Page number |
| `page_size` | int | `20` | Results per page |
| `search` | string | null | Search by playlist name |
| `is_active` | bool | null | Filter active/inactive lists |

**Response:** total count, pagination metadata, and `VideoListSummary` results.

### 4.3 `GET /signage/video-lists/{list_uuid}`

Returns a single playlist with its `video_items` included.

### 4.4 `PUT /signage/video-lists/{list_uuid}`

Updates editable playlist properties such as name, description, loop mode, transition duration, publication state, or active state.

### 4.5 `DELETE /signage/video-lists/{list_uuid}`

Deletes a playlist and its list items.

### 4.6 `POST /signage/etl/sync`

Initiates synchronization of a playlist to one or more target devices.

**Request body:**

| Field | Type | Description |
| ----- | ---- | ----------- |
| `video_list_id` | UUID | Playlist UUID |
| `target_devices` | UUID[] | Target signage device UUIDs |
| `sync_mode` | enum | `full` or `incremental` |
| `force_update` | bool | Re-sync even if device appears current |
| `notify_on_complete` | bool | Completion notification toggle |

**Current implementation note:** the route currently forwards only the first target device to `SignageSyncService.sync_video_list_to_device(...)`, while still reporting the full `target_device_count` in the response.

### 4.7 `GET /signage/etl/sync-history`

Returns paginated synchronization history.

**Parameters:**

| Param | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `video_list_id` | int | null | Filter by playlist DB ID |
| `device_id` | UUID | null | Filter by device UUID |
| `page` | int | `1` | Page number |
| `page_size` | int | `50` | Results per page |

### 4.8 `POST /signage/playback/control`

Sends remote playback commands to one or more devices.

**Supported commands:**

- `start`
- `pause`
- `resume`
- `stop`
- `next`
- `previous`
- `seek` (defined in schemas, though not exposed in frontend controls)

**Request body:**

| Field | Type | Description |
| ----- | ---- | ----------- |
| `device_ids` | UUID[] | Devices to control |
| `command` | enum | Playback command |
| `video_list_id` | UUID? | Required for `start` |
| `parameters` | object? | `start_index`, `volume`, `speed` |

### 4.9 `POST /signage/devices`

Registers a signage device in the media-service device table.

The payload includes both operator-friendly fields and device metadata such as manufacturer, model, Android version, screen resolution, and app version.

### 4.10 `GET /signage/devices`

Lists registered signage devices with pagination and filters for `is_online` and `is_active`.

### 4.11 `GET /signage/devices/{device_id}`

Returns a single registered device record.

### 4.12 `PATCH /signage/devices/{device_id}`

Updates mutable device fields such as `device_name`, `location`, `notes`, and `is_active`.

### 4.13 `POST /signage/devices/{device_id}/heartbeat`

Records a device heartbeat in the media-service table so the device can remain marked online.

### 4.14 `POST /signage/etl/batch-sync`

Queues batch sync jobs for multiple playlists and multiple devices through the ETL worker.

### 4.15 `POST /signage/etl/sync-to-all`

Queues a sync job for all currently online devices.

### 4.16 `GET /signage/etl/job-status/{job_id}`

Returns the status of a queued ETL sync job.

### 4.17 `GET /signage/health`

Simple health check for the signage router and its database connectivity.

### 4.18 `GET /signage/stream/{media_id}`

Unauthenticated video streaming endpoint for signage players. Supports HTTP range requests so devices can play media efficiently.

---

## 5. Frontend API Clients

Two client layers participate in signage operations.

### 5.1 `SignageApiClient` (management UI)

Located in `ppl-meta-frontend/lib/services/signage_api_client.dart`.

This client talks to:

- the media-service signage router for playlists, sync, and playback control
- the discovery service for finding devices
- the player-local HTTP API for status, health, and history

| Method | Target | Purpose |
| ------ | ------ | ------- |
| `getVideoLists()` | `/api/v1/signage/video-lists` | Load playlists |
| `getVideoList()` | `/api/v1/signage/video-lists/{id}` | Load one playlist |
| `createVideoList()` | `/api/v1/signage/video-lists` | Create playlist |
| `updateVideoList()` | `/api/v1/signage/video-lists/{id}` | Update playlist |
| `deleteVideoList()` | `/api/v1/signage/video-lists/{id}` | Delete playlist |
| `syncVideoListToDevices()` | `/api/v1/signage/etl/sync` | Trigger sync |
| `controlPlayback()` | `/api/v1/signage/playback/control` | Send playback command |
| `getSignageDevices()` | Discovery service | Discover signage players |
| `getDeviceStatus()` | player `/api/v1/status` | Read live playback status |
| `getDeviceHealth()` | player `/health` | Read local health |
| `getDeviceHistory()` | player `/api/v1/history` | Read local playback history |

### 5.2 `SignageApiClient` (player app)

Located in `ppl-meta-signage-simple-player/lib/api/signage_api_client.dart`.

This client is intended to let the player sync playlists, receive control commands, report state, and upload history. It exposes methods like:

- `syncPlaylist()`
- `sendControlCommand()`
- `reportStatus()`
- `uploadHistory()`
- `checkConnectivity()`

However, several of those methods reference routes such as `/api/v1/signage/status/report` and `/api/v1/signage/history/upload` that are not present in the current media-service signage router.

---

## 6. Data Models

The signage module persists three main database entities in `ppl-meta-media/src/models/signage.py`.

### `VideoList`

A playlist assembled from one or more media collections.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `uuid` | UUID | Public identifier |
| `name` | string | Playlist name |
| `description` | text? | Optional notes |
| `user_id` | UUID | Owner |
| `loop_mode` | string | Playback mode |
| `transition_duration` | int | Transition ms |
| `is_active` | bool | Active flag |
| `is_published` | bool | Distribution readiness flag |
| `total_duration_ms` | int | Cached total duration |
| `video_count` | int | Cached item count |
| `published_at` | datetime? | Publish timestamp |

### `VideoListItem`

An ordered playlist item that references a video inside a collection.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `uuid` | UUID | Public identifier |
| `video_list_id` | int | Parent list |
| `collection_id` | int | Source collection |
| `video_id` | int | Source media item |
| `sequence_order` | int | Order within playlist |
| `duration_override` | int? | Optional display override |
| `title_override` | string? | Optional display title |
| `transition_override` | int? | Optional transition override |
| `is_available` | bool | False if backing media disappeared |

### `VideoListSyncHistory`

Audit record for every sync attempt.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `uuid` | UUID | Public sync ID |
| `video_list_id` | int | Playlist reference |
| `signage_device_id` | UUID | Device target |
| `sync_status` | string | `pending`, `in_progress`, `completed`, `partial`, `failed` |
| `sync_mode` | string | `full` or `incremental` |
| `videos_synced` | int | Success count |
| `videos_failed` | int | Failure count |
| `data_transferred_bytes` | int | Transfer volume |
| `sync_started_at` | datetime? | Start time |
| `sync_completed_at` | datetime? | End time |
| `sync_duration_ms` | int? | Duration |
| `error_message` | text? | Failure summary |

### `SignageDevice`

Registered device metadata stored in the media service.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `uuid` | UUID | Internal signage device UUID |
| `device_id` | UUID | Discovery-service device ID |
| `device_name` | string | Human-readable name |
| `ip_address` | string? | Last known IP |
| `port` | int? | Last known HTTP port |
| `is_active` | bool | Administrative active flag |
| `is_online` | bool | Current online flag |
| `last_seen` | datetime? | Last observed time |
| `last_heartbeat` | datetime? | Last heartbeat time |
| `current_video_list_id` | int? | Current assigned list |
| `playback_state` | string? | `playing`, `paused`, `stopped`, etc. |
| `app_version` | string? | Player build version |
| `screen_resolution` | string? | Device resolution |

---

## 7. UI Layout

The management screen uses a tabbed operational layout instead of a dashboard stack.

```text
┌──────────────────────────────────────────────┐
│ CustomAppBar [Refresh]                      │
├──────────────────────────────────────────────┤
│ Tabs: [Playlists] [Devices] [Control]       │
├──────────────────────────────────────────────┤
│ Playlists tab                               │
│ ┌──────────────────────────────────────────┐ │
│ │ Search field        [New Playlist]       │ │
│ ├──────────────────────────────────────────┤ │
│ │ Playlist cards                           │ │
│ │ - name                                   │ │
│ │ - video count                            │ │
│ │ - duration                               │ │
│ │ - actions: edit / sync / duplicate / del │ │
│ └──────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│ Devices tab                                 │
│ ┌──────────────────────────────────────────┐ │
│ │ Discovered devices                       │ │
│ │ - online/offline state                   │ │
│ │ - endpoint / metadata                    │ │
│ │ - status / health                        │ │
│ └──────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│ Control tab                                 │
│ ┌──────────────────────────────────────────┐ │
│ │ Select device + playlist                 │ │
│ │ Start / Pause / Resume / Stop / Next     │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### Playlists tab

The Playlists tab includes:

- search field
- create-playlist action
- empty state with first-playlist CTA
- per-playlist card actions: edit, sync to devices, duplicate, delete
- playlist detail view on tap

### Devices tab

The Devices tab is discovery-centric. It surfaces signage players that are currently known to the discovery service and can optionally fetch player-local status.

### Control tab

The Control tab is oriented around device actions rather than content editing. It sends direct playback commands through the backend.

### Player UI

The standalone player is a full-screen immersive playback experience with:

- full-screen video rendering
- optional development controls
- status overlay
- keyboard shortcuts
- immersive sticky system UI mode
- orientation toggle support
- long-press configuration dialog for backend/discovery settings

---

## 8. Playlist and Device Flows

### Playlist creation flow

1. Operator chooses one or more media collections.
2. Frontend sends collection UUIDs to the signage backend.
3. Backend validates ownership and fetches videos from `MediaCollectionItem`.
4. `VideoListItem` rows are generated in sequence order.
5. Cached playlist metrics are recomputed.

### Device discovery flow

1. Frontend calls the Discovery service for `edge` services.
2. Results are filtered to names starting with `signage-simple-`.
3. Discovered `host` and `port` are cached per device UUID.
4. UI can then query the player directly for status/health/history.

### Sync flow

1. Operator chooses a playlist and one or more devices.
2. Frontend posts a `SyncRequest`.
3. Backend validates the playlist and target device(s).
4. Sync service pushes list metadata and associated media information to the player.
5. Backend records a `VideoListSyncHistory` result.

### Playback flow

1. Operator chooses a device and optionally a playlist.
2. Frontend posts a playback command.
3. Backend resolves the target device and forwards the command.
4. Player engine updates local playback state.
5. Device status is later visible through the player-local status endpoint.

---

## 9. Operational Semantics

### Loop modes

The backend schema defines four loop modes:

- `continuous`
- `once`
- `shuffle`
- `repeat_one`

The frontend model currently exposes three enum values:

- `once`
- `continuous`
- `shuffle`

`repeat_one` exists in backend schemas and models but is not represented in the current frontend enum.

### Device identity handling

There are two important identifiers:

- `device.id` in the frontend model is the discovered service UUID used for direct player communication.
- `device.deviceId` represents the discovery metadata device ID string.

The provider comments explicitly note that playback control should use the UUID-style `device.id`, not the human/device label.

### Online status handling

Online state is a composition of:

- discovery registration freshness
- media-service heartbeat timestamps
- direct player reachability for status and health checks

Because these sources are separate, a device can appear discovered but still fail direct status retrieval if its local player HTTP server is unavailable.

---

## 10. Caching and Background Processing

The module uses lightweight client-side and backend-side caching patterns rather than a centralized cache layer.

- The frontend caches player endpoints in `_deviceEndpointCache` to avoid repeated discovery lookups.
- Sync jobs are tracked through `VideoListSyncHistory` and, for batch work, through an in-memory ETL worker queue.
- The ETL worker supports:
  - job queueing
  - bounded worker concurrency
  - retry-oriented processing structure
  - active/completed job lookup

The signage module is operationally asynchronous in sync scenarios, even though the base CRUD endpoints are synchronous.

---

## 11. Known Limitations

1. **Sync request fan-out is partial in the direct sync route.** `POST /signage/etl/sync` currently processes only the first target device even when multiple devices are supplied.

2. **Frontend/back-end pagination naming is inconsistent.** The management client sends `limit` while the backend route expects `page_size` for playlist listing.

3. **Sync history path is inconsistent.** The frontend client calls `/api/v1/signage/etl/sync-history/$listId`, while the backend route currently exposes `/api/v1/signage/etl/sync-history` with query parameters.

4. **Player client references routes that do not exist in the current backend router.** Methods such as `reportStatus()` and `uploadHistory()` assume `/status/report` and `/history/upload` endpoints that are not implemented in `ppl-meta-media/src/api/v1/signage.py`.

5. **Discovery and registry are split systems.** Device discovery comes from the Discovery service while device registration metadata is stored in media-service tables, so those sources can drift.

6. **Live device status is not centralized.** The UI must reach each player directly to get `/api/v1/status`, which makes the Devices tab sensitive to network topology and endpoint reachability.

7. **Playback command IDs are placeholder values.** The playback control route returns a hard-coded command UUID instead of a generated operation identifier.

8. **The player app and management backend appear to reflect different generations of the contract.** Some player API assumptions do not line up exactly with the currently implemented signage router.

---

## 12. File Inventory

| File | Purpose |
| ---- | ------- |
| `ppl-meta-frontend/lib/screens/signage_management_screen.dart` | Main management UI for playlists, devices, and playback control |
| `ppl-meta-frontend/lib/providers/signage_provider.dart` | State management for playlists, devices, sync, and playback actions |
| `ppl-meta-frontend/lib/services/signage_api_client.dart` | Frontend client for signage backend, discovery, and player-local APIs |
| `ppl-meta-frontend/lib/models/signage_models.dart` | Dart models and enums for playlists, devices, sync, and playback |
| `ppl-meta-media/src/api/v1/signage.py` | Media-service signage router with CRUD, sync, playback, device, and utility endpoints |
| `ppl-meta-media/src/services/signage_service.py` | Core playlist, sync, and playback business logic |
| `ppl-meta-media/src/services/signage_etl_worker.py` | Background ETL worker for queued and batch sync jobs |
| `ppl-meta-media/src/models/signage.py` | SQLAlchemy models for `VideoList`, `VideoListItem`, `VideoListSyncHistory`, and `SignageDevice` |
| `ppl-meta-media/src/schemas/signage.py` | Pydantic schemas for signage requests and responses |
| `ppl-meta-signage-simple-player/lib/screens/signage_player_screen.dart` | Full-screen signage player UI |
| `ppl-meta-signage-simple-player/lib/api/signage_api_client.dart` | Player-side API client for sync/control/reporting operations |
| `ppl-meta-signage-simple-player/lib/main.dart` | Player startup and discovery registration flow |
| `ppl-meta-media/tests/test_signage_service.py` | Backend signage service tests |
| `ppl-meta-media/tests/test_signage_integration.py` | Backend integration tests for signage flows |
| `tests/test_intelligent_signage_lifecycle.py` | Higher-level signage lifecycle coverage |
