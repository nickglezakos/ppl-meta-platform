# Vehicle + Plate Trigger — Acceptance Checklist

**Mode:** `vehicle_plate`  
**Docs:** [vehicle-plate-trigger.md](./vehicle-plate-trigger.md)

## Prerequisites

- [ ] Media migration applied: `cd ppl-meta-media && alembic upgrade head` (includes `add_vehicle_plate_trigger_fields`)
- [ ] Instant detection ON for target camera(s)
- [ ] Camera `processing_options.auto_vehicle_detection` = true
- [ ] COCO YOLO ONNX available (`body-yolo-person-os` / `vehicle-yolo-coco-os` alias)
- [ ] (Optional V2) EasyOCR installed in Vision for plate text; otherwise plate fields stay null

## V1 — Vehicle STABLE fire

- [ ] Create trigger mode **Vehicle + Plate** with allow-list including `car`
- [ ] Park/hold a car in ROI ≥ `T_stable` (default 15s)
- [ ] Exactly one fire per track; `last_match_info.class_label=car`
- [ ] `plate_text` may be null
- [ ] Face / body instant path still works when vehicle stage is OFF or busy (isolated breaker)

## V2 — Plate metadata

- [ ] Readable plate in view → `plate_text` / `plate_confidence` on fire payload
- [ ] Unreadable plate still fires vehicle event with null plate
- [ ] OCR every N cycles respects latency budget (no face breaker open)
- [ ] Rows may appear in Vision `plate_readings` (never `mvr_people`)

## Classes

- [ ] Motorcycle / bicycle / truck / bus behave the same when in allow-list

## Metrics

Process-local counters on Media worker: `vehicle_tracks`, `vehicle_fired`, `vehicle_cleared`, `plate_ocr_ok`, `plate_ocr_fail`

## Plate OCR note

Set `PLATE_OCR_ENGINE=easyocr` on Vision to enable EasyOCR. Default is heuristic ROI only (null `plate_text`) so Vision stays stable without the OCR stack.
