# Proposal: People Counters — Automated Batched MVR Search with Persistent Result Reuse

> Status: Draft proposal
> Owner: Orchestrator (job scheduling + driver) + vmeta (storage + merge endpoint) + frontend (settings UI)
> Related: `HIERARCHICAL_MVR_PEOPLE_MERGING.md`, `mvr-people-persistent-storage-for-instant-detection.md`, `vmeta-search-from-persisted-person-objects.md`
> Target version: 2.25.x

---

## 1. Problem Statement

Today, when a user issues an MVR search across an arbitrary time window (e.g. "show me everybody seen between 13:00 and 18:00 on camera X"), vmeta performs a full search across every video in that window. Each request:

1. Loads persisted `person_objects` for every video in the range.
2. Runs cross-video similarity merging.
3. Writes a single `mvr_search_sessions` row keyed on the *exact* `(camera_ids, video_uuids)` input set.

Two operational problems follow:

- **Cold cost is paid every time the input set changes by even one video.** The cache key (`same_input_key`) is the canonical hash of the full video list, so a 5-hour window and a 5-hour-15-minute window share zero work.
- **Identical sub-windows are recomputed repeatedly.** A user inspecting "08:00–12:00" and later "10:00–14:00" recomputes the overlapping 10:00–12:00 slice twice.

We want a **people counter** abstraction: an automation that pre-computes merged MVR results for canonical, fixed-size **batches** of recorded video, persists them, and lets ad-hoc user queries assemble their answer from those pre-computed batches plus a small amount of "fill-in" work for partial-coverage edges.

---

## 2. Goals

- G1. Run an automated job that partitions a day's recordings (per camera) into deterministic, hour-aligned batches and pre-computes a merged MVR search session for each batch.
- G2. Persist each batch's result in `mvr_search_sessions` (or a derived view) with a deterministic `batch_key` so it is trivially looked up by `(camera_id, day, hour)`.
- G3. When a user runs a search over an arbitrary `[start, end]`, decompose the request into:
  - **Fully-covered batches** → reuse stored result_payload (no compute).
  - **Edge gaps** (videos at the leading/trailing edges that don't align to a batch boundary) → run a fresh on-demand merge over only those videos.
  - **Final aggregation** → merge the reused batch results with the edge-gap fresh result into one unified response.
- G4. Keep the existing `/search/by-videos/persisted-merge-session` endpoint as the single source of truth for "merge a list of videos and persist the session"; the new automation is a *driver* on top of it, not a replacement.
- G5. Provide cache invalidation hooks so that batches whose underlying `mvr_people` rows have been merged, deleted, or recomputed are flagged stale and re-run.

## 3. Non-Goals

- NG1. Realtime streaming counters. This proposal is for **post-recording** batched analysis.
- NG2. Cross-camera merging in batch. Each batch is scoped to a single `camera_id` to keep the batch_key deterministic and the merge surface tractable.
- NG3. Replacing instant-detection cache (covered by `instant-detection-cache-behavior` and the persisted person_objects pipeline).

---

## 4. Existing Infrastructure We Build On

### 4.1 Endpoint
`POST /api/v1/mvr-people/search/by-videos/persisted-merge-session` (vmeta, `mvr_people.py:3735`)

Body:
- `camera_ids: List[str]`
- `video_uuids: List[str]`
- `start_time`, `end_time` (ISO8601, optional bounds for filtering appearances)
- `limit` (default 100)
- `similarity_threshold` (default 0.70)
- `ignore_existing_session: bool` (skip cache lookup)
- `video_details: List[{video_uuid, camera_id, media_timestamp}]`

Reuse path: `mvr_repository.get_search_session_by_same_input(camera_ids, video_uuids)` returns the prior session if `same_input_key` matches.

Persistence path: `mvr_repository.create_search_session(..., search_mode="merge_preview", ...)` writes a row to `mvr_search_sessions` plus link rows in `mvr_search_session_cameras` and `mvr_search_session_videos`.

### 4.2 Tables (existing)
- `mvr_search_sessions` — one row per persisted merge session. Holds `result_payload` (full merged people list) and `summary_payload` (aggregates). Indexed by `same_input_key`.
- `mvr_search_session_cameras` — `(search_session_uuid, camera_id)`.
- `mvr_search_session_videos` — `(search_session_uuid, video_uuid, camera_id, media_timestamp)`.

The `same_input_key` is built from the canonical sorted hash of `(camera_ids, video_uuids)` (see `build_same_input_key` in `mvr_repository.py`). This means the existing reuse logic *already* supports our use case **as long as we always invoke a batch with the same exact video list**. That is precisely what hour-aligned batches give us.

---

## 5. Design

### 5.1 Batch Definition

A **batch** is identified by `(camera_id, batch_start_utc, batch_end_utc)`. We propose hour-aligned UTC batches:

```
batch_key = f"{camera_id}|{batch_start_utc.isoformat()}|{batch_end_utc.isoformat()}"
```

Default batch size: **1 hour**. Configurable per deployment (`PEOPLE_COUNTERS_BATCH_SECONDS`, default 3600). A day yields 24 batches per camera.

Why hour-aligned (not "N videos per batch"):
- Deterministic regardless of recording cadence.
- Trivial to map any user `[start, end]` to a contiguous set of fully-covered batches with two boundary-rounding operations.
- Aligns with how operators already think about CCTV review.

Edge case: a video that spans a batch boundary (e.g. starts at 08:59:30 and ends at 09:01:10). Two options — we recommend **option B**:

- Option A: assign by start time → some appearances near the boundary leak into the wrong batch.
- **Option B (recommended): assign by midpoint of `media_timestamp + duration/2`.** Boundary leakage is at most `batch_size / 2` and symmetric.

### 5.2 Storage Strategy

We reuse `mvr_search_sessions` as-is and add three optional columns to make batches first-class:

```sql
ALTER TABLE mvr_search_sessions
  ADD COLUMN batch_key       TEXT,                       -- NULL for ad-hoc sessions
  ADD COLUMN batch_camera_id TEXT,
  ADD COLUMN batch_start_utc TIMESTAMP,
  ADD COLUMN batch_end_utc   TIMESTAMP,
  ADD COLUMN is_stale        BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX idx_mvr_search_sessions_batch_key
  ON mvr_search_sessions(batch_key)
  WHERE batch_key IS NOT NULL;

CREATE INDEX idx_mvr_search_sessions_batch_lookup
  ON mvr_search_sessions(batch_camera_id, batch_start_utc, batch_end_utc)
  WHERE batch_key IS NOT NULL AND is_stale = FALSE;
```

Rationale:
- `batch_key` uniqueness lets the daily job be safely re-runnable (idempotent UPSERT).
- The lookup index supports the sub-period query pattern `WHERE camera_id = ? AND batch_start >= ? AND batch_end <= ?`.
- `is_stale` lets invalidation hooks mark batches dirty cheaply without deleting them.

### 5.3 Service Ownership

The people-counters job is **owned by `ppl-meta-orchestrator`**, not by vmeta. Reasons:

- The orchestrator already owns cross-service workflows (vision → vmeta → media), runs background jobs, and holds the platform's scheduler. Adding another scheduled driver there is the natural fit.
- vmeta should remain a stateless query/merge engine. Pushing the cron into vmeta would couple a long-running periodic job to the same process that serves user-facing search latency.
- Keeping vmeta as a pure HTTP target (`/search/by-videos/persisted-merge-session`) preserves testability and lets the orchestrator throttle, retry, and prioritize without touching merge code.

What lives where:

| Concern | Service |
|---|---|
| Cron schedule, job state, retries, advisory locks per camera | orchestrator |
| Worker pool + low-priority queue | orchestrator |
| `/api/v1/people-counters/*` endpoints | orchestrator (gateway-proxied) |
| `/search/by-videos/persisted-merge-session` (the actual merge) | vmeta (unchanged) |
| `mvr_search_sessions` storage + new batch columns | vmeta DB (unchanged location) |
| Settings UI (§5.8) | frontend |

### 5.4 Daily Batch Job

**Trigger options** (proposal supports all three):

1. **Scheduled cron** — `cron: 30 2 * * *` (02:30 UTC, after the previous day is closed). Runs in the orchestrator's scheduler. **Recommended primary trigger.**
2. **Recording-stop hook** — when a video file is finalized and its persisted `person_objects` are written, enqueue its containing batch for processing. Allows near-realtime population without waiting for the daily cron.
3. **Manual admin button** — `POST /api/v1/people-counters/run-daily-batch` with `{ date, camera_ids?, force? }` for backfill / re-run.

**Job algorithm (per camera, per day):**

```
for hour in [0..23]:
    batch_start = day @ hour:00:00 UTC
    batch_end   = day @ hour:59:59.999 UTC
    batch_key   = f"{camera_id}|{batch_start}|{batch_end}"

    if exists(batch_key) and not is_stale and not force:
        continue

    videos = list_videos(camera_id, midpoint_in=[batch_start, batch_end])
    if not videos:
        upsert_empty_batch(batch_key, ...)   # so we don't re-scan tomorrow
        continue

    response = POST /search/by-videos/persisted-merge-session {
        camera_ids:           [camera_id],
        video_uuids:          [v.uuid for v in videos],
        start_time:           batch_start,
        end_time:             batch_end,
        similarity_threshold: settings.similarity_threshold,  # default 0.60 (see §5.11)
        ignore_existing_session: force,
        video_details:        videos,
    }

    # mvr_search_sessions row was just written. Tag it as a batch.
    UPDATE mvr_search_sessions
       SET batch_key=$1, batch_camera_id=$2,
           batch_start_utc=$3, batch_end_utc=$4, is_stale=FALSE
     WHERE search_session_uuid = $5;
```

The job concurrency model: **one in-flight batch per `camera_id`** (advisory lock on `('people_counters_batch', camera_id)`); multiple cameras run in parallel up to the worker pool's low-priority budget.

### 5.5 Low-Priority Worker Queue

Batch computation must **never compete with interactive workloads** (live ingestion, instant detection, user-triggered search, materialization from the preview screen). When the feature is enabled in Settings (§5.8), the worker is **always running in the background** — it continuously polls for batches that need (re)computation, picks one up, runs it, and goes back to polling. There is no separate "start" action; the master switch in Settings is the only on/off control.

**Implementation framework.** The orchestrator does **not** use Celery today — background work runs on its existing `automation_engine` (asyncio + interval / time-of-day schedulers in `automation_engine.py`, plus FastAPI `BackgroundTasks` for ad-hoc jobs). The people-counters worker reuses that exact pattern:

- A long-lived `asyncio.create_task` loop registered at orchestrator startup when `PEOPLE_COUNTERS_ENABLED=true`.
- Scheduling driven by `automation_engine`'s `_interval_scheduler` (poll cadence) and `_time_of_day_scheduler` (the daily 02:30 UTC pass).
- Job state, retries, and dead-letter rows persisted in a new `people_counters_jobs` table on the orchestrator DB (analogous to existing workflow tables in `workflow_models.py`).

If at some future point the platform adopts Celery/RQ for background work, this worker is the obvious first candidate to migrate — but introducing that dependency just for this feature is not justified.

**Low-priority guarantees** are enforced by the worker loop itself, not by a queue broker:

- **Bounded concurrency**: at most `PEOPLE_COUNTERS_WORKERS` (default 2) batches in flight; multiple cameras can run in parallel up to that cap.
- **System-load gate** before each batch is dispatched. Skip if any of the following are true (all configurable):
  - vmeta CPU > `PEOPLE_COUNTERS_MAX_CPU_PCT` (default 60%) over the last 60 s.
  - vmeta active-request count > `PEOPLE_COUNTERS_MAX_INFLIGHT` (default 5).
  - Vision service utilization > `PEOPLE_COUNTERS_VISION_THRESHOLD` (default 70%).
  - When gated, the loop sleeps `PEOPLE_COUNTERS_BACKOFF_SECONDS` (default 60) and re-checks. The day's batches are not time-critical — finishing within 24 h is acceptable.
- **Quiet-hours preference**: optional config window (e.g. 01:00–06:00 local) during which the load gate is relaxed and parallelism scales up to `PEOPLE_COUNTERS_QUIET_WORKERS` (default 4).
- **Cooperative pause**: a manual MVR search arriving at vmeta sets a short-lived "hot" flag; the worker finishes the in-flight `/persisted-merge-session` call and then sleeps before picking up the next batch.
- **Per-batch HTTP timeout** (default 5 min) bounds stuck merges.
- **Retry with backoff**: failures retry up to 3 times with exponential backoff; persistent failures land in `people_counters_jobs` with `status='dead_letter'` and surface in the Settings UI as actionable rows.

#### 5.5.1 Resumability and Backlog Recovery

The worker is **fully resumable** because all of its state lives in two tables, never in process memory:

- `mvr_search_sessions` — every successfully computed batch is one durable row keyed by `batch_key`. Its presence with `is_stale = FALSE` is the authoritative signal that the batch is done.
- `people_counters_jobs` — one row per dispatched batch attempt with `status ∈ {pending, running, success, failed, dead_letter}`, `attempts`, `last_error`, `heartbeat_at`.

**On orchestrator startup** (cold boot, crash recovery, or admin restart) the worker runs a single recovery pass before entering its normal poll loop:

```
1. Reset orphans:
     UPDATE people_counters_jobs
        SET status = 'pending'
      WHERE status = 'running'
        AND heartbeat_at < NOW() - INTERVAL '10 minutes';

2. Enumerate the work backlog (next-batch selection, see §5.5.2):
     for each enabled camera:
       compute the set of expected (camera_id, hour) batches from the
       earliest media timestamp the camera has on disk through "now",
       minus any (batch_key) already present in mvr_search_sessions
       with is_stale = FALSE.

3. Insert missing batches into people_counters_jobs as status='pending'
   (idempotent — UNIQUE on batch_key).

4. Begin the normal poll loop.
```

**Stop / pause semantics:**

- **Admin pause** (master switch in Settings → "Pause computation"): the worker finishes the current in-flight batch (if any), commits its row, and stops dispatching. The `pending` rows remain in `people_counters_jobs`. On resume, the worker picks up exactly where it left off — the next pending batch — because batch selection is purely a database query, not an in-memory cursor.
- **Process crash / SIGTERM**: an in-flight batch's `running` row will be picked up by step 1 above (orphan reset) on the next boot, and re-dispatched. The underlying `/persisted-merge-session` call is idempotent on `same_input_key`, so a re-run produces the same row (or a no-op if the session was already persisted before the crash).
- **Service stopped for hours/days**: nothing special happens during the downtime — no work is lost because no work was queued in memory. On restart, step 2 above naturally discovers every missing batch since the last successful run and queues them all.

Net: there is no "last-batch pointer" to lose. The set of batches still to do is always `expected_batches − completed_batches`, computed fresh on every boot.

#### 5.5.2 Backlog Prioritization After Long Downtime

When the system has been off (or the feature deactivated) for **more than ~24 h**, the backlog can be large — for a deployment with 10 cameras and 3 days off, that is `10 × 24 × 3 = 720` batches. Burning through them in arrival order would keep the system saturated for a long time and would leave the *most useful* (newest) data uncovered the longest. We therefore order the backlog explicitly:

**Priority tiers (highest first):**

1. **Today (current UTC day), newest hour first.** Operators almost always query "today" first; covering the most recent few hours immediately makes the Settings dashboard and the user-facing `/aggregate` endpoint useful within minutes of boot.
2. **Yesterday, newest hour first.** Second-most-queried window in practice.
3. **`is_stale = TRUE` batches** (any age). Stale rows already have a usable approximate answer in `result_payload`; refreshing them is lower urgency than filling holes, but they should not be starved indefinitely. Capped at ~25% of worker capacity so they cannot block fresh-coverage work.
4. **Older missing days, newest day first, newest hour within the day first.** This is the bulk-backfill tier. A 3-day backlog completes day-N+0 → day-N-1 → day-N-2 in that order, so each completed day immediately becomes queryable end-to-end before the next one starts.
5. **Pre-existing dead-letter rows** are never auto-retried by the backlog pass — they require an explicit "Retry now" action from the Settings UI.

Implementation: a single SQL ordering on the `pending` selection query. No separate priority queue:

```sql
SELECT batch_key, batch_camera_id, batch_start_utc
  FROM people_counters_jobs
 WHERE status = 'pending'
 ORDER BY
   CASE
     WHEN batch_start_utc::date = CURRENT_DATE                          THEN 0  -- today
     WHEN batch_start_utc::date = CURRENT_DATE - INTERVAL '1 day'       THEN 1  -- yesterday
     WHEN is_stale_refresh                                              THEN 2  -- stale refresh
     ELSE 3                                                                  -- older backfill
   END ASC,
   batch_start_utc DESC                                                       -- newest within tier first
 LIMIT :worker_budget;
```

**Throttling for large backlogs:**

- The same low-priority gates from §5.5 still apply — a 720-batch backlog will not pin CPU at 100%.
- Quiet-hours scaling (§5.5) is the primary tool to drain large backlogs: the worker scales to `PEOPLE_COUNTERS_QUIET_WORKERS` (default 4) overnight while the system is otherwise idle.
- An optional `PEOPLE_COUNTERS_BACKFILL_DAILY_BUDGET` (default 200 batches/day) caps how many backfill-tier batches the worker will dispatch in a 24 h window, so a multi-week backlog is amortized rather than monopolizing the worker for days. Tier-0/1/2 batches are exempt from this cap.
- The Settings → Status tab shows a live "Backlog: N batches (today: a, yesterday: b, stale: c, older: d) — ETA based on current rate: …" so operators have visibility while the system catches up.

This prioritization is opinionated but configurable: the tier ordering and the daily budget are exposed in Settings → Schedule & Priority.

### 5.6 Sub-Period Query Algorithm

The user-facing query — "show me everyone seen on camera X between `start` and `end`" — runs:

```
1. Identify fully-covered batches:
       SELECT * FROM mvr_search_sessions
        WHERE batch_camera_id = :camera_id
          AND batch_start_utc >= :start
          AND batch_end_utc   <= :end
          AND is_stale = FALSE
        ORDER BY batch_start_utc ASC;

2. Identify uncovered edges:
       leading_gap  = [start,            first_batch.batch_start_utc]
       trailing_gap = [last_batch.batch_end_utc, end]
       interior_holes = ranges where consecutive batches are non-contiguous (rare)

3. For each gap, fetch the videos in that gap (by midpoint) and call:
       POST /search/by-videos/persisted-merge-session
            with ignore_existing_session = false
       (it may itself be cached if the gap has been queried before)

4. Aggregate:
       all_results = union(batch.result_payload for batch in batches)
                   + union(gap.result_payload   for gap   in gaps)
       run final cross-batch merge on `all_results` using the same
       similarity_threshold (default 0.60, see §5.11) so people seen in two
       adjacent batches collapse into one mvr_people row in the response.
```

The **final cross-batch merge** is the one bit of new compute that doesn't exist today. It is a pure in-memory pass over already-merged groups (each group has a representative embedding), so it is O(N²) on the count of mvr_people across batches — orders of magnitude cheaper than re-running the per-video merge.

### 5.7 Cache Invalidation

Batches must be marked stale when:

| Event | Action |
|---|---|
| New `mvr_people` rows materialized for a video inside a batch's window | `UPDATE mvr_search_sessions SET is_stale = TRUE WHERE batch_camera_id = ? AND batch_start_utc <= ? AND batch_end_utc >= ?` |
| Hierarchical merge of `mvr_people` across the system | Mark all batches that referenced any merged uuid as stale (lookup via `result_payload @> ...` or a lightweight `mvr_search_session_people` linking table) |
| Manual force re-run | `force=true` ignores cache and overwrites the row |
| Video deleted / soft-deleted | Mark its batch stale |

The daily cron also re-processes any `is_stale = TRUE` batches as a self-healing pass.

To make merge-driven invalidation efficient we add (optional, phase 2):

```sql
CREATE TABLE mvr_search_session_people (
    search_session_uuid UUID NOT NULL REFERENCES mvr_search_sessions ON DELETE CASCADE,
    mvr_people_uuid     UUID NOT NULL,
    PRIMARY KEY (search_session_uuid, mvr_people_uuid)
);
CREATE INDEX idx_mssp_mvr_people ON mvr_search_session_people(mvr_people_uuid);
```

Populated whenever `create_search_session` writes a row. The hierarchical merge job then runs `UPDATE mvr_search_sessions SET is_stale = TRUE WHERE search_session_uuid IN (SELECT search_session_uuid FROM mvr_search_session_people WHERE mvr_people_uuid = ANY($1))`.

### 5.8 Settings UI

A dedicated section is added to the frontend at `http://localhost:3000/#/settings` → **"People Counters"** (route: `#/settings/people-counters`). It is the operator-facing surface for the entire feature.

**Tabs / sub-sections:**

1. **Status** — read-only:
   - Feature flag state (`PEOPLE_COUNTERS_ENABLED`).
   - Current worker count (low-priority + quiet-hours).
   - Last cron run timestamp + outcome per camera.
   - Live counters: batches ready / stale / pending / failed (last 7 days).
   - Mini chart: batches computed per hour for the last 24 h.

2. **Schedule & Priority** — editable:
   - Cron expression (default `30 2 * * *`).
   - Batch size in minutes (default 60).
   - Low-priority caps: `PEOPLE_COUNTERS_WORKERS`, `MAX_CPU_PCT`, `MAX_INFLIGHT`, `BACKOFF_SECONDS`.
   - Quiet-hours window + `QUIET_WORKERS`.
   - "Pause computation" master switch (stops dispatching new batches; in-flight ones complete).

3. **Cameras** — per-camera enable/disable toggle, last batch timestamp, today's coverage (e.g. `18 / 24 hours computed`), "Backfill last N days" action button.

4. **Batches Browser** — table of recent batches: `batch_key`, `video_count`, `total_individuals`, `is_stale`, `created_at`, `duration_ms`. Row actions: invalidate, re-run, view payload. Filter by camera + date.

5. **Failures / Dead-Letter** — failed batches with last error, retry count, "Retry now" action.

6. **Advanced** — similarity threshold (default 0.70), exact-mode default for `/aggregate`, retention policy (auto-drop batches whose underlying videos are deleted).

All settings are persisted via a new `/api/v1/people-counters/settings` endpoint on the orchestrator (GET/PUT) backed by a single-row config table; environment-variable defaults seed the row on first boot. Changes take effect on the next batch dispatch — no service restart required.

The Settings page is **gated by admin role** (existing role infrastructure). Non-admin users see read-only Status only.

### 5.9 New Endpoints

All under `/api/v1/people-counters/` (served by orchestrator, gateway-proxied):

| Method | Path | Purpose |
|---|---|---|
| POST | `/run-daily-batch` | Body: `{ date: 'YYYY-MM-DD', camera_ids?: string[], force?: bool }`. Kicks the per-camera batch job for the given UTC day. Returns a job id. |
| GET | `/jobs/{job_id}` | Job status + per-batch progress. |
| GET | `/aggregate?camera_id=...&start=...&end=...` | The user-facing sub-period query (§5.4). Returns the same shape as `/search/by-videos/persisted-merge-session` plus a `coverage` field describing which batches were reused vs. computed live. |
| GET | `/batches?camera_id=...&date=...` | Diagnostic listing of batches with `{ batch_key, video_count, total_individuals, is_stale, created_at }`. |
| POST | `/batches/{batch_key}/invalidate` | Admin: mark stale. |
| GET | `/settings` | Read current config (schedule, low-priority caps, quiet hours, per-camera enable). |
| PUT | `/settings` | Update config (admin only). |
| POST | `/pause` / `/resume` | Master switch from the Settings UI. |
| POST | `/batches/{batch_key}/retry` | Re-run a failed/stale batch immediately. |

Gateway proxy entries to add (mirroring existing mvr-people routes).

### 5.10 Frontend Integration

- **Analytics dashboard**: a "People Counters" tile per camera showing `total_individuals` per hour for the selected day, sourced from the batch summaries (cheap — only `summary_payload`, no `result_payload`).
- **Search screen**: when the user picks a time range, surface `coverage` (e.g. "5 of 5 batches reused — instant") so operators understand why a long-window query returned in milliseconds.
- **Camera card**: small badge "Today: N unique people seen" pulled from the day's batches.

No changes are required to the existing person-objects detail screen or media preview screen.

### 5.11 Default Similarity Threshold for Auto-Merge — 0.60

**Change**: lower the default `similarity_threshold` for MVR search with merging from **0.70 → 0.60** across the platform, and make the Settings value the single source of truth that *all* code paths consult.

**Why**: operator feedback indicates 0.70 is too conservative for our face-embedding distribution — the same person across angles/lighting frequently lands in the 0.60–0.69 band and ends up split across multiple MVR rows. 0.60 matches the empirical sweet spot already used in some manual workflows.

**Audit — places that currently hard-code 0.70 (must switch to the configured default):**

| File | Line | Context |
|---|---|---|
| `ppl-meta-vmeta/src/api/routes/mvr_people.py` | 2913 | `/search/by-videos` Body default |
| `ppl-meta-vmeta/src/api/routes/mvr_people.py` | 3755 | `/search/by-videos/persisted-merge-session` Body default |
| `ppl-meta-vmeta/src/api/routes/mvr_people.py` | 5936 | hierarchical-merge endpoint default |
| `ppl-meta-vmeta/src/background/mvr_background_processor.py` | 429 | background processor default |
| `ppl-meta-vmeta/src/background/hierarchical_merge_scheduler.py` | 61 | scheduler default |
| `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py` | 134, 140, 275 | merger defaults + contamination check |
| `ppl-meta-vmeta/src/services/mvr_service.py` | 59, 464 | service defaults |
| `ppl-meta-vmeta/src/services/individual_groups_manager.py` | 1997 | groups manager default |
| `ppl-meta-vmeta/src/main.py` | 154 | startup task default |
| `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py` | 182, 228, 884 | cross-video tracking defaults |
| `ppl-meta-vmeta/src/models/individual_group.py` | 360 | model field default |

**Implementation**:

1. Add `mvr_default_similarity_threshold` to the existing settings store (the same one that backs the Settings page) with default value `0.60`.
2. Replace every hard-coded `0.70` above with a call to `settings.get_mvr_similarity_threshold()` (or constructor injection where applicable). Endpoint Body defaults stay as fallbacks for callers that explicitly pass a value, but when the parameter is omitted the setting wins.
3. The hierarchical merge contamination check (`hierarchical_mvr_merger.py:134`) keeps a separate `contamination_similarity_threshold` — it is a **safety floor**, not a merge default, and is intentionally unaffected.
4. Tests in `test_mvr_api.py:160` updated to assert the new default.
5. The People Counters worker reads the same setting, so changing it in the UI immediately affects future batches (existing batches keep their `is_stale=FALSE` flag; operators may bulk-invalidate via §5.8 "Cameras" tab if they want the new threshold applied retroactively).

This is a behavior change with platform-wide impact and should ship as its own commit ahead of the People Counters rollout so it can be observed and reverted independently.

---

## 6. Migration Plan

Phase 1 (DDL, additive, no behavioral change):
1. Add the five columns + two indexes from §5.2 to `mvr_search_sessions`.
2. Optional: add `mvr_search_session_people` (§5.5) — can defer to phase 3.

Phase 2 (job + read-side, dark-launched):
3. Implement the daily batch job behind a feature flag `PEOPLE_COUNTERS_ENABLED`.
4. Implement `/people-counters/aggregate` and `/people-counters/run-daily-batch`.
5. Backfill the last 7 days for one pilot camera.
6. Verify: `/aggregate?start&end` for ranges spanning whole hours returns identical mvr_people lists to `/search/by-videos` over the same range, modulo merge ordering.

Phase 3 (invalidation + UI):
7. Add the `mvr_search_session_people` link table and write-side hooks in `create_search_session`.
8. Wire invalidation to hierarchical merge and to instant-detection materialization.
9. Ship the dashboard + search-screen `coverage` UI.

Phase 4 (rollout):
10. Enable the cron globally.
11. Backfill the last 30 days per camera in the background.
12. Promote `/people-counters/aggregate` to be the default execution path for any user search whose `[start, end]` spans ≥ 1 full hour; fall back to `/search/by-videos/persisted-merge-session` otherwise.

---

## 7. Validation Plan

- **Correctness parity**: for a chosen camera and day, run `/search/by-videos` over the full day vs. `/people-counters/aggregate` for the same range and assert `total_individuals` agree within ±1% (small drift is acceptable due to the cross-batch merge being a 2-pass approximation of the global merge).
- **Idempotency**: running the daily cron twice on the same day produces zero net DB writes (UPSERT on `batch_key`).
- **Concurrency**: two simultaneous `run-daily-batch` calls for the same `(date, camera)` produce one batch row, not two (advisory lock).
- **Invalidation**: after a hierarchical merge of two `mvr_people` known to live in batches B1 and B2, both batches are flagged `is_stale = TRUE`; the next cron pass re-materializes them and the merged person appears once.
- **Performance budgets**:
  - Daily cron, single camera, 24 hourly batches, ~10 videos/hour: target < 5 min.
  - `/aggregate` over a 5-hour range, all batches present: target < 200 ms (DB reads + in-memory merge).
  - `/aggregate` over a 5-hour range with 30-min edge gaps on each side: target < 5 s (one fresh per-video merge per gap).

---

## 8. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Hour-boundary leakage of appearances | Midpoint assignment (§5.1); document the ±batch_size/2 bound in the API. |
| `result_payload` size growth (large batches with many people) | Already paginated by `limit` in the underlying endpoint; keep `limit=100` per batch. Compress JSONB if it becomes an issue. |
| Stale batches if invalidation hook is missed | Daily cron self-heals by re-running any `is_stale = TRUE` rows. Add a Prometheus gauge for `mvr_search_sessions_stale_count`. |
| Cross-batch merge approximation differs from full merge | Quantify drift in validation; tune similarity threshold; offer a `mode=exact` flag that disables batch reuse for high-stakes queries. |
| Schema change on a hot table | All DDL is additive (new columns NULL-default, new index `WHERE batch_key IS NOT NULL`). Safe online migration. |

---

## 9. Open Questions

- Q1. Should batches be **per-camera** or **per-camera-group** (e.g. all cameras in one zone)? Phase 1 ships per-camera; per-group is a future extension.
- Q2. Should the user query auto-merge across batches, or return them as separate sections that the UI stitches? Proposal: server-side merge for API simplicity.
- Q3. Retention: how long do we keep batch rows? Suggest tying to media retention — when the underlying videos are deleted, drop the batches.
- Q4. Should `similarity_threshold` be configurable per-batch or fixed? Fixed at 0.70 in phase 1 (matches today's default); make it a column in phase 2 if operators ask.

---

## 10. Summary

We can deliver people-counter-style batched search **without changing the merge engine**, by:
1. Adding a small set of columns to `mvr_search_sessions` to mark certain rows as **batches**.
2. Running a daily cron that pre-computes one merged session per `(camera, hour)` via the existing `/search/by-videos/persisted-merge-session` endpoint.
3. Adding a thin `/people-counters/aggregate` endpoint that decomposes a user's `[start, end]` into reused batches plus minimal edge-gap fresh searches, then runs an in-memory cross-batch merge.

The result: arbitrary multi-hour MVR queries become near-instant for typical operator review patterns, while the heavy similarity-merge work runs once per batch in the background.
