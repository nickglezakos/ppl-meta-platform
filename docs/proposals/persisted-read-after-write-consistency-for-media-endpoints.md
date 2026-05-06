# Persisted Read-After-Write Consistency for Media Endpoints

**Proposal Version**: 1.0  
**Date**: May 6, 2026  
**Status**: Draft  
**Author**: Engineering

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current Failure Pattern](#current-failure-pattern)
3. [Goal](#goal)
4. [Core Pattern](#core-pattern)
5. [Reference Implementation](#reference-implementation)
6. [Where to Apply This Next](#where-to-apply-this-next)
7. [Platform Contract](#platform-contract)
8. [Backend Design Changes](#backend-design-changes)
9. [Observability Requirements](#observability-requirements)
10. [Rollout Plan](#rollout-plan)
11. [Risks and Mitigations](#risks-and-mitigations)
12. [Acceptance Criteria](#acceptance-criteria)

---

## 1. Problem Statement

Several media-facing endpoints follow this sequence:

1. Resolve persisted session or persisted media state
2. Attempt to read persisted structured output
3. Fall back to a live pipeline when the persisted read is missing or incomplete
4. Write new persisted records during fallback
5. Return a live-only response shape even though persisted records now exist

This creates an inconsistency window:

- The first request writes durable data but still behaves like a transient request
- The next request may behave differently from the first request for the same media
- Callers cannot assume a stable response contract after fallback succeeds
- Logs and database state show persistence exists, but the API response still reflects live regrouping semantics

The USB04 person-objects path exposed this clearly:

- The media already resolved to a persisted session UUID
- The fallback path wrote person objects under that session
- Before the recent fix, the endpoint could still return a live-only shape instead of round-tripping the persisted result

This proposal defines a platform-wide pattern so any media endpoint that writes persisted records during fallback immediately converges to the persisted response shape.

---

## 2. Current Failure Pattern

### Behavioural pattern

The problematic pattern is:

```text
request
  -> try persisted read
  -> persisted read unavailable
  -> execute fallback pipeline
  -> write persisted rows
  -> return fallback payload directly
```

Instead of:

```text
request
  -> try persisted read
  -> persisted read unavailable
  -> execute fallback pipeline
  -> write persisted rows
  -> finalize persistence boundary
  -> re-read persisted state
  -> return persisted payload
```

### Consequences

- First request and second request can return different shapes for the same media
- Response fields such as `session_uuid`, `status`, `routes_data`, `person_groups`, and stable UUIDs may differ between calls
- Frontend code is forced to support multiple semantic meanings for the same endpoint
- Debugging is harder because a successful write does not guarantee a readable persisted contract

---

## 3. Goal

For any media endpoint that falls back to a live computation and writes persisted records, guarantee that:

1. The persisted identity key is preserved during fallback
2. The fallback write is finalized into a readable persisted state
3. The same request attempts a persisted re-read before returning
4. If the persisted re-read succeeds, the endpoint returns the persisted response shape immediately
5. Subsequent requests go directly through the persisted read path with no regroup or live-only response shape

This yields a stable platform contract:

- **Prime path**: persisted read
- **Fallback path**: materialize persistence
- **Return path**: persisted read again

---

## 4. Core Pattern

### Canonical pattern

Every media endpoint that can persist during fallback should follow this pattern:

```python
async def get_media_result(media_id: str, auth_token: str):
    persisted_key = await resolve_persisted_key(media_id)

    persisted = await try_read_persisted(media_id, persisted_key, auth_token)
    if persisted.success:
        return persisted.response

    fallback_result = await run_live_fallback(
        media_id=media_id,
        auth_token=auth_token,
        persisted_key=persisted_key,
    )
    if not fallback_result.success:
        return fallback_result.error_response

    await finalize_persisted_state(
        media_id=media_id,
        persisted_key=fallback_result.persisted_key,
        fallback_result=fallback_result,
    )

    persisted = await retry_read_persisted(
        media_id=media_id,
        persisted_key=fallback_result.persisted_key,
        auth_token=auth_token,
        attempts=3,
        delay_seconds=0.1,
    )
    if persisted.success:
        return persisted.response

    return fallback_result.transitional_response
```

### Required properties

- The fallback must reuse an existing persisted session key when one already exists
- If no session exists yet, the fallback-created session key becomes the authoritative key for future reads
- The persistence boundary must be explicit, not assumed
- The endpoint must not return success from a fallback write without at least attempting to re-read the persisted result

---

## 5. Reference Implementation

The current reference implementation is the Orchestrator person-objects media endpoint.

### Current reference path

- Resolve media to session UUID
- Attempt persisted session details read
- If unavailable, run live grouping under the authoritative session UUID
- After writing person objects, immediately retry the persisted session-details read
- Return the persisted response shape when the read succeeds

### Why this is the right reference

It proves the correct platform behaviour:

- Stable `session_uuid`
- Stable person UUIDs
- Stable persisted response message and shape
- No second request needed to “normalize” the API contract

This should be treated as the model for other media endpoints.

---

## 6. Where to Apply This Next

The next candidates are endpoints that meet all of the following conditions:

1. They are media-scoped or session-scoped reads
2. They can compute live fallback data
3. They write durable rows during fallback
4. They currently return a live-only or transitional shape after writing

### Priority 1: Vision and Orchestrator media detail endpoints

These should be audited first:

- Media person-object summary endpoints
- Session detail endpoints with live fallback recovery
- Face-detection enriched media endpoints that create session records and derived outputs
- Any endpoint that currently returns `faces_only`, `pending`, `no_session`, or transient workflow payloads after writing durable data

### Priority 2: VMeta derived media endpoints

Any VMeta endpoint that:

- builds derived records during request handling
- writes best-face, demographics, appearance, or identity linkage rows
- then responds from in-memory intermediate objects instead of persisted rows

should adopt the same round-trip rule.

### Priority 3: Cross-service aggregation endpoints

Endpoints in Gateway or Orchestrator that aggregate downstream results should also normalize on the persisted read-after-write rule if they trigger writes in downstream services before responding.

---

## 7. Platform Contract

### Proposed rule

If a request writes the authoritative persisted representation of a resource, the same request should try to return that authoritative representation.

### Practical contract

For media endpoints:

- **Read persisted first**
- **Fallback only when persisted read is missing or invalid**
- **Write to authoritative persisted key**
- **Finalize write state**
- **Re-read persisted state**
- **Return persisted state if available**

### Transitional fallback response

Returning a live-only response after persistence should be reserved for true failure cases only:

- downstream persisted read remains unavailable after bounded retry
- persistence finalization failed
- dependent service is degraded

In those cases, the response should explicitly mark itself as transitional and include enough metadata to explain that persisted convergence did not complete.

---

## 8. Backend Design Changes

### 8.1 Add a reusable helper pattern

Introduce a small shared pattern in Orchestrator and, where appropriate, in Vision:

- `resolve_authoritative_session_or_media_key(...)`
- `try_load_persisted_response(...)`
- `materialize_persisted_state(...)`
- `retry_load_persisted_response(...)`

This reduces one-off implementations and makes code review easier.

### 8.2 Distinguish three states explicitly

Every endpoint should separate:

1. `persisted_missing`
2. `persisted_written_but_not_yet_readable`
3. `persisted_readable`

At present, some code paths collapse states 1 and 2 into a generic fallback branch. That makes it hard to know whether the issue is missing data or missing convergence.

### 8.3 Finalize session lifecycle explicitly

If fallback writes session-scoped data, the endpoint should also ensure the session lifecycle reflects completion where relevant:

- session status completed
- ended timestamp set
- face or object counts updated
- workflow completion timestamp set

This is especially important where multiple tables participate in read eligibility.

### 8.4 Prefer persisted re-read over reformatting in-memory objects

After fallback writes, do not treat the live in-memory object graph as the source of truth if a persisted read is available.

The persisted read should be preferred because it validates:

- row linkage
- workflow completion
- schema compatibility
- actual downstream readability

---

## 9. Observability Requirements

Every endpoint adopting this pattern should log four milestones:

1. `persisted read miss`
2. `fallback materialization started`
3. `fallback materialization completed`
4. `persisted re-read succeeded` or `persisted re-read still unavailable`

Recommended log fields:

- `media_id`
- `session_uuid`
- `workflow_id`
- `attempt_count`
- `service_name`
- `response_shape` (`persisted`, `transitional_fallback`, `error`)

Suggested success log:

```text
Fallback materialized readable persisted response for media {media_id} session {session_uuid}
```

Suggested warning log:

```text
Persisted response still unavailable after fallback write for media {media_id} session {session_uuid}
```

---

## 10. Rollout Plan

### Phase 1: Inventory

Search for endpoints that:

- call live pipeline helpers during GET-style reads
- write sessions, workflows, or derived records during fallback
- return fallback payloads directly

Output: a list of candidate endpoints grouped by service.

### Phase 2: Shared checklist

Create an engineering checklist for each candidate:

- authoritative persisted key identified
- persisted read path exists
- fallback writes under authoritative key
- session/workflow finalization exists
- persisted re-read added
- transitional response only used on true convergence failure

### Phase 3: Service-by-service implementation

Apply the pattern to:

1. Orchestrator media endpoints
2. Vision derived media endpoints
3. VMeta media-derived endpoints
4. Gateway aggregation endpoints where applicable

### Phase 4: Contract tests

For each endpoint, add tests that prove:

- first request with no persisted result triggers fallback write
- first request returns persisted shape when write succeeds
- second request uses persisted path directly
- stable IDs and counts across repeated requests

---

## 11. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Added latency from immediate persisted re-read | Medium | Medium | Use bounded retries with short delays and only after successful fallback writes |
| Hidden schema drift between write path and read path | High | Medium | Treat re-read failure as a signal; add structured logs and contract tests |
| Endpoint-specific response builders diverge | Medium | Medium | Centralize helper pattern and require persisted-response builders |
| Returning transitional responses too often under load | Medium | Low | Add retry budget and service metrics; tune retry count and delay |
| Duplicate writes from repeated fallback triggers | High | Low | Preserve authoritative session/media key and make writes idempotent where possible |

---

## 12. Acceptance Criteria

This proposal is successful when the following are true for each adopted endpoint:

1. If fallback writes persisted rows successfully, the same request attempts a persisted re-read before returning.
2. If that persisted re-read succeeds, the endpoint returns the persisted response shape immediately.
3. A repeated request for the same media returns the same authoritative IDs and the same persisted semantic shape.
4. Logs clearly show whether the response came from persisted read, fallback materialization, or transitional fallback.
5. No endpoint silently returns a live-only success shape after writing authoritative persisted rows unless the persisted re-read failed within a bounded retry budget.

---

## Summary

The platform should treat fallback writes as a convergence step, not a terminal response step.

The rule is simple:

- write persisted state
- finalize it
- read it back
- return it

Applying this pattern consistently will eliminate first-read vs second-read drift, stabilize media endpoint contracts, and make persistence behaviour predictable across Orchestrator, Vision, VMeta, and Gateway.