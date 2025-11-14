# PPL Meta vmeta Service - API Documentation
**Version:** 1.0.0  
**Description:** Vector-based facial embeddings and person detection analytics  
**Date:** October 23, 2025

## Overview
The vmeta service provides advanced facial recognition, person tracking, and analytics capabilities through a RESTful API. It supports cross-video individual tracking, facial embedding generation, and spatial analytics.

## Base URL
```
http://localhost:8008
```

## API Endpoints

### Health & Monitoring

#### GET /health
**Purpose:** Service health check endpoint  
**Tags:** health  
**Description:** Returns service health status and operational metrics  
**Response:** JSON object containing service health information  

#### GET /metrics  
**Purpose:** Service performance metrics  
**Tags:** health  
**Description:** Returns detailed service performance and usage metrics  
**Response:** JSON object with performance data  

---

### Cross-Video Individual Tracking

#### POST /api/v1/cross-video/individuals/tracking/sessions
**Purpose:** Create new cross-video individual tracking session  
**Tags:** cross-video-tracking, Cross-Video Individual Tracking  
**Description:** Creates a new session to track individuals across multiple videos in specified collections and time ranges  

**Request Body:** `CreateTrackingSessionRequest`
```json
{
  "collections": ["string"],           // 1-10 collection names
  "start_time": "2025-10-19T10:00:00Z", // ISO datetime
  "end_time": "2025-10-19T10:30:00Z",   // ISO datetime  
  "algorithm_config": {                 // Optional algorithm parameters
    "config_name": "string",
    "max_gap_seconds": 30,
    "min_sequence_length": 2,
    "iou_threshold": 0.3
  },
  "background_processing": true,        // Default: true
  "force_reprocess": false,            // Default: false
  "description": "string"              // Optional description
}
```

**Response:** `TrackingSessionResponse`
```json
{
  "session_uuid": "string",     // Unique session identifier
  "status": "string",           // Session status (initialized, running, completed, failed)
  "message": "string",          // Status message
  "cache_hit_rate": 0.0,       // Cache utilization percentage
  "total_videos": 0             // Number of videos to process
}
```

#### GET /api/v1/cross-video/individuals/tracking/sessions/{session_uuid}
**Purpose:** Get tracking session status and progress  
**Tags:** cross-video-tracking, Cross-Video Individual Tracking  
**Description:** Retrieves real-time status, progress, and results of a tracking session  

**Parameters:**
- `session_uuid` (path, required): Session identifier string

**Response:**
```json
{
  "session_uuid": "string",
  "status": "string",           // initialized, running, completed, failed
  "collections": ["string"],    // Collections being processed
  "created_at": "datetime",     // Session creation time
  "started_at": "datetime",     // Processing start time
  "completed_at": "datetime",   // Processing completion time  
  "total_videos": 0,           // Total videos in scope
  "processed_videos": 0,       // Videos processed so far
  "individuals_found": 0,      // Number of unique individuals detected
  "cache_hits": 0             // Number of cache hits during processing
}
```

#### GET /api/v1/cross-video/individuals/tracking/cache/status
**Purpose:** Get cache status and statistics  
**Tags:** cross-video-tracking, Cross-Video Individual Tracking  
**Description:** Returns comprehensive cache performance metrics and storage information  

**Response:**
```json
{
  "total_sessions": 0,         // Number of tracking sessions
  "total_individuals": 0,      // Number of individuals in database
  "total_cached_objects": 0,   // Number of cached person objects
  "status": "operational"      // Cache operational status
}
```

#### GET /api/v1/cross-video/individuals/{individual_uuid}/appearances
**Purpose:** Get all appearances of a specific individual across videos  
**Tags:** cross-video-tracking, Cross-Video Individual Tracking  
**Description:** Returns detailed information about when and where an individual appeared in each video, including timestamps and spatial data  

**Parameters:**
- `individual_uuid` (path, required): Individual identifier string

**Response:** `IndividualAppearancesResponse`
```json
{
  "individual_uuid": "string",          // Individual identifier
  "individual_id": "string",            // Human-readable identifier (e.g., "person_2_videos")
  "total_appearances": 0,               // Number of video appearances
  "total_videos": 0,                    // Number of unique videos
  "appearances": [                      // Array of appearance objects
    {
      "individual_uuid": "string",      // Individual identifier
      "video_uuid": "string",           // Video where individual appeared
      "person_object_uuid": "string",   // Person object that was detected
      "start_timestamp": "datetime",    // When individual first appeared in video
      "end_timestamp": "datetime",      // When individual last appeared in video
      "entry_bbox": [x1, y1, x2, y2],  // First face rectangle coordinates (optional)
      "exit_bbox": [x1, y1, x2, y2],   // Last face rectangle coordinates (optional)
      "confidence_score": 0.85          // Confidence of this appearance match
    }
  ]
}
```

---

### Workflow Management

#### POST /api/v1/workflows/execute
**Purpose:** Execute enhanced person detection workflow  
**Tags:** workflows  
**Description:** Executes person detection and analysis workflows with configurable parameters  

**Request Body:** Generic workflow data object
**Response:** Workflow execution results

#### GET /api/v1/workflows/status/{session_uuid}
**Purpose:** Get workflow execution status  
**Tags:** workflows  
**Description:** Retrieves status and progress of a running workflow  

**Parameters:**
- `session_uuid` (path, required): Workflow session identifier

#### GET /api/v1/workflows/sessions/active
**Purpose:** Get all active workflow sessions  
**Tags:** workflows  
**Description:** Returns list of currently active/running workflow sessions  

---

### Facial Embeddings

#### POST /api/v1/embeddings/generate
**Purpose:** Generate facial embeddings for face images  
**Tags:** embeddings  
**Description:** Creates vector embeddings from facial images for similarity comparison and recognition  

**Request Body:** Embedding generation parameters
**Response:** Generated facial embedding vectors

#### POST /api/v1/embeddings/search
**Purpose:** Search for similar faces using vector similarity  
**Tags:** embeddings  
**Description:** Performs vector similarity search to find faces similar to a given embedding  

**Request Body:** Vector search parameters  
**Response:** Similar faces results with similarity scores

---

### Analytics

#### POST /api/v1/analytics/person-routes
**Purpose:** Analyze person movement routes and patterns  
**Tags:** analytics  
**Description:** Computes movement analytics, routes, and behavioral patterns from person tracking data  

**Request Body:** Analytics computation parameters
**Response:** Movement analytics and route data

#### GET /api/v1/analytics/heatmap
**Purpose:** Generate spatial heatmap for person detection  
**Tags:** analytics  
**Description:** Creates spatial heatmaps showing person detection density and movement patterns  

**Parameters:**
- `session_uuid` (query, optional): Filter heatmap by specific session

**Response:** Heatmap data and visualization information

---

## Usage Examples

### Basic Cross-Video Tracking Workflow

1. **Create Session:**
```bash
curl -X POST "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collections": ["usb camera 0"],
    "start_time": "2025-10-19T10:09:00Z",
    "end_time": "2025-10-19T10:20:00Z",
    "background_processing": true
  }'
```

2. **Check Status:**
```bash
curl -X GET "http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/$SESSION_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

3. **Check Cache:**
```bash
curl -X GET "http://localhost:8008/api/v1/cross-video/individuals/tracking/cache/status" \
  -H "Authorization: Bearer $TOKEN"
```

4. **Get Individual Appearances:**
```bash
curl -X GET "http://localhost:8008/api/v1/cross-video/individuals/$INDIVIDUAL_UUID/appearances" \
  -H "Authorization: Bearer $TOKEN"
```

## Authentication
All API endpoints require JWT Bearer token authentication obtained from the Node service:

```bash
TOKEN=$(curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')
```

## Response Codes
- **200**: Success
- **422**: Validation Error  
- **404**: Resource Not Found
- **500**: Internal Server Error

## Key Features
- **Cross-Video Tracking**: Track individuals across multiple video sequences
- **Real-time Processing**: Background processing with status monitoring
- **Cache Management**: Intelligent caching for performance optimization
- **Vector Embeddings**: Advanced facial recognition using vector similarity
- **Spatial Analytics**: Movement patterns and heatmap generation
- **Workflow Orchestration**: Configurable person detection workflows

## Notes
- Sessions support background processing for non-blocking operation
- Cache provides performance optimization for repeated queries
- All datetime parameters use ISO 8601 format with timezone
- Collection names are case-sensitive strings
- Session UUIDs are generated automatically and returned in creation response