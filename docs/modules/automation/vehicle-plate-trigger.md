# Vehicle + Plate Trigger

**Status:** Implemented (V1 vehicles + V2 plate metadata)  
**Trigger mode:** `vehicle_plate`  
**Last updated:** September 2026

## Product contract

Detect cars and bikes in a camera ROI; fire Logic actions when a track is stable. Attach license-plate text as metadata when OCR succeeds (never MVR people).

| Version | Behaviour |
|---------|-----------|
| **V1** | Track COCO vehicle classes; fire once per track after `T_stable` in ROI |
| **V2** | On vehicle crops, run plate localization + OCR every N cycles; attach `plate_text` |

## YOLO compatibility

- **Vehicles:** YOLOv8n COCO ONNX (`body-yolo-person-os` / `vehicle-yolo-coco-os`) with class ids bicycle=1, car=2, motorcycle=3, bus=5, truck=7.
- **Plates:** Not in COCO — plate crop heuristics / optional plate detector + OCR (EasyOCR when installed; otherwise null plate metadata).

## State machine

```text
NEW → STABLE (low motion for T_stable) → FIRE once → ACKNOWLEDGED → CLEARED
```

## Config fields

| Field | Default |
|-------|---------|
| `vehicle_class_allowlist` | car, motorcycle, bicycle, truck, bus |
| `vehicle_roi` | full frame |
| `vehicle_t_stable_seconds` | 15 |
| `vehicle_min_box_area_px` | 800 |
| `vehicle_plate_ocr_enabled` | true |
| `vehicle_plate_ocr_every_n_cycles` | 2 |
| `vehicle_iou_threshold` | 0.3 |

## Camera prerequisites

- Instant detection ON
- `processing_options.auto_vehicle_detection` = true
- YOLO COCO weights available (same as body-person ONNX)

## Fire payload

```json
{
  "source_camera_id": "usb_camera_0",
  "track_id": "…",
  "class_label": "car",
  "bbox": [x1,y1,x2,y2],
  "dwell_seconds": 18.2,
  "plate_text": "ABC1234",
  "plate_confidence": 0.81,
  "state": "STABLE"
}
```

## Metrics

`vehicle_tracks`, `vehicle_fired`, `vehicle_cleared`, `plate_ocr_ok`, `plate_ocr_fail`

Plate OCR is opt-in on Vision via `PLATE_OCR_ENGINE=easyocr` (default: heuristic ROI only, null plate text).
