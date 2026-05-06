# VMeta Person-Object Materialization Implementation Spec

**Status:** Implemented initial bridge  
**Date:** 2026-05-06

## Purpose

Define the exact backend-owned bridge from persisted Vision/Orchestrator person objects into VMeta's single-media materialization tables.

This spec intentionally leaves `search/by-videos` read-oriented. Search does not become responsible for discovering or creating missing local rows.

## Chosen Boundary

The chosen event boundary is inside Orchestrator's face-detection pipeline after Vision has already persisted person objects and returned the persisted payload.

Implemented hook point:

- `ppl-meta-orchestrator/src/face_detection_endpoints.py`

Specifically, the bridge runs immediately after:

1. `_trigger_person_objects_workflow(...)` succeeds
2. `_complete_vision_session(...)` runs
3. before person objects are enqueued for later cross-video batching

## Why This Boundary

This is the strongest producer boundary because it already has all of the following at once:

- `media_id`
- `session_uuid`
- persisted `person_objects`
- user or service auth context
- certainty that Vision completed the write path

This is better than wiring the bridge in `workflow_orchestrator.py` because that path only knows that the person-object workflow was started. It does not reliably hold the persisted `person_objects` payload.

## Producer

Producer service:

- Orchestrator

Producer implementation:

- `ppl-meta-orchestrator/src/face_detection_endpoints.py`

Producer method:

- `_materialize_vmeta_from_persisted_person_objects(...)`

Producer trigger condition:

- Vision person-object workflow succeeded for a media item
- persisted `person_objects` were returned

## Consumer

Consumer service:

- VMeta

Consumer implementation:

- `ppl-meta-vmeta/src/api/routes/mvr_people.py`

Consumer endpoint:

- `POST /api/v1/mvr-people/materialize/persisted-person-objects`

Consumer auth:

- accepts either a normal user JWT
- or the shared internal service token via `X-Service-Name`

Consumer auth dependency:

- `ppl-meta-vmeta/src/api/dependencies.py`
- `get_current_user_or_internal_service(...)`

## Request Contract

### Endpoint

```text
POST /api/v1/mvr-people/materialize/persisted-person-objects
```

### Request body

```json
{
  "media_uuid": "<uuid>",
  "session_uuid": "<uuid-or-null>",
  "media_type": "video",
  "person_objects": [
    {
      "person_id": "<persisted-vision-person-id>",
      "person_uuid": "<same-or-compatible-id>",
      "face_count": 3,
      "representative_faces": [],
      "quality_score": 21.09,
      "average_confidence": 0.93,
      "spatial_bounds": {},
      "temporal_span": {},
      "movement_tracking": {}
    }
  ],
  "processing_options": {
    "similarity_threshold": 0.7,
    "min_face_quality": 0.2,
    "include_demographics": true,
    "include_route_data": true,
    "async_processing": false
  }
}
```

### Required fields

- `media_uuid`
- `person_objects`

### Optional fields

- `session_uuid`
- `media_type`
- `processing_options`

## Response Contract

```json
{
  "success": true,
  "media_uuid": "<uuid>",
  "session_uuid": "<uuid-or-null>",
  "status": "completed",
  "media_type": "video",
  "existing_mvr_people_count": 0,
  "mvr_people_count": 2,
  "total_faces_detected": 2,
  "processing_time_ms": 184
}
```

Possible `status` values:

- `completed`
- `skipped_existing`
- `failed`

## Idempotency Rule

The consumer is idempotent at the media level.

Before materialization, VMeta checks whether isolated rows already exist:

```text
mvr_people.source_media_uuid = media_uuid
AND is_isolated = TRUE
AND is_orphaned = FALSE
```

If rows already exist, the consumer returns `status = skipped_existing` and does not create duplicate isolated MVR rows.

## Data Mapping Rules

### Identity

For each incoming person object:

```text
person_object_uuid := person_id || person_uuid || person_object_uuid
```

Priority order:

1. `person_id`
2. `person_uuid`
3. `person_object_uuid`

No synthetic UUIDs are created in this bridge.

### Media metadata

VMeta resolves media metadata itself through `MediaClient` using the forwarded auth token.

Used fields:

- media type
- media timestamp

### Face enrichment

VMeta reuses the existing crop-enrichment path:

- `enrich_person_objects_with_face_crops(...)`

This keeps the bridge aligned with the current ML pipeline rather than inventing a second face-crop workflow.

### Materialization writer

VMeta reuses:

- `MVRService.process_single_media_for_mvr(...)`

This creates:

1. `individuals`
2. `individual_video_appearances`
3. `individual_mvr_mapping`
4. isolated `mvr_people`

## Resulting Invariants

After successful materialization for a video:

1. `mvr_people` contains isolated rows with `source_media_uuid = media_uuid`
2. `individual_video_appearances` exists for the materialized individuals
3. `individual_video_appearances.person_object_uuid` points to the persisted Vision identity
4. `individual_mvr_mapping` links the new individuals to isolated MVR rows
5. `search/by-videos` can remain read-only and still discover the video through normal VMeta tables

## Initial Implementation Files

- `ppl-meta-orchestrator/src/face_detection_endpoints.py`
- `ppl-meta-vmeta/src/api/dependencies.py`
- `ppl-meta-vmeta/src/api/models/process_media.py`
- `ppl-meta-vmeta/src/api/routes/mvr_people.py`

## Follow-Up Work

1. Move the Orchestrator-to-VMeta HTTP call into a dedicated service client instead of a local helper in `face_detection_endpoints.py`.
2. Add metrics and retry/backoff for the materialization bridge.
3. Add an integration test that proves a fresh video with persisted person objects gains VMeta `individual_video_appearances` and isolated `mvr_people` rows without invoking `search/by-videos` writes.
