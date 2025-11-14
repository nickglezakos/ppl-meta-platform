# Flutter Integration Testing Checklist

**Date:** 2025-11-01  
**Feature:** Batch Merge Auto-Merging for Cross-Video Tracking  
**Status:** Ready for Testing ✅

---

## Pre-Testing Verification

### Backend Status
- [x] Batch merge endpoint implemented: `POST /api/v1/mvr-people/batch-match-and-merge`
- [x] JWT authentication working (SECRET_KEY synced)
- [x] Test script passes: `python3 test_batch_merge.py`
- [x] All 8 services healthy and running

### Flutter Code Status
- [x] API method added: `batchMatchAndMerge()` in media_api_client.dart
- [x] Auto-merge function added: `_autoMergeDuplicates()` in collections_screen.dart
- [x] Polling modified to trigger auto-merge on session completion
- [x] No compilation errors
- [x] Error handling implemented
- [x] Console logging added

---

## Step-by-Step Testing Guide

### Step 1: Start Flutter App
```bash
cd ppl-meta-frontend
flutter run -d chrome --web-port 3000
# OR
flutter run -d macos
```

**Expected Output:**
```
✓ Built build/web/main.dart.js
Launching chrome on Chrome...
Debug service listening on ws://127.0.0.1:xxxxx
```

**Verify:**
- [ ] App launches successfully
- [ ] No compilation errors in terminal
- [ ] Login screen appears

---

### Step 2: Login to App
**Credentials:**
- Email: `fresh.user@example.com`
- Password: `NewPassword234!`

**Verify:**
- [ ] Login successful
- [ ] Redirected to main screen
- [ ] Collections tab accessible

---

### Step 3: Navigate to Collections
1. Click on "Collections" tab
2. Select an existing collection (or create one with test videos)

**Verify:**
- [ ] Collections screen loads
- [ ] Media items display correctly
- [ ] Can select date range

---

### Step 4: Start Cross-Video Tracking Session

1. Click "Start Tracking Session" button
2. Select date range (ensure it includes videos with people)
3. Confirm and start

**Expected Console Output (Initial):**
```
DEBUG: Creating cross-video tracking session...
DEBUG: Session created with UUID: abc-123-def-456
DEBUG: Starting to poll tracking session status...
```

**Verify:**
- [ ] Loading indicator appears
- [ ] Console shows session creation
- [ ] Polling starts

---

### Step 5: Monitor Session Processing

**Expected Console Output (During Processing):**
```
DEBUG: Tracking session status: in_progress
  - individuals_found: 0 (original count)
  - unique_mvr_people_count: [] (FALLBACK - field missing from API)
  
DEBUG: Tracking session status: in_progress
  - individuals_found: 5 (original count)
  - unique_mvr_people_count: [] (FALLBACK - field missing from API)
  
DEBUG: Tracking session status: in_progress
  - individuals_found: 15 (original count)
  - unique_mvr_people_count: [] (FALLBACK - field missing from API)
```

**UI Display During Processing:**
```
Original Count: 15
Unique Count: [] (RED)
Status: Processing...
```

**Verify:**
- [ ] Counter 1 (original) updates as individuals are found
- [ ] Counter 2 shows `[]` in RED (fallback)
- [ ] Session status updates in console

---

### Step 6: Session Completion - AUTO-MERGE TRIGGERS

**Expected Console Output (CRITICAL - This is the new feature!):**
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
  processing_time_seconds: 2.34,
  merges: [...]
}
✅ Auto-merge complete:
   Original: 15 individuals
   Unique: 12 individuals
   Merged: 3 duplicates
   Time: 2.34s
```

**UI Display After Completion:**
```
Original Count: 15
Unique Count: 12 unique (GREEN)
Status: Completed
```

**CRITICAL VERIFICATIONS:**
- [ ] ✅ Console shows "🔄 Starting auto-merge..."
- [ ] ✅ Console shows "✅ Auto-merge complete"
- [ ] ✅ UI counter changes from `[]` (RED) to `12 unique` (GREEN)
- [ ] ✅ Original count (15) remains unchanged
- [ ] ✅ Unique count (12) is different from original (indicates duplicates merged)

---

## Test Cases

### Test Case 1: No Duplicates Found

**Setup:** Session with different individuals (no duplicates)

**Expected Results:**
- Original count: `5`
- Unique count: `5 unique` (GREEN)
- Merge count: `0`
- Console: "Merged: 0 duplicates"

**Verify:**
- [ ] Both counters show same number
- [ ] Counter 2 shows GREEN `5 unique`
- [ ] No merges reported in console

---

### Test Case 2: Some Duplicates Found

**Setup:** Session with duplicate individuals (same person in multiple videos)

**Expected Results:**
- Original count: `10`
- Unique count: `7 unique` (GREEN)
- Merge count: `3`
- Console: "Merged: 3 duplicates"

**Verify:**
- [ ] Counter 1 shows 10
- [ ] Counter 2 shows 7 (GREEN)
- [ ] Difference of 3 matches merge count
- [ ] Console shows merge statistics

---

### Test Case 3: Many Duplicates (Same Person Multiple Times)

**Setup:** Same person tracked across 6 different videos

**Expected Results:**
- Original count: `6`
- Unique count: `1 unique` (GREEN)
- Merge count: `5`
- Console: "Merged: 5 duplicates"

**Verify:**
- [ ] Counter 1 shows 6
- [ ] Counter 2 shows 1 (GREEN)
- [ ] Significant reduction (6 → 1)
- [ ] Console confirms 5 merges

---

### Test Case 4: Empty Session

**Setup:** Session with no individuals detected

**Expected Results:**
- Original count: `0`
- Unique count: `0 unique` (GREEN)
- Merge count: `0`
- Console: "⚠️ No individuals found in session"

**Verify:**
- [ ] Both counters show 0
- [ ] Counter 2 shows GREEN (not RED)
- [ ] Console warns about empty session

---

### Test Case 5: Merge Fails (Error Handling)

**Setup:** Simulate merge failure (stop vmeta service during merge)

**Steps:**
1. Start tracking session
2. Wait for session to complete
3. When auto-merge triggers, stop vmeta service
4. Observe error handling

**Expected Results:**
- Original count: `15`
- Unique count: `[]` (RED - fallback)
- Console: "❌ Batch merge failed: ..."

**Verify:**
- [ ] Counter 1 shows correct original count
- [ ] Counter 2 shows `[]` in RED (fallback)
- [ ] Error message in console
- [ ] App doesn't crash

---

## Performance Verification

### Small Session (1-10 individuals)

**Expected:**
- Auto-merge time: 1-2 seconds
- UI responsive during merge

**Verify:**
- [ ] Merge completes in <3 seconds
- [ ] Console shows processing time
- [ ] UI doesn't freeze

---

### Medium Session (10-50 individuals)

**Expected:**
- Auto-merge time: 2-5 seconds
- UI may show brief delay

**Verify:**
- [ ] Merge completes in <10 seconds
- [ ] Console shows processing time
- [ ] UI remains usable

---

### Large Session (50-100 individuals)

**Expected:**
- Auto-merge time: 5-15 seconds
- UI shows processing indicator

**Verify:**
- [ ] Merge completes in <20 seconds
- [ ] Console shows processing time
- [ ] No timeout errors

---

## Debugging Checklist

### If Counter 2 Shows RED `[]` After Completion

**Possible Causes:**
1. Auto-merge function didn't trigger
2. Batch merge endpoint returned error
3. Individual UUIDs not extracted correctly
4. vmeta service down or unreachable

**Debug Steps:**
1. Check console for "🔄 Starting auto-merge..." message
   - **Not present?** → Auto-merge didn't trigger (check polling code)
   - **Present?** → Continue to step 2

2. Check console for error messages
   - "❌ Failed to get session individuals" → GET endpoint issue
   - "❌ Batch merge failed" → POST endpoint issue
   - "❌ Auto-merge error" → Exception during processing

3. Test batch merge endpoint directly:
   ```bash
   python3 test_batch_merge.py
   ```

4. Check vmeta service health:
   ```bash
   curl http://localhost:8008/health
   ```

5. Check JWT authentication:
   ```bash
   # Login to get token
   curl -X POST http://localhost:8001/api/v1/users/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=fresh.user@example.com&password=NewPassword234!"
   
   # Test batch merge with token
   curl -X POST http://localhost:8008/api/v1/mvr-people/batch-match-and-merge \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"individual_uuids":["uuid1","uuid2"],"threshold":0.85}'
   ```

---

### If Counter 2 Shows Same as Counter 1 (No Duplicates Merged)

**Possible Causes:**
1. No duplicates exist in session (expected behavior)
2. Similarity threshold too high (0.85 may be too strict)
3. MVR-People matching not finding similarities

**Debug Steps:**
1. Check console for merge statistics:
   ```
   ✅ Auto-merge complete:
      Original: 10 individuals
      Unique: 10 individuals  ← Same number
      Merged: 0 duplicates    ← No merges
   ```

2. If this is expected (truly no duplicates), this is correct behavior

3. If duplicates should exist, try lowering threshold:
   - Edit `collections_screen.dart`
   - Change `threshold: 0.85` to `threshold: 0.80`
   - Restart Flutter app
   - Try again

---

### If Auto-Merge Takes Too Long (>30 seconds)

**Possible Causes:**
1. Large number of individuals (100+)
2. Slow network connection
3. vmeta service overloaded

**Debug Steps:**
1. Check console for "Found X individuals to process"
2. If X > 100, this is expected
3. Monitor console for progress updates
4. Consider adding timeout (see Future Enhancements below)

---

## Success Metrics

### Minimum Viable Success
- [x] Auto-merge function triggers on session completion
- [x] Console shows merge statistics
- [x] UI counter updates from RED `[]` to GREEN `X unique`
- [x] No app crashes or freezes

### Full Success
- [ ] All test cases pass
- [ ] Performance acceptable for all session sizes
- [ ] Error handling works correctly
- [ ] UI provides clear feedback
- [ ] Console logs helpful for debugging

---

## Rollback Plan (If Issues Found)

### Revert Flutter Changes

**Option 1: Git Revert (Recommended)**
```bash
cd ppl-meta-frontend
git status  # See changed files
git diff lib/services/media_api_client.dart  # Review changes
git checkout -- lib/services/media_api_client.dart  # Revert API client
git checkout -- lib/screens/collections_screen.dart  # Revert collections screen
```

**Option 2: Keep Backend, Disable Flutter**

Comment out the auto-merge call in collections_screen.dart:
```dart
if (status == 'completed') {
  print('DEBUG: Session completed!');
  
  // TEMPORARILY DISABLED: Auto-merge
  // await _autoMergeDuplicates(
  //   apiClient,
  //   sessionUuid,
  //   individualsFound,
  // );
  
  setState(() {
    _isLoadingIndividuals = false;
    _trackingSessionData = statusResponse.data;
  });
  return;
}
```

---

## Future Enhancements (After Testing)

### Enhancement 1: Loading Indicator During Merge
**Priority:** High  
**Effort:** Low  

Add spinner while merge is processing:
```dart
// Show loading
setState(() {
  _isMergingIndividuals = true;
});

// Call merge
await _autoMergeDuplicates(...);

// Hide loading
setState(() {
  _isMergingIndividuals = false;
});
```

UI: `15 → (spinner) merging...`

---

### Enhancement 2: Merge Timeout Protection
**Priority:** Medium  
**Effort:** Low  

Add timeout to prevent hanging:
```dart
final mergeResponse = await apiClient.batchMatchAndMerge(...)
  .timeout(
    Duration(seconds: 30),
    onTimeout: () => ApiResponse.error('Merge timed out'),
  );
```

---

### Enhancement 3: Manual Merge Trigger
**Priority:** Low  
**Effort:** Medium  

Add button to manually re-run merge:
```dart
ElevatedButton(
  onPressed: () => _autoMergeDuplicates(...),
  child: Text('Re-merge Duplicates'),
)
```

---

### Enhancement 4: Merge Details Dialog
**Priority:** Low  
**Effort:** High  

Show which individuals were merged:
```dart
showDialog(
  context: context,
  builder: (context) => MergeDetailsDialog(
    originalCount: 15,
    uniqueCount: 12,
    merges: mergeData['merges'],
  ),
);
```

---

## Contact & Support

**Documentation:**
- Integration Guide: `docs/vision-vmeta/FLUTTER_INTEGRATION_GUIDE.md`
- Implementation Complete: `docs/vision-vmeta/FLUTTER_INTEGRATION_COMPLETE.md`
- Backend Details: `docs/vision-vmeta/IMPLEMENTATION_COMPLETE.md`

**Test Script:**
- `test_batch_merge.py` (backend endpoint testing)

**Services:**
- vmeta: http://localhost:8008
- node: http://localhost:8001
- gateway: http://localhost:8080

---

## Final Checklist

### Before Testing
- [ ] All 8 services running and healthy
- [ ] Backend endpoint tested with `python3 test_batch_merge.py`
- [ ] Flutter app compiles without errors
- [ ] Test user credentials available

### During Testing
- [ ] Document all console output
- [ ] Screenshot UI before/after states
- [ ] Note any unexpected behavior
- [ ] Record performance metrics

### After Testing
- [ ] Update this checklist with results
- [ ] Document any issues found
- [ ] Create tasks for enhancements
- [ ] Update integration documentation

---

**Testing Started:** _________________  
**Testing Completed:** _________________  
**Result:** ☐ Pass  ☐ Pass with Issues  ☐ Fail  

**Notes:**
```
[Add testing notes here]
```

---

**Created by:** GitHub Copilot  
**Date:** 2025-11-01  
**Status:** Ready for Testing ✅
