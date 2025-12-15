# Hierarchical MVR People Merging - Executive Summary

**Created**: December 15, 2025  
**Status**: Proposal  
**Full Proposal**: [HIERARCHICAL_MVR_PEOPLE_MERGING.md](./HIERARCHICAL_MVR_PEOPLE_MERGING.md)

---

## Problem

When searching a collection, MVR people from different batches (5 videos each) may represent the same person, causing duplicates in the Cross-Video Individual Analysis screen.

**Example**:
- Videos 1-5 → Batch 1 → Creates MVR Person A
- Videos 6-10 → Batch 2 → Creates MVR Person B  
- **Issue**: Person A and Person B are the SAME PERSON but appear as 2 separate entries

---

## Proposed Solution

### Three-Tier Hierarchy (Plus Standalone)

```
🔵 LEVEL 1: Super-Individual (Merged) - Blue badge
   └── 🔹 LEVEL 2: MVR Person (Individual)
       └── 🔹 LEVEL 3: Person Objects (detections)

⚫ LEVEL 1: Standalone Individual - Grey badge
   └── 🔹 LEVEL 2: Person Objects (detections)
```

**Visual Distinction**:
- **Blue badge** (🔵): Merged super-individual with "X batches merged" chip
- **Grey badge** (⚫): Standalone individual with "Standalone individual" chip
- Both shown at same Level 1 with equal visual weight

### Automatic Post-Search Merging

1. User searches collection → Get all MVR people
2. **NEW**: Calculate similarity between all MVR people
3. **NEW**: Auto-merge MVR people with similarity > threshold (e.g., 0.70)
4. **NEW**: Display hierarchical structure showing merge relationships
5. User sees unique people instead of duplicates

---

## Key Benefits

✅ **Automatic Deduplication**: Same person across batches shown once  
✅ **Clear Visual Distinction**: Blue badges for merged, grey for standalone  
✅ **User Control**: Adjustable similarity threshold (0.60-0.90)  
✅ **Full Provenance**: Track which MVR people were merged  
✅ **Backward Compatible**: Works with existing 2-level hierarchy  
✅ **No Schema Changes**: Reuses existing merge tracking fields

---

## Technical Approach

### Database (No Changes!)

**Reuse existing schema**:
- `merged_into_mvr_uuid`: Already tracks merge target
- `is_orphaned`: Already marks merged MVR people
- `previous_individual_uuids`: Already tracks merge history

### Backend (New Components)

1. **Service**: `HierarchicalMVRMerger`
   - Similarity matrix calculation (O(N²) optimized)
   - Connected components (Union-Find algorithm)
   - Group merging (highest quality wins)

2. **Endpoints**:
   - `POST /api/v1/mvr-people/merge/hierarchical`
   - `GET /api/v1/mvr-people/super-individual/{uuid}/hierarchy`

### Frontend (Enhanced UI)

1. **Collections Screen**: Auto-merge after search
   - Shows: "500 appearances → 50 individuals → 15 unique people"
 with color-coded badges
   - **🔵 Blue badge** (Merged): Super-individual with "3 batches merged" chip
   - **⚫ Grey badge** (Standalone): Individual with "Standalone individual" chip
   - **Level 1** (Collapsed): Shows best quality face and aggregate stats
   - **Level 2** (Expanded): Shows merged MVR people with similarity scores (merged only)e
   - **Level 2** (Expanded): Shows merged MVR people with similarity scores
   - **Level 3** (Expanded): Shows individuals and person objects per MVR

---

## Example User Flow

### Before (Current)

```
Search collection → See 45 MVR people
Problem: 15 real people × 3 duplicates each = 45 entries
User must manually identify duplicates
```

### After (Proposed)

```
Search collection → Auto-merge similar MVR people
Result: See 15 super-individuals (unique people)
Each super-individual shows:
  └─ 3 merged MVR people (from different batches)
     └─ 5 videos each
        └─ 100+ person object detections
```

---

## Implementation Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1** | Week 1 | Backend core service + unit tests |
| **Phase 2** | Week 2 | API endpoints + integration tests |
| **Phase 3** | Week 3 | Frontend data models + API client |
| **Phase 4** | Week 4 | UI hierarchical display |
| **Phase 5** | Week 5 | Polish, deploy, monitor |

**Total**: 5 weeks

---

## Performance Characteristics

### Similarity Calculation

- **Input**: 500 MVR people
- **Comparisons**: 250,000 (N²/2)
- **Time**: ~15-30 seconds (with optimization)
- **Memory**: ~100-200 MB

### Optimizations

- Batch processing (100 MVR at a time)
- Early termination (skip if similarity < 0.5)
- Sparse matrix storage
- Parallel computation

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-merging (false positives) | Medium | Conservative threshold (0.70), user-adjustable |
| Performance with 1000+ MVR | High | Batch processing, approximate methods |
| Complex UI confuses users | Medium | Clear badges, tooltips, user guide |
| Backward compatibility breaks | High | Graceful fallback, feature flag |

---

## Success Metrics

### Functional

- ✅ 95%+ reduction in duplicates (same person shown once)
- ✅ < 5% over-merge rate (different people merged)
- ✅ Full audit trail (can track merge provenance)

### Performance

- ✅ < 30 seconds for 500 MVR people
- ✅ < 5 seconds UI response time
- ✅ < 500 MB memory usage

### User Experience

- ✅ 90%+ user satisfaction (post-launch survey)
- ✅ < 2 minutes to understand hierarchy (user testing)
- ✅ < 3 clicks to see full merge details

---

## Recommendation

**APPROVE** this proposal to proceed with implementation.

**Why**:
1. Solves critical duplicate problem
2. No database migration required
3. Backward compatible
4. Clear 5-week implementation path
5. Performance optimized for production scale

**Next Steps**:
1. Review and approval from stakeholders
2. Assign development team
3. Create GitHub issues for each phase
4. Begin Phase 1 implementation

---

## Questions?

Contact: PPL Meta Development Team  
Full Technical Proposal: [HIERARCHICAL_MVR_PEOPLE_MERGING.md](./HIERARCHICAL_MVR_PEOPLE_MERGING.md)
