# Body detection → MVR People Body

**Scope:** Parallel pipeline to face → person objects → MVR People for body/pose tracks  
**Status:** Implemented (V1)  
**Last updated:** September 2026

## Overview

When a camera has **Body detection** enabled (`auto_body_detection`), the platform runs YOLO-pose (preferred) or YOLO-person detect, groups detections into **body person objects**, and materializes **MVR People Body** records with posture / relative height metadata.

```text
Frames → YOLO-pose → object_detections (+ keypoints)
       → body_person_objects (within-video IoU tracks)
       → mvr_people_body (posture, height_px; colors/fallen placeholders)
       → cyan replay overlay (bodies_by_frame)
```

Face and body pipelines are independent. Camera Face OFF does not block body; Body OFF does not block face.

## YOLO capabilities and restrictions

| Source | Available | Not available |
|--------|-----------|---------------|
| `body-yolo-person-os` (detect) | bbox, confidence, class person | keypoints, reliable posture |
| `body-yolo-pose-os` (pose) | bbox + COCO-17 keypoints | absolute height in meters; clothing colors |
| V1 post-process | posture upright/horizontal/uncertain; height_px / height_relative | height_m (needs calibration) |
| Placeholders | `estimate_dominant_colors`, `estimate_fallen` | — |

**Partial bodies:** Models do **not** require a full body. Truncated or occluded people still get boxes; low keypoint visibility forces posture `uncertain`. Prefer hips+shoulders visible before trusting upright/horizontal.

**Industrial / ships:** Horizontal posture is a useful operational signal under mostly non-occluded views. It is **not** certified life-safety fall detection. Use the separate `estimate_fallen` placeholder for a future temporal classifier.

## Metadata on MVR People Body (analogous to age/gender)

| Field | V1 |
|-------|----|
| `posture` / `posture_confidence` | From pose geometry (bbox aspect fallback) |
| `height_px` / `height_relative` | Head–ankle or bbox height |
| `height_m` | Always null until calibration |
| `dominant_colors` | **Placeholder** — not computed; see commented stubs in `onnx_yolo.estimate_dominant_colors` / VMeta service |
| `fallen` / `fallen_confidence` | Always `unknown`; stub `estimate_fallen` |

## Cross-segment identity (verified stitch only)

`POST /api/v1/body-person-objects/stitch-segments` and `POST /api/v1/mvr-people-body/stitch` continue a track across a **cut** only when:

1. Same `camera_id`
2. Continuous time (`|t_start_B - t_end_A| <= delta`)
3. Small motion (IoU / center distance between last boxes of A and first of B)

This is **track continuation across a cut**, not same-person matching across unrelated videos (no ReID).

## Key APIs

| Service | Endpoint |
|---------|----------|
| Vision | `POST /api/v1/object-detections/detect` (pose + persist + frame provenance) |
| Vision | `GET /api/v1/object-detections/by-frame` → `bodies_by_frame` |
| Vision | `POST /api/v1/object-detections/process-media` (bulk/recording/Compute) |
| Vision | `POST /api/v1/body-person-objects/group-from-detections` |
| Vision | `POST /api/v1/body-person-objects/stitch-segments` |
| VMeta | `POST /api/v1/mvr-people-body/materialize/persisted-body-person-objects` |
| VMeta | `GET /api/v1/mvr-people-body/media/{media_id}` |

## Triggers

- **Instant (face-aligned):** detect + group in memory on every burst when `auto_body_detection` ON; results cached on the cycle; Redis batch flush (same queue as faces: 10 cycles / 30s) materializes `mvr_people_body` via VMeta `instant-detection/persist-batch`. No per-cycle Vision `object_detections` / `body_person_objects` writes.
- Recording / continuous upload: `process-media` when body ON (persists Vision detections for replay overlays)
- Preview **Compute**: also calls `process-media` (explicit recalculate)

## Frontend

- Cyan body rectangles on video replay (`simple_video_face_detection_overlay.dart`)
- `MvrPeopleBodyDetailPanel` lists posture / height / placeholders
- Camera settings Body subtitle describes real pose → MVR People Body behavior

## Seed pose weights

```bash
# Optional: place yolov8n-pose.onnx under ppl-meta-models/seed_weights/
python ppl-meta-models/scripts/seed_yolo_onnx.py
```

If pose weights are missing, detect-only still runs with weaker posture (bbox aspect).

## Related docs

- [Frame to analytics pipeline](../frame-to-analytics-pipeline.md)
- [Detection model lifecycle](../detection-model-lifecycle.md)
- [Person Objects (faces)](../person%20objects/Person%20Objects%20module.md)
