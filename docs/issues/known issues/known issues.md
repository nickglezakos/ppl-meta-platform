# Known issues

Living list of product / UI issues to fix later. Each entry includes **date** and platform **VERSION**.

| Field | Value |
|--------|--------|
| Document | `docs/issues/known issues/known issues.md` |
| Platform VERSION | see root [`VERSION`](../../../VERSION) |

---

## Open

### KI-004 — vmeta stall blocks analytics / video-preview; residual Tailscale UI lag
- **Date:** 2026-10-21
- **VERSION:** 2.25.103
- **Area:** `ppl-meta-vmeta` (materialization / health), gateway analytics fan-out, frontend analytics screen  
  Lab: `eyenet-demo` (`lab-work-dual-64g`)
- **Symptom:** Analytics and video-preview details fail with gateway **503** after ~60 s when vmeta is wedged (alive, high mem, `/health` hangs). After restart, APIs are fast but analytics page still feels slow over Tailscale because the UI loads endpoints sequentially with multi-second gaps.
- **Expected:** vmeta stays responsive under live cameras + preview traffic; analytics/preview fail fast or recover without manual restart; analytics first paint usable remotely in a few seconds.
- **Mitigation (lab):** `docker restart pplmeta-ppl-meta-vmeta-1` (confirm new `StartedAt`; compose restart may no-op).
- **Plan:** [2026-10-21-vmeta-stall-analytics-preview-lag.md](./2026-10-21-vmeta-stall-analytics-preview-lag.md) — Phase 0 runbook → Phase 1 disable watchfiles reload → Phase 2 harden vmeta → Phase 3 parallelize analytics → Phase 4 monitoring.
- **Impact:** Demo-blocking when wedged; residual UX lag after recovery.
- **Status:** Open — mitigated by restart; durable fixes not shipped.

### KI-003 — Authority `/admin` has no release-channel / pilot-tagging UI
- **Date:** 2026-10-04
- **VERSION:** 2.25.94
- **Area:** Authority laconic admin (`autonomous/ppl-meta-authority` `/admin`) — licence / release eligibility  
  Related policy text (archived, not published):  
  `docs/documentation/archived-wiki/distributors/release-channels.md`
- **Symptom:** Distributors and operators cannot tag a licence or entitlement as `sandbox` / `pilot` / `stable`, or promote a release through pilot soak, from the rebuilt `/admin` shell (Home · People · Licences · Me). Those steps remain control-plane / policy / runbook work outside the UI.
- **Expected:** In-product controls (or a clear operator path linked from Licences) to set channel eligibility and record soak / stable-promotion audit, matching installation lifecycle CI/CD policy.
- **Wiki:** The distributor wiki page **Release channels and pilot tagging** was **archived** (removed from the published site) so partners are not sent to a page that invents click-paths for missing UI. Re-publish under `docs/documentation/wiki/distributors/` when the product ships the controls.
- **Impact:** Channel rollout and pilot soak stay manual / out-of-band; risk of operators assuming People or Licences can change channels.
- **Status:** Open — product gap; wiki archived until UI exists.

### KI-001 — Mobile Connect button does not show orange “lease open” state
- **Date:** 2026-09-23
- **VERSION:** 2.25.83
- **Area:** Frontend `/cameras` — mobile camera card Connect control  
  (`ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`,  
  `mobileConnectPhaseProvider` in `camera_providers.dart`)
- **Symptom:** Mobile connect flow works (Connect → start stream on phone → Connect again), but the Connect control never visibly changes to the orange **LEASE OPEN** affordance after the first Connect. Operator gets no clear UI signal that the platform stream lease is open / awaiting the phone.
- **Expected:** After first Connect on a mobile camera: solid orange chip (“LEASE OPEN” / `phonelink_ring`), orange snackbar, and orange leading phone icon until second Connect attaches (then red Disconnect).
- **Tried:** Local optimistic state on the button (lost on `loadCameras()` rebuild); Riverpod `mobileConnectPhaseProvider` + high-visibility orange chip. Issue still observed in lab after those changes (also after Stage 3 frontend `f9e2aacc…` — re-check with hard refresh).
- **Impact:** UX only — lease / attach process still works; operators must remember the two-step flow without a color cue.
- **Status:** Open — defer; revisit later.

---

## Resolved

### KI-002 — Mobile camera Stop stream control was intermittent
- **Date:** 2026-09-23
- **Resolved:** 2026-09-23
- **VERSION:** 2.25.83
- **Area:** `ppl_meta_mobile_camera` — `CameraScreen` / `CameraControls`
- **Fix:** `_isLiveStreaming` flag; persistent top-right **Stop stream**; center button morphs to Stop; full teardown.
- **Verified:** Latest APK rebuilt and installed on device (2026-09-23).
