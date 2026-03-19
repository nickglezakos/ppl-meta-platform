# MVR People Merge Worker — Two-Tier Merge with Cross-Source Identity Groups

**Last Updated**: March 19, 2026  
**Status**: Implemented  
**Version**: 2.23.0  
**Related**: [Instant Detection Module](Instant-detection%20module.md), [Hierarchical Merge Scheduler](../../../ppl-meta-vmeta/src/background/hierarchical_merge_scheduler.py), [Hierarchical MVR Merger](../../../ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py)

---

## Overview

The **Hierarchical Merge Scheduler** (Queue C) is a background worker in the VMeta service that periodically finds similar MVR people and merges duplicates. It uses a **two-tier merge** architecture to handle MVR people from both the recording pipeline and instant detection:

- **Tier 1** — Source-separated hard merge: recording and instant detection MVR people are merged independently within their own source (losers orphaned).
- **Tier 2** — Cross-source soft link: surviving winners from different sources that represent the same real person are linked via a shared `identity_group_uuid` without orphaning either side.

This ensures accurate analytics counts in all three filtering modes: recording only, instant detection only, and combined (both sources).

---

## How the Merge Worker Operates

### Scheduling

| Parameter | Value | Description |
|-----------|-------|-------------|
| `periodic_interval_minutes` | **30** | Runs every 30 minutes |
| `lookback_minutes` | **120** | Considers MVR people created in the last 2 hours |
| `post_session_delay_seconds` | **30** | Also triggers 30 seconds after Queue B completes |
| `similarity_threshold` | **0.70** | Cosine similarity threshold for merging |

Configured in `ppl-meta-vmeta/src/main.py` (lines 147–160).

### Two Trigger Modes

1. **Periodic mode** — Every 30 minutes, runs the full two-tier merge cycle.
2. **Post-session mode** — Triggered after Queue B (individual → MVR creation) completes for a recording session, with a 30-second delay.

### Core Merge Algorithm (used by both tiers)

1. Fetch candidate MVR people with face embeddings
2. Compute pairwise **cosine similarity** on face embeddings
3. Build connected components using **Union-Find** (similarity ≥ 0.70)
4. For each group: select **winner** (highest `quality_score`), orphan the rest (Tier 1) or assign shared `identity_group_uuid` (Tier 2)

---

## Schema

### New Column (Migration 020)

```sql
ALTER TABLE mvr_people
    ADD COLUMN IF NOT EXISTS identity_group_uuid UUID DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_mvr_people_identity_group
    ON mvr_people (identity_group_uuid)
    WHERE identity_group_uuid IS NOT NULL;
```

Migration file: `ppl-meta-vmeta/migrations/020_add_identity_group_uuid.sql`

MVR people representing the same real person across different sources share the same `identity_group_uuid`. MVR people only seen in one source have `identity_group_uuid = NULL`.

### Distinguishing Fields Used by the Merger

| Table | Field | Recording Value | Instant Detection Value | Used by |
|-------|-------|-----------------|------------------------|---------|
| `tracking_sessions` | `source_type` | `'recording_pipeline'` | `'instant_detection'` | Tier 1 (source-filtered queries) |
| `individual_mvr_mapping` | `link_method` | `'auto_create'` / `'auto_merge'` | `'instant_detection'` | Analytics queries |
| `mvr_people` | `identity_group_uuid` | Shared UUID | Shared UUID | Tier 2 (cross-source dedup) |

---

## Two-Tier Merge Architecture

### Processing Flow

```
Recording Pipeline              Instant Detection Pipeline
         │                                  │
  Queue A (Videos → Individuals)    Persist endpoint
  Queue B (Individuals → MVR)       (POST /instant-detection/persist)
         │                                  │
  MVR People created with:         MVR People created with:
  link_method = 'auto_create'      link_method = 'instant_detection'
         │                                  │
         ▼                                  ▼
┌─────────────────────────────────────────────────────┐
│           Queue C — Two-Tier Merge                  │
│                                                     │
│  TIER 1: Source-Separated Hard Merge                │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Pass 1: Recording│  │ Pass 2: Instant Detection│ │
│  │ Union-Find→Orphan│  │ Union-Find→Orphan        │ │
│  └──────────────────┘  └──────────────────────────┘ │
│                    │          │                      │
│                    ▼          ▼                      │
│  TIER 2: Cross-Source Soft Link                     │
│  ┌──────────────────────────────────────────┐       │
│  │ All surviving winners from both sources  │       │
│  │ Union-Find→Assign identity_group_uuid    │       │
│  │ (NO orphaning)                           │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### Tier 1: Source-Separated Hard Merge

Each source is merged independently. Losers are orphaned (`is_orphaned = true`, `merged_into_mvr_uuid` set to winner). This produces one surviving MVR per real person **per source**.

**Pass 1 — Recording pipeline MVRs:**

```sql
SELECT mp.mvr_people_uuid
FROM mvr_people mp
JOIN tracking_sessions ts ON mp.created_by_session = ts.session_uuid
WHERE mp.created_at >= $1
  AND ts.source_type = 'recording_pipeline'
ORDER BY mp.created_at DESC
```

**Pass 2 — Instant detection MVRs:**

```sql
SELECT mp.mvr_people_uuid
FROM mvr_people mp
JOIN tracking_sessions ts ON mp.created_by_session = ts.session_uuid
WHERE mp.created_at >= $1
  AND ts.source_type = 'instant_detection'
ORDER BY mp.created_at DESC
```

Each pass feeds the result UUIDs into `merger.merge_hierarchical()` — the same algorithm as before, just scoped to one source.

### Tier 2: Cross-Source Soft Link

After both Tier 1 passes complete, all **surviving (non-orphaned)** MVR people from both sources are evaluated together:

```sql
SELECT mvr_people_uuid
FROM mvr_people
WHERE created_at >= $1
  AND is_orphaned = false
  AND merged_into_mvr_uuid IS NULL
ORDER BY created_at DESC
```

The algorithm:
1. Fetch face embeddings for all survivors
2. Calculate pairwise cosine similarity
3. Find connected components via Union-Find (threshold 0.70)
4. For each multi-member group: assign a shared `identity_group_uuid` (generated via `uuid4()`)
5. For singletons: clear any stale `identity_group_uuid` from previous cycles

**No MVR is orphaned in Tier 2.** Both sides remain `is_orphaned = false` and visible in their respective source filter.

### Execution Sequence

```
Queue C periodic cycle (every 30 minutes):
  1. Tier 1 Pass 1 — hard merge recording MVRs
  2. Tier 1 Pass 2 — hard merge instant detection MVRs
  3. Tier 2 — soft link surviving winners across sources
```

---

## Worked Example

3 real people (A, B, C). Camera runs both funnels concurrently.

**Input:**

| MVR | Source | Person | quality_score |
|-----|--------|--------|---------------|
| A₁  | instant detection | Person A | 0.65 |
| A₂  | instant detection | Person A | 0.70 |
| B₁  | instant detection | Person B | 0.60 |
| B₂  | instant detection | Person B | 0.68 |
| C₁  | instant detection | Person C | 0.62 |
| A₃  | recording | Person A | 0.90 |
| B₃  | recording | Person B | 0.88 |
| C₂  | recording | Person C | 0.85 |

**After Tier 1 (source-separated hard merge):**

| MVR | Source | is_orphaned | merged_into |
|-----|--------|-------------|-------------|
| A₁  | instant detection | `true` | A₂ |
| A₂  | instant detection | `false` | — |
| B₁  | instant detection | `true` | B₂ |
| B₂  | instant detection | `false` | — |
| C₁  | instant detection | `false` | — |
| A₃  | recording | `false` | — |
| B₃  | recording | `false` | — |
| C₂  | recording | `false` | — |

**After Tier 2 (cross-source soft link):**

| MVR | Source | is_orphaned | identity_group_uuid |
|-----|--------|-------------|---------------------|
| A₂  | instant detection | `false` | `group-A` |
| B₂  | instant detection | `false` | `group-B` |
| C₁  | instant detection | `false` | `group-C` |
| A₃  | recording | `false` | `group-A` |
| B₃  | recording | `false` | `group-B` |
| C₂  | recording | `false` | `group-C` |

---

## Analytics Integration

### Query Logic Per Filter Mode

#### Filtered by Source

Per-source queries use `link_method` joins — unchanged from before:

```sql
-- Instant detection only → 3 MVR people ✅
SELECT COUNT(*) FROM mvr_people mp
JOIN individual_mvr_mapping imm ON mp.mvr_people_uuid = imm.mvr_people_uuid
WHERE mp.is_orphaned = false
  AND mp.merged_into_mvr_uuid IS NULL
  AND imm.link_method = 'instant_detection'
  AND mp.created_at >= $1 AND mp.created_at <= $2

-- Recording only → 3 MVR people ✅
SELECT COUNT(*) FROM mvr_people mp
JOIN individual_mvr_mapping imm ON mp.mvr_people_uuid = imm.mvr_people_uuid
WHERE mp.is_orphaned = false
  AND mp.merged_into_mvr_uuid IS NULL
  AND imm.link_method IN ('auto_create', 'auto_merge')
  AND mp.created_at >= $1 AND mp.created_at <= $2
```

#### Unfiltered — Both Sources

Uses `COALESCE(identity_group_uuid, mvr_people_uuid)` to deduplicate across sources:

```sql
-- Deduplicated total → 3 unique people ✅
SELECT COUNT(DISTINCT COALESCE(identity_group_uuid, mvr_people_uuid))
FROM mvr_people
WHERE is_orphaned = false
  AND merged_into_mvr_uuid IS NULL
  AND created_at >= $1 AND created_at <= $2
```

`COALESCE` handles MVR people that were never cross-linked (only seen in one source) — they count as their own group.

#### Demographics in Combined Mode

Picks one representative MVR per identity group (highest quality) to avoid double-counting:

```sql
SELECT gender, age_min, age_max FROM (
    SELECT DISTINCT ON (COALESCE(identity_group_uuid, mvr_people_uuid))
        gender, age_min, age_max, quality_score
    FROM mvr_people
    WHERE is_orphaned = false
      AND merged_into_mvr_uuid IS NULL
      AND created_at >= $1 AND created_at <= $2
    ORDER BY COALESCE(identity_group_uuid, mvr_people_uuid), quality_score DESC
) deduplicated
```

#### Collection / Camera Scoping

All queries work with additional camera/collection filters:

```sql
SELECT COUNT(DISTINCT COALESCE(mp.identity_group_uuid, mp.mvr_people_uuid))
FROM mvr_people mp
JOIN tracking_sessions ts ON mp.created_by_session = ts.session_uuid
WHERE mp.is_orphaned = false
  AND mp.merged_into_mvr_uuid IS NULL
  AND ts.camera_device_id = ANY($1)
  AND mp.created_at >= $2 AND mp.created_at <= $3
```

### Results Summary

| Filter Mode | Count | Method |
|-------------|-------|--------|
| Recording only | 3 | Direct count with `link_method` filter |
| Instant detection only | 3 | Direct count with `link_method` filter |
| Both / No filter | 3 | `COUNT(DISTINCT COALESCE(identity_group_uuid, mvr_people_uuid))` |

All three modes return the correct real-person count.

---

## Implementation Reference

### Files Changed

| Component | File | Change |
|-----------|------|--------|
| **Migration** | `ppl-meta-vmeta/migrations/020_add_identity_group_uuid.sql` | Adds `identity_group_uuid UUID` column + partial index |
| **Scheduler** | `ppl-meta-vmeta/src/background/hierarchical_merge_scheduler.py` | `_run_periodic_merge()` runs two-tier: source-filtered Tier 1 + cross-source Tier 2. New `_run_cross_source_link()` method |
| **Analytics** | `ppl-meta-vmeta/src/api/v1/quality_metrics.py` | MVR queries include `identity_group_uuid`. Unfiltered path deduplicates via `COALESCE`. Added `recording_pipeline` source filter. Demographics use `DISTINCT ON` with `COALESCE` |

### Files Unchanged

| Component | File | Reason |
|-----------|------|--------|
| **Merger** | `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py` | Already works correctly — the scheduler feeds it source-filtered UUID lists |
| **Tracking Summary** | `ppl-meta-vmeta/src/api/v1/tracking_sessions_summary.py` | Always called with `source_type` filter; Tier 2 doesn't orphan so per-source counts remain correct |
| **Scheduler Init** | `ppl-meta-vmeta/src/main.py` | No configuration changes needed |

### Key Code Locations

| Component | File | Method/Section | Purpose |
|-----------|------|----------------|---------|
| Two-tier merge | `hierarchical_merge_scheduler.py` | `_run_periodic_merge()` | Orchestrates Tier 1 Pass 1 → Pass 2 → Tier 2 |
| Cross-source link | `hierarchical_merge_scheduler.py` | `_run_cross_source_link()` | Assigns `identity_group_uuid` to cross-source groups |
| Hard merge | `hierarchical_mvr_merger.py` | `merge_hierarchical()` | Union-Find + orphan (called by Tier 1) |
| Similarity calc | `hierarchical_mvr_merger.py` | `_calculate_similarity_matrix()` | Pairwise cosine similarity (called by both tiers) |
| MVR dedup (analytics) | `quality_metrics.py` | `get_mvr_quality_metrics()` | `COALESCE(identity_group_uuid, mvr_people_uuid)` dedup |
| Demographics dedup | `quality_metrics.py` | `get_mvr_quality_metrics()` | `DISTINCT ON` with `COALESCE` for combined mode |
