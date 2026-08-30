# Signage Playlist Video Order — Persisting Issues & Current Behavior

Date: 2026-08-28
Scope: `ppl-meta-media` (backend) and `ppl-meta-frontend` (Flutter).

## 0. Items that still persist (open issues, listed first as requested)

> **Status update (same day, after fixes):** issues 1 was fixed in code (see §4). Issues 2–6 are behavioral/environment notes that remain true.

1. **[FIXED IN CODE] Playlist content pane ignores the stored sequence order.**
   `signage_management_screen.dart` → `_buildPlaylistContent()` previously rendered the playlist's videos via `ResponsiveMediaGallery` with `sortBy: 'created_at', sortOrder: 'desc'` (lines ~424–434), querying the *collections* by `created_at` and never using `video_items[].sequence_order`. It now renders the playlist's `video_items` sorted by `sequence_order`, resolving each to a full `MediaItem` and passing them to the gallery as `preloadedItems` (see §4).
2. **Drag-to-reorder only exists in the Settings pane.**
   The `ReorderableListView` lives in `video_list_builder.dart` (settings/edit form). There is no reorder affordance in the Content pane, and the content pane's gallery order (issue 1) is unaffected by any reorder.
3. **No dedicated reorder endpoint is exposed.**
   The service has `SignageService.reorder_video_items()` (`src/services/signage_service.py` ~line 464), but `src/api/v1/signage.py` exposes only `POST/GET /video-lists` and `GET/PUT/DELETE /video-lists/{list_uuid}`. The ONLY way to change order is a full `PUT` with `video_order`.
4. **Order changes are not persisted until "Save" is tapped.**
   The drag handler updates local state only (see §3). If the user drags and leaves without saving, the order is silently lost — there is no auto-save or warning.
5. **`_orderedVideos` only auto-seeds when the form opens with an empty list.**
   `_buildVideoOrderList()` calls `_autoOrderVideos()` only when `_orderedVideos.isEmpty` (line ~465). When editing an existing playlist, order is preloaded from `videoList.videoItems` in `initState` (lines 79–85) — this works, but only if the detail endpoint returned hydrated `video_items` (it does after the `loadVideoList` hydration in `_selectPlaylist`).
6. **Live verification via curl requires a valid JWT (verified).**
   Anonymous curls against the running backend on port 8000 return `{"detail":"Not authenticated"}`. A token obtained from `POST http://localhost:8001/api/v1/users/login` (Node service, form-encoded) works — used for the live verification in §4.
7. **`SYNC-1` — "Sync to Devices" only syncs the FIRST online device (backend) — ✅ FIXED.**
   Tracking doc: `docs/modules/digital signage/Digital Signage.md` §3.5.1.
   **Fix applied:** backend `POST /etl/sync` now enqueues a single batch job covering **all** `target_devices` (via `get_batch_sync_manager().sync_list_to_devices`) instead of `target_devices[0]`; frontend `_showSyncDialog` now uses functional `CheckboxListTile`s that track user selection and sends only the selected devices through `syncVideoListToDevices`.
   **Residual (pre-existing, not introduced here):** the batch worker's `enqueue_sync_job` builds `job_id` from an in-memory counter (`UUID(int=len(active)+len(completed)+1)`), which is fragile across restarts — worth a separate ticket if it matters.

8. **`SYNC-2` — UI-triggered sync to signage devices failed at device lookup (device-ID mismatch) — ✅ FIXED + related bugs.**
   Tracking: `docs/modules/digital signage/Plan-DELTA-SYNC-1.md` → Workstream E (RESOLVED section).
   - **Root cause:** the frontend sends `device.id` (= API `uuid`), but the backend `get_device_by_id` + discovery/auto-registration key on `device_id` → uuid lookup returned None → `ValueError("Device not found...")`.
   - **Fix:** `get_device_by_id` now falls back to matching `SignageDevice.uuid`; `POST /etl/sync` with the frontend uuid verified live → **202** (was 500).
   - **Additionally fixed (pre-existing, surfaced while exercising the real HTTP sync path):**
     1. `import httpx` missing in `src/api/v1/signage.py` (except clauses referenced it → `NameError` → 500).
     2. `UUID(...)` re-wrap of an already-`List[UUID]` field → `'UUID' object has no attribute 'replace'`.
     3. ETL worker passed a `str` as `SyncMode` (service calls `sync_mode.value`) → silent "0/1 synced".
     4. Worker counted a device as synced even when the push failed (history `failed`) — now counts only `completed`/`partial` and logs per-device errors.
   - **Noted:** the live device's `POST /api/v1/sync` was intermittently timing out (~30s) this session — device/network-level, not code.
   - **Also fixed (player, Workstream A gap):** `GET /api/v1/assets` returned an error because `playlists.map(...)` (a lazy iterable) wasn't `jsonDecode`-able. Added `.toList()` on the outer map. Verified `flutter analyze` clean. **This change must be built into the APK you deploy.**
   - **Backend hardened:** `_get_device_assets` now treats a manifest response without a `playlists` key as "unavailable" → falls back to full push (so a player with the old/broken manifest never yields an incorrect delta).

9. **`SYNC-3` — Sync to the live player fails with `[Errno 65] No route to host` (environment/network routing).**
   - Symptom: `POST /etl/sync` queues (202) but history = `failed`; log shows the media backend cannot reach the player.
   - Findings:
     - A live player runs at `192.168.1.81:8009` (`/health` → `healthy`, version 1.0.0). The interactive shell's `curl` and `ping` reach it.
     - The **media service process** (local uvicorn, PID running `/opt/anaconda3` python) gets `[Errno 65] No route to host` for `192.168.1.81`, while it reaches `127.0.0.1` and `192.168.1.85` (its own host) fine.
     - The same anaconda python with `source 192.168.1.85` still fails → this is a **macOS multi-interface routing quirk** (host has `en0` 192.168.1.85 + Tailscale `100.64.0.22`); the LAN host `.81` isn't routable from the media process.
     - Discovery does **not** currently list the signage player (only 4 backend services), and the DB `ip_address` was stale (`192.168.1.66`) — updated manually to `192.168.1.81`.
   - **Not a code defect in DELTA-SYNC-1.** Options to resolve (environment):
     1. Run the media service on the same network context as the player (or fix the macOS route so the media process reaches `192.168.1.81`).
     2. Ensure the player registers in Discovery with a routable `host`/`port` (it currently isn't listed).
     3. If using Tailscale, use the player's Tailscale IP and make the media process route it.


---

## 1. Does the video order come from the backend correctly?

**Storage / model** (`ppl-meta-media/src/models/signage.py`):
- `VideoListItem.sequence_order = Column(Integer, nullable=False)` (line ~149).
- The `VideoList.video_items` relationship is explicitly ordered:
  ```python
  video_items = relationship(
      ...,
      order_by="VideoListItem.sequence_order",
  )
  ```
  (lines ~100–104). So any load of a `VideoList` via the ORM returns its items already sorted by `sequence_order`.

**API schemas** (`src/schemas/signage.py`):
- `VideoListItemBase.sequence_order: int = Field(..., ge=0)` — "Order in the playlist" (line ~79).
- `VideoListDetailResponse` extends `VideoListResponse` and includes `video_items`.

**Service** (`src/services/signage_service.py`):
- `_add_video_item(...)` writes `sequence_order=sequence` (line ~451).
- `create_video_list` maps `data.video_order` entries (`{"collection_id", "video_id", "sequence"}`) to internal IDs and inserts them in the given order (lines ~128–156).

**Conclusion:** Yes — the backend stores and returns `video_items` ordered by `sequence_order`, and `GET /api/v1/signage/video-lists/{uuid}` returns that order. The gap is on the frontend Content pane, which ignores it (issue 1 above).


---

## 2. How the order changes ONLY from backend curls (not the frontend)

There is no frontend-independent reorder UI; the order is authoritative in the DB and any change goes through the API. The flow:

**a) Read current order:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/signage/video-lists/<LIST_UUID>
# video_items[] comes back sorted by sequence_order
```

**b) Change order (the only supported mechanism — full PUT with `video_order`):**
```bash
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/signage/video-lists/<LIST_UUID> \
  -d '{
    "video_order": [
      {"collection_id": "<coll-uuid>", "video_id": "<video-uuid-B>", "sequence": 0},
      {"collection_id": "<coll-uuid>", "video_id": "<video-uuid-A>", "sequence": 1}
    ]
  }'
```

Backend handling (`src/services/signage_service.py`, `update_video_list` ~lines 283–330):
- `video_order` is popped from the update payload so it is not treated as a column.
- Each entry's UUIDs are resolved; items are written with the supplied `sequence` values.
- Because the ORM relationship is `order_by=sequence_order`, the next `GET` returns the new order.

**c) A pure-backend reorder with no frontend involvement** is thus: `PUT` with a reshuffled `video_order` → rows' `sequence_order` updated → subsequent `GET` (and any frontend hydration via `loadVideoList`) reflects it. The frontend cannot independently change the DB order: every reorder in the UI ends in this same `PUT` (see §3), and the content pane does not write anything.

> ⚠️ Note (verified against OpenAPI): `reorder_video_items()` in the service layer has **no HTTP route**. If you want a lightweight curl-driven reorder (per-item `new_sequence`), an endpoint like `PUT /video-lists/{uuid}/reorder` would need to be added.

---

## 3. What happens in the frontend when the user drags a video row

All in `ppl-meta-frontend/lib/widgets/signage/video_list_builder.dart`:

1. **Initial seeding.**
   - Editing an existing playlist: `initState()` (lines 79–85) maps `widget.videoList!.videoItems` (hydrated from the backend detail endpoint, sorted by `sequence_order`) into `List<VideoOrderItem> _orderedVideos`.
   - New playlist: `_buildVideoOrderList()` calls `_autoOrderVideos()` (lines 465–467, 522–540) which walks the selected collections' videos and assigns sequences 0..n.

2. **The drag itself — `ReorderableListView.builder` (lines 469–489):**
   ```dart
   onReorder: (oldIndex, newIndex) {
     setState(() {
       if (newIndex > oldIndex) newIndex -= 1;   // Flutter's off-by-one convention
       final item = _orderedVideos.removeAt(oldIndex);
       _orderedVideos.insert(newIndex, item);
       for (var i = 0; i < _orderedVideos.length; i++) {   // resequence 0..n
         _orderedVideos[i] = VideoOrderItem(
           collectionId: ..., videoId: ..., sequence: i);
       }
     });
   }
   ```
   Event sequence when the user long-presses/drags a row:
   - Flutter raises `onReorder(oldIndex, newIndex)` when the row is dropped.
   - `setState` rebuilds the list; `CircleAvatar('${index + 1}')` shows the new position numbers immediately.
   - **No network call, no API event, no provider notification occurs at drag time.** It is purely local state.

3. **Persistence — only on "Save" (`_savePlaylist`, lines 567+):**
   - Builds `CreateVideoListRequest(..., videoOrder: _orderedVideos, ...)` whose `toJson()` emits `video_order: [{collection_id, video_id, sequence}, ...]` (`signage_models.dart` lines 278–300).
   - Calls `signageProvider.createVideoList` (POST) or `updateVideoList` (PUT `/api/v1/signage/video-lists/{id}`) via `signage_api_client.dart` (lines 59–79).
   - The backend rewrites `sequence_order` per §2, and the response rehydrates the provider.

4. **Deleting a row from the order list** (trash icon, lines 501–516) is likewise local-only until Save.

### Known gaps in this flow
- Leaving the settings pane without Save discards the reorder (issue 4).
- ~~The Content pane (`ResponsiveMediaGallery`, sorted `created_at desc`) never re-sorts to the new order~~ — **fixed**, see §4b: Content mode now renders the playlist's `video_items` in `sequence_order`.

---

## 4. Live verification & the Content-pane order fix (applied)

### 4a. Backend order round-trip — VERIFIED LIVE
Using a token from `POST http://localhost:8001/api/v1/users/login` (`fresh.user@example.com` / dev password):

```
PUT  /api/v1/signage/video-lists/30922035-…   video_order = [575, 1241, 1235]
→ 200
GET  /api/v1/signage/video-lists/30922035-…
→ video_items = [
    (0, men-demo-hd_1280_720_24fps.mp4),      # video_id 575
    (1, two_men_one_woman_office.mp4),        # video_id 1241
    (2, two_men_outdoors.mp4)                 # video_id 1235
  ]
```
PUT response and subsequent GET agree — the backend persists and returns `sequence_order` correctly.

### 4b. Frontend Content-pane fix — APPLIED
Two changes:

1. **`responsive_media_gallery.dart`** — added `preloadedItems` mode:
   - New constructor param `List<MediaItem>? preloadedItems`.
   - `initState`: when set, `_applyPreloadedItems()` installs the list verbatim (`_hasMoreItems = false`), skipping `searchMedia`/sorting entirely.
   - `didUpdateWidget`: swaps in a new preloaded list when it changes; falls back to fetching when leaving preloaded mode.
   - Existing tile rendering (thumbnail, play overlay, tap) is untouched.

2. **`signage_management_screen.dart` → `_buildPlaylistContent()`**:
   - Sorts `videoItems` by `sequenceOrder` (defensive — backend already returns them sorted).
   - Fetches each video's full `MediaItem` via `mediaClient.getMediaByUuid(videoId)` (the backend `GET /api/v1/media/{media_id}` accepts integer DB IDs, and returns generated `thumbnail_url` + `url`).
   - Per-item failures are skipped so one missing video doesn't blank the pane.
   - Passes the ordered `MediaItem`s as `preloadedItems` with `enableInfiniteScroll: false`.

**Result:** the Content pane now renders exactly the playlist's videos in the backend's `sequence_order`, with real filenames and working tap-through to `/media-preview`.

### 4c. To verify in the app
1. Hot-restart the Flutter app (models + widgets changed).
2. `/signage → Playlists → select a playlist` → Content pane shows videos in the saved order (compare against Settings list numbering).
3. Reorder in Settings → Save → Content pane order matches.


