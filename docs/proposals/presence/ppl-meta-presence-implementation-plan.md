# PPL Meta Presence Implementation Plan

**Date**: June 1, 2026  
**Status**: Active Implementation  
**Depends On**: [docs/proposals/presence/Eyenet presence.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/presence/Eyenet%20presence.md)

---

## Purpose

This document turns the Eyenet Presence proposal into a backend implementation plan for `ppl-meta-presence`.

The service is intended to act as the presence-domain orchestrator for:

- presence profile management
- reserved presence resource management
- mobile presence session management
- QR lifecycle management
- instant detection orchestration
- trigger and action execution
- presence analytics publication

The design goal is to reuse current platform capabilities rather than introduce duplicate identity, detection, or automation systems.

For the mobile side of the solution, this should mean explicit reuse of the current service and process layer already implemented in [ppl_meta_mobile_camera](/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera).

Updated mobile product direction:

- Presence should not introduce a dedicated mobile Presence screen as the primary operator flow
- Presence should be entered directly from the existing mobile camera surface
- the mobile camera control bar should expose Presence-specific actions in place of low-priority controls such as timer and zoom when Presence mode is active
- the preferred Presence architecture is to orchestrate the already-streaming registered platform camera rather than require a second burst-upload pipeline

---

## Scope

The first implementation of `ppl-meta-presence` should include:

1. presence profile entities for installation, device, and user scope
2. presence mobile session lifecycle endpoints
3. QR render and validation endpoints
4. short-feed intake for front-camera burst uploads
5. orchestration into existing instant detection endpoints
6. reserved presence camera and reserved presence collection lifecycle
7. presence-type group, trigger, and action orchestration rules
8. presence analytics event publication and summary endpoints

Out of scope for the first implementation:

- building a second vision inference stack
- replacing the existing instant detection pipeline
- replacing current authentication ownership
- replacing current camera or collection services
- implementing arbitrary concurrent dual-camera mobile capture requirements
- building a second independent mobile login, discovery, registration, or feed transport pipeline when those are already solved in `ppl_meta_mobile_camera`
- introducing a permanently separate mobile Presence screen when the existing camera UI can host the full Presence workflow more directly

---

## Naming Decision

This implementation plan standardizes the domain spelling to **presence**.

Canonical names should be:

- service: `ppl-meta-presence`
- mobile app: `ppl-meta-presence-mobile`
- API base path: `/api/v1/presence`
- semantic types: `presence`

Older `presense` spellings in draft material should be treated as transitional and should not be propagated into new APIs, tables, or service names.

---

## Architecture Role

`ppl-meta-presence` should be a headless REST service in the same architectural tier as the other PPL Meta backend services.

It should sit between:

- the mobile client
- existing platform identity and installation context
- existing instant detection endpoints
- existing trigger and action endpoints
- existing individual group, camera, and collection models
- the analytics domain

It should own orchestration and presence policy, not low-level detection or generic user management.

The service contract should therefore be designed so the presence mobile client can reuse the same mobile-side flows already used by `ppl_meta_mobile_camera` for authentication, endpoint discovery, device registration, and feed submission.

---

## Core Responsibilities

The service should own the following responsibilities directly.

## 1. Presence Identity Graph

Maintain a normalized presence identity graph with:

- installation presence profile
- device presence profile
- user presence profile

The graph should support lookup by installation UUID, device UUID, and user UUID.

## 2. Reserved Presence Resources

Manage the presence-specific reserved resources:

- reserved presence camera
- reserved presence collection

Current local implementation notes:

- installation reservation state is inspectable at `/api/presence/installations/current`
- installation camera and collection bindings can be cleared at `/api/presence/installations/current/reset-reservations`
- when no reservation exists, the service auto-selects a real registered platform camera and its linked media collection
- camera selection order defaults to `USB, EDGE, RTSP, MOBILE` and can be overridden with `PRESENCE_PREFERRED_CAMERA_TYPES`
- camera name preference can be forced with `PRESENCE_PREFERRED_CAMERA_NAMES`, matched against camera name or `device_id`
- allowed candidate statuses default to `available,disconnected,connected` and can be overridden with `PRESENCE_ALLOWED_CAMERA_STATUSES`
- local VS Code testing includes a `♻️ Reset Presence Reservations (Local)` task, which calls `ppl-meta-presence/reset_presence_reservations.sh`
- explicit reservation endpoints currently support validated `bind` mode only; unsupported reservation modes fail fast instead of being silently coerced
- presence camera listings now expose reservation metadata including the internal reserved resource UUID, installation UUID, and linked collection UUID for operator-facing debugging

The service should either create these resources through existing platform contracts or bind to already-created ones and validate them.

## 3. Presence Mobile Sessions

Manage short-lived mobile sessions that correlate:

- authenticated user
- device context
- QR challenge
- existing camera streaming state
- instant detection attempts
- final presence result

## 4. QR Operations

Generate and validate short-lived QR payloads for mobile presence interactions.

## 5. Instant Detection Orchestration

Prefer the existing platform camera streaming path as the authoritative source for instant detection. Front-camera burst upload remains available for mixed-mode experiments, but `camera_only` should rely on the already-registered, already-streaming platform camera rather than a second burst-ingestion path.

Revised orchestration expectation for mobile-driven Presence:

- mobile user taps a Presence action directly from the live camera UI
- backend creates a Presence session for `qr_only`, `camera_only`, or `qr_plus_camera`
- for `camera_only` and `qr_plus_camera`, backend remotely connects the reserved platform camera if needed
- on successful connect, backend remotely starts instant detection on that same camera
- for `qr_only`, mobile launches the QR scanner immediately
- for `qr_plus_camera`, mobile runs camera and QR work as one asynchronous sequence rather than forcing the operator through a separate dedicated Presence screen
- on success or terminal failure, backend remotely stops instant detection and disconnects the camera so the Presence lifecycle is self-cleaning

Queueing note:

- `qr_plus_camera` should be treated as an asynchronous orchestration flow
- the existing Redis-backed platform infrastructure is the preferred first queueing/event coordination option unless a concrete limitation forces a second queue mechanism

---

## Mobile UX Direction

The preferred mobile Presence UX is now a camera-overlay model rather than a dedicated Presence view.

Expected control changes on the existing mobile camera screen:

- replace the timer button with a QR Presence action
- replace the zoom button with a camera-only Presence action
- replace the gallery shortcut with a guided sequential Presence action for camera -> QR scan -> camera / verified-presence flow

Behavioral rules:

- tapping any Presence button should automatically transition the mobile camera app into Presence orchestration mode
- operators should not need to separately open a dedicated Presence page before starting the flow
- the app should continue to reuse existing authentication, registration, discovery, and streaming contracts already owned by the mobile camera app
- the station-side web flow remains responsible for rendering the QR challenge when QR is part of the selected mode

Mode-specific expectations:

- `qr_only`: launch scanner immediately and submit the station QR
- `camera_only`: remotely connect camera, start instant detection, wait for result, then remotely stop and disconnect
- `qr_plus_camera`: orchestrate connect + instant detection + QR scan as one asynchronous sequence and then remotely stop and disconnect on terminal outcome

## 6. Presence Decisioning

Resolve whether the resulting identity match satisfies the user-scoped or installation-scoped presence policy.

## 7. Action Execution

Map presence outcomes to existing trigger and action workflows.

## 8. Analytics Publication

Publish presence-specific aggregates and event records for analytics.

---

## Service Dependencies

The implementation will need explicit integration contracts with the following platform areas.

## Local Runtime Contract

Local development now standardizes inter-service auth on the repository root
file `.env.service-auth`.

Current local contract:

- `SERVICE_SECRET` and `NODE_SERVICE_SECRET` are dedicated service-auth values
- they are not derived from installation UUIDs, license UUIDs, or any other
  identifiers
- `ppl-meta-node` and `ppl-meta-presence` both source
  `scripts/load-presence-runtime-env.sh` before startup
- the loader only imports the shared auth values and does not import unrelated
  service env settings such as `DATABASE_URL`
- deterministic validation should explicitly target the presence database when
  needed rather than inheriting ambient shell state

Operational implication:

- if the presence admin repair path fails with service-auth errors, verify both
  node and presence were started through the shared loader path and that
  `.env.service-auth` contains the current shared secret

## Existing Camera Lifecycle Reuse

Presence should reuse the existing camera-service lifecycle instead of creating a
parallel camera control path.

Current reusable process discovered in the platform:

- camera inventory comes from `ppl-meta-cameras` `GET /api/v1/cameras/`
- camera connection is handled by `POST /api/v1/cameras/{device_id}/connect`
- camera disconnection is handled by `POST /api/v1/cameras/{device_id}/disconnect`
- instant-detection start is handled by `POST /api/v1/instant-detection/start/{camera_id}`
- instant-detection stop is handled by `POST /api/v1/instant-detection/stop/{camera_id}`
- gateway only proxies the instant-detection routes to camera service
- camera service already auto-connects mobile-camera queue workers before
  instant detection starts when the worker is missing

Observed gap from live validation:

- presence could start instant detection successfully
- gateway status showed a per-camera instant-detection session record
- but the camera sampler stopped without publishing a terminal result
- presence remained in `pending_results` because `results/{camera_id}` stayed `404`

Updated presence-side orchestration expectation:

- resolve an available camera
- connect that camera through the camera service when needed
- start instant detection for that resolved camera
- poll for a terminal result
- if no terminal result is published and the sampler is no longer running,
  reconnect and restart detection up to a bounded retry count
- stop instant detection and disconnect the camera after success or retry exhaustion

This keeps camera lifecycle ownership in camera service while letting presence
orchestrate the full presence-session workflow.

Validated local outcome:

- local live validation completed in `auto` mode with non-simulated detection
- instant detection produced a granted presence result and executed the mapped
  trigger/action workflow
- trigger alerts were observed on the resolved camera during the live run
- camera hardware then released cleanly, confirmed both by the brief LED window
  on the development machine and by the repaired `GET /api/v1/cameras/active`
  endpoint returning `active_count: 0` after the flow

This closes the earlier gap where presence could complete logically while camera
cleanup remained unverified at the hardware/runtime level.

Operational note from repeated live runs:

- presence grants remained correctly gated on fresh trigger-backed `ppl_match`
  results and did not reproduce a false-positive grant path
- direct session, result, and trace APIs now expose the provisioned external
  asset UUIDs used for the presence group, trigger, and action
- repeated live runs confirmed that the presence-related email action can be
  delivered successfully for the same provisioned trigger
- one earlier missed email did not reproduce after the UUID-based validation
  pass, so the remaining risk is narrowed to intermittent downstream multi-action
  delivery or fan-out behavior under concurrent same-camera trigger activity,
  not the presence service's match-to-grant rule
- the presence backend now exposes the provisioned trigger's configured action
  UUIDs and names on its own action-plan/result debugging surface so operators
  can verify expected fan-out without leaving the presence API

## Authentication And User Context

Expected dependency:

- existing Node or current auth service

Required data:

- authenticated user UUID
- email
- display name
- roles or capabilities

Expected client inheritance:

- the first presence mobile client should reuse `EnhancedAuthenticationService` and `HybridServiceDiscoveryService` behavior from `ppl_meta_mobile_camera`

## Installation Identity And Licence Context

Expected dependency:

- existing installation lifecycle or authority-backed identity contract

Required data:

- installation UUID
- installation metadata
- licence status

## Instant Detection

Expected dependency:

- existing instant detection endpoints through Cameras or Gateway

Required behavior:

- submit short-feed-derived detection inputs
- poll or fetch results by correlation ID

## Individuals, Groups, Cameras, Collections

Expected dependency:

- existing cameras and group management contracts

Required behavior:

- resolve or provision presence-type groups
- resolve or provision presence-type camera
- resolve or provision presence-type collection

Expected client inheritance:

- if presence needs a registered device anchor, it should align with the current `AutoCameraRegistrationService` conventions already used in `ppl_meta_mobile_camera`

## Triggers And Actions

Expected dependency:

- current trigger and action endpoints

Required behavior:

- create or resolve presence-specific trigger and action definitions
- execute mapped actions based on presence outcomes

## Analytics

Expected dependency:

- current analytics ingestion and query surfaces

Required behavior:

- publish presence events and summary views

---

## Domain Model

## PresenceProfile

Suggested fields:

- `presence_profile_uuid`
- `profile_type`
- `parent_presence_profile_uuid`
- `installation_uuid`
- `device_uuid`
- `user_uuid`
- `display_name`
- `status`
- `metadata`
- `created_at`
- `updated_at`

## PresenceReservedResource

Suggested fields:

- `resource_uuid`
- `resource_type` with values `camera` or `collection`
- `installation_uuid`
- `bound_profile_uuid`
- `platform_resource_uuid`
- `status`
- `created_at`
- `updated_at`

## PresenceMobileSession

Suggested fields:

- `session_uuid`
- `installation_uuid`
- `device_uuid`
- `user_uuid`
- `status`
- `qr_token`
- `expires_at`
- `created_at`
- `updated_at`

## PresenceDetectionAttempt

Suggested fields:

- `attempt_uuid`
- `session_uuid`
- `attempt_index`
- `capture_phase`
- `instant_detection_request_id`
- `instant_detection_status`
- `result_payload`
- `created_at`

## PresenceDecision

Suggested fields:

- `decision_uuid`
- `session_uuid`
- `matched_group_uuid`
- `resolved_camera_uuid`
- `resolved_collection_uuid`
- `decision`
- `reason_code`
- `policy_source`
- `trigger_type`
- `action_type`
- `action_execution_status`
- `executed_at`

---

## REST API Plan

## Phase 1 Endpoints

- `GET /api/v1/presence/installations/current`
- `GET /api/v1/presence/profiles/me`
- `POST /api/v1/presence/mobile/sessions`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}`
- `POST /api/v1/presence/qr/render`
- `POST /api/v1/presence/qr/validate`
- `GET /api/v1/presence/cameras`
- `POST /api/v1/presence/cameras/reserve`
- `GET /api/v1/presence/collections`
- `POST /api/v1/presence/collections/reserve`

## Phase 2 Endpoints

- `POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst`
- `POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst/retry`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}/instant-detection-status`
- `POST /api/v1/presence/mobile/sessions/{session_uuid}/qr-hit`
- `POST /api/v1/presence/mobile/sessions/{session_uuid}/bind-resources`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}/result`

## Phase 3 Endpoints

- `GET /api/v1/presence/analytics/summary`
- `GET /api/v1/presence/analytics/by-user`
- `GET /api/v1/presence/analytics/by-device`
- `GET /api/v1/presence/analytics/outcomes`
- `GET /api/v1/presence/analytics/by-policy-source`
- `POST /api/v1/presence/analytics/repair`
- `GET /api/v1/presence/decision-history`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}/action-plan`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}/decision-history`
- `GET /api/v1/presence/mobile/sessions/{session_uuid}/trace`
- `GET /api/v1/presence/mobile/session-traces`

---

## Decision Flow

The initial backend decision flow should be:

1. user authenticates through existing auth
2. mobile app creates a presence session
3. service resolves installation profile, user profile, and device profile
4. service resolves or validates reserved presence camera and collection
5. mobile app uploads the first front-camera burst
6. service forwards the burst into instant detection
7. mobile app submits a QR hit
8. service binds the QR target to the session
9. service fetches instant detection result
10. service evaluates group membership and collection scope
11. service resolves policy precedence as group policy, then installation policy, then default policy
12. service maps the decision to a presence trigger and action path and records `policy_source`
13. service executes action
14. service persists decision and analytics
15. service returns final result

If step 9 does not yield a sufficient result in time, the service should keep the session open and accept a retry burst.

## Presence Assurance Modes

The first frontend-integrated presence design should support three explicit assurance modes while keeping one backend orchestration model.

### QR-Only Mode

Suggested contract:

- session mode: `qr_only`
- required inputs: authenticated user, resolved installation context, QR hit bound to a rendered installation challenge
- skipped inputs: camera-backed capture evidence and camera-match requirement
- intended result: lowest-assurance presence outcome appropriate for QR-only check-in semantics

This mode should not be treated as camera-backed identity verification.

### Camera-Only Mode

Suggested contract:

- session mode: `camera_only`
- required inputs: authenticated user, resolved installation context, validated reserved camera context, camera-backed capture evidence
- skipped input: QR challenge
- intended result: lower-assurance presence grant that still depends on successful backend decisioning and persisted analytics

This mode is appropriate when the frontend already provides enough trusted installation context and the product does not require QR-based proof of interaction with a rendered station.

### QR Plus Camera Mode

Suggested contract:

- session mode: `qr_plus_camera`
- required inputs: authenticated user, resolved installation context, validated reserved camera context, camera-backed capture evidence, QR hit bound to a rendered installation challenge
- intended result: higher-assurance presence grant tied both to the camera-backed match and the rendered session target

This mode should remain the stronger and more explicit verification path.

### Backend Semantics

To keep the model coherent:

- session records should persist the selected assurance mode
- decision history and analytics should be able to differentiate the three modes
- policy mapping should be able to distinguish actions allowed for `qr_only`, `camera_only`, and `qr_plus_camera`
- the frontend should never make a skipped-QR session look equivalent to a QR-bound session unless policy intentionally treats them the same
- the frontend should never make a QR-only session look equivalent to a camera-backed session unless policy intentionally treats them the same

Suggested assurance ordering:

- `qr_only`: lowest assurance
- `camera_only`: medium assurance
- `qr_plus_camera`: highest assurance

## Frontend Flow Mapping

The frontend presence module can support all three modes without splitting the backend into separate systems.

### QR-Only Flow

1. frontend loads current installation presence state
2. mobile user taps the QR Presence action from the live camera controls
3. backend starts a `qr_only` session
4. station frontend renders a QR challenge in the target installation context
5. mobile launches the QR scanner and submits the QR successfully
6. backend returns the QR-only check-in result

### Web Or Mobile Camera-Only Flow

1. frontend loads current installation presence state
2. frontend queries presence-eligible cameras
3. user or operator chooses a camera when more than one candidate exists
4. frontend requests reservation or binding through the presence backend
5. mobile user taps the camera-only Presence action from the live camera controls
6. backend starts a `camera_only` session
7. backend remotely connects the reserved mobile camera when needed
8. backend remotely starts instant detection on that same reserved platform camera
9. backend completes the presence decision and returns the lower-assurance result
10. backend remotely stops instant detection and disconnects the camera on terminal outcome

### Web Plus Mobile QR Flow

1. web frontend loads current installation presence state
2. web frontend queries presence-eligible cameras
3. operator chooses the reserved presence camera when needed
4. web frontend binds the context and renders a QR
5. mobile user taps the guided combined Presence action from the live camera controls
6. backend starts a `qr_plus_camera` session
7. backend remotely connects the reserved mobile camera and starts instant detection
8. mobile app launches QR scanning as part of the same asynchronous flow
9. backend correlates camera-backed detection and QR resolution
10. backend returns the higher-assurance result
11. backend remotely stops instant detection and disconnects the camera on terminal outcome

### Responsibility Split

- frontend: discovery, operator choice, station QR presentation, session progress, result display
- mobile app: authenticated user capture surface, Presence action launch points, QR scan surface, streaming reuse
- backend: validation, remote camera lifecycle orchestration, policy evaluation, action execution, analytics persistence

Recommended product wording:

- `qr_only`: check-in
- `camera_only`: presence match
- `qr_plus_camera`: verified presence

Current operator note:

- `camera_only` should be validated against the reserved streaming platform camera path, not against the experimental front-burst upload path
- the preferred implementation direction is to remove the dedicated mobile Presence workflow in favor of camera-overlay actions on the normal camera screen

---

## Provisioning Rules

The service should support two provisioning models.

## Auto-Provisioning

On first use for an installation:

- create installation presence profile
- create or bind a reserved presence camera
- create or bind a reserved presence collection
- create user presence profile when a user first uses presence
- create presence-type group for that user when enabled by policy

## Admin-Provisioned

An administrator pre-creates:

- reserved presence camera
- reserved presence collection
- presence-type groups
- presence-type triggers and actions

The service then validates and binds those resources at runtime.

The implementation should support both models, but the first release should prefer auto-provisioning with explicit admin override.

---

## Presence Resource Rules

Reserved presence resources should obey the following rules.

## Presence Camera

- must be typed or tagged as `presence`
- must belong to the target installation
- must be discoverable from the presence service
- must be usable as the reporting anchor for presence events

## Presence Collection

- must be typed or tagged as `presence`
- must belong to the target installation or target presence station scope
- should contain the reserved presence camera
- should be usable for scoping analytics and actions

## Presence Group

- must be typed or tagged as `presence`
- may be associated with one user or one installation-level policy

---

## Trigger And Action Rules

The implementation should introduce presence-specific semantics without building a separate automation system.

Recommended trigger semantics:

- `presence_match`
- `presence_no_match`
- `presence_retry_required`

Recommended action semantics:

- `presence_grant`
- `presence_deny`
- `presence_notify`
- `presence_log`

These should be represented through the existing trigger and action system and resolved by the presence service.

## Assurance-Aware Policy Rules

The backend policy layer should treat the three session modes as distinct outcome classes, not as cosmetic variants of the same grant.

Suggested normalized mapping:

- `qr_only` -> `assurance_level=low` -> `grant_type=check_in`
- `camera_only` -> `assurance_level=medium` -> `grant_type=presence_match`
- `qr_plus_camera` -> `assurance_level=high` -> `grant_type=verified_presence`

Recommended first-release policy rules:

- `qr_only`
  - should succeed on valid authenticated QR correlation alone
  - should not require `ppl_match`
  - should not unlock actions that imply strong identity verification
- `camera_only`
  - should require successful camera-backed presence evaluation
  - may succeed without QR correlation
  - should remain weaker than `qr_plus_camera` when policy distinguishes stronger installation-bound assurance
- `qr_plus_camera`
  - should require both successful QR correlation and successful camera-backed presence evaluation
  - should be the only mode eligible for the strongest verified-presence actions when policy requires the highest assurance

Current backend policy behavior:

- installation and group `action_policy` metadata may now provide mode-specific overrides under `qr_only`, `camera_only`, and `qr_plus_camera`
- those override buckets may supply decision-specific trigger/action mappings and take precedence over the generic decision mapping for the same policy scope

Recommended first-release action examples:

- `qr_only`: attendance check-in, arrival mark, low-risk notification, audit log
- `camera_only`: presence match, medium-trust notification, medium-trust workflow enablement, audit log
- `qr_plus_camera`: verified presence grant, strongest workflow enablement, strongest automation path, audit log

Current backend default mapping note:

- granted `qr_only` sessions currently default to `trigger_type=presence_check_in` and `action_type=presence_log`
- granted `camera_only` sessions currently default to `trigger_type=presence_match` and `action_type=presence_grant`
- granted `qr_plus_camera` sessions currently default to `trigger_type=presence_verified_match` and `action_type=presence_grant`

Frontend and backend should both surface the resolved `session_mode`, `assurance_level`, and `grant_type` so users and operators can understand what class of presence result was actually returned.

Current frontend implementation status in `ppl-meta-frontend`:

- a dedicated `Presence` screen now consumes the presence backend directly
- the current screen exposes summary analytics, `session_mode` and `grant_type` breakdowns, recent session trace visibility, and a first execution panel for starting a session, retrieving current QR-backed state, validating the current QR token, submitting a test QR hit, and polling live result state
- the current screen also exposes the admin flows already supported cleanly by the backend: installation policy editing, presence-group ensure, camera reservation, and reservation reset
- direct collection reservation is not yet exposed in the frontend module because the current backend contract only exposes reserved collections, not a browsable platform collection inventory suitable for operator selection
- reserving a camera remains the preferred operator flow for now because the backend auto-binds a linked media collection when one can be resolved from the selected camera

---

## Analytics Plan

The service should publish:

- presence attempt count
- presence success count
- presence failure count
- retry count
- by-user breakdown
- by-device breakdown
- by-policy-source breakdown
- by-installation breakdown
- by-session-mode breakdown
- by-grant-type breakdown
- by-reserved-collection breakdown
- action outcome breakdown

The event model should be consistent enough to support widgets and audit views.

Operational note:

- older analytics events may not have `policy_source`, `trigger_type`, or `action_type` in their saved payloads
- the current service repairs that metadata lazily on startup by backfilling from persisted decision history and session state before analytics are served
- the current backend also exposes analytics grouped by `session_mode` and `grant_type`, so dashboards can separate check-ins, presence matches, and verified presence outcomes directly from API aggregates
- those `session_mode` and `grant_type` aggregates are now exposed through first-class HTTP endpoints, not just internal service methods

Validation note:

- local deterministic validation now covers all three precedence branches: `default_policy`, `installation_policy`, and `group_policy`
- `🧪 Validate Presence Flow (Local)` proves a completed simulated flow against a temporary simulated presence service
- `🧪 Validate Presence Policy Modes (Local)` proves all three policy-source branches in-process without mutating the running local service
- `🧪 Validate Presence Trace And Analytics (Local)` remains the live-stack authenticated check for trace and analytics routes
- the live validator now asserts the production contract for non-simulated completion: `reason_code=presence_ppl_match` and `policy_source=platform_trigger`

Validated local runtime outcome:

- presence no longer grants on a bare instant-detection transport success with `people_count=0`
- first successful enrollment can seed the presence individuals group and start one automatic confirmation detection pass
- completed live-stack grants now require a real media `ppl_match` hit and persist as `reason_code=presence_ppl_match`
- the validated local run completed with `policy_source=platform_trigger`, `action_execution_status=executed`, and an audit log recorded by communications
- an additional pre-existing alert trigger on the same camera also fired during local validation, which confirms the expected multi-trigger behavior for a shared camera feed in this runtime
- the explicit empty-group validation path was also proven live: the validator cleared the existing presence group member, the first detection re-seeded the group, a second confirmation attempt was observed, and the session completed only after the follow-up `ppl_match`
- the presence trigger was validated live with multiple bound actions, including a user-configured email action that delivered successfully after the same trigger-backed match
- failed presence sessions now surface explicit user-facing unsuccessful alerts in both the web and mobile presence clients instead of ending silently when no grant is produced
- presence session timeout enforcement is now wall-clock driven rather than poll-driven: session expiry schedules active backend timeout handling and no longer depends on a later read request to notice the expiry
- timed-out or failed camera-backed presence sessions now schedule instant-detection stop and camera disconnect cleanup so the reserved camera is released as part of terminal failure handling
- installation-scoped presence session settings are now exposed at `#/settings` and persisted across restarts by selecting the most recently updated installation profile that actually contains saved `session_settings`
- live PostgreSQL validation confirmed that the saved 30-second timeout remained present in persisted installation profile metadata and that duplicate legacy installation profiles were the root cause of the earlier restart regression

Current camera-only validation checklist:

1. keep the mobile camera connected and actively streaming through the existing camera app path
2. reserve that same mobile camera in Presence settings
3. ensure the generated Presence trigger points to that same reserved mobile camera
4. start a fresh `camera_only` session
5. verify the outcome through Presence result state plus cameras, presence, and communications logs

Validated platform assets in local runtime:

- group: `Presence Individuals 7`
- action: `Presence Action 7`
- trigger: `Presence Trigger 7`
- trigger mode: `ppl_match`
- threshold: `0.6`
- action set validated live: local presence action plus an attached email action on the same trigger

Operational note:

- operators can now query cross-session decision history and full session traces by `session_uuid`, `user_uuid`, `installation_uuid`, `policy_source`, and optional `limit`
- collection responses now include `total`, `returned`, `limit`, and `has_more` so dashboards and support tooling can distinguish a full result set from a limited slice
- the single-session routes remain the primary detail view, while the new collection routes support debugging and support workflows across many sessions
- operators can also trigger the existing analytics metadata backfill through an authenticated API route, so the local repair script is no longer the only operational path
- the repair route now requires admin-level authorization; presence resolves that either from token claims or by querying node's `user-permissions` endpoint with `SERVICE_SECRET`
- analytics routes now expose the remaining Phase 4 dashboard breakdowns as first-class API surfaces: by installation, by reserved collection, and by action outcome
- action outcome analytics now make downstream execution state visible without requiring an operator to inspect individual session traces one by one
- local persistence debugging revealed many duplicate `installation` profiles for the same `local-installation` context in PostgreSQL; presence startup now prefers the newest installation profile carrying `session_settings` so operator-selected timeout and attempt settings are not lost behind older empty metadata rows

---

## Security Requirements

The implementation should enforce:

- authenticated session ownership
- capability checks on administrative endpoints
- short-lived QR tokens
- replay protection for QR flows
- data minimization for raw front-camera bursts
- audit logging for every decision and action execution

---

## Delivery Phases

## Phase 1

- service scaffold
- profile entities
- session entities
- QR endpoints
- resource reservation endpoints

## Phase 2

- instant detection integration
- session decisioning
- retry path support

## Phase 3

- trigger and action mapping
- auto-provisioning of groups and resources
- analytics publication

## Phase 4

- hardening
- metrics
- operational dashboards
- admin management refinements

Backend completion status:

- completed for the presence backend API surface
- covered by the current implementation through stricter reservation validation, cross-session trace and decision-history queries, trigger fan-out observability, admin-gated analytics repair, and analytics breakdowns for policy source, installation, reserved collection, and action outcomes
- frontend/admin widget work remains a separate consumer task rather than a backend gap
- that statement is now only partially true: a first consumer slice exists in `ppl-meta-frontend`, including analytics, admin controls, session-detail drill-down for action plan, decision history, and trace inspection, plus initial execution controls for starting a session, validating and exercising QR flow, and retrieving current QR/state; an initial mobile execution slice now also exists inside `ppl_meta_mobile_camera`, reusing the existing authenticated node/gateway bootstrap and registered camera anchor for session creation, front-burst upload, QR scan submission, and result polling, while a fuller dedicated mobile flow remains follow-up work

---

## Recommended Implementation Order

The recommended implementation order for the presence initiative is backend-first.

The reason is that the mobile application and backend-facing widgets depend on stable backend contracts for: 

- presence session lifecycle
- QR issuance and validation
- burst upload DTOs
- presence decisioning
- analytics persistence and retrieval

The implementation should therefore proceed in the following order.

## Order 1. Presence Backend Service Skeleton

Implement `ppl-meta-presence` first with:

- service scaffold
- core entities
- session lifecycle endpoints
- QR endpoints
- reserved presence resource endpoints

## Order 2. Backend Integration With Existing Platform Services

Connect the backend service to:

- instant detection
- groups
- triggers and actions
- cameras and collections
- analytics persistence

This step should make the backend capable of accepting a presence session, correlating QR and burst data, and producing a terminal presence event.

## Order 3. Minimal Backend Frontend Widget Layer

Implement only the minimum backend-facing UI needed to drive the use case:

- presence QR widget
- presence session status widget

At this stage, the goal is not full frontend polish. The goal is to make the backend-generated QR and backend-driven session lifecycle visible and testable.

## Order 4. Presence Mobile Application

Only after backend contracts are stable should `ppl-meta-presence-mobile` be implemented in earnest.

The mobile app should then be built on top of the frozen contracts and inherited service/process layer from `ppl_meta_mobile_camera`.

## Order 5. Presence Analytics Widgets And Operational Polish

After the end-to-end flow works, complete:

- backend analytics widgets
- richer admin setup flows
- metrics and operational dashboards
- retry and failure-state refinements

## Minimum Executable Milestone

Before mobile implementation should begin in earnest, the backend should already be able to:

1. issue a presence QR
2. create a presence session
3. accept a front-camera burst upload
4. accept a QR hit
5. produce and persist a terminal presence result
6. expose that result through presence analytics endpoints

---

## Risks

1. Existing instant detection APIs may not currently accept the exact burst-upload contract the service needs.
2. Current camera and collection models may need schema extension for `presence` semantics.
3. Auto-provisioning could create resource sprawl if lifecycle rules are not explicit.
4. Trigger and action reuse may expose naming collisions unless presence semantics are clearly namespaced.
5. QR replay and stale-session handling need strict validation to avoid incorrect grants.

---

## Implementation-Readiness Gaps

The simple presence use case is directionally covered by the documentation, but the following backend surfaces still need to be made explicit or implemented before the use case is fully implementation-ready.

## Backend UI Widgets Still Needed

The backend-facing frontend should expose at least the following presence widgets:

- a presence QR widget that requests a short-lived QR payload from `ppl-meta-presence` and renders it on screen
- a presence session status widget that can show whether a mobile session is waiting, retrying, granted, denied, or failed
- presence analytics widgets that show summary, outcomes, and recent presence activity

The proposal already assumes these widgets exist conceptually, but their exact frontend contracts are not yet fully specified.

## Backend Endpoints Still Needed Or Need Tightening

The following endpoints are either required by the simple use case or need tighter implementation-level definition:

- `POST /api/v1/presence/qr/render`
Needed for the backend presence widget to request renderable QR payload data.

- `GET /api/v1/presence/qr/current`
Implemented.

Current behavior:

- returns the current session-backed QR payload for a device when one exists
- returns `found=false` without minting a synthetic token when no current QR exists
- supports backend widgets that need to poll or refresh QR state safely

- `POST /api/v1/presence/mobile/sessions`
Already defined, but the implementation contract should confirm whether a registered `device_uuid` is mandatory on day one.

- `POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst`
Already defined, but the inherited burst DTO now needs server-side DTO and validation implementation.

- `POST /api/v1/presence/mobile/sessions/{session_uuid}/qr-hit`
Needed to correlate the QR shown in the backend UI with the mobile session.

- `GET /api/v1/presence/mobile/sessions/{session_uuid}/result`
Needed for the mobile app to retrieve final presence outcome.

- `POST /api/v1/presence/mobile/sessions/{session_uuid}/bind-resources`
Implemented with stricter validation.

Current behavior:

- explicit bind requests must reference resources already reserved for presence
- successful binding resolves and stores the validated platform resource UUIDs
- invalid resource references now fail fast instead of silently persisting arbitrary values

- `POST /api/v1/presence/cameras/reserve`
- `POST /api/v1/presence/collections/reserve`
Tightened.

Current behavior:

- only validated `bind` mode is currently supported
- unsupported reservation modes fail fast with a validation error
- reserved camera listings now surface richer operator-facing reservation metadata

- `GET /api/v1/presence/analytics/summary`
- `GET /api/v1/presence/analytics/outcomes`
- `GET /api/v1/presence/analytics/by-user`
- `GET /api/v1/presence/analytics/by-device`
- `GET /api/v1/presence/analytics/by-policy-source`
- `GET /api/v1/presence/analytics/by-installation`
- `GET /api/v1/presence/analytics/by-reserved-collection`
- `GET /api/v1/presence/analytics/action-outcomes`
- `POST /api/v1/presence/analytics/repair`
Implemented.

Current behavior:

- presence analytics now cover the Phase 4 backend dashboard breakdowns called for by the plan
- operators can query installation-level, collection-level, and action-outcome aggregates directly from the presence API
- analytics metadata repair is available through an admin-gated endpoint instead of only through startup repair or local scripts

## Backend Domain Behavior Still Needing Explicit Confirmation

The following behaviors are assumed by the simple use case, but still need to be locked down during implementation:

- whether the backend QR widget should prefer `qr/current` reuse or force a fresh `qr/render` on each operator action
- whether a mobile session can exist before QR scan, or only after the QR is scanned
- whether the first presence release requires successful action execution before analytics are published, or whether analytics are published for all terminal decisions including action failure
- whether presence analytics should appear in generic analytics dashboards, presence-specific dashboards, or both

## Minimum Readiness Definition For The Simple Use Case

The simple use case should be considered implementation-ready only when all of the following are true:

1. the backend frontend has a QR-rendering presence widget
2. `ppl-meta-presence` can issue and validate short-lived QR payloads
3. the mobile app can create a presence session, upload a burst, and submit a QR hit
4. the backend can persist a terminal presence event
5. presence analytics endpoints can return that persisted event in summary and outcome views

---

## Recommended Next Steps

1. confirm the canonical existing endpoints for instant detection submission and result retrieval
2. confirm how camera and collection type metadata should be represented in current services
3. define the first-release presence action set
4. map `EnhancedAuthenticationService`, `HybridServiceDiscoveryService`, `AutoCameraRegistrationService`, and `MobileStreamingService` from `ppl_meta_mobile_camera` into the presence mobile design
5. implement the service skeleton and initial entities
