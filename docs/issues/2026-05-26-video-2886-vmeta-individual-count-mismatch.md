# Video 2886 VMeta Individual Count Mismatch

## Summary

For media `2886beb9-5166-45a2-a82d-1b91c0babd3d`, the expected grouped individual count is `4`.

Manual UI testing still shows `24` individuals in cross-video/individual analysis.

Backend-only evidence is internally contradictory for this exact video:

- Vision/Orchestrator persisted person objects report `4` grouped persons.
- VMeta single-media materialization reports `skipped_existing` with `24` existing MVR people for the same media.

This means the remaining issue is no longer just a frontend rendering problem. There is strong evidence of a backend-side VMeta counting/materialization/search inconsistency for this video.

## Expected Result

- Backend grouped persons for media `2886beb9-5166-45a2-a82d-1b91c0babd3d`: `4`
- UI analysis count for this media should resolve to `4`

## Backend-Only Evidence For This Specific Video

### Vision / Orchestrator evidence: 4 grouped persons

From `ppl-meta-orchestrator/logs/ppl-meta-orchestrator.log.1`:

- `2026-05-26 06:45:59,773`: raw Vision response includes `total_faces: 112`
- `2026-05-26 06:45:59,960`: `Materializing 4 persisted person objects into VMeta for media 2886beb9-5166-45a2-a82d-1b91c0babd3d`
- `2026-05-26 06:46:00,062`: `Retrieved 4 persisted person groups from session e078770f-68fb-4e63-8605-fbf66a2e6dc7`

Repeated again later for the same media:

- `2026-05-26 06:53:45,438`: `Materializing 4 persisted person objects into VMeta for media 2886beb9-5166-45a2-a82d-1b91c0babd3d`
- `2026-05-26 06:53:45,548`: `Retrieved 4 persisted person groups from session e078770f-68fb-4e63-8605-fbf66a2e6dc7`

Conclusion:

- The Vision-side temporal grouping result for this exact media is `112 faces -> 4 persisted person groups`.

### VMeta materialization evidence: 24 existing MVR people

From the same orchestrator log for the same media:

- `2026-05-26 06:45:59,975`:
  - `status: 'skipped_existing'`
  - `existing_mvr_people_count: 24`
  - `mvr_people_count: 24`
  - `total_faces_detected: 4`

- `2026-05-26 06:53:45,467`:
  - `status: 'skipped_existing'`
  - `existing_mvr_people_count: 24`
  - `mvr_people_count: 24`
  - `total_faces_detected: 4`

Conclusion:

- VMeta believes this media already has `24` reachable MVR identities and therefore refuses to re-materialize from the current `4` person objects.

### Direct VMeta database evidence: 24 reachable rows for this media

Direct SQL inspection against local database `ppl_meta_vmeta` for media `2886beb9-5166-45a2-a82d-1b91c0babd3d` returned:

- `COUNT(DISTINCT individual_uuid)` in `individual_video_appearances` = `24`
- `COUNT(DISTINCT mvr_people_uuid)` through `individual_mvr_mapping` = `24`
- `COUNT(DISTINCT mvr_people_uuid)` in `mvr_people WHERE source_media_uuid = video_uuid` = `24`

Additionally, every returned row was effectively one-to-one:

- `1` distinct `individual_uuid` per `mvr_people_uuid`
- `1` IVA row per `mvr_people_uuid`
- all rows had `source_media_uuid = 2886beb9-5166-45a2-a82d-1b91c0babd3d`
- all rows had `is_orphaned = false`

This confirms the stale/inflated `24` count is physically present in VMeta tables for this media, not just a frontend-derived number.

## Why This Looks Like A Backend Issue

The contradiction exists before the frontend aggregates anything:

- Vision persisted grouping says the media contains `4` persons.
- VMeta materialization skip logic says the same media already has `24` active MVR identities.

If both values are derived from backend state for the same media UUID, the backend contract is already inconsistent.

That makes the current primary suspect a VMeta-side stale or incorrect single-media state, not a pure frontend counting bug.

## Strongest Suspect Fallback Methods

These fallback or reuse paths are the strongest suspects because they can preserve or re-surface stale `24`-count state.

### 1. Single-media materialization fallback: `skipped_existing`

In `ppl-meta-vmeta/src/api/routes/mvr_people.py`, `_materialize_single_media_from_persisted_person_objects(...)` does this before any new materialization:

- Count existing reachable MVR people via:
  - `mvr_people`
  - `individual_mvr_mapping`
  - `individual_video_appearances`
- If any rows exist, return immediately with `status="skipped_existing"`

Observed effect for this video:

- Current materialization input = `4` persisted person objects
- Skip gate says existing reachable MVR rows = `24`
- Result: VMeta never rebuilds the media from the current grouped person-object truth

Why this is suspicious:

- The skip gate may be treating stale or duplicated IVA/mapping state as authoritative.
- Once `existing_count` is non-zero, fresh grouped person-object input is ignored.

Status update:

- A targeted backend fix has now been prepared in `ppl-meta-vmeta/src/api/routes/mvr_people.py`.
- New behavior: if reachable existing VMeta rows for a media do not match the current persisted person-object count, VMeta deletes the per-video IVA/mapping/MVR rows and rebuilds them instead of returning `skipped_existing`.

### 2. Search fallback: raw `/search/by-videos` returns unmerged linked MVR rows

In `ppl-meta-vmeta/src/api/routes/mvr_people.py`, `/search/by-videos` defaults to:

- fetch linked MVR rows directly from `individual_mvr_mapping`
- no merge unless `auto_merge=true`

Why this is suspicious:

- If a UI path or internal backend path falls back to raw `/search/by-videos`, the result can legitimately be `24` linked MVR rows instead of `4` grouped identities.

### 3. Persisted merge session reuse can preserve stale result payloads

In `ppl-meta-vmeta/src/api/routes/mvr_people.py`, `/search/by-videos/persisted-merge-session` does this:

- if `ignore_existing_session=false`
- and an existing session with the same input exists
- it returns the stored `result_payload` directly

Why this is suspicious:

- A previously stored persisted merge session may be re-used even if backend data for the media has since changed.
- If that stored payload was based on an older `24`-identity state, the UI will keep seeing `24`.

### 4. Persisted merge session internally forces `ignore_existing_hierarchy=true`

The persisted merge-session endpoint calls `/search/by-videos` with:

- `auto_merge=true`
- `ignore_existing_hierarchy=true`

Why this is suspicious:

- This path intentionally ignores the already-persisted hierarchy and rebuilds a merge preview from base linked MVR rows.
- If the base linked rows for this video are already inflated to `24`, the merge preview is responsible for collapsing them back to `4`.
- If preview grouping under-performs or works on polluted input, the output can remain inflated.

### 5. Auto-merge failure fallback returns unmerged results

In `/search/by-videos`, when `auto_merge=true`:

- VMeta runs `preview_hierarchical_merge(...)`
- if that merge throws an exception, the code logs the error and returns unmerged results

Why this is suspicious:

- Any merge-preview failure would silently preserve the raw result count rather than failing hard.
- That would surface as `24` instead of `4`.

### 6. Rematerialization fallback for invalid linked embeddings

When `auto_merge=true`, `/search/by-videos` checks for invalid linked MVR rows.
If found, it can call a fallback rematerialization path for the target videos.

Why this is suspicious:

- If the fallback path reuses or preserves polluted IVA/MVR mappings instead of rebuilding a clean per-video state, it can keep the inflated count alive.

## Working Hypothesis

For media `2886beb9-5166-45a2-a82d-1b91c0babd3d`:

1. Vision persisted person-object grouping is correct at `4`.
2. VMeta has stale or duplicated single-media IVA/MVR mapping state already reachable for this video.
3. The `skipped_existing` gate prevents VMeta from rebuilding from the current `4` grouped person objects.
4. Search or persisted-merge-session paths then operate on that stale `24`-row VMeta state.

## What Must Be Verified Next

### Backend-only checks

Run backend-only checks for this exact media UUID:

1. Query reachable VMeta rows for `video_uuid = 2886beb9-5166-45a2-a82d-1b91c0babd3d`
   - count distinct `individual_uuid` in `individual_video_appearances`
   - count distinct `mvr_people_uuid` through `individual_mvr_mapping`
   - list all linked `mvr_people_uuid`

2. Compare those rows against the current Vision person-object session:
   - session `e078770f-68fb-4e63-8605-fbf66a2e6dc7`
   - expected persisted person groups: `4`

3. Verify whether `/search/by-videos/persisted-merge-session` for only this video returns:
   - raw count near `24`
   - merged count `4`
   - reused existing session payload versus fresh merge result

4. Verify whether a stored persisted merge session is being reused for this input.

5. Verify whether merge preview is logging a reduction for this exact request, or whether it is falling back to unmerged results.

## Likely Fix Directions

### Option A: Fix the single-media `skipped_existing` gate

The most direct backend fix is likely here.

Instead of treating any reachable IVA/MVR state as sufficient to skip, validate that the existing per-video VMeta state is consistent with the current persisted person-object input.

If inconsistent, re-materialize instead of skipping.

### Option B: Invalidate persisted merge sessions when source video state changes

If persisted merge sessions are reused across stale VMeta state, invalidate or bypass them when the underlying video materialization state changed.

### Option C: Add a forced clean rebuild path for one media UUID

For diagnostics and repair, add or use a backend-only path that:

- deletes per-video IVA/mapping/MVR rows for one media UUID
- rebuilds from persisted person objects
- confirms resulting distinct MVR count

## Current Conclusion

For media `2886beb9-5166-45a2-a82d-1b91c0babd3d`, backend-only evidence is already enough to justify a backend bug investigation:

- Vision persisted groups: `4`
- VMeta existing reachable MVR count for the same media: `24`

Until that contradiction is resolved, the frontend cannot be considered the sole source of the wrong count.