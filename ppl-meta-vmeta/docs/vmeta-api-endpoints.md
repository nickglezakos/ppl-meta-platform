# PPL Meta vmeta Service - API Endpoints Documentation

**Document Version**: 1.0  
**Date**: November 9, 2025  
**Service**: vmeta (Vector-based facial embeddings and analytics)  
**Base URL**: `http://localhost:8008`  
**Related Version**: v2.19.30 (in development)

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Authentication](#authentication)
3. [Health & Status Endpoints](#health--status-endpoints)
4. [Cross-Video Individual Tracking](#cross-video-individual-tracking)
5. [MVR-People Management](#mvr-people-management)
6. [Embeddings & Search](#embeddings--search)
7. [Analytics & Workflows](#analytics--workflows)
8. [Error Handling](#error-handling)
9. [Rate Limits & Performance](#rate-limits--performance)

---

## Service Overview

The vmeta service is the core vector-based facial recognition and cross-video tracking component of the PPL Meta platform. It provides:

- **Cross-Video Individual Tracking**: Track unique individuals across multiple video recordings
- **MVR (Multi-Video Recognition) People**: Canonical representations of unique persons
- **Face Embeddings**: 512-dimensional Facenet512 embeddings with pgvector storage
- **Similarity Search**: Fast HNSW-indexed face similarity matching
- **Session-Wide Caching**: Three-level caching architecture for performance optimization
- **Background Processing**: Asynchronous MVR creation and matching

**Key Technologies**:
- FastAPI for REST API
- PostgreSQL with pgvector extension for vector operations
- HNSW indexing for fast similarity search
- Facenet512 model for face embeddings
- JWT authentication for secure access

---

## Authentication

⚠️ **Most endpoints require authentication via JWT token.**

### Obtain Authentication Token

**Endpoint**: `POST http://localhost:8001/api/v1/users/login` (Node Service)

**Request**:
```bash
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -X GET 'http://localhost:8008/api/v1/endpoint' \
  -H "Authorization: Bearer <access_token>"
```

---

## Health & Status Endpoints

### 1. Service Health Check

**Endpoint**: `GET /health`

**Authentication**: None required

**Description**: Returns service health status including MVR-People system availability, database connection, and component status.

**Request**:
```bash
curl http://localhost:8008/health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "vmeta",
  "version": "1.0.0",
  "description": "Vector-based facial embeddings and analytics",
  "timestamp": "2025-11-09T12:00:00.000000",
  "mvr_people_available": true,
  "database": {
    "connected": true
  },
  "ml_models": {
    "total_loaded": 1
  },
  "statistics": {
    "total_mvr_people": 245,
    "total_individuals_mapped": 1203
  }
}
```

**Scope**: Monitoring and health checks for service discovery and load balancers.

---

### 2. Root Service Info

**Endpoint**: `GET /`

**Authentication**: None required

**Description**: Returns service metadata and capabilities.

**Response**:
```json
{
  "service": "vmeta",
  "version": "1.0.0",
  "description": "PPL Meta Vector-based facial embeddings and analytics",
  "status": "operational",
  "capabilities": [
    "facial_embeddings",
    "vector_search",
    "cross_video_tracking",
    "mvr_people_management"
  ]
}
```

---

## Cross-Video Individual Tracking

### 3. Create Tracking Session

**Endpoint**: `POST /api/v1/cross-video/individuals/tracking/sessions`

**Authentication**: Required

**Description**: Creates a new cross-video individual tracking session. Discovers videos from specified collections and time range, detects individuals, and tracks unique people across videos. Implements **three-level caching** for performance:
- **Level 0**: Session-wide bulk cache (reuses entire completed sessions)
- **Level 1**: Individual-level cache (reuses individuals for known videos)
- **Level 2**: MVR-level cache (reuses MVR people for known individuals)

**Request Body**:
```json
{
  "collections": ["usb_camera_0", "usb_camera_1"],
  "start_time": "2025-11-06T06:00:00",
  "end_time": "2025-11-07T16:00:00",
  "algorithm_config": {
    "similarity_threshold": 0.75,
    "merge_method": "agglomerative"
  },
  "force_reprocess": false
}
```

**Parameters**:
- `collections` (required): Array of camera/collection identifiers
- `start_time` (required): ISO 8601 timestamp for range start
- `end_time` (required): ISO 8601 timestamp for range end
- `algorithm_config` (optional): Tracking algorithm parameters
- `force_reprocess` (optional): Skip cache and reprocess (default: false)

**Response**:
```json
{
  "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
  "status": "processing",
  "message": "Session created successfully",
  "total_videos": 12,
  "cache_hit": false,
  "created_at": "2025-11-08T19:06:53.123456"
}
```

**Status Values**:
- `processing`: Session is being processed
- `completed`: All processing finished
- `failed`: Processing failed
- `cached`: Returned from cache (instant response)

**Example**:
```bash
curl -X POST http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "collections": ["usb_camera_0"],
    "start_time": "2025-11-06T06:00:00",
    "end_time": "2025-11-07T16:00:00"
  }'
```

**Scope**: Primary endpoint for initiating cross-video tracking. Handles video discovery, individual detection via Orchestrator service, face embedding extraction, similarity-based merging, and MVR creation. Supports caching at multiple levels for performance optimization.

---

### 4. Get Session Status

**Endpoint**: `GET /api/v1/cross-video/individuals/tracking/sessions/{session_uuid}`

**Authentication**: Required

**Description**: Retrieves detailed status and results for a tracking session, including videos processed, individuals found, MVR people created, and processing statistics.

**Parameters**:
- `session_uuid` (path): UUID of the tracking session

**Response**:
```json
{
  "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
  "status": "completed",
  "created_at": "2025-11-08T19:06:53.123456",
  "completed_at": "2025-11-08T19:07:15.789012",
  "total_videos": 12,
  "processed_videos": 12,
  "failed_videos": 0,
  "individuals_found": 18,
  "mvr_people_created": 6,
  "cache_hits": 0,
  "processing_time_seconds": 22.67,
  "collections": ["usb_camera_0"],
  "start_time": "2025-11-06T06:00:00",
  "end_time": "2025-11-07T16:00:00",
  "algorithm_config": {
    "similarity_threshold": 0.75
  }
}
```

**Example**:
```bash
curl http://localhost:8008/api/v1/cross-video/individuals/tracking/sessions/{session_uuid} \
  -H "Authorization: Bearer <token>"
```

**Scope**: Monitor tracking session progress, retrieve results, and audit processing metrics. Used by frontend to display session status and results.

---

### 5. Get Session Individuals

**Endpoint**: `GET /api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals`

**Authentication**: Required

**Description**: Retrieves all individuals detected in a tracking session with their video appearances, confidence scores, and MVR mappings.

**Parameters**:
- `session_uuid` (path): UUID of the tracking session
- `include_mvr` (query, optional): Include MVR people data (default: true)
- `min_confidence` (query, optional): Filter by minimum confidence score

**Response**:
```json
{
  "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
  "total_individuals": 18,
  "individuals": [
    {
      "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
      "individual_id": "IND-001",
      "confidence_score": 0.92,
      "video_count": 3,
      "video_uuids": ["video-1", "video-2", "video-3"],
      "first_seen": "2025-11-06T08:15:23",
      "last_seen": "2025-11-06T14:32:10",
      "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
      "processing_type": "new"
    }
  ]
}
```

**Scope**: Retrieve detailed individual tracking results for display, analysis, and downstream processing.

---

### 6. Get Individual Video Appearances

**Endpoint**: `GET /api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/appearances`

**Authentication**: Required

**Description**: Retrieves all video appearances for a specific individual, including timestamps, confidence scores, and bounding box data.

**Parameters**:
- `individual_uuid` (path): UUID of the individual

**Response**:
```json
{
  "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
  "total_appearances": 3,
  "appearances": [
    {
      "video_uuid": "video-1",
      "video_filename": "camera_0_2025-11-06_08-15.mp4",
      "timestamp": "2025-11-06T08:15:23",
      "confidence_score": 0.94,
      "bounding_box": {
        "x": 450,
        "y": 230,
        "width": 120,
        "height": 160
      },
      "frame_number": 345
    }
  ]
}
```

**Scope**: Detailed tracking of individual appearances for analytics, playback, and verification.

---

### 7. Get Individual Aggregated Analysis

**Endpoint**: `GET /api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis`

**Authentication**: Required

**Description**: Provides aggregated analytics for an individual across all video appearances, including temporal patterns, spatial distribution, and quality metrics.

**Parameters**:
- `individual_uuid` (path): UUID of the individual

**Response**:
```json
{
  "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
  "total_appearances": 3,
  "time_span_hours": 6.28,
  "average_confidence": 0.92,
  "max_confidence": 0.96,
  "min_confidence": 0.88,
  "cameras_visited": ["usb_camera_0", "usb_camera_1"],
  "temporal_distribution": {
    "morning": 1,
    "afternoon": 2,
    "evening": 0
  },
  "quality_metrics": {
    "clear_frames": 234,
    "blurry_frames": 12,
    "occluded_frames": 3
  }
}
```

**Scope**: Analytics dashboard for individual behavior analysis and tracking quality assessment.

---

### 8. Cache Status

**Endpoint**: `GET /api/v1/cross-video/individuals/tracking/cache/status`

**Authentication**: Required

**Description**: Returns cache performance metrics for the three-level caching system.

**Response**:
```json
{
  "cache_enabled": true,
  "session_wide_cache": {
    "total_sessions": 145,
    "cache_hits": 42,
    "cache_misses": 103,
    "hit_rate": 0.29
  },
  "individual_cache": {
    "total_individuals": 1203,
    "reused_individuals": 856,
    "reuse_rate": 0.71
  },
  "mvr_cache": {
    "total_mvr_people": 245,
    "reused_mvr": 189,
    "reuse_rate": 0.77
  },
  "performance_impact": {
    "average_time_with_cache_ms": 450,
    "average_time_without_cache_ms": 2300,
    "speedup_factor": 5.11
  }
}
```

**Scope**: Monitor cache effectiveness and optimize caching strategy based on hit rates.

---

### 9. Manual Merge Individuals

**Endpoint**: `POST /api/v1/cross-video/individuals/tracking/merge`

**Authentication**: Required

**Description**: Manually merges two or more individuals into a single MVR person. Used for correcting tracking errors or merging individuals that were not automatically merged.

**Request Body**:
```json
{
  "individual_uuids": [
    "5cf43abf-1234-5678-90ab-cdef12345678",
    "6192901d-2345-6789-01bc-def234567890"
  ],
  "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
  "similarity_threshold": 0.70,
  "merge_source": "manual_correction"
}
```

**Parameters**:
- `individual_uuids` (required): Array of at least 2 individual UUIDs
- `session_uuid` (required): Session UUID for audit trail
- `similarity_threshold` (optional): Minimum similarity for validation (default: 0.70)
- `merge_source` (optional): Source identifier for tracking (default: "manual")

**Response**:
```json
{
  "success": true,
  "merged_individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
  "merged_count": 2,
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "average_similarity": 0.87,
  "merge_timestamp": "2025-11-09T10:30:45.123456"
}
```

**Scope**: Manual correction of tracking results and quality control for automated tracking.

---

## MVR-People Management

MVR (Multi-Video Recognition) People represent canonical, unique individuals detected across the platform. Each MVR person has a quality-weighted face embedding derived from all associated individual detections.

### 10. Process Single Media for MVR Creation

**Endpoint**: `POST /api/v1/mvr-people/process-media`

**Authentication**: Required

**Description**: Processes one or more media files (videos) to create isolated MVR-People records with full ML processing. This endpoint performs Face Detection V2 orchestration, person object extraction, face embedding generation, age/gender estimation, and MVR creation **without cross-media merging**. Each media file is processed independently, creating isolated individuals that are linked to MVR people within that specific media only.

**Key Features**:
- Face Detection V2 workflow orchestration with Vision service
- Complete ML pipeline: FaceNet512 embeddings, age estimation, gender classification
- Intra-media face clustering (groups similar faces within the same video)
- Creates isolated individual records in vmeta database
- Links person objects to individuals via `individual_video_appearances` table
- Creates MVR people with `is_isolated=true` flag
- Maintains relational structure for appearance tracking and routes data
- No cross-video merging (each media processed independently)

**Use Cases**:
- Process individual videos without cross-video tracking overhead
- Generate MVR people for specific media files
- Quick face detection and recognition for single videos
- Batch processing of media files independently

**Request Body**:
```json
{
  "media_uuids": [
    "5c00d13d-1a64-4be7-885b-477f441e2ab9",
    "b663af24-512f-46e3-8281-3e7d591da13a"
  ],
  "processing_options": {
    "similarity_threshold": 0.8,
    "min_face_quality": 0.70,
    "include_demographics": true,
    "include_route_data": true
  }
}
```

**Parameters**:
- `media_uuids` (required): Array of media UUIDs to process
- `processing_options` (optional):
  - `similarity_threshold` (optional): Threshold for intra-media clustering (default: 0.8)
  - `min_face_quality` (optional): Minimum face quality threshold (default: 0.70)
  - `include_demographics` (optional): Include age/gender estimation (default: true)
  - `include_route_data` (optional): Include route/trajectory data (default: true)

**Response** (200 OK):
```json
{
  "success": true,
  "processed_media": 2,
  "failed_media": 0,
  "mvr_people_count": 8,
  "results": [
    {
      "media_uuid": "5c00d13d-1a64-4be7-885b-477f441e2ab9",
      "status": "completed",
      "mvr_people": [
        {
          "mvr_people_uuid": "4979b5b9-3d76-462f-9aa4-fa89b94fe835",
          "individual_uuids": ["11017f6e-8589-41d1-b8be-82fef0ab0ce8"],
          "total_appearances": 1,
          "unique_videos": 1,
          "confidence_score": 0.9,
          "quality_score": 0.85,
          "demographics": {
            "gender": "male",
            "gender_confidence": 0.9992887377738953,
            "age_min": 30,
            "age_max": 40,
            "age_confidence": 0.85
          },
          "appearances": [
            {
              "individual_uuid": "11017f6e-8589-41d1-b8be-82fef0ab0ce8",
              "video_uuid": "5c00d13d-1a64-4be7-885b-477f441e2ab9",
              "person_object_uuid": "11017f6e-8589-41d1-b8be-82fef0ab0ce8",
              "start_timestamp": "2025-11-28T13:14:09.397059+02:00",
              "end_timestamp": "2025-11-28T13:14:09.397059+02:00",
              "confidence": 0.9
            }
          ],
          "route_data": {
            "route_points": [],
            "total_detections": 0
          },
          "face_embedding_available": true,
          "is_isolated": true,
          "source_media_uuid": "5c00d13d-1a64-4be7-885b-477f441e2ab9"
        }
      ],
      "total_faces_detected": 1,
      "mvr_people_count": 1,
      "processing_time_ms": 4085
    }
  ],
  "aggregate_statistics": {
    "total_mvr_people_created": 8,
    "total_individuals_detected": 15,
    "avg_processing_ms": 3542.5,
    "total_processing_ms": 7085
  }
}
```

**Error Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "No media UUIDs provided",
  "processed_media": 0,
  "failed_media": 0
}
```

**Processing Flow**:
1. **Face Detection V2**: Orchestrates Vision service workflow to detect faces
2. **Person Objects**: Extracts person objects with metadata and face crops
3. **Quality Filtering**: Filters faces based on quality threshold (default 0.70)
4. **ML Processing**: Generates FaceNet512 embeddings, estimates age and gender
5. **Intra-Media Clustering**: Groups similar faces within same video using cosine similarity
6. **Individual Creation**: Creates isolated individual records with unique IDs
7. **Person Object Linking**: Links person objects to individuals via `individual_video_appearances`
8. **MVR Creation**: Creates MVR people linked to isolated individuals

**Performance**:
- Average processing time: ~4-5 seconds per video
- Depends on: Number of faces, video resolution, ML model performance
- Parallel processing: Multiple media files processed sequentially (not parallel)

**Database Impact**:
- Creates records in: `individuals`, `individual_video_appearances`, `mvr_people`, `individual_mvr_mapping`
- Sets `is_isolated=true` for all MVR people created
- Maintains foreign key relationships for data integrity

**Important Notes**:
- ⚠️ Face Detection V2 returns `quality_score=0.0` by design (in-memory workflow)
- Default quality score of 0.85 is used for V2 person objects to pass filtering
- No cross-media merging: Each video creates independent MVR people
- Isolated individuals maintain relational structure for appearance counting and routes
- Demographics included if ML models are loaded and enabled

**Example**:
```bash
export TOKEN="your_jwt_token"
curl -X POST 'http://localhost:8008/api/v1/mvr-people/process-media' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "media_uuids": ["5c00d13d-1a64-4be7-885b-477f441e2ab9"],
    "processing_options": {
      "similarity_threshold": 0.8,
      "include_demographics": true
    }
  }'
```

**Scope**: Single-media MVR processing for independent video analysis, isolated face recognition, and quick demographic profiling without cross-video tracking overhead.

---

### 11. Create MVR for Individual

**Endpoint**: `POST /api/v1/mvr-people/individuals/{individual_uuid}/create`

**Authentication**: Required

**Description**: Creates an MVR-People record for a specific individual. Can be processed synchronously or asynchronously via background task.

**Parameters**:
- `individual_uuid` (path): UUID of the individual
- `async` (body, optional): Process asynchronously (default: false)

**Request Body**:
```json
{
  "async": false,
  "priority": "normal"
}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
  "status": "completed",
  "processing_time_ms": 234,
  "face_embedding": {
    "dimensions": 512,
    "model": "Facenet512",
    "confidence": 0.92
  }
}
```

**Scope**: Create MVR records for individuals that bypassed automatic MVR creation (e.g., singles without merge candidates).

---

### 11. Get MVR by UUID

**Endpoint**: `GET /api/v1/mvr-people/{mvr_people_uuid}`

**Authentication**: Required

**Description**: Retrieves complete MVR-People record including face embedding, demographic estimates, mapped individuals, and video appearances.

**Parameters**:
- `mvr_people_uuid` (path): UUID of the MVR person

**Response**:
```json
{
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "featured_individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
  "face_embedding_available": true,
  "embedding_confidence": 0.92,
  "embedding_model": "Facenet512",
  "confidence_score": 0.91,
  "quality_score": 0.89,
  "mapped_individuals_count": 6,
  "video_appearances_count": 12,
  "created_at": "2025-11-08T19:05:37.607285",
  "updated_at": "2025-11-08T19:05:37.607285",
  "demographics": {
    "estimated_age": 32,
    "estimated_gender": "male",
    "confidence": 0.78
  }
}
```

**Scope**: Retrieve complete MVR data for display, analysis, and matching operations.

---

### 12. Search Similar MVR People

**Endpoint**: `POST /api/v1/mvr-people/search/similar`

**Authentication**: Required

**Description**: Searches for MVR people similar to a given face embedding or individual using HNSW-indexed vector similarity search.

**Request Body**:
```json
{
  "query_embedding": [0.41377905, 0.36214602, ...],
  "top_k": 10,
  "similarity_threshold": 0.75,
  "exclude_uuids": ["uuid-to-exclude"]
}
```

**Alternative** (search by individual):
```json
{
  "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
  "top_k": 10,
  "similarity_threshold": 0.75
}
```

**Parameters**:
- `query_embedding` (optional): 512-dimensional face embedding vector
- `individual_uuid` (optional): Use individual's embedding as query
- `top_k` (optional): Maximum results to return (default: 10)
- `similarity_threshold` (optional): Minimum cosine similarity (default: 0.70)
- `exclude_uuids` (optional): MVR UUIDs to exclude from results

**Response**:
```json
{
  "total_results": 3,
  "search_time_ms": 12,
  "results": [
    {
      "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
      "similarity_score": 0.94,
      "confidence_score": 0.91,
      "mapped_individuals_count": 6,
      "last_seen": "2025-11-08T14:32:10"
    },
    {
      "mvr_people_uuid": "503ec72f-abcd-1234-5678-90abcdef1234",
      "similarity_score": 0.87,
      "confidence_score": 0.88,
      "mapped_individuals_count": 3,
      "last_seen": "2025-11-07T18:45:23"
    }
  ]
}
```

**Scope**: Face recognition, duplicate detection, person search, and identity verification.

---

### 13. Search MVR by Demographics

**Endpoint**: `POST /api/v1/mvr-people/search/demographics`

**Authentication**: Required

**Description**: Searches MVR people based on demographic filters (age range, gender, confidence threshold).

**Request Body**:
```json
{
  "age_min": 25,
  "age_max": 40,
  "gender": "male",
  "min_confidence": 0.80,
  "limit": 50
}
```

**Response**:
```json
{
  "total_results": 12,
  "results": [
    {
      "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
      "estimated_age": 32,
      "estimated_gender": "male",
      "confidence_score": 0.91,
      "mapped_individuals_count": 6
    }
  ]
}
```

**Scope**: Demographic analysis, targeted search, and statistical reporting.

---

### 14. Link Individual to MVR

**Endpoint**: `POST /api/v1/mvr-people/{mvr_people_uuid}/link`

**Authentication**: Required

**Description**: Manually links an individual to an existing MVR-People record. Used for corrections or linking individuals that were not automatically matched.

**Parameters**:
- `mvr_people_uuid` (path): UUID of the MVR person

**Request Body**:
```json
{
  "individual_uuid": "6192901d-2345-6789-01bc-def234567890",
  "confidence": 0.85,
  "source": "manual_link"
}
```

**Response**:
```json
{
  "success": true,
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "individual_uuid": "6192901d-2345-6789-01bc-def234567890",
  "linked_at": "2025-11-09T10:45:12.345678",
  "total_individuals": 7
}
```

**Scope**: Manual quality control and correction of automatic matching.

---

### 15. Batch Create MVR People

**Endpoint**: `POST /api/v1/mvr-people/batch/create`

**Authentication**: Required

**Description**: Creates MVR-People records for multiple individuals in a single request. Processes asynchronously in background.

**Request Body**:
```json
{
  "individual_uuids": [
    "5cf43abf-1234-5678-90ab-cdef12345678",
    "6192901d-2345-6789-01bc-def234567890",
    "91b5508e-3456-7890-12cd-ef3456789012"
  ],
  "priority": "normal"
}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "total_requested": 3,
  "batch_id": "batch-abc-123",
  "status": "processing",
  "estimated_completion_seconds": 5
}
```

**Scope**: Bulk MVR creation after tracking sessions or batch imports.

---

### 16. Get MVR Statistics

**Endpoint**: `GET /api/v1/mvr-people/statistics`

**Authentication**: Required

**Description**: Returns system-wide MVR-People statistics including total counts, quality metrics, and demographic distributions.

**Response**:
```json
{
  "total_mvr_people": 245,
  "total_individuals_mapped": 1203,
  "average_individuals_per_mvr": 4.91,
  "mvr_with_embeddings": 238,
  "average_confidence": 0.87,
  "demographic_distribution": {
    "age_ranges": {
      "18-30": 82,
      "31-50": 134,
      "51+": 29
    },
    "gender_distribution": {
      "male": 156,
      "female": 89
    }
  },
  "quality_metrics": {
    "high_quality": 198,
    "medium_quality": 42,
    "low_quality": 5
  }
}
```

**Scope**: System monitoring, analytics dashboard, and capacity planning.

---

### 17. Match Individual to MVR

**Endpoint**: `POST /api/v1/mvr-people/match`

**Authentication**: Required

**Description**: Finds the best matching MVR-People record for an individual based on face embedding similarity.

**Request Body**:
```json
{
  "individual_uuid": "6192901d-2345-6789-01bc-def234567890",
  "similarity_threshold": 0.80,
  "auto_link": false
}
```

**Parameters**:
- `individual_uuid` (required): Individual to match
- `similarity_threshold` (optional): Minimum similarity (default: 0.80)
- `auto_link` (optional): Automatically link if match found (default: false)

**Response**:
```json
{
  "match_found": true,
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "similarity_score": 0.89,
  "confidence": 0.91,
  "auto_linked": false,
  "alternatives": [
    {
      "mvr_people_uuid": "503ec72f-abcd-1234-5678-90abcdef1234",
      "similarity_score": 0.76
    }
  ]
}
```

**Scope**: Automatic linking of new individuals to existing MVR records during tracking.

---

### 18. Merge MVR People

**Endpoint**: `POST /api/v1/mvr-people/merge`

**Authentication**: Required

**Description**: Merges two or more MVR-People records into a single MVR, combining all mapped individuals and recomputing the canonical embedding.

**Request Body**:
```json
{
  "source_mvr_uuids": [
    "503ec72f-abcd-1234-5678-90abcdef1234",
    "7a8b9c0d-def1-2345-6789-0abcdef12345"
  ],
  "target_mvr_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "merge_reason": "duplicate_detection"
}
```

**Parameters**:
- `source_mvr_uuids` (required): MVR UUIDs to merge (orphaned after merge)
- `target_mvr_uuid` (required): Target MVR that will receive all individuals
- `merge_reason` (optional): Reason for merge (audit trail)

**Response**:
```json
{
  "success": true,
  "target_mvr_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "merged_count": 2,
  "total_individuals_now": 12,
  "embedding_recomputed": true,
  "new_confidence": 0.93,
  "merge_timestamp": "2025-11-09T11:15:30.123456"
}
```

**Scope**: Quality control, duplicate cleanup, and identity consolidation.

---

### 19. Get MVR Merge History

**Endpoint**: `GET /api/v1/mvr-people/{mvr_people_uuid}/merge-history`

**Authentication**: Required

**Description**: Retrieves complete merge history for an MVR person, showing all merges that contributed to the current record.

**Parameters**:
- `mvr_people_uuid` (path): UUID of the MVR person

**Response**:
```json
{
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "total_merges": 3,
  "merge_history": [
    {
      "merged_at": "2025-11-08T19:05:37.607285",
      "source_mvr_uuid": "503ec72f-abcd-1234-5678-90abcdef1234",
      "individuals_merged": 3,
      "merge_reason": "automatic_similarity",
      "similarity_score": 0.89
    },
    {
      "merged_at": "2025-11-08T20:15:42.123456",
      "source_mvr_uuid": "7a8b9c0d-def1-2345-6789-0abcdef12345",
      "individuals_merged": 2,
      "merge_reason": "manual_correction",
      "similarity_score": 0.75
    }
  ]
}
```

**Scope**: Audit trail, quality assurance, and merge validation.

---

### 20. List Orphaned MVR People

**Endpoint**: `GET /api/v1/mvr-people/orphaned`

**Authentication**: Required

**Description**: Lists MVR-People records that have no mapped individuals (orphaned after merges or individual deletions).

**Parameters**:
- `limit` (query, optional): Maximum results (default: 100)

**Response**:
```json
{
  "total_orphaned": 5,
  "orphaned_mvr": [
    {
      "mvr_people_uuid": "503ec72f-abcd-1234-5678-90abcdef1234",
      "created_at": "2025-11-07T18:45:23",
      "orphaned_at": "2025-11-08T19:05:37",
      "reason": "merged_into_01447ff5"
    }
  ]
}
```

**Scope**: Database cleanup and maintenance.

---

### 21. Update MVR Matching Configuration

**Endpoint**: `PUT /api/v1/mvr-people/config/matching`

**Authentication**: Required (Admin)

**Description**: Updates global MVR matching configuration parameters (similarity thresholds, algorithm settings).

**Request Body**:
```json
{
  "similarity_threshold": 0.75,
  "auto_link_enabled": true,
  "min_confidence": 0.70,
  "max_alternatives": 5
}
```

**Response**:
```json
{
  "success": true,
  "updated_at": "2025-11-09T11:30:00",
  "config": {
    "similarity_threshold": 0.75,
    "auto_link_enabled": true,
    "min_confidence": 0.70,
    "max_alternatives": 5
  }
}
```

**Scope**: System administration and tuning.

---

### 22. Get MVR Matching Configuration

**Endpoint**: `GET /api/v1/mvr-people/config/matching`

**Authentication**: Required

**Description**: Retrieves current MVR matching configuration.

**Response**:
```json
{
  "similarity_threshold": 0.75,
  "auto_link_enabled": true,
  "min_confidence": 0.70,
  "max_alternatives": 5,
  "last_updated": "2025-11-09T11:30:00"
}
```

---

### 23. Get Background Processing Status

**Endpoint**: `GET /api/v1/mvr-people/background/status`

**Authentication**: Required

**Description**: Returns status of background MVR processing tasks (async MVR creation, matching, merging).

**Response**:
```json
{
  "total_tasks": 12,
  "pending_tasks": 3,
  "processing_tasks": 2,
  "completed_tasks": 7,
  "failed_tasks": 0,
  "queue_health": "healthy",
  "average_processing_time_seconds": 2.34
}
```

**Scope**: Monitor background task queue and processing health.

---

### 24. Batch Match and Merge

**Endpoint**: `POST /api/v1/mvr-people/batch-match-and-merge`

**Authentication**: Required

**Description**: Batch processes multiple individuals to find similar faces and automatically merge duplicates. Returns unique count after deduplication.

**Request Body**:
```json
{
  "individual_uuids": [
    "5cf43abf-1234-5678-90ab-cdef12345678",
    "6192901d-2345-6789-01bc-def234567890",
    "91b5508e-3456-7890-12cd-ef3456789012"
  ],
  "threshold": 0.85,
  "triggered_by": "cross_video_tracking_session",
  "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b"
}
```

**Parameters**:
- `individual_uuids` (required): List of individual UUIDs to process
- `threshold` (optional): Similarity threshold for merging (default: 0.85)
- `triggered_by` (optional): Source identifier (default: "batch_auto_match")
- `session_uuid` (optional): Tracking session UUID for audit

**Response**:
```json
{
  "success": true,
  "original_count": 15,
  "unique_count": 12,
  "merge_count": 3,
  "merges": [
    {
      "keep_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
      "merged_uuids": [
        "6192901d-2345-6789-01bc-def234567890"
      ],
      "similarity": 0.89,
      "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88"
    }
  ],
  "processing_time_seconds": 2.34
}
```

**Scope**: Automatic deduplication during cross-video tracking, returning unique individual count.

---

## Embeddings & Search

### 25. Generate Face Embeddings

**Endpoint**: `POST /api/v1/embeddings/generate`

**Authentication**: Required

**Description**: Generates 512-dimensional Facenet512 embeddings for face images.

**Request Body**:
```json
{
  "face_images": [
    {
      "image_data": "base64_encoded_image",
      "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678"
    }
  ],
  "normalize": true
}
```

**Response**:
```json
{
  "embeddings_generated": 1,
  "model": "Facenet512",
  "dimensions": 512,
  "status": "completed",
  "results": [
    {
      "individual_uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
      "embedding": [0.41377905, 0.36214602, ...],
      "confidence": 0.92
    }
  ]
}
```

**Scope**: Generate embeddings for external face images or offline processing.

---

### 26. Search Similar Faces

**Endpoint**: `POST /api/v1/embeddings/search`

**Authentication**: Required

**Description**: Searches for similar faces using vector similarity across all stored embeddings (individuals and MVR people).

**Request Body**:
```json
{
  "query_embedding": [0.41377905, 0.36214602, ...],
  "top_k": 20,
  "search_scope": "all",
  "similarity_threshold": 0.70
}
```

**Parameters**:
- `query_embedding` (required): 512-dimensional embedding vector
- `top_k` (optional): Maximum results (default: 10)
- `search_scope` (optional): "individuals", "mvr", or "all" (default: "all")
- `similarity_threshold` (optional): Minimum similarity (default: 0.70)

**Response**:
```json
{
  "similar_faces": [
    {
      "type": "mvr_people",
      "uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
      "similarity_score": 0.94,
      "confidence": 0.91
    },
    {
      "type": "individual",
      "uuid": "5cf43abf-1234-5678-90ab-cdef12345678",
      "similarity_score": 0.87,
      "confidence": 0.88
    }
  ],
  "total_matches": 2,
  "search_time_ms": 15
}
```

**Scope**: Face recognition, identity verification, and similarity search.

---

## Analytics & Workflows

### 27. Analyze Person Routes

**Endpoint**: `POST /api/v1/analytics/person-routes`

**Authentication**: Required

**Description**: Analyzes person movement routes and patterns across cameras and time.

**Request Body**:
```json
{
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "start_time": "2025-11-06T00:00:00",
  "end_time": "2025-11-07T23:59:59",
  "include_trajectory": true
}
```

**Response**:
```json
{
  "mvr_people_uuid": "01447ff5-9643-4ba5-b761-2952ddee3e88",
  "person_routes": [
    {
      "camera": "usb_camera_0",
      "entry_time": "2025-11-06T08:15:23",
      "exit_time": "2025-11-06T08:32:10",
      "duration_seconds": 1007
    }
  ],
  "movement_statistics": {
    "total_distance_meters": 145.3,
    "average_velocity_mps": 0.14,
    "time_in_frame_seconds": 1007,
    "cameras_visited": 2
  },
  "trajectory": {
    "points": [
      {"x": 450, "y": 230, "timestamp": "2025-11-06T08:15:23"},
      {"x": 520, "y": 245, "timestamp": "2025-11-06T08:16:30"}
    ]
  },
  "status": "completed"
}
```

**Scope**: Movement analytics, behavior analysis, and security monitoring.

---

### 28. Generate Heatmap

**Endpoint**: `GET /api/v1/analytics/heatmap`

**Authentication**: Required

**Description**: Generates spatial heatmap for person detection frequency across camera views.

**Parameters**:
- `session_uuid` (query, optional): Filter by tracking session
- `start_time` (query, optional): Time range start
- `end_time` (query, optional): Time range end
- `camera` (query, optional): Filter by camera

**Response**:
```json
{
  "heatmap_data": [
    {
      "x": 100,
      "y": 150,
      "intensity": 23
    }
  ],
  "grid_size": {
    "width": 1920,
    "height": 1080,
    "cell_size": 50
  },
  "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
  "generated_at": "2025-11-09T12:00:00Z",
  "total_detections": 1523
}
```

**Scope**: Spatial analytics, crowd density analysis, and zone monitoring.

---

### 29. Execute Workflow

**Endpoint**: `POST /api/v1/workflows/execute`

**Authentication**: Required

**Description**: Executes a predefined workflow combining multiple operations (e.g., track → analyze → export).

**Request Body**:
```json
{
  "workflow_type": "full_tracking_analysis",
  "parameters": {
    "collections": ["usb_camera_0"],
    "start_time": "2025-11-06T00:00:00",
    "end_time": "2025-11-07T23:59:59",
    "output_format": "json"
  }
}
```

**Response**:
```json
{
  "workflow_id": "workflow-abc-123",
  "status": "processing",
  "estimated_completion_minutes": 5,
  "steps": [
    {
      "step": "video_discovery",
      "status": "completed"
    },
    {
      "step": "individual_detection",
      "status": "processing"
    },
    {
      "step": "analysis",
      "status": "pending"
    }
  ]
}
```

**Scope**: Automated multi-step processing pipelines.

---

### 30. Get Workflow Status

**Endpoint**: `GET /api/v1/workflows/status/{workflow_id}`

**Authentication**: Required

**Description**: Retrieves status of a running or completed workflow.

**Parameters**:
- `workflow_id` (path): Workflow identifier

**Response**:
```json
{
  "workflow_id": "workflow-abc-123",
  "status": "completed",
  "started_at": "2025-11-09T10:00:00",
  "completed_at": "2025-11-09T10:04:32",
  "results": {
    "tracking_session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
    "individuals_found": 18,
    "mvr_people_created": 6
  }
}
```

---

### 31. Get Active Sessions

**Endpoint**: `GET /api/v1/workflows/sessions/active`

**Authentication**: Required

**Description**: Lists all currently active tracking sessions and workflows.

**Response**:
```json
{
  "active_sessions": [
    {
      "session_uuid": "dc1bcdef-7022-4f68-90c4-53822d70041b",
      "status": "processing",
      "started_at": "2025-11-09T11:45:23",
      "progress": 0.67
    }
  ],
  "active_workflows": [
    {
      "workflow_id": "workflow-abc-123",
      "type": "full_tracking_analysis",
      "status": "processing",
      "progress": 0.42
    }
  ],
  "total_active": 2
}
```

**Scope**: Monitor system load and active processing.

---

## Error Handling

### Standard Error Response

All endpoints return errors in a consistent format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required parameter: collections",
    "details": {
      "parameter": "collections",
      "expected": "array of strings"
    },
    "timestamp": "2025-11-09T12:00:00.000000",
    "request_id": "req-abc-123"
  }
}
```

### HTTP Status Codes

| Status Code | Meaning | When It Occurs |
|-------------|---------|----------------|
| 200 OK | Success | Request completed successfully |
| 201 Created | Resource created | New resource created (rare, usually 202) |
| 202 Accepted | Async processing | Request accepted, processing asynchronously |
| 400 Bad Request | Invalid input | Missing parameters, invalid format |
| 401 Unauthorized | Not authenticated | Missing or invalid JWT token |
| 403 Forbidden | Not authorized | Valid token but insufficient permissions |
| 404 Not Found | Resource not found | Session UUID, Individual UUID not found |
| 409 Conflict | Resource conflict | Duplicate resource, constraint violation |
| 422 Unprocessable Entity | Validation failed | Valid format but business logic error |
| 429 Too Many Requests | Rate limit exceeded | Too many requests from client |
| 500 Internal Server Error | Server error | Unexpected server-side error |
| 503 Service Unavailable | Service down | Database connection lost, service overloaded |

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Request validation failed |
| `AUTHENTICATION_REQUIRED` | JWT token missing |
| `INVALID_TOKEN` | JWT token invalid or expired |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | Requested resource does not exist |
| `DUPLICATE_RESOURCE` | Resource already exists |
| `DATABASE_ERROR` | Database operation failed |
| `EXTERNAL_SERVICE_ERROR` | Orchestrator/Media service unavailable |
| `PROCESSING_ERROR` | Internal processing error |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

---

## Rate Limits & Performance

### Rate Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Health checks | Unlimited | - |
| Read operations | 100 req/min | Per user |
| Create tracking session | 10 req/min | Per user |
| Search operations | 50 req/min | Per user |
| Batch operations | 5 req/min | Per user |
| Background tasks | 20 req/min | Per user |

### Performance Characteristics

| Operation | Avg Response Time | Notes |
|-----------|-------------------|-------|
| Health check | < 50ms | Simple database query |
| Session cache hit | < 100ms | Instant cache response |
| Session cache miss (10 videos) | 5-15 seconds | Depends on Orchestrator |
| MVR similarity search | 10-50ms | HNSW index optimized |
| Individual search | 15-30ms | Vector similarity search |
| Batch match & merge (15 individuals) | 2-4 seconds | CPU-bound operation |
| Face embedding generation | 50-200ms | Per face, GPU accelerated |

### Optimization Tips

1. **Use caching**: Set `force_reprocess: false` to leverage session-wide cache
2. **Batch operations**: Use batch endpoints for multiple individuals
3. **Narrow time ranges**: Smaller time ranges = faster video discovery
4. **Filter early**: Use confidence thresholds to reduce result sets
5. **Async processing**: Use async mode for non-critical operations
6. **Pagination**: Use pagination for large result sets

---

## Appendix: Database Schema

### Key Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `tracking_sessions` | Tracking sessions | session_uuid, status, total_videos, individuals_found |
| `individuals` | Detected individuals | individual_uuid, video_uuid, confidence_score |
| `mvr_people` | MVR canonical records | mvr_people_uuid, face_embedding, confidence_score |
| `individual_mvr_mapping` | Individual→MVR links | individual_uuid, mvr_people_uuid |
| `session_individuals` | Session→Individual links | session_uuid, individual_uuid, processing_type |
| `video_processing_states` | Video processing status | video_uuid, session_uuid, status |
| `individual_video_appearances` | Individual appearances | individual_uuid, video_uuid, timestamp |

### Indexes

| Index | Type | Purpose |
|-------|------|---------|
| `idx_mvr_people_embedding` | HNSW | Fast face similarity search |
| `idx_individuals_video_uuid` | B-tree | Video-based individual lookup |
| `idx_session_individuals_session` | B-tree | Session individual retrieval |
| `idx_tracking_sessions_config_hash` | B-tree | Session cache lookup |

---

## Document Status

**Status**: Complete and verified  
**Last Updated**: November 9, 2025  
**Endpoints Documented**: 31  
**Authentication**: Required for all endpoints except health checks  
**API Version**: v1  

**Changes**:
- 2025-11-09: Initial documentation created
- 2025-11-09: Added session-wide bulk cache details
- 2025-11-09: Documented three-level caching architecture

---

**For Implementation Details**: See `individual-and-mvr-caching-methods.md`  
**For API Code**: See `ppl-meta-vmeta/src/api/`  
**For Service Configuration**: See `ppl-meta-vmeta/src/config/settings.py`
