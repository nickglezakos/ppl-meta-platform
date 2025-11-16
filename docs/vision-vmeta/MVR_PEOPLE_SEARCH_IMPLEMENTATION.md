# MVR People Search Implementation - v2.19.33

**Date:** November 16, 2025  
**Author:** PPL Meta Platform  
**Version:** 2.19.33

## Summary

Modified the Collections screen search functionality to fetch **existing cached MVR people** and their linked individuals without triggering any merge operations. The search modal now displays pre-computed MVR analysis results instead of creating new tracking sessions.

## Problem Statement

The collections screen search button was creating a new cross-video tracking session which:
1. Triggered MVR merge processing
2. Created duplicate tracking sessions for the same time range
3. Unnecessarily reprocessed videos that had already been analyzed

**User Request:**
> "I need this modal to stay as is but to execute a search fetching the MVR people objects and linked individual that were created within the search parameters. I don't need it to execute any merge mvr people endpoint just fetch the existing / cached MVR people and linked individual data objects following the EXACT SAME STRUCTURE as the existing ones that feed the analysis screen"

## Solution Overview

Created a new search endpoint that:
- **Fetches existing MVR people** created within the date/time range
- **Returns linked individuals** and their video appearances
- **Uses the same data structure** as the aggregated analysis endpoint
- **Does NOT trigger any merge operations** - read-only cached data

## Changes Made

### 1. Backend - VMeta Service

#### New Models (`ppl-meta-vmeta/src/api/models/mvr_search_models.py`)

```python
class MVRPeopleSearchRequest(BaseModel):
    collection_name: str
    start_time: datetime
    end_time: datetime
    limit: int = Field(100, ge=1, le=500)

class MVRPersonResult(BaseModel):
    mvr_people_uuid: str
    individual_uuids: List[str]
    total_appearances: int
    unique_videos: int
    first_seen: datetime
    last_seen: datetime
    confidence_score: float
    quality_score: float
    appearances: List[IndividualAppearance]
    estimated_age: Optional[int]
    estimated_gender: Optional[str]

class MVRPeopleSearchResponse(BaseModel):
    success: bool = True
    total_results: int
    mvr_people: List[MVRPersonResult]
    search_parameters: dict
    message: Optional[str]
```

#### New Endpoint (`ppl-meta-vmeta/src/api/routes/mvr_people.py`)

**Endpoint:** `POST /api/v1/mvr-people/search/by-collection`

**Features:**
- Queries MVR people created within specified date range
- Filters by collection (camera device ID or collection UUID)
- Joins with `individual_mvr_mapping` to get linked individuals
- Joins with `individual_video_appearances` to get video appearances
- Returns aggregated statistics (total appearances, unique videos, time range)
- **Read-only operation** - no merge processing

**Query Logic:**
```sql
SELECT DISTINCT mp.* 
FROM mvr_people mp
JOIN individual_mvr_mapping imm ON mp.mvr_people_uuid = imm.mvr_people_uuid
JOIN individuals ind ON imm.individual_uuid = ind.individual_uuid
JOIN individual_video_appearances iva ON ind.individual_uuid = iva.individual_uuid
JOIN videos v ON iva.video_uuid = v.video_uuid
WHERE v.collection_name = $1
    AND mp.created_at >= $2
    AND mp.created_at <= $3
    AND mp.is_orphaned = false
```

### 2. Gateway Service

#### New Route (`ppl-meta-gateway/src/api/v1/router.py`)

```python
@api_router.post("/mvr-people/search/by-collection")
async def search_mvr_people_by_collection(request: Request):
    """Proxy MVR people search by collection request to vmeta service."""
    return await _proxy_to_vmeta_service(request)
```

### 3. Frontend - Flutter

#### API Client (`ppl-meta-frontend/lib/services/media_api_client.dart`)

**New Method:** `searchMVRPeopleByCollection()`

```dart
Future<ApiResponse<Map<String, dynamic>>> searchMVRPeopleByCollection({
  required String collectionName,
  required DateTime startTime,
  required DateTime endTime,
  int limit = 100,
}) async {
  final response = await _apiClient.post(
    '/api/v1/mvr-people/search/by-collection',
    data: {
      'collection_name': collectionName,
      'start_time': startTime.toIso8601String(),
      'end_time': endTime.toIso8601String(),
      'limit': limit,
    },
  );
  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

#### Collections Screen (`ppl-meta-frontend/lib/screens/collections_screen.dart`)

**Modified Method:** `_fetchIndividualsCount()`

**Before:**
- Created new cross-video tracking session
- Polled for session completion
- Triggered MVR merge processing
- Waited for background processing

**After:**
- Searches for existing MVR people
- Fetches cached data (read-only)
- Counts total appearances and unique MVR people
- No merge operations or reprocessing

**Key Changes:**
```dart
// OLD: Create tracking session
final createResponse = await mediaApiClient.createCrossVideoTrackingSession(
  collectionName: collectionIdentifier,
  startTime: _startDate!,
  endTime: _endDate!,
);

// NEW: Search existing MVR people
final searchResponse = await mediaApiClient.searchMVRPeopleByCollection(
  collectionName: collectionIdentifier,
  startTime: _startDate!,
  endTime: _endDate!,
  limit: 500,
);
```

**Modified Method:** `_navigateToIndividualAnalysis()`

**Before:**
- Fetched individuals from tracking session UUID
- Required active tracking session

**After:**
- Extracts MVR people UUIDs from search results
- Uses MVR UUIDs for analysis navigation
- Creates dummy session UUID (not needed for analysis)

## Data Flow

### Old Flow (Tracking Session)
```
User clicks Search
  ↓
Create tracking session → Process videos → Match person objects
  ↓                         ↓                ↓
Poll status → Background processing → MVR merge
  ↓
Display counts (original + unique)
  ↓
Navigate to analysis screen
```

### New Flow (MVR Search)
```
User clicks Search
  ↓
Search existing MVR people (by collection + date range)
  ↓
Return cached MVR people with linked individuals
  ↓
Count appearances and MVR people
  ↓
Display counts (appearances + unique MVR)
  ↓
Navigate to analysis screen with MVR UUIDs
```

## Benefits

1. **No Reprocessing:** Fetches existing analysis results instead of creating new sessions
2. **Faster Response:** Direct database query instead of background processing
3. **No Duplicates:** Avoids creating multiple tracking sessions for same parameters
4. **Read-Only:** No side effects - doesn't trigger merge operations
5. **Same Structure:** Returns data in exact same format as aggregated analysis endpoint
6. **Backwards Compatible:** Analysis screen works with MVR UUIDs

## API Response Structure

### Search Response
```json
{
  "success": true,
  "total_results": 5,
  "mvr_people": [
    {
      "mvr_people_uuid": "mvr-uuid-1",
      "individual_uuids": ["ind-001", "ind-007"],
      "total_appearances": 15,
      "unique_videos": 3,
      "first_seen": "2025-11-16T08:15:00Z",
      "last_seen": "2025-11-16T10:30:00Z",
      "confidence_score": 0.92,
      "quality_score": 0.88,
      "appearances": [
        {
          "video_uuid": "video-001",
          "person_object_uuid": "person-001",
          "start_timestamp": "2025-11-16T08:15:00Z",
          "end_timestamp": "2025-11-16T08:20:00Z",
          "confidence": 0.95
        }
      ],
      "estimated_age": 35,
      "estimated_gender": "male"
    }
  ],
  "search_parameters": {
    "collection_name": "usb_camera_0",
    "start_time": "2025-11-16T08:00:00Z",
    "end_time": "2025-11-16T12:00:00Z",
    "limit": 500
  },
  "message": "Found 5 existing MVR people"
}
```

## Testing

### Manual Test Steps

1. **Start Services:**
   ```bash
   # Terminal 1 - Start all services
   🚀 Start All Local Python Services
   ```

2. **Open Flutter App:**
   - Navigate to Collections screen
   - Select a collection (e.g., `usb_camera_0`)

3. **Use Search Modal:**
   - Click search icon (🔍)
   - Select date/time range with existing MVR data
   - Click "Apply"

4. **Verify Results:**
   - Should show: "Individuals: X → Y unique"
   - X = Total appearances across all MVR people
   - Y = Total unique MVR people found
   - No tracking session created
   - No merge operations triggered

5. **Navigate to Analysis:**
   - Click "Analysis" button
   - Should open PersonObjectsDetailScreen
   - Display aggregated analysis for MVR people

### Expected Console Output

```
🔍 Searching existing MVR people for collection: usb_camera_0
   Date range: 2025-11-16T08:00:00.000 to 2025-11-16T12:00:00.000
✅ Found 5 existing MVR people
📊 MVR Search Results:
   Total appearances: 23
   Unique MVR people: 5
📊 Navigating to analysis with 5 MVR people
```

## Files Modified

1. `ppl-meta-vmeta/src/api/models/mvr_search_models.py` (NEW)
2. `ppl-meta-vmeta/src/api/routes/mvr_people.py` (MODIFIED)
3. `ppl-meta-gateway/src/api/v1/router.py` (MODIFIED)
4. `ppl-meta-frontend/lib/services/media_api_client.dart` (MODIFIED)
5. `ppl-meta-frontend/lib/screens/collections_screen.dart` (MODIFIED)

## Backwards Compatibility

- Old tracking session functionality still available via different endpoints
- Analysis screen supports both individual UUIDs and MVR UUIDs
- No breaking changes to existing endpoints

## Future Enhancements

1. **Cache Duration Filter:** Add option to filter by when MVR was created vs when videos were recorded
2. **Quality Filtering:** Add min_quality_score parameter to filter low-quality MVR people
3. **Pagination:** Implement proper pagination for large result sets
4. **Demographic Filters:** Add age/gender filters to search
5. **Collection Groups:** Support searching multiple collections at once

## Notes

- The analysis screen's `getIndividualAggregatedAnalysis` endpoint already supports MVR UUIDs, so no changes needed there
- We use MVR UUIDs as "individual" UUIDs when navigating to the analysis screen
- The search is based on when the MVR person was created, not when the videos were recorded
- Results are limited to 500 by default to prevent overwhelming the UI

## Version History

- **v2.19.32:** Incremental MVR batching with recording-aware polling
- **v2.19.33:** MVR people search by collection (this version)

---

**Implementation Complete:** November 16, 2025
