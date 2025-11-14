# Flutter Integration Complete - Batch Merge Endpoint

**Date:** 2025-11-01  
**Status:** ✅ COMPLETE  
**Integration Time:** ~10 minutes  

---

## Overview

Successfully integrated the new `POST /api/v1/mvr-people/batch-match-and-merge` endpoint into the Flutter frontend. This enables automatic duplicate merging for cross-video tracking sessions, providing users with both original and unique individual counts.

---

## Changes Made

### 1. MediaApiClient - New API Method

**File:** `ppl-meta-frontend/lib/services/media_api_client.dart`

**Added Method:** `batchMatchAndMerge()`

```dart
/// Batch match and merge individuals using MVR-People matching
Future<ApiResponse<Map<String, dynamic>>> batchMatchAndMerge({
  required List<String> individualUuids,
  double threshold = 0.85,
  String triggeredBy = 'cross_video_tracking_session',
  String? sessionUuid,
}) async {
  final response = await _apiClient.post(
    '/api/v1/mvr-people/batch-match-and-merge',
    data: {
      'individual_uuids': individualUuids,
      'threshold': threshold,
      'triggered_by': triggeredBy,
      if (sessionUuid != null) 'session_uuid': sessionUuid,
    },
  );
  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

**Lines Added:** ~30 lines  
**Location:** End of MediaApiClient class (before closing brace)

---

### 2. CollectionsScreen - Auto-Merge Function

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`

**Added Function:** `_autoMergeDuplicates()`

```dart
/// Automatically merge duplicate individuals using MVR-People batch matching
Future<void> _autoMergeDuplicates(
  MediaApiClient apiClient,
  String sessionUuid,
  int originalCount,
) async {
  // Step 1: Get all individuals from session
  final individualsResponse = await apiClient.getCrossVideoSessionIndividuals(
    sessionUuid: sessionUuid,
  );
  
  // Step 2: Extract individual UUIDs
  final individualUuids = individuals
      .map((i) => i['individual_uuid'] as String?)
      .where((uuid) => uuid != null)
      .cast<String>()
      .toList();
  
  // Step 3: Call batch merge endpoint
  final mergeResponse = await apiClient.batchMatchAndMerge(
    individualUuids: individualUuids,
    threshold: 0.85,
    sessionUuid: sessionUuid,
  );
  
  // Step 4: Update UI with results
  setState(() {
    _uniqueMvrCount = mergeResponse.data!['unique_count'];
    _uniqueCountIsFallback = false; // Real data
  });
}
```

**Lines Added:** ~95 lines  
**Location:** After `_pollTrackingSessionStatus()`, before `_enterSelectionMode()`

---

### 3. CollectionsScreen - Polling Modification

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`

**Modified Function:** `_pollTrackingSessionStatus()`

**Change:** Added auto-merge call when session completes

```dart
if (status == 'completed') {
  print('DEBUG: Session completed!');
  
  // NEW: Trigger automatic duplicate merging via MVR-People
  await _autoMergeDuplicates(
    apiClient,
    sessionUuid,
    individualsFound,
  );
  
  setState(() {
    _isLoadingIndividuals = false;
    _trackingSessionData = statusResponse.data;
  });
  return;
}
```

**Lines Modified:** 1 location, ~6 lines added  
**Location:** Line ~1005 in `_pollTrackingSessionStatus()`

---

## How It Works

### User Flow

1. **User starts cross-video tracking session** in Flutter
   - Selects collection and time range
   - Clicks "Start Tracking Session"

2. **Backend processes videos**
   - Detects individuals across multiple videos
   - Returns `individuals_found: 15` (original count)

3. **Session completes → Auto-merge triggers**
   ```
   Session status: 'completed'
   ↓
   _autoMergeDuplicates() runs
   ↓
   GET /sessions/{uuid}/individuals → [uuid1, uuid2, uuid3, ...]
   ↓
   POST /batch-match-and-merge → {original: 15, unique: 12, merged: 3}
   ↓
   UI updates counters
   ```

4. **UI displays dual counters**
   - Before: `15 → []` (RED - fallback, no unique count)
   - After: `15 → 12 unique` (GREEN - real merge data)

### API Call Sequence

```
1. GET /api/v1/cross-video/sessions/{uuid}/individuals
   Response: {
     "individuals": [
       {"individual_uuid": "abc-123", ...},
       {"individual_uuid": "def-456", ...},
       ...
     ]
   }

2. POST /api/v1/mvr-people/batch-match-and-merge
   Request: {
     "individual_uuids": ["abc-123", "def-456", ...],
     "threshold": 0.85,
     "triggered_by": "cross_video_tracking_session",
     "session_uuid": "session-uuid"
   }
   
   Response: {
     "success": true,
     "original_count": 15,
     "unique_count": 12,
     "merge_count": 3,
     "merges": [...],
     "processing_time_seconds": 2.34
   }

3. UI State Update:
   _individualsCount = 15         // Original
   _uniqueMvrCount = 12           // After merge
   _uniqueCountIsFallback = false // Real data
```

---

## UI States

### State 1: Before Session Completes
```
Counter Display: "15 → []"
Color: RED
Status: _uniqueCountIsFallback = true
Meaning: Backend hasn't returned unique count yet
```

### State 2: During Auto-Merge (Brief)
```
Counter Display: "15 → []"
Backend Activity: Calling batch merge endpoint
Duration: 1-5 seconds typically
```

### State 3: After Auto-Merge Success
```
Counter Display: "15 → 12 unique"
Color: GREEN
Status: _uniqueCountIsFallback = false
Meaning: Successfully merged duplicates
Console Log:
  ✅ Auto-merge complete:
     Original: 15 individuals
     Unique: 12 individuals
     Merged: 3 duplicates
     Time: 2.34s
```

### State 4: Auto-Merge Failed (Fallback)
```
Counter Display: "15 → []"
Color: RED
Status: _uniqueCountIsFallback = true
Meaning: Merge failed, falling back to original count
Console Log:
  ❌ Batch merge failed: [error message]
```

---

## Test Scenarios

### Scenario 1: No Duplicates
**Setup:** Session with 5 completely different individuals  
**Expected Result:**
- Original count: `5`
- Unique count: `5`
- Merge count: `0`
- UI: `5 → 5 unique` (GREEN)

### Scenario 2: Some Duplicates
**Setup:** Session with 10 individuals, 3 are duplicates  
**Expected Result:**
- Original count: `10`
- Unique count: `7`
- Merge count: `3`
- UI: `10 → 7 unique` (GREEN)

### Scenario 3: Many Duplicates
**Setup:** Same person tracked across 6 videos  
**Expected Result:**
- Original count: `6`
- Unique count: `1`
- Merge count: `5`
- UI: `6 → 1 unique` (GREEN)

### Scenario 4: Merge Endpoint Fails
**Setup:** Batch merge returns error (e.g., 500 error)  
**Expected Result:**
- Original count: `15`
- Unique count: `[]` (fallback)
- UI: `15 → []` (RED)
- Console: `❌ Batch merge failed: [error]`

### Scenario 5: Empty Session
**Setup:** No individuals detected in session  
**Expected Result:**
- Original count: `0`
- Unique count: `0`
- UI: `0 → 0 unique` (GREEN)

---

## Performance Characteristics

### Expected Processing Times

| Individual Count | Expected Time | Network Latency | Total Time |
|-----------------|---------------|-----------------|------------|
| 1-10            | 0.5-1.5s      | 0.5s           | 1-2s       |
| 10-50           | 1-3s          | 0.5s           | 2-4s       |
| 50-100          | 3-10s         | 0.5s           | 4-11s      |
| 100-200         | 10-20s        | 0.5s           | 11-21s     |

### Timeout Strategy

**Current:** No explicit timeout (relies on Dio defaults)  
**Recommendation:** Add timeout if processing takes >30 seconds  

**Future Enhancement:**
```dart
final mergeResponse = await apiClient.batchMatchAndMerge(
  individualUuids: individualUuids,
  threshold: 0.85,
  sessionUuid: sessionUuid,
).timeout(
  Duration(seconds: 30),
  onTimeout: () {
    print('⚠️ Batch merge timed out after 30s');
    return ApiResponse.error('Merge operation timed out');
  },
);
```

---

## Console Output Examples

### Success Case
```
DEBUG: Session completed!
🔄 Starting auto-merge for session abc-123-def-456...
  Found 15 individuals to process
  Extracted 15 individual UUIDs
🔄 Batch merge result: {
  success: true,
  original_count: 15,
  unique_count: 12,
  merge_count: 3,
  processing_time_seconds: 2.34
}
✅ Auto-merge complete:
   Original: 15 individuals
   Unique: 12 individuals
   Merged: 3 duplicates
   Time: 2.34s
```

### Error Case
```
DEBUG: Session completed!
🔄 Starting auto-merge for session abc-123-def-456...
  Found 15 individuals to process
  Extracted 15 individual UUIDs
❌ Batch merge failed: {error message}
❌ Auto-merge error: DioException [...]
```

---

## Comparison: Before vs After Integration

### Before Integration

**UI Display:**
- Original count: `15` ✅
- Unique count: `[]` (RED) ❌
- Fallback warning in console

**User Experience:**
- Only saw total individuals detected
- No way to know if duplicates existed
- Counter always showed RED `[]`

**Developer Experience:**
- Had to manually test merge endpoints
- No automatic duplicate detection
- Required separate API calls

---

### After Integration

**UI Display:**
- Original count: `15` ✅
- Unique count: `12 unique` (GREEN) ✅
- Clear distinction between counters

**User Experience:**
- Sees both original and unique counts
- Immediately knows if duplicates were found
- Counter shows GREEN when merge succeeds
- Automatic - no user action required

**Developer Experience:**
- Automatic duplicate merging
- Clear console logs for debugging
- Error handling with fallback
- Performance metrics in logs

---

## Error Handling

### Error Type 1: Failed to Get Individuals
**Scenario:** GET /sessions/{uuid}/individuals returns error  
**Handling:**
```dart
if (!individualsResponse.success) {
  print('❌ Failed to get session individuals');
  return; // Keep fallback values
}
```
**UI Result:** Shows `15 → []` (RED) - fallback remains

---

### Error Type 2: Empty Individual List
**Scenario:** Session has no individuals  
**Handling:**
```dart
if (individuals.isEmpty) {
  print('⚠️ No individuals found in session');
  setState(() {
    _uniqueMvrCount = 0;
    _uniqueCountIsFallback = false;
  });
  return;
}
```
**UI Result:** Shows `0 → 0 unique` (GREEN) - explicit zero

---

### Error Type 3: Batch Merge Endpoint Fails
**Scenario:** POST /batch-match-and-merge returns 500 error  
**Handling:**
```dart
if (!mergeResponse.success) {
  print('❌ Batch merge failed: ${mergeResponse.error}');
  return; // Keep fallback values
}
```
**UI Result:** Shows `15 → []` (RED) - fallback remains

---

### Error Type 4: Exception During Processing
**Scenario:** Network error, JSON parsing error, etc.  
**Handling:**
```dart
try {
  // ... merge logic ...
} catch (e) {
  print('❌ Auto-merge error: $e');
  // Keep fallback values - don't update state
}
```
**UI Result:** Shows `15 → []` (RED) - fallback remains

---

## Configuration

### Merge Threshold
**Current Value:** `0.85` (85% similarity)  
**Location:** `_autoMergeDuplicates()` function  
**Adjustable:** Yes, change the `threshold` parameter

**Options:**
- `0.80`: More aggressive merging (may merge different people)
- `0.85`: Balanced (recommended default)
- `0.90`: Conservative (only merge very similar individuals)
- `0.95`: Very strict (may miss some duplicates)

---

### Triggered By Identifier
**Current Value:** `'cross_video_tracking_session'`  
**Purpose:** Identifies merge operations initiated from cross-video tracking  
**Location:** `_autoMergeDuplicates()` function

**Other Possible Values:**
- `'manual_user_merge'`: User-initiated merge
- `'batch_processing'`: Automated batch job
- `'collection_optimization'`: Collection cleanup

---

## Files Modified Summary

| File | Lines Added | Lines Modified | Purpose |
|------|-------------|----------------|---------|
| `media_api_client.dart` | ~30 | 0 | New API method |
| `collections_screen.dart` | ~95 | ~6 | Auto-merge function + trigger |
| **Total** | **~125** | **~6** | **Complete integration** |

---

## Next Steps

### Immediate Testing
1. ✅ **Compilation Check:** No errors (verified)
2. ⏳ **Run Flutter App:** Test in development mode
3. ⏳ **Create Tracking Session:** Verify auto-merge triggers
4. ⏳ **Check Console Logs:** Verify merge statistics appear
5. ⏳ **Verify UI Update:** Confirm GREEN `X unique` appears

### Test Cases to Run
- [ ] Test with 5 different individuals (no duplicates)
- [ ] Test with 10 individuals (3 duplicates expected)
- [ ] Test with empty session (0 individuals)
- [ ] Test with network error (verify fallback works)
- [ ] Test with large session (50+ individuals)

### Future Enhancements
1. **Add Loading Spinner:** Show "Merging..." during batch merge
2. **Add Timeout:** 30-second timeout for large batches
3. **Add User Controls:** Allow threshold adjustment in settings
4. **Add Manual Trigger:** Button to re-run merge on demand
5. **Add Merge Details:** Show which individuals were merged
6. **Add Performance Metrics:** Display merge time in UI

---

## Success Criteria

### Backend Integration ✅
- [x] Endpoint implemented and tested
- [x] Authentication working
- [x] Returns correct response format
- [x] Test script passes

### Flutter Integration ✅
- [x] API method added to MediaApiClient
- [x] Auto-merge function implemented
- [x] Polling function modified to trigger merge
- [x] Error handling implemented
- [x] Console logging added
- [x] UI state management integrated
- [x] No compilation errors

### User Experience ⏳ (Pending Testing)
- [ ] UI shows GREEN `X unique` (not RED `[]`)
- [ ] Both counters display correctly
- [ ] Counter 1 (original) unchanged from before
- [ ] Counter 2 (unique) reflects merged count
- [ ] Performance acceptable (<15s for 100 individuals)
- [ ] Error handling graceful (falls back to `[]`)

---

## Documentation References

- **Integration Guide:** `docs/vision-vmeta/FLUTTER_INTEGRATION_GUIDE.md`
- **Implementation Plan:** `docs/vision-vmeta/OPTION_B_IMPLEMENTATION_PLAN.md`
- **Proposal Analysis:** `docs/vision-vmeta/PROPOSAL_USE_EXISTING_MERGE_ENDPOINTS.md`
- **Backend Implementation:** `docs/vision-vmeta/IMPLEMENTATION_COMPLETE.md`
- **Test Script:** `test_batch_merge.py`

---

## Timeline

- **Backend Implementation:** 2025-10-31 (10 hours)
- **Flutter Integration:** 2025-11-01 (10 minutes)
- **Total Project Time:** ~10 hours
- **Documentation:** 22,000+ lines across 5 documents

---

## Conclusion

✅ **Flutter integration is now COMPLETE.**

The dual counter system is fully implemented:
- **Counter 1:** Original individuals count (before merging)
- **Counter 2:** Unique individuals count (after auto-merging duplicates)

**Status:**
- Backend: ✅ Complete and tested
- Flutter: ✅ Complete (compilation verified)
- Testing: ⏳ Pending user testing in app

**Next Action:** Run the Flutter app and test with a real cross-video tracking session to verify the end-to-end flow.

---

**Integration completed by:** GitHub Copilot  
**Date:** 2025-11-01  
**Status:** Ready for testing ✅
