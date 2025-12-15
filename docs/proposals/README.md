# PPL Meta Platform - Technical Proposals

This directory contains technical proposals for major features and architectural changes to the PPL Meta platform.

---

## Active Proposals

### 1. Hierarchical MVR People Merging

**Status**: 📋 Proposal - Awaiting Approval  
**Created**: December 15, 2025  
**Priority**: High

**Documents**:
- [📄 Executive Summary](./HIERARCHICAL_MVR_MERGING_SUMMARY.md) - 5-minute overview
- [📄 Full Technical Proposal](./HIERARCHICAL_MVR_PEOPLE_MERGING.md) - Complete implementation details
- [📄 Visual Architecture](./HIERARCHICAL_MVR_MERGING_DIAGRAMS.md) - Diagrams and data flow

**Problem**: MVR people from different batches (5 videos each) may represent the same person, causing duplicates in search results.

**Solution**: Implement a 3-tier hierarchical system with automatic post-search merging:
- **Tier 1**: Super-Individuals (merged MVR people across batches)
- **Tier 2**: MVR People (individuals from single batches)
- **Tier 3**: Person Objects (frame-level detections)

**Key Benefits**:
- ✅ 95%+ reduction in duplicates
- ✅ No database schema changes (reuses existing merge fields)
- ✅ Backward compatible
- ✅ User-adjustable similarity threshold

**Timeline**: 5 weeks (5 phases)

**Next Steps**: Review and approval from stakeholders

---

## Proposal Process

### 1. Proposal Creation

Use this template structure:
```
proposals/
├── {FEATURE_NAME}_SUMMARY.md        # Executive summary (1-2 pages)
├── {FEATURE_NAME}_PROPOSAL.md       # Full technical proposal
├── {FEATURE_NAME}_DIAGRAMS.md       # Visual architecture
└── README.md                         # This file
```

### 2. Required Sections

Every proposal should include:

**Executive Summary**:
- Problem statement
- Proposed solution
- Key benefits
- Timeline estimate
- Risks & mitigation

**Full Technical Proposal**:
- Architecture analysis
- Database schema changes
- Backend implementation
- Frontend implementation
- API changes
- Migration strategy
- Testing strategy
- Performance considerations

**Visual Architecture**:
- Data flow diagrams
- UI mockups
- Database schema diagrams
- Sequence diagrams

### 3. Review Process

1. **Draft**: Create proposal documents
2. **Review**: Team reviews and provides feedback
3. **Revise**: Address feedback and update proposal
4. **Approve**: Stakeholders approve for implementation
5. **Implement**: Move to implementation phase
6. **Archive**: Move to `implemented/` directory after completion

### 4. Status Labels

- 📋 **Proposal**: Initial proposal, awaiting review
- 🔍 **Under Review**: Being reviewed by team
- ✏️ **Revising**: Addressing feedback
- ✅ **Approved**: Approved for implementation
- 🚧 **In Progress**: Currently being implemented
- ✅ **Implemented**: Completed and deployed
- ❌ **Rejected**: Not approved for implementation
- ⏸️ **Deferred**: Postponed for future consideration

---

## Proposal Guidelines

### Writing Style

- **Be Clear**: Use simple language, avoid jargon
- **Be Specific**: Provide concrete examples and numbers
- **Be Visual**: Include diagrams and mockups
- **Be Realistic**: Acknowledge risks and limitations
- **Be Thorough**: Cover all technical aspects

### Technical Depth

- **Executive Summary**: High-level, non-technical
- **Full Proposal**: Technical, implementation-focused
- **Diagrams**: Visual, intuitive

### Code Examples

Include code snippets where helpful:
```python
# Bad: Vague description
"Add a method to merge MVR people"

# Good: Concrete implementation
async def merge_mvr_people(
    self,
    mvr_uuids: List[UUID],
    similarity_threshold: float = 0.70
) -> Dict[str, Any]:
    """
    Merge MVR people based on similarity threshold.
    
    Args:
        mvr_uuids: List of MVR UUIDs to merge
        similarity_threshold: Minimum similarity (0.0-1.0)
        
    Returns:
        Dict with merge results and statistics
    """
    # Implementation details...
```

### Performance Analysis

Always include:
- Complexity analysis (Big O notation)
- Expected performance metrics
- Load testing results (if available)
- Optimization strategies

**Example**:
```
Input: N MVR people
Complexity: O(N²) similarity comparisons
Example: N=500 → 250,000 comparisons
Time: ~15-30 seconds (with optimization)
Memory: ~100-200 MB
```

### Risk Assessment

Use this template:

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Over-merging (false positives) | Medium | Low | Conservative threshold, user-adjustable |
| Performance degradation | High | Medium | Batch processing, caching |

---

## Templates

### Executive Summary Template

```markdown
# {Feature Name} - Executive Summary

**Created**: {Date}  
**Status**: {Status Label}

## Problem

{Clear problem statement}

## Proposed Solution

{High-level solution overview}

## Key Benefits

✅ Benefit 1  
✅ Benefit 2  
✅ Benefit 3

## Timeline

{Duration} ({X} phases)

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| ... | ... |

## Recommendation

{Approve/Reject with rationale}
```

### Full Proposal Template

See [HIERARCHICAL_MVR_PEOPLE_MERGING.md](./HIERARCHICAL_MVR_PEOPLE_MERGING.md) as reference.

---

## Past Proposals

### Implemented

*None yet - first proposal in this directory*

### Rejected

*None yet*

### Deferred

*None yet*

---

## Contributing

To create a new proposal:

1. Copy the template structure
2. Fill in all required sections
3. Create visual diagrams
4. Submit for review
5. Update this README with proposal entry

---

**Last Updated**: December 15, 2025  
**Maintained By**: PPL Meta Development Team
