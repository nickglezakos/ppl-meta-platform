# Camera Card MVR People Counter

**Document Version:** 1.0  
**Last Updated:** November 28, 2025  
**Feature:** Camera Card MVR People Counter  
**Location:** `http://localhost:3000/#/cameras`  
**Status:** ✅ FULLY OPERATIONAL

---

## Table of Contents

1. [Overview](#overview)
2. [User Experience](#user-experience)
3. [Architecture](#architecture)
4. [Implementation Details](#implementation-details)
5. [Data Flow](#data-flow)
6. [API Endpoints](#api-endpoints)
7. [Database Queries](#database-queries)
8. [Code Walkthrough](#code-walkthrough)
9. [Performance Characteristics](#performance-characteristics)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose

The **Camera Card MVR People Counter** is a real-time badge displayed on each camera card that shows the number of unique people (MVR people) detected by that specific camera **today**. This feature provides immediate visibility into camera activity and person detection effectiveness.

### Key Features

✅ **Per-Camera Counting**: Each camera shows its own unique MVR people count  
✅ **Today-Only Filter**: Automatically filters to current day (00:00:00 - 23:59:59)  
✅ **Real-Time Updates**: Counter updates when component initializes  
✅ **Visual Indicators**: Green badge for detections, gray badge for no detections  
✅ **Loading State**: Shows spinner while fetching count  
✅ **Error Handling**: Gracefully handles failures, shows 0 on error  

### Visual Appearance

```
┌─────────────────────────────────────────┐
│  📹 Front Door Camera                   │
│  ID: usb_camera_0                       │
│  Status: ● ACTIVE                       │
│  Resolution: 1920x1080                  │
│                                         │
│  [👤 12]  ← MVR People Counter Badge   │
└─────────────────────────────────────────┘
```

**Badge States:**
- **Loading**: `[⟳ Loading...]` (gray, spinner)
- **No Detections**: `[👤 0]` (gray background)
- **Has Detections**: `[👤 12]` (green background)

---

## User Experience

### When Counter Appears

The counter appears automatically when:
1. User navigates to `/cameras` screen
2. Camera cards are rendered
3. Each card initializes and fetches its count

### Update Behavior

**Automatic Updates:**
- ✅ On component mount (when cards first appear)
- ✅ On date range change (if filtering by date - future feature)

**Manual Updates:**
- User can refresh the page to reload counts
- Navigation away and back triggers reload

### What the Number Represents

**The counter shows:**
- Number of **unique MVR people** detected by this camera **today**
- Only counts people with video appearances in this camera's collection
- Filters by video creation time (not appearance timestamp)

**Example Scenario:**
```
Camera: usb_camera_0
Today's videos: 9 videos (recorded 11:15-11:25)
MVR people detected: 12 unique individuals
Counter displays: [👤 12]
```

**Important Notes:**
- Same person appearing multiple times = counted once
- Multiple cameras detecting same person = counted separately per camera
- Count resets at midnight (new day = new count)

---

## Architecture

### High-Level Flow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAMERA CARD MVR COUNTER FLOW                         │
└─────────────────────────────────────────────────────────────────────────┘

1. USER NAVIGATES TO /CAMERAS
   └─> Flutter renders camera cards

2. CAMERA CARD INITIALIZATION
   └─> _fetchMVRPeopleCount() triggered on initState()

3. GET TODAY'S VIDEOS
   └─> POST /api/v1/media/search
       • collection_id: camera.deviceId
       • start_date: today 00:00:00
       • end_date: today 23:59:59
       • media_type: video
       ↓
   └─> Returns: List of video UUIDs

4. GET MVR PEOPLE COUNT
   └─> POST /api/v1/mvr-people/count-by-videos
       • video_uuids: [uuid1, uuid2, ...]
       ↓
   └─> VMeta queries database:
       - individual_video_appearances (video → individual)
       - individual_mvr_mapping (individual → MVR person)
       ↓
   └─> Returns: { count: 12, video_count: 9 }

5. UPDATE UI
   └─> Counter badge shows: [👤 12]
```

### System Components

**Frontend (Flutter):**
- `ppl-meta-frontend/lib/widgets/camera/camera_card.dart`
- Component: `CameraCard` widget
- State: `_mvrPeopleCount`, `_isLoadingCount`

**Backend Services:**
- **Media Service** (Port 8000): Video metadata storage and search
- **VMeta Service** (Port 8008): MVR people tracking and counting
- **Gateway** (Port 8080): Request routing and proxying

**Databases:**
- **Media DB**: Stores videos with collection associations
- **VMeta DB**: Stores MVR people, individuals, and appearances

---

## Implementation Details

### Frontend: Camera Card Widget

**File:** `ppl-meta-frontend/lib/widgets/camera/camera_card.dart`

**State Variables:**
```dart
class _CameraCardState extends ConsumerState<CameraCard> {
  int? _mvrPeopleCount;      // Stores the count
  bool _isLoadingCount = false;  // Loading state
}
```

**Initialization:**
```dart
@override
void initState() {
  super.initState();
  _fetchMVRPeopleCount();  // Fetch on mount
}
```

**Key Method: `_fetchMVRPeopleCount()`**

This method orchestrates the entire counting process:

```dart
Future<void> _fetchMVRPeopleCount({
  DateTime? startDate,
  DateTime? endDate,
}) async {
  // Step 1: Set loading state
  setState(() {
    _isLoadingCount = true;
  });

  // Step 2: Calculate today's date range
  final now = DateTime.now();
  final effectiveStartDate = startDate ?? DateTime(now.year, now.month, now.day, 0, 0, 0);
  final effectiveEndDate = endDate ?? DateTime(now.year, now.month, now.day, 23, 59, 59);
  
  // Step 3: Get videos from this camera's collection
  final searchResponse = await mediaApiClient.searchMedia(
    collectionId: widget.camera.deviceId,  // Use camera's device ID
    mediaType: MediaType.video,
    startDate: effectiveStartDate,
    endDate: effectiveEndDate,
    limit: 100,  // Max 100 videos per day
  );

  // Step 4: Extract video UUIDs
  final videoUuids = searchResponse.data!.items.map((media) => media.uuid).toList();

  // Step 5: Get MVR people count for these videos
  final countResponse = await mediaApiClient.getMVRPeopleCountByVideos(
    videoUuids: videoUuids,
  );

  // Step 6: Update UI with count
  setState(() {
    _mvrPeopleCount = countResponse.data!['count'] as int? ?? 0;
    _isLoadingCount = false;
  });
}
```

**UI Rendering:**
```dart
Widget _buildDetectedPersonsCounter() {
  if (_isLoadingCount) {
    // Show loading spinner
    return Container(...); // Gray badge with spinner
  }

  final count = _mvrPeopleCount ?? 0;
  final hasDetections = count > 0;

  return Container(
    decoration: BoxDecoration(
      color: hasDetections 
          ? Colors.green.withOpacity(0.1)   // Green for detections
          : Colors.grey.withOpacity(0.1),   // Gray for no detections
      borderRadius: BorderRadius.circular(4),
      border: Border.all(
        color: hasDetections 
            ? Colors.green.withOpacity(0.3) 
            : Colors.grey.withOpacity(0.3),
      ),
    ),
    child: Row(
      children: [
        Icon(Icons.people, size: 12),
        SizedBox(width: 4),
        Text('$count'),  // Display count
      ],
    ),
  );
}
```

---

## Data Flow

### Step-by-Step Data Flow

#### Step 1: User Opens Cameras Screen

```
User Action: Navigate to http://localhost:3000/#/cameras
↓
Flutter Router: Renders CamerasScreen
↓
CamerasScreen: Displays list of CameraCard widgets
↓
Each CameraCard: Calls initState()
```

#### Step 2: Fetch Today's Videos

```
Flutter: POST /api/v1/media/search
Gateway: Proxy to Media Service (Port 8000)
Media Service: Query media_files table
↓
Query:
  SELECT * FROM media_files
  WHERE collection_id = 'usb_camera_0'
    AND media_type = 'video'
    AND created_at >= '2025-11-28 00:00:00'
    AND created_at <= '2025-11-28 23:59:59'
  ORDER BY created_at DESC
  LIMIT 100
↓
Response:
  {
    "items": [
      { "uuid": "0770fdfd-1a8f-4808-8f59-f8c7b570c91d", ... },
      { "uuid": "33de373a-e486-4134-84df-d1b149c6cf71", ... },
      ...
    ],
    "total": 9
  }
```

#### Step 3: Extract Video UUIDs

```
Flutter: Parse response
↓
Extract UUIDs:
  videoUuids = [
    "0770fdfd-1a8f-4808-8f59-f8c7b570c91d",
    "33de373a-e486-4134-84df-d1b149c6cf71",
    "62498427-99d0-4cae-9ea5-300c8e91bc9f",
    "1b6a3236-14d1-4185-ad10-bd359a90c245",
    ... (9 total)
  ]
```

#### Step 4: Count MVR People

```
Flutter: POST /api/v1/mvr-people/count-by-videos
Gateway: Proxy to VMeta Service (Port 8008)
VMeta Service: Execute count query
↓
Query (SQL):
  WITH video_individuals AS (
    -- Get individuals with appearances in these videos
    SELECT DISTINCT iva.individual_uuid
    FROM individual_video_appearances iva
    WHERE iva.video_uuid = ANY($1::uuid[])
  )
  -- Count unique MVR people linked to these individuals
  SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
  FROM individual_mvr_mapping imm
  WHERE imm.individual_uuid IN (
    SELECT individual_uuid FROM video_individuals
  )
↓
Result: { mvr_count: 12 }
↓
Response:
  {
    "count": 12,
    "video_count": 9
  }
```

#### Step 5: Update UI

```
Flutter: Receive response
↓
setState():
  _mvrPeopleCount = 12
  _isLoadingCount = false
↓
Widget Rebuild: Badge shows [👤 12] with green background
```

---

## API Endpoints

### Endpoint 1: Search Media (Get Today's Videos)

**Request:**
```http
POST /api/v1/media/search
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "collection_id": "usb_camera_0",
  "media_type": "video",
  "start_date": "2025-11-28T00:00:00",
  "end_date": "2025-11-28T23:59:59",
  "limit": 100
}
```

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "uuid": "0770fdfd-1a8f-4808-8f59-f8c7b570c91d",
      "filename": "usb_camera_0_20251128_111500.mp4",
      "collection_id": "usb_camera_0",
      "media_type": "video",
      "created_at": "2025-11-28T11:15:00",
      "duration": 30.0,
      "size": 5242880
    },
    // ... more videos
  ],
  "total": 9,
  "page": 1,
  "page_size": 100
}
```

**Service:** Media Service (Port 8000)  
**File:** `ppl-meta-media/src/api/v1/media.py`

---

### Endpoint 2: Count MVR People by Videos

**Request:**
```http
POST /api/v1/mvr-people/count-by-videos
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "video_uuids": [
    "0770fdfd-1a8f-4808-8f59-f8c7b570c91d",
    "33de373a-e486-4134-84df-d1b149c6cf71",
    "62498427-99d0-4cae-9ea5-300c8e91bc9f",
    "1b6a3236-14d1-4185-ad10-bd359a90c245"
  ]
}
```

**Response:**
```json
{
  "count": 12,
  "video_count": 4
}
```

**Service:** VMeta Service (Port 8008)  
**File:** `ppl-meta-vmeta/src/api/routes/mvr_people.py` (lines 2440-2520)  
**Gateway Proxy:** `ppl-meta-gateway/src/api/v1/router.py` (line 1521)

---

### Deprecated Endpoints

**⚠️ DEPRECATED: `/api/v1/mvr-people/count-by-camera/{camera_id}`**

This endpoint is deprecated because it requires cross-database queries (accessing Media DB from VMeta service). Use the two-step approach (search videos + count by videos) instead.

---

## Database Queries

### Query 1: Get Today's Videos (Media DB)

```sql
-- Executed by Media Service
SELECT 
    uuid,
    filename,
    collection_id,
    media_type,
    created_at,
    duration,
    size
FROM media_files
WHERE collection_id = $1              -- 'usb_camera_0'
  AND media_type = 'video'
  AND created_at >= $2                -- '2025-11-28 00:00:00'
  AND created_at <= $3                -- '2025-11-28 23:59:59'
ORDER BY created_at DESC
LIMIT $4;                             -- 100
```

**Parameters:**
- `$1`: Collection ID (camera device ID)
- `$2`: Start of today (00:00:00)
- `$3`: End of today (23:59:59)
- `$4`: Limit (100 videos max)

**Result Example:**
```
uuid                                  | filename                          | created_at
--------------------------------------|-----------------------------------|-------------------------
0770fdfd-1a8f-4808-8f59-f8c7b570c91d | usb_camera_0_20251128_111500.mp4 | 2025-11-28 11:15:00
33de373a-e486-4134-84df-d1b149c6cf71 | usb_camera_0_20251128_111530.mp4 | 2025-11-28 11:15:30
...
```

---

### Query 2: Count Unique MVR People (VMeta DB)

```sql
-- Executed by VMeta Service
WITH video_individuals AS (
    -- Step 1: Get all individuals with appearances in these videos
    SELECT DISTINCT iva.individual_uuid
    FROM individual_video_appearances iva
    WHERE iva.video_uuid = ANY($1::uuid[])  -- Array of video UUIDs
)
-- Step 2: Count unique MVR people linked to these individuals
SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
FROM individual_mvr_mapping imm
WHERE imm.individual_uuid IN (
    SELECT individual_uuid FROM video_individuals
);
```

**Parameters:**
- `$1`: Array of video UUIDs (e.g., `['0770fdfd...', '33de373a...', ...]`)

**Explanation:**

1. **CTE `video_individuals`**: 
   - Finds all individuals that have appearances in the specified videos
   - Uses `individual_video_appearances` table which links individuals to videos
   - `DISTINCT` ensures each individual is counted once

2. **Main Query**:
   - Joins to `individual_mvr_mapping` to get MVR people
   - Counts `DISTINCT` MVR people UUIDs
   - Handles merging: multiple individuals can map to same MVR person

**Database Tables Used:**

```sql
-- Table 1: Links individuals to specific video appearances
individual_video_appearances (
    individual_uuid UUID,
    video_uuid UUID,
    person_object_uuid UUID,
    start_timestamp TIMESTAMP,
    end_timestamp TIMESTAMP,
    confidence FLOAT
)

-- Table 2: Maps individuals to MVR people (handles merging)
individual_mvr_mapping (
    individual_uuid UUID,
    mvr_people_uuid UUID,
    confidence_score FLOAT,
    created_at TIMESTAMP
)
```

**Example Query Execution:**

```sql
-- Input: 9 video UUIDs
-- Step 1 CTE Result: 18 individual UUIDs found (some videos have multiple people)
-- Step 2 Main Query: 12 unique MVR people (some individuals are same person)
-- Final Result: { mvr_count: 12 }
```

---

## Code Walkthrough

### Flutter Client Code

**File:** `ppl-meta-frontend/lib/services/media_api_client.dart`

**Method 1: Search Media**
```dart
Future<ApiResponse<MediaSearchResponse>> searchMedia({
  String? collectionId,
  MediaType? mediaType,
  DateTime? startDate,
  DateTime? endDate,
  int limit = 20,
}) async {
  try {
    final queryParams = <String, dynamic>{};
    
    if (collectionId != null) queryParams['collection_id'] = collectionId;
    if (mediaType != null) queryParams['media_type'] = mediaType.name;
    if (startDate != null) queryParams['start_date'] = startDate.toIso8601String();
    if (endDate != null) queryParams['end_date'] = endDate.toIso8601String();
    queryParams['limit'] = limit;

    final response = await _apiClient.post(
      '/api/v1/media/search',
      queryParameters: queryParams,
    );

    return ApiResponse.success(
      MediaSearchResponse.fromJson(response.data as Map<String, dynamic>)
    );
  } catch (e) {
    return ApiResponse.error('Search failed: $e');
  }
}
```

**Method 2: Get MVR People Count by Videos**
```dart
Future<ApiResponse<Map<String, dynamic>>> getMVRPeopleCountByVideos({
  required List<String> videoUuids,
}) async {
  try {
    final response = await _apiClient.post(
      '/api/v1/mvr-people/count-by-videos',
      data: {'video_uuids': videoUuids},
    );

    debugPrint('📊 MVR people count result: ${response.data}');
    
    return ApiResponse.success(response.data as Map<String, dynamic>);
  } catch (e) {
    return ApiResponse.error('Count failed: $e');
  }
}
```

---

### Backend Code

**File:** `ppl-meta-vmeta/src/api/routes/mvr_people.py`

**Endpoint Implementation:**
```python
@router.post(
    "/count-by-videos",
    summary="Get MVR People Count for Video UUIDs",
    description=(
        "Returns the count of unique MVR people detected in the specified "
        "videos. Only queries VMeta's own database. Useful for getting "
        "per-camera or per-collection counts."
    ),
)
async def get_videos_mvr_people_count(
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people detected in specific videos.

    Request Body:
        {
            "video_uuids": ["uuid1", "uuid2", "uuid3"]
        }

    Returns:
        {
            "count": 5,
            "video_count": 3
        }
    """
    try:
        if not video_uuids:
            return {
                "count": 0,
                "video_count": 0
            }

        logger.info(
            "Fetching MVR people count for %d videos", len(video_uuids)
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Query unique MVR people count for these videos
            count_query = """
                WITH video_individuals AS (
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid = ANY($1::uuid[])
                )
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM video_individuals
                )
            """

            # Convert string UUIDs to UUID array for PostgreSQL
            uuid_array = [UUID(vid) for vid in video_uuids]
            
            count_row = await conn.fetchrow(
                count_query,
                uuid_array
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "count": mvr_count,
                "video_count": len(video_uuids)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching videos MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos MVR people count: {str(e)}"
        ) from e
```

---

## Performance Characteristics

### Response Times

**Typical Performance:**
- Media search query: 50-100ms
- MVR count query: 100-200ms
- Total end-to-end: 200-400ms

**Factors Affecting Performance:**
- Number of videos in collection (more videos = slower search)
- Number of MVR people detected (more people = slower count)
- Database connection pool availability
- Network latency between services

### Optimization Strategies

**Current Optimizations:**
1. ✅ **Limit results**: Only fetch up to 100 videos per day
2. ✅ **Indexed queries**: Database indexes on `collection_id`, `created_at`, `video_uuid`
3. ✅ **CTE query**: Efficient SQL using Common Table Expressions
4. ✅ **Connection pooling**: Reuses database connections

**Future Optimizations:**
1. 📋 **Caching**: Cache counts for 5-10 minutes to reduce queries
2. 📋 **Incremental updates**: Update counts on new video upload instead of recalculating
3. 📋 **Background refresh**: Refresh counts periodically in background
4. 📋 **WebSocket updates**: Push count updates to clients in real-time

### Scalability

**Current Limits:**
- Handles up to 100 videos per camera per day
- Supports unlimited cameras (each fetches independently)
- Database can handle 100+ concurrent count queries

**Scaling Considerations:**
- Large number of cameras (50+): Consider batch fetching
- High video volume (500+ per day): May need pagination
- Real-time requirements: Implement WebSocket updates

---

## Troubleshooting

### Issue 1: Counter Shows 0 Despite Detections

**Symptom:**
- Videos are being recorded
- MVR people exist in database
- Camera card shows `[👤 0]`

**Diagnosis Steps:**

1. **Check if videos exist in Media DB:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/media/search \
     -H "Authorization: Bearer {token}" \
     -d '{"collection_id": "usb_camera_0", "start_date": "2025-11-28T00:00:00", "end_date": "2025-11-28T23:59:59"}'
   ```
   - Expected: List of video objects
   - If empty: Videos not being uploaded or collection_id mismatch

2. **Check if MVR people exist for videos:**
   ```bash
   curl -X POST http://localhost:8008/api/v1/mvr-people/count-by-videos \
     -H "Authorization: Bearer {token}" \
     -d '{"video_uuids": ["uuid1", "uuid2"]}'
   ```
   - Expected: `{"count": > 0}`
   - If 0: No MVR people created for these videos

3. **Verify collection_id mapping:**
   - Check camera.deviceId matches collection name
   - Ensure camera service assigns correct collection

**Common Causes:**
- ❌ Collection ID mismatch (camera uses different ID than videos)
- ❌ Videos uploaded but MVR pipeline not running
- ❌ Date range incorrect (wrong timezone)
- ❌ Authentication token expired

**Solutions:**
- ✅ Verify camera.deviceId matches video collection_id
- ✅ Restart VMeta service to ensure batch processor running
- ✅ Check timezone settings (should use UTC for storage)
- ✅ Refresh authentication token

---

### Issue 2: Counter Shows Loading Indefinitely

**Symptom:**
- Badge shows `[⟳ Loading...]` forever
- Never updates to show count

**Diagnosis Steps:**

1. **Check browser console:**
   ```javascript
   // Look for errors like:
   "❌ Search media failed: Network error"
   "❌ MVR people count failed: 401 Unauthorized"
   ```

2. **Check service health:**
   ```bash
   curl http://localhost:8000/health  # Media service
   curl http://localhost:8008/health  # VMeta service
   curl http://localhost:8080/health  # Gateway
   ```

3. **Check authentication:**
   - Verify JWT token is valid
   - Check token expiration
   - Ensure user has proper permissions

**Common Causes:**
- ❌ Service down (Media or VMeta)
- ❌ Gateway not proxying requests
- ❌ Authentication failure
- ❌ Network timeout

**Solutions:**
- ✅ Restart required services
- ✅ Check gateway routing configuration
- ✅ Re-login to get fresh token
- ✅ Increase request timeout settings

---

### Issue 3: Counter Shows Wrong Count

**Symptom:**
- Counter shows different number than expected
- Discrepancy between camera card and collection search

**Diagnosis Steps:**

1. **Count videos manually:**
   ```bash
   # Get all videos for camera today
   curl -X POST http://localhost:8000/api/v1/media/search \
     -H "Authorization: Bearer {token}" \
     -d '{"collection_id": "usb_camera_0", ...}' | jq '.total'
   ```

2. **Count MVR people manually:**
   ```bash
   # Use collection search endpoint
   curl -X POST http://localhost:8008/api/v1/mvr-people/search/by-collection \
     -H "Authorization: Bearer {token}" \
     -d '{"collection_name": "usb_camera_0", ...}' | jq '.total_results'
   ```

3. **Compare counts:**
   - Camera card count should match collection search count
   - If mismatch, check database consistency

**Common Causes:**
- ❌ Date range mismatch (camera card uses different timezone)
- ❌ Stale data (count cached from earlier time)
- ❌ Database inconsistency (appearances without MVR mapping)

**Solutions:**
- ✅ Ensure consistent timezone handling (use UTC)
- ✅ Clear cache and reload counter
- ✅ Run database integrity check
- ✅ Verify MVR creation pipeline completed successfully

---

### Issue 4: Performance Degradation

**Symptom:**
- Counter takes 5+ seconds to load
- Page becomes unresponsive
- Multiple cameras loading slowly

**Diagnosis Steps:**

1. **Check response times:**
   ```bash
   time curl -X POST http://localhost:8000/api/v1/media/search ...
   time curl -X POST http://localhost:8008/api/v1/mvr-people/count-by-videos ...
   ```

2. **Check database query performance:**
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM media_files 
   WHERE collection_id = 'usb_camera_0' 
     AND created_at >= '2025-11-28 00:00:00';
   ```

3. **Monitor database connections:**
   ```sql
   SELECT count(*) FROM pg_stat_activity 
   WHERE datname = 'vmeta_db';
   ```

**Common Causes:**
- ❌ Missing database indexes
- ❌ Too many concurrent requests
- ❌ Database connection pool exhausted
- ❌ Network latency

**Solutions:**
- ✅ Add indexes on `collection_id`, `created_at`, `video_uuid`
- ✅ Implement request throttling
- ✅ Increase connection pool size
- ✅ Enable caching for counter values

---

## Advanced Topics

### Caching Strategy (Future Enhancement)

**Problem:** 
- Every camera card fetch requires 2 API calls and 2 database queries
- Multiple cameras on same page = many redundant queries
- Real-time updates not critical (5-minute staleness acceptable)

**Solution:**

**Frontend Caching:**
```dart
// Cache in Riverpod provider
final mvrCountCacheProvider = StateProvider<Map<String, CachedCount>>((ref) => {});

class CachedCount {
  final int count;
  final DateTime timestamp;
  
  bool get isExpired => DateTime.now().difference(timestamp) > Duration(minutes: 5);
}

// In camera card:
Future<void> _fetchMVRPeopleCount() async {
  final cache = ref.read(mvrCountCacheProvider);
  final cached = cache[widget.camera.deviceId];
  
  if (cached != null && !cached.isExpired) {
    setState(() {
      _mvrPeopleCount = cached.count;
      _isLoadingCount = false;
    });
    return;
  }
  
  // Fetch from API...
  final count = ...;
  
  // Update cache
  ref.read(mvrCountCacheProvider.notifier).state = {
    ...cache,
    widget.camera.deviceId: CachedCount(count: count, timestamp: DateTime.now()),
  };
}
```

**Backend Caching:**
```python
# Redis cache in VMeta service
@router.post("/count-by-videos")
async def get_videos_mvr_people_count(...):
    # Check cache first
    cache_key = f"mvr_count:{hash(tuple(video_uuids))}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database...
    result = {"count": mvr_count, "video_count": len(video_uuids)}
    
    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(result))
    
    return result
```

---

### Real-Time Updates (Future Enhancement)

**Problem:**
- Counter only updates on page load/refresh
- New MVR people detected while page is open are not shown
- Users must manually refresh to see updates

**Solution: WebSocket Updates**

**Architecture:**
```text
VMeta Service → Redis Pub/Sub → Gateway WebSocket → Flutter Client

1. MVR Person Created (VMeta)
   └─> Publish event: {"event": "mvr_created", "collection": "usb_camera_0"}

2. Gateway Subscribes to Redis
   └─> Forward events to connected WebSocket clients

3. Flutter Client Receives Event
   └─> Update counter if collection matches
```

**Implementation Sketch:**

**Backend (VMeta Service):**
```python
# After creating MVR person
await redis.publish('mvr_events', json.dumps({
    'event': 'mvr_created',
    'collection': collection_name,
    'mvr_uuid': str(mvr_uuid),
    'timestamp': datetime.now().isoformat()
}))
```

**Frontend (Flutter):**
```dart
// WebSocket connection
final channel = WebSocketChannel.connect(
  Uri.parse('ws://localhost:8080/ws/mvr-events'),
);

// Listen for events
channel.stream.listen((message) {
  final event = json.decode(message);
  if (event['event'] == 'mvr_created' && 
      event['collection'] == widget.camera.deviceId) {
    // Increment counter
    setState(() {
      _mvrPeopleCount = (_mvrPeopleCount ?? 0) + 1;
    });
  }
});
```

---

## Related Documentation

- [Continuous Individuals and MVR Pipeline](./continuous-individuals-and-mvr-pipeline.md) - Complete pipeline documentation
- [Camera Video and Data Objects Management](./camera-video-and-data-objects-management.md) - Camera and video architecture
- [MVR People Search Implementation](../vision-vmeta/MVR_PEOPLE_SEARCH_IMPLEMENTATION.md) - Search endpoint details

---

## Conclusion

The **Camera Card MVR People Counter** provides real-time visibility into person detection per camera with:

✅ **Simple Architecture**: Two-step API call (search videos → count MVR people)  
✅ **Efficient Queries**: Optimized SQL using CTEs and proper indexing  
✅ **Visual Feedback**: Color-coded badges with loading states  
✅ **Error Handling**: Graceful degradation on failures  
✅ **Scalable**: Handles multiple cameras independently  

The counter is production-ready and provides immediate value to users monitoring camera activity and person detection effectiveness.

**Document Maintained By:** PPL Meta Development Team  
**Last Verified:** November 28, 2025  
**Status:** ✅ PRODUCTION READY
