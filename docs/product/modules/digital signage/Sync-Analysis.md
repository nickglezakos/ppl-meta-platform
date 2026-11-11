# Digital Signage — ETL Sync Analysis

> **Scope:** Analysis of the ETL sync flow in `ppl-meta-media` and `ppl-meta-signage-simple-player`,
> incorporating the current behavior, best-practice review, and the *reorder-then-sync* scenario.
> Companion to: `docs/modules/digital signage/Digital Signage.md` (3.5/3.5.1) and
> `docs/video-order-issues.md` (`SYNC-1`).
> Date: 2026-08-28

---

## 1. Executive summary

- The **ETL currently does not perform a device-content pre-check.** For a given playlist it always
  rebuilds and pushes the **full** video manifest (`_prepare_video_list_data` in
  `ppl-meta-media/src/services/signage_service.py`) and forwards `sync_mode`/`force_update` to the
  player as hints; it never asks the device what it already holds and never trims the payload.
- **Idempotent / delta sync is the desired best practice**, but the "already there" decision is
  effectively delegated to the **player**, which dedups at the *manifest level by video ID*
  (`signage-simple-player/lib/services/sync_service.dart`), not at the *asset-bytes level*.
- Syncing a playlist whose videos are already present does **not** error and does **not** re-transfer
  files (videos stream on demand). The backend still records `videos_synced = len(items)` and marks
  the history `completed`; the player counts unchanged IDs as "updated" and moves on.
- **Reordering videos then tapping Sync** has a subtle consequence: the backend pushes the same
  video IDs in a *new `sequence_order`*. On the player, this is a manifest **change** (order differs),
  so it triggers an update that rewrites the ordered playlist — **only if** the player's comparison
  is order-sensitive. If it is order-agnostic (set-of-IDs only), the order silently does not reach
  the device.

---

## 2. Current sync flow (as built)

### 2.1 Frontend → Backend trigger

- Playlist ⋮ → **"Sync to Devices"** → `_showSyncDialog` → selected devices →
  `syncVideoListToDevices(...)` → `POST /api/v1/signage/etl/sync`
  (`SyncRequest`: `video_list_id`, `target_devices`, `sync_mode`, `force_update`).
- (Post-`SYNC-1` fix) backend enqueues **one batch job** covering all selected devices via
  `get_batch_sync_manager().sync_list_to_devices(...)` → `SignageETLWorker.enqueue_sync_job(...)`.

### 2.2 ETL worker (`signage_etl_worker.py`)

`_process_sync_job`:
- Loads the playlist with items.
- For each target device, calls `SignageSyncService.sync_video_list_to_device(...)` with
  controlled concurrency (`Semaphore(3)`).
- Aggregates `successful_devices` / `failed_devices`.

### 2.3 Per-device push (`signage_service.py`)

`sync_video_list_to_device`:
- Resolves playlist and device; auto-registers the device from discovery if needed.
- Creates a `VideoListSyncHistory` row.
- `_prepare_video_list_data` builds the **full** ordered `videos[]` array:
  `id` (item UUID), `video_id`, `sequence_order`, `filename`, `file_path` (a **stream URL**),
  `duration_ms`, `title`, `thumbnail_url` (stream/thumbnail endpoints).
- `_send_to_device` POSTs `{video_list, sync_mode, force_update}` to the player's `/api/v1/sync`.
- On success: marks history `completed` with `videos_synced = len(video_items)`, sets the device's
  `current_video_list_id`.

### 2.4 Player (`signage-simple-player` `sync_service.dart`)

- Fetches the assigned playlist.
- If the playlist ID is new → `upsertPlaylist`, counts all as added.
- If it exists and `_shouldUpdatePlaylist` says unchanged → **skip** ("Playlist unchanged").
- If changed → compute set differences on video **IDs**:
  - `added = new - old`, `removed = old - new`, `updated = new & old` (intersection).
  - `upsertPlaylist` rewrites the local ordered list.
- Playback is **on-demand streaming** via the manifest's stream URL, so no asset bytes are moved

---

## 3. Best-practice review — should the ETL pre-check for existing videos?

### 3.1 Is the practice good?

**Yes — a pre-check / delta is the healthy pattern** for an ETL over potentially slow signage links:

- Reduces bandwidth and transfer time when only a subset of a playlist changed.
- Makes sync **idempotent** (re-running is a no-op when nothing changed).
- Produces accurate history (added / skipped / removed counts) instead of "everything synced".
- Lets `force_update` override the skip when a corrupt / stale asset needs a refresh.

### 3.2 How best practice differs from the current implementation

| Aspect | Best practice (delta) | Current build |
| --- | --- | --- |
| Server knows device content | ETL queries a device manifest (hashes/IDs) | No |
| Payload trimmed | Only added/changed videos | Always full manifest |
| Skip-decision location | Server (stateful ETL) + player confirmation | Player-only (manifest dedup) |
| Asset comparison | Content-hash comparison | None (video IDs only) |
| `force_update` | Forces full re-sync | Forwarded to player (no asset force) |

> **Note on `incremental`:** in the current code `sync_mode=incremental` only influences the hint
> sent to the player; it does **not** drive a server-side diff. The only real dedup is the player's
> playlist-manifest ID comparison.

### 3.3 Recommended architecture (if pursued)

1. Add `GET /api/v1/assets` (or `/manifest`) on the player returning `[{video_id, hash, size, updated_at}]`.
2. ETL fetches the device manifest before pushing; computes a delta against the playlist items.
3. Push only `added` / `updated` (by hash) videos; skip present-and-unchanged.
4. Record accurate per-device history counts and expose "skipped" in the job status.
5. `force_update=true` bypasses the diff and pushes everything.
6. For **reorder-only** changes, add a dedicated "order" push that updates `sequence_order` without
   re-transferring any asset.

---

## 4. Scenario — user changes the video order in a playlist, then taps Sync

### 4.1 What the user does

1. Opens playlist **Settings**, drags videos in the `ReorderableListView`
   (`video_list_builder.dart`), reorders them, taps **Save**.
2. Save → `PUT /api/v1/signage/video-lists/{uuid}` with `video_order` → backend rewrites
   `sequence_order` on the `video_list_items` rows.
3. User returns to the playlist ⋮ menu → **"Sync to Devices"**.

### 4.2 What the backend does

- The worker loads the playlist with items sorted by `sequence_order` (relationship
  `order_by="VideoListItem.sequence_order"`).
- `_prepare_video_list_data` builds `videos[]` **in the new order** with the new `sequence_order`
  values. Video **IDs are identical** to before; only ordering metadata changed.

### 4.3 What the player does — and the subtle gap

- The player compares the incoming playlist with its stored playlist.
  - If `_shouldUpdatePlaylist` treats **order as part of "changed"** (compares `sequence_order` or
    the ordered video-ID sequence), it detects the change, calls `upsertPlaylist`, and **re-applies
    the new order** on the device. ✅
  - If it only compares the **set** of video IDs (order-agnostic), the playlists are "equal" →
    `_shouldUpdatePlaylist` returns false → **"Playlist unchanged" → order is NOT updated** on the
    device. ❌ The reorder silently never reaches the player.

> **✅ Fixed:** `_shouldUpdatePlaylist` is now order-sensitive (see §4.5) — reorders propagate to the
> device. This closes the order-persistence gap flagged in `docs/video-order-issues.md`.

### 4.4 Asset side of reorder + sync

Because videos stream by URL, reordering-and-syncing does **not** re-download any media — the player
simply rewrites the ordered manifest if it recognizes the order change. If the player is
order-agnostic (case above), the reorder is lost but no bandwidth is wasted.

### 4.5 Recommended handling for the reorder case — ✅ IMPLEMENTED

- **Implemented:** `ppl-meta-signage-simple-player/lib/services/sync_service.dart` →
  `_shouldUpdatePlaylist` now compares the **ordered sequence of video IDs** (via `videoId`)
  instead of the set. This means a backend reorder (same IDs, new `sequence_order`) is detected as a
  change, `_shouldUpdatePlaylist` returns true, and `upsertPlaylist` (which deletes + re-inserts
  `playlist_videos` with their `sequence_order`, and reads them `ORDER BY sequence_order ASC`)
  re-applies the new order on the device.
- Verified: `flutter analyze` on the player — no errors from the change.
- A lightweight "sync-metadata-only" / order push (so a reorder isn't counted as a full sync) is a
  further optimization and can be tracked separately; with the current streaming design no asset
  bytes are transferred anyway, so this is cosmetic for history reporting.


---

## 5. Defects / gaps identified (summary)

1. **No server-side device-content pre-check** — always pushes the full manifest (Q1).
2. **`sync_mode` / `incremental` is only a player hint**, not a server-driven delta.
3. **History is inaccurate** — `videos_synced = len(items)` even when everything was already present.
4. **No content-hash comparison** — dedup is by video ID only.
5. **Reorder propagation** — ✅ IMPLEMENTED.
6. (Pre-existing) ETL worker `job_id` uses an in-memory counter (`UUID(int=...)`), fragile across
   restarts.
7. (Pre-existing) `/api/v1/signage/health` reports unhealthy due to a SQLAlchemy 2.0
   `text('SELECT 1')` issue in its DB probe — unrelated to sync but worth a separate fix.

---

## 6. References

- `ppl-meta-media/src/api/v1/signage.py` — `POST /etl/sync`
- `ppl-meta-media/src/services/signage_etl_worker.py` — `_process_sync_job`, `BatchSyncManager`
- `ppl-meta-media/src/services/signage_service.py` — `sync_video_list_to_device`, `_prepare_video_list_data`, `_send_to_device`
- `ppl-meta-signage-simple-player/lib/services/sync_service.dart` — player-side dedup + updates
- `ppl-meta-frontend/lib/screens/signage_management_screen.dart` — `_showSyncDialog`, `syncVideoListToDevices`
- `ppl-meta-frontend/lib/widgets/signage/video_list_builder.dart` — reorder UI + Save
- `docs/modules/digital signage/Digital Signage.md` — 3.5 / 3.5.1 (marked per `SYNC-1`)
- `docs/video-order-issues.md` — tracked issues incl. order-gap + `SYNC-1`

  during sync.
