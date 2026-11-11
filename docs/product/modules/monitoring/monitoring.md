# Monitoring Dashboard

**Route:** `/workflows`  
**Screen:** `WorkflowDashboardScreen`  
**Main Widget:** `MonitoringSummaryWidget`

## Overview

The Monitoring Dashboard provides a real-time overview of system health, workflow metrics, and MVR activity. Data is fetched from:
- **Orchestrator service** at `/api/v1/monitoring/summary` — system health + face detection metrics (Redis-cached, 60s TTL)
- **Orchestrator service** at `/api/v1/monitoring/charts` — time-series chart data (Redis-cached, 60s TTL)
- **vmeta service** at `/api/v1/mvr-people/stats/daily` — MVR activity totals and daily breakdowns (called by orchestrator internally)

The dashboard supports manual refresh via the header refresh button. All data is cached on the backend for 60 seconds to minimize API load.

---

## Current Layout

### 1. System Health Card

| Element | Description |
|---------|-------------|
| Health status badge | `HEALTHY` / `DEGRADED` / `UNHEALTHY` (green / orange / red) |
| Health message | Text summary of overall system state |
| Stuck workflows warning | Badge shown when workflows are stuck (processing > 2 hours) |
| Recent failures count | Badge shown when failures detected in the last hour |

**Data source:** Orchestrator DB — `WorkflowExecution` table

### 2. Face Detection (Low-Level Workflows)

| Metric | Type | Source |
|--------|------|--------|
| Active Sessions | Count | `WorkflowExecution` rows with status `queued` or `processing` |
| Completed (Total) | Count | `WorkflowExecution` rows with status `completed` |
| Completed (24h) | Count | `MethodLifecycle` rows completed in last 24h |
| Avg Processing Time | Seconds | Average `completed_at - started_at` from `MethodLifecycle` (24h) |
| Success Rate (24h) | Percentage | `completed / (completed + failed)` from `MethodLifecycle` (24h) |

**Data source:** Orchestrator DB — `WorkflowExecution` and `MethodLifecycle` tables

### 3. MVR & Tracking (High-Level Workflows)

| Metric | Type | Source |
|--------|------|--------|
| Active MVR People | Count | Non-orphaned, non-merged `mvr_people` rows |
| MVR Created (Today) | Count | `mvr_people.created_at` for today |
| Cross-Video Matches (Today) | Count | Sum of today's merges + individual-MVR mappings |
| Total Merges (7d) | Count | `mvr_merge_hierarchy.merge_timestamp` over last 7 days |
| Total Mappings (7d) | Count | `individual_mvr_mapping.linked_at` over last 7 days |

**Data source:** vmeta DB — queried via `GET /api/v1/mvr-people/stats/daily` (called by orchestrator over HTTP, 5s timeout, graceful fallback to zeros)

---

## Charts (Analytics Section)

All charts are rendered using `fl_chart` and appear below the metric cards under an "Analytics" heading. Data is fetched from `/api/v1/monitoring/charts`.

### Detection Throughput (24h)
- **Type:** Line chart with filled area
- **X-axis:** Hour (last 24h)
- **Y-axis:** Completed detections per hour
- **Source:** `MethodLifecycle` — hourly count of `completed` rows
- **Tooltip:** Shows time and detection count

### Success Rate Trend (7d)
- **Type:** Line chart with dots
- **X-axis:** Date (last 7 days)
- **Y-axis:** Success rate (0–100%)
- **Source:** `MethodLifecycle` — daily completed vs failed ratio
- **Tooltip:** Shows date, rate percentage, and completed/total counts

### Active Sessions (24h)
- **Type:** Area chart
- **X-axis:** Hour (last 24h)
- **Y-axis:** Workflows created per hour
- **Source:** `WorkflowExecution.created_at` — hourly counts
- **Tooltip:** Shows time and session count

### Processing Time Distribution
- **Type:** Color-coded bar chart
- **X-axis:** Time buckets (`<1s`, `1-5s`, `5-15s`, `15-30s`, `30-60s`, `>60s`)
- **Y-axis:** Number of workflows
- **Source:** `MethodLifecycle` — `completed_at - started_at` bucketed (last 24h)
- **Colors:** Green (fast) → Red (slow)
- **Tooltip:** Shows bucket label and workflow count

### MVR Activity (7d)
- **Type:** Grouped bar chart (two bars per day)
- **X-axis:** Date (last 7 days)
- **Y-axis:** Activity count
- **Bars:** Cyan = merges + individual links, Blue = MVR people created
- **Source:** vmeta DB via `/api/v1/mvr-people/stats/daily`
- **Tooltip:** Shows breakdown of merges, links, or MVR created per day
- **Empty state:** "No MVR activity in the last 7 days"

---

## Architecture

```
Frontend (Flutter)
  │
  ├── GET /api/v1/monitoring/summary ──→ Orchestrator
  │     ├── Queries WorkflowExecution + MethodLifecycle (local DB)
  │     └── Calls vmeta /api/v1/mvr-people/stats/daily (HTTP, 5s timeout)
  │
  └── GET /api/v1/monitoring/charts ──→ Orchestrator
        ├── Queries WorkflowExecution + MethodLifecycle (local DB)
        └── Calls vmeta /api/v1/mvr-people/stats/daily (HTTP, 5s timeout)
```

Both endpoints use Redis caching (60s TTL). If vmeta is unreachable, MVR metrics gracefully fall back to zeros.

---

## Related Components

| Component | Location |
|-----------|----------|
| `MonitoringSummaryWidget` | `ppl-meta-frontend/lib/widgets/workflow/monitoring_summary_widget.dart` |
| `MonitoringChartsWidget` | `ppl-meta-frontend/lib/widgets/workflow/monitoring_charts_widget.dart` |
| `HealthMonitoringWidget` | `ppl-meta-frontend/lib/widgets/workflow/health_monitoring_widget.dart` |
| `WorkflowDashboardScreen` | `ppl-meta-frontend/lib/screens/workflow_dashboard_screen.dart` |
| Monitoring providers | `ppl-meta-frontend/lib/providers/monitoring_providers.dart` |
| Backend endpoint (orchestrator) | `ppl-meta-orchestrator/src/api/monitoring_endpoints.py` |
| MVR stats endpoint (vmeta) | `ppl-meta-vmeta/src/api/routes/mvr_people.py` |

> **Note:** The separate Analytics Dashboard (`analytics_dashboard.dart`) has functional `fl_chart` graphs for media upload analytics — those are not part of this monitoring screen.
