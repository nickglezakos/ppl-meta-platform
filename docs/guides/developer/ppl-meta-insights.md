# PPL Meta Platform Insights

This document provides detailed explanations of various features and components within the PPL Meta platform, offering insights into their implementation and functionality.

---

## Counters

### Camera Card MVR People Counter

The counter displayed in each camera card shows the total number of **unique MVR (Machine Vision Representation) people** detected in that camera's videos today.

#### How It Works

**Frontend Implementation** (`camera_card.dart`):

1. **Initialization**: When the card loads, `_fetchMVRPeopleCount()` is automatically called
2. **Step 1 - Get Today's Videos**: Queries Media API to search for all videos in this camera's collection (using `camera.deviceId` as `collectionId`) within today's date range (00:00 to 23:59)
3. **Step 2 - Extract Video UUIDs**: Extracts the list of video UUIDs from the search results
4. **Step 3 - Count MVR People**: Calls VMeta API endpoint `/api/v1/mvr-people/count-by-videos` with these video UUIDs
5. **Display**: Shows the count with a green badge if people are detected, gray badge if zero

**Backend Implementation** (`ppl-meta-vmeta/src/api/routes/mvr_people.py`):

The `/count-by-videos` endpoint executes this SQL query:

```sql
WITH video_individuals AS (
  -- Get all individuals appearing in these videos
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
```

#### Key Characteristics

- **MVR People**: Unique individuals across multiple videos (merged/deduplicated representations)
- **Date Range**: Uses today's date range by default (00:00:00 to 23:59:59)
- **Update Trigger**: Counter updates automatically on card initialization
- **Visual Indicators**:
  - Green badge with person icon (✓) when count > 0
  - Gray badge with person icon (−) when count = 0
  - Loading spinner displayed while fetching data
- **Purpose**: Provides a quick overview of how many unique people were detected by that specific camera today

#### Data Flow

```
Flutter Camera Card
    ↓
Media API: GET /api/v1/media/search
    (collectionId = camera.deviceId, type = video, today's date range)
    ↓
Returns: List of video records with UUIDs
    ↓
Extract: video_uuids = [uuid1, uuid2, uuid3, ...]
    ↓
VMeta API: POST /api/v1/mvr-people/count-by-videos
    (body: { video_uuids: [...] })
    ↓
VMeta Database Query: Count unique MVR people
    ↓
Returns: { count: 12, video_count: 9 }
    ↓
Display: Green badge showing "👤 12"
```

#### Technical Notes

- **Performance**: Efficient query using PostgreSQL CTEs and UUID arrays
- **Microservice Architecture**: Respects service boundaries (Media → VMeta)
- **Authentication**: Requires valid JWT token for API calls
- **Error Handling**: Gracefully handles failures by showing 0 count
- **State Management**: Uses Flutter StatefulWidget with local state for counter value
