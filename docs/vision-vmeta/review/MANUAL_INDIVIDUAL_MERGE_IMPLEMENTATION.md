# Manual Individual Merge Implementation

**Date:** May 28, 2025  
**Feature:** Manual merge functionality for cross-video individuals with face embedding validation  
**Status:** ✅ COMPLETE - Ready for Testing

---

## Overview

Implemented a complete end-to-end feature that allows users to manually select and merge individuals in the Flutter UI with backend validation using facial embeddings. This feature builds upon the automatic merge functionality documented in `FACE_EMBEDDINGS_FOR_INDIVIDUAL_MERGING.md`.

---

## Feature Description

### User Workflow

1. **Navigate to Cross-Video Individuals Tab**
   - User creates a cross-video tracking session
   - Opens the "Individuals" tab in PersonObjectsDetailScreen
   - Views list of detected individuals

2. **Select Individuals for Merging**
   - Each individual card displays a checkbox
   - User selects 2 or more individuals they want to merge
   - A FloatingActionButton appears when ≥2 individuals are selected

3. **Confirm Merge**
   - User clicks "Merge X Individuals" button
   - System shows confirmation dialog with:
     - Number of individuals to merge
     - List of selected individual UUIDs
     - Explanation of embedding validation
   - User confirms or cancels

4. **Backend Processing**
   - System validates face similarity using Facenet512 embeddings
   - Calculates cosine similarity between face crops
   - Validates similarity against threshold (default 0.75)
   - Merges individuals if similar enough
   - Transfers all appearances to predominant individual
   - Deletes merged individuals

5. **UI Refresh**
   - Success message shows merge statistics and similarity score
   - Individual list automatically refreshes
   - Merged individuals are removed from the list
   - Selection is cleared

---

## Implementation Details

### Backend Changes

#### 1. Pydantic Models (`ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`)

**MergeIndividualsRequest** (Lines 70-83):
```python
class MergeIndividualsRequest(BaseModel):
    """Request model for manually merging individuals."""
    individual_uuids: List[str] = Field(
        ...,
        min_length=2,
        description="List of individual UUIDs to merge (minimum 2)"
    )
    session_uuid: str = Field(
        ..., description="Session UUID for filtering"
    )
    similarity_threshold: float = Field(
        0.75,
        ge=0.0, le=1.0,
        description="Minimum similarity score for merge (0.0-1.0)"
    )
    triggered_by: str = Field(
        "manual_ui",
        description="Source of merge trigger"
    )
```

**MergeIndividualsResponse** (Lines 86-95):
```python
class MergeIndividualsResponse(BaseModel):
    """Response model for individual merge operation."""
    success: bool
    predominant_individual_uuid: str
    merged_individual_uuids: List[str]
    similarity_score: Optional[float]
    statistics: Dict[str, Any]
    message: str
    timestamp: str
```

#### 2. Merge Endpoint (`ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`)

**Route:** `POST /api/v1/cross-video/individuals/tracking/merge`

**Functionality:**
- Validates request (minimum 2 individuals)
- Retrieves individual data from database
- Fetches face crops from Vision database
- Generates 512-dimensional embeddings using Facenet512
- Calculates pairwise cosine similarity
- Validates similarity against threshold
- Selects predominant individual (best quality score)
- Transfers all appearances in transaction
- Deletes merged individuals
- Returns merge statistics

**Key Implementation Steps:**
1. Validate individual UUIDs exist in session
2. Query Vision DB for best face crops
3. Generate facial embeddings using `EmbeddingService._generate_facial_embedding()`
4. Calculate cosine similarity with sklearn
5. Select predominant based on quality scores
6. Transfer appearances atomically
7. Delete merged individuals
8. Return comprehensive response

#### 3. Gateway Route (`ppl-meta-gateway/src/api/v1/router.py`)

**Route:** `POST /api/v1/cross-video/individuals/tracking/merge`

Proxies requests to vmeta service with JWT token propagation.

---

### Frontend Changes

#### 1. API Client Method (`ppl-meta-frontend/lib/services/media_api_client.dart`)

**Method:** `mergeIndividuals()`

```dart
Future<ApiResponse<Map<String, dynamic>>> mergeIndividuals({
  required List<String> individualUuids,
  required String sessionUuid,
  double similarityThreshold = 0.75,
}) async {
  final requestBody = {
    'individual_uuids': individualUuids,
    'session_uuid': sessionUuid,
    'similarity_threshold': similarityThreshold,
    'triggered_by': 'flutter_ui_manual_selection',
  };
  
  final response = await _apiClient.post(
    '/api/v1/cross-video/individuals/tracking/merge',
    data: requestBody,
  );
  
  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

#### 2. UI State Management (`ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`)

**Added State Variables:**
```dart
// Track selected individuals for merging
final Set<String> _selectedIndividuals = {};
```

**Modified Individual Card:**
- Added Checkbox widget before individual icon
- Checkbox state tracked in `_selectedIndividuals` Set
- OnChanged handler adds/removes individual UUID

```dart
Checkbox(
  value: isSelected,
  onChanged: (bool? value) {
    setState(() {
      if (value == true) {
        _selectedIndividuals.add(analysis.individualUuid);
      } else {
        _selectedIndividuals.remove(analysis.individualUuid);
      }
    });
  },
),
```

#### 3. Floating Action Button

**Conditional Display:**
- Only shown in cross-video mode
- Only visible when ≥2 individuals selected
- Shows count of selected individuals

```dart
floatingActionButton: _isCrossVideoMode && _selectedIndividuals.length >= 2
    ? FloatingActionButton.extended(
        onPressed: _showMergeConfirmationDialog,
        icon: const Icon(Icons.merge),
        label: Text('Merge ${_selectedIndividuals.length} Individuals'),
        backgroundColor: Colors.blue,
      )
    : null,
```

#### 4. Confirmation Dialog

**Method:** `_showMergeConfirmationDialog()`

**Features:**
- Shows number of individuals to merge
- Lists selected individual UUIDs
- Explains embedding validation process
- Provides Cancel/Merge buttons

#### 5. Merge Execution

**Method:** `_executeMerge()`

**Flow:**
1. Shows loading indicator
2. Calls `mediaApiClient.mergeIndividuals()`
3. Dismisses loading on response
4. Shows success/error SnackBar with statistics
5. Clears selection
6. Reloads cross-video data to reflect changes

**Success Message:**
```
Successfully merged X individuals
Similarity: YY.Y%
```

**Error Handling:**
- Network errors caught and displayed
- Backend validation errors shown to user
- Loading indicator always dismissed

---

## Technical Architecture

### Embedding Generation Pipeline

1. **Database Retrieval**
   - Query `individual_video_appearances` for individual's videos
   - Query Vision DB `person_objects` for best quality face
   - Retrieve `face_crops` with base64 data

2. **Face Processing**
   - Decode base64 → numpy array
   - Decode image with OpenCV
   - Validate image format (HxWxC)

3. **Embedding Generation**
   - Use `EmbeddingService._generate_facial_embedding()`
   - Model: DeepFace Facenet512
   - Output: 512-dimensional vector (L2 normalized)

4. **Similarity Calculation**
   - Compute pairwise cosine similarity
   - Use sklearn.metrics.pairwise.cosine_similarity
   - Formula: `similarity = (A · B) / (||A|| × ||B||)`
   - Threshold: 0.75 (configurable)

### Database Transaction Safety

Merge operation uses atomic transaction:
```python
async with db_client.vmeta_pool.acquire() as conn:
    async with conn.transaction():
        # Transfer appearances
        await conn.execute(
            "UPDATE individual_video_appearances SET individual_uuid = $1 WHERE individual_uuid = $2",
            predominant_uuid, merge_uuid
        )
        # Delete merged individual
        await conn.execute(
            "DELETE FROM individuals WHERE individual_uuid = $1",
            merge_uuid
        )
```

---

## API Reference

### Request

**Endpoint:** `POST /api/v1/cross-video/individuals/tracking/merge`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Body:**
```json
{
  "individual_uuids": [
    "5c73fd34-737a-48c7-a69a-f17b40adbead",
    "8f91ab25-9d3e-4c1a-b45f-3e8c7a2f1b9c"
  ],
  "session_uuid": "4a0515cf-12ee-45f0-8945-e7b2ae7bbe24",
  "similarity_threshold": 0.75,
  "triggered_by": "flutter_ui_manual_selection"
}
```

### Response

**Success (200):**
```json
{
  "success": true,
  "predominant_individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "merged_individual_uuids": [
    "8f91ab25-9d3e-4c1a-b45f-3e8c7a2f1b9c"
  ],
  "similarity_score": 0.852,
  "statistics": {
    "total_appearances_transferred": 5,
    "total_videos_affected": 3
  },
  "message": "Successfully merged 1 individuals into predominant individual",
  "timestamp": "2025-05-28T14:32:45Z"
}
```

**Validation Error (400):**
```json
{
  "detail": "Faces are not similar enough to merge (similarity: 0.42 < threshold: 0.75)"
}
```

**Not Found (404):**
```json
{
  "detail": "Individual UUID not found in session"
}
```

---

## Testing Instructions

### Prerequisites
1. Ensure all services are running (vmeta, gateway, vision, media)
2. Have Flutter app running (web or desktop)
3. Authenticated user with valid JWT token

### Test Case 1: Successful Merge

1. **Create Tracking Session:**
   ```
   Collections: usb_camera_0
   Time Range: Last 7 days
   Wait for completion
   ```

2. **Navigate to Individuals Tab:**
   - Click "View Individuals" button
   - PersonObjectsDetailScreen opens in cross-video mode
   - Individuals tab shows list of detected individuals

3. **Select Individuals:**
   - Check boxes for 2-3 individuals
   - Verify FloatingActionButton appears
   - Button text shows "Merge X Individuals"

4. **Initiate Merge:**
   - Click FloatingActionButton
   - Confirmation dialog appears
   - Review selected UUIDs
   - Click "Merge"

5. **Verify Success:**
   - Loading indicator displays
   - Success SnackBar shows merge statistics
   - Individual list refreshes automatically
   - Merged individuals removed from list
   - Selection cleared

6. **Verify Database:**
   ```sql
   -- Check predominant individual has more appearances
   SELECT * FROM individual_video_appearances 
   WHERE individual_uuid = '<predominant_uuid>';
   
   -- Verify merged individuals deleted
   SELECT * FROM individuals 
   WHERE individual_uuid IN ('<merged_uuids>');
   -- Should return 0 rows
   ```

### Test Case 2: Similarity Validation Failure

1. Select individuals with visually different faces
2. Attempt merge
3. Verify error message: "Faces are not similar enough to merge"
4. Check selection remains intact
5. Verify no database changes occurred

### Test Case 3: Error Handling

1. **Network Error:**
   - Disconnect network
   - Attempt merge
   - Verify error SnackBar displays
   - Verify loading indicator dismissed

2. **Invalid Session:**
   - Use non-existent session UUID
   - Verify 404 error handled gracefully

---

## Files Modified

### Backend
1. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`
   - Lines 70-95: Added MergeIndividualsRequest and MergeIndividualsResponse models
   - Lines 1710+: Added merge_individuals_manual() endpoint

2. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/src/api/v1/router.py`
   - Line 1496: Added POST /cross-video/individuals/tracking/merge proxy route

### Frontend
3. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/services/media_api_client.dart`
   - Lines 988-1037: Added mergeIndividuals() method

4. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
   - Line 65: Added _selectedIndividuals state variable
   - Lines 110-119: Added FloatingActionButton with conditional display
   - Lines 3147-3190: Modified _buildIndividualCard() to include Checkbox
   - Lines 1300-1437: Added _showMergeConfirmationDialog() and _executeMerge() methods

### Documentation
5. `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/docs/MANUAL_INDIVIDUAL_MERGE_IMPLEMENTATION.md` (this file)

---

## Code Statistics

**Lines Added:**
- Backend: ~250 lines (models + endpoint + validation logic)
- Frontend: ~180 lines (UI + dialog + API call)
- Total: ~430 lines

**Compilation:** ✅ Zero errors in Flutter files  
**Linting:** Python files have expected IDE warnings (imports, lazy logging)

---

## Future Enhancements

1. **Batch Merge:**
   - Allow merging 3+ individuals simultaneously
   - Show similarity matrix for all pairs
   - Visualize merge clusters

2. **Face Preview:**
   - Show face thumbnails in confirmation dialog
   - Display similarity scores between each pair
   - Highlight predominant individual visually

3. **Undo Functionality:**
   - Track merge history
   - Allow reverting recent merges
   - Restore split individuals

4. **Smart Suggestions:**
   - Automatically suggest individuals likely to be duplicates
   - Pre-select high-similarity pairs
   - Show confidence indicators

5. **Advanced Filtering:**
   - Filter individuals by similarity range
   - Show only duplicates above threshold
   - Group by likely identity

---

## Related Documentation

- `FACE_EMBEDDINGS_FOR_INDIVIDUAL_MERGING.md` - Technical analysis of embedding extraction
- `CROSS_VIDEO_INDIVIDUAL_ANALYSIS_IMPLEMENTATION.md` - Overall cross-video feature architecture
- `FLUTTER_PHASE_5_6_INTEGRATION_COMPLETE.md` - Flutter integration patterns
- `WORKING_CROSS_VIDEO_TRACKING_ANALYSIS.md` - Working session creation flow

---

## Success Metrics

**Feature Completion:**
- ✅ Backend models implemented
- ✅ Backend endpoint with embedding validation
- ✅ Gateway proxy route
- ✅ Flutter API client method
- ✅ UI checkboxes for selection
- ✅ Floating action button with dynamic count
- ✅ Confirmation dialog with details
- ✅ Error handling and loading states
- ✅ Auto-refresh after merge
- ⏳ End-to-end testing (pending)

**Code Quality:**
- ✅ Type-safe Pydantic models with validation
- ✅ Transaction-safe database operations
- ✅ Proper error propagation
- ✅ Comprehensive logging
- ✅ Clean Flutter state management
- ✅ User-friendly error messages

---

## Conclusion

The manual individual merge feature is **fully implemented and ready for testing**. It provides a complete user workflow from selection through validation to database update, with robust error handling and a polished UI experience. The implementation follows existing patterns in the codebase and integrates seamlessly with the cross-video tracking system.

**Next Step:** End-to-end testing to verify the complete workflow and validate embedding similarity calculations.

---

**Last Updated:** May 28, 2025  
**Implementation Version:** v2.20.0  
**Status:** ✅ COMPLETE - READY FOR TESTING
