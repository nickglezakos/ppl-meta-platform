# Camera Operations Implementation Breakdown

## Purpose
Provide an execution-ready work breakdown by service to deliver stream stability, operations retention, admin controls, and support analytics.

Companion execution tickets:
- `docs/proposals/cameras/camera-operations-implementation-tickets-week1-week5.md`

## Scope
- Camera stream lifecycle control-plane hardening
- Operations readings retention
- Admin policy management with guardrails
- Support analytics API surface
- Admin overview frontend

## Delivery Tracks
- Track A: Backend control-plane and retention
- Track B: Authorization and audit
- Track C: API and analytics
- Track D: Frontend operations overview
- Track E: SRE rollout and guardrails

## Service Breakdown

## 1) ppl-meta-cameras (Core Owner)
### Work Packages
1. Stream state model
- Add normalized stream state object with camera type and policy profile.
- Add transition reason taxonomy.

2. Redis integration
- Liveness TTL keys
- Viewer counters
- State hash/json
- Redis Streams lifecycle events

3. Dual-condition stale policy
- Require liveness expired and viewer criteria
- Apply profile policy by camera type
- Add hard-failure override pathway

4. Reconciliation hooks
- Expose reconciliation interfaces consumed by Celery worker tasks.

5. Metrics and logging
- frame gap, read failures, reconnects, stale candidates, transition causes.

### Acceptance
- No stale teardown with active viewers unless hard failure.
- Accurate viewer counts under attach/detach storms.

## 2) workers (Celery / Celery Beat Owner)
### Work Packages
1. Periodic reconciliation task
- Compare local and Redis state.
- Repair drift and emit events.

2. Recovery workflow tasks
- bounded retries with jitter
- cooldown handling
- dead-letter on repeated failures

3. Retention pipeline tasking
- periodic snapshots to analytics store
- downsampling jobs for older data

### Acceptance
- Reduced reconnect thrashing.
- Bounded task retries with traceable outcomes.

## 3) ppl-meta-authority (RBAC Owner)
### Work Packages
1. Define permissions
- `camera_operations.read`
- `camera_operations.write`
- `camera_operations.rollback`

2. Role mapping
- platform_admin -> full
- support_admin -> read/write (scoped)
- support_readonly -> read

3. Token claims and middleware checks
- Ensure all operations endpoints enforce role permissions.

### Acceptance
- Unauthorized policy writes are blocked.
- Read-only roles cannot access edit endpoints.

## 4) Shared API layer (Gateway/Orchestrator as applicable)
### Work Packages
1. Endpoint contracts
- implement status, policy, readings, aggregates, incident timeline

2. Validation and concurrency
- range validation
- optimistic concurrency with `if_version`

3. Error model
- standardized error envelope with request id

4. Rate and payload controls
- max time-window and row limits per endpoint

### Acceptance
- Contract compliance with schema document.
- Stable endpoint latency under expected support query load.

## 5) Analytics Storage Module (Existing stack integration)
### Work Packages
1. Schema design
- raw readings table/series
- aggregate buckets
- lifecycle event linkage

2. Retention policy
- raw short-term retention
- aggregate long-term retention
- TTL and compaction/downsampling

3. Query adapters
- efficient range queries by camera, type, site

### Acceptance
- Support can retrieve incident windows without log scraping.
- Storage growth remains within defined budget.

## 6) ppl-meta-frontend (Admin Overview Owner)
### Work Packages
1. Operations page
- KPI row + operations table + filters + saved views

2. Policy drawer
- editable fields with range validation
- reason capture
- optimistic concurrency handling

3. Incident timeline
- event feed with metric overlays

4. Role-sensitive UI
- hide/disable editing controls by role

### Acceptance
- Read-only and write roles behave correctly.
- Policy edit UX blocks invalid values before submit.

## 7) Observability and SRE
### Work Packages
1. Dashboards
- by camera type, site, state, severity

2. Alerts
- stale teardown with viewers > 0
- reconnect storm thresholds
- analytics pipeline lag

3. Feature flags and rollout controls
- per-phase toggles
- type-by-type progressive rollout

### Acceptance
- Clear rollback path and detection of regressions.

## Cross-Service Contracts
1. Camera type enum must be identical across services.
2. Stream state names and transition reasons must be centralized.
3. Policy key names must stay stable for API and UI compatibility.
4. Audit event schema must be shared between authority, API, and storage layers.

## Suggested Milestones

## Milestone 1: Control-Plane Baseline (Week 1)
- Cameras state model + Redis liveness/viewer counters
- Instrumentation and transition reason coverage

## Milestone 2: Stable Cleanup + Recovery (Week 2)
- Dual-condition stale policy
- Celery reconciliation and recovery tasks

## Milestone 3: Operations APIs + Storage (Week 3)
- Status and analytics endpoints
- retention and downsampling jobs

## Milestone 4: Admin UI + RBAC + Audit (Week 4)
- Operations overview page
- policy editor + audit trail
- role enforcement end-to-end

## Milestone 5: Progressive Rollout (Week 5)
- usb -> mobile -> rtsp -> edge -> mixed full rollout
- support playbook handoff

## Testing Plan by Layer
1. Unit tests
- policy validation, range enforcement, transitions

2. Integration tests
- camera mixed-type multi-view scenarios
- API contract tests against schema examples

3. End-to-end tests
- admin policy edit from UI to runtime effect
- incident timeline consistency after policy changes

4. Fault tests
- Redis outage mode
- worker restarts
- analytics store lag and recovery

## Operational Runbooks
1. Incident triage runbook
- identify impacted camera set
- inspect timeline
- compare policy version before/after incident

2. Safe policy tuning runbook
- apply small changes
- monitor gate metrics
- rollback if adverse signal appears

3. Rollback runbook
- feature flags reverse disable order
- verify stable fallback behavior

## Dependencies and Order
1. Cameras state model and Redis keys first.
2. Celery reconciliation second.
3. API endpoints and storage third.
4. RBAC and audit integration fourth.
5. Frontend editing enablement after backend safety checks.

## Exit Definition for Program Completion
- All acceptance criteria in primary proposal are satisfied.
- Support team can resolve incidents without direct log access in normal cases.
- Admin policy edits are safe, auditable, and reversible.
- Multi-camera-type rollout is stable for agreed burn-in period.
