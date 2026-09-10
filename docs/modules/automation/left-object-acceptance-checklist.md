# Left Object Trigger — Acceptance Checklist

**Module:** [left-object-trigger.md](../modules/automation/left-object-trigger.md)  
**Date:** 2026-09-10

## Licence / gating

- [ ] Logic licence allows another trigger (Lite: 1, Business: 5, Enterprise: unlimited).
- [ ] Camera has object stage enabled: `processing_options.auto_object_detection` (or `enable_object_detection`) = true.
- [ ] V2 only: `auto_body_detection` = true on the same camera.
- [ ] Instant / Vradar detection ON for the camera.
- [ ] COCO detect weights available (reuse `body-yolo-person-os` / yolov8n.onnx). Model resolve for `capability=object_detection` may fall back to that artifact.

## V1 — Stable in ROI

1. Create Logic trigger mode **Left / Stationary Object**.
2. Select camera(s), allow-list `backpack`, `T_stable=60`, `require_person_left=false`, link an alert action, cooldown ≥ 60.
3. Place a backpack in the ROI and leave it motionless ≥ 60 s.
4. Expect **one** action fire; trigger `last_match_info` contains `class_label`, `bbox`, `state=STABLE`, `dwell_seconds`.
5. Object remains → no re-fire until cooldown expires **and** track is CLEARED then re-established (or new track after object leaves and returns).
6. Remove object for several instant cycles → track CLEARED (`left_object_cleared` metric).

## V2 — Person left

1. Same setup with `require_person_left=true`, `T_abandon=30`, body detection ON.
2. Person stands next to bag while it is stable → no fire (ATTENDED).
3. Person walks away ≥ `T_abandon` → one fire with `state=ABANDONED`.
4. With body detection OFF and require_person_left ON → never fires (fail closed).

## Isolation

- [ ] Face demographic / posture / velocity triggers still evaluate when object stage is OFF or object circuit open.
- [ ] Object Vision failures do not open the face Vision circuit breaker (`VisionObject` is separate).

## Metrics (Media logs)

Look for: `left_object_tracks`, `left_object_fired`, `left_object_cleared` in worker log lines after soak.

## Unit tests

```bash
cd ppl-meta-media && python -m pytest tests/test_left_object_worker.py -q
```
