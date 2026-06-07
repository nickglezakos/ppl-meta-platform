# Proposal: Multi-Camera Stream State Management Stabilization

## Summary
This proposal defines a practical implementation path to stabilize stream lifecycle behavior across all supported camera types in multi-stream view by introducing Redis-backed stream state as the source of truth and using Celery for control-plane recovery workflows.

Supported camera types:
- USB cameras
- Mobile cameras
- RTSP cameras
- Edge cameras

The immediate objective is to prevent the "tile exists but no video" scenario caused by timing/race issues between:
- frame ingestion cadence,
- stale cleanup decisions,
- multi-view parallel stream creation,
- reconnect/recovery orchestration.

In addition, this proposal introduces persistent operational value retention for every streaming camera, an admin-facing operations overview for live status and policy control, and support-focused analytics endpoints.

This path intentionally avoids a full stream pipeline rewrite and instead applies incremental architecture hardening with low operational risk.

## Problem Statement
Observed behavior class:
- Single stream may work while multi-stream can show wrapper tiles with no video for one or more camera types.

Likely cause class:
- Backend stream lifecycle race/timing issue, amplified under multi-view fan-out and camera-type-specific cadence variability.

Current pain points:
- Staleness decisions depend too heavily on local/in-process timing.
- Viewer activity and source liveness are not consistently coordinated across workers.
- Cleanup can stop/mark streams stale during transient ingestion gaps.

## Goals
1. Make stream liveness and viewer activity deterministic across processes.
2. Reduce false stale disconnects across USB/mobile/RTSP/edge under multi-view load.
3. Keep frame-plane fast and local while moving control-plane truth to Redis.
4. Reuse existing platform capabilities (Redis + Celery) with minimal disruption.
5. Support per-camera-type policy tuning without forking core lifecycle logic.
6. Retain operational readings and policy history for troubleshooting and support analytics.
7. Provide an admin operations screen with safe editing of acceptable ranges and thresholds.

## Non-Goals
- No migration of raw video frame transport to Celery.
- No immediate protocol change (MJPEG/WebRTC/etc.).
- No frontend redesign.

## Proposed Architecture (Control Plane)
### 1) Redis as stream state source of truth
Use Redis keys/structures for camera stream session state:
- Per-camera liveness key with TTL (heartbeat from frame ingestion path).
- Per-camera active-viewer counter.
- Per-camera session metadata (status, last frame timestamp, worker id, last transition reason).

Recommended key patterns:
- `camera:stream:{camera_id}:liveness` (TTL key)
- `camera:stream:{camera_id}:viewers` (integer)
- `camera:stream:{camera_id}:state` (hash/json)

### 2) Redis Streams for lifecycle events
Record state transitions in Redis Streams for ordering and replay:
- `frame_received`
- `viewer_attached`
- `viewer_detached`
- `stale_candidate`
- `stale_marked`
- `stream_resumed`
- `cleanup_skipped_due_to_active_viewers`

Benefits:
- Cross-worker visibility.
- Post-incident diagnostics.
- Safer state machine transitions.

### 2.1) Operational readings retention
Persist operational readings for any actively streaming camera:
- hot path: latest values in Redis for real-time dashboard reads,
- history path: append to a time-series analytics store for support analysis (retention + downsampling policy).

Suggested value groups:
- health: last frame timestamp, frame gap, liveness ttl remaining, stale candidate count,
- quality: effective fps, frame read failures, timeout count,
- recovery: reconnect attempts, cooldown state, last recovery reason,
- usage: active viewers, attach/detach rate,
- source: camera type, transport/source latency where available.

Sampling guidance:
- event-driven writes on transition,
- periodic snapshots every N seconds,
- downsample older windows to control storage cost.

### 3) Cleanup policy with dual condition gating
A stream is eligible for stale teardown only when both are true:
- Liveness expired (or stale threshold exceeded), and
- Active viewers == 0 (or below configurable threshold after grace).

Add grace windows:
- camera-type-specific stale grace (USB/mobile/RTSP/edge profiles).
- `post_viewer_attach_protection_seconds` to avoid immediate teardown after multi-view starts.

### 3.1) Camera-type policy profiles
All camera types use the same lifecycle/state machine, but thresholds differ by profile:
- USB profile: low jitter, local capture, stricter stale thresholds.
- Mobile profile: higher jitter, network variability, longer stale grace.
- RTSP profile: medium jitter, network transport variability, reconnect-aware thresholds.
- Edge profile: push/bridge variability, explicit connectivity and frame freshness split.

### 3.2) Initial policy matrix
Use this matrix as the implementation baseline, then tune in Phase 0/1 from observed data:

| Camera Type | Liveness TTL (s) | Stale Grace (s) | Reconnect Cooldown (s) | Retry Cap | Notes |
| --- | --- | --- | --- | --- | --- |
| USB | 12 | 20 | 5 | 3 | Local capture, low jitter expected |
| Mobile | 20 | 45 | 10 | 5 | Network jitter and app backgrounding tolerance |
| RTSP | 18 | 35 | 8 | 5 | Transport variability and upstream source restarts |
| Edge | 20 | 40 | 10 | 5 | Bridge/push variability; separate connectivity freshness |

### 3.3) Editable acceptable ranges (admin-controlled)
Each policy profile must define editable bounds with hard safety rails:
- min/max allowed threshold values per setting,
- optional warn/critical bands for dashboard highlighting,
- scoped overrides at global, camera type, and single-camera level.

Required controls:
- only admin role can edit,
- all edits require reason text,
- every policy change is versioned and audit logged,
- fast revert to previous policy version.

### 4) Celery for recovery and periodic control tasks
Use Celery/Celery Beat for:
- periodic stale scans (control-plane checks),
- reconnect/recover workflows,
- delayed retries with backoff and jitter,
- reconciliation task to fix drift between worker-local and Redis state.

Do not send raw frames through Celery.

## Why This Works
Single-view vs multi-view discrepancy is usually caused by timing sensitivity. This architecture addresses timing races by:
- externalizing shared truth to Redis,
- making cleanup decisions state-aware (viewer + liveness),
- adding controlled camera-type-specific grace windows,
- decoupling recovery orchestration into Celery tasks.

## Implementation Path (Phased)

## Phase 0: Baseline and Instrumentation (1-2 days)
### Deliverables
- Add metrics/logging for:
  - `frame_gap_ms` per camera,
  - `frame_gap_ms` distribution per camera type,
  - `viewer_count` transitions,
  - stale candidate/marked events,
  - time-to-first-frame after viewer attach,
  - teardown reasons.
- Add correlation id per stream session request path.

### Exit Criteria
- Can reconstruct stream lifecycle timeline from logs for a given camera id.

## Phase 1: Redis Liveness + Viewer Counters (2-4 days)
### Deliverables
- On frame ingest: refresh liveness TTL key.
- On stream start/attach: increment viewer counter.
- On stream end/detach: decrement viewer counter safely.
- Add camera type to stream state metadata for profile-based policy resolution.
- Introduce atomic update helpers (Lua or transaction/locking strategy).

### Exit Criteria
- Viewer count remains accurate under concurrent multi-view open/close.
- Liveness reflects real frame activity.

## Phase 2: Dual-Condition Stale Cleanup (2-3 days)
### Deliverables
- Replace direct stale cleanup trigger with policy:
  - stale only if liveness expired AND viewer count permits teardown.
- Add configurable camera-type policy profiles (USB/mobile/RTSP/edge).
- Emit lifecycle events to Redis Streams.

### Exit Criteria
- No stale teardown while active viewers exist (except hard-failure override).

## Phase 3: Celery-Based Reconciliation and Recovery (2-4 days)
### Deliverables
- Celery beat periodic task:
  - reconcile worker-local state with Redis state.
- Recovery tasks:
  - delayed reconnect attempts,
  - cooldown handling to avoid connect thrashing,
  - bounded retries with jitter.

### Exit Criteria
- Reduced reconnect loops and reduced stale oscillation events.

## Phase 4: Operations Retention + Admin Console APIs (3-5 days)
### Deliverables
- Retain per-camera operational readings in analytics storage with retention policy.
- Provide read APIs for:
  - live per-camera status,
  - policy/range definitions,
  - historical readings and aggregates.
- Provide write APIs for admin policy/range updates with validation and audit trail.

### Exit Criteria
- Support can query historical readings for incidents without log scraping.
- Admin can update thresholds within approved ranges and see changes reflected live.

## Phase 5: Progressive Rollout + Guardrails (2-3 days)
### Deliverables
- Feature flags:
  - `STREAM_STATE_REDIS_ENABLED`
  - `STREAM_DUAL_CONDITION_STALE_ENABLED`
  - `STREAM_RECOVERY_CELERY_ENABLED`
  - `STREAM_OPERATIONS_RETENTION_ENABLED`
  - `STREAM_ADMIN_POLICY_EDIT_ENABLED`
- Progressive rollout by camera type risk and traffic:
  - usb canary,
  - mobile canary,
  - rtsp canary,
  - edge canary,
  - full mixed-type rollout.
- Dashboards/alerts for regressions.

### Exit Criteria
- Stable canary for agreed burn-in period.

## API Surface (Proposed)
### Live status and operations overview
- `GET /api/v1/cameras/operations/status`
  - Returns current state and latest operational readings for all streaming cameras.
  - Supports filters: camera type, site, status, stale risk.

### Policy and acceptable ranges
- `GET /api/v1/cameras/operations/policies`
  - Returns effective policies and allowed ranges by scope.
- `PATCH /api/v1/cameras/operations/policies/{scope}`
  - Updates policy values within allowed ranges.
  - Admin role only, reason required, audit event emitted.

### Support analytics
- `GET /api/v1/cameras/operations/analytics/readings`
  - Time-windowed raw/near-raw readings.
- `GET /api/v1/cameras/operations/analytics/aggregates`
  - Bucketed metrics (p50/p95 frame gap, reconnect rates, stale events, blank-rate proxy).
- `GET /api/v1/cameras/operations/analytics/incidents/{camera_id}`
  - Incident timeline view combining lifecycle events and policy changes.

## Data Model and State Machine (High-Level)
### States
- `DISCONNECTED`
- `CONNECTING`
- `CONNECTED_NO_VIEWERS`
- `CONNECTED_WITH_VIEWERS`
- `STALE_CANDIDATE`
- `STALE_DISCONNECTED`

### Core Transitions
- `frame_received` updates liveness and can promote to connected.
- `viewer_attached` moves to viewer-present state.
- Cleanup may only move to stale disconnected after dual-condition pass.
- New frame after stale candidate can auto-recover with guardrails.

## Operational Safeguards
1. Idempotent state transitions.
2. Counter floor at zero (never negative viewer count).
3. Backoff + jitter on reconnect tasks.
4. Dead-letter/error queue for repeated recovery failures.
5. Emergency kill switch via feature flags.
6. Policy edit guardrails (validation bounds + role checks + audit).

## Testing Strategy
### Unit tests
- Viewer counter atomicity.
- Liveness TTL refresh logic.
- Dual-condition stale policy function.

### Integration tests
- Single view stability for each type: USB/mobile/RTSP/edge.
- Multi-view mixed matrix: USB+mobile, USB+RTSP, mobile+RTSP+edge, all-four.
- Simulated ingestion jitter per type profile and temporary pauses.
- Admin policy update flow: valid updates, out-of-range rejection, rollback.
- Analytics endpoint correctness: raw vs aggregate consistency.

### Chaos/fault tests
- Redis transient disconnect.
- Worker restart during active viewers.
- Delayed frame bursts after stale candidate.

## Acceptance Criteria
1. Stream tile blank rate in multi-view reduced to near-zero for all four camera types under normal conditions.
2. No stale teardown while active viewers are present (verified by logs/metrics), regardless of camera type.
3. Recovery from temporary ingestion gaps without manual reconnect for each camera type according to profile SLO.
4. No significant latency regression in stream startup time by camera type.
5. Operations overview shows live status and key readings for all active streams.
6. Admin policy edits are range-validated, audited, and reversible.
7. Support analytics endpoints provide incident-grade historical data without direct log access.

## Rollout Gates (Per Camera Type)
1. Gate A (pre-canary):
  - Phase 0 metrics active and stable for 24h.
  - No unknown state transition reasons in logs.
2. Gate B (canary):
  - Blank tile rate <= 1% for that type over agreed sample window.
  - No teardown while viewers > 0.
3. Gate C (promotion):
  - Recovery success rate meets type SLO.
  - Startup latency does not regress beyond agreed threshold.
4. Gate D (mixed rollout):
  - Mixed-type matrix tests pass without new oscillation patterns.

## Risks and Mitigations
### Risk: Redis dependency increases blast radius
Mitigation:
- Fallback mode via feature flag.
- Local-safe defaults for temporary Redis unavailability.

### Risk: Counter drift due to abrupt client disconnects
Mitigation:
- Reconciliation task and periodic correction.
- Session TTL leases for viewers.

### Risk: Overly permissive grace delays true failure detection
Mitigation:
- Camera-type-specific thresholds.
- Alerting for long stale-with-viewers periods.

### Risk: One-size-fits-all defaults hurt specific camera types
Mitigation:
- Explicit profile configuration per type.
- Type-level dashboards and canary validation before broad rollout.

### Risk: Analytics retention cost grows too fast
Mitigation:
- tiered retention and downsampling,
- strict payload schema and cardinality limits,
- storage usage alerts.

### Risk: Unsafe admin edits degrade stream stability
Mitigation:
- enforce allowed ranges and step sizes,
- require reason and audit trail,
- one-click rollback to prior policy version.

## Rollback Plan
- Disable feature flags in reverse order:
  1) celery recovery,
  2) dual-condition cleanup,
  3) redis source-of-truth.
- Revert to existing local cleanup behavior if needed.

## Suggested Configuration Defaults (Initial)
- `stream_profile_usb_liveness_ttl_seconds`: 12
- `stream_profile_usb_stale_grace_seconds`: 20
- `stream_profile_mobile_liveness_ttl_seconds`: 20
- `stream_profile_mobile_stale_grace_seconds`: 45
- `stream_profile_rtsp_liveness_ttl_seconds`: 18
- `stream_profile_rtsp_stale_grace_seconds`: 35
- `stream_profile_edge_liveness_ttl_seconds`: 20
- `stream_profile_edge_stale_grace_seconds`: 40
- `post_viewer_attach_protection_seconds`: 15
- `reconcile_interval_seconds`: 10
- `reconnect_backoff_seconds`: exponential with jitter, capped at 30
- `operations_snapshot_interval_seconds`: 10
- `operations_raw_retention_hours`: 72
- `operations_aggregate_retention_days`: 30
- `policy_update_requires_reason`: true
- `policy_update_admin_roles`: `platform_admin, support_admin`

Note: values should be tuned from observed metrics in Phase 0.

## Open Decisions
1. Confirm the exact Redis schema format for `state` (`hash` vs serialized `json`) for operability and tooling.
2. Define hard-failure override conditions that can bypass viewer protection (for example, unrecoverable source errors).
3. Finalize per-type SLO targets for:
  - blank tile rate,
  - recovery success,
  - startup latency.
4. Decide retention window for Redis Streams lifecycle events to balance diagnostics with storage cost.

## Timeline Estimate
- Phase 0-1: 3-6 days
- Phase 2: 2-3 days
- Phase 3: 2-4 days
- Phase 4: 3-5 days
- Phase 5: 2-3 days

Total: 12-21 working days depending on test depth, retention scope, and rollout caution.

## Decision
Proceed with phased implementation, beginning with instrumentation and Redis-backed liveness/viewer state for all camera types, then introduce profile-driven dual-condition stale cleanup, Celery recovery orchestration, and operations retention/admin policy control behind feature flags.

## Companion Documents
- API schemas: `docs/proposals/cameras/camera-operations-api-schemas.md`
- Admin UI proposal: `docs/proposals/cameras/camera-operations-admin-overview-ui-proposal.md`
- Implementation breakdown: `docs/proposals/cameras/camera-operations-implementation-breakdown.md`
- Week-by-week tickets: `docs/proposals/cameras/camera-operations-implementation-tickets-week1-week5.md`
