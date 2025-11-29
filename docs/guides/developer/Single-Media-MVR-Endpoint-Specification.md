# Single-Media MVR People Endpoint - Technical Specification

**Document Version**: 1.0  
**Date**: November 29, 2025  
**Service**: vmeta (Vector-based facial embeddings and analytics)  
**Feature**: Independent Media Processing (Photos & Videos)  
**Status**: Proposed Specification

---

## Table of Contents

1. [Overview](#overview)
2. [Key Differences from Cross-Video Tracking](#key-differences-from-cross-video-tracking)
3. [Endpoint Specification](#endpoint-specification)
4. [Request Structure](#request-structure)
5. [Response Structure](#response-structure)
6. [Processing Logic](#processing-logic)
7. [Photo-Specific Handling](#photo-specific-handling)
8. [Video-Specific Handling](#video-specific-handling)
9. [MVR People Data Structure](#mvr-people-data-structure)
10. [Error Handling](#error-handling)
11. [Implementation Guide](#implementation-guide)
12. [Testing Strategy](#testing-strategy)
13. [Use Cases](#use-cases)

---

## Overview

### Purpose

This endpoint provides **independent, per-media processing** of photos and videos to generate MVR people data objects. Unlike the existing cross-video tracking endpoints, this endpoint treats each media item in isolation—individuals detected in one media are never merged or correlated with individuals from other media in the same request.

### Core Principle

**Isolation Guarantee**: Each media UUID is processed independently. An MVR person created from Media A will **never** be merged with an MVR person from Media B, even if they represent the same physical person.

### Primary Use Cases

1. **Photo Gallery Analysis**: Process individual photos to detect and identify people without cross-photo correlation
2. **Single Video Processing**: Analyze a standalone video without reference to other recordings
3. **Real-Time Media Ingestion**: Process media as it arrives without waiting for batch operations
4. **Independent Media Libraries**: Maintain separate identity spaces for different media sources

---

## Key Differences from Cross-Video Tracking

| Feature | Cross-Video Tracking | Single-Media MVR (New) |
|---------|---------------------|------------------------|
| **Scope** | Multiple videos, collection-based | Individual media items (photos/videos) |
| **MVR Merging** | Across all media in session | Within single media only |
| **Face Matching** | Global similarity search | Per-media similarity only |
| **Route Data** | Multi-video trajectories | Single-media routes (or single point for photos) |
| **Session Concept** | Required tracking session | No session, stateless operation |
| **Caching** | Session-wide cache | No cross-media caching |
| **Use Case** | "Who appeared across camera network?" | "Who is in this specific photo/video?" |

### Architectural Comparison

**Cross-Video Tracking Flow:**
```
Videos → Session → Individual Detection → Global Matching → Cross-Video MVR People
         └─ Cache sessions across videos
```

**Single-Media MVR Flow (New):**
```
Media → Individual Detection → Per-Media Matching → Isolated MVR People
└─ No cross-media correlation
└─ Each media processed independently
```

---

## Endpoint Specification

### Endpoint Details

**Endpoint**: `POST /api/v1/mvr-people/process-media`

**Method**: `POST`

**Authentication**: Required (JWT Bearer token)

**Base URL**: `http://localhost:8008`

**Gateway Proxy**: `http://localhost:8080/api/v1/mvr-people/process-media`

### Path Parameters

None (all parameters in request body)

### Query Parameters

None (all parameters in request body)

---

## Request Structure

### Request Body Schema

```json
{
  "media_uuids": [
    "photo-uuid-1",
    "video-uuid-1",
    "photo-uuid-2"
  ],
  "processing_options": {
    "similarity_threshold": 0.85,
    "min_face_quality": 0.70,
    "include_demographics": true,
    "include_route_data": true,
    "async_processing": false
  },
  "response_format": {
    "include_embeddings": false,
    "include_face_crops": false,
    "aggregate_statistics": true
  }
}
```

### Parameter Definitions

#### `media_uuids` (required)
- **Type**: `Array<String>`
- **Description**: List of media UUIDs to process independently
- **Constraints**: 
  - Minimum: 1 media UUID
  - Maximum: 50 media UUIDs per request (prevent overload)
  - Each UUID must exist in Media service
- **Example**: `["56ebe3bc-6b40-4850-b57a-5068ed4ebda1", "7f1a2b3c-..."]`

#### `processing_options` (optional)
Configuration for detection and matching algorithms.

**Fields:**

- **`similarity_threshold`** (optional, default: `0.85`)
  - **Type**: `Float`
  - **Range**: `0.70` to `0.95`
  - **Description**: Minimum cosine similarity for matching faces **within the same media**
  - **Note**: Higher threshold = fewer MVR merges per media (more unique individuals)

- **`min_face_quality`** (optional, default: `0.70`)
  - **Type**: `Float`
  - **Range**: `0.50` to `0.95`
  - **Description**: Minimum quality score for face detection to be included
  - **Purpose**: Filter out blurry, occluded, or low-resolution faces

- **`include_demographics`** (optional, default: `true`)
  - **Type**: `Boolean`
  - **Description**: Whether to estimate age and gender for detected faces

- **`include_route_data`** (optional, default: `true`)
  - **Type**: `Boolean`
  - **Description**: Whether to include movement tracking data
  - **Note**: For photos, this will be a single point

- **`async_processing`** (optional, default: `false`)
  - **Type**: `Boolean`
  - **Description**: Process asynchronously in background (return immediately with job ID)

#### `response_format` (optional)
Control what data is included in the response.

**Fields:**

- **`include_embeddings`** (optional, default: `false`)
  - **Type**: `Boolean`
  - **Description**: Include 512-dimensional face embeddings in response
  - **Warning**: Large payload size (512 floats per face)

- **`include_face_crops`** (optional, default: `false`)
  - **Type**: `Boolean`
  - **Description**: Include base64-encoded face crop images
  - **Warning**: Very large payload size

- **`aggregate_statistics`** (optional, default: `true`)
  - **Type**: `Boolean`
  - **Description**: Include summary statistics across all processed media

---

## Response Structure

### Synchronous Response (async_processing: false)

```json
{
  "success": true,
  "total_media": 3,
  "processed_media": 3,
  "failed_media": 0,
  "processing_time_seconds": 4.23,
  "results": [
    {
      "media_uuid": "photo-uuid-1",
      "media_type": "photo",
      "status": "completed",
      "mvr_people": [
        {
          "mvr_people_uuid": "mvr-abc-123",
          "individual_uuids": ["ind-001", "ind-002"],
          "total_appearances": 2,
          "unique_videos": 1,
          "first_seen": "2025-11-29T10:15:00.000000",
          "last_seen": "2025-11-29T10:15:00.000000",
          "confidence_score": 0.92,
          "quality_score": 0.89,
          "demographics": {
            "gender": "Male",
            "gender_confidence": 0.87,
            "age_min": 30,
            "age_max": 40,
            "age_mean": 35.0,
            "age_confidence": 0.82
          },
          "appearances": [
            {
              "individual_uuid": "ind-001",
              "video_uuid": "photo-uuid-1",
              "person_object_uuid": "po-001",
              "start_timestamp": "2025-11-29T10:15:00.000000",
              "end_timestamp": "2025-11-29T10:15:00.000000",
              "confidence": 0.94
            }
          ],
          "route_data": {
            "route_points": [
              {
                "center_x": 640.5,
                "center_y": 480.2,
                "timestamp": 0.0,
                "frame_number": 0,
                "confidence": 0.94
              }
            ],
            "total_detections": 1,
            "movement_duration": 0.0
          }
        }
      ],
      "total_faces_detected": 5,
      "mvr_people_count": 2,
      "processing_time_ms": 1234
    },
    {
      "media_uuid": "video-uuid-1",
      "media_type": "video",
      "status": "completed",
      "mvr_people": [
        {
          "mvr_people_uuid": "mvr-def-456",
          "individual_uuids": ["ind-003", "ind-004", "ind-005"],
          "total_appearances": 3,
          "unique_videos": 1,
          "first_seen": "2025-11-29T10:20:15.000000",
          "last_seen": "2025-11-29T10:25:42.000000",
          "confidence_score": 0.91,
          "quality_score": 0.87,
          "demographics": {
            "gender": "Female",
            "gender_confidence": 0.89,
            "age_min": 25,
            "age_max": 35,
            "age_mean": 30.0,
            "age_confidence": 0.84
          },
          "appearances": [
            {
              "individual_uuid": "ind-003",
              "video_uuid": "video-uuid-1",
              "person_object_uuid": "po-002",
              "start_timestamp": "2025-11-29T10:20:15.000000",
              "end_timestamp": "2025-11-29T10:22:30.000000",
              "confidence": 0.93
            }
          ],
          "route_data": {
            "route_points": [
              {
                "center_x": 450.2,
                "center_y": 320.8,
                "timestamp": 13.333333,
                "frame_number": 400,
                "velocity_x": 0.012,
                "velocity_y": -0.008,
                "confidence": 0.93
              },
              {
                "center_x": 520.5,
                "center_y": 310.2,
                "timestamp": 26.666666,
                "frame_number": 800,
                "velocity_x": 0.015,
                "velocity_y": -0.005,
                "confidence": 0.91
              }
            ],
            "total_detections": 45,
            "sampled_points": 45,
            "movement_duration": 135.0,
            "average_velocity": 0.0234
          }
        }
      ],
      "total_faces_detected": 12,
      "mvr_people_count": 1,
      "processing_time_ms": 2890
    }
  ],
  "aggregate_statistics": {
    "total_mvr_people_created": 3,
    "total_individuals_detected": 17,
    "total_faces_detected": 17,
    "average_mvr_per_media": 1.0,
    "processing_breakdown": {
      "photos": {
        "count": 2,
        "total_mvr": 2,
        "avg_processing_ms": 1100
      },
      "videos": {
        "count": 1,
        "total_mvr": 1,
        "avg_processing_ms": 2890
      }
    }
  }
}
```

### Asynchronous Response (async_processing: true)

```json
{
  "success": true,
  "job_id": "job-xyz-789",
  "status": "processing",
  "message": "Media processing job created successfully",
  "total_media": 3,
  "estimated_completion_seconds": 10,
  "status_endpoint": "/api/v1/mvr-people/jobs/job-xyz-789/status",
  "created_at": "2025-11-29T10:30:00.000000"
}
```

**Status Polling Endpoint**: `GET /api/v1/mvr-people/jobs/{job_id}/status`

**Job Status Response**:
```json
{
  "job_id": "job-xyz-789",
  "status": "completed",
  "progress": 1.0,
  "processed_media": 3,
  "total_media": 3,
  "started_at": "2025-11-29T10:30:00.000000",
  "completed_at": "2025-11-29T10:30:10.123456",
  "results_endpoint": "/api/v1/mvr-people/jobs/job-xyz-789/results"
}
```

---

## Processing Logic

### High-Level Algorithm

```
FOR each media_uuid IN media_uuids:
  
  1. Fetch media metadata from Media Service
     - Determine media type (photo vs video)
     - Get resolution, duration, timestamp
  
  2. Fetch person objects from Orchestrator Service
     - GET /api/v1/orchestrator/person-objects/{media_uuid}
     - Extract face detections, bounding boxes, route points
  
  3. Generate face embeddings (if not already cached)
     - Extract face crops from person objects
     - Generate 512-dimensional Facenet512 embeddings
  
  4. Create individuals (one per person object)
     - Store in `individuals` table
     - Link to media_uuid
  
  5. Match faces WITHIN this media only
     - Compare embeddings using cosine similarity
     - Threshold: processing_options.similarity_threshold
     - Group similar faces into clusters
  
  6. Create MVR people (one per cluster)
     - Compute canonical embedding (quality-weighted average)
     - Estimate demographics (age, gender)
     - Store in `mvr_people` table with isolation flag
  
  7. Build route data
     - FOR photos: Single point at face center
     - FOR videos: Multi-point trajectory from route_points
  
  8. Return MVR people data in standard format

RETURN aggregated results for all media
```

### Detailed Processing Steps

#### Step 1: Media Metadata Fetch

**API Call**: `GET http://localhost:8000/api/v1/media/{media_uuid}`

**Extract**:
- `media_type`: "photo" or "video"
- `resolution`: Width x Height
- `duration`: Duration in seconds (0 for photos)
- `timestamp`: Media capture/creation timestamp
- `collection_id`: Source collection (optional)

#### Step 2: Person Objects Fetch

**API Call**: `GET http://localhost:8080/api/v1/orchestrator/person-objects/{media_uuid}`

**Extract**:
- `person_groups`: Array of detected person objects
- `faces`: Face detections with bounding boxes
- `route_points`: Movement tracking data (empty for photos)

#### Step 3: Face Embedding Generation

**For each face detection**:

```python
# Check if embedding already exists
existing_embedding = check_embedding_cache(person_object_uuid)

if existing_embedding:
    embedding = existing_embedding
else:
    # Extract face crop from video/photo
    face_crop = extract_face_crop(media, bounding_box)
    
    # Generate Facenet512 embedding
    embedding = facenet512_model.generate(face_crop)
    
    # Cache embedding
    store_embedding(person_object_uuid, embedding)

# Store individual record
individual_uuid = create_individual(
    video_uuid=media_uuid,
    person_object_uuid=person_object_uuid,
    face_embedding=embedding,
    confidence=detection_confidence
)
```

#### Step 4: Per-Media Face Matching

**Clustering Algorithm** (Agglomerative Clustering):

```python
# Get all individuals for THIS media only
individuals = get_individuals_for_media(media_uuid)

# Extract embeddings
embeddings = [ind.face_embedding for ind in individuals]

# Compute pairwise similarity matrix
similarity_matrix = cosine_similarity(embeddings, embeddings)

# Apply threshold
similarity_matrix[similarity_matrix < similarity_threshold] = 0

# Perform agglomerative clustering
clusters = agglomerative_cluster(
    similarity_matrix,
    threshold=similarity_threshold,
    linkage='average'
)

# Each cluster = one MVR person
for cluster in clusters:
    create_mvr_person(
        individual_uuids=cluster.individual_uuids,
        canonical_embedding=compute_weighted_average(cluster.embeddings),
        media_uuid=media_uuid,
        isolation_flag=True  # Mark as isolated (no cross-media merging)
    )
```

#### Step 5: MVR People Creation

**For each cluster**:

```python
# Compute canonical embedding (quality-weighted average)
canonical_embedding = sum(
    embedding * quality_score 
    for embedding, quality_score in cluster
) / sum(quality_scores)

# Estimate demographics
demographics = estimate_demographics(cluster.face_crops)

# Create MVR person record
mvr_person = create_mvr_person(
    face_embedding=canonical_embedding,
    confidence_score=avg_confidence(cluster),
    quality_score=avg_quality(cluster),
    gender=demographics.gender,
    age_min=demographics.age_min,
    age_max=demographics.age_max,
    is_isolated=True,  # CRITICAL: Marks this MVR as media-isolated
    source_media_uuid=media_uuid
)

# Link individuals to MVR person
for individual_uuid in cluster.individual_uuids:
    link_individual_to_mvr(individual_uuid, mvr_person.uuid)
```

#### Step 6: Route Data Assembly

**See [Photo-Specific Handling](#photo-specific-handling) and [Video-Specific Handling](#video-specific-handling) below.**

---

## Photo-Specific Handling

### Route Data for Photos

Since photos are **single-frame captures**, route data consists of a **single point** at the face center.

### Route Point Structure (Photo)

```json
{
  "route_points": [
    {
      "center_x": 640.5,
      "center_y": 480.2,
      "timestamp": 0.0,
      "frame_number": 0,
      "velocity_x": 0.0,
      "velocity_y": 0.0,
      "confidence": 0.94
    }
  ],
  "total_detections": 1,
  "sampled_points": 1,
  "movement_duration": 0.0,
  "average_velocity": 0.0
}
```

### Field Definitions (Photo)

- **`center_x`**: X-coordinate of face bounding box center (pixels)
- **`center_y`**: Y-coordinate of face bounding box center (pixels)
- **`timestamp`**: Always `0.0` for photos (no temporal dimension)
- **`frame_number`**: Always `0` for photos
- **`velocity_x`**: Always `0.0` for photos (no movement)
- **`velocity_y`**: Always `0.0` for photos (no movement)
- **`confidence`**: Face detection confidence score
- **`total_detections`**: Always `1` for photos
- **`movement_duration`**: Always `0.0` for photos
- **`average_velocity`**: Always `0.0` for photos

### Photo Processing Example

**Input Photo**: `photo-uuid-1` (1920x1080 resolution)

**Person Objects Response**:
```json
{
  "success": true,
  "person_groups": [
    {
      "person_id": "person-1",
      "faces": [
        {
          "bbox": [450, 300, 120, 160],
          "confidence": 0.94
        }
      ]
    }
  ]
}
```

**Route Data Generation**:
```python
# Calculate face center from bounding box
bbox = [450, 300, 120, 160]  # [x, y, width, height]
center_x = bbox[0] + bbox[2] / 2  # 450 + 60 = 510
center_y = bbox[1] + bbox[3] / 2  # 300 + 80 = 380

# Create single route point
route_point = {
    "center_x": 510.0,
    "center_y": 380.0,
    "timestamp": 0.0,
    "frame_number": 0,
    "velocity_x": 0.0,
    "velocity_y": 0.0,
    "confidence": 0.94
}

# Wrap in route data structure
route_data = {
    "route_points": [route_point],
    "total_detections": 1,
    "sampled_points": 1,
    "movement_duration": 0.0,
    "average_velocity": 0.0
}
```

### Photo MVR Response

```json
{
  "media_uuid": "photo-uuid-1",
  "media_type": "photo",
  "status": "completed",
  "mvr_people": [
    {
      "mvr_people_uuid": "mvr-photo-123",
      "individual_uuids": ["ind-photo-001"],
      "total_appearances": 1,
      "unique_videos": 1,
      "first_seen": "2025-11-29T10:15:00.000000",
      "last_seen": "2025-11-29T10:15:00.000000",
      "route_data": {
        "route_points": [
          {
            "center_x": 510.0,
            "center_y": 380.0,
            "timestamp": 0.0,
            "frame_number": 0,
            "velocity_x": 0.0,
            "velocity_y": 0.0,
            "confidence": 0.94
          }
        ],
        "total_detections": 1,
        "movement_duration": 0.0,
        "average_velocity": 0.0
      }
    }
  ]
}
```

---

## Video-Specific Handling

### Route Data for Videos

Videos contain **temporal movement tracking** with multiple route points captured over the video duration.

### Route Point Structure (Video)

```json
{
  "route_points": [
    {
      "center_x": 450.2,
      "center_y": 320.8,
      "timestamp": 13.333333,
      "frame_number": 400,
      "velocity_x": 0.012,
      "velocity_y": -0.008,
      "confidence": 0.93
    },
    {
      "center_x": 520.5,
      "center_y": 310.2,
      "timestamp": 26.666666,
      "frame_number": 800,
      "velocity_x": 0.015,
      "velocity_y": -0.005,
      "confidence": 0.91
    }
  ],
  "total_detections": 45,
  "sampled_points": 45,
  "movement_duration": 135.0,
  "average_velocity": 0.0234
}
```

### Field Definitions (Video)

- **`center_x`**: X-coordinate of person center (pixels)
- **`center_y`**: Y-coordinate of person center (pixels)
- **`timestamp`**: Seconds from video start (float)
- **`frame_number`**: Frame index in video
- **`velocity_x`**: Normalized horizontal velocity (px/s)
- **`velocity_y`**: Normalized vertical velocity (px/s)
- **`confidence`**: Detection confidence at this frame
- **`total_detections`**: Total route points before sampling
- **`sampled_points`**: Route points after sampling (if applied)
- **`movement_duration`**: Duration from first to last detection (seconds)
- **`average_velocity`**: Average movement speed (normalized px/s)

### Route Sampling (Video)

**Applies when**: `total_detections > 100` (configurable threshold)

**Algorithm**: Uniform interval sampling with endpoint preservation

```python
if len(route_points) > 100:
    interval = ceil(len(route_points) / 100)
    sampled = []
    
    # Always include first point
    sampled.append(route_points[0])
    
    # Sample intermediate points
    for i in range(interval, len(route_points) - 1, interval):
        sampled.append(route_points[i])
    
    # Always include last point
    sampled.append(route_points[-1])
    
    route_points = sampled
```

### Velocity Calculation (Video)

**Backend calculates normalized velocity** between consecutive route points:

```python
width, height = 1920, 1080
velocities = []

for i in range(1, len(route_points)):
    prev = route_points[i-1]
    curr = route_points[i]
    
    # Normalize coordinates
    x1_norm = prev['center_x'] / width
    y1_norm = prev['center_y'] / height
    x2_norm = curr['center_x'] / width
    y2_norm = curr['center_y'] / height
    
    # Calculate distance
    dx = x2_norm - x1_norm
    dy = y2_norm - y1_norm
    distance_normalized = (dx**2 + dy**2)**0.5
    
    # Time difference
    time_diff = curr['timestamp'] - prev['timestamp']
    
    if time_diff > 0:
        velocity = distance_normalized / time_diff
        velocities.append(velocity)

average_velocity = sum(velocities) / len(velocities)
```

### Video Processing Example

**Input Video**: `video-uuid-1` (1920x1080, 45 seconds duration)

**Person Objects Response**:
```json
{
  "success": true,
  "person_groups": [
    {
      "person_id": "person-1",
      "movement_tracking": {
        "route_points": [
          {
            "center_x": 450.2,
            "center_y": 320.8,
            "timestamp": 13.333333,
            "frame_number": 400,
            "confidence": 0.93
          },
          // ... 43 more points
        ]
      }
    }
  ]
}
```

**Route Data Generation**:
```python
# Fetch route points from orchestrator
route_points = person_group['movement_tracking']['route_points']

# Calculate velocity between consecutive points
velocities = calculate_velocities(route_points)
average_velocity = mean(velocities)

# Apply sampling if needed
if len(route_points) > 100:
    route_points = sample_route_points(route_points, threshold=100)

# Calculate duration
first_timestamp = route_points[0]['timestamp']
last_timestamp = route_points[-1]['timestamp']
movement_duration = last_timestamp - first_timestamp

# Build route data structure
route_data = {
    "route_points": route_points,
    "total_detections": len(original_route_points),
    "sampled_points": len(route_points),
    "movement_duration": movement_duration,
    "average_velocity": average_velocity
}
```

---

## MVR People Data Structure

### Standard MVR Person Object

This endpoint returns MVR people in the **same structure** as existing VMeta endpoints (e.g., `/api/v1/mvr-people/mvr-person/{uuid}/analysis`).

```json
{
  "mvr_people_uuid": "mvr-abc-123",
  "individual_uuids": ["ind-001", "ind-002"],
  "total_appearances": 2,
  "unique_videos": 1,
  "first_seen": "2025-11-29T10:15:00.000000",
  "last_seen": "2025-11-29T10:15:00.000000",
  "confidence_score": 0.92,
  "quality_score": 0.89,
  "average_route_velocity": 0.0234,
  "demographics": {
    "gender": "Male",
    "gender_confidence": 0.87,
    "age_min": 30,
    "age_max": 40,
    "age_mean": 35.0,
    "age_confidence": 0.82
  },
  "appearances": [
    {
      "individual_uuid": "ind-001",
      "video_uuid": "photo-uuid-1",
      "person_object_uuid": "po-001",
      "start_timestamp": "2025-11-29T10:15:00.000000",
      "end_timestamp": "2025-11-29T10:15:00.000000",
      "confidence": 0.94
    }
  ],
  "route_data": {
    "route_points": [...],
    "total_detections": 45,
    "sampled_points": 45,
    "movement_duration": 135.0,
    "average_velocity": 0.0234
  },
  "face_embedding_available": true,
  "embedding_model": "Facenet512",
  "is_isolated": true,
  "source_media_uuid": "video-uuid-1"
}
```

### New Fields (Endpoint-Specific)

#### `is_isolated` (Boolean)
- **Description**: Marks this MVR person as **isolated** (not merged across media)
- **Value**: Always `true` for MVR people from this endpoint
- **Purpose**: Prevents future cross-media merging operations from including this MVR

#### `source_media_uuid` (String)
- **Description**: UUID of the single media (photo/video) this MVR was created from
- **Value**: One of the `media_uuids` from the request
- **Purpose**: Track which media produced this MVR

### Demographics Structure

```json
{
  "gender": "Male" | "Female" | null,
  "gender_confidence": 0.87,
  "age_min": 30,
  "age_max": 40,
  "age_mean": 35.0,
  "age_confidence": 0.82
}
```

**Estimation Method**:
- Gender: CNN-based classification from face crops
- Age: Regression model estimating age range
- Confidence: Model prediction confidence score

### Appearances Array

Each appearance represents a detection of this MVR person in the source media.

```json
{
  "individual_uuid": "ind-001",
  "video_uuid": "photo-uuid-1",
  "person_object_uuid": "po-001",
  "start_timestamp": "2025-11-29T10:15:00.000000",
  "end_timestamp": "2025-11-29T10:15:00.000000",
  "confidence": 0.94
}
```

**For Photos**:
- `start_timestamp` = `end_timestamp` (single frame)
- One appearance per face detected in photo

**For Videos**:
- `start_timestamp` = First detection frame timestamp
- `end_timestamp` = Last detection frame timestamp
- One appearance per continuous detection sequence

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "MEDIA_NOT_FOUND",
    "message": "Media UUID not found: photo-uuid-1",
    "details": {
      "media_uuid": "photo-uuid-1",
      "checked_service": "media"
    },
    "timestamp": "2025-11-29T10:30:00.000000",
    "request_id": "req-xyz-789"
  }
}
```

### Error Codes

| Code | HTTP Status | Description | Resolution |
|------|-------------|-------------|------------|
| `MEDIA_NOT_FOUND` | 404 | Media UUID doesn't exist in Media service | Verify UUID with Media service |
| `PERSON_OBJECTS_NOT_FOUND` | 404 | No person objects for media | Media not processed by Vision service |
| `NO_FACES_DETECTED` | 200 | No faces detected in media | Valid response, return empty MVR array |
| `EMBEDDING_GENERATION_FAILED` | 500 | Face embedding generation error | Check ML model availability |
| `INVALID_MEDIA_TYPE` | 400 | Unsupported media type | Only photos and videos supported |
| `MEDIA_LIMIT_EXCEEDED` | 400 | Too many media UUIDs (>50) | Split into multiple requests |
| `PROCESSING_TIMEOUT` | 504 | Processing exceeded timeout | Use async mode or reduce media count |
| `INVALID_THRESHOLD` | 400 | similarity_threshold out of range | Use value between 0.70 and 0.95 |

### Partial Failure Handling

If some media fail while others succeed:

```json
{
  "success": true,
  "total_media": 5,
  "processed_media": 3,
  "failed_media": 2,
  "results": [
    {
      "media_uuid": "photo-1",
      "status": "completed",
      "mvr_people": [...]
    },
    {
      "media_uuid": "video-1",
      "status": "failed",
      "error": {
        "code": "PERSON_OBJECTS_NOT_FOUND",
        "message": "No person objects available"
      }
    }
  ]
}
```

### Timeout Configuration

- **Synchronous timeout**: 30 seconds (configurable)
- **Async timeout**: 5 minutes (configurable)
- **Per-media timeout**: 10 seconds (configurable)

**Recommendation**: Use `async_processing: true` for >10 media or videos >1 minute.

---

## Implementation Guide

### Backend Implementation (Python/FastAPI)

**File**: `ppl-meta-vmeta/src/api/routes/mvr_people.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import asyncio

router = APIRouter()

@router.post(
    "/process-media",
    summary="Process Media Independently for MVR People",
    description=(
        "Processes photos and videos independently to generate MVR people. "
        "Each media is processed in isolation—no cross-media merging. "
        "Photos produce single-point route data, videos produce multi-point routes."
    ),
)
async def process_media_independently(
    request: ProcessMediaRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Process media (photos/videos) independently for MVR people creation.
    
    Key behaviors:
    - No cross-media merging (each media processed in isolation)
    - Photos: Single-point route data
    - Videos: Multi-point route data with velocity calculation
    - Returns MVR people in standard format
    """
    logger.info(
        f"Processing {len(request.media_uuids)} media independently "
        f"(user: {current_user.get('email')})"
    )
    
    # Validate request
    if len(request.media_uuids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 media UUIDs per request"
        )
    
    # Async processing mode
    if request.processing_options.async_processing:
        job_id = create_background_job(request, current_user)
        return {
            "success": True,
            "job_id": job_id,
            "status": "processing",
            "total_media": len(request.media_uuids),
            "status_endpoint": f"/api/v1/mvr-people/jobs/{job_id}/status"
        }
    
    # Synchronous processing
    results = []
    for media_uuid in request.media_uuids:
        try:
            result = await process_single_media(
                media_uuid=media_uuid,
                options=request.processing_options,
                mvr_repository=mvr_repository
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing media {media_uuid}: {e}")
            results.append({
                "media_uuid": media_uuid,
                "status": "failed",
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": str(e)
                }
            })
    
    # Calculate aggregate statistics
    aggregate_stats = calculate_aggregate_statistics(results)
    
    return {
        "success": True,
        "total_media": len(request.media_uuids),
        "processed_media": sum(1 for r in results if r.get("status") == "completed"),
        "failed_media": sum(1 for r in results if r.get("status") == "failed"),
        "results": results,
        "aggregate_statistics": aggregate_stats
    }


async def process_single_media(
    media_uuid: str,
    options: ProcessingOptions,
    mvr_repository: MVRRepository
) -> dict:
    """
    Process a single media (photo or video) to generate MVR people.
    
    Returns MVR people data in standard format with isolation flag.
    """
    import time
    start_time = time.time()
    
    # 1. Fetch media metadata
    media_metadata = await fetch_media_metadata(media_uuid)
    media_type = media_metadata['type']  # 'photo' or 'video'
    
    # 2. Fetch person objects from orchestrator
    person_objects = await fetch_person_objects(media_uuid)
    
    if not person_objects:
        return {
            "media_uuid": media_uuid,
            "media_type": media_type,
            "status": "completed",
            "mvr_people": [],
            "total_faces_detected": 0,
            "mvr_people_count": 0
        }
    
    # 3. Create individuals from person objects
    individuals = []
    for person_obj in person_objects:
        # Generate face embedding if not cached
        embedding = await get_or_generate_embedding(
            person_obj['person_object_uuid']
        )
        
        # Create individual record
        individual = await create_individual_record(
            video_uuid=media_uuid,
            person_object_uuid=person_obj['person_object_uuid'],
            face_embedding=embedding,
            confidence=person_obj['confidence']
        )
        individuals.append(individual)
    
    # 4. Match faces WITHIN this media only
    clusters = perform_clustering(
        individuals=individuals,
        threshold=options.similarity_threshold
    )
    
    # 5. Create MVR people (one per cluster)
    mvr_people = []
    for cluster in clusters:
        # Compute canonical embedding
        canonical_embedding = compute_weighted_average_embedding(
            cluster.embeddings,
            cluster.quality_scores
        )
        
        # Estimate demographics
        demographics = None
        if options.include_demographics:
            demographics = estimate_demographics(cluster.face_crops)
        
        # Create MVR person record
        mvr_person_uuid = await create_mvr_person_record(
            face_embedding=canonical_embedding,
            confidence_score=cluster.avg_confidence,
            quality_score=cluster.avg_quality,
            demographics=demographics,
            is_isolated=True,  # CRITICAL: Mark as isolated
            source_media_uuid=media_uuid
        )
        
        # Link individuals to MVR person
        for individual_uuid in cluster.individual_uuids:
            await link_individual_to_mvr(individual_uuid, mvr_person_uuid)
        
        # Build route data
        route_data = await build_route_data(
            media_uuid=media_uuid,
            media_type=media_type,
            individual_uuids=cluster.individual_uuids,
            include_route=options.include_route_data
        )
        
        # Fetch appearances
        appearances = await fetch_appearances(cluster.individual_uuids)
        
        # Build MVR person object
        mvr_person = {
            "mvr_people_uuid": mvr_person_uuid,
            "individual_uuids": cluster.individual_uuids,
            "total_appearances": len(appearances),
            "unique_videos": 1,  # Always 1 for single-media processing
            "first_seen": min(app['start_timestamp'] for app in appearances),
            "last_seen": max(app['end_timestamp'] for app in appearances),
            "confidence_score": cluster.avg_confidence,
            "quality_score": cluster.avg_quality,
            "average_route_velocity": route_data.get('average_velocity', 0.0),
            "demographics": demographics,
            "appearances": appearances,
            "route_data": route_data,
            "is_isolated": True,
            "source_media_uuid": media_uuid
        }
        
        mvr_people.append(mvr_person)
    
    processing_time = time.time() - start_time
    
    return {
        "media_uuid": media_uuid,
        "media_type": media_type,
        "status": "completed",
        "mvr_people": mvr_people,
        "total_faces_detected": len(individuals),
        "mvr_people_count": len(mvr_people),
        "processing_time_ms": int(processing_time * 1000)
    }


async def build_route_data(
    media_uuid: str,
    media_type: str,
    individual_uuids: List[str],
    include_route: bool
) -> dict:
    """
    Build route data for MVR person.
    
    For photos: Single point at face center
    For videos: Multi-point trajectory with velocity
    """
    if not include_route:
        return {}
    
    if media_type == 'photo':
        # Fetch face bounding box
        individual = await fetch_individual(individual_uuids[0])
        person_object = await fetch_person_object(individual['person_object_uuid'])
        
        # Calculate face center
        bbox = person_object['bbox']  # [x, y, width, height]
        center_x = bbox[0] + bbox[2] / 2
        center_y = bbox[1] + bbox[3] / 2
        
        return {
            "route_points": [
                {
                    "center_x": center_x,
                    "center_y": center_y,
                    "timestamp": 0.0,
                    "frame_number": 0,
                    "velocity_x": 0.0,
                    "velocity_y": 0.0,
                    "confidence": person_object['confidence']
                }
            ],
            "total_detections": 1,
            "sampled_points": 1,
            "movement_duration": 0.0,
            "average_velocity": 0.0
        }
    
    else:  # video
        # Fetch route points from orchestrator
        gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
        response = await httpx_client.get(
            f"{gateway_url}/api/v1/orchestrator/person-objects/{media_uuid}"
        )
        
        person_groups = response.json()['person_groups']
        
        # Find person group matching our individuals
        # (Implementation depends on person_object_uuid matching)
        route_points = extract_route_points(person_groups, individual_uuids)
        
        # Calculate velocity
        velocities = calculate_velocities(route_points)
        average_velocity = sum(velocities) / len(velocities) if velocities else 0.0
        
        # Apply sampling if needed
        total_detections = len(route_points)
        if total_detections > 100:
            route_points = sample_route_points(route_points, threshold=100)
        
        # Calculate duration
        movement_duration = (
            route_points[-1]['timestamp'] - route_points[0]['timestamp']
            if len(route_points) > 1 else 0.0
        )
        
        return {
            "route_points": route_points,
            "total_detections": total_detections,
            "sampled_points": len(route_points),
            "movement_duration": movement_duration,
            "average_velocity": average_velocity
        }
```

### Database Schema Additions

**Table**: `mvr_people`

**New Columns**:

```sql
ALTER TABLE mvr_people 
ADD COLUMN is_isolated BOOLEAN DEFAULT FALSE,
ADD COLUMN source_media_uuid UUID,
ADD CONSTRAINT fk_source_media FOREIGN KEY (source_media_uuid) 
    REFERENCES videos(uuid) ON DELETE SET NULL;

CREATE INDEX idx_mvr_people_isolated ON mvr_people(is_isolated);
CREATE INDEX idx_mvr_people_source_media ON mvr_people(source_media_uuid);
```

**Purpose**:
- `is_isolated`: Prevents future cross-media merging operations from including this MVR
- `source_media_uuid`: Track which media produced this MVR (for auditing and filtering)

---

## Testing Strategy

### Unit Tests

**Test File**: `tests/test_process_media_endpoint.py`

```python
import pytest

@pytest.mark.asyncio
async def test_process_single_photo():
    """Test processing a single photo."""
    response = await client.post(
        "/api/v1/mvr-people/process-media",
        json={
            "media_uuids": ["photo-test-1"],
            "processing_options": {"similarity_threshold": 0.85}
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_media"] == 1
    assert data["processed_media"] == 1
    
    # Verify photo-specific behavior
    result = data["results"][0]
    assert result["media_type"] == "photo"
    assert len(result["mvr_people"]) > 0
    
    # Verify single-point route data
    mvr = result["mvr_people"][0]
    route_data = mvr["route_data"]
    assert len(route_data["route_points"]) == 1
    assert route_data["route_points"][0]["timestamp"] == 0.0
    assert route_data["movement_duration"] == 0.0
    assert route_data["average_velocity"] == 0.0


@pytest.mark.asyncio
async def test_process_single_video():
    """Test processing a single video."""
    response = await client.post(
        "/api/v1/mvr-people/process-media",
        json={
            "media_uuids": ["video-test-1"],
            "processing_options": {"include_route_data": True}
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify video-specific behavior
    result = data["results"][0]
    assert result["media_type"] == "video"
    
    # Verify multi-point route data
    mvr = result["mvr_people"][0]
    route_data = mvr["route_data"]
    assert len(route_data["route_points"]) > 1
    assert route_data["movement_duration"] > 0.0
    assert route_data["average_velocity"] > 0.0


@pytest.mark.asyncio
async def test_no_cross_media_merging():
    """Verify MVR people are NOT merged across media."""
    # Process two media with the same person
    response = await client.post(
        "/api/v1/mvr-people/process-media",
        json={
            "media_uuids": ["photo-same-person-1", "photo-same-person-2"],
            "processing_options": {"similarity_threshold": 0.85}
        },
        headers=auth_headers
    )
    
    data = response.json()
    
    # Extract all MVR UUIDs
    mvr_uuids = set()
    for result in data["results"]:
        for mvr in result["mvr_people"]:
            mvr_uuids.add(mvr["mvr_people_uuid"])
    
    # Verify no duplicate MVR UUIDs (no cross-media merging)
    assert len(mvr_uuids) == sum(
        len(result["mvr_people"]) for result in data["results"]
    )
    
    # Verify is_isolated flag
    for result in data["results"]:
        for mvr in result["mvr_people"]:
            assert mvr["is_isolated"] is True
            assert mvr["source_media_uuid"] in ["photo-same-person-1", "photo-same-person-2"]


@pytest.mark.asyncio
async def test_async_processing():
    """Test asynchronous processing mode."""
    response = await client.post(
        "/api/v1/mvr-people/process-media",
        json={
            "media_uuids": ["video-1", "video-2", "video-3"],
            "processing_options": {"async_processing": True}
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    
    # Poll job status
    job_id = data["job_id"]
    for _ in range(30):  # 30 second timeout
        status_response = await client.get(
            f"/api/v1/mvr-people/jobs/{job_id}/status",
            headers=auth_headers
        )
        status_data = status_response.json()
        
        if status_data["status"] == "completed":
            break
        
        await asyncio.sleep(1)
    
    assert status_data["status"] == "completed"
    assert status_data["processed_media"] == 3
```

### Integration Tests

**Test Scenarios**:

1. **End-to-End Photo Processing**
   - Upload photo to Media service
   - Process with Vision service
   - Call new endpoint
   - Verify MVR created with single-point route

2. **End-to-End Video Processing**
   - Upload video to Media service
   - Process with Vision service
   - Call new endpoint
   - Verify MVR created with multi-point route and velocity

3. **Mixed Media Batch**
   - Process 5 photos + 3 videos in single request
   - Verify isolation (no cross-media MVR merging)
   - Verify correct route data types

4. **Error Handling**
   - Invalid media UUID → 404 error
   - Unprocessed media → Empty MVR array
   - Timeout → Async mode fallback

---

## Use Cases

### Use Case 1: Photo Gallery Person Detection

**Scenario**: User uploads 50 photos from an event to analyze who attended.

**Request**:
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_uuids": ["photo-1", "photo-2", ..., "photo-50"],
    "processing_options": {
      "similarity_threshold": 0.85,
      "include_demographics": true,
      "async_processing": true
    }
  }'
```

**Result**:
- Each photo processed independently
- MVR people identified within each photo (not across photos)
- Demographics estimated for each detected person
- Single-point route data for each face

**Frontend Display**:
- Gallery view showing photos
- Overlay with detected faces and demographics
- Click face → Show MVR details for that photo only

---

### Use Case 2: Security Footage Analysis

**Scenario**: Analyze security camera footage to identify individuals in each video clip independently.

**Request**:
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_uuids": ["camera-1-clip-1", "camera-1-clip-2", "camera-2-clip-1"],
    "processing_options": {
      "similarity_threshold": 0.80,
      "include_route_data": true,
      "min_face_quality": 0.75
    }
  }'
```

**Result**:
- Each video clip analyzed separately
- Movement tracking within each clip
- Velocity calculation for each detected person
- No cross-clip person correlation

**Use Case**: Identify suspicious behavior patterns within individual clips without triggering cross-clip identity matching.

---

### Use Case 3: Real-Time Media Ingestion

**Scenario**: Process incoming media in real-time as it's uploaded/captured.

**Workflow**:
1. Media uploaded to Media service
2. Vision service processes for person detection
3. Webhook triggers VMeta endpoint with single media UUID
4. MVR people created immediately for that media

**Request** (per media):
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_uuids": ["newly-uploaded-video-1"],
    "processing_options": {
      "async_processing": false
    }
  }'
```

**Result**:
- Immediate MVR creation (no batching delay)
- Independent processing (no waiting for other media)
- Fast response (<5 seconds for typical video)

---

### Use Case 4: Isolated Media Collections

**Scenario**: Maintain separate identity spaces for different projects/collections.

**Example**: University has two projects:
- Project A: Campus security footage
- Project B: Event photography

**Requirement**: People detected in Project A should **never** be matched with people in Project B, even if it's the same physical person.

**Solution**: Use this endpoint for each project separately. The `is_isolated` flag ensures MVR people from different projects never merge.

**Request Project A**:
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -d '{"media_uuids": ["project-a-video-1", "project-a-video-2"]}'
```

**Request Project B**:
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -d '{"media_uuids": ["project-b-photo-1", "project-b-photo-2"]}'
```

**Result**: Complete isolation between projects, even if same person appears in both.

---

## Summary

### Key Features

✅ **Independent Processing**: Each media processed in isolation, no cross-media correlation

✅ **Photo Support**: Single-point route data for photos (timestamp = 0.0)

✅ **Video Support**: Multi-point route data with velocity calculation and sampling

✅ **Standard Format**: Returns MVR people in same structure as existing endpoints

✅ **Isolation Flag**: `is_isolated` field prevents future cross-media merging

✅ **Async Support**: Background processing for large batches

✅ **Demographics**: Age and gender estimation included

✅ **Error Handling**: Partial failure support, detailed error codes

### Architectural Benefits

1. **No Session Overhead**: Stateless operation, no tracking session required
2. **Real-Time Capable**: Process media immediately upon arrival
3. **Scalable**: Each media processed independently (easy parallelization)
4. **Flexible**: Works with photos and videos seamlessly
5. **Standard Output**: Reuses existing MVR data structure (UI compatibility)

### Implementation Checklist

- [ ] Backend endpoint implementation (`/api/v1/mvr-people/process-media`)
- [ ] Database schema updates (`is_isolated`, `source_media_uuid` columns)
- [ ] Photo route data handler (single-point generation)
- [ ] Video route data handler (multi-point with velocity)
- [ ] Async processing job queue
- [ ] Error handling and validation
- [ ] Unit tests (photo, video, mixed batch)
- [ ] Integration tests (end-to-end)
- [ ] API documentation update
- [ ] Frontend integration (optional)

---

## Related Documentation

- **Existing VMeta Endpoints**: [vmeta-api-endpoints.md](../../../ppl-meta-vmeta/docs/vmeta-api-endpoints.md)
- **Cross-Video Tracking**: [Cross-Video Individual Analysis](./Cross-Video-Individual-Analysis.md)
- **Route Sampling**: [Route Sample Rendering](./route-sample-rendering.md)
- **MVR People Architecture**: [MVR People Search Implementation](../../vision-vmeta/MVR_PEOPLE_SEARCH_IMPLEMENTATION.md)

---

**Document Status**: ✅ Complete Specification  
**Version**: 1.0  
**Author**: GitHub Copilot (Claude Sonnet 4.5)  
**Date**: November 29, 2025  
**Next Steps**: Backend implementation and testing
