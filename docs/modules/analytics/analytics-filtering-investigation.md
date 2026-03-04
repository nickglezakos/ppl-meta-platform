# Analytics Filtering Investigation (`http://localhost:3000/#/analytics`)

## Objective
Document:
1. Which endpoints provide data to the analytics screen.
2. How filtering is applied per endpoint.
3. A concrete test/debug scenario to pinpoint inconsistencies.

---

## 1) Analytics Data Sources and Endpoint Map

### Frontend orchestration (single page load)
The analytics screen triggers these calls in sequence from `_loadAnalytics()`:
- Summary metrics
- MVR quality metrics
- Time-series analytics
- Demographics analytics
- Behavioral analytics

Relevant frontend call sites:
- `ppl-meta-frontend/lib/screens/analytics_screen.dart` (calls at lines ~74, ~97, ~136, ~156, ~173)

### Endpoint inventory

1. **Camera list for filter UI**
   - Frontend client method: `getCamerasList()`
   - URL: `GET /api/v1/analytics/cameras`
   - Used for: populating filter checkbox list
   - Expected behavior: return stable IDs + display names

2. **Summary (Level 1 metrics)**
   - Frontend client method: `getAnalyticsSummary()`
   - URL: `GET /api/v1/analytics/summary`
   - Frontend currently sends: `collection_ids` (comma-separated)
   - Backend endpoint parameter is declared with alias `camera_ids`

3. **Time-series (Level 2)**
   - Frontend client method: `getTimeBasedAnalytics()`
   - URL: `GET /api/v1/analytics/time-series`
   - Frontend sends: `camera_ids`
   - Backend expects alias `camera_ids`

4. **Demographics (Level 3)**
   - Frontend client method: `getDemographicsBreakdown()`
   - URL: `GET /api/v1/analytics/demographics`
   - Frontend sends: `camera_ids`
   - Backend expects alias `camera_ids`

5. **Behavioral (Level 4)**
   - Frontend client method: `getBehavioralAnalytics()`
   - URL: `GET /api/v1/analytics/behavioral`
   - Frontend sends: `camera_ids`
   - Backend expects alias `camera_ids`

6. **MVR quality metrics (Level 1.5 card)**
   - Frontend client method: `getMvrQualityMetrics()`
   - URL: `GET /api/v1/analytics/mvr-quality-metrics`
   - Supports: `collection_name` (single value), not `camera_ids`
   - Current frontend call uses `collectionName: null` (always unfiltered)

---

## 2) How Filtering Works Today (Per Endpoint)

## Filter selection in UI
- Filter dialog stores selected collection IDs in `_selectedCollectionIds`.
- Recent change in UI uses UUID-first ID extraction:
  - `id = camera['uuid'] ?? camera['id'] ?? ...`
- Display labels still use camera/collection names.

This is correct UI behavior: **ID for filtering, name for display**.

## Backend matching behavior
Gateway analytics now includes helper functions for UUID-first matching:
- `_get_collection_identifier(...)`
- `_get_collection_filter_keys(...)`
- `_collection_matches_selected_ids(...)`

These normalize matching across UUID/name/device ID variants.

## Critical inconsistency points

### A) Summary endpoint parameter mismatch
- Frontend sends `collection_ids` in `getAnalyticsSummary()`.
- Backend expects alias `camera_ids` in `get_analytics_summary(...)`.
- Result: summary filtering can be ignored (or behave differently), while other panels filter correctly.

### B) MVR quality card is always global
- Frontend calls `getMvrQualityMetrics(..., collectionName: null)`.
- So this card does not follow selected camera filters at all.
- Result: quality card may disagree with other filtered panels.

### C) Mixed semantics across endpoints
- Most analytics endpoints are multi-select via `camera_ids`.
- `mvr-quality-metrics` is single `collection_name` based.
- Result: filtering contract is inconsistent by design unless adapted in frontend/backend.

### D) Behavioral internal dependency caveat
- Behavioral flow still depends on fields like `camera_device_id` and `uuid` for deeper lookups.
- If collections match filter but miss required internal fields, they can be skipped, causing partial results.

---

## 3) Test & Debug Scenario (to Pinpoint Inconsistencies)

## Phase 0: Preconditions
1. Ensure gateway/media/vmeta services are running.
2. Use one user with known data in at least 2 collections.
3. Pick two collections from `/analytics/cameras` response:
   - `A`: active collection with data
   - `B`: another active collection with data

## Phase 1: Capture source-of-truth IDs
1. Call `GET /api/v1/analytics/cameras`.
2. Record per collection:
   - `id`
   - `uuid`
   - `name`
   - `collection_name`
3. Confirm selected filter IDs in UI match these IDs (prefer UUID).

## Phase 2: Endpoint-level filter verification (manual API)
For each endpoint below, run with:
- No filter
- `camera_ids=<A>`
- `camera_ids=<B>`
- `camera_ids=<A>,<B>`

Endpoints:
- `/api/v1/analytics/summary`
- `/api/v1/analytics/time-series`
- `/api/v1/analytics/demographics`
- `/api/v1/analytics/behavioral`
- `/api/v1/analytics/quality-metrics`

Expected invariant:
- `A+B` should be approximately the aggregate of `A` and `B` (for additive metrics).
- Single-filter responses should differ from no-filter when data differs per camera.

### Special check for summary mismatch
Also test:
- `/api/v1/analytics/summary?collection_ids=<A>`
- `/api/v1/analytics/summary?camera_ids=<A>`

If these produce different results, parameter mismatch is confirmed.

## Phase 3: UI network verification
In browser devtools (Network tab) while using analytics filters:
1. Select only collection `A`.
2. Apply filters.
3. Verify outgoing query params per call:
   - Summary currently uses `collection_ids` (problematic)
   - Others use `camera_ids`
4. Verify quality call sends `collection_name` (it currently sends none).

## Phase 4: Correlate backend logs
Enable/inspect gateway logs around analytics endpoints:
- Log parsed incoming params (`camera_ids`, `collection_ids`, `collection_name`).
- Log matched collection IDs after filtering.
- Log skipped collections with reason (missing uuid/device_id/etc).

Primary evidence to capture:
- Requested IDs
- Matched IDs
- Processed IDs
- Final counts per endpoint

## Phase 5: Consistency matrix
Build a quick table after test run:

| Endpoint | Filter Param Seen | Matched IDs | Data Returned | Consistent with selected A/B? |
|---|---|---|---|---|
| summary | ? | ? | ? | yes/no |
| time-series | ? | ? | ? | yes/no |
| demographics | ? | ? | ? | yes/no |
| behavioral | ? | ? | ? | yes/no |
| mvr-quality-metrics | ? | ? | ? | yes/no |

This pinpoints exactly which endpoint(s) diverge.

---

## 4) Likely Root Causes (from current code)

1. **Summary request param mismatch** (`collection_ids` vs `camera_ids`).
2. **Quality card not connected to selected filters** (`collectionName: null`).
3. **Endpoint contract mismatch** (multi-select `camera_ids` vs single `collection_name`).
4. **Field availability differences** (`uuid`/`camera_device_id`) leading to partial processing.

---

## 5) Recommended Debug-First Fix Order

1. Fix summary to send `camera_ids` from frontend and verify parity.
2. Decide quality-filter contract:
   - Option A: support `camera_ids` in `mvr-quality-metrics`.
   - Option B: map selected single camera UUID -> `collection_name` when one selected.
3. Add temporary structured logs in gateway for filter resolution.
4. Re-run consistency matrix and confirm deterministic behavior.

---

## 6) Files Reviewed
- `ppl-meta-frontend/lib/screens/analytics_screen.dart`
- `ppl-meta-frontend/lib/services/media_api_client.dart`
- `ppl-meta-frontend/lib/services/analytics_api_client.dart`
- `ppl-meta-gateway/src/api/v1/analytics.py`

---

## Note
This document is focused on investigation and reproducibility first, so inconsistencies can be proven endpoint-by-endpoint before applying additional fixes.
