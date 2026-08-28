# Ticket DELTA-SYNC-1 — Delta / Idempotent ETL Sync

**Status:** Spec (draft — not implemented)
**Source:** `docs/modules/digital signage/Sync-Analysis.md` §3.3 (recommended architecture)
**Repos:** `ppl-meta-media` (backend ETL) + `ppl-meta-signage-simple-player` (device)
**Priority:** Medium (bandwidth/idempotency improvement; not a correctness blocker — sync already works, it just always pushes the full manifest)

---

## 1. Problem statement

Today the ETL always rebuilds and pushes the **full** playlist manifest to a device,
`_prepare_video_list_data` + `_send_to_device` in
`ppl-meta-media/src/services/signage_service.py`. It never asks the device what it already holds and
never trims the payload. Consequences:

- Re-running a sync re-pushes every video's metadata even if nothing changed (idempotency gap).
- `VideoListSyncHistory.videos_synced` is set to `len(video_items)` regardless of what was new,
  resulting in misleading history.
- `sync_mode` (`full`/`incremental`) and `force_update` are forwarded to the player as hints but do
  **not** drive a server-side delta.

(Note: because the manifest stores videos as **stream URLs** — `/api/v1/signage/stream/{video_id}` —
playback is on-demand and no asset **bytes** are transferred at sync time. This ticket is therefore
about **metadata/manifest efficiency + accurate history + idempotency**, not byte-level asset delta.)

---

## 2. Scope (corresponds to §3.3 items 1–6)

1. **Player manifest endpoint** — expose the device's current content.
2. **ETL queries the manifest** before pushing.
3. **ETL computes a delta** (added / removed / unchanged) and pushes only what changed.
4. **Accurate history** — record added / skipped (unchanged) / failed counts.
5. **`force_update` override** — bypasses the diff and pushes everything.
6. **Reorder-only handling** — a metadata/order push that does not inflate "synced" counts.


---

## 3. Protocol design

### 3.1 Player: `GET /api/v1/assets` (new)

Returns the device's current known playlist assets (from the local `playlist_videos` table, aggregated
per playlist):

```json
{
  "playlist_id": "<playlist-uuid>",
  "videos": [
    {
      "video_id": "<media-uuid-or-id>",
      "video_hash": "sha256:<hex>",     // optional; today we have no hash, see note
      "sequence_order": 0,
      "updated_at": "2026-08-28T00:00:00Z"
    }
  ]
}
```

- Implement in `ppl-meta-signage-simple-player/lib/services/http_server.dart` (`_createRouter`,
  add `router.get('/api/v1/assets', _handleAssets)`).
- Reads from `PlaylistDatabase.getPlaylist(...)` / the `playlist_videos` table (already `ORDER BY
  sequence_order ASC`).
- **Hash note:** the player does not currently compute content hashes and the manifest stores stream
  URLs, not bytes. For v1, treat a video as "present" if its `video_id` (and optionally its
  `sequence_order`) already matches. Content-hash comparison (analysis §3.2 / §5 item 4) is **out of
  scope** unless/until the player stores hashes.

### 3.2 Backend: query device manifest before push

In `sync_video_list_to_device` (`ppl-meta-media/src/services/signage_service.py`), before
`_send_to_device`:

- `GET http://{device_endpoint}/api/v1/assets` (use the same endpoint resolution as `_send_to_device`
  — discovery lookup, Tailscale translation).
- If the device endpoint is reachable and returns a manifest, use it to compute the delta.
- If the fetch fails (device unreachable / manifest unsupported), **fall back to the current
  full-push behavior** so a device that hasn't been updated never breaks.

### 3.3 Backend: compute delta

`_prepare_video_list_data` gains an optional `existing_video_ids` set (from the manifest). Build the
`videos[]` array as:

- **included:** videos whose `video_id` is NOT in `existing_video_ids` (these are "added"), OR when
  `force_update` is true (all included).
- **excluded:** videos already present (and unchanged order) when NOT forcing.

For **reorder-only** changes (same IDs, different `sequence_order`): still send the full ordered
metadata (the player needs it to reorder), but they should be counted as "updated/skipped", not
"added".

### 3.4 Backend: accurate history

- Add `videos_skipped: int` column to `VideoListSyncHistory`
  (`ppl-meta-media/src/models/signage.py`, `src/schemas/signage.py`
  `VideoListSyncHistoryResponse`).
- `mark_completed(videos_synced, videos_failed)`: pass through `videos_skipped`.
- In `sync_video_list_to_device`: count `added` (included), `updated` (same IDs, different order),
  and `skipped` (same IDs, same order, not forced); set `videos_synced = added` and record
  `videos_skipped = skipped`.
- Requires an alembic migration for the new column.

---

## 4. Out of scope (deferred)

- **Content-hash comparison** (real byte-level dedup) — requires the player to compute/store hashes
  and upload them; no bytes transfer today, so low value until that changes.
- **Asset (byte) pre-positioning / download** — player still streams on demand.
- `POST /etl/sync-to-all` route frontend wiring — the frontend already sends all selected devices via
  `POST /etl/sync` (post-`SYNC-1`).
- Player's order-sensitive `_shouldUpdatePlaylist` — **already implemented** and functioning; not part
  of this ticket.

---

## 5. Acceptance criteria

> **Status:** Workstreams A–D implemented. Criterion **6 (fallback) verified LIVE** against a real
> player (old build, `/api/v1/assets` 404 → full push succeeded, history `synced=3/skipped=0`).
> Criteria 1–5 code-verified; **live delta-path verification still pending** a player build with Workstream A.

1. `GET /api/v1/assets` on the player returns the current playlist video IDs (and sequence order). ✅ (A)
2. When a device already has all of a playlist's videos in the same order and `force_update=false`,
   a sync sends **no** videos and history records `videos_synced=0, videos_skipped=N` (success). ✅ (B, C, D)
3. When a video is added to the playlist, a subsequent sync sends the full ordered list with the new
   video and records `videos_synced=newCount, videos_skipped=unchangedCount`. ✅ (B, D)
4. When the order changes, the sync still delivers the reordered metadata (counted as reordered, not
   added), and the order-sensitive player applies the new order. ✅ (B, D + prior player order fix)
5. `force_update=true` bypasses the delta (full push; all counted synced). ✅ (B)
6. If `GET /api/v1/assets` is unreachable, sync falls back to full-push with no error. ✅ (B) — **verified live**
7. `flutter analyze` and backend `py_compile` are clean; no regression on the existing full-sync path. ✅
   (remaining: live delta-path matrix against a new-build player)

> ⚠️ **Related pre-existing finding (not from A–D):** the frontend sync sends `device.id` (= API
> `uuid`), but the backend sync/auto-registration keys on `device_id`. A **UI-triggered sync fails at
> device lookup** unless the device was already registered and looked up by `device_id`. Follow-up
> ticket: align identifiers. See `Plan-DELTA-SYNC-1.md` → Workstream E.



---

## 6. Related

- `docs/modules/digital signage/Sync-Analysis.md` (§3.2 comparison table, §3.3 items 1–6).
- `docs/video-order-issues.md` (`SYNC-1` — first-device bug, already fixed).


