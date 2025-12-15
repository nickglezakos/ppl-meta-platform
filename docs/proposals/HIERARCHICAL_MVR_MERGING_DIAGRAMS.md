# Hierarchical MVR People Merging - Visual Architecture

## Current Problem

```
┌────────────────────────────────────────────────────────────────┐
│                    CURRENT: Duplicates                          │
└────────────────────────────────────────────────────────────────┘

Recording Session (30 minutes)
│
├─ Videos 1-5  ──► Batch 1 Processing ──► MVR Person A (John)
│                                          - quality: 0.85
│                                          - 45 detections
│
├─ Videos 6-10 ──► Batch 2 Processing ──► MVR Person B (John)
│                                          - quality: 0.78
│                                          - 52 detections
│
└─ Videos 11-15 ─► Batch 3 Processing ──► MVR Person C (John)
                                           - quality: 0.92
                                           - 61 detections

Search Result: 3 separate MVR people (but all same person!)
└─ User sees: "158 appearances → 3 individuals"
   Problem: Should show "158 appearances → 1 unique person"
```

## Proposed Solution

```
┌────────────────────────────────────────────────────────────────┐
│              PROPOSED: Hierarchical Merging                     │
└────────────────────────────────────────────────────────────────┘

Step 1: Search Collection
│
├─ Get all MVR people from all batches
│  └─ Returns: [MVR A, MVR B, MVR C, ...]
│
Step 2: Calculate Similarity Matrix
│
├─ Compare A ↔ B: 0.87 (similar!)
├─ Compare A ↔ C: 0.89 (similar!)
├─ Compare B ↔ C: 0.84 (similar!)
│
Step 3: Find Merge Groups (Connected Components)
│
└─ Group 1: [A, B, C] (all similar > 0.70 threshold)
   └─ Merge into Super-Individual S1
      ├─ Winner: C (highest quality: 0.92)
      └─ Losers: A, B (marked as orphaned)

Search Result: 1 super-individual (correct!)
└─ User sees: "158 appearances → 1 unique person (3 batches merged)"
```

## Three-Tier Hierarchy

### UI Display: Individuals Tab

```
┌─────────────────────────────────────────────────────────────┐
│ Individuals Tab (Cross-Video Mode)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─[Super-Individual #1]──────────────────────────────────┐│
│  │ 👤 Male, 25-35 [🔵 3 batches merged]                   ││  <- Level 1: Merged
│  │ Confidence: 94.2% | 127 detections                     ││     (Blue badge + chip)
│  │ ▼ Expand to see constituent MVR people                 ││     Elevation: 4
│  └─────────────────────────────────────────────────────────┘│
│     └─[MVR Person from Batch 1]──────────────────────────┐ │
│       │ 👤 Confidence: 92% | 45 detections               │ │  <- Level 2: MVR People
│       │ ▼ Expand to see person objects                   │ │
│       └──────────────────────────────────────────────────┘ │
│          └─[Person Object #234]──────────────────────┐     │
│            │ Frame 1523 | Conf: 0.89                 │     │  <- Level 3: Objects
│            │ Bbox: [120, 340, 89, 210]               │     │
│            └─────────────────────────────────────────┘     │
│                                                             │
│  ┌─[Standalone Individual #2]─────────────────────────────┐│
│  │ 👤 Female, 35-45 [⚫ Standalone individual]            ││  <- Level 1: Standalone
│  │ Confidence: 91.5% | 23 detections                     ││     (Grey badge + chip)
│  │ ▼ Expand to see person objects                        ││     Elevation: 4
│  └─────────────────────────────────────────────────────────┘│
│     └─[Person Object #567]──────────────────────────┐      │
│       │ Frame 892 | Conf: 0.87                      │      │  <- Level 2: Objects
│       │ Bbox: [200, 180, 95, 220]                  │      │     (No MVR level for
│       └─────────────────────────────────────────────┘      │      standalone)
│                                                             │
│  ┌─[Super-Individual #3]──────────────────────────────────┐│
│  │ 👤 Male, 40-50 [🔵 2 batches merged]                   ││  <- Level 1: Merged
│  │ Confidence: 89.1% | 78 detections                      ││
│  │ ▼ Expand to see constituent MVR people                 ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘

**Visual Legend:**
🔵 Blue badge = Merged super-individual (3-tier: Super → MVR → Objects)
⚫ Grey badge = Standalone individual (2-tier: Individual → Objects)
Both types: Same elevation (4), same Level 1 positioning
```

## Three-Tier Hierarchy Details

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TIER 1: Super-Individual                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 👤 John (Male, Age 30-40)                                       │ │
│  │ 📊 Statistics:                                                  │ │
│  │    • 158 total appearances                                      │ │
│  │    • 15 videos (5 per batch × 3 batches)                       │ │
│  │    • 3 batches merged                                           │ │
│  │ 🎯 Best Quality: 0.92                                          │ │
│  │ 🔗 Featured MVR: MVR Person C                                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│       │                                                               │
│       │ [Click to expand...]                                        │
│       ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              TIER 2: Merged MVR People                         │ │
│  │ ┌──────────────────────────────────────────────────────────────┐│
│  │ │ 📦 MVR Person C (Batch 3) - Featured                         ││
│  │ │    • Quality: 0.92                                            ││
│  │ │    • Videos: 11-15                                            ││
│  │ │    • 61 detections                                            ││
│  │ │    • 2 individuals                                            ││
│  │ │    • Similarity to featured: 1.00 (self)                      ││
│  │ └──────────────────────────────────────────────────────────────┘│
│  │       │                                                           │
│  │       │ [Click to expand...]                                    │
│  │       ▼                                                           │
│  │  ┌────────────────────────────────────────────────────────────┐ │
│  │  │         TIER 3: Individuals & Person Objects               │ │
│  │  │ ┌────────────────────────────────────────────────────────┐ │ │
│  │  │ │ 📹 Video 11: usb_camera_0_segment_11.mp4              │ │ │
│  │  │ │    • Individual UUID: ind-abc-123                      │ │ │
│  │  │ │    • 32 person objects (frame detections)              │ │ │
│  │  │ │    • First seen: 00:05.2                               │ │ │
│  │  │ │    • Last seen: 00:28.7                                │ │ │
│  │  │ └────────────────────────────────────────────────────────┘ │ │
│  │  │ ┌────────────────────────────────────────────────────────┐ │ │
│  │  │ │ 📹 Video 12: usb_camera_0_segment_12.mp4              │ │ │
│  │  │ │    • Individual UUID: ind-def-456                      │ │ │
│  │  │ │    • 29 person objects (frame detections)              │ │ │
│  │  │ │    • First seen: 00:02.1                               │ │ │
│  │  │ │    • Last seen: 00:27.3                                │ │ │
│  │  │ └────────────────────────────────────────────────────────┘ │ │
│  │  └────────────────────────────────────────────────────────────┘ │
│  │                                                                   │
│  │ ┌──────────────────────────────────────────────────────────────┐│
│  │ │ 📦 MVR Person B (Batch 2)                                    ││
│  │ │    • Quality: 0.78                                            ││
│  │ │    • Videos: 6-10                                             ││
│  │ │    • 52 detections                                            ││
│  │ │    • 2 individuals                                            ││
│  │ │    • Similarity to featured: 0.87                             ││
│  │ │    • Status: Merged into C                                   ││
│  │ └──────────────────────────────────────────────────────────────┘│
│  │                                                                   │
│  │ ┌──────────────────────────────────────────────────────────────┐│
│  │ │ 📦 MVR Person A (Batch 1)                                    ││
│  │ │    • Quality: 0.85                                            ││
│  │ │    • Videos: 1-5                                              ││
│  │ │    • 45 detections                                            ││
│  │ │    • 2 individuals                                            ││
│  │ │    • Similarity to featured: 0.89                             ││
│  │ │    • Status: Merged into C                                   ││
│  │ └──────────────────────────────────────────────────────────────┘│
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│               TIER 1: Standalone Individual (2-tier)                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 👤 Sarah (Female, Age 35-45)                                   │ │
│  │ ⚫ Standalone individual (no matches found)                     │ │
│  │ 📊 Statistics:                                                  │ │
│  │    • 23 total appearances                                       │ │
│  │    • 5 videos (single batch)                                   │ │
│  │    • 1 MVR person (not merged)                                 │ │
│  │ 🎯 Quality: 0.87                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│       │                                                               │
│       │ [Click to expand...]                                        │
│       ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              TIER 2: Person Objects (Direct)                   │ │
│  │ ┌────────────────────────────────────────────────────────────┐ │ │
│  │ │ 📹 Video 16: usb_camera_0_segment_16.mp4                  │ │ │
│  │ │    • Individual UUID: ind-xyz-789                          │ │ │
│  │ │    • 8 person objects (frame detections)                   │ │ │
│  │ │    • First seen: 00:03.1                                   │ │ │
│  │ │    • Last seen: 00:15.8                                    │ │ │
│  │ └────────────────────────────────────────────────────────────┘ │ │
│  │ ┌────────────────────────────────────────────────────────────┐ │ │
│  │ │ 📹 Video 17: usb_camera_0_segment_17.mp4                  │ │ │
│  │ │    • Individual UUID: ind-uvw-456                          │ │ │
│  │ │    • 6 person objects (frame detections)                   │ │ │
│  │ │    • First seen: 00:01.5                                   │ │ │
│  │ │    • Last seen: 00:22.4                                    │ │ │
│  │ └────────────────────────────────────────────────────────────┘ │ │
│  │ ┌────────────────────────────────────────────────────────────┐ │ │
│  │ │ 📹 Video 18: usb_camera_0_segment_18.mp4                  │ │ │
│  │ │    • Individual UUID: ind-rst-123                          │ │ │
│  │ │    • 9 person objects (frame detections)                   │ │ │
│  │ │    • First seen: 00:04.2                                   │ │ │
│  │ │    • Last seen: 00:28.9                                    │ │ │
│  │ └────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

**Key Differences:**
- Merged (Blue 🔵): 3-tier hierarchy (Super → MVR → Objects)
- Standalone (Grey ⚫): 2-tier hierarchy (Individual → Objects)
- Both shown at same Level 1 with equal visual weight (elevation 4)
```

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INITIATES SEARCH                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  Collections Screen (Flutter)                       │
        │  • User selects date range                          │
        │  • Clicks "Apply"                                   │
        └────────────────────┬───────────────────────────────┘
                             │
                             │ POST /api/v1/mvr-people/search/by-collection
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  VMeta Service (Backend)                           │
        │  • Query MVR people in videos                      │
        │  • Returns: 45 MVR people from 3 batches           │
        └────────────────────┬───────────────────────────────┘
                             │
                             │ search_results[]
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  Collections Screen - AUTO-MERGE (NEW!)            │
        │  POST /api/v1/mvr-people/merge/hierarchical        │
        │  • Input: 45 MVR UUIDs                             │
        │  • Input: similarity_threshold = 0.70              │
        └────────────────────┬───────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  HierarchicalMVRMerger Service (NEW!)              │
        │                                                     │
        │  Step 1: Extract face embeddings                   │
        │  └─ 45 MVR × 128-dim vectors                       │
        │                                                     │
        │  Step 2: Calculate similarity matrix               │
        │  └─ 45×45 = 2,025 comparisons                      │
        │  └─ Cosine similarity for each pair                │
        │                                                     │
        │  Step 3: Find merge groups                         │
        │  └─ Union-Find algorithm                           │
        │  └─ Group MVR with similarity > 0.70               │
        │  └─ Result: 15 groups found                        │
        │                                                     │
        │  Step 4: Execute merges within each group          │
        │  └─ Group 1: [A, B, C] → Winner: C (quality 0.92) │
        │  └─ Mark A and B as orphaned                       │
        │  └─ Update A.merged_into_mvr_uuid = C              │
        │  └─ Update B.merged_into_mvr_uuid = C              │
        │                                                     │
        │  Returns: 15 super-individual UUIDs                │
        └────────────────────┬───────────────────────────────┘
                             │
                             │ {super_individuals: [...], merge_groups: [...]}
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  Collections Screen - Display Results              │
        │  • Shows: "158 appearances → 15 unique people"     │
        │  • Badge: "30 MVR merged into 15 super-individuals"│
        │  • Enables "Analysis" button                        │
        └────────────────────┬───────────────────────────────┘
                             │
                             │ User clicks "Analysis"
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  Navigate to PersonObjectsDetailScreen             │
        │  • Pass: super_individual_uuids (15 UUIDs)         │
        │  • Pass: merge_groups (hierarchy data)             │
        │  • Pass: sessionData with merge statistics         │
        └────────────────────┬───────────────────────────────┘
                             │
                             │ For each super-individual UUID
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  GET /api/v1/mvr-people/super-individual/{uuid}/   │
        │      hierarchy                                      │
        │                                                     │
        │  Returns:                                           │
        │  • super_individual: Featured MVR (C)              │
        │  • merged_mvr_people: [A, B]                       │
        │  • all_individuals: 6 individuals                  │
        │  • total_person_objects: 158 detections            │
        └────────────────────┬───────────────────────────────┘
                             │
                             │ Render hierarchical UI
                             ▼
        ┌────────────────────────────────────────────────────┐
        │  Individuals Tab - Hierarchical Display            │
        │                                                     │
        │  📂 Super-Individual Card (Collapsed)              │
        │  ├─ Thumbnail: Best quality face                   │
        │  ├─ 🔵 Badge: "3 batches merged"                   │
        │  ├─ Stats: 158 appearances, 15 videos              │
        │  └─ [Expand ▼]                                     │
        │                                                     │
        │  📂 Super-Individual Card (Expanded)               │
        │  ├─ 📦 MVR Person C (Batch 3) [Featured]          │
        │  │   └─ [Expand to show 2 individuals...]          │
        │  ├─ 📦 MVR Person B (Batch 2) [Similarity: 0.87]  │
        │  │   └─ [Expand to show 2 individuals...]          │
        │  └─ 📦 MVR Person A (Batch 1) [Similarity: 0.89]  │
        │      └─ [Expand to show 2 individuals...]          │
        │                                                     │
        │  📂 Standalone Individual Card (Collapsed)         │
        │  ├─ Thumbnail: Face from single batch              │
        │  ├─ ⚫ Badge: "Standalone individual"               │
        │  ├─ Stats: 23 appearances, 5 videos                │
        │  └─ [Expand ▼]                                     │
        │                                                     │
        │  📂 Standalone Individual Card (Expanded)          │
        │  └─ 📹 Person Objects (23 total)                   │
        │      ├─ Video 1: 8 detections                      │
        │      ├─ Video 2: 6 detections                      │
        │      └─ Video 3: 9 detections                      │
        └────────────────────────────────────────────────────┘

Legend:
  🔵 Blue badge = Merged super-individual (3-tier hierarchy)
  ⚫ Grey badge = Standalone individual (2-tier hierarchy)
```

## Database Schema (No Changes!)

```sql
┌─────────────────────────────────────────────────────────────────────┐
│                    mvr_people TABLE (EXISTING)                       │
├─────────────────────────────────────────────────────────────────────┤
│ mvr_people_uuid         UUID PRIMARY KEY                             │
│ featured_individual_uuid UUID NOT NULL                               │
│ face_embedding          BYTEA (128-dim vector)                       │
│ quality_score           FLOAT                                        │
│ gender                  VARCHAR(20)                                  │
│ age_range               VARCHAR(20)                                  │
│                                                                       │
│ ✅ ALREADY EXISTS: Merge tracking fields                             │
│ ├─ is_orphaned          BOOLEAN DEFAULT FALSE                        │
│ │   └─ TRUE when merged into another MVR                            │
│ │                                                                     │
│ ├─ orphaned_at          TIMESTAMP                                    │
│ │   └─ When merge occurred                                          │
│ │                                                                     │
│ ├─ merged_into_mvr_uuid UUID                                         │
│ │   └─ Points to the winner/super-individual                        │
│ │   └─ Example: A.merged_into_mvr_uuid = C (A merged into C)        │
│ │                                                                     │
│ └─ previous_individual_uuids JSONB                                   │
│     └─ Array of individual UUIDs that were merged                    │
│                                                                       │
│ created_at              TIMESTAMP DEFAULT NOW()                      │
│ updated_at              TIMESTAMP DEFAULT NOW()                      │
└─────────────────────────────────────────────────────────────────────┘

Example Data After Merge:
┌────────────────────────────────────────────────────────────────────┐
│ MVR Person C (Super-Individual / Winner)                            │
├────────────────────────────────────────────────────────────────────┤
│ mvr_people_uuid:         uuid-C                                     │
│ quality_score:           0.92                                       │
│ is_orphaned:             FALSE ✅ (Active super-individual)          │
│ merged_into_mvr_uuid:    NULL                                       │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ MVR Person A (Merged)                                               │
├────────────────────────────────────────────────────────────────────┤
│ mvr_people_uuid:         uuid-A                                     │
│ quality_score:           0.85                                       │
│ is_orphaned:             TRUE ❌ (Merged into C)                     │
│ orphaned_at:             2025-12-15 14:30:00                        │
│ merged_into_mvr_uuid:    uuid-C ➡️  (Points to super-individual)    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ MVR Person B (Merged)                                               │
├────────────────────────────────────────────────────────────────────┤
│ mvr_people_uuid:         uuid-B                                     │
│ quality_score:           0.78                                       │
│ is_orphaned:             TRUE ❌ (Merged into C)                     │
│ orphaned_at:             2025-12-15 14:30:00                        │
│ merged_into_mvr_uuid:    uuid-C ➡️  (Points to super-individual)    │
└────────────────────────────────────────────────────────────────────┘

Query to Get Hierarchy:
SELECT * FROM mvr_people 
WHERE mvr_people_uuid = 'uuid-C'  -- Get super-individual
   OR merged_into_mvr_uuid = 'uuid-C'  -- Get merged MVR people
ORDER BY quality_score DESC;
```

## Similarity Matrix Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│           SIMILARITY MATRIX (Example: 6 MVR People)                  │
└─────────────────────────────────────────────────────────────────────┘

        A      B      C      D      E      F
    ┌──────┬──────┬──────┬──────┬──────┬──────┐
  A │ 1.00 │ 0.87 │ 0.89 │ 0.45 │ 0.52 │ 0.41 │
    ├──────┼──────┼──────┼──────┼──────┼──────┤
  B │ 0.87 │ 1.00 │ 0.84 │ 0.48 │ 0.49 │ 0.39 │
    ├──────┼──────┼──────┼──────┼──────┼──────┤
  C │ 0.89 │ 0.84 │ 1.00 │ 0.43 │ 0.51 │ 0.44 │
    ├──────┼──────┼──────┼──────┼──────┼──────┤
  D │ 0.45 │ 0.48 │ 0.43 │ 1.00 │ 0.92 │ 0.88 │
    ├──────┼──────┼──────┼──────┼──────┼──────┤
  E │ 0.52 │ 0.49 │ 0.51 │ 0.92 │ 1.00 │ 0.91 │
    ├──────┼──────┼──────┼──────┼──────┼──────┤
  F │ 0.41 │ 0.39 │ 0.44 │ 0.88 │ 0.91 │ 1.00 │
    └──────┴──────┴──────┴──────┴──────┴──────┘

Threshold: 0.70

Merge Groups Found:
┌─────────────────────────────────────────────────────┐
│ Group 1: [A, B, C]                                  │
│ • A ↔ B: 0.87 ✅                                     │
│ • A ↔ C: 0.89 ✅                                     │
│ • B ↔ C: 0.84 ✅                                     │
│ → Merge into C (quality: 1.00)                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Group 2: [D, E, F]                                  │
│ • D ↔ E: 0.92 ✅                                     │
│ • D ↔ F: 0.88 ✅                                     │
│ • E ↔ F: 0.91 ✅                                     │
│ → Merge into E (quality: 1.00)                      │
└─────────────────────────────────────────────────────┘

Result: 6 MVR people → 2 super-individuals
```

## Performance Optimization

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE STRATEGY                              │
└─────────────────────────────────────────────────────────────────────┘

Input: N MVR People
Complexity: O(N²) similarity comparisons

Example: N = 500
├─ Comparisons: 500 × 500 = 250,000
├─ Time (naive): ~60 seconds
└─ Time (optimized): ~15 seconds

Optimizations:
┌─────────────────────────────────────────────────────────────────┐
│ 1. Early Termination                                            │
│    • Skip if similarity < 0.50 (clearly different people)       │
│    • Reduces comparisons by ~70%                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. Batch Processing                                             │
│    • Process 100 MVR at a time                                  │
│    • Prevents memory overflow                                   │
│    • Parallel batch processing (3 workers)                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. Sparse Matrix Storage                                        │
│    • Only store similarities > 0.50                             │
│    • Reduces memory: 250K → 75K entries (~70% reduction)        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. Union-Find Optimization                                      │
│    • Path compression: O(α(n)) ≈ O(1)                          │
│    • Find merge groups in near-linear time                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 5. Database Query Optimization                                  │
│    • Single recursive CTE for full hierarchy                    │
│    • Fetch all levels in one query (not N queries)             │
│    • Index on merged_into_mvr_uuid                              │
└─────────────────────────────────────────────────────────────────┘

Final Performance:
├─ 500 MVR people: ~15-20 seconds
├─ 1000 MVR people: ~45-60 seconds (with approximate methods)
└─ Memory: < 300 MB
```

---

**See full technical details**: [HIERARCHICAL_MVR_PEOPLE_MERGING.md](./HIERARCHICAL_MVR_PEOPLE_MERGING.md)

**Executive Summary**: [HIERARCHICAL_MVR_MERGING_SUMMARY.md](./HIERARCHICAL_MVR_MERGING_SUMMARY.md)
