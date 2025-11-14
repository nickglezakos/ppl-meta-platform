# Vision Service, Orchestrator & vmeta - API Endpoints Reference

**Date:** October 25, 2025  
**Services:** Vision Service (port 8003), Orchestrator Service (port 8002), vmeta Service (port 8008)  
**Purpose:** Complete reference for person detection, face detection, person objects workflows, and cross-video individual tracking

---

## Overview

The PPL Meta platform provides three main approaches for person/face detection and tracking:

1. **Cross-Video Individual Tracking** (vmeta) - Track individuals across multiple videos with caching
2. **Person Objects Workflow** (Recommended) - Session-based, grouping, tracking within single videos
3. **Legacy Face Detection** - Direct face detection without person grouping

## Service Architecture

```plaintext
┌─────────────────┐
│   Gateway       │  Port 8080 - Routes to services
│   (Proxy)       │
└────────┬────────┘
         │
    ┌────┴────┬─────────┐
    │         │         │
┌───▼──┐  ┌──▼────────┐  ┌──▼────┐
│Vision│  │Orchestrator│  │ vmeta │
│8003  │  │   8002     │  │ 8008  │
└──────┘  └────────────┘  └───────┘
```

---

## 1. Cross-Video Individual Tracking API (vmeta Service)

### Base Path
- **vmeta Service**: `http://localhost:8008/api/v1/cross-video/individuals`
- **Gateway**: `http://localhost:8080/api/v1/vmeta/cross-video/individuals`

### 1.1 Create Tracking Session

**Endpoint**: `/tracking/sessions`

**Description**: Create a cross-video individual tracking session. This endpoint:
- Discovers videos within specified time range and collections
- Groups person objects across multiple videos using IoU-based matching
- Creates individual entities that persist across videos
- Caches results to avoid reprocessing identical requests
- Returns cached session if same parameters were used before

**Service**: vmeta only
- ✅ **vmeta**: `http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions`

**Method**: POST

**Authentication**: Bearer token required

**Request Body**:
```json
{
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "background_processing": true,
  "algorithm_config": {
    "max_gap_seconds": 10,
    "iou_threshold": 0.3,
    "min_overlap_confidence": 0.5
  }
}
```

**Parameters**:
- `collections` (array, required): List of collection names to search
- `start_time` (ISO 8601, required): Start of time window
- `end_time` (ISO 8601, required): End of time window
- `background_processing` (boolean, optional): Process asynchronously (default: true)
- `algorithm_config` (object, optional): Tracking algorithm configuration
  - `max_gap_seconds` (number): Maximum time gap between videos for same individual
  - `iou_threshold` (number): Intersection over Union threshold for matching
  - `min_overlap_confidence` (number): Minimum confidence for overlap matching

**Request Example**:
```bash
TOKEN=$(cat /tmp/token.txt)
curl -X POST "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-19T13:05:00Z",
    "end_time": "2025-10-19T13:14:00Z",
    "background_processing": true,
    "algorithm_config": {
      "max_gap_seconds": 10,
      "iou_threshold": 0.3,
      "min_overlap_confidence": 0.5
    }
  }'
```

**Response** (New Session Created):
```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "processing",
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "created_at": "2025-10-25T18:25:01.237726",
  "message": "Session created and processing started"
}
```

**Response** (Cached Session Found):
```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "completed",
  "message": "Cached session found",
  "cache_hit_rate": 1.0,
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "created_at": "2025-10-25T18:25:01.237726",
  "completed_at": "2025-10-25T18:25:01.304325"
}
```

**Features**:
- ✅ Smart caching using MD5 hash of (config + collections + time range)
- ✅ Returns existing session instantly if already processed
- ✅ Authenticated video discovery via Gateway/Media service
- ✅ Background processing for long-running operations
- ✅ Automatic person object grouping across videos
- ✅ Database persistence of individuals and appearances

---

### 1.2 Get Tracking Session Status

**Endpoint**: `/tracking/sessions/{session_uuid}`

**Description**: Retrieve status and results of a tracking session.

**Service**: vmeta only
- ✅ **vmeta**: `http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}`

**Method**: GET

**Authentication**: Bearer token required

**Request Example**:
```bash
TOKEN=$(cat /tmp/token.txt)
SESSION_UUID="221e0bc4-af11-49a9-af39-1705cce4aa50"
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID"
```

**Response** (Processing):
```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "processing",
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "total_videos": 0,
  "processed_videos": 0,
  "created_at": "2025-10-25T18:25:01.237726"
}
```

**Response** (Completed):
```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "completed",
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,
  "created_at": "2025-10-25T18:25:01.237726",
  "completed_at": "2025-10-25T18:25:01.304325"
}
```

**Status Values**:
- `pending`: Session created, not yet started
- `processing`: Currently processing videos
- `completed`: Successfully completed
- `failed`: Processing failed
- `cancelled`: Session was cancelled

---

### 1.3 Get Individuals from Session

**Endpoint**: `/tracking/sessions/{session_uuid}/individuals`

**Description**: Retrieve all individuals discovered in a tracking session with their video appearances.

**Service**: vmeta only
- ✅ **vmeta**: `http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals`

**Method**: GET

**Authentication**: Bearer token required

**Response**:
```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "total_individuals": 1,
  "individuals": [
    {
      "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
      "individual_id": "ind_5c73fd34",
      "confidence_score": 0.85,
      "total_appearances": 2,
      "total_videos": 2,
      "first_seen": "2025-10-19T13:05:00Z",
      "last_seen": "2025-10-19T13:14:30Z",
      "video_appearances": [
        {
          "video_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
          "start_timestamp": "2025-10-19T13:05:00Z",
          "end_timestamp": "2025-10-19T13:05:30Z",
          "confidence": 0.85,
          "appearance_count": 1
        },
        {
          "video_uuid": "38f80c41-e0af-41fc-882d-f7ff79abd43d",
          "start_timestamp": "2025-10-19T13:14:00Z",
          "end_timestamp": "2025-10-19T13:14:30Z",
          "confidence": 0.85,
          "appearance_count": 1
        }
      ]
    }
  ]
}
```

---

### 1.4 Database Schema

The vmeta service uses three main tables for cross-video tracking:

**tracking_sessions table**:
- `session_uuid` (UUID, PK): Unique session identifier
- `status` (VARCHAR): processing, completed, failed, cancelled
- `collections` (JSONB): Array of collection names searched
- `start_time` (TIMESTAMP): Time window start
- `end_time` (TIMESTAMP): Time window end
- `total_videos` (INTEGER): Total videos found
- `processed_videos` (INTEGER): Videos processed so far
- `individuals_found` (INTEGER): Number of individuals tracked
- `config_hash` (VARCHAR): MD5 hash for caching
- `created_at` (TIMESTAMP): Session creation time
- `completed_at` (TIMESTAMP): Session completion time

**individuals table**:
- `individual_uuid` (UUID, PK): Unique individual identifier
- `individual_id` (VARCHAR): Human-readable ID (e.g., "ind_5c73fd34")
- `session_uuid` (UUID, FK): Reference to tracking session
- `confidence_score` (FLOAT): Overall tracking confidence
- `spatial_signature` (JSONB): Spatial features for matching
- `temporal_signature` (JSONB): Temporal features for matching
- `total_appearances` (INTEGER): Total appearance records
- `total_videos` (INTEGER): Number of videos individual appears in
- `first_seen` (TIMESTAMP): First appearance timestamp
- `last_seen` (TIMESTAMP): Last appearance timestamp
- `created_by_session` (UUID): Original session that created this individual

**individual_video_appearances table**:
- `appearance_uuid` (UUID, PK): Unique appearance identifier
- `individual_uuid` (UUID, FK): Reference to individual
- `video_uuid` (UUID): Video identifier
- `start_timestamp` (TIMESTAMP): Appearance start time
- `end_timestamp` (TIMESTAMP): Appearance end time
- `confidence` (FLOAT): Confidence for this appearance
- `appearance_count` (INTEGER): Number of detections in video
- `metadata` (JSONB): Additional appearance data

---

## 2. Person Objects API (Vision Service)

### Base Path
- **Vision Service**: `http://localhost:8003/api/v1/person-objects`
- **Orchestrator**: `http://localhost:8002/person-objects`
- **Gateway**: `http://localhost:8080/api/v1/person-objects`

### 1.1 GET Person Objects for Media

**Endpoint**: `/person-objects/{media_id}`

**Description**: Retrieve person objects for a specific media UUID. This endpoint:
- Checks if person objects exist
- Returns summary with person count and face count
- Indicates processing status

**Services**:
- ✅ **Orchestrator**: `http://localhost:8002/person-objects/{media_id}`
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/{media_id}`

**Method**: GET

**Authentication**: Bearer token required

**Request**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8002/person-objects/7b462847-cd1f-441a-8bd9-aaed6643b7cb"
```

**Response** (Success - Person Objects Exist):
```json
{
  "success": true,
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "total_persons": 3,
  "total_faces": 45,
  "status": "completed",
  "message": "Found 3 persons"
}
```

**Response** (No Person Objects Yet):
```json
{
  "success": false,
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "total_persons": 0,
  "total_faces": 0,
  "status": "pending",
  "message": "Face detection complete, person processing pending"
}
```

**Response** (No Face Data):
```json
{
  "success": false,
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "total_persons": 0,
  "total_faces": 0,
  "status": "no_faces",
  "message": "No face detection data found"
}
```

---

### 1.2 Trigger Person Objects Workflow

**Endpoint**: `/person-objects/workflow/trigger`

**Description**: **V2 Endpoint** - Automatically triggers person objects detection:
1. Checks if face detection data exists
2. If exists but no person objects → runs PPL Thread workflow
3. If person objects exist → returns cached results
4. If no face data → runs face detection first, then person objects

**Service**: Vision Service only
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/workflow/trigger`

**Method**: POST

**Authentication**: Bearer token required

**Request Body**:
```json
{
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb"
}
```

**Request Example**:
```bash
curl -X POST "http://localhost:8003/api/v1/person-objects/workflow/trigger" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb"}'
```

**Response**:
```json
{
  "success": true,
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "total_persons": 3,
  "total_faces": 45,
  "status": "completed",
  "message": "Person objects workflow completed",
  "group_tracking": [...],
  "processing_time_ms": 1234.56
}
```

**Features**:
- ✅ Checks for existing person objects first
- ✅ Only runs processing if needed
- ✅ Returns cached results if available
- ✅ Handles both face detection and person grouping

---

### 1.3 Start Person Objects Workflow (Manual)

**Endpoint**: `/person-objects/workflows/start`

**Description**: Manually start person objects workflow for an existing face detection session.

**Service**: Vision Service only
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/workflows/start`

**Method**: POST

**Request Body**:
```json
{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "iou_threshold": 0.3,
  "min_overlap_confidence": 0.5
}
```

---

### 1.4 Get Person Objects by Session

**Endpoint**: `/person-objects/sessions/{session_uuid}`

**Description**: Retrieve detailed person objects data for a face detection session.

**Services**:
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/sessions/{session_uuid}`

**Method**: GET

**Parameters**:
- `include_quality_analysis` (query, optional): Include best face quality data (default: true)

**Response**:
```json
{
  "success": true,
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "total_persons": 3,
  "total_faces": 45,
  "group_tracking": [
    {
      "person_uuid": "uuid-1",
      "person_id": "person_1",
      "face_count": 15,
      "representative_faces": [...],
      "all_face_ids": [...],
      "average_confidence": 0.85,
      "quality_metrics": {...}
    }
  ],
  "status": "completed"
}
```

---

### 1.5 Find Session by Media UUID

**Endpoint**: `/person-objects/media/{media_uuid}/session`

**Description**: Look up which face detection session UUID corresponds to a media UUID.

**Services**:
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/media/{media_uuid}/session`
- ✅ **Gateway**: `http://localhost:8080/api/v1/person-objects/media/{media_uuid}/session`

**Method**: GET

**Response** (Success):
```json
{
  "success": true,
  "media_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "session_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Found session 550e... for media 7b46..."
}
```

**Response** (Not Found):
```json
{
  "detail": "No session found for media UUID 7b462847-cd1f-441a-8bd9-aaed6643b7cb"
}
```

---

### 1.6 Get Session Statistics

**Endpoint**: `/person-objects/sessions/{session_uuid}/statistics`

**Description**: Get statistical summary of person objects for a session.

**Service**: Vision Service only
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/sessions/{session_uuid}/statistics`

**Method**: GET

---

### 1.7 Get Workflow Status

**Endpoint**: `/person-objects/workflows/{workflow_id}/status`

**Description**: Check status of a running person objects workflow.

**Service**: Vision Service only
- ✅ **Vision**: `http://localhost:8003/api/v1/person-objects/workflows/{workflow_id}/status`

**Method**: GET

---

## 2. Face Detection API (Legacy)

### Base Path
- **Vision Service**: `http://localhost:8003/api/v1/face-detection`
- **Gateway**: `http://localhost:8080/api/v1/vision`

### 2.1 Detect Faces (Legacy - Not Recommended)

**Endpoint**: `/face-detection/detect`

**Description**: Direct face detection without session management or person grouping.

**Service**: Vision Service only
- ⚠️ **Vision**: `http://localhost:8003/api/v1/face-detection/detect`

**Method**: POST

**Request**:
```json
{
  "media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
  "method": "dlib",
  "confidence_threshold": 0.5
}
```

**Note**: This is the OLD approach. Use person objects workflow instead.

---

### 2.2 Get Face Detection Results

**Endpoint**: `/face-detection/results/{media_id}`

**Description**: Get raw face detection results (faces only, no person grouping).

**Services**:
- ⚠️ **Vision**: `http://localhost:8003/api/v1/face-detection/results/{media_id}`
- ⚠️ **Gateway**: `http://localhost:8080/api/v1/vision/face-detection/results/{media_id}`

**Method**: GET

---

## 3. Orchestrator Enhanced Endpoints

### 3.1 Enhanced Person Objects V2

**Endpoint**: `/api/v1/media/{media_id}/faces/enhanced-v2`

**Description**: Orchestrator's enhanced endpoint that combines face detection and person grouping.

**Service**: Orchestrator only
- ✅ **Orchestrator**: `http://localhost:8002/api/v1/media/{media_id}/faces/enhanced-v2`

**Method**: GET

**Features**:
- Session-based workflow management
- Distance calculations
- Quality scoring
- Route tracking

---

## 4. Cross-Service Integration Flow

### Recommended Workflow: Get Person Objects

```
1. Check if person objects exist:
   GET /person-objects/{media_id}
   
   If success=true → Done, use the data
   If success=false, status="pending" → Continue to step 2
   If success=false, status="no_faces" → Need face detection first

2. Trigger person objects workflow (V2):
   POST /person-objects/workflow/trigger
   Body: {"media_id": "uuid"}
   
   This will:
   - Check for face data
   - Run face detection if needed
   - Process person objects
   - Return results

3. If needed, get detailed data:
   GET /person-objects/sessions/{session_uuid}
```

### Alternative: Find Session First

```
1. Find session UUID for media:
   GET /person-objects/media/{media_uuid}/session
   
2. Get person objects for session:
   GET /person-objects/sessions/{session_uuid}
```

---

## 5. Service-Specific Endpoints Summary

### vmeta Service (Port 8008)

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/cross-video/individuals/tracking/sessions` | POST | Create cross-video tracking session |
| `/api/v1/cross-video/individuals/tracking/sessions/{uuid}` | GET | Get tracking session status |
| `/api/v1/cross-video/individuals/tracking/sessions/{uuid}/individuals` | GET | Get individuals from session |

### Orchestrator (Port 8002)

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/person-objects/{media_id}` | GET | Get person objects summary for media |
| `/api/v1/media/{media_id}/faces/enhanced-v2` | GET | Enhanced person objects with quality scoring |

### Vision Service (Port 8003)

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/person-objects/{media_id}` | GET | Get person objects summary |
| `/api/v1/person-objects/workflow/trigger` | POST | **V2 Auto-trigger** with face detection check |
| `/api/v1/person-objects/workflows/start` | POST | Manual workflow start |
| `/api/v1/person-objects/sessions/{uuid}` | GET | Get person objects by session |
| `/api/v1/person-objects/media/{uuid}/session` | GET | Find session for media |
| `/api/v1/person-objects/sessions/{uuid}/statistics` | GET | Get statistics |
| `/api/v1/person-objects/workflows/{id}/status` | GET | Workflow status |

### Gateway (Port 8080)

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/api/v1/person-objects/*` | ALL | Proxy to Vision Service |
| `/api/v1/vmeta/*` | ALL | Proxy to vmeta Service |

---

## 6. Testing Examples

### Test 1: Cross-Video Individual Tracking

```bash
# Get authentication token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')

# Create tracking session
curl -X POST "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-19T13:05:00Z",
    "end_time": "2025-10-19T13:14:00Z",
    "background_processing": true,
    "algorithm_config": {
      "max_gap_seconds": 10,
      "iou_threshold": 0.3,
      "min_overlap_confidence": 0.5
    }
  }' | jq

# Check session status
SESSION_UUID="<uuid-from-response>"
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID" | jq

# Get individuals
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID/individuals" | jq
```

### Test 2: Simple Person Objects Check

```bash
# Check for person objects (Orchestrator)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8002/person-objects/7b462847-cd1f-441a-8bd9-aaed6643b7cb" | jq
```

### Test 3: Trigger Person Objects Workflow (V2)

```bash
# Trigger workflow (checks for faces, runs if needed)
curl -X POST "http://localhost:8003/api/v1/person-objects/workflow/trigger" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"media_id": "7b462847-cd1f-441a-8bd9-aaed6643b7cb"}' | jq
```

### Test 4: Find Session for Media

```bash
# Find which session belongs to this media
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8003/api/v1/person-objects/media/7b462847-cd1f-441a-8bd9-aaed6643b7cb/session" | jq
```

### Test 4: Get Detailed Person Objects

```bash
# Get session UUID from previous test, then:
SESSION_UUID="550e8400-e29b-41d4-a716-446655440000"

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8003/api/v1/person-objects/sessions/$SESSION_UUID" | jq
```

---

## 7. Error Responses

### 404 Not Found
```json
{
  "detail": "No person objects found for session"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "media_id"],
      "msg": "Field required"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to retrieve person objects: Database connection error"
}
```

---

## 8. Best Practices

### ✅ DO

- **Cross-Video Tracking**: Use vmeta service for tracking individuals across multiple videos
- **Person Objects**: Use `POST /person-objects/workflow/trigger` for automatic processing (V2)
- **Simple Checks**: Use Orchestrator endpoint `/person-objects/{media_id}` for quick status checks
- **Authentication**: Always use bearer token authentication for all requests
- **Response Validation**: Always check response `success` field before using data
- **Caching**: Leverage vmeta caching - identical requests return cached results instantly
- **Background Processing**: Set `background_processing: true` for long-running operations

### ❌ DON'T

- **Legacy Endpoints**: Don't use legacy `/face-detection/detect` endpoint
- **Manual Workflows**: Don't call face detection manually - use workflow trigger instead
- **Authentication**: Don't skip authentication - all endpoints require valid tokens
- **Assumptions**: Don't assume person objects exist - always check first
- **Cache Invalidation**: Don't create slightly different requests expecting same cache - hash is precise
- **Polling**: Don't poll too frequently - background tasks complete within seconds

### 🔧 VMETA SPECIFIC

- **Time Ranges**: Use precise time ranges to avoid discovering too many videos
- **Collections**: Specify exact collections to narrow search scope
- **Algorithm Config**: Tune `iou_threshold` (0.3) and `min_overlap_confidence` (0.5) based on use case
- **Session Reuse**: Check for existing sessions before creating new ones - leverage caching
- **Token Lifetime**: Ensure authentication token is valid for duration of background processing

---

## 9. Troubleshooting

### Cross-Video Tracking Issues

**Problem: "Session returns 0 videos found"**

**Solution**: Check time range and collection names. Videos must exist in that exact timeframe.

**Problem: "Session status stuck at 'processing'"**

**Solution**: Check background task logs. Common causes:
- Invalid authentication token
- No person objects in videos (run person detection first)
- Database connection issues

**Problem: "Cache not working - new session created every time"**

**Solution**: Ensure EXACT same parameters:
- Same collections array (same order)
- Same start_time and end_time (ISO 8601 format)
- Same algorithm_config values

**Problem: "0 individuals found but videos were processed"**

**Solution**:
- Videos may not contain person objects - check person detection results
- IoU threshold may be too strict - try lowering from 0.3 to 0.2
- Videos may be too far apart in time - increase max_gap_seconds

### Person Objects Issues

**Problem: "No person objects found"**

**Solution**: Run the workflow trigger endpoint to process the media

**Problem: "No session found for media UUID"**

**Solution**: Face detection hasn't been run yet. Use workflow trigger.

**Problem: 404 on direct media lookup**

**Solution**: Use the correct service (Orchestrator vs Vision)

**Problem: Person objects incomplete**

**Solution**: Check if face detection completed first

### Authentication Issues

**Problem: 401 Unauthorized**

**Solution**: Refresh authentication token - tokens expire after set duration

**Problem: "Failed to discover videos"**

**Solution**: Ensure Bearer token is properly formatted in Authorization header

---

## 10. Quick Reference Card

**Want to track individuals across multiple videos?**

```bash
# Create cross-video tracking session (vmeta)
POST http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions
Body: {
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "background_processing": true,
  "algorithm_config": {
    "max_gap_seconds": 10,
    "iou_threshold": 0.3,
    "min_overlap_confidence": 0.5
  }
}

# Get session status
GET http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}

# Get individuals found
GET http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals
```

**Want person objects for a video?**

```bash
# Option 1: Simple check (Orchestrator)
GET http://localhost:8002/person-objects/{media_id}

# Option 2: Auto-process if needed (Vision V2)
POST http://localhost:8003/api/v1/person-objects/workflow/trigger
Body: {"media_id": "{media_id}"}
```

**Want detailed person groups?**

```bash
# Step 1: Find session
GET /api/v1/person-objects/media/{media_id}/session

# Step 2: Get details
GET /api/v1/person-objects/sessions/{session_uuid}
```

**Want to verify system is working?**

```bash
# Health check
GET http://localhost:8003/api/v1/person-objects/health
```

---

## Appendix A: Cross-Video Individual Tracking - Complete Example

### Context

This example demonstrates successful cross-video individual tracking using the vmeta service. The test tracked a person across two consecutive videos from the "usb_camera_0" collection.

**Test Environment:**
- Collection: `usb_camera_0` (UUID: 76241fb0-fc86-4859-b442-f7f2979a5c53)
- Time Range: 2025-10-19 13:05:00 to 13:14:00 (9-minute window)
- Videos Found: 2 consecutive videos
  - Video 1: `7b462847-cd1f-441a-8bd9-aaed6643b7cb` (13:05:00-13:05:30, 1 person, 11 faces)
  - Video 2: `38f80c41-e0af-41fc-882d-f7ff79abd43d` (13:14:00-13:14:30, 1 person, 35 faces)
- Expected Result: 1 individual tracked across both videos

### Step 1: Authentication

```bash
# Get authentication token from node service
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')

# Store token for reuse
echo "$TOKEN" > /tmp/token.txt
```

### Step 2: Create Cross-Video Tracking Session

```bash
# Create tracking session with specific time window and algorithm config
TOKEN=$(cat /tmp/token.txt)

curl -X POST "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-19T13:05:00Z",
    "end_time": "2025-10-19T13:14:00Z",
    "background_processing": true,
    "algorithm_config": {
      "max_gap_seconds": 10,
      "iou_threshold": 0.3,
      "min_overlap_confidence": 0.5
    }
  }'
```

**Response:**

```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "processing",
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "created_at": "2025-10-25T18:25:01.237726",
  "message": "Session created and processing started"
}
```

### Step 3: Check Session Status

```bash
# Poll session status until completed
SESSION_UUID="221e0bc4-af11-49a9-af39-1705cce4aa50"

curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID" | \
  jq
```

**Response (Completed):**

```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "completed",
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,
  "created_at": "2025-10-25T18:25:01.237726",
  "completed_at": "2025-10-25T18:25:01.304325"
}
```

**Key Metrics:**
- Processing time: 67ms (completed_at - created_at)
- Videos found: 2
- Videos processed: 2
- Individuals tracked: 1

### Step 4: Retrieve Individual Data

```bash
# Get detailed individual and appearance data
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID/individuals" | \
  jq
```

**Response:**

```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "total_individuals": 1,
  "individuals": [
    {
      "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
      "individual_id": "ind_5c73fd34",
      "confidence_score": 0.85,
      "total_appearances": 2,
      "total_videos": 2,
      "first_seen": "2025-10-19T13:05:00Z",
      "last_seen": "2025-10-19T13:14:30Z",
      "video_appearances": [
        {
          "video_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
          "start_timestamp": "2025-10-19T13:05:00Z",
          "end_timestamp": "2025-10-19T13:05:30Z",
          "confidence": 0.85,
          "appearance_count": 1
        },
        {
          "video_uuid": "38f80c41-e0af-41fc-882d-f7ff79abd43d",
          "start_timestamp": "2025-10-19T13:14:00Z",
          "end_timestamp": "2025-10-19T13:14:30Z",
          "confidence": 0.85,
          "appearance_count": 1
        }
      ]
    }
  ]
}
```

### Step 5: Test Caching

```bash
# Create identical request to test caching
curl -X POST -s -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-10-19T13:05:00Z",
    "end_time": "2025-10-19T13:14:00Z",
    "background_processing": true,
    "algorithm_config": {
      "max_gap_seconds": 10,
      "iou_threshold": 0.3,
      "min_overlap_confidence": 0.5
    }
  }' \
  "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" | jq
```

**Response (Cached):**

```json
{
  "session_uuid": "221e0bc4-af11-49a9-af39-1705cce4aa50",
  "status": "completed",
  "message": "Cached session found",
  "cache_hit_rate": 1.0,
  "total_videos": 2,
  "processed_videos": 2,
  "individuals_found": 1,
  "collections": ["usb_camera_0"],
  "start_time": "2025-10-19T13:05:00Z",
  "end_time": "2025-10-19T13:14:00Z",
  "created_at": "2025-10-25T18:25:01.237726",
  "completed_at": "2025-10-25T18:25:01.304325"
}
```

**Cache Benefits:**
- Instant response (no reprocessing)
- Same session UUID returned
- `cache_hit_rate: 1.0` indicates perfect cache hit
- All results preserved from original session

### Step 6: Database Verification

```bash
# Verify individual record in database
psql -U postgres -d ppl_meta -c "
  SELECT 
    individual_uuid,
    individual_id,
    confidence_score,
    total_appearances,
    total_videos,
    first_seen,
    last_seen
  FROM individuals
  WHERE individual_uuid = '5c73fd34-737a-48c7-a69a-f17b40adbead';
"
```

**Database Result:**

```
individual_uuid                  | individual_id | confidence_score | total_appearances | total_videos | first_seen          | last_seen
---------------------------------+---------------+------------------+-------------------+--------------+---------------------+---------------------
5c73fd34-737a-48c7-a69a-f17b40a... | ind_5c73fd34 |             0.85 |                 2 |            2 | 2025-10-19 13:05:00 | 2025-10-19 13:14:30
```

```bash
# Verify video appearances
psql -U postgres -d ppl_meta -c "
  SELECT 
    video_uuid,
    start_timestamp,
    end_timestamp,
    confidence,
    appearance_count
  FROM individual_video_appearances
  WHERE individual_uuid = '5c73fd34-737a-48c7-a69a-f17b40adbead'
  ORDER BY start_timestamp;
"
```

**Database Result:**

```
video_uuid                          | start_timestamp     | end_timestamp       | confidence | appearance_count
------------------------------------+---------------------+---------------------+------------+------------------
7b462847-cd1f-441a-8bd9-aaed6643... | 2025-10-19 13:05:00 | 2025-10-19 13:05:30 |       0.85 |                1
38f80c41-e0af-41fc-882d-f7ff79ab... | 2025-10-19 13:14:00 | 2025-10-19 13:14:30 |       0.85 |                1
```

### Test Results Summary

✅ **Video Discovery**: Successfully found 2 videos in time range  
✅ **Person Grouping**: Grouped person objects across videos into 1 individual  
✅ **Appearance Tracking**: Created 2 video appearance records  
✅ **Database Persistence**: All data properly stored with correct schema  
✅ **Caching**: Identical request returned cached session instantly  
✅ **Authentication**: Bearer token properly propagated through entire chain  

### Key Implementation Details

**Video Discovery Flow:**
1. vmeta endpoint receives authenticated request
2. Extracts Authorization header from request
3. Passes token to background processing task
4. Background task calls `discover_videos_in_collection` with token
5. Function makes authenticated GET to Gateway media search
6. Returns 2 videos matching time range and collection

**Individual Creation Flow:**
1. Process person objects from both videos
2. Group persons using IoU threshold (0.3) and confidence (0.5)
3. Generate unique individual UUID and ID (e.g., "ind_5c73fd34")
4. Create individual record with JSONB signatures
5. Create video appearance records for each video
6. Database triggers update total_appearances and total_videos

**Caching Flow:**
1. Compute MD5 hash of: algorithm_config + collections + start_time + end_time
2. Query database for existing completed session with same hash
3. If found, return cached session with cache_hit_rate=1.0
4. If not found, create new session and process videos

### Technical Achievements

1. **Authentication Chain**: Fixed token passing through 4 layers (endpoint → background task → discovery function → Gateway API)
2. **Database Schema**: Aligned all column types (JSONB, TIMESTAMP, FLOAT) and names (confidence vs confidence_score)
3. **Unique Constraints**: Individual IDs using UUID prefix prevents collisions
4. **Error Handling**: Comprehensive try-catch with database logging via failed_videos array
5. **Background Processing**: Asynchronous execution with status polling
6. **Smart Caching**: MD5 hash-based deduplication prevents reprocessing

### Performance Metrics

- **Session Creation**: ~67ms total (including video discovery and processing)
- **Video Discovery**: Found 2 videos via authenticated media search
- **Individual Processing**: 1 individual created with 2 appearances
- **Cache Lookup**: Instant response (< 10ms) for duplicate requests
- **Database Writes**: 3 records total (1 session, 1 individual, 2 appearances)

---

**Document Version:** 2.0  
**Last Updated:** October 25, 2025  
**Maintained by:** PPL Meta Platform Team
