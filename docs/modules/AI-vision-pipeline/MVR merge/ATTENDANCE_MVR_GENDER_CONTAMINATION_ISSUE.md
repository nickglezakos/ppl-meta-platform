# MVR Merge — Attendance Gender Contamination via Active Root MVRs

**Status:** VERIFIED against codebase, logs, and live database queries  
**Date:** 2026-05-05  
**Severity:** HIGH — analytics and attendance gender summaries can be materially wrong

---

## The Problem in One Sentence

Attendance and demographics analytics can report an all-male result even when the underlying video individuals are female or unknown, because the analytics path aggregates from the surviving active `mvr_people` roots rather than from the underlying linked individuals or person objects.

---

## Verified Scope

This issue affects the analytics-style demographics path that goes through gateway analytics and camera MVR counters.

It does **not** describe the same rendering path as the person-detail Attendance tab in cross-video analysis, which builds its view from already-loaded aggregated appearances.

---

## Code-Verified Request Path

### Frontend analytics path

The analytics dashboard calls:

- `getAnalyticsSummary(...)`
- `getDemographicsBreakdown(...)`

Files:

- `ppl-meta-frontend/lib/screens/analytics_screen.dart`
- `ppl-meta-frontend/lib/services/media_api_client.dart`

### Gateway aggregation path

The gateway demographics handler aggregates per camera by calling:

```text
GET /api/v1/cameras/{camera_id}/mvr-count
```

File:

- `ppl-meta-gateway/src/api/v1/analytics.py`

Relevant behavior:

1. Enumerate selected cameras
2. Call `/api/v1/cameras/{camera_id}/mvr-count`
3. Read `count` and `demographics` from that response
4. Sum `total_male`, `total_female`, `total_unknown_gender`, etc.

### Camera counter path

The camera MVR count endpoint computes demographics by:

1. Fetching videos for the camera and date range from Media
2. Sending those `video_uuids` to VMeta
3. Returning MVR-based count and demographics

File:

- `ppl-meta-gateway/src/api/v1/camera_counters.py`

### VMeta demographic source

The decisive source is:

- `ppl-meta-vmeta/src/api/routes/mvr_people.py`

The demographic count query reads **active root MVR rows**:

```sql
SELECT 
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE LOWER(mp.gender) = 'male') as male_count,
    COUNT(*) FILTER (WHERE LOWER(mp.gender) = 'female') as female_count
FROM mvr_people mp
WHERE mp.mvr_people_uuid IN (SELECT mvr_people_uuid FROM linked_mvr_people)
  AND mp.is_orphaned = false
```

This means the analytics path is counting `mvr_people.gender`, not `individuals.gender_estimate` and not person-object demographics.

---

## Live Evidence — USB Camera 04

### Camera identity

Verified in `ppl_media_db`:

- Collection name: `USB Camera 04`
- Camera device id: `251263da-b850-4ca0-bc19-3f048664f035`

### Six-video investigation subset

The six-video subset repeatedly involved in the contamination investigation is:

- `cf11360a-1616-4db7-b746-0f9521e3165d`
- `77d9fd50-abab-43b7-b1b5-eee0cb92dc5d`
- `f22b08ec-69af-4a92-8bdd-d569d7ebfe9f`
- `d233ed4e-6b35-4cb7-9bbe-3258d15bd018`
- `e3d88b2c-a3a8-470f-aa47-c7d0210b251c`
- `67a5b5a6-2e1f-49c3-b853-eb97672068be`

### Endpoint-equivalent MVR result for the six-video subset

Live query result:

| Layer                     | Total | Male | Female | Unknown gender |
| ------------------------- | ----: | ---: | -----: | -------------: |
| Active MVR roots          |     2 |    2 |      0 |              0 |

Active root MVR rows:

| MVR UUID                               | Gender | is_orphaned |
| -------------------------------------- | ------ | ----------- |
| `710272d0-4357-45b9-9b57-b00904e7a01f` | male   | false       |
| `ab24bf76-5e5d-494b-9987-2247aca4cdf9` | male   | false       |

### Raw underlying individuals for the same six-video subset

Live query result:

| Layer                       | Total | Male | Female | Unknown gender |
| --------------------------- | ----: | ---: | -----: | -------------: |
| Distinct linked individuals |    26 |    0 |      0 |             26 |

This proves the male-only result is being introduced by the MVR layer, not by the raw linked individual layer.

### Full raw date-range check

For the full raw USB04 date range from `2026-04-27` to `2026-05-05`, the pattern remains the same:

| Layer                       | Total | Male | Female | Unknown gender |
| --------------------------- | ----: | ---: | -----: | -------------: |
| Active MVR roots            |     2 |    2 |      0 |              0 |
| Distinct linked individuals |    31 |    0 |      0 |             31 |

### Per-video pre-merge check

I also checked each USB04 video separately before any cross-video merge interpretation.

Result: the raw per-video `individuals` layer does not contain male or female labels for these videos. The `male` labels appear only in the single-media `mvr_people` rows created for a subset of the videos.

|Filename|Video UUID|Raw individuals|Raw male|Raw female|Raw null gender|Single-media MVRs|MVR male|MVR female|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|`8aa19fd81ca37223fd1a565d10d73cf6.mp4`|`cf11360a-1616-4db7-b746-0f9521e3165d`|0|0|0|0|0|0|0|
|`91996512f43136f41fada7cf53633957.mp4`|`77d9fd50-abab-43b7-b1b5-eee0cb92dc5d`|0|0|0|0|0|0|0|
|`aebb139a030f627f0228ee657079f8a6.mp4`|`f22b08ec-69af-4a92-8bdd-d569d7ebfe9f`|6|0|0|6|6|6|0|
|`5cded9f237243e7964e676958e8c7a24.mp4`|`d233ed4e-6b35-4cb7-9bbe-3258d15bd018`|6|0|0|6|6|6|0|
|`395d653b0f6a30479ab71096ec8ad082.mp4`|`e3d88b2c-a3a8-470f-aa47-c7d0210b251c`|7|0|0|7|4|4|0|
|`9fb326e641a9e7898e01dee6420c1bcb.mp4`|`67a5b5a6-2e1f-49c3-b853-eb97672068be`|7|0|0|7|4|4|0|
|`d5d022ea1dcc3c9d4eb7f3d5004a0b54.mp4`|`5d774c32-d83c-4705-952c-bba5f837c1a7`|2|0|0|2|0|0|0|
|`716009a450bf2d98f95aa16829b8fdac.mp4`|`1e45febf-b8a8-44ee-a389-17dbbd82a849`|2|0|0|2|0|0|0|
|`dbdef644e4174665ec9ae416b24d92cc.mp4`|`e7864fcc-dfac-48fb-a14d-b11a63eb498d`|0|0|0|0|0|0|0|
|`2ebcaa4cf4d82feb27b10063368f053c.mp4`|`765eff23-e7e3-4624-8782-07a122706fe3`|1|0|0|1|0|0|0|

This narrows the contamination point further:

1. Raw per-video individuals are not being stored as male or female here
2. Four videos already create all-male single-media MVR rows before any cross-video merge
3. Several videos have raw tracked individuals but no persisted single-media MVR rows at all

---

## Additional Findings From Follow-up Investigation

### Finding 1: Single-media processing computes demographics but does not persist them to `individuals`

This is code-verified in:

- `ppl-meta-vmeta/src/services/mvr_service.py`

During single-media processing, ML returns `age_estimate` and `gender_estimate`, and those values are used to populate the created `mvr_people` row.

However, the same code inserts into `individuals` with only:

- `individual_uuid`
- `individual_id`
- `confidence_score`
- `spatial_signature`
- `temporal_signature`

The insert does **not** populate:

- `gender_estimate`
- `age_estimate`

So the current stored behavior is:

```text
ML demographics exist in memory during single-media processing
but are written to mvr_people only,
not to individuals
```

This directly explains why the raw `individuals` rows for these videos are all `NULL` for gender even though the system is clearly producing gender output elsewhere.

### Finding 2: Videos with no persisted MVR rows can still have tracked people

This is also verified in the current schema and endpoint behavior.

The count/search-by-videos endpoints are driven by:

1. `individual_video_appearances`
2. `individual_mvr_mapping`

The per-video count endpoint does **not** count from Media alone and does **not** create MVRs on demand. It counts mapped MVR rows only.

That means a video can be in one of these states:

1. Has people in Orchestrator / preview / live analysis
2. Has `individual_video_appearances`
3. But has no `individual_mvr_mapping` rows and no persisted `mvr_people.source_media_uuid` rows

In that state, the video will look like it contains people, but the persisted per-video MVR queries will return zero MVRs.

### Finding 3: The frontend can trigger live single-media processing separately from persisted search/count flows

The frontend Vision processing flow calls:

- `POST /api/v1/mvr-people/process-media`

from:

- `ppl-meta-frontend/lib/services/vision_processing_service.dart`
- `ppl-meta-frontend/lib/screens/collections_screen.dart`

This means some UI flows can show MVR-style results from a live processing pass, while the persisted search/count endpoints still depend on what has actually been written into:

- `individual_video_appearances`
- `individual_mvr_mapping`
- `mvr_people`

So the apparent contradiction is explainable:

```text
"video details shows MVR results"
does not necessarily mean
"this video already has persisted per-video MVR rows used by count/search endpoints"
```

### Current interpretation of the two new questions

#### Why do single MVR objects or individuals have no gender?

For `individuals`, this is explained by a persistence bug/omission in `mvr_service.py`: the code does not write `gender_estimate` into the `individuals` table during single-media creation.

For `mvr_people`, some do have gender, but it is currently being sourced directly from ML at MVR creation time, which is exactly where the incorrect `male` labels are entering for the contaminated videos.

#### Why are there videos with no MVRs even though people are scanned?

Because "people scanned" and "persisted per-video MVR rows available to count/search endpoints" are not the same condition.

The current backend/video query path requires persisted appearance and mapping rows. A video can still produce visible details or live processing output without having durable `individual_mvr_mapping` and `mvr_people` rows that the count/search endpoints rely on.

This part is strongly supported by the code and by the per-video query results above. The exact UI screen the user refers to may still need one final endpoint trace if we want to prove the precise request being made in that screen.

### Finding 4: Media preview Details uses orchestrator person-objects, not persisted per-video MVR search/count rows

This is now fully traced for the problematic video:

- `d233ed4e-6b35-4cb7-9bbe-3258d15bd018`

Frontend flow:

1. media preview wires the Details button to `PersonObjectsDetailScreen`
2. the Persons tab watches `personObjectsDataProvider(mediaUuid)`
3. that provider calls `GET /api/v1/orchestrator/person-objects/{mediaUuid}` through gateway
4. the Routes tab separately fetches the same orchestrator endpoint again

Verified request chain from logs for `d233ed4e-6b35-4cb7-9bbe-3258d15bd018`:

1. gateway receives `GET /api/v1/orchestrator/person-objects/d233ed4e-6b35-4cb7-9bbe-3258d15bd018`
2. gateway proxies to orchestrator `GET http://localhost:8002/person-objects/d233ed4e-6b35-4cb7-9bbe-3258d15bd018`
3. orchestrator runs PPL Thread detailed grouping
4. orchestrator invokes Enhanced Logic V2
5. Enhanced Logic V2 reads Vision stored faces from `http://localhost:8003/faces/media/d233ed4e-6b35-4cb7-9bbe-3258d15bd018`

The orchestrator log confirms:

- `has_stored_faces=true`
- `total_faces=75`

So the media-preview Details screen is using stored continuous-pipeline face detections as input, but the person groups shown there are recomputed on demand by orchestrator from those stored faces. That screen is not reading VMeta `search/by-videos` results and it is not using persisted per-video MVR search/count rows as its primary source.

### Finding 5: Missing gender and age in the single-video Persons tab is partly a schema problem, not just a rendering problem

The orchestrator response model for `GET /person-objects/{media_id}` returns per-person-group data such as:

- representative faces
- route points
- movement statistics
- quality metrics

It does **not** define top-level per-person-group fields for:

- `gender`
- `gender_confidence`
- `age_min`
- `age_max`
- `age_mean`

This means the single-video Persons tab cannot show full demographics from the orchestrator contract alone, even when the underlying stored face detections exist.

However, representative faces do preserve nested face data from Enhanced Logic V2, and those nested payloads can include age estimates. So the UI can recover some age information directly from stored person-object data even though the orchestrator person-group schema does not expose a normalized demographics object.

### Follow-up change applied in the frontend

The single-video `PersonObjectsDetailScreen` has now been updated so that:

1. it preserves raw orchestrator `person_groups` instead of discarding them during client transformation
2. it derives per-person age ranges from stored representative-face `age_detection` data when available
3. it shows a persisted-VMeta demographics banner for the current video by calling the existing `search/by-videos` path separately

Important limitation:

- this improves visibility, especially for age
- it does **not** invent a false per-person gender mapping between orchestrator person groups and VMeta MVR roots where no stable join exists

So after this change, the single-video Persons tab can surface more truthful stored data without pretending that orchestrator person groups and persisted MVR roots are the same object model.

### Finding 6: Person-group UUID stability depended on whether the running Orchestrator served the persisted retrieval path

This is now both code-verified and live-validated.

#### The root cause that originally produced unstable UUIDs

The instability investigation was correct about the old failure mode.

When `GET /person-objects/{media_id}` is served by the legacy regroup-on-read path, it:

1. creates a fresh request-scoped grouping result
2. reruns Enhanced Logic V2 / rectangle-overlap grouping
3. mints new `person_uuid = str(uuid.uuid4())` values during response construction

In that mode, `person_uuid` is not a durable persisted identity key and cannot be used as a reliable join key across requests.

#### Current code path on disk

The retrieval endpoint in:

- `ppl-meta-orchestrator/src/ppl_thread_endpoints.py`

now prefers persisted Vision data:

1. resolve `media_uuid -> session_uuid`
2. fetch stored session details from Vision
3. map stored `person_objects` into Orchestrator `person_groups`
4. return stored `person_id` / `person_uuid` values
5. only fall back to live regrouping when no persisted session exists

So the intended current behavior is durable UUID reuse for materialized media, with regrouping only as a fallback.

#### Live validation after service restart

This behavior was validated live after restarting the services, which mattered because an earlier stale Orchestrator process was still serving the legacy regroup-on-read path.

Validated example 1:

- media: `87eff63e-9a5a-4c5e-b1e8-0f033cff5658`
- persisted session: `83fcd465-f7f7-4981-bda1-f7c75f3b4c12`

Two successive calls to `GET /api/v1/orchestrator/person-objects/{media_id}` returned:

- `message = "Retrieved 2 persisted person groups"`
- the same `session_uuid`
- the same `person_uuid` set:
  - `5add3664-97d5-40d9-865e-1def413e7fdf`
  - `a5117d6b-e832-48c5-b87d-b7b345b25386`

Validated example 2:

- media: `38f80c41-e0af-41fc-882d-f7ff79abd43d`
- persisted session: `8452a84d-b577-4e06-a8f8-4f554aad96ea`

Two successive calls returned persisted groups for the same session and should reuse the same `person_uuid` set across reads.

#### Important operational caveat

The earlier contradictory result was real, but it came from a stale running service, not from the current code on disk.

Before the restart, the same media lookup produced:

- regroup-on-read message text
- blank `session_uuid`
- regenerated UUIDs across successive reads

After restart, the persisted retrieval path was served and the UUIDs stabilized.

So the correct current conclusion is:

```text
The durable UUID design is now implemented for persisted media.
If unstable UUIDs reappear, first verify that the running Orchestrator instance is actually serving the persisted retrieval code path.
```

#### Practical implementation checkpoint

Before relying on `person_uuid` as a durable join key for a given environment, verify that:

1. `GET /person-objects/{media_id}` returns a persisted-session message, not a regroup-on-read message
2. the response includes the expected stored `session_uuid`
3. repeated GETs for the same materialized media return the same `person_uuid` set
4. fallback/live regrouping is only occurring for media that truly have no persisted session or no resolvable stored media context

---

## Why This Produces False Attendance / Demographics

Once multiple people are collapsed into a contaminated root MVR:

1. The analytics endpoint sees only the surviving active root row
2. The root row contributes one stored `gender` value
3. All child/orphaned MVRs are excluded by `mp.is_orphaned = false`
4. All underlying linked individuals with female or unknown labels are effectively hidden from the summary

If a contaminated root has `gender='male'`, the dashboard can show an all-male result even when the underlying linked individuals do not support that conclusion.

---

## Reinforcing Risk: Gender Propagation

The route:

- `ppl-meta-vmeta/src/api/routes/mvr_people.py`

contains `update_mvr_person_gender(...)`, which can propagate a chosen gender through a merge hierarchy.

That means a gender applied to one contaminated MVR root can also be copied to:

1. The root itself
2. Related super-individuals
3. Constituent merged MVRs

This increases the risk that the MVR layer drifts even further away from raw individual-level truth.

---

## What This Is Not

This is **not** evidence of a guard that forcibly converts people to male.

The current merge safeguards in:

- `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py`
- `ppl-meta-vmeta/src/services/mvr_service.py`

are blocking conditions:

- `_can_auto_merge_by_gender(...)` blocks some conflicting confident merges
- `_is_contamination_suspect(...)` blocks suspicious high-similarity merges

These guards do not assign `male`; they only allow or block merge decisions.

---

## Root Cause Summary

The immediate cause of the bad attendance/demographics summary is:

```text
Analytics reads persisted active MVR root genders
instead of raw individual/person-object demographics
```

The upstream enabling cause is:

```text
Contaminated MVR hierarchy has already collapsed multiple people
into two active male-labeled roots
```

---

## Recommended Fix Directions

### Fix Direction 1: Change analytics aggregation source

For dashboard demographics and attendance summaries, aggregate from one of:

1. `individuals.gender_estimate` across distinct linked individuals for the selected videos
2. raw person objects / orchestrator demographic truth when available

Do not treat `mvr_people.gender` on active roots as authoritative when hierarchy contamination is possible.

### Fix Direction 2: Provide source transparency in API responses

Return metadata such as:

- `demographics_source: mvr_roots | linked_individuals | person_objects`
- `active_root_count`
- `linked_individual_count`
- `orphaned_child_count`

This makes contamination visible instead of silently collapsing it.

Additional note:

The API should expose the effective demographics source used for each displayed gender/age value, so the UI can tell whether a rendered value came from:

- linked `individuals.gender_estimate` / `individuals.age_estimate`
- a root `mvr_people` row
- person-object level evidence

Without that response metadata, the UI cannot distinguish between upstream single-video evidence and a root-level value that may already be contaminated by merge history.

### Fix Direction 3: Tighten manual MVR creation and expose merge decisions

The explicit session-level MVR creation path can still collapse different same-day individuals when it relies too heavily on embedding similarity alone.

The next fixes should be:

1. tighten the manual merge guard so same-day individuals do not merge unless they also satisfy stronger demographic and appearance-consistency checks
2. expose the effective merge-guard decision in API responses or debug logs so each candidate pair can be explained as merged or blocked, with the reason visible

### Fix Direction 4: Preserve raw session visibility and keep session counts truthful

The session analysis flow should continue to expose the underlying tracked individuals even after explicit MVR creation has been run, and the session summary counters should reflect persisted session-linked mappings rather than in-memory estimates.

The next fixes should be:

1. keep a raw session-individual view available even when MVRs exist, so the original per-session individuals remain inspectable without being hidden behind the merged MVR layer
2. derive `unique_mvr_people_count` from actual `session_individuals -> individual_mvr_mapping` rows so the stored session summary always matches persisted reality

---

## Current Conclusion

This issue is verified.

For USB Camera 04, the analytics path is reading two active male root MVRs while the underlying linked individuals for the same investigated videos are entirely unknown-gender at the raw stored level. The male-only summary therefore comes from the contaminated active MVR hierarchy, not from the underlying linked individual layer.

---

## Additional Verified Failure Mode: Continuous Pipeline Truth Exists, But VMeta Video Search Returns Zero

This is a separate but related architecture failure.

It was verified against a fresh three-video recording session where:

- instant face detection succeeded
- route points were present
- persisted person objects with stable UUIDs were present through Orchestrator / Vision
- `MVR search by videos` returned zero person objects / zero MVR people

### Concrete media IDs

- `8529cf30-6373-466c-8987-feeab04d1e39`
- `d64b2ce9-d432-499b-861d-fc7dd002071d`
- `1d059949-dc4c-4bc1-8f57-5a8a77a459b1`

### Verified upstream truth for these three videos

Direct Orchestrator calls returned persisted person groups:

- `8529cf30-6373-466c-8987-feeab04d1e39` → `total_persons = 1`, `total_faces = 9`
- `d64b2ce9-d432-499b-861d-fc7dd002071d` → `total_persons = 2`, `total_faces = 76`
- `1d059949-dc4c-4bc1-8f57-5a8a77a459b1` → `total_persons = 2`, `total_faces = 76`

This proves the continuous pipeline had already produced:

1. stored face detections
2. stored person objects
3. stable persisted `person_id` / `person_uuid`
4. stored route-point histories

### Verified VMeta search failure for the same videos

Running:

```http
POST /api/v1/mvr-people/search/by-videos
```

with those same three `video_uuids` returned:

```json
{
  "success": true,
  "total_results": 0,
  "mvr_people": [],
  "message": "No individuals found in videos"
}
```

### Database verification of the exact gap

For those same three video UUIDs, VMeta had:

- no `individual_video_appearances` rows
- no `mvr_people.source_media_uuid` rows

So the failure is not:

- missing face detections
- missing route points
- missing persisted person objects
- unstable person UUIDs

The failure is specifically that VMeta search has no local materialized rows for those videos, even though the upstream persisted person-object layer is already correct.

---

## Root Cause: VMeta Still Depends On Legacy Local Materialization Instead Of The Persisted Person-Object Layer

The continuous pipeline currently produces the correct persisted truth in Vision / Orchestrator:

```text
faces -> persisted person_objects -> stable person_id -> route_points
```

But VMeta `search/by-videos` still assumes this older local persistence chain already exists:

```text
individual_video_appearances
-> individuals
-> individual_mvr_mapping
-> mvr_people
```

The search handler in:

- `ppl-meta-vmeta/src/api/routes/mvr_people.py`

does this first:

1. query `individual_video_appearances` by `video_uuid`
2. derive `individual_uuid`
3. derive `mvr_people` through `individual_mvr_mapping`
4. return zero when no local appearance rows exist

So the architectural mismatch is:

```text
The continuous pipeline writes correct persisted person-object truth,
but VMeta video search does not treat that persisted layer as its canonical input.
It still treats its own local appearance/mapping tables as the gatekeeper.
```

### Why this matters

This means a video can simultaneously have:

1. valid persisted face detections
2. valid persisted person objects
3. valid persisted route points
4. stable persistent person UUIDs
5. zero results from `search/by-videos`

That is not a detection failure.
That is a VMeta integration failure.

### Practical interpretation

The continuous pipeline is already respecting the new structure.
The VMeta video-search/count layer is not.

So the correct system-level statement is:

```text
The root problem is not that the continuous pipeline fails to create person objects.
The root problem is that VMeta search/count endpoints are still coupled to legacy
materialized local rows instead of using the persisted person-object structure
as the primary source of truth for single-video MVR discovery.
```

---

## Implementation Implication

This investigation supports a stronger conclusion than a narrow bugfix.

The right long-term direction is not to keep layering read-time fallbacks.
The right direction is to align VMeta with the new persisted architecture:

1. treat persisted Vision / Orchestrator person objects as the canonical single-video source
2. make VMeta materialization explicit and durable from that source
3. stop requiring `individual_video_appearances` to pre-exist before video search can discover people

Until that alignment is completed, VMeta can continue to return zero MVR results for videos whose continuous-pipeline person objects already exist and are correct.

### Verified Missing Integration Point

The current gap is now narrowed further.

What is automatically triggered today:

- after face detection, the frontend auto-triggers person-object workflow creation through Orchestrator-facing flows
- this happens in `ppl-meta-frontend/lib/providers/person_objects_provider.dart`
- and in `ppl-meta-frontend/lib/services/person_objects_api_client.dart`

What is not part of that same automatic path:

- VMeta single-media materialization through `POST /api/v1/mvr-people/process-media`
- this explicit VMeta call is implemented in `ppl-meta-frontend/lib/services/vision_processing_service.dart`

So the platform currently has two separate flows:

1. continuous pipeline flow that produces persisted Vision / Orchestrator person objects
2. separate VMeta materialization flow that creates `individual_video_appearances`, `individual_mvr_mapping`, and isolated `mvr_people`

There is also an existing VMeta background hook for automatic MVR creation, but it only runs after VMeta itself creates an `individual` row. That hook lives in:

- `ppl-meta-vmeta/src/database/repository.py`
- `ppl-meta-vmeta/src/background/mvr_helper.py`
- `ppl-meta-vmeta/src/background/mvr_background_processor.py`

That means it cannot solve the fresh-video zero-result case by itself, because for those videos the continuous pipeline never entered the VMeta `individual` creation path in the first place.

So the more precise root-cause statement is:

```text
persisted person objects are created upstream,
but no automatic backend-owned bridge materializes them into the VMeta local search tables.
```

That is the architecture gap between the new continuous pipeline structure and the old VMeta search assumptions.
