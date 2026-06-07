# Camera Operations Implementation Tickets (Week 1 to Week 5)

## Purpose
Convert the approved proposal set into execution tickets grouped by milestone week, with suggested assignees per service and clear completion criteria.

## Assignee Mapping (Suggested)
- `ppl-meta-cameras`: Cameras Service Maintainer
- `workers` (Celery/Celery Beat): Workers Service Maintainer
- `ppl-meta-authority`: Authority Service Maintainer
- API layer (gateway/orchestrator): API Platform Maintainer
- Analytics storage module: Data Platform Maintainer
- `ppl-meta-frontend`: Frontend Service Maintainer
- Observability and rollout: Platform SRE Maintainer

Note: replace role-based assignees with named owners in sprint planning.

## Ticket Template (Use For Tracking)
- ID
- Title
- Service
- Suggested Assignee
- Dependencies
- Scope
- Acceptance Criteria
- Estimate (days)

## Week 1: Control-Plane Baseline

### TKT-CAM-001
- Title: Introduce normalized stream state object with camera type profile
- Service: `ppl-meta-cameras`
- Suggested Assignee: Cameras Service Maintainer
- Dependencies: none
- Scope:
  - Add canonical stream state model.
  - Include camera type, profile, transition reason, and updated timestamp.
- Acceptance Criteria:
  - Stream state serialized consistently in all state transitions.
  - Unit tests cover all enum states and reason values.
- Estimate (days): 1.5

### TKT-CAM-002
- Title: Add Redis liveness TTL and viewer counter primitives
- Service: `ppl-meta-cameras`
- Suggested Assignee: Cameras Service Maintainer
- Dependencies: TKT-CAM-001
- Scope:
  - Implement liveness key updates on frame ingest.
  - Implement attach/detach viewer counter updates.
  - Ensure counter floor remains zero.
- Acceptance Criteria:
  - Viewer counts remain correct under concurrent attach/detach test.
  - Liveness TTL reflects active ingest path.
- Estimate (days): 2

### TKT-CAM-003
- Title: Add lifecycle event emission to Redis Streams
- Service: `ppl-meta-cameras`
- Suggested Assignee: Cameras Service Maintainer
- Dependencies: TKT-CAM-001, TKT-CAM-002
- Scope:
  - Emit lifecycle events (`frame_received`, `viewer_attached`, `stale_candidate`, etc.).
  - Add request/correlation id propagation.
- Acceptance Criteria:
  - Event stream contains complete ordered transitions for a sample camera session.
- Estimate (days): 1

### TKT-SRE-001
- Title: Baseline dashboard and alert skeleton for stream lifecycle metrics
- Service: observability
- Suggested Assignee: Platform SRE Maintainer
- Dependencies: TKT-CAM-003
- Scope:
  - Create initial dashboard panels for frame gap, viewer counts, stale events.
  - Add placeholder alerts with muted severity for baseline period.
- Acceptance Criteria:
  - Dashboard visible in target environment and populated by live metrics.
- Estimate (days): 1

## Week 2: Stable Cleanup and Recovery

### TKT-CAM-004
- Title: Implement dual-condition stale cleanup policy
- Service: `ppl-meta-cameras`
- Suggested Assignee: Cameras Service Maintainer
- Dependencies: TKT-CAM-002, TKT-CAM-003
- Scope:
  - Enforce stale cleanup only when liveness is expired and viewer condition permits.
  - Add hard-failure override with explicit reason.
- Acceptance Criteria:
  - No stale teardown when active viewers are present in integration tests.
  - Override path produces explicit audit-friendly reason.
- Estimate (days): 2

### TKT-CAM-005
- Title: Add camera-type policy profiles and bounds loading
- Service: `ppl-meta-cameras`
- Suggested Assignee: Cameras Service Maintainer
- Dependencies: TKT-CAM-004
- Scope:
  - Load and apply USB/mobile/RTSP/edge profile values.
  - Validate policy values against allowed bounds.
- Acceptance Criteria:
  - Type-specific values are applied at runtime.
  - Out-of-bound values are rejected with deterministic errors.
- Estimate (days): 1.5

### TKT-WRK-001
- Title: Implement reconciliation periodic task
- Service: `workers`
- Suggested Assignee: Workers Service Maintainer
- Dependencies: TKT-CAM-002, TKT-CAM-003
- Scope:
  - Compare local process state vs Redis state and repair drift.
  - Emit reconciliation result events.
- Acceptance Criteria:
  - Drift scenarios are detected and corrected in test harness.
- Estimate (days): 1.5

### TKT-WRK-002
- Title: Implement recovery workflow with backoff and jitter
- Service: `workers`
- Suggested Assignee: Workers Service Maintainer
- Dependencies: TKT-WRK-001, TKT-CAM-005
- Scope:
  - Add bounded retries and reconnect cooldown behavior.
  - Add dead-letter behavior after retry cap.
- Acceptance Criteria:
  - Recovery attempts stop at configured cap and emit failure events.
- Estimate (days): 1.5

## Week 3: Operations APIs and Retention

### TKT-API-001
- Title: Implement GET operations status endpoint
- Service: API layer (gateway/orchestrator)
- Suggested Assignee: API Platform Maintainer
- Dependencies: TKT-CAM-005
- Scope:
  - Implement `GET /api/v1/cameras/operations/status`.
  - Add filtering, sorting, and cursor pagination.
- Acceptance Criteria:
  - Endpoint returns live operational status with bounded latency.
- Estimate (days): 1.5

### TKT-DAT-001
- Title: Create analytics storage schema for raw and aggregate readings
- Service: analytics storage
- Suggested Assignee: Data Platform Maintainer
- Dependencies: TKT-CAM-003
- Scope:
  - Define schema for raw readings, aggregates, and linkage keys.
  - Implement retention and compaction policy.
- Acceptance Criteria:
  - Raw and aggregate retention works according to configured windows.
- Estimate (days): 2

### TKT-WRK-003
- Title: Implement snapshot and downsampling jobs
- Service: `workers`
- Suggested Assignee: Workers Service Maintainer
- Dependencies: TKT-DAT-001
- Scope:
  - Periodic snapshot job for readings.
  - Downsampling jobs for older windows.
- Acceptance Criteria:
  - Snapshot cadence and downsampling outputs match expected counts.
- Estimate (days): 1.5

### TKT-API-002
- Title: Implement analytics readings and aggregates endpoints
- Service: API layer (gateway/orchestrator)
- Suggested Assignee: API Platform Maintainer
- Dependencies: TKT-DAT-001, TKT-WRK-003
- Scope:
  - Implement `GET /analytics/readings` and `GET /analytics/aggregates`.
  - Enforce max time-window and response size limits.
- Acceptance Criteria:
  - Endpoints satisfy schema contract with correct aggregation behavior.
- Estimate (days): 2

## Week 4: RBAC, Audit, and Admin UI

### TKT-AUTH-001
- Title: Add camera operations permissions and role mapping
- Service: `ppl-meta-authority`
- Suggested Assignee: Authority Service Maintainer
- Dependencies: none
- Scope:
  - Add `camera_operations.read`, `camera_operations.write`, `camera_operations.rollback`.
  - Map permissions to platform and support roles.
- Acceptance Criteria:
  - Token claims enforce read/write boundaries correctly.
- Estimate (days): 1

### TKT-API-003
- Title: Implement policy read and write endpoints with validation
- Service: API layer (gateway/orchestrator)
- Suggested Assignee: API Platform Maintainer
- Dependencies: TKT-AUTH-001, TKT-CAM-005
- Scope:
  - Implement `GET /policies` and `PATCH /policies/{scope_type}/{scope_id}`.
  - Add optimistic concurrency and range validation.
- Acceptance Criteria:
  - Invalid edits are rejected with structured validation errors.
  - Concurrent update conflicts are handled deterministically.
- Estimate (days): 2

### TKT-API-004
- Title: Implement incident timeline endpoint with policy-change correlation
- Service: API layer (gateway/orchestrator)
- Suggested Assignee: API Platform Maintainer
- Dependencies: TKT-API-003, TKT-CAM-003, TKT-DAT-001
- Scope:
  - Implement `GET /analytics/incidents/{camera_id}`.
  - Join lifecycle events with policy change events.
- Acceptance Criteria:
  - Timeline includes ordered lifecycle and policy events for selected window.
- Estimate (days): 1.5

### TKT-FE-001
- Title: Build operations overview page (read-only baseline)
- Service: `ppl-meta-frontend`
- Suggested Assignee: Frontend Service Maintainer
- Dependencies: TKT-API-001, TKT-API-002
- Scope:
  - KPI row, operations table, filters, severity/state views.
- Acceptance Criteria:
  - Support read-only users can inspect live status and filter quickly.
- Estimate (days): 2

### TKT-FE-002
- Title: Build policy editor drawer with role-aware controls
- Service: `ppl-meta-frontend`
- Suggested Assignee: Frontend Service Maintainer
- Dependencies: TKT-FE-001, TKT-API-003
- Scope:
  - Edit form, range validation, reason capture, submit and rollback hooks.
- Acceptance Criteria:
  - Out-of-range values blocked in UI.
  - Edit controls hidden for read-only users.
- Estimate (days): 1.5

### TKT-FE-003
- Title: Build incident timeline panel with metric overlays
- Service: `ppl-meta-frontend`
- Suggested Assignee: Frontend Service Maintainer
- Dependencies: TKT-API-004
- Scope:
  - Timeline feed and chart overlays for selected camera/time window.
- Acceptance Criteria:
  - Support users can correlate policy edits and lifecycle incidents visually.
- Estimate (days): 1.5

## Week 5: E2E Validation and Progressive Rollout

### TKT-QA-001
- Title: End-to-end test matrix for mixed camera types
- Service: test platform (cross-service)
- Suggested Assignee: Cameras Service Maintainer
- Dependencies: Week 1 to Week 4 completion
- Scope:
  - Validate USB/mobile/RTSP/edge single and mixed scenarios.
  - Validate policy updates and runtime effects.
- Acceptance Criteria:
  - All critical scenario tests pass in staging.
- Estimate (days): 2

### TKT-SRE-002
- Title: Progressive rollout execution with gates and rollback checks
- Service: observability and operations
- Suggested Assignee: Platform SRE Maintainer
- Dependencies: TKT-QA-001
- Scope:
  - Rollout order: USB -> Mobile -> RTSP -> Edge -> mixed full.
  - Verify gate thresholds at each step.
  - Run rollback drill once before full rollout.
- Acceptance Criteria:
  - All rollout gates passed with no unresolved critical regressions.
- Estimate (days): 2

### TKT-OPS-001
- Title: Support playbook and handoff for operations screen and analytics APIs
- Service: cross-service enablement
- Suggested Assignee: API Platform Maintainer
- Dependencies: TKT-FE-003, TKT-API-004
- Scope:
  - Produce support runbook for triage and policy tuning.
  - Include query examples and known failure signatures.
- Acceptance Criteria:
  - Support team can complete incident triage without direct log scraping for standard cases.
- Estimate (days): 1

## Program-Level Exit Criteria
1. Multi-stream blank tile rate remains within agreed SLO across all camera types.
2. No stale teardown while active viewers are present unless hard-failure override is triggered.
3. Admin policy edits are range-validated, audited, and reversible.
4. Support can use operations UI and analytics APIs for incident triage without direct log access in normal cases.
5. Rollout completes with gate compliance and documented rollback readiness.

## Suggested Epic Grouping
- EPIC-1: Stream state and lifecycle hardening (Week 1-2)
- EPIC-2: Operations data and analytics APIs (Week 3)
- EPIC-3: RBAC, audit, and admin controls (Week 4)
- EPIC-4: Validation, rollout, and support enablement (Week 5)