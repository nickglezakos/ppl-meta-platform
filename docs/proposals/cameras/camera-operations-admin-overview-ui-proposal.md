# Camera Operations Admin Overview UI Proposal

## Purpose
Define a dedicated admin/support screen to monitor camera stream operations, edit policy ranges safely, and troubleshoot incidents without raw log access.

## Users
- Platform admins
- Support admins
- Support read-only users

## Primary Outcomes
- Rapidly identify unhealthy cameras and patterns by type/site/state.
- Safely tune policy thresholds with guardrails and audit.
- Build incident timelines that correlate lifecycle events with policy changes.

## Information Architecture

## 1) Global Header
- Time range selector (`15m`, `1h`, `6h`, `24h`, custom).
- Environment selector (`local`, `staging`, `production`).
- Site selector.
- Refresh mode (`live`, `manual`).

## 2) KPI Row
- Total streaming cameras.
- Cameras in warn and critical state.
- Blank-rate proxy.
- Recovery success rate.
- Startup latency p95.

## 3) Camera Operations Table (Primary Surface)
Columns:
- camera name
- camera id
- type
- site
- stream state
- severity
- active viewers
- frame gap
- effective fps
- reconnect attempts (15m)
- stale candidates (15m)
- effective policy profile
- last update time

Actions:
- open incident timeline
- open policy drawer (if write role)
- jump to camera details

Table behavior:
- sortable columns
- multi-filter by type/state/severity
- saved views (for support playbooks)
- cursor pagination with sticky filters

## 4) Policy Drawer (Right Panel)
For selected scope (global, type, camera):
- current effective values
- editable ranges with min/max/step
- warn thresholds visualized inline
- change form with required reason
- impact preview:
  - impacted camera count
  - expected sensitivity shift (strict/relaxed)

Write flow:
1. edit value
2. validation in UI before submit
3. submit with reason
4. success toast with new policy version
5. optional rollback action

## 5) Incident Timeline Panel
For a selected camera and time window:
- lifecycle events stream
- policy changes stream
- key readings overlay (frame gap, viewers, reconnects)
- annotations for stale candidate/disconnect/recovered transitions

## Role-Based UX
- `support_readonly`: no edit controls, view-only timeline and analytics.
- `support_admin`: edit controls available, guarded by reason + validation.
- `platform_admin`: full scope editing (global/type/camera) and rollback.

## UX Safety Requirements
- Disable save when changes are outside allowed ranges.
- Show explicit red warning for critical-range edits.
- Require reason text with minimum length.
- Show optimistic concurrency conflict if version changed server-side.
- Show exact backend validation message on rejection.

## Visual Status Language
- `ok`: green
- `warn`: amber
- `critical`: red

States should include text labels and not rely on color alone.

## API Mapping
- Table + KPI: `GET /api/v1/cameras/operations/status`
- Policy drawer load: `GET /api/v1/cameras/operations/policies`
- Policy save: `PATCH /api/v1/cameras/operations/policies/{scope_type}/{scope_id}`
- Timeline + charts: `GET /api/v1/cameras/operations/analytics/readings`
- Trend cards: `GET /api/v1/cameras/operations/analytics/aggregates`
- Incident drilldown: `GET /api/v1/cameras/operations/analytics/incidents/{camera_id}`

## Frontend State Model
- Query state:
  - filters, sort, pagination cursor, time range.
- Live status cache:
  - short TTL cache with soft refresh.
- Editor state:
  - baseline version, dirty fields, validation results, submit status.
- Timeline state:
  - selected camera, time window, metric overlays.

## Performance Targets
- Initial table render under 2 seconds for 200 cameras.
- Filter/sort response under 500 ms after data load.
- Policy drawer open under 300 ms with cached policy set.
- Timeline query under 2 seconds for 24h window at 1m resolution.

## Accessibility Requirements
- Full keyboard navigation for table and drawer.
- Proper focus management for drawer and modal confirmations.
- Contrast ratio at least WCAG AA for status indicators.
- Screen-reader labels for all critical metrics and action buttons.

## Rollout Plan
1. Release read-only status page to support group.
2. Enable timeline panel for support admins.
3. Enable policy editing for platform admins only.
4. Expand editing to support admins after burn-in.

## Success Metrics
- Reduction in time-to-triage incidents.
- Reduction in manual log-scraping incidents.
- Policy change rollback rate (should trend down over time).
- Decrease in blank-tile incidents after controlled policy tuning.

## Open Questions
1. Should per-camera policy edits be time-limited overrides with auto-expiry?
2. Should we require dual approval for global policy edits in production?
3. Should incident timeline export be CSV, JSON, or both?
