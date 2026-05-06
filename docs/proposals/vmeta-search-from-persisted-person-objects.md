# VMeta Search From Persisted Person Objects

**Status:** Proposal  
**Date:** 2026-05-06

Implementation follow-up:

- see `docs/proposals/vmeta-person-object-materialization-implementation-spec.md`

## Problem

The continuous pipeline now persists correct single-video truth in Vision and exposes it correctly through Orchestrator:

- stored face detections
- stored person objects
- stable persisted `person_id`
- stored route-point histories

But VMeta video search and count flows still depend on legacy local materialization in VMeta:

- `individual_video_appearances`
- `individuals`
- `individual_mvr_mapping`
- `mvr_people`

If those VMeta rows do not exist yet, `search/by-videos` returns zero even when persisted person objects already exist upstream.

## Verified Example

The following videos had persisted person groups in Orchestrator / Vision but zero VMeta search results:

- `8529cf30-6373-466c-8987-feeab04d1e39`
- `d64b2ce9-d432-499b-861d-fc7dd002071d`
- `1d059949-dc4c-4bc1-8f57-5a8a77a459b1`

Observed state:

- Orchestrator returned persisted `person_groups`
- Vision had persisted `person_objects`
- VMeta had no `individual_video_appearances` rows for those media
- VMeta had no `mvr_people.source_media_uuid` rows for those media
- `POST /api/v1/mvr-people/search/by-videos` returned `total_results = 0`

This proves the failure is not in the continuous pipeline. It is at the VMeta integration boundary.

## Root Cause

VMeta search is still treating legacy local rows as the gatekeeper for discovery.

Current search contract:

```text
video_uuid
-> individual_video_appearances
-> individual_uuid
-> individual_mvr_mapping
-> mvr_people
```

Current continuous pipeline truth:

```text
media_uuid
-> persisted Vision person_objects
-> stable person_id
-> representative faces + route points
```

These two graphs are not aligned.

## Verified Missing Integration

### What *is* auto-triggered today

Frontend / Orchestrator auto-trigger person-object creation after face detection:

- `ppl-meta-frontend/lib/providers/person_objects_provider.dart`
- `ppl-meta-frontend/lib/services/person_objects_api_client.dart`

This ensures person objects can be materialized and later read through Orchestrator.

### What is *not* auto-triggered today

The VMeta single-media materialization path is separate:

- `POST /api/v1/mvr-people/process-media`
- `ppl-meta-frontend/lib/services/vision_processing_service.dart`

That path is explicit/manual and is not part of the normal continuous pipeline contract.

### Why the existing VMeta background hook does not solve this

VMeta background MVR creation only runs when VMeta itself creates an `individual`:

- `ppl-meta-vmeta/src/database/repository.py`
- `ppl-meta-vmeta/src/background/mvr_helper.py`
- `ppl-meta-vmeta/src/background/mvr_background_processor.py`

That means:

- if VMeta never creates the `individual`
- then no background MVR hook fires
- and no `individual_video_appearances` / `individual_mvr_mapping` / `mvr_people` rows appear

So the missing step is not just “run the hook.” The missing step is that the continuous persisted person-object pipeline never enters the VMeta `individual` creation path in the first place.

## Design Goal

Make persisted single-video person objects the canonical source for VMeta single-video discovery.

## Recommended Direction

### Option A: Explicit materialization job from persisted person objects

Create a durable backend job that:

1. reads persisted Vision person objects for a media UUID
2. creates VMeta `individuals`
3. creates `individual_video_appearances`
4. creates `individual_mvr_mapping`
5. creates isolated `mvr_people` with `source_media_uuid`

This materialization should run automatically after persisted person objects are available, not only from a manual UI action.

### Option B: Search reads directly from persisted person objects, then materializes lazily

Refactor `search/by-videos` so it can:

1. detect missing local VMeta rows for the requested videos
2. read persisted Orchestrator / Vision person objects directly
3. materialize the missing isolated VMeta rows before executing the normal search query

This is operationally simpler at first, but it still relies on a search-triggered write path.

### Recommended long-term target

Option A is the cleaner architecture.

Reason:

- materialization becomes explicit and durable
- search endpoints stay read-oriented
- VMeta tables remain the durable search/count layer
- the continuous pipeline and the VMeta layer become aligned by design, not by fallback behavior

## Required Invariants

After the refactor, these should always be true for a materialized video:

1. every persisted Vision person object that should be searchable has a corresponding VMeta `individual`
2. every searchable VMeta individual has an `individual_video_appearance`
3. `individual_video_appearances.person_object_uuid` equals the persisted Vision `person_id`
4. every searchable single-video individual has an `individual_mvr_mapping`
5. every searchable single-video MVR row has `is_isolated = true` and `source_media_uuid = media_uuid`

## Non-Goals

This proposal does not recommend:

- adding permanent ad hoc read-time fallback logic everywhere
- bypassing VMeta persistence entirely for analytics/search/count endpoints
- treating regroup-on-read person objects as authoritative when persisted person objects already exist

## Practical Next Step

Implement and document a backend-owned materialization contract:

```text
persisted person objects available
-> single-media VMeta materialization job runs
-> search/count endpoints can discover the video through normal VMeta tables
```

That is the missing architecture bridge today.
