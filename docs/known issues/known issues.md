# Known issues

Living list of product / UI issues to fix later. Each entry includes **date** and platform **VERSION**.

| Field | Value |
|--------|--------|
| Document | `docs/known issues/known issues.md` |
| Platform VERSION | see root [`VERSION`](../../VERSION) |

---

## Open

### KI-002 — Mobile camera Stop stream control was intermittent (fixed in source; verify on device)
- **Date:** 2026-09-23
- **VERSION:** 2.25.83
- **Area:** `ppl_meta_mobile_camera` — `CameraScreen` / `CameraControls`
- **Symptom:** Red Stop control only appeared sometimes; vanished after UI taps (e.g. front/back switch). Center video/record button did not clearly stop the stream.
- **Cause:** Streaming started via `CameraService` / `MobileStreamingService` without `setState` / provider notify, so the Stop overlay often never rebuilt. Stop path also only called `disableFrameSending()` without full teardown.
- **Fix (source, pending APK rebuild):** `_isLiveStreaming` local flag; persistent top-right **Stop stream** chip while live; center button morphs to Stop and calls `_stopAndResetCameraState`; full stop tears down camera + mobile upload.
- **Status:** Open until verified on TrebleDroid / device after APK rebuild.

### KI-001 — Mobile Connect button does not show orange “lease open” state
- **Date:** 2026-09-23
- **VERSION:** 2.25.83
- **Area:** Frontend `/cameras` — mobile camera card Connect control  
  (`ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`,  
  `mobileConnectPhaseProvider` in `camera_providers.dart`)
- **Symptom:** Mobile connect flow works (Connect → start stream on phone → Connect again), but the Connect control never visibly changes to the orange **LEASE OPEN** affordance after the first Connect. Operator gets no clear UI signal that the platform stream lease is open / awaiting the phone.
- **Expected:** After first Connect on a mobile camera: solid orange chip (“LEASE OPEN” / `phonelink_ring`), orange snackbar, and orange leading phone icon until second Connect attaches (then red Disconnect).
- **Tried:** Local optimistic state on the button (lost on `loadCameras()` rebuild); Riverpod `mobileConnectPhaseProvider` + high-visibility orange chip. Issue still observed in lab after those changes.
- **Impact:** UX only — lease / attach process still works; operators must remember the two-step flow without a color cue.
- **Status:** Open — defer; revisit later (confirm hot-reload vs release frontend, phase provider write timing, whether running UI is an older build).

---

## Resolved

_None yet._
