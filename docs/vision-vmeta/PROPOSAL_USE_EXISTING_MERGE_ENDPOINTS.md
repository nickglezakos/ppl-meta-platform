# Proposal: Use Existing MVR-People Merge Endpoints for Unique Counter

**Date:** November 1, 2025  
**Status:** Proposed Alternative Approach  
**Author:** PPL Meta Platform Team

---

## Executive Summary

Instead of modifying the cross-video tracking endpoint, we can use **existing MVR-People merge endpoints** to:
1. Get individuals from cross-video tracking (existing endpoint)
2. Use existing match & merge endpoints to find and merge duplicates
3. Calculate unique count in Flutter by counting non-orphaned individuals

**Benefits:**
- ✅ No backend changes to cross-video tracking
- ✅ Uses proven, existing merge logic
- ✅ Clean separation of concerns
- ✅ Flutter controls when to merge (user-initiated or auto)

---

## Current System Analysis

### Existing Endpoints Available

#### 1. Cross-Video Tracking (Produces Individuals)

**Endpoint:** `GET /api/v1/cross-video/sessions/{session_uuid}/individuals`

**What it returns:**
```json
{
  "session_uuid": "abc-123",
  "total_individuals": 15,
  "individuals": [
    {
      "individual_uuid": "ind-001",
      "individual_id": "IND-001",
      "total_appearances": 5,
      "total_videos": 3,
      "first_seen": "2025-11-01T10:00:00",
      "last_seen": "2025-11-01T10:30:00",
      "confidence_score": 0.92
    },
    // ... 14 more individuals
  ]
}
```

**Status:** ✅ Already working, returns all individuals found

---

#### 2. Match Individual (Find Duplicates)

**Endpoint:** `POST /api/v1/mvr-people/individuals/{individual_uuid}/match`

**What it does:** Finds other individuals with similar faces (face similarity > threshold)

**Request:**
```json
{
  "threshold": 0.85,
  "auto_merge": false,
  "max_results": 10
}
```

**Response:**
```json
{
  "individual_uuid": "ind-001",
  "matches": [
    {
      "individual_uuid": "ind-007",
      "similarity_score": 0.92,
      "confidence": 0.88
    },
    {
      "individual_uuid": "ind-012",
      "similarity_score": 0.87,
      "confidence": 0.85
    }
  ],
  "total_matches": 2,
  "matches_above_threshold": 2,
  "threshold_used": 0.85
}
```

**Status:** ✅ Already implemented and working

---

#### 3. Merge Individuals (Remove Duplicates)

**Endpoint:** `POST /api/v1/mvr-people/merge`

**What it does:** Merges two individuals into one (predominant based on quality)

**Request:**
```json
{
  "individual_a_uuid": "ind-001",
  "individual_b_uuid": "ind-007",
  "similarity_score": 0.92,
  "triggered_by": "auto_match_session"
}
```

**Response:**
```json
{
  "success": true,
  "predominant_mvr_uuid": "mvr-001",
  "orphaned_mvr_uuid": "mvr-007",
  "reassigned_individual_uuid": "ind-007",
  "similarity_score": 0.92,
  "predominant_quality_score": 0.95,
  "orphaned_quality_score": 0.88,
  "merged_at": "2025-11-01T10:35:00",
  "message": "Individual merged successfully"
}
```

**Status:** ✅ Already implemented and working

---

#### 4. Get Merge History

**Endpoint:** `GET /api/v1/mvr-people/individuals/{individual_uuid}/merge-history`

**What it does:** Shows merge history (current + orphaned MVR-People)

**Response:**
```json
{
  "individual_uuid": "ind-007",
  "current_mvr_people": {
    "mvr_uuid": "mvr-001",
    "status": "active"
  },
  "previous_mvr_people": [
    {
      "mvr_uuid": "mvr-007",
      "status": "orphaned",
      "merged_into": "mvr-001",
      "merged_at": "2025-11-01T10:35:00"
    }
  ],
  "merge_events": [...],
  "total_merges": 1
}
```

**Status:** ✅ Already implemented and working

---

## Proposed Implementation Approach

### Option A: Flutter-Side Auto-Merge (Recommended)

**Flow:**
```
1. User creates tracking session
   └─> POST /api/v1/cross-video/sessions
   
2. Poll for completion
   └─> GET /api/v1/cross-video/sessions/{uuid}
   └─> Status: "completed", individuals_found: 15
   
3. Get list of individuals (EXISTING ENDPOINT)
   └─> GET /api/v1/cross-video/sessions/{uuid}/individuals
   └─> Returns 15 individuals
   
4. FOR EACH individual, find matches (EXISTING ENDPOINT)
   └─> POST /api/v1/mvr-people/individuals/{uuid}/match
       {
         "threshold": 0.85,
         "auto_merge": false,
         "max_results": 10
       }
   └─> Returns list of similar individuals
   
5. FOR EACH match, merge duplicates (EXISTING ENDPOINT)
   └─> POST /api/v1/mvr-people/merge
       {
         "individual_a_uuid": "ind-001",
         "individual_b_uuid": "ind-007",
         "similarity_score": 0.92,
         "triggered_by": "auto_match_session"
       }
   └─> Returns merge result
   
6. Re-fetch individuals list
   └─> GET /api/v1/cross-video/sessions/{uuid}/individuals
   └─> Returns 12 individuals (3 were merged)
   
7. Display both counts in UI
   └─> Original count: 15 (from step 2)
   └─> Unique count: 12 (from step 6)
   └─> UI shows: "15 → 12 unique"
```

**Implementation in Flutter:**

```dart
// Step 1: Track original count before merging
int _individualsCountBeforeMerge = 0;
int _individualsCountAfterMerge = 0;
bool _mergeInProgress = false;
List<String> _mergedIndividuals = [];

// Step 2: After session completes
void _onSessionCompleted(Map<String, dynamic> sessionData) async {
  final originalCount = sessionData['individuals_found'] as int;
  _individualsCountBeforeMerge = originalCount;
  
  setState(() {
    _individualsCount = originalCount;
    _uniqueMvrCount = originalCount; // Initially same
  });
  
  // Step 3: Fetch individuals
  final individualsResponse = await _apiService.get(
    '/api/v1/cross-video/sessions/$_trackingSessionUuid/individuals'
  );
  
  final individuals = individualsResponse.data['individuals'] as List;
  
  // Step 4: Auto-merge duplicates
  await _autoMergeDuplicates(individuals);
}

Future<void> _autoMergeDuplicates(List<dynamic> individuals) async {
  setState(() {
    _mergeInProgress = true;
  });
  
  Set<String> processedIndividuals = {};
  int mergeCount = 0;
  
  try {
    for (var individual in individuals) {
      final individualUuid = individual['individual_uuid'] as String;
      
      // Skip if already processed
      if (processedIndividuals.contains(individualUuid)) continue;
      
      // Find matches
      final matchResponse = await _apiService.post(
        '/api/v1/mvr-people/individuals/$individualUuid/match',
        data: {
          'threshold': 0.85,
          'auto_merge': false,
          'max_results': 10,
        },
      );
      
      final matches = matchResponse.data['matches'] as List;
      
      // Merge each match above threshold
      for (var match in matches) {
        final matchUuid = match['individual_uuid'] as String;
        final similarity = match['similarity_score'] as double;
        
        // Skip if already processed
        if (processedIndividuals.contains(matchUuid)) continue;
        
        // Only merge if above threshold
        if (similarity >= 0.85) {
          try {
            final mergeResponse = await _apiService.post(
              '/api/v1/mvr-people/merge',
              data: {
                'individual_a_uuid': individualUuid,
                'individual_b_uuid': matchUuid,
                'similarity_score': similarity,
                'triggered_by': 'auto_match_session',
              },
            );
            
            if (mergeResponse.data['success'] == true) {
              // Track orphaned individual
              final orphanedUuid = mergeResponse.data['orphaned_mvr_uuid'] as String;
              processedIndividuals.add(orphanedUuid);
              _mergedIndividuals.add(orphanedUuid);
              mergeCount++;
              
              print('✅ Merged: $matchUuid → $individualUuid (similarity: ${similarity.toStringAsFixed(3)})');
            }
          } catch (e) {
            print('⚠️ Failed to merge $individualUuid with $matchUuid: $e');
            // Continue with next match
          }
        }
      }
      
      processedIndividuals.add(individualUuid);
    }
    
    // Step 5: Calculate unique count
    final uniqueCount = _individualsCountBeforeMerge - mergeCount;
    
    setState(() {
      _individualsCount = _individualsCountBeforeMerge;
      _uniqueMvrCount = uniqueCount;
      _uniqueCountIsFallback = false; // Real data
      _mergeInProgress = false;
    });
    
    print('📊 Auto-merge complete: $_individualsCountBeforeMerge → $uniqueCount unique ($mergeCount merged)');
    
  } catch (e) {
    print('❌ Auto-merge failed: $e');
    
    setState(() {
      _mergeInProgress = false;
      _uniqueCountIsFallback = true; // Fallback to original count
    });
  }
}
```

**UI Display:**

```dart
// Show merge progress
if (_mergeInProgress) {
  return Row(
    children: [
      Text('${_individualsCount ?? 0} → '),
      SizedBox(width: 4),
      SizedBox(
        width: 12,
        height: 12,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      SizedBox(width: 4),
      Text('merging...', style: TextStyle(color: AppColors.warning)),
    ],
  );
}

// Show final result
return Row(
  children: [
    Text('${_individualsCount ?? 0}'),
    Text(' → '),
    Text(
      _uniqueCountIsFallback 
        ? '[]' 
        : '${_uniqueMvrCount ?? 0} unique',
      style: TextStyle(
        color: _uniqueCountIsFallback 
          ? AppColors.error 
          : AppColors.success,
        fontWeight: FontWeight.w700,
      ),
    ),
  ],
);
```

---

### Option B: Backend Batch Merge Endpoint (New Endpoint)

**If we want to reduce Flutter complexity, create ONE new endpoint:**

**Endpoint:** `POST /api/v1/mvr-people/batch-match-and-merge`

**Request:**
```json
{
  "individual_uuids": [
    "ind-001", "ind-002", "ind-003", ..., "ind-015"
  ],
  "threshold": 0.85,
  "triggered_by": "auto_match_session"
}
```

**Response:**
```json
{
  "success": true,
  "original_count": 15,
  "unique_count": 12,
  "merge_count": 3,
  "merges": [
    {
      "predominant": "ind-001",
      "orphaned": "ind-007",
      "similarity": 0.92
    },
    {
      "predominant": "ind-002",
      "orphaned": "ind-012",
      "similarity": 0.89
    },
    {
      "predominant": "ind-003",
      "orphaned": "ind-014",
      "similarity": 0.87
    }
  ]
}
```

**Backend Implementation:**
```python
@router.post("/batch-match-and-merge")
async def batch_match_and_merge(
    request: BatchMatchAndMergeRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
):
    """
    Batch match and merge all individuals from a tracking session.
    
    This is a convenience endpoint that:
    1. Finds matches for all individuals
    2. Merges duplicates above threshold
    3. Returns original vs unique count
    """
    individual_uuids = request.individual_uuids
    threshold = request.threshold or 0.85
    
    original_count = len(individual_uuids)
    processed = set()
    merge_count = 0
    merges = []
    
    for individual_uuid in individual_uuids:
        if individual_uuid in processed:
            continue
        
        # Find matches
        matches = await mvr_matcher.find_matching_mvr(
            individual_uuid=individual_uuid,
            threshold=threshold,
        )
        
        # Merge each match
        for match in matches:
            match_uuid = match['individual_uuid']
            similarity = match['similarity_score']
            
            if match_uuid in processed or similarity < threshold:
                continue
            
            # Execute merge
            merge_result = await mvr_matcher.merge_individuals(
                individual_a_uuid=individual_uuid,
                individual_b_uuid=match_uuid,
                similarity_score=similarity,
                triggered_by=request.triggered_by,
            )
            
            if merge_result and merge_result['success']:
                orphaned_uuid = merge_result['orphaned_mvr_uuid']
                processed.add(orphaned_uuid)
                merge_count += 1
                
                merges.append({
                    "predominant": individual_uuid,
                    "orphaned": orphaned_uuid,
                    "similarity": similarity,
                })
        
        processed.add(individual_uuid)
    
    unique_count = original_count - merge_count
    
    return {
        "success": True,
        "original_count": original_count,
        "unique_count": unique_count,
        "merge_count": merge_count,
        "merges": merges,
    }
```

**Flutter Implementation (Simplified):**
```dart
void _onSessionCompleted(Map<String, dynamic> sessionData) async {
  final originalCount = sessionData['individuals_found'] as int;
  
  // Get individuals
  final individualsResponse = await _apiService.get(
    '/api/v1/cross-video/sessions/$_trackingSessionUuid/individuals'
  );
  
  final individuals = individualsResponse.data['individuals'] as List;
  final individualUuids = individuals
      .map((i) => i['individual_uuid'] as String)
      .toList();
  
  // Batch merge
  final mergeResponse = await _apiService.post(
    '/api/v1/mvr-people/batch-match-and-merge',
    data: {
      'individual_uuids': individualUuids,
      'threshold': 0.85,
      'triggered_by': 'auto_match_session',
    },
  );
  
  final uniqueCount = mergeResponse.data['unique_count'] as int;
  
  setState(() {
    _individualsCount = originalCount;
    _uniqueMvrCount = uniqueCount;
    _uniqueCountIsFallback = false;
  });
}
```

---

## Comparison: New Approach vs Original Plan

| Aspect | Original Plan | Proposed Approach (Option A) | Proposed Approach (Option B) |
|--------|--------------|------------------------------|------------------------------|
| **Backend Changes** | Modify `cross_video_tracking_simple.py` | None (use existing endpoints) | Add 1 new batch endpoint |
| **Database Changes** | Add `unique_mvr_people_count` column | None (count in Flutter) | None (count in Flutter) |
| **Merge Logic** | New auto-matching code | Use existing `MVRMatcher` | Use existing `MVRMatcher` |
| **Flutter Complexity** | Simple (read 2 fields) | Medium (loop + merge calls) | Low (1 batch call) |
| **Performance** | O(n²) in backend | O(n²) with network overhead | O(n²) in backend |
| **Error Handling** | Backend falls back | Flutter falls back | Backend falls back |
| **Separation of Concerns** | Coupled | Clean separation | Clean separation |
| **Development Time** | 10-13 hours | 3-4 hours (Flutter only) | 6-8 hours (1 endpoint + Flutter) |

---

## Recommendations

### Option A (Recommended for MVP)

**Pros:**
- ✅ Zero backend changes
- ✅ Uses proven existing endpoints
- ✅ Clean separation (tracking vs merging)
- ✅ Flutter controls when to merge
- ✅ Can be user-initiated or automatic

**Cons:**
- ⚠️ More network calls (O(n) match + O(m) merge calls)
- ⚠️ Flutter logic more complex
- ⚠️ Network failures could interrupt merging

**Best for:** Quick MVP, testing the feature with real users

---

### Option B (Recommended for Production)

**Pros:**
- ✅ Single network call
- ✅ Simple Flutter code
- ✅ Better performance (all in backend)
- ✅ Atomic operation (all-or-nothing merge)

**Cons:**
- ⚠️ Requires 1 new backend endpoint
- ⚠️ Still need to test new endpoint

**Best for:** Production-ready feature after MVP validation

---

### Original Plan (Not Recommended Now)

**Cons:**
- ❌ Modifies working cross-video tracking code
- ❌ Couples tracking with merging (violates single responsibility)
- ❌ Adds database column that may not be needed
- ❌ More complex to test and debug
- ❌ Longer development time

**When to use:** Only if we want tracking sessions to ALWAYS auto-merge (no user control)

---

## Implementation Timeline

### Option A: 3-4 hours
1. ✅ Database migration - Already done
2. ✅ Flutter UI - Already done
3. ⏳ Flutter auto-merge logic - 2-3 hours
4. ⏳ Testing - 1 hour

### Option B: 6-8 hours
1. ✅ Database migration - Already done
2. ✅ Flutter UI - Already done
3. ⏳ New batch endpoint - 3-4 hours
4. ⏳ Flutter integration - 1 hour
5. ⏳ Testing - 2 hours

---

## Decision Matrix

| Criteria | Option A | Option B | Original |
|----------|----------|----------|----------|
| **Time to Market** | ⭐⭐⭐ Fast | ⭐⭐ Medium | ⭐ Slow |
| **Code Quality** | ⭐⭐⭐ Clean | ⭐⭐⭐ Clean | ⭐⭐ Coupled |
| **Performance** | ⭐⭐ Network overhead | ⭐⭐⭐ Fast | ⭐⭐⭐ Fast |
| **Maintainability** | ⭐⭐⭐ Separate | ⭐⭐⭐ Separate | ⭐⭐ Coupled |
| **Flexibility** | ⭐⭐⭐ High | ⭐⭐ Medium | ⭐ Low |
| **Risk** | ⭐⭐⭐ Low | ⭐⭐ Low | ⭐ High |

---

## Next Steps

**Recommended Path:**

1. **Phase 1 (This Week):** Implement Option A
   - Use existing endpoints
   - Add auto-merge logic in Flutter
   - Test with real data
   - Get user feedback

2. **Phase 2 (Next Week):** If successful, implement Option B
   - Create batch merge endpoint
   - Simplify Flutter code
   - Deploy to production

3. **Phase 3 (Future):** Monitor and optimize
   - Track merge accuracy
   - Adjust threshold if needed
   - Add user controls (manual merge, undo merge)

---

## Conclusion

**We recommend Option A for immediate implementation** because:
- ✅ Fastest to market (3-4 hours vs 10-13 hours)
- ✅ Zero risk to existing working code
- ✅ Uses proven, battle-tested merge endpoints
- ✅ Clean separation of concerns
- ✅ Easy to rollback (just disable auto-merge in Flutter)

**Then upgrade to Option B** once we validate the feature works correctly with real users.

---

**Questions for Decision:**
1. Do you want tracking sessions to ALWAYS auto-merge, or should users control when merging happens?
2. Are you comfortable with Flutter making multiple API calls, or do you prefer a single batch endpoint?
3. Should merging be synchronous (wait for completion) or asynchronous (background task)?

---

**Author:** PPL Meta Platform Team  
**Date:** November 1, 2025  
**Status:** Awaiting decision on Option A vs Option B
