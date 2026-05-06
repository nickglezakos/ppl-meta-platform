# Single-Video Person-Object Demographics Proposal

**Status:** Proposed and partially implemented on 2026-05-05  
**Scope:** Single-video person objects, single-media MVR creation, merge-guard inputs

---

## Problem

The current pipeline computes demographics during single-media processing, but that evidence is not consistently exposed or persisted at the single-video person-object level.

This creates three problems:

1. The media preview Details screen can show per-person grouping and routes, but not reliable normalized demographics.
2. Single-video demographic evidence is lost too early, so later merge logic depends too much on root MVR demographics.
3. The system has weaker guardrails against contamination than it should, because single-video evidence is not being treated as first-class merge input.

---

## Proposed Change

Promote age and gender evidence to the single-video person-object layer before cross-video merge.

The intended behavior is:

1. Build normalized demographics for each single-video person group from the grouped face evidence.
2. Return those demographics in the orchestrator `person_groups` response.
3. Persist single-media demographic evidence into the created VMeta `individuals` rows.
4. Reuse those demographics later as confidence-aware merge guards instead of relying only on the final active root MVR rows.

---

## Why This Makes Sense

Single-video grouping is the closest layer to the original face evidence.

At that point the system still has:

- grouped faces for one video
- timestamps and route continuity
- representative-face quality ranking
- local demographic evidence before cross-video contamination

That makes it the right place to derive demographic evidence that is:

- more explainable
- less contaminated
- more suitable for merge guardrails

---

## Design Principles

### 1. Demographics are probabilistic evidence, not identity truth

The system should not treat age or gender as absolute identity keys.

Instead:

- high-confidence conflicts should block or heavily penalize merges
- low-confidence or unknown values should not block merges
- age should be stored as range and summary, not just a single exact age

### 2. Single-video evidence should survive upward aggregation

Cross-video MVR demographics should be derived from contributing single-video evidence, not copied from one arbitrary winning member.

### 3. UI should show what is directly supported by the current object model

If single-video person groups have demographics, the UI can render them directly. If not, the UI should not invent a per-person join from another object model.

---

## Proposed Data Contract

Single-video orchestrator `person_groups` should expose:

```json
{
  "person_uuid": "...",
  "person_id": "person_1",
  "face_count": 12,
  "demographics": {
    "gender": "female",
    "gender_confidence": 0.91,
    "age_min": 24,
    "age_max": 29,
    "age_mean": 26.5,
    "age_confidence": 0.88,
    "demographics_source": "single_video_person_group",
    "face_sample_count": 3
  }
}
```

Notes:

- `gender` should be omitted or `null` when evidence is absent or too weak.
- `age_*` fields should come from grouped face evidence rather than a single arbitrary frame whenever possible.
- extra provenance fields are useful even if some current clients ignore them.

---

## Persistence Proposal

When VMeta creates the single-media `individuals` row for an isolated cluster, it should persist the best supported demographics into:

- `individuals.gender_estimate`
- `individuals.age_estimate`

This is not the full long-term model, but it is a correct intermediate step because those columns already exist and are currently underused.

---

## Merge Guard Strategy

Use single-video demographics as confidence-aware guard signals.

Recommended behavior:

1. high-confidence male vs high-confidence female: block or strongly penalize merge
2. large non-overlapping age bands with strong evidence: penalize merge
3. unknown or low-confidence demographics: do not block merge
4. aggregate from multiple faces when possible rather than one face only

---

## Implemented Slice

The current implementation slice attached to this proposal does the following:

1. Orchestrator now emits normalized `demographics` on single-video `person_groups` when age or gender evidence exists in grouped face payloads.
2. VMeta now persists single-media demographic evidence into the created `individuals` row.
3. The single-video Persons tab renders group-level gender when the backend provides it, alongside age.

This is intentionally limited:

- it does not yet create a stable per-person join between orchestrator person groups and persisted MVR rows
- it does not yet redesign all cross-video merge logic to consume the new evidence everywhere
- it does not assume gender exists in every stored face payload

---

## Verified Vision Limits

The current Vision person-object workflow does not yet provide a complete persisted demographics source.

Verified findings from `ppl-meta-vision/src/person_objects/ppl_thread_workflow.py` and `ppl-meta-vision/src/person_objects/person_objects_api.py`:

1. the stored session face query fetches frame and bbox data, but not any persisted gender fields
2. stored person objects persist `estimated_age`, but age handling is still marked in key places as a future enhancement
3. the formatted best-quality response still uses `{"estimated_age": "Unknown"}` as a placeholder in one path

So the current practical conclusion is:

- Vision is not yet a trustworthy persisted gender source for this workflow
- age is partially modeled, but not consistently propagated as finalized stored truth
- the safest merge guard input today is the single-video demographics carried and persisted in VMeta `individuals`

---

## Cross-Video Guard Wiring

The cross-video merge pipeline now prefers demographics in this order:

1. demographics already carried on the matched individual in memory
2. demographics extracted from the single-video person-object payload
3. fresh ML fallback on the cropped representative face

This means the merge guard no longer depends only on ad hoc recomputation at merge time. It now carries forward single-video evidence and persists it into `individuals` for reuse.

---

## Next Recommended Backend Steps

1. Trace the exact Vision stored-face schema for gender evidence and confidence values.
2. Standardize demographic field names across Vision, Orchestrator, and VMeta.
3. Feed persisted single-video demographic evidence into all merge paths, not only the currently patched single-media path.
4. Add response metadata that explains whether demographics came from single-video person groups, linked individuals, or active root MVR rows.

---

## Expected Outcome

This change makes the pipeline more defensible in two ways:

1. the single-video screen can show more truthful per-person evidence
2. merge safeguards can operate on earlier, less contaminated demographic signals

That does not solve every contamination path by itself, but it moves demographic truth closer to the source and reduces dependence on contaminated root-level MVR summaries.
