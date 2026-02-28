# PPL Match Trigger Proposal

## Objective
Add a new trigger capability named **ppl-match** that compares the MVR object currently driving trigger demographic evaluation against MVR objects that belong to a selected Individual Group. If a similarity match is found, the trigger fires and persists structured match details for downstream actions, audit, and UI visibility.

## Problem Statement
Current demographic triggers evaluate aggregate conditions (people count, age/gender percentages) but cannot answer identity-level questions such as:
- “Is this detected person likely a member of Group X?”
- “If matched, which group member and with what confidence?”

This proposal adds an identity-aware trigger path without removing existing demographic triggers.

## Proposed Functionality (compact)
- New trigger type/mode: **ppl-match**.
- Trigger config includes:
  - `group_id` (target Individual Group)
  - `similarity_threshold` (default e.g. 0.75)
  - optional `top_k` (default 1)
  - standard trigger controls (`is_active`, `cooldown_seconds`, `time_span`).
- Runtime behavior:
  1. During trigger evaluation, obtain the source MVR object that produced the current demographic context.
  2. Load candidate MVR members from the configured group.
  3. Compute similarity scores source-vs-group members.
  4. If any score ≥ threshold, trigger passes.
  5. Persist match payload with candidate UUID(s), score(s), threshold, and source MVR UUID.

## High-Level Architecture
- **Trigger Evaluation Layer**: add `ppl-match` evaluator alongside existing demographic condition evaluator.
- **Identity Matching Layer**: reuse/align with existing duplicate-check style similarity logic used in Individual Groups.
- **Action Dispatch Layer**: unchanged action execution pipeline; receives enriched trigger context including match metadata.
- **Storage/Audit Layer**: persist match result details for each fired `ppl-match` event.

## Data Model Changes
### Trigger Configuration
Extend trigger configuration with ppl-match fields:
- `trigger_mode` (enum: `demographic`, `ppl_match`, optional `hybrid` future)
- `match_group_id` (string)
- `match_similarity_threshold` (float)
- `match_top_k` (int)

### Execution Log
Add/extend trigger execution history table to store:
- `trigger_uuid`
- `evaluated_at`
- `passed`
- `source_mvr_uuid`
- `matched_group_id`
- `matched_member_uuid`
- `similarity_score`
- `threshold`
- `match_details_json` (top-K candidates, embeddings version, debug metadata)

## API & Contract Updates
- Trigger CRUD request/response contracts support ppl-match fields.
- Evaluation response includes optional match block:
```json
{
  "passed": true,
  "match": {
    "source_mvr_uuid": "...",
    "group_id": "grp_xxx",
    "matched_member_uuid": "...",
    "similarity_score": 0.88,
    "threshold": 0.75,
    "top_candidates": [ ... ]
  }
}
```
- Action payload enrichment: include `match` object for email/webhook/alert/log/signage contexts.

## Evaluation Flow (runtime)
1. Receive detection event and build evaluation context.
2. If trigger mode is `ppl-match`, resolve source MVR UUID from current event pipeline context.
3. Fetch group member MVR UUIDs and embeddings.
4. Compute similarity and select best candidates.
5. Apply threshold + cooldown + time span checks.
6. If passed: execute action and persist match result.

## UI/UX Impact (compact)
- In Triggers create/edit dialog:
  - add mode selector (`Demographic` / `PPL Match`)
  - show group picker and threshold input when `PPL Match` selected
- In trigger list/details:
  - display mode and linked group
  - show latest match summary (member, score, timestamp)

## Backward Compatibility
- Existing demographic triggers remain unchanged.
- Default mode for existing rows: `demographic`.
- No behavior change unless new ppl-match mode is explicitly configured.

## Risks & Mitigations
- **Risk**: false positives/negatives from threshold choice.
  - **Mitigation**: configurable threshold, top-K logging, calibration guide.
- **Risk**: increased evaluation latency.
  - **Mitigation**: cache group embeddings in memory/Redis and bound candidate set.
- **Risk**: missing source MVR in some event paths.
  - **Mitigation**: explicit fallback: mark evaluation inconclusive, do not fire.

## Performance Design (compact)
- **Cache model**: cache group member embeddings by key `ppl_match:group:{group_id}:v{embedding_version}` in process memory + Redis (shared fallback).
- **Payload shape**: `[ { member_mvr_uuid, embedding, updated_at } ]` plus small metadata (`count`, `version`, `generated_at`).
- **Read strategy**: try in-memory first, then Redis, then DB rebuild on miss.
- **Invalidation**: evict/refresh on member add/remove, merge operations, embedding updates, and model-version changes; apply TTL (e.g., 5-15 min) as safety net.
- **Candidate bounds**: compare only against selected group and cap candidates (e.g., max 500 real-time members); if exceeded, use top-K prefilter/ANN then exact scoring.
- **Latency guardrails**: add evaluation timeout budget (e.g., 100-200 ms for matching stage) and fail closed (`not fired`) when budget is exceeded.
- **Observability**: publish cache hit ratio, candidate count, match latency p50/p95, and timeout rate.

## Incremental Delivery Plan
1. **Phase 1**: schema + API contracts + feature flag (`PPL_MATCH_TRIGGER_ENABLED`).
2. **Phase 2**: evaluator + matching integration + execution logging.
3. **Phase 3**: frontend trigger configuration + match visibility.
4. **Phase 4**: performance tuning (caching), telemetry, and threshold calibration.

## Success Criteria
- Users can configure a trigger against an Individual Group using ppl-match mode.
- Trigger fires only when similarity threshold is met.
- Fired event contains persisted, queryable match metadata.
- Existing trigger functionality remains stable and unchanged.
