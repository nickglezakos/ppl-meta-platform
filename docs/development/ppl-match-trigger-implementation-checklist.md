# PPL Match Trigger Implementation Checklist

## Scope
Implement `ppl-match` trigger mode that:
- compares the source MVR object from trigger evaluation context against MVR members of a configured Individual Group,
- fires only when similarity threshold is met,
- persists match metadata for audit, actions, and UI.

## Engineering Tasks

### 1) Data & Schema
- [ ] Add trigger config fields:
  - [ ] `trigger_mode` (`demographic`, `ppl_match`)
  - [ ] `match_group_id`
  - [ ] `match_similarity_threshold`
  - [ ] `match_top_k`
- [ ] Add/extend trigger execution log table with match columns:
  - [ ] `source_mvr_uuid`, `matched_group_id`, `matched_member_uuid`
  - [ ] `similarity_score`, `threshold`, `match_details_json`, `evaluated_at`, `passed`
- [ ] Add migration defaults for existing triggers (`trigger_mode=demographic`).

### 2) API Contracts
- [ ] Extend trigger create/update/list/get schemas for ppl-match fields.
- [ ] Extend evaluation response schema with optional `match` object.
- [ ] Ensure action payload contract includes `match` block when present.
- [ ] Add validation rules:
  - [ ] `match_group_id` required when `trigger_mode=ppl_match`
  - [ ] threshold range check (0..1)
  - [ ] `match_top_k >= 1`

### 3) Evaluation Engine
- [ ] Add ppl-match evaluator branch in trigger evaluation pipeline.
- [ ] Resolve source MVR UUID from current event context.
- [ ] Fetch candidate member embeddings for configured group.
- [ ] Compute similarity scores and select top-K.
- [ ] Apply threshold, cooldown, and time-span checks.
- [ ] Persist evaluation result + match details.
- [ ] Pass enriched context to action dispatcher.

### 4) Performance Design
- [ ] Implement two-level cache:
  - [ ] in-memory cache (per instance)
  - [ ] Redis cache (shared)
- [ ] Cache key format: `ppl_match:group:{group_id}:v{embedding_version}`.
- [ ] Add invalidation hooks on:
  - [ ] group membership changes
  - [ ] merge operations
  - [ ] embedding updates / model version changes
- [ ] Add TTL fallback (e.g., 5-15 minutes).
- [ ] Bound candidate set (e.g., max 500 real-time candidates).
- [ ] Add timeout budget for matching stage (e.g., 100-200 ms).

### 5) Frontend
- [x] Add trigger mode selector in Triggers create/edit dialog.
- [x] Show ppl-match fields when mode is selected:
  - [x] group picker
  - [x] similarity threshold
  - [x] top-K
- [x] Display mode and group on trigger list/details.
- [x] Display latest match summary on trigger details/log views.

### 6) Feature Flags & Rollout
- [ ] Add `PPL_MATCH_TRIGGER_ENABLED` flag.
- [ ] Guard API/UI behavior behind flag.
- [ ] Add staged rollout config (dev -> staging -> prod).

### 7) Observability
- [ ] Add metrics:
  - [ ] cache hit ratio
  - [ ] candidate count
  - [ ] matching latency p50/p95
  - [ ] timeout rate
  - [ ] match fire rate
- [ ] Add structured logs including trigger UUID, source MVR UUID, matched member UUID, score, threshold.

## Acceptance Tests

### A) Functional
- [ ] Create trigger with `trigger_mode=ppl_match` succeeds with valid group + threshold.
- [ ] Existing demographic triggers continue unchanged after migration.
- [ ] Trigger fires when similarity >= threshold and returns `match` payload.
- [ ] Trigger does not fire when similarity < threshold.
- [ ] Trigger does not fire when source MVR is missing; returns inconclusive reason.
- [ ] Cooldown prevents repeated firing within configured interval.

### B) Data Integrity
- [ ] Every fired ppl-match writes execution log row with match fields populated.
- [ ] Non-fired evaluations still log pass/fail status and reason.
- [ ] Action payload includes exact persisted match object.

### C) Performance
- [ ] Cache hit path meets matching latency target.
- [ ] Redis miss + DB rebuild path completes without pipeline failure.
- [ ] Candidate bound enforcement works when group size exceeds limit.
- [ ] Timeout budget exits safely without false firing.

### D) API/UI
- [x] Trigger CRUD endpoints accept and return ppl-match fields.
- [x] UI conditionally renders ppl-match configuration fields.
- [x] UI shows latest match info for fired triggers.

### E) Rollout Safety
- [ ] With feature flag OFF, ppl-match is not configurable/executable.
- [ ] With feature flag ON, ppl-match works end-to-end in staging.

## Definition of Done
- [ ] End-to-end ppl-match flow is functional (configure -> evaluate -> fire -> action -> audit).
- [ ] Metrics/logging dashboards available for operational monitoring.
- [ ] Backward compatibility validated for existing trigger configurations.
- [ ] Documentation updated (proposal + API schema + operator run notes).
