# Option B Implementation Plan: Batch Match & Merge Endpoint

**Date:** November 1, 2025  
**Status:** Ready for Implementation  
**Approach:** Add new endpoint WITHOUT modifying existing code

---

## Strategy: Additive Only (No Modifications)

### What We Will NOT Touch:

- ❌ `GET /api/v1/cross-video/sessions/{uuid}` - Leave unchanged
- ❌ `GET /api/v1/cross-video/sessions/{uuid}/individuals` - Leave unchanged  
- ❌ `POST /api/v1/mvr-people/individuals/{uuid}/match` - Leave unchanged
- ❌ `POST /api/v1/mvr-people/merge` - Leave unchanged
- ❌ Flutter `collections_screen.dart` - Leave unchanged (for now)
- ❌ Database `tracking_sessions` table - Leave unchanged (we have the column, just don't use it yet)

### What We WILL Add:

- ✅ **NEW** endpoint: `POST /api/v1/mvr-people/batch-match-and-merge`
- ✅ **NEW** Pydantic request/response models
- ✅ **NEW** Flutter service method to call batch endpoint
- ✅ **NEW** Flutter UI component to show comparison (optional, separate from existing)

---

## Implementation Steps

### Step 1: Add Pydantic Models (New File)

**File:** `ppl-meta-vmeta/src/api/models/batch_merge.py` (NEW)

```python
"""
Batch Match & Merge Models
Pydantic models for batch matching and merging of individuals.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class BatchMatchAndMergeRequest(BaseModel):
    """Request to batch match and merge individuals."""
    
    individual_uuids: List[UUID] = Field(
        ...,
        min_items=1,
        description="List of individual UUIDs to match and merge"
    )
    threshold: Optional[float] = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for matching (0.0-1.0)"
    )
    triggered_by: Optional[str] = Field(
        default="batch_auto_match",
        description="Source that triggered the merge"
    )
    session_uuid: Optional[UUID] = Field(
        default=None,
        description="Optional tracking session UUID for audit trail"
    )


class MergeDetail(BaseModel):
    """Details of a single merge operation."""
    
    predominant_individual_uuid: UUID
    orphaned_individual_uuid: UUID
    predominant_mvr_uuid: UUID
    orphaned_mvr_uuid: UUID
    similarity_score: float
    merged_at: datetime


class BatchMatchAndMergeResponse(BaseModel):
    """Response from batch match and merge operation."""
    
    success: bool
    original_count: int = Field(
        ...,
        description="Number of individuals before merging"
    )
    unique_count: int = Field(
        ...,
        description="Number of unique individuals after merging"
    )
    merge_count: int = Field(
        ...,
        description="Number of individuals that were merged (orphaned)"
    )
    merges: List[MergeDetail] = Field(
        default_factory=list,
        description="Details of each merge operation"
    )
    skipped_count: int = Field(
        default=0,
        description="Number of individuals skipped due to errors"
    )
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time in seconds"
    )
    message: Optional[str] = None


class BatchMatchAndMergeError(BaseModel):
    """Error response for batch operations."""
    
    success: bool = False
    error: str
    original_count: int
    unique_count: int
    partial_results: Optional[BatchMatchAndMergeResponse] = None
```

---

### Step 2: Add Batch Merge Endpoint (Extend Existing Router)

**File:** `ppl-meta-vmeta/src/api/routes/mvr_people.py`

**Location:** Add at end of file, before any closing statements

```python
# ============================================================================
# ENDPOINT 15: Batch Match and Merge Individuals
# ============================================================================

@router.post(
    "/batch-match-and-merge",
    response_model=BatchMatchAndMergeResponse,
    summary="Batch Match and Merge Individuals",
    description="Batch operation to match and merge multiple individuals from a tracking session",
)
async def batch_match_and_merge(
    request: BatchMatchAndMergeRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Batch match and merge all individuals from a tracking session.
    
    This endpoint:
    1. Takes a list of individual UUIDs (from tracking session)
    2. For each individual, finds matching individuals (face similarity)
    3. Merges duplicates above the similarity threshold
    4. Returns original count vs unique count
    
    **Use Case:** Get unique individual count after cross-video tracking
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuids: List of individual UUIDs to process
    - threshold: Similarity threshold (default: 0.85)
    - triggered_by: Source identifier (default: "batch_auto_match")
    - session_uuid: Optional tracking session UUID for audit
    
    **Returns:**
    - 200 OK: Batch merge completed with statistics
    - 400 Bad Request: Invalid request (empty list, invalid UUIDs)
    - 500 Internal Server Error: Processing failed
    
    **Example:**
    ```
    POST /api/v1/mvr-people/batch-match-and-merge
    {
      "individual_uuids": ["uuid-1", "uuid-2", ..., "uuid-15"],
      "threshold": 0.85,
      "triggered_by": "cross_video_tracking_session",
      "session_uuid": "session-abc-123"
    }
    
    Response:
    {
      "success": true,
      "original_count": 15,
      "unique_count": 12,
      "merge_count": 3,
      "merges": [...],
      "processing_time_seconds": 2.34
    }
    ```
    """
    import time
    start_time = time.time()
    
    logger.info(
        f"Batch match and merge: {len(request.individual_uuids)} individuals "
        f"(threshold: {request.threshold}, user: {current_user.get('email')})"
    )
    
    original_count = len(request.individual_uuids)
    processed_individuals = set()
    merge_count = 0
    merges = []
    skipped_count = 0
    
    try:
        # Process each individual
        for individual_uuid in request.individual_uuids:
            individual_uuid_str = str(individual_uuid)
            
            # Skip if already processed (was orphaned in a previous merge)
            if individual_uuid_str in processed_individuals:
                logger.debug(f"Skipping {individual_uuid_str} (already processed)")
                continue
            
            try:
                # Find matches for this individual
                matches = await mvr_matcher.find_matching_mvr(
                    individual_uuid=individual_uuid_str,
                    threshold=request.threshold,
                )
                
                logger.debug(
                    f"Found {len(matches)} potential matches for {individual_uuid_str}"
                )
                
                # Merge each match above threshold
                for match in matches:
                    match_uuid = str(match.get('individual_uuid'))
                    similarity = match.get('similarity_score', 0.0)
                    
                    # Skip if already processed
                    if match_uuid in processed_individuals:
                        continue
                    
                    # Only merge if above threshold
                    if similarity >= request.threshold:
                        logger.info(
                            f"Merging {individual_uuid_str} with {match_uuid} "
                            f"(similarity: {similarity:.3f})"
                        )
                        
                        try:
                            # Execute merge
                            merge_result = await mvr_matcher.merge_individuals(
                                individual_a_uuid=individual_uuid_str,
                                individual_b_uuid=match_uuid,
                                similarity_score=similarity,
                                triggered_by=request.triggered_by,
                            )
                            
                            if merge_result and merge_result.get('success'):
                                # Track the orphaned individual
                                orphaned_mvr_uuid = merge_result.get('orphaned_mvr_uuid')
                                predominant_mvr_uuid = merge_result.get('predominant_mvr_uuid')
                                reassigned_uuid = merge_result.get('reassigned_individual_uuid')
                                
                                processed_individuals.add(str(reassigned_uuid))
                                merge_count += 1
                                
                                # Record merge details
                                merges.append(MergeDetail(
                                    predominant_individual_uuid=individual_uuid,
                                    orphaned_individual_uuid=match_uuid,
                                    predominant_mvr_uuid=predominant_mvr_uuid,
                                    orphaned_mvr_uuid=orphaned_mvr_uuid,
                                    similarity_score=similarity,
                                    merged_at=merge_result.get('merged_at', datetime.now()),
                                ))
                                
                                logger.info(
                                    f"Successfully merged: {reassigned_uuid} is now orphaned"
                                )
                            else:
                                logger.warning(
                                    f"Merge failed for {individual_uuid_str} and {match_uuid}"
                                )
                                skipped_count += 1
                                
                        except Exception as merge_error:
                            logger.error(
                                f"Error merging {individual_uuid_str} with {match_uuid}: {merge_error}"
                            )
                            skipped_count += 1
                            # Continue with next match
                            continue
                
                # Mark current individual as processed
                processed_individuals.add(individual_uuid_str)
                
            except Exception as match_error:
                logger.error(
                    f"Error finding matches for {individual_uuid_str}: {match_error}"
                )
                skipped_count += 1
                # Continue with next individual
                continue
        
        # Calculate final counts
        unique_count = original_count - merge_count
        processing_time = time.time() - start_time
        
        logger.info(
            f"Batch merge complete: {original_count} → {unique_count} unique "
            f"({merge_count} merged, {skipped_count} skipped) in {processing_time:.2f}s"
        )
        
        return BatchMatchAndMergeResponse(
            success=True,
            original_count=original_count,
            unique_count=unique_count,
            merge_count=merge_count,
            merges=merges,
            skipped_count=skipped_count,
            processing_time_seconds=round(processing_time, 2),
            message=f"Successfully merged {merge_count} duplicates from {original_count} individuals",
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Batch merge failed: {e}", exc_info=True)
        
        # Return partial results if we made any progress
        if merge_count > 0:
            unique_count = original_count - merge_count
            return BatchMatchAndMergeResponse(
                success=False,
                original_count=original_count,
                unique_count=unique_count,
                merge_count=merge_count,
                merges=merges,
                skipped_count=skipped_count,
                processing_time_seconds=round(processing_time, 2),
                message=f"Partial completion: {merge_count} merged before error: {str(e)}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch merge failed: {str(e)}"
            )
```

---

### Step 3: Import New Models in Router

**File:** `ppl-meta-vmeta/src/api/routes/mvr_people.py`

**Location:** In the imports section at the top

```python
# Add to existing imports
from api.models.batch_merge import (
    BatchMatchAndMergeRequest,
    BatchMatchAndMergeResponse,
    MergeDetail,
)
```

---

### Step 4: Flutter Service Method (New, Optional)

**File:** `ppl-meta-frontend/lib/services/vmeta_service.dart` (or wherever API calls are)

```dart
/// Batch match and merge individuals from a tracking session
Future<ApiResponse<Map<String, dynamic>>> batchMatchAndMerge({
  required List<String> individualUuids,
  double threshold = 0.85,
  String triggeredBy = 'cross_video_tracking_session',
  String? sessionUuid,
}) async {
  try {
    final response = await _apiClient.post(
      '/api/v1/mvr-people/batch-match-and-merge',
      data: {
        'individual_uuids': individualUuids,
        'threshold': threshold,
        'triggered_by': triggeredBy,
        if (sessionUuid != null) 'session_uuid': sessionUuid,
      },
    );
    
    return ApiResponse.success(response.data);
  } catch (e) {
    return ApiResponse.error('Failed to batch merge individuals: $e');
  }
}
```

---

### Step 5: Flutter Usage Example (New Component)

**File:** `ppl-meta-frontend/lib/screens/collection_comparison_widget.dart` (NEW)

```dart
/// Widget to show original count vs unique count comparison
class IndividualCountComparison extends StatefulWidget {
  final String sessionUuid;
  final int originalCount;
  
  const IndividualCountComparison({
    Key? key,
    required this.sessionUuid,
    required this.originalCount,
  }) : super(key: key);
  
  @override
  State<IndividualCountComparison> createState() => _IndividualCountComparisonState();
}

class _IndividualCountComparisonState extends State<IndividualCountComparison> {
  int? _uniqueCount;
  bool _isProcessing = false;
  String? _errorMessage;
  
  Future<void> _calculateUniqueCount() async {
    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });
    
    try {
      // Step 1: Get individuals from session
      final individualsResponse = await _vmetaService.getSessionIndividuals(
        sessionUuid: widget.sessionUuid,
      );
      
      if (!individualsResponse.success) {
        throw Exception('Failed to fetch individuals');
      }
      
      final individuals = individualsResponse.data!['individuals'] as List;
      final individualUuids = individuals
          .map((i) => i['individual_uuid'] as String)
          .toList();
      
      // Step 2: Batch match and merge
      final mergeResponse = await _vmetaService.batchMatchAndMerge(
        individualUuids: individualUuids,
        threshold: 0.85,
        triggeredBy: 'cross_video_tracking_session',
        sessionUuid: widget.sessionUuid,
      );
      
      if (!mergeResponse.success) {
        throw Exception('Batch merge failed');
      }
      
      final uniqueCount = mergeResponse.data!['unique_count'] as int;
      final mergeCount = mergeResponse.data!['merge_count'] as int;
      
      setState(() {
        _uniqueCount = uniqueCount;
        _isProcessing = false;
      });
      
      print('✅ Batch merge complete: ${widget.originalCount} → $uniqueCount unique ($mergeCount merged)');
      
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isProcessing = false;
      });
      
      print('❌ Batch merge error: $e');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Original count
        Text(
          '${widget.originalCount}',
          style: AppTextStyles.bodyMedium.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        
        Text(' → ', style: AppTextStyles.bodyMedium),
        
        // Unique count
        if (_isProcessing)
          Row(
            children: [
              SizedBox(
                width: 12,
                height: 12,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              SizedBox(width: 4),
              Text('calculating...', style: TextStyle(color: AppColors.warning)),
            ],
          )
        else if (_errorMessage != null)
          Text(
            '[]',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.error,
              fontWeight: FontWeight.w700,
            ),
          )
        else if (_uniqueCount != null)
          Text(
            '$_uniqueCount unique',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.success,
              fontWeight: FontWeight.w700,
            ),
          )
        else
          TextButton(
            onPressed: _calculateUniqueCount,
            child: Text('Calculate'),
          ),
      ],
    );
  }
}
```

---

## Testing Plan

### Test 1: No Duplicates
```bash
curl -X POST http://localhost:8008/api/v1/mvr-people/batch-match-and-merge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "individual_uuids": ["uuid-1", "uuid-2", "uuid-3", "uuid-4", "uuid-5"],
    "threshold": 0.85
  }'

# Expected: original_count=5, unique_count=5, merge_count=0
```

### Test 2: Some Duplicates
```bash
# Assuming uuid-2 and uuid-4 are same person
curl -X POST http://localhost:8008/api/v1/mvr-people/batch-match-and-merge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "individual_uuids": ["uuid-1", "uuid-2", "uuid-3", "uuid-4", "uuid-5"],
    "threshold": 0.85
  }'

# Expected: original_count=5, unique_count=4, merge_count=1
```

### Test 3: All Duplicates
```bash
# Assuming all 5 are same person
curl -X POST http://localhost:8008/api/v1/mvr-people/batch-match-and-merge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "individual_uuids": ["uuid-1", "uuid-2", "uuid-3", "uuid-4", "uuid-5"],
    "threshold": 0.85
  }'

# Expected: original_count=5, unique_count=1, merge_count=4
```

### Test 4: Error Handling
```bash
# Invalid UUID
curl -X POST http://localhost:8008/api/v1/mvr-people/batch-match-and-merge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "individual_uuids": ["invalid-uuid"],
    "threshold": 0.85
  }'

# Expected: 400 Bad Request or partial results
```

---

## Deployment Checklist

- [ ] Create new models file: `api/models/batch_merge.py`
- [ ] Add endpoint to: `api/routes/mvr_people.py`
- [ ] Import models in router
- [ ] Restart vmeta service
- [ ] Test endpoint with curl
- [ ] Create Flutter service method (optional)
- [ ] Create Flutter comparison widget (optional)
- [ ] Test end-to-end flow
- [ ] Document in API docs

---

## Success Criteria

1. ✅ Endpoint returns correct counts (original vs unique)
2. ✅ Merges are recorded in database
3. ✅ No modifications to existing endpoints
4. ✅ Existing Flutter UI continues working unchanged
5. ✅ New endpoint can be called independently
6. ✅ Performance: <5 seconds for 100 individuals

---

## Timeline

- **Backend implementation:** 3-4 hours
- **Testing:** 1-2 hours
- **Flutter integration (optional):** 2-3 hours
- **Total:** 6-9 hours

---

**Next Step:** Implement the backend endpoint first, test it, then decide if we want to add Flutter integration now or later.
