# AI Vision Pipeline

Documentation for the PPL Meta platform's computer-vision pipeline: frame-based face detection, single-video person grouping, cross-video individuals, MVR (Machine Vision Representation) objects, and analytics reporting.

**Start here:** [Frame to Analytics Pipeline](frame-to-analytics-pipeline.md)

**Last updated:** September 2026  
**Status:** Production documentation

---

## Glossary

| Term | Definition |
|------|------------|
| **Face detection / face record** | A single face found in one video frame. Stored in Vision (`face_detections`, optional `face_crops`) with bounding box, confidence, frame number, and session linkage. |
| **Face detection session** | A processing run for one media item. Groups all frame-level detections under a `session_uuid`. |
| **Person object** | A single-video grouping of face detections belonging to one person. Identified by `person_object_uuid`. Produced by Vision (3-tier cascade) or Orchestrator (IoU overlap). |
| **Individual** | A cross-video identity linking one or more person objects across videos via `individual_video_appearances`. Owned by VMeta. |
| **MVR / MVR people** | Machine Vision Representation — the canonical biometric record for a person (Facenet512 embedding, age/gender, quality scores). Stored in `mvr_people`. Typically 1:1 with an individual at creation time. |
| **Tracking session** | VMeta time-bounded container for a batch of detections/materializations (recording or instant-detection). |
| **Isolated row** | Per-video VMeta materialization derived from persisted person objects before cross-video linking completes. |
| **Super-individual** | Root MVR after hierarchical merge; losers point to it via `merged_into_mvr_uuid`. |
| **Detection model / model version** | Versioned inference artifact (Haar, Dlib, ONNX, …) plus runtime adapter. Assigned per scope and path. Accepted design: [detection-model-lifecycle.md](detection-model-lifecycle.md). Implementation: [ppl-meta-models implementation plan](../../proposals/mv-models/ppl-meta-models-implementation-plan.md). |
| **Capability** | Task type in the model registry (`face_detection`, `body_detection`, `license_plate`, …). Not the same as VMeta identity models (Facenet512, age, gender). |
| **Path (model assignment)** | Which pipeline consumes the model: `instant`, `bulk`, or `preview` (Media overlay). |

---

## Documentation map

### End-to-end guide

| Document | Description |
|----------|-------------|
| [frame-to-analytics-pipeline.md](frame-to-analytics-pipeline.md) | Master guide: detection models → person objects → individuals → MVR → analytics |
| [detection-model-lifecycle.md](detection-model-lifecycle.md) | **Accepted design:** upload / activate / deactivate / archive / delete for face and other MV models (instant and bulk) |
| [body-mvr-people-body.md](body-mvr-people-body.md) | Body/pose → body person objects → MVR People Body (posture/height; stitch rules) |
| [ppl-meta-models implementation plan](../../proposals/mv-models/ppl-meta-models-implementation-plan.md) | Implementation plan: `ppl-meta-models` (:8013), APIs, schema, frontend tile, Authority keys, Phases A–C |

### Pipeline stage deep dives

| Stage | Document |
|-------|----------|
| Detection model registry (accepted design) | [detection-model-lifecycle.md](detection-model-lifecycle.md) |
| Face detection & person objects (single video) | [person objects/Person Objects module.md](person%20objects/Person%20Objects%20module.md) |
| Body detection & MVR People Body | [body-mvr-people-body.md](body-mvr-people-body.md) |
| Real-time / instant detection | [instant-detection/Instant-detection module.md](instant-detection/Instant-detection%20module.md) |
| Instant detection event path | [instant-detection/instant-detection-event-path.md](instant-detection/instant-detection-event-path.md) |
| MVR search & merge UX | [MVR merge/mvr-merge-module.md](MVR%20merge/mvr-merge-module.md) |
| Individual groups (downstream) | [individual-groups/individual-groups.md](individual-groups/individual-groups.md) |

### Known issues & proposals

| Topic | Document |
|-------|----------|
| Embedding contamination (multi-face crops) | [MVR merge/EMBEDDING_CONTAMINATION.md](MVR%20merge/EMBEDDING_CONTAMINATION.md) |
| Gender skew in attendance analytics | [MVR merge/ATTENDANCE_MVR_GENDER_CONTAMINATION_ISSUE.md](MVR%20merge/ATTENDANCE_MVR_GENDER_CONTAMINATION_ISSUE.md) |
| Cross-video statistics tab integrity | [MVR merge/CROSS_VIDEO_STATISTICS_TAB_DATA_INTEGRITY_ISSUE.md](MVR%20merge/CROSS_VIDEO_STATISTICS_TAB_DATA_INTEGRITY_ISSUE.md) |
| Single-video demographics at merge time | [MVR merge/SINGLE_VIDEO_PERSON_OBJECT_DEMOGRAPHICS_PROPOSAL.md](MVR%20merge/SINGLE_VIDEO_PERSON_OBJECT_DEMOGRAPHICS_PROPOSAL.md) |
| Persistent MVR search sessions | [MVR merge/MVR_SEARCH_PERSISTENCE_UPGRADE_PROPOSAL.md](MVR%20merge/MVR_SEARCH_PERSISTENCE_UPGRADE_PROPOSAL.md) |
| Merged MVR group assignment | [individual-groups/merged-mvr-group-assignment-fact-finding-2026-05-08.md](individual-groups/merged-mvr-group-assignment-fact-finding-2026-05-08.md) |
| Detection model implementation (`ppl-meta-models`) | [ppl-meta-models implementation plan](../../proposals/mv-models/ppl-meta-models-implementation-plan.md) |

### Related service documentation

| Service | Document |
|---------|----------|
| VMeta API catalog | [ppl-meta-vmeta/docs/vmeta-api-endpoints.md](../../../ppl-meta-vmeta/docs/vmeta-api-endpoints.md) |
| VMeta integration guide | [ppl-meta-vmeta/docs/integration-guide.md](../../../ppl-meta-vmeta/docs/integration-guide.md) |
| Vision service | [ppl-meta-vision/README.md](../../../ppl-meta-vision/README.md) |

---

## Service ownership

| Service | Port (local) | Pipeline responsibilities |
|---------|--------------|---------------------------|
| **ppl-meta-vision** | 8003 | Frame face detection, face sessions, person_objects grouping & persistence, playback cache |
| **ppl-meta-orchestrator** | 8002 | Enhanced Logic V2 coordination, distance enrichment, person_objects trigger, VMeta materialize call, MVR merge settings, people counters |
| **ppl-meta-vmeta** | 8008 | Materialization, cross-video tracking, individuals, MVR CRUD/match/merge/search, embeddings & demographics ML, analytics APIs |
| **ppl-meta-media** | 8000 | Media/collections, optional embedded face detection for streaming, VMeta proxy, trigger webhooks |
| **ppl-meta-cameras** | 8005 | Camera streams, instant detection sampling, recording lifecycle |
| **ppl-meta-models** | 8013 | Detection model catalog, assignments, golden-set validation (planned; see implementation plan) |

---

## Quick pipeline summary

```
Frames → Vision (detect) → Vision (person_objects) → VMeta (materialize)
      → VMeta (cross-video individuals) → VMeta (MVR create/match/merge) → Analytics
```

Orchestrator coordinates the recording path (Enhanced Logic V2). Instant detection uses a parallel path with Orchestrator IoU grouping; see the master guide for the trigger matrix.
