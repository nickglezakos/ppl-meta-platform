# Flutter Integration Guide: Batch Match & Merge Endpoint

**Date:** November 1, 2025  
**Status:** Ready for Integration  
**Endpoint:** `POST /api/v1/mvr-people/batch-match-and-merge`

---

## Overview

The batch merge endpoint is **NOT yet integrated in Flutter**. This guide shows you exactly where and how to add it.

---

## Integration Location

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`

**Function:** `_pollTrackingSessionStatus()` around **line 1005**

**When to call:** When tracking session status becomes `'completed'`

---

## Step-by-Step Integration

### Step 1: Add API Client Method

**File:** `ppl-meta-frontend/lib/services/media_api_client.dart` (or wherever API methods are)

```dart
/// Batch match and merge individuals to get unique count
Future<ApiResponse<Map<String, dynamic>>> batchMatchAndMerge({
  required List<String> individualUuids,
  double threshold = 0.85,
  String triggeredBy = 'cross_video_tracking_session',
  String? sessionUuid,
}) async {
  try {
    final response = await post(
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
    logger.e('Batch merge error: $e');
    return ApiResponse.error('Failed to merge individuals: $e');
  }
}
```

---

### Step 2: Modify `_pollTrackingSessionStatus()` 

**Location:** Around line 1005 in `collections_screen.dart`

**Replace this:**
```dart
if (status == 'completed') {
  print('DEBUG: Session completed!');
  setState(() {
    _isLoadingIndividuals = false;
    _trackingSessionData = statusResponse.data;
  });
  return;
}
```

**With this:**
```dart
if (status == 'completed') {
  print('DEBUG: Session completed!');
  
  // NEW: Auto-merge duplicates after session completes
  await _autoMergeDuplicates(apiClient, sessionUuid, individualsFound);
  
  setState(() {
    _isLoadingIndividuals = false;
    _trackingSessionData = statusResponse.data;
  });
  return;
}
```

---

### Step 3: Add Auto-Merge Function

**Location:** Add this new function in `collections_screen.dart` (around line 960)

```dart
/// Auto-merge duplicate individuals after tracking session completes
Future<void> _autoMergeDuplicates(
  MediaApiClient apiClient,
  String sessionUuid,
  int originalCount,
) async {
  print('🔄 Starting auto-merge for session $sessionUuid...');
  
  try {
    // Step 1: Get list of individuals from session
    final individualsResponse = await apiClient.get(
      '/api/v1/cross-video/sessions/$sessionUuid/individuals',
    );
    
    if (!individualsResponse.success || individualsResponse.data == null) {
      print('⚠️ Failed to get individuals list for merging');
      setState(() {
        _uniqueCountIsFallback = true; // Fall back to original count
      });
      return;
    }
    
    final individuals = individualsResponse.data!['individuals'] as List;
    
    if (individuals.isEmpty) {
      print('⚠️ No individuals to merge');
      setState(() {
        _uniqueMvrCount = 0;
        _uniqueCountIsFallback = false;
      });
      return;
    }
    
    // Extract UUIDs
    final individualUuids = individuals
        .map((i) => i['individual_uuid'] as String)
        .toList();
    
    print('  Found ${individualUuids.length} individuals to process');
    
    // Step 2: Call batch merge endpoint
    final mergeResponse = await apiClient.batchMatchAndMerge(
      individualUuids: individualUuids,
      threshold: 0.85,
      triggeredBy: 'cross_video_tracking_session',
      sessionUuid: sessionUuid,
    );
    
    if (!mergeResponse.success || mergeResponse.data == null) {
      print('⚠️ Batch merge failed, using fallback');
      setState(() {
        _uniqueCountIsFallback = true; // Fall back to original count
      });
      return;
    }
    
    // Step 3: Update UI with unique count
    final uniqueCount = mergeResponse.data!['unique_count'] as int;
    final mergeCount = mergeResponse.data!['merge_count'] as int;
    final processingTime = mergeResponse.data!['processing_time_seconds'] as double;
    
    setState(() {
      _individualsCount = originalCount;
      _uniqueMvrCount = uniqueCount;
      _uniqueCountIsFallback = false; // Real data from API
    });
    
    print('✅ Auto-merge complete:');
    print('   Original: $originalCount individuals');
    print('   Unique: $uniqueCount individuals');
    print('   Merged: $mergeCount duplicates');
    print('   Time: ${processingTime.toStringAsFixed(2)}s');
    
  } catch (e) {
    print('❌ Auto-merge error: $e');
    setState(() {
      _uniqueCountIsFallback = true; // Fall back to original count
    });
  }
}
```

---

## Expected Flow

### Before Integration:
```
1. User creates tracking session
2. Session completes
3. UI shows: "15 individuals found"
4. Counter shows: "15 → []" (fallback)
```

### After Integration:
```
1. User creates tracking session
2. Session completes → individualsFound = 15
3. Auto-merge runs:
   a. Get individuals list
   b. Call batch merge API
   c. API finds 3 duplicates
   d. API merges them
   e. API returns unique_count = 12
4. UI updates: "15 → 12 unique" (GREEN)
```

---

## UI States

### State 1: Before Session Starts
```dart
Individuals: -
```

### State 2: Session Running
```dart
Individuals: (spinner)
```

### State 3: Session Complete, Before Merge
```dart
Individuals: 15 → [] (RED - fallback)
```

### State 4: Merging in Progress
```dart
Individuals: 15 → (spinner) merging...
```

### State 5: Merge Complete
```dart
Individuals: 15 → 12 unique (GREEN - real data)
```

---

## Testing the Integration

### Test Case 1: No Duplicates
**Setup:** All individuals are different people  
**Expected:**
- Original count: 5
- Unique count: 5
- Merge count: 0
- UI: "5 → 5 unique" (GREEN)

### Test Case 2: Some Duplicates
**Setup:** 10 individuals, 3 are duplicates  
**Expected:**
- Original count: 10
- Unique count: 7
- Merge count: 3
- UI: "10 → 7 unique" (GREEN)

### Test Case 3: Merge Fails
**Setup:** Network error or API failure  
**Expected:**
- Original count: 10
- Unique count: 10 (fallback)
- UI: "10 → []" (RED - fallback)

---

## Error Handling

The auto-merge function includes comprehensive error handling:

1. **Individuals fetch fails** → Falls back to original count (shows `[]`)
2. **Batch merge API fails** → Falls back to original count (shows `[]`)
3. **Network timeout** → Falls back to original count (shows `[]`)
4. **Invalid response** → Falls back to original count (shows `[]`)

**Result:** The UI will ALWAYS show something, never crash.

---

## Performance Considerations

- **Small sessions (1-10 individuals):** ~1-2 seconds
- **Medium sessions (10-50 individuals):** ~2-5 seconds
- **Large sessions (50-100 individuals):** ~5-15 seconds

**Recommendation:** Show a spinner during merge: "15 → (spinner) merging..."

---

## Alternative: Manual Trigger (Optional)

Instead of auto-merge, you can add a button for users to manually trigger:

```dart
IconButton(
  icon: Icon(Icons.merge_type),
  tooltip: 'Merge duplicates',
  onPressed: _isLoadingIndividuals ? null : () async {
    await _autoMergeDuplicates(
      _apiClient,
      _trackingSessionUuid!,
      _individualsCount ?? 0,
    );
  },
)
```

---

## Summary

### Files to Modify:
1. ✅ `lib/services/media_api_client.dart` - Add `batchMatchAndMerge()` method
2. ✅ `lib/screens/collections_screen.dart` - Add `_autoMergeDuplicates()` function
3. ✅ `lib/screens/collections_screen.dart` - Call it in `_pollTrackingSessionStatus()`

### Total Lines to Add: ~80-100 lines

### Integration Time: 15-30 minutes

### Testing Time: 10-15 minutes

---

## Need Help?

If you run into issues:
1. Check the test script works: `python3 test_batch_merge.py`
2. Verify services are healthy: Run health check task
3. Check Flutter console logs for error messages
4. Test API directly with curl first

---

**Ready to integrate?** Start with Step 1 (add API method) and test each step!
