# PPL Meta Presence Mobile Functional Spec

**Date**: May 30, 2026  
**Status**: Draft  
**Depends On**: [docs/proposals/presence/Eyenet presence.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/presence/Eyenet%20presence.md)

---

## Purpose

This document defines the first functional specification for `ppl-meta-presence-mobile`.

The mobile application should provide a user-facing presence flow that is operationally reliable on standard mobile devices without depending on simultaneous front and back camera capture.

It should explicitly inherit and reuse existing processes and code patterns from [ppl_meta_mobile_camera](/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera) wherever those already solve the problem.

The app should therefore use a sequential capture model:

1. short front-camera burst
2. back-camera QR scan
3. optional second front-camera burst

The app should not introduce a new login, discovery, registration, or feed transport stack unless the existing mobile camera application services prove insufficient for a presence-specific requirement.

---

## Product Role

`ppl-meta-presence-mobile` is the handheld user interface for Eyenet Presence.

It should allow an authenticated user to:

- sign into the platform
- initiate a presence interaction
- send short front-camera feeds for instant detection
- scan a QR from the target installation
- receive a presence action result

The mobile app is not intended to be a general-purpose streaming app or a continuous surveillance client.

It should still reuse the existing mobile camera application's foundations for user login, token persistence, service discovery, platform endpoint resolution, device registration, and feed packaging/upload patterns.

---

## Core User Story

A user opens the app, logs in, taps the main presence action, briefly lets the app capture a short front-camera burst, points the phone at a QR shown by the installation, and then receives a result based on instant detection and presence policy. If the first burst did not produce a sufficient result by the time QR scanning succeeds, the app shows a holding state and runs a second short front-camera burst.

---

## Primary Workflow

## Happy Path

1. user opens app
2. user authenticates
3. app loads current presence context
4. user taps primary presence CTA
5. app requests or confirms camera permission
6. app captures short front-camera burst
7. app uploads burst
8. app switches to back-camera QR scanner
9. user scans QR successfully
10. app waits for backend decision
11. backend returns granted or completed presence result
12. app shows success state

## Retry Path

1. user scans QR successfully
2. first instant detection result is missing or insufficient
3. app shows holding animation and explanatory state
4. app switches back to front camera
5. app captures second short burst
6. app uploads retry burst
7. backend returns presence result
8. app shows final success or failure state

## Failure Path

The app should handle:

- login failure
- camera permission denial
- front-camera capture failure
- upload failure
- QR timeout
- invalid QR
- expired session
- backend decision timeout
- final presence denial

---

## Screens

The first release should include the following screens.

## 1. Login Screen

Required behavior:

- email and password sign-in
- loading and error states
- persisted authenticated session where allowed

## 2. Presence Home Screen

Required behavior:

- shows current signed-in identity
- shows current installation or environment context if available
- has one primary CTA to start presence flow

## 3. Front Burst Capture Screen

Required behavior:

- activates front camera
- no complex preview UI required
- shows simple capture progress
- automatically completes after configured frame count or duration

## 4. QR Scan Screen

Required behavior:

- activates back camera
- shows live preview with scan guide
- shows scanning progress and timeout state
- reports QR success immediately

## 5. Holding And Retry Screen

Required behavior:

- displays waiting animation
- explains that a second confirmation is being processed
- transitions automatically to second front-burst capture when needed

## 6. Result Screen

Required behavior:

- shows success, denial, or retry-failed state
- shows minimal explanation
- offers return to home or retry flow

---

## Functional Requirements

## Auth API

The app must:

- authenticate against the existing platform authentication contract
- store session tokens securely according to platform standards
- restore authenticated session if allowed by policy
- allow sign-out

Inheritance requirement:

- the first implementation should reuse the current `EnhancedAuthenticationService` and hybrid service discovery flow from `ppl_meta_mobile_camera`

## Presence Session Lifecycle

The app must:

- create a presence mobile session before capture begins
- keep the session UUID for the entire flow
- associate both front-camera bursts with the same session
- poll or query the final result using the same session

Inheritance requirement:

- session creation and subsequent calls should build on top of the same persisted token and platform-services context already used by the existing mobile camera app

## Front-Camera Burst Capture

The app must:

- capture a small number of front-camera frames
- prefer low or medium-low resolution
- stop the front camera immediately after capture
- upload the burst promptly

Inheritance requirement:

- burst upload should reuse the existing feed transport patterns from `MobileStreamingService` where practical, adapting payload semantics for presence instead of rebuilding transport from scratch

Recommended first-release defaults:

- `3-8` frames
- `320x240` or equivalent low-resolution target
- total burst duration under `1.5s`

## QR Scanning

The app must:

- use the back camera
- show a visible preview for user guidance
- detect QR success quickly
- stop scanning once a valid QR is obtained

## Retry Burst

The app must:

- support one automatic retry burst when requested by the backend or implied by session status
- avoid infinite retry loops
- surface a clear failure if retry also fails or times out

## Result Handling

The app must:

- fetch final result state from the backend
- show explicit success and failure states
- distinguish transport failure from presence denial

---

## State Machine

The app state machine should be:

```text
idle
-> authenticating
-> ready
-> starting_session
-> front_burst_1_capturing
-> front_burst_1_uploading
-> qr_scanning
-> qr_hit
-> waiting_for_result
-> success
```

Retry branch:

```text
waiting_for_result
-> retry_required
-> front_burst_2_capturing
-> front_burst_2_uploading
-> waiting_for_result
-> success | denied | failed
```

Terminal failure states:

- `auth_failed`
- `permission_denied`
- `capture_failed`
- `upload_failed`
- `qr_timeout`
- `invalid_qr`
- `session_expired`
- `decision_failed`
- `presence_denied`

---

## UX Principles

The mobile flow should optimize for speed and clarity.

Required principles:

- minimal steps visible to the user
- immediate feedback after each phase transition
- no unnecessary configuration in the primary flow
- clear separation between technical failure and business denial
- clear instruction during QR scan and retry states

---

## API Expectations

The app is expected to use the following backend contracts.

## Authentication

- existing platform auth endpoints

Implementation note:

- the client auth flow should reuse the same discovery and login process already used by `ppl_meta_mobile_camera`

## Presence Session

- `POST /api/v1/presence/mobile/sessions`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}`
- `POST /api/v1/presence/mobile/sessions/{session_uuid}/qr-hit`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}/result`

## Feed Upload

- `POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst`
- `POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst/retry`

## QR Support

- `GET /api/v1/presence/qr/current` where applicable
- `POST /api/v1/presence/qr/validate` if client-assisted validation is needed

---

## Device And Permission Requirements

The app must request:

- camera permission
- network access

The app should not depend on:

- background camera execution for the first release
- concurrent front and back camera support
- microphone permission

---

## Data Handling Rules

The app should:

- keep raw burst data in memory only as long as needed for upload
- avoid long-term local storage of captured frames unless explicitly required
- clear session artifacts after terminal completion
- log operational errors without leaking sensitive user image data

---

## Telemetry

The mobile app should emit telemetry for:

- login success and failure
- first burst capture success and failure
- QR success and timeout
- retry required and retry completion
- final result outcome
- total flow duration

This telemetry should support product tuning and operational debugging.

---

## Non-Functional Requirements

The first release should aim for:

- end-to-end happy path under a few seconds on normal network conditions
- graceful degradation on slower devices
- deterministic cleanup when camera phases switch
- stable behavior across common Android devices

---

## Risks

1. Camera handoff latency may make the flow feel slow on lower-end devices.
2. Existing backend contracts may not yet support burst-oriented upload exactly as required.
3. Some QR scanning libraries may conflict with camera lifecycle if not isolated carefully.
4. Weak network conditions may require a more explicit result polling UX.

---

## Recommended Next Steps

1. define the first-release UI wireframes and state transitions
2. map the reusable services from `ppl_meta_mobile_camera` into the new app architecture
3. confirm the exact burst upload contract with `ppl-meta-presence`
4. confirm the result-polling and retry contract
5. scaffold the Flutter app with the state machine above
