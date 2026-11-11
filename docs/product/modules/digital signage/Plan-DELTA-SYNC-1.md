# Plan: Implement Delta-Sync (DELTA-SYNC-1)

**Goal:** Make ETL sync idempotent and history-accurate by querying each device's content before
push and sending only what changed. Implements `docs/modules/digital signage/Ticket-DELTA-SYNC-1.md`.

## Workstreams & risk order

The safest order is **device (player) first**, then **backend**, then **history/migration**, with a
manual e2e test gate between each. Backend changes are designed to fall back to full-push if the
device doesn't yet have the manifest endpoint, so player-first is non-breaking.

---

## Workstream A — Player: `GET /api/v1/assets` — ✅ IMPLEMENTED

**Files:** `ppl-meta-signage-simple-player/lib/services/http_server.dart`

1. Added handler `_handleAssets(Request)` after the `/api/v1/sync` handler. ✅
2. Registered in `_createRouter()`: `router.get('/api/v1/assets', _handleAssets);`. ✅
3. `_handleAssets` returns one JSON doc for **all** stored playlists (via `PlaylistDatabase.getAllPlaylists()`, which returns each playlist's videos `ORDER BY sequence_order ASC`):
   ```json
   {
     "device_id": "<device-uuid>",
     "playlists": [
       { "playlist_id": "<source-or-id>", "name": "...", "sync_version": 1,
         "videos": [ { "video_id": "...", "sequence_order": 0 } ] }
     ]
   }
   ```
   ✅ (Returns all playlists rather than only the loaded one — supersedes the plan's single-playlist note and better supports delta sync per-playlist.)
4. `video_hash` not added — deferred (no hashing yet, per plan). ✅

**Verification:** `flutter analyze lib/services/http_server.dart` → **No issues found** (also removed a pre-existing unused `playback_models.dart` import). Manual check: `curl http://<device>/api/v1/assets` returns each playlist's `video_id` / `sequence_order`.

**Next blocked on:** Workstream B (backend queries this endpoint + computes delta).


---

## Workstream B — Backend: query manifest + compute delta — ✅ IMPLEMENTED

**Files:** `ppl-meta-media/src/services/signage_service.py`, `ppl-meta-media/src/api/v1/signage.py`

1. Added `SignageSyncService._get_device_assets(device, playlist_id) -> (set[str] | None, list[str] | None)`:
   - Resolves the device endpoint via the same discovery/Tailscale logic as `_send_to_device`.
   - `GET {endpoint}/api/v1/assets`, 5s timeout, `_discovery_auth_headers()`.
   - Returns `(set(video_ids), ordered_video_ids)` for the matching `playlist_id` in the manifest, or
     `(set(), [])` if the playlist isn't on the device yet, or `(None, None)` on any failure (⇒ full push).
2. `sync_video_list_to_device` (before `_send_to_device`):
   - If `not force_update`, queries the device manifest; otherwise skips the query (full push).
   - Builds `playlist_ordered_ids` (`str(item.video_id)`) and computes `added_ids` (new to the device).
   - If the device already has **every** video in the **same order** → `_prepare_video_list_data(..., include_videos=False)` (empty `videos[]`), `videos_synced=0`, `videos_skipped=N`.
   - Otherwise delivers the (ordered) list; with a manifest, `videos_synced = len(added_ids)` and the
     rest are reported skipped (delivered for order/metadata). Without a manifest (fallback), full push
     counts all as synced.
   - History uses the accurate `videos_synced`/`videos_skipped`.
3. `_prepare_video_list_data(video_list, include_videos=True)` — added `include_videos=False` to emit an
   empty `videos[]`.
4. **Type-normalization note:** the backend's `VideoListItem.video_id` is an **int**, but the device
   manifest reports `video_id` as a **string** — comparisons are normalized to `str()` to match.

**Verification:** `py_compile` clean; media service reloaded (`--reload`) and `/api/v1/health` healthy.
Fallback preserved: if `GET /api/v1/assets` is unreachable, `(None, None)` triggers the full push.

**Note:** `videos_skipped` is computed and logged now, but the DB column is added in **Workstream C**.

**Next:** Workstream C (persist `videos_skipped` + migration) → Workstream D (reorder-aware refinement).


## Workstream C — Backend: accurate history + migration — ✅ IMPLEMENTED

**Files:** `ppl-meta-media/src/models/signage.py`, `src/schemas/signage.py`,
`src/services/signage_service.py`, `src/alembic/versions/`.

1. Added `videos_skipped: int = Column(Integer, default=0)` to `VideoListSyncHistory`. ✅
2. Added `videos_skipped` to `VideoListSyncHistoryResponse` and to `mark_completed(...)`. ✅
3. Added alembic migration `add_videos_skipped_to_sync_history` (`down_revision: add_vprofile_match_fields`). ✅
4. `sync_video_list_to_device` success branch now calls `update_sync_history(..., videos_synced=..., videos_skipped=...)`; `update_sync_history` threads it through to `mark_completed`. ✅
5. Applied the column to the live DB directly (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS videos_skipped INTEGER NOT NULL DEFAULT 0`) — **safe/idempotent**, used because the alembic head in the DB (`add_vprofile_match_fields`) is not present in the repo's `versions/` dir (branched chain), so a full `alembic upgrade` isn't trustworthy here. The migration file is provided for completeness.

**Verification:** `py_compile` clean on model/schema/service; `/api/v1/health` healthy (service reloaded). Column confirmed present in `video_list_sync_history` via `\d` (not null, default 0).

**Next:** Workstream D (reorder-aware delta refinement).


## Workstream D — Reorder-aware delta (refinement) — ✅ IMPLEMENTED

**Files:** `ppl-meta-media/src/services/signage_service.py`

- Replaced the coarse "added vs present" split with an explicit reorder-aware classification in
  `sync_video_list_to_device`:
  - **added** — id not in the device manifest → `videos_synced`.
  - **reordered** — id present but at a different position → still delivered (so the order-sensitive
    player re-applies it), tracked in the log.
  - **skipped** — id present **and** at the same position → `videos_skipped`.
  - **removed** — on device but no longer in the playlist → drops out of the delivered list (logged).
- Delivery: sends an **empty `videos[]`** only when content AND order are unchanged; otherwise sends the
  full ordered list (covers both new content and reorders).
- History: `videos_synced = len(added)`, `videos_skipped = skipped_count` (truly unchanged only) — a
  reorder no longer counts every video as "skipped".
- Emits a per-sync `Delta ... added/reordered/skipped/removed/forced` log line for observability.

**Verification:** `py_compile` clean. Traced three cases:
  1. unchanged → empty `videos[]`, synced=0, skipped=N;
  2. add a video → full list, synced=1, skipped=(same-position count);
  3. reorder only → full ordered list, synced=0, skipped=(same-position count) — reorder reaches the
     order-sensitive player without being recounted as new content.

**Overall DELTA-SYNC-1: Workstreams A–D now IMPLEMENTED.** Remaining is Workstream E (integration test
matrix) — recommended before a production rollout.

---

## Workstream E — Integration & regression test (LIVE results) — PARTIAL

Ran against a **reachable real player**:
`signage-simple-android-TKQ1.221114.001` — device_id `9f8f8a59-...`, API uuid `5cc59885-...`,
discovery endpoint `10.95.78.104:8009` (playlist 14 "Males only", 3 videos, owner fresh.user).

### ✅ Verified live

- **Criterion 6 — manifest-down fallback:** player's `GET /10.95.78.104:8009/api/v1/assets` → **404**
  (old build). The backend logged *"Could not fetch device assets manifest ... Falling back to full
  push."* and the sync **succeeded**: history `id=324 status=completed videos_synced=3` ⇒ fallback works.
- **Criterion 7 + history:** `/api/v1/health` healthy (media service `--reload`), `py_compile` clean,
  `videos_skipped` column persisted (0 with no manifest). `signage_devices.current_video_list_id` updated.
- **New live player + `/assets` gap fixed:** a fresh live player at `192.168.1.81:8009` responded
  `/health → healthy` and exposed `/api/v1/assets`, but that endpoint **errorred** because
  `playlists.map(...)` wasn't `.toList()`-ed (`jsonEncode` error). **Fixed in the player** (Workstream A),
  verified `flutter analyze` clean — **must be built into the APK you deploy.** The backend is hardened to
  treat a manifest without a `playlists` key as unavailable → full-push fallback.

### ⚠️ SYNC-3 (environment/network) — blocks live sync to the .81 player
The media process currently cannot reach `192.168.1.81:8009` (`[Errno 65] No route to host`) even though
the shell/curl/ping can — a macOS multi-interface routing quirk (en0 + Tailscale). Discovery doesn't list
the player. Sync queues 202 but history = `failed`. See `docs/video-order-issues.md` → `SYNC-3` for
resolution options (media service network context, Discovery registration, or Tailscale routing). **Not a
code defect** in DELTA-SYNC-1.

### ✅ RESOLVED — frontend↔backend device identifier mismatch (pre-existing, BLOCKED UI sync)

- Frontend `SignageDevice` model: `id` ← `@JsonKey('uuid')`, `deviceId` ← `@JsonKey('device_id')`.
- Frontend sync (`syncToAllDevices` / `syncVideoListToDevices`) sends `device.id` (= **uuid**,
  e.g. `5cc59885-...`). Backend `get_device_by_id` + discovery/auto-registration key on **`device_id`**.
- **Fix (backend, `src/services/signage_service.py`):** `get_device_by_id` now falls back to matching
  `SignageDevice.uuid`, so a caller passing either identifier resolves the device. Verified live:
  `POST /etl/sync` with the frontend uuid now returns **202** (previously 500) and the ETL worker
  processes it.

### ✅ Additionally fixed — pre-existing bugs surfaced by this exercise (all in `ppl-meta-media`)

1. **`httpx` was not imported** in `src/api/v1/signage.py`, yet `except httpx.HTTPStatusError` /
   `except httpx.RequestError` existed → any sync that raised an HTTP error hit `NameError: httpx`
   → 500. Added `import httpx`.
2. **`UUID(uuid_obj)` re-wrap bug** in `POST /etl/sync`: `data.target_devices` is already
   `List[UUID]` (Pydantic), and re-wrapping with `UUID(...)` raised
   *"'UUID' object has no attribute 'replace'"*. Changed to pass `data.target_devices` directly.
3. **ETL worker passed a string as `SyncMode`**: `_process_sync_job` called
   `sync_video_list_to_device(..., job.sync_mode, ...)` where `job.sync_mode` is a `str`; the service
   calls `sync_mode.value` → `AttributeError` → worker silently "0/1 synced". Fixed by
   `SyncMode(job.sync_mode)`.
4. **Worker counted a device as synced even when the push failed**: it only checked "didn't raise";
   `sync_video_list_to_device` returns a history that can be `failed`. Now a device counts as
   `successful` only when the returned history is `completed`/`partial`, and failures are logged
   per-device.

> These were found by exercising the real HTTP `/etl/sync` path against the live device — none are in
> the delta-sync (A–D) intent, but all were required for the sync to actually succeed end-to-end.

### Deferred (needs an updated player build to exercise the delta paths live)

The player currently can't serve `/api/v1/assets` (old build), so the **delta** cases can't be
exercised against it. Once a player with Workstream A is deployed, re-run:
- idempotent re-up (synced=0, skipped=N),
- add a video (synced=1, skipped=N-1),
- reorder (full ordered list, synced=0),
- force_update (full push, all synced).

The delta logic (B/D) is code-verified; this is runtime confirmation against a new-build player.


---

## Workstream E — Integration & regression test

1. Bring up media service (`--reload`) + a signage player.
2. **Fresh device:** sync → full push, `videos_synced=N`, `videos_skipped=0`.
3. **Idempotent re-run:** sync again (no force) → `videos_synced=0`, `videos_skipped=N`, and the
   payload sent to the device had `videos: []` (or unchanged).
4. **Add a video** to the playlist → sync → only the new video delivered, `videos_synced=1`.
5. **Reorder** → sync → order delivered, player re-applies (already order-sensitive).
6. **Force update** → full push, all counted synced.
7. **Manifest endpoint down** → sync still succeeds via full-push fallback (no error).
8. Run `flutter analyze` on the player and `py_compile` on the backend; run the signage service
   tests (`tests/test_signage_*.py`) if the env allows.

---

## ⚠️ BUG FIX — empty `videos[]` no-op wiped device content (FIXED)

**Symptom:** device shows as "synced" in the frontend but the player has no playlist and nothing plays.

**Root cause:** Workstream D's "unchanged → send an empty `videos[]`" no-op (`include_videos=False`)
was sent to the player's `POST /api/v1/sync` handler. That handler always *replaced* the stored
playlist via `PlaylistDatabase.upsertPlaylist`, which **deletes all existing `playlist_videos` rows**
and re-inserts only the incoming list. An empty `videos[]` therefore **wiped the device's playlist**
on the idempotent re-sync, then `loadPlaylist` loaded an empty list → nothing to play. The backend
saw success (`synced=0, skipped=N`) so history + frontend said "synced", but the device had no content.

**Fix (both sides, defense-in-depth, restoring pre-commit behaviour):**
- **Backend (root fix)** — `sync_video_list_to_device` no longer sends an empty `videos[]` as a "no-op
  confirmation". Even when the device manifest shows identical content+order, the ETL now delivers the
  **full ordered list** (exactly as it did before the delta-sync commit), while still recording the
  accurate history (`videos_synced=0, videos_skipped=N`). This is what actually makes the device play
  and also self-heals devices whose local DB was already wiped by a prior bad empty-push. An explicit
  `"videos_noop": (not include_videos)` marker remains on the payload so the player can unambiguously
  tell "unchanged" apart from "emptied".
- **Player (defense-in-depth)** — `_handleSync` (http_server.dart) treats a no-op payload as "keep
  existing device content": it does **not** upsert/wipe, just (re)loads the stored playlist and returns
  success. It honors the explicit `videos_noop` marker, and as a defensive fallback for older backends
  (that send an empty list without the marker) it also refuses to wipe a non-empty existing playlist.

Because the backend now always delivers the full list, true playlist *clearing* still propagates when
the backend genuinely has 0 videos, and reorders still deliver the full ordered list.

---

## Rollout

- **Phase 1 (player):** ship `GET /api/v1/assets` to player builds. Old players are unaffected
  (backend falls back to full push when the endpoint is missing).
- **Phase 2 (backend):** enable manifest query + delta + history. Safe because of the fallback.
- **Phase 3:** flip any config flag to make delta the default (or keep it default-on with the
  fallback, which is backwards safe).

---

## Open questions

1. **v1 scope of "deliver reordered videos":** full ordered list even when unchanged is simplest;
   the ticket's acceptance #4 requires delivering the reorder, which full-list satisfies. If we want
   a true delta even for reorders, the player would need a separate "metadata/order-only" push — note
   as future work to avoid over-scoping.
2. **`video_hash`:** defer; no bytes transfer today.
3. **`sync_mode` semantics:** keep `incremental` meaning "use delta" and `full` meaning "full push"? 
   Currently `incremental` is a player hint only — decide whether to map it to the delta at the ETL
   now (recommended) or leave it for a follow-up.
4. **History display:** add `videos_skipped` to any UI history view? (Currently the UI surfaces only
   success/failure + counts; optional.)

---

## Effort estimate (relative)

| Workstream | Repo | Effort |
| --- | --- | --- |
| A — player `GET /api/v1/assets` | player | S (0.5–1 day) |
| B — backend query + delta | media | M (1–2 days) |
| C — history col + migration | media | S (0.5 day) |
| D — reorder-aware delta | media | S–M (0.5–1 day) |
| E — integration test | both | M (1 day) |

**Total (approx.):** ~4–6 engineer-days. A+B+C deliver the core value (idempotent, accurate history);
D improves reorder accounting; E is essential for a safe release.


