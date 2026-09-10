# Left / Stationary Object Trigger

**Status:** Implemented (V1 + V2)  
**Trigger mode:** `left_object`  
**Last updated:** September 2026

## Product contract

Pinpoint a small COCO object (backpack, handbag, suitcase, bottle, …) that stays stable in a camera ROI. Optionally require that a person was near it and then left (abandoned luggage semantics).

| Version | Fire condition |
|---------|----------------|
| **V1** | Track of an allow-listed class is **STABLE** in ROI for `T_stable` seconds |
| **V2** | Same, but only after **ATTENDED** then **ABANDONED** (`require_person_left=true`) |

Out of scope: custom-trained classes, multi-camera object identity, background subtraction, life-safety claims.

## State machine (per track)

```text
NEW → STABLE (centroid motion / IoU hold for T_stable)
    → ATTENDED (V2: body in proximity)
    → ABANDONED (V2: no body for T_abandon) → FIRE once
    → CLEARED (object gone) / ACKNOWLEDGED (cooldown / already fired)
```

- **V1** (`require_person_left=false`): FIRE when entering STABLE (once per track, then ACKNOWLEDGED until CLEARED).
- **V2** (`require_person_left=true`): FIRE only on ABANDONED. Fail closed if body boxes are unavailable.

## Architecture

```text
Camera → Vradar instant cycle → Vision object_detection (COCO YOLO)
       → Redis instant-detection { objects, body_persons }
       → Media left_object_worker (IoU tracks)
       → action_uuids + last_match_info (bbox pin payload)
```

Reuses: instant pub/sub, `object_detections` capability (never face/MVR people), action pipeline, body boxes for V2 proximity.

## Configuration fields

| Field | Default | Meaning |
|-------|---------|---------|
| `left_object_class_allowlist` | `["backpack","handbag","suitcase","bottle"]` | JSON class labels |
| `left_object_roi` | full frame | Normalized polygon `[[x,y],…]` in 0–1 |
| `left_object_t_stable_seconds` | 60 | Seconds of low motion before STABLE |
| `left_object_t_abandon_seconds` | 30 | Seconds without nearby body (V2) |
| `left_object_min_box_area_px` | 400 | Reject tiny noisy boxes |
| `left_object_require_person_left` | false | Enable V2 abandon semantics |
| `left_object_proximity_px` | 120 | Body–object center distance (V2) |
| `left_object_iou_threshold` | 0.3 | Track continuation IoU |
| `camera_device_ids` | required | Cameras to monitor |
| `cooldown_seconds` | 60 | Min time between firings |

## Fire payload (`last_match_info`)

```json
{
  "source_camera_id": "usb_camera_0",
  "track_id": "…",
  "class_label": "backpack",
  "bbox": [x1, y1, x2, y2],
  "dwell_seconds": 72.5,
  "state": "STABLE",
  "zone_id": "roi",
  "confidence": 0.81,
  "crop_media_id": null
}
```

## Camera prerequisites

- Instant detection ON for the camera.
- Object stage ON: set `processing_options.auto_object_detection` (or `enable_object_detection`) true so the instant cycle runs COCO YOLO.
- V2: also enable `auto_body_detection` so body boxes are published on the same cycle.

## Metrics (logs)

Counters emitted by the worker: `left_object_tracks`, `left_object_fired`, `left_object_cleared`.

## Acceptance

**V1:** ROI + allow-list backpack + `T_stable=60` → one alert, overlay pin payload, no re-fire until cooldown or CLEARED. Face pipeline unaffected when object stage skipped.

**V2:** `require_person_left=true` → no fire while person nearby; fire once after leave for `T_abandon`.
