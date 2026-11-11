# MVR Search Persistence Upgrade Proposal

## Purpose

This proposal analyzes an upgrade of the existing MVR search process so that:

- all base MVR data objects produced by MVR searches are persisted in the database
- any super-individuals produced by merge-enabled searches remain ephemeral and are not persisted as search-owned hierarchy
- merge-enabled search results are stored in a new persistent search-results layer
- repeated searches with the same effective input can reuse previously computed results instead of re-running the full flow

This proposal is intentionally aligned with the current architecture in which:

- `search/by-videos` is the main MVR search entry point
- missing per-video MVR rows can already be materialized on demand
- merge-enabled search currently uses an ephemeral preview flow
- persisted hierarchy in `mvr_merge_hierarchy` exists today but should be ignored for this new search mode

## Current Behavior

The current search flow is split across two modes:

1. Base search:
   - frontend resolves media first
   - frontend sends `video_uuids` to `POST /api/v1/mvr-people/search/by-videos`
   - backend returns persisted MVR people linked to those videos

2. Merge-enabled search:
   - backend can build an in-memory merge preview using `HierarchicalMVRMerger.preview_hierarchical_merge(...)`
   - preview groups winners and merged members without persisting new hierarchy state
   - frontend uses the preview output to render cross-video merged analysis

There is already one important foundation in place:

- if a target video has no persisted MVR rows yet, the search endpoint can materialize isolated per-video MVR rows during fallback

That means the repo already supports part of the requested design:

- persistent storage of base MVR objects per video
- ephemeral merge output for search-time grouping

What is missing is the persistent search-results layer and the reuse logic keyed by search identity.

## Requested Target Behavior

For merge-enabled MVR search, the desired flow is:

1. Determine whether the same search input has already produced results.
2. If yes, return the stored result session instead of recomputing.
3. If no, ensure all target videos have persisted base MVR rows.
4. Run merge on the found and any newly created base MVR rows.
5. Persist the search session summary and inputs.
6. Return the stored search session result.

The requested persistence rules are:

- persist all base MVR rows produced for videos
- do not persist search-produced super-individual hierarchy
- do persist a search session and its summary output
- ignore past stored super-individual hierarchy when executing this search mode

The requested stored search summary includes:

- search session UUID
- total individuals
- total appearances
- unique videos
- average confidence
- average quality
- total duration
- search time span
- first appearance
- last appearance
- total men
- total women
- total unknown
- average age
- cameras involved
- videos involved
- start date
- end date

## Main Design Decision

The cleanest design is to separate three concepts that are currently partially entangled:

1. Base MVR persistence
   - stable, per-video, per-individual, database-owned MVR records

2. Persisted long-lived merge hierarchy
   - current `mvr_merge_hierarchy`
   - should not participate in this new search mode

3. Search-session merge result
   - new persistent layer
   - stores summary and input identity for a merge-enabled search run
   - does not mutate global MVR hierarchy

This separation matters because the user requirement is not “make search merges globally real”.
It is “make base MVR rows real, but keep search-time super-individuals session-scoped”.

## Recommended Architecture

### 1. Keep base MVR rows persistent

When merge-enabled search runs, the system must first guarantee that every requested video has persisted base MVR rows.

Recommended rule:

- for each requested video UUID, check whether isolated base MVR rows already exist
- if not, materialize them using the current single-media fallback path
- persist only base MVR rows and their normal mappings
- do not create search-owned hierarchy in `mvr_merge_hierarchy`

This aligns with the existing fallback already implemented in `search/by-videos`.

### 2. Add a new persistent search-session layer

Create a new persistence layer dedicated to merge-enabled search sessions.

Recommended tables:

#### `mvr_search_sessions`

Purpose:

- one row per persisted merge-enabled search result

Suggested columns:

- `search_session_uuid UUID PRIMARY KEY`
- `search_mode TEXT NOT NULL`
  value for this proposal: `merge_preview`
- `same_input_key TEXT NOT NULL`
- `created_at TIMESTAMP NOT NULL`
- `updated_at TIMESTAMP NOT NULL`
- `requested_start_date TIMESTAMP NULL`
- `requested_end_date TIMESTAMP NULL`
- `search_time_span_seconds DOUBLE PRECISION NULL`
- `total_individuals INTEGER NOT NULL`
- `total_appearances INTEGER NOT NULL`
- `unique_videos INTEGER NOT NULL`
- `average_confidence DOUBLE PRECISION NOT NULL`
- `average_quality DOUBLE PRECISION NOT NULL`
- `total_duration_seconds DOUBLE PRECISION NOT NULL`
- `first_appearance TIMESTAMP NULL`
- `last_appearance TIMESTAMP NULL`
- `total_men INTEGER NOT NULL DEFAULT 0`
- `total_women INTEGER NOT NULL DEFAULT 0`
- `total_unknown INTEGER NOT NULL DEFAULT 0`
- `average_age DOUBLE PRECISION NULL`
- `result_payload JSONB NOT NULL`
  stores the actual merge preview output returned to the client
- `summary_payload JSONB NOT NULL`
  stores the denormalized summary payload for direct reuse

#### `mvr_search_session_cameras`

Purpose:

- normalized list of cameras participating in the session

Suggested columns:

- `search_session_uuid UUID NOT NULL`
- `camera_id TEXT NOT NULL`

Unique index:

- `(search_session_uuid, camera_id)`

#### `mvr_search_session_videos`

Purpose:

- normalized list of videos participating in the session

Suggested columns:

- `search_session_uuid UUID NOT NULL`
- `video_uuid UUID NOT NULL`
- optional `camera_id TEXT NULL`
- optional `media_timestamp TIMESTAMP NULL`

Unique index:

- `(search_session_uuid, video_uuid)`

### 3. Define “same input” precisely

The user requirement says “same input” means:

- same cameras involved
- same video UUIDs involved
- dates are not part of sameness

That means the authoritative reuse key should be built from canonical camera and video sets, not timestamps.

Recommended rule:

- sort camera IDs
- sort video UUIDs
- hash the two sorted lists into `same_input_key`

Example logical key:

- `sha256(join(sorted(camera_ids)) + '|' + join(sorted(video_uuids)))`

This is much safer than fuzzy date-window matching as a primary key.

### 4. Use date-range lookup only as a performance optimization

The request says to first check existing sessions for the cameras involved in a span around the one given, and then drill down to same-search criteria.

That should be treated as a candidate-reduction strategy, not the source of truth.

Recommended lookup flow:

1. Find candidate sessions that reference any of the requested cameras and whose stored request dates are near the incoming dates.
2. From those candidates, compare canonical camera set equality.
3. Compare canonical video UUID set equality.
4. If both sets match exactly, treat as same input and reuse.

This preserves the requested operational flow while avoiding incorrect matches caused by date heuristics.

## Proposed Execution Flow

For merge-enabled search:

1. Resolve media input.
   - frontend still asks media service for videos from selected cameras and date range
   - backend receives the final `video_uuids`

2. Build canonical input identity.
   - derive `camera_ids`
   - derive sorted `video_uuids`
   - derive `same_input_key`

3. Look for an existing persisted search session.
   - narrow by cameras and approximate date span if desired
   - confirm by exact camera-set equality and exact video-set equality

4. If a matching session exists:
   - return stored `result_payload` and `summary_payload`
   - do not rerun materialization
   - do not rerun merge

5. If no matching session exists:
   - for each target video, ensure base MVR rows exist
   - materialize missing videos without merge

6. Gather base MVR rows for the requested videos.
   - query only base stored MVR rows
   - ignore `mvr_merge_hierarchy`
   - ignore pre-existing super-individual roots for this search mode

7. Run ephemeral merge.
   - use preview-style grouping only
   - no writes to `mvr_merge_hierarchy`
   - no writes that orphan losers into a winner

8. Compute session summary.
   - total individuals
   - total appearances
   - unique videos
   - average confidence
   - average quality
   - total duration
   - search time span
   - first appearance
   - last appearance
   - total men / women / unknown
   - average age

9. Persist the search session.
   - insert `mvr_search_sessions`
   - insert related camera rows
   - insert related video rows
   - store full result payload

10. Return the persisted session output.

## Critical Rule: Ignore Persisted Hierarchy

The requirement says all these searches should ignore past stored super-individual hierarchy.

That has major architectural consequences.

For this new mode, `search/by-videos` should not:

- walk `merged_into_mvr_uuid`
- expand descendants from a root winner
- reuse `mvr_merge_hierarchy`
- collapse orphaned rows into a persisted winner

Instead, it should:

- fetch base stored MVR rows linked directly to the target videos
- treat them as the raw merge candidates
- run session-scoped merge preview on those candidates only

This is the most important behavioral change in the proposal.

Without this rule, old persisted hierarchy contaminates new search sessions and prevents the search-session layer from being a true record of the search result for the requested inputs.

## Data Model Recommendation

The persistent search layer should store both:

1. normalized relational identity data
2. denormalized result snapshot data

That dual model is recommended because:

- normalized rows support efficient “same input” lookup
- snapshot JSON supports fast reuse and exact replay of the UI payload
- summary columns support reporting and indexing without reparsing JSON

Recommended persistence split:

- relational:
  - session row
  - camera links
  - video links
- JSON snapshot:
  - merge groups
  - grouped individuals returned to UI
  - statistics block
  - search parameters block

## API Recommendation

Add a new backend search mode instead of overloading the existing endpoint semantics too aggressively.

Recommended new endpoint:

- `POST /api/v1/mvr-people/search/by-videos/persisted-merge-session`

Suggested request:

- `camera_ids`
- `video_uuids`
- `start_time`
- `end_time`
- `limit`
- `similarity_threshold`
- `force_refresh` or `ignore_existing_session`

Suggested response:

- `search_session_uuid`
- `reused_existing_session: bool`
- `summary`
- `result_payload`
- `search_parameters`

This is preferable to mutating the meaning of existing `auto_merge=true` because the current endpoint is documented as a cached search endpoint with optional ephemeral merge preview, not as a persistent session creator.

## Reuse Semantics

Recommended reuse behavior:

- if exact same camera set and exact same video set exists, reuse regardless of requested dates
- always return the stored dates that belonged to the reused session as session metadata
- optionally also include the newly requested dates in response metadata for transparency

Important note:

If date range is excluded from sameness, then two searches with the same videos but different requested dates must intentionally reuse the same search session. That is consistent with the user requirement, but it should be documented clearly because it can surprise operators.

## Summary Computation Rules

The session summary should be computed from the final grouped search result, not from the raw base MVR rows.

Recommended rules:

- `total_individuals`
  - count final grouped results after ephemeral merge

- `total_appearances`
  - sum appearances across final grouped results

- `unique_videos`
  - union of video UUIDs across grouped appearances

- `average_confidence`
  - average of grouped-result confidence values

- `average_quality`
  - average of grouped-result quality values

- `total_duration_seconds`
  - sum of grouped-result durations

- `search_time_span_seconds`
  - derived from requested start/end dates, not from appearance duration

- `first_appearance` and `last_appearance`
  - derived from grouped appearances

- demographics counts and average age
  - derived from grouped demographics payloads
  - if demographics missing, classify as unknown and exclude from average age

## Risks and Tradeoffs

### 1. Reuse based on videos instead of dates

Risk:

- users may expect a narrower date search to create a different result

Mitigation:

- expose `reused_existing_session`
- return both stored session dates and requested dates
- allow `ignore_existing_session=true` when a fresh run is needed

### 2. Snapshot drift from base MVR changes

Risk:

- if underlying MVR rows later change, old search session snapshots may no longer match current live data

Mitigation:

- treat search session rows as immutable historical snapshots
- optionally add source version metadata or invalidation policy later

### 3. Ignoring persisted hierarchy increases duplicate candidates

Risk:

- merge-enabled searches may process more raw candidates than today

Mitigation:

- this is required by the requested behavior
- input reuse and persisted sessions should offset runtime cost for repeated searches

### 4. Storing only summary is insufficient

Risk:

- summary-only persistence would force recomputation of the actual grouped results when the UI needs details

Mitigation:

- store the full result snapshot in JSON alongside the summary columns

## Recommended Implementation Phases

### Phase 1. Persistence schema

- create `mvr_search_sessions`
- create `mvr_search_session_cameras`
- create `mvr_search_session_videos`
- add indexes on `same_input_key`, `created_at`, and join tables

### Phase 2. Repository layer

- add repository methods to:
  - find candidate sessions by camera and date span
  - compare exact camera/video sets
  - load full persisted session payload
  - persist new session and related rows

### Phase 3. Search service orchestration

- add a dedicated persistent merge-session endpoint or service method
- ensure missing per-video MVR rows are materialized before merge
- query base stored MVR rows only
- ignore persisted hierarchy for this mode
- run ephemeral merge preview
- compute summary and persist session

### Phase 4. Frontend integration

- switch merge-enabled search to the new endpoint
- preserve existing analysis navigation shape
- surface whether results were reused or freshly computed

## Recommended Final Position

This upgrade should be implemented.

It is consistent with the current codebase direction because:

- base MVR materialization already exists
- ephemeral merge preview already exists
- current search results already drive the analysis screen

The missing architectural piece is a search-session persistence layer that records merge-enabled search output without polluting global MVR hierarchy.

The strongest recommendation is:

- persist base MVR rows per video
- keep search-generated super-individuals ephemeral
- persist search sessions and their full result snapshots
- key reuse by canonical camera and video sets
- treat date-range proximity only as a candidate lookup optimization
- completely ignore prior persisted hierarchy in this new search mode

That design best matches the requested behavior and minimizes unintended interaction between global merge history and search-session-specific results.
