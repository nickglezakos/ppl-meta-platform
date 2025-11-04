# Individual Counting: Original vs MVR-Merged

**Feature:** Dual Counter System for Cross-Video Tracking  
**Date:** November 1, 2025  
**Status:** ✅ Implemented

---

## Overview

The system now provides **TWO individual counters** to compare the original detection count vs. the deduplicated count after MVR-People auto-matching:

1. **`individuals_found`**: Original individuals detected (before MVR merging)
2. **`unique_mvr_people_count`**: Unique individuals after MVR-People auto-matching and merging

---

## Why Two Counters?

### Problem
When tracking individuals across multiple videos, the same person may be detected as multiple "individuals" if they:
- Appear in different videos
- Move between camera views
- Have different lighting conditions
- Have different angles/poses

### Solution
Keep BOTH metrics for comparison:

**`individuals_found` (Original Count)**
- Raw detections from cross-video tracking
- Shows how many "individual" records were created
- **Does NOT account for duplicates**
- Example: 15 individuals

**`unique_mvr_people_count` (Merged Count)**
- After MVR-People auto-matching
- Duplicates merged based on face similarity (threshold: 0.85)
- **Actual unique people**
- Example: 12 unique people (3 duplicates merged)

---

## API Endpoints

### 1. GET `/sessions/{session_uuid}` - Session Status

Returns both counters in the session status:

```json
{
  "session_uuid": "abc-123",
  "status": "completed",
  "collections": ["camera-01"],
  "total_videos": 10,
  "processed_videos": 10,
  "individuals_found": 15,              ← Original count
  "unique_mvr_people_count": 12,        ← After merging
  "cache_hits": 0
}
```

**Interpretation:**
- 15 individuals detected initially
- 12 are actually unique people
- 3 duplicates were merged

---

### 2. GET `/sessions/{session_uuid}/individuals` - Individuals List

Returns both counters plus the list of individuals:

```json
{
  "session_uuid": "abc-123",
  "total_individuals": 15,              ← Original count (list length)
  "unique_mvr_people_count": 12,        ← After merging
  "individuals": [
    {
      "individual_uuid": "uuid-1",
      "individual_id": "IND-001",
      "total_appearances": 3,
      "total_videos": 2,
      "first_seen": "2025-11-01T10:00:00Z",
      "last_seen": "2025-11-01T10:30:00Z",
      "confidence_score": 0.923
    },
    // ... 14 more individuals
  ]
}
```

**Note:** The `individuals` array contains ALL individuals (including duplicates). The `unique_mvr_people_count` shows how many are actually unique after merging.

---

## Comparison Examples

### Example 1: Retail Store (High Duplicate Rate)

**Scenario:** 8-hour store operation, 4 cameras

```json
{
  "individuals_found": 250,
  "unique_mvr_people_count": 180
}
```

**Analysis:**
- 250 total detections
- 180 unique shoppers
- 70 duplicates (28% duplicate rate)
- Average 1.39 appearances per shopper

**Business Insight:** High duplicate rate indicates good coverage (customers detected multiple times as they shop)

---

### Example 2: Security Corridor (Low Duplicate Rate)

**Scenario:** Hallway monitoring, 2 cameras

```json
{
  "individuals_found": 50,
  "unique_mvr_people_count": 48
}
```

**Analysis:**
- 50 total detections
- 48 unique people
- 2 duplicates (4% duplicate rate)
- Most people just passing through once

**Business Insight:** Low duplicate rate indicates transient traffic (one-time passers)

---

### Example 3: Event Venue (Very High Duplicate Rate)

**Scenario:** Conference with 6 cameras in different rooms

```json
{
  "individuals_found": 1500,
  "unique_mvr_people_count": 850
}
```

**Analysis:**
- 1500 total detections
- 850 unique attendees  
- 650 duplicates (43% duplicate rate)
- Average 1.76 room visits per attendee

**Business Insight:** High duplicate rate shows attendees moving between rooms

---

## Calculation Logic

### Step-by-Step Process

```
1. Cross-Video Tracking Runs
   └─> Creates individual records
   └─> individuals_found = 15

2. Auto-MVR Matching Starts (if individuals_found > 1)
   └─> For each individual:
       ├─> Find similar individuals (similarity > 0.85)
       └─> Merge duplicates

3. Merge Example:
   Individual A (score: 0.95) + Individual B (score: 0.92)
   └─> Similarity: 0.93 (> 0.85 threshold)
   └─> Merge: Keep A (higher score), orphan B
   └─> merge_count += 1

4. Calculate Unique Count
   └─> unique_mvr_people_count = individuals_found - merge_count
   └─> unique_mvr_people_count = 15 - 3 = 12

5. Update Database
   └─> Store BOTH counts
```

---

## Use Cases

### Use Case 1: Tracking Accuracy Validation

**Question:** "How accurate is our cross-video tracking?"

**Answer:**
```
Duplicate Rate = (individuals_found - unique_mvr_people_count) / individuals_found * 100

Example: (250 - 180) / 250 * 100 = 28% duplicate rate
```

**Interpretation:**
- High duplicate rate (>30%): Good multi-camera coverage
- Low duplicate rate (<10%): Single-camera or transient traffic
- Very high (>50%): Possible over-detection issue

---

### Use Case 2: Customer Behavior Analysis

**Question:** "How many times does each customer appear on average?"

**Answer:**
```
Avg Appearances = individuals_found / unique_mvr_people_count

Example: 250 / 180 = 1.39 appearances per customer
```

**Interpretation:**
- 1.0-1.2: Mostly one-time visitors
- 1.2-1.5: Some repeat appearances
- 1.5-2.0: High engagement (browsing/shopping)
- 2.0+: Extended visits or high mobility

---

### Use Case 3: System Debugging

**Question:** "Why are my individual counts so high?"

**Check the ratio:**

```json
{
  "individuals_found": 1000,
  "unique_mvr_people_count": 100
}
```

**Ratio:** 10:1 (very high)

**Diagnosis:** Possible issues:
- Cross-video tracking creating too many individuals
- MVR matching threshold too strict (missing similar faces)
- Same person re-entering/leaving repeatedly
- Quality issues causing false negatives in matching

---

## Frontend Display Recommendations

### Display Format 1: Side-by-Side

```
┌─────────────────────────────────────┐
│ Tracking Session Results           │
├─────────────────────────────────────┤
│ Total Detections:        15         │
│ Unique Individuals:      12 ✓       │
│ Duplicates Merged:       3          │
│ Accuracy:                80%        │
└─────────────────────────────────────┘
```

### Display Format 2: Progress Bar

```
Total: 15 individuals
Unique: ████████████░░░ 12 (80%)
       (3 duplicates removed)
```

### Display Format 3: Comparison Card

```
Before Merging    After Merging
    15         →      12
individuals       unique people
                  ✓ 3 duplicates removed
```

---

## Database Schema

### Table: `tracking_sessions`

```sql
CREATE TABLE tracking_sessions (
    session_uuid UUID PRIMARY KEY,
    status VARCHAR(20),
    total_videos INTEGER,
    processed_videos INTEGER,
    individuals_found INTEGER,           -- Original count
    unique_mvr_people_count INTEGER,     -- After merging
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Query Examples

**Find sessions with high duplicate rates:**
```sql
SELECT 
    session_uuid,
    individuals_found,
    unique_mvr_people_count,
    ROUND(100.0 * (individuals_found - unique_mvr_people_count) / individuals_found, 1) 
        AS duplicate_rate_percent
FROM tracking_sessions
WHERE status = 'completed' 
  AND individuals_found > 0
  AND (individuals_found - unique_mvr_people_count) > 0
ORDER BY duplicate_rate_percent DESC
LIMIT 10;
```

**Calculate average appearances per individual:**
```sql
SELECT 
    session_uuid,
    individuals_found,
    unique_mvr_people_count,
    ROUND(individuals_found::NUMERIC / NULLIF(unique_mvr_people_count, 0), 2) 
        AS avg_appearances_per_person
FROM tracking_sessions
WHERE status = 'completed'
  AND unique_mvr_people_count > 0
ORDER BY avg_appearances_per_person DESC;
```

---

## Testing

### Test Case 1: No Duplicates

**Setup:** Create 5 individuals with distinct faces

**Expected:**
```json
{
  "individuals_found": 5,
  "unique_mvr_people_count": 5
}
```

**Result:** No merging, counts match

---

### Test Case 2: Some Duplicates

**Setup:** Create 10 individuals (8 unique, 2 pairs of duplicates)

**Expected:**
```json
{
  "individuals_found": 10,
  "unique_mvr_people_count": 8
}
```

**Result:** 2 merges, 8 unique

---

### Test Case 3: All Duplicates

**Setup:** Create 6 individuals (all same person, different angles)

**Expected:**
```json
{
  "individuals_found": 6,
  "unique_mvr_people_count": 1
}
```

**Result:** 5 merges, 1 unique

---

## Summary

### Key Points

✅ **Two counters provided:**
- `individuals_found`: Original detections
- `unique_mvr_people_count`: After MVR merging

✅ **Available in two endpoints:**
- GET `/sessions/{uuid}` - Status
- GET `/sessions/{uuid}/individuals` - Details

✅ **Use cases:**
- Tracking accuracy validation
- Customer behavior analysis
- System debugging
- Business analytics

✅ **Always comparable:**
- `unique_mvr_people_count` ≤ `individuals_found`
- Difference = number of duplicates merged
- Ratio = average appearances per person

---

**Implementation Date:** November 1, 2025  
**Status:** ✅ Production Ready  
**Author:** PPL Meta Platform Team
