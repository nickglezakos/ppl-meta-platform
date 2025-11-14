# PPL Meta Orchestrator Service - API Documentation

**Version:** 1.0.0 (Phase 1-2.4)  
**Service:** ppl-meta-orchestrator  
**Port:** 8002  
**Base URL:** `http://localhost:8002`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [Health & Status](#health--status)
   - [Camera Workflows](#camera-workflows)
   - [Face Detection Workflows](#face-detection-workflows)
   - [Person Objects (PPL Thread)](#person-objects-ppl-thread)
   - [Recording Sessions](#recording-sessions)
   - [Session Management](#session-management)
   - [Master Lifecycle Workflows](#master-lifecycle-workflows)
   - [Camera Automation](#camera-automation)
   - [Camera Events](#camera-events)
   - [Method Lifecycle](#method-lifecycle)
   - [Automation Rules](#automation-rules)
4. [Data Models](#data-models)
5. [Workflow Architecture](#workflow-architecture)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

---

## Overview

The PPL Meta Orchestrator Service is the central coordination hub for the PPL Meta platform, responsible for:

- **Workflow Orchestration**: Coordinates multi-service workflows across Camera, Media, and Vision services
- **Face Detection**: Manages bulk face detection workflows with session tracking
- **Camera Automation**: Automates camera recording and processing workflows
- **Event Management**: Publishes and handles camera events (motion detection, recording start/stop)
- **Recording Sessions**: Tracks and manages camera recording sessions with database persistence
- **Method Lifecycle**: Manages detection method lifecycles per camera
- **Automation Rules**: Executes conditional automation rules based on triggers

### Key Features

- Multi-phase architecture (Phase 1-2.4)
- Service discovery and health monitoring
- Traceability and audit logging
- Self-referencing architecture for face detection
- Real-time event publishing and webhook support
- Database-backed session persistence
- Flexible automation engine
- Comprehensive analytics and monitoring

### Service Dependencies

- **Camera Service** (port 8005): Camera management and video recordings
- **Media Service** (port 8000): Media storage and retrieval
- **Vision Service** (port 8003): Face detection and recognition
- **VMeta Service** (port 8008): Cross-video tracking and MVR-People

---

## Authentication

All endpoints (except health checks and root) require JWT authentication.

### Authentication Header

```http
Authorization: Bearer <jwt_token>
```

### Token Usage

The orchestrator validates tokens and forwards them to downstream services.

**Example:**

```bash
curl -X POST http://localhost:8002/workflows/face-detection/bulk-process \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"media_ids": ["uuid1", "uuid2"]}'
```

---

## API Endpoints

### Health & Status

#### 1. Health Check

**GET** `/health`

Get comprehensive health status with component information.

**Response:**
```json
{
  "status": "healthy",
  "service": "ppl-meta-orchestrator",
  "version": "1.0.0-phase1-2.4",
  "environment": "development",
  "phase": "1-2.4",
  "capabilities": [
    "orchestration",
    "camera_automation",
    "camera_event_publishing",
    "method_lifecycle_management",
    "automation_engine",
    "face_detection_workflows",
    "traceability"
  ],
  "service_connections": {
    "camera": true,
    "media": true,
    "vision": true
  },
  "workflow_orchestrator": {
    "active_workflows": 3,
    "historical_workflows": 47
  }
}
```

**Example:**
```bash
curl http://localhost:8002/health
```

---

#### 2. Root Endpoint

**GET** `/`

Get service information and available endpoints.

**Response:**
```json
{
  "message": "PPL Meta Orchestrator Service - Phase 1",
  "status": "running",
  "version": "1.0.0-phase1",
  "phase": "1",
  "description": "Orchestrator with Camera Integration and Workflow Management",
  "endpoints": {
    "health": "/health",
    "workflows": "/workflows/*",
    "camera_events": "/workflows/camera/events",
    "bulk_processing": "/workflows/face-detection/bulk-process",
    "analytics": "/workflows/analytics"
  }
}
```

---

### Camera Workflows

#### 3. Camera Event Handler

**POST** `/workflows/camera/events`

Process camera storage events and trigger face detection workflows.

**Request Body:**
```json
{
  "event_type": "video_stored",
  "camera_device_id": "cam-001",
  "video_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "filepath": "/storage/videos/cam-001/recording.mp4",
  "timestamp": "2025-11-12T10:30:00Z",
  "metadata": {
    "duration": 120,
    "size": 15728640
  }
}
```

**Response:**
```json
{
  "success": true,
  "workflow_id": "wf-abc123",
  "message": "Face detection workflow initiated",
  "event_type": "video_stored",
  "camera_device_id": "cam-001",
  "processing_started": true
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/workflows/camera/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "video_stored",
    "camera_device_id": "cam-001",
    "video_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "filepath": "/storage/videos/cam-001/recording.mp4"
  }'
```

---

#### 4. Bulk Face Detection Processing

**POST** `/workflows/face-detection/bulk-process`

Start bulk face detection workflow for multiple media items.

**Request Body:**
```json
{
  "media_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "methods": ["two_stage", "enhanced_v2"],
  "processing_options": {
    "confidence_threshold": 0.5,
    "store_results": true
  },
  "priority": "normal"
}
```

**Response:**
```json
{
  "workflow_id": "wf-bulk-123",
  "status": "initiated",
  "media_count": 2,
  "estimated_completion": "2025-11-12T10:35:00Z",
  "message": "Bulk processing workflow started"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/workflows/face-detection/bulk-process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "media_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "methods": ["two_stage"]
  }'
```

---

#### 5. Get Workflow Status

**GET** `/workflows/face-detection/status/{workflow_id}`

Get the current status of a workflow.

**Path Parameters:**
- `workflow_id`: Workflow UUID

**Response:**
```json
{
  "workflow_id": "wf-bulk-123",
  "status": "processing",
  "progress": 0.65,
  "completed_items": 13,
  "total_items": 20,
  "current_item": "660e8400-e29b-41d4-a716-446655440001",
  "started_at": "2025-11-12T10:30:00Z",
  "estimated_completion": "2025-11-12T10:35:00Z"
}
```

**Example:**
```bash
curl http://localhost:8002/workflows/face-detection/status/wf-bulk-123 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### 6. Get Workflow Lifecycles

**GET** `/workflows/face-detection/lifecycles/{workflow_id}`

Get detailed lifecycle information for a workflow.

**Response:**
```json
{
  "workflow_id": "wf-bulk-123",
  "lifecycles": [
    {
      "media_id": "550e8400-e29b-41d4-a716-446655440000",
      "method": "two_stage",
      "status": "completed",
      "faces_detected": 23,
      "processing_time": 12.5,
      "started_at": "2025-11-12T10:30:15Z",
      "completed_at": "2025-11-12T10:30:27Z"
    }
  ]
}
```

---

#### 7. Get User Workflows

**GET** `/workflows/user/{user_id}/workflows`

Get all workflows for a specific user.

**Path Parameters:**
- `user_id`: User identifier

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Results limit (default: 50)

**Response:**
```json
{
  "user_id": "user123",
  "total_workflows": 47,
  "workflows": [
    {
      "workflow_id": "wf-bulk-123",
      "status": "completed",
      "created_at": "2025-11-12T10:30:00Z",
      "media_count": 20
    }
  ]
}
```

---

#### 8. Get Camera Workflows

**GET** `/workflows/camera/{camera_device_id}/workflows`

Get all workflows for a specific camera.

**Path Parameters:**
- `camera_device_id`: Camera device identifier

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "total_workflows": 15,
  "workflows": [
    {
      "workflow_id": "wf-cam-001-123",
      "status": "completed",
      "recording_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "faces_detected": 23,
      "created_at": "2025-11-12T10:00:00Z"
    }
  ]
}
```

---

#### 9. Get Camera Analytics

**GET** `/workflows/camera/{camera_device_id}/analytics`

Get analytics for a specific camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "total_recordings_processed": 145,
  "total_faces_detected": 2387,
  "average_faces_per_recording": 16.5,
  "processing_time": {
    "total_seconds": 1847.5,
    "average_per_recording": 12.7
  },
  "success_rate": 0.987
}
```

---

#### 10. Get Platform Analytics

**GET** `/workflows/analytics`

Get platform-wide workflow analytics.

**Response:**
```json
{
  "total_workflows": 523,
  "active_workflows": 3,
  "completed_workflows": 487,
  "failed_workflows": 33,
  "total_media_processed": 523,
  "total_faces_detected": 12456,
  "average_processing_time": 13.8,
  "success_rate": 0.937,
  "by_camera": {
    "cam-001": 145,
    "cam-002": 89
  }
}
```

---

#### 11. Workflow Health Check

**GET** `/workflows/health`

Get health status of workflow system.

**Response:**
```json
{
  "status": "healthy",
  "active_workflows": 3,
  "queue_size": 0,
  "processing_capacity": 0.15
}
```

---

### Face Detection Workflows

#### 12. Trigger Face Detection

**POST** `/face-detection`

Trigger face detection for a single media item using Enhanced Logic V2.

**Request Body:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "enhanced_v2",
  "options": {
    "confidence_threshold": 0.5,
    "include_distance": true,
    "store_results": true
  }
}
```

**Response:**
```json
{
  "session_id": "fd-session-123",
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "method": "enhanced_v2",
  "created_at": "2025-11-12T10:30:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/face-detection \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "media_id": "550e8400-e29b-41d4-a716-446655440000",
    "method": "enhanced_v2"
  }'
```

---

#### 13. Get Face Detection Session

**GET** `/face-detection/sessions/{session_id}`

Get details of a face detection session.

**Response:**
```json
{
  "session_id": "fd-session-123",
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "method": "enhanced_v2",
  "faces_detected": 23,
  "processing_time": 12.5,
  "created_at": "2025-11-12T10:30:00Z",
  "completed_at": "2025-11-12T10:30:12Z"
}
```

---

#### 14. List Face Detection Sessions

**GET** `/face-detection/sessions`

List all face detection sessions.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Results limit
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "total": 145,
  "sessions": [
    {
      "session_id": "fd-session-123",
      "media_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "faces_detected": 23
    }
  ]
}
```

---

#### 15. Get Face Detection Results

**GET** `/face-detection/sessions/{session_id}/results`

Get detailed results from a face detection session.

**Response:**
```json
{
  "session_id": "fd-session-123",
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": {
    "total_faces": 23,
    "faces": [
      {
        "face_id": "face-001",
        "bbox": [100, 150, 200, 250],
        "confidence": 0.95,
        "frame_number": 45,
        "timestamp": 1.5,
        "distance_meters": 2.3
      }
    ],
    "metadata": {
      "processing_method": "enhanced_v2",
      "distance_calculation": "enabled"
    }
  }
}
```

---

#### 16. Get Enhanced V2 Faces

**GET** `/face-detection/media/{media_id}/faces/enhanced-v2`

Get Enhanced Logic V2 face detection results with distance calculations.

**Path Parameters:**
- `media_id`: Media UUID

**Response:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "enhanced_v2",
  "total_faces": 23,
  "faces": [
    {
      "face_id": "face-001",
      "bbox": [100, 150, 200, 250],
      "confidence": 0.95,
      "frame_number": 45,
      "distance_meters": 2.3,
      "bbox_height_pixels": 100,
      "calculation_method": "focal_length"
    }
  ],
  "processing_completed": true
}
```

---

#### 17. Delete Face Detection Session

**DELETE** `/face-detection/sessions/{session_id}`

Delete a face detection session.

**Response:**
```json
{
  "message": "Session deleted successfully",
  "session_id": "fd-session-123"
}
```

---

#### 18. Face Detection Health Check

**GET** `/face-detection/face-detection/health`

Check health of face detection system.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 2,
  "vision_service_available": true
}
```

---

### Person Objects (PPL Thread)

#### 19. Trigger PPL Thread Workflow

**POST** `/person-objects/trigger`

Trigger person objects (PPL Thread) workflow for a media item.

**Request Body:**
```json
{
  "media_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "success": true,
  "media_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_persons": 5,
  "total_faces": 23,
  "status": "completed",
  "message": "Person objects workflow completed",
  "person_groups": [
    {
      "person_uuid": "person-001",
      "person_id": "P001",
      "face_count": 8,
      "representative_faces": [
        {
          "face_id": "face-001",
          "quality_score": 0.95,
          "bbox": [100, 150, 200, 250],
          "frame_number": 45
        }
      ],
      "average_confidence": 0.89,
      "spatial_bounds": {
        "min_x": 50,
        "max_x": 800,
        "min_y": 100,
        "max_y": 600
      },
      "temporal_span": {
        "start_frame": 10,
        "end_frame": 245,
        "duration_seconds": 7.8
      },
      "movement_tracking": {
        "route_points": 15,
        "average_velocity": 0.5
      }
    }
  ],
  "grouping_algorithm": "rectangle_overlap_detection",
  "iou_threshold": 0.3,
  "processing_time_ms": 245.7,
  "session_uuid": "session-abc123"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/person-objects/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"media_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

---

#### 20. Get Person Objects Results

**GET** `/person-objects/{media_id}`

Get person objects results for a media item.

**Path Parameters:**
- `media_id`: Media UUID

**Response:** Same format as trigger response with cached results

---

### Recording Sessions

Recording sessions provide database-backed persistence for camera recordings with lifecycle tracking.

#### 21. Create Recording Session

**POST** `/recording-sessions/`

Create a new recording session.

**Request Body:**
```json
{
  "camera_device_id": "cam-001",
  "user_id": "user123",
  "recording_path": "/storage/recordings/cam-001/video.mp4",
  "metadata": {
    "duration": 120,
    "resolution": "1920x1080"
  }
}
```

**Response:**
```json
{
  "session_uuid": "rec-session-abc123",
  "camera_device_id": "cam-001",
  "user_id": "user123",
  "status": "recording",
  "recording_path": "/storage/recordings/cam-001/video.mp4",
  "created_at": "2025-11-12T10:30:00Z",
  "last_heartbeat": "2025-11-12T10:30:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:8002/recording-sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_device_id": "cam-001",
    "user_id": "user123",
    "recording_path": "/storage/recordings/cam-001/video.mp4"
  }'
```

---

#### 22. Get Recording Session

**GET** `/recording-sessions/{session_uuid}`

Get details of a specific recording session.

**Response:**
```json
{
  "session_uuid": "rec-session-abc123",
  "camera_device_id": "cam-001",
  "user_id": "user123",
  "status": "completed",
  "recording_path": "/storage/recordings/cam-001/video.mp4",
  "media_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "face_detection_triggered": true,
  "face_detection_completed": true,
  "created_at": "2025-11-12T10:30:00Z",
  "completed_at": "2025-11-12T10:32:00Z",
  "duration_seconds": 120,
  "metadata": {
    "resolution": "1920x1080",
    "fps": 30
  }
}
```

---

#### 23. List Recording Sessions

**GET** `/recording-sessions/`

List all recording sessions with filters.

**Query Parameters:**
- `camera_device_id` (optional): Filter by camera
- `user_id` (optional): Filter by user
- `status` (optional): Filter by status
- `limit` (optional): Results limit
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "total": 145,
  "sessions": [
    {
      "session_uuid": "rec-session-abc123",
      "camera_device_id": "cam-001",
      "status": "completed",
      "created_at": "2025-11-12T10:30:00Z"
    }
  ]
}
```

---

#### 24. Delete Recording Session

**DELETE** `/recording-sessions/{session_uuid}`

Delete a recording session.

**Response:**
```json
{
  "message": "Recording session deleted",
  "session_uuid": "rec-session-abc123"
}
```

---

#### 25. Update Session Status

**PUT** `/recording-sessions/{session_uuid}/status`

Update the status of a recording session.

**Request Body:**
```json
{
  "status": "completed",
  "error_message": null
}
```

**Response:**
```json
{
  "session_uuid": "rec-session-abc123",
  "status": "completed",
  "updated_at": "2025-11-12T10:32:00Z"
}
```

---

#### 26. Update Session Progress

**PUT** `/recording-sessions/{session_uuid}/progress`

Update progress information for a recording session.

**Request Body:**
```json
{
  "progress_percentage": 65,
  "frames_processed": 1950,
  "total_frames": 3000
}
```

---

#### 27. Session Heartbeat

**POST** `/recording-sessions/{session_uuid}/heartbeat`

Send heartbeat to keep session alive.

**Response:**
```json
{
  "session_uuid": "rec-session-abc123",
  "last_heartbeat": "2025-11-12T10:31:30Z",
  "status": "recording"
}
```

---

#### 28. Trigger Face Detection

**POST** `/recording-sessions/{session_uuid}/face-detection/trigger`

Trigger face detection for a completed recording session.

**Response:**
```json
{
  "session_uuid": "rec-session-abc123",
  "face_detection_triggered": true,
  "workflow_id": "wf-fd-123"
}
```

---

#### 29. Complete Face Detection

**POST** `/recording-sessions/{session_uuid}/face-detection/complete`

Mark face detection as completed for a session.

**Request Body:**
```json
{
  "faces_detected": 23,
  "processing_time": 12.5
}
```

---

#### 30. Update Media Upload

**PUT** `/recording-sessions/{session_uuid}/media-upload`

Update session with uploaded media UUID.

**Request Body:**
```json
{
  "media_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "upload_completed": true
}
```

---

#### 31. Get Active Sessions

**GET** `/recording-sessions/monitoring/active`

Get all currently active recording sessions.

**Response:**
```json
{
  "total_active": 3,
  "sessions": [
    {
      "session_uuid": "rec-session-abc123",
      "camera_device_id": "cam-001",
      "status": "recording",
      "duration_seconds": 45
    }
  ]
}
```

---

#### 32. Get Stale Sessions

**GET** `/recording-sessions/monitoring/stale`

Get sessions without recent heartbeats (potential issues).

**Query Parameters:**
- `threshold_minutes` (optional): Heartbeat timeout threshold (default: 5)

**Response:**
```json
{
  "total_stale": 2,
  "threshold_minutes": 5,
  "sessions": [
    {
      "session_uuid": "rec-session-xyz789",
      "camera_device_id": "cam-002",
      "last_heartbeat": "2025-11-12T10:20:00Z",
      "minutes_since_heartbeat": 12
    }
  ]
}
```

---

#### 33. Cleanup Stale Sessions

**POST** `/recording-sessions/monitoring/cleanup-stale`

Cleanup stale sessions by marking them as failed.

**Request Body:**
```json
{
  "threshold_minutes": 10,
  "dry_run": false
}
```

**Response:**
```json
{
  "cleaned_count": 2,
  "sessions_cleaned": [
    "rec-session-xyz789",
    "rec-session-def456"
  ]
}
```

---

#### 34. Get Session Statistics

**GET** `/recording-sessions/statistics`

Get overall recording session statistics.

**Response:**
```json
{
  "total_sessions": 523,
  "by_status": {
    "recording": 3,
    "completed": 487,
    "failed": 33
  },
  "by_camera": {
    "cam-001": 145,
    "cam-002": 89
  },
  "average_duration": 132.5,
  "total_recording_time": 69307.5
}
```

---

#### 35. Get Sessions by Camera

**GET** `/recording-sessions/camera/{camera_device_id}`

Get all sessions for a specific camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "total_sessions": 145,
  "sessions": [
    {
      "session_uuid": "rec-session-abc123",
      "status": "completed",
      "created_at": "2025-11-12T10:00:00Z"
    }
  ]
}
```

---

#### 36. Get Sessions by User

**GET** `/recording-sessions/user/{user_id}`

Get all sessions for a specific user.

**Response:**
```json
{
  "user_id": "user123",
  "total_sessions": 87,
  "sessions": [
    {
      "session_uuid": "rec-session-abc123",
      "camera_device_id": "cam-001",
      "status": "completed"
    }
  ]
}
```

---

#### 37. Recording Sessions Health Check

**GET** `/recording-sessions/health`

Check health of recording session system.

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "active_sessions": 3,
  "stale_sessions": 0
}
```

---

### Session Management

#### 38. List Sessions

**GET** `/sessions/`

List all workflow sessions.

**Query Parameters:**
- `status` (optional): Filter by status
- `limit` (optional): Results limit

**Response:**
```json
{
  "total": 523,
  "sessions": [
    {
      "session_id": "session-123",
      "type": "face_detection",
      "status": "completed",
      "created_at": "2025-11-12T10:00:00Z"
    }
  ]
}
```

---

#### 39. Get Sessions Overview

**GET** `/sessions/overview`

Get overview of all sessions.

**Response:**
```json
{
  "total_sessions": 523,
  "active": 3,
  "completed": 487,
  "failed": 33,
  "by_type": {
    "face_detection": 400,
    "person_objects": 123
  }
}
```

---

#### 40. Create Session

**POST** `/sessions/`

Create a new workflow session.

---

#### 41. Get Session

**GET** `/sessions/{session_id}`

Get details of a specific session.

---

#### 42. Update Session

**PUT** `/sessions/{session_id}`

Update session information.

---

#### 43. Delete Session

**DELETE** `/sessions/{session_id}`

Delete a session.

---

### Master Lifecycle Workflows

#### 44. Start Master Workflow

**POST** `/master-workflows/workflows/start`

Start a master lifecycle workflow.

**Request Body:**
```json
{
  "workflow_type": "face_detection_pipeline",
  "media_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "configuration": {
    "methods": ["two_stage", "enhanced_v2"],
    "auto_merge": true
  }
}
```

**Response:**
```json
{
  "session_uuid": "master-wf-123",
  "status": "running",
  "created_at": "2025-11-12T10:30:00Z",
  "configuration": {
    "methods": ["two_stage", "enhanced_v2"]
  }
}
```

---

#### 45. Get Workflow Status

**GET** `/master-workflows/workflows/{session_uuid}/status`

Get status of a master workflow.

**Response:**
```json
{
  "session_uuid": "master-wf-123",
  "status": "running",
  "progress": 0.65,
  "current_phase": "face_detection",
  "phases_completed": ["initialization", "preprocessing"],
  "phases_remaining": ["post_processing", "cleanup"]
}
```

---

#### 46. Get Workflow Results

**GET** `/master-workflows/workflows/{session_uuid}/results`

Get results from a completed master workflow.

**Response:**
```json
{
  "session_uuid": "master-wf-123",
  "status": "completed",
  "results": {
    "total_media_processed": 20,
    "total_faces_detected": 456,
    "unique_individuals": 23,
    "processing_time": 125.7
  }
}
```

---

#### 47. Cancel Workflow

**DELETE** `/master-workflows/workflows/{session_uuid}`

Cancel a running workflow.

**Response:**
```json
{
  "session_uuid": "master-wf-123",
  "status": "cancelled",
  "message": "Workflow cancelled successfully"
}
```

---

#### 48. Get Active Workflows

**GET** `/master-workflows/workflows/active`

Get all currently active master workflows.

**Response:**
```json
{
  "total_active": 3,
  "workflows": [
    {
      "session_uuid": "master-wf-123",
      "status": "running",
      "progress": 0.65
    }
  ]
}
```

---

#### 49. Cleanup Workflows

**POST** `/master-workflows/workflows/cleanup`

Cleanup completed or failed workflows.

**Request Body:**
```json
{
  "older_than_hours": 24,
  "status": ["completed", "failed"]
}
```

**Response:**
```json
{
  "cleaned_count": 45,
  "disk_space_freed": 524288000
}
```

---

#### 50. Master Workflow Health

**GET** `/master-workflows/health`

Check health of master workflow system.

---

### Camera Automation

#### 51. Get Camera Settings

**GET** `/camera-automation/cameras/{camera_device_id}/settings`

Get automation settings for a camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "automation_enabled": true,
  "auto_process_recordings": true,
  "face_detection_methods": ["two_stage"],
  "processing_priority": "normal"
}
```

---

#### 52. Update Camera Settings

**PUT** `/camera-automation/cameras/{camera_device_id}/settings`

Update automation settings for a camera.

**Request Body:**
```json
{
  "automation_enabled": true,
  "auto_process_recordings": true,
  "face_detection_methods": ["two_stage", "enhanced_v2"]
}
```

---

#### 53. Get Camera Statistics

**GET** `/camera-automation/cameras/{camera_device_id}/stats`

Get automation statistics for a camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "total_recordings": 145,
  "processed_recordings": 140,
  "processing_success_rate": 0.965,
  "average_processing_time": 13.2
}
```

---

#### 54. Process Camera Recording

**POST** `/camera-automation/cameras/{camera_device_id}/process`

Manually trigger processing for a camera recording.

**Request Body:**
```json
{
  "recording_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "methods": ["two_stage"]
}
```

---

#### 55. Get Automation Options

**GET** `/camera-automation/options`

Get available automation options and configurations.

**Response:**
```json
{
  "available_methods": [
    "two_stage",
    "enhanced_v2",
    "person_objects"
  ],
  "priority_levels": ["low", "normal", "high"],
  "default_settings": {
    "auto_process": true,
    "methods": ["two_stage"]
  }
}
```

---

#### 56. Camera Automation Health

**GET** `/camera-automation/health`

Check health of camera automation system.

---

### Camera Events

#### 57. Register Webhook

**POST** `/camera-events/cameras/{camera_device_id}/webhook/register`

Register a webhook for camera events.

**Request Body:**
```json
{
  "webhook_url": "https://example.com/webhooks/camera-events",
  "event_types": ["motion_detected", "recording_started", "recording_stopped"]
}
```

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "webhook_registered": true,
  "event_types": ["motion_detected", "recording_started", "recording_stopped"]
}
```

---

#### 58. Unregister Webhook

**DELETE** `/camera-events/cameras/{camera_device_id}/webhook/unregister`

Unregister webhook for a camera.

---

#### 59. Process Webhook Event

**POST** `/camera-events/webhook`

Process incoming webhook event from camera.

**Request Body:**
```json
{
  "camera_device_id": "cam-001",
  "event_type": "motion_detected",
  "timestamp": "2025-11-12T10:30:00Z",
  "metadata": {
    "confidence": 0.95
  }
}
```

---

#### 60. Get Camera Event Statistics

**GET** `/camera-events/cameras/{camera_device_id}/stats`

Get event statistics for a camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "total_events": 523,
  "by_type": {
    "motion_detected": 400,
    "recording_started": 123,
    "recording_stopped": 0
  },
  "last_event": "2025-11-12T10:30:00Z"
}
```

---

#### 61. Register All User Cameras

**POST** `/camera-events/users/{user_id}/cameras/register-all`

Register webhooks for all cameras of a user.

---

#### 62. Start Polling

**POST** `/camera-events/cameras/{camera_device_id}/polling/start`

Start event polling for a camera (alternative to webhooks).

**Request Body:**
```json
{
  "interval_seconds": 5,
  "event_types": ["motion_detected"]
}
```

---

#### 63. Stop Polling

**POST** `/camera-events/cameras/{camera_device_id}/polling/stop`

Stop event polling for a camera.

---

#### 64. Camera Events Health

**GET** `/camera-events/health`

Check health of camera events system.

---

### Method Lifecycle

#### 65. Initialize Method for Camera

**POST** `/method-lifecycle/cameras/{camera_device_id}/initialize`

Initialize detection methods for a camera.

**Request Body:**
```json
{
  "methods": ["two_stage", "enhanced_v2"],
  "configuration": {
    "confidence_threshold": 0.5
  }
}
```

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "initialized_methods": ["two_stage", "enhanced_v2"],
  "status": "ready"
}
```

---

#### 66. Execute Method

**POST** `/method-lifecycle/cameras/{camera_device_id}/execute`

Execute a detection method on a recording.

**Request Body:**
```json
{
  "method_name": "two_stage",
  "recording_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "execution_id": "exec-123",
  "camera_device_id": "cam-001",
  "method_name": "two_stage",
  "status": "running"
}
```

---

#### 67. Get Method Status

**GET** `/method-lifecycle/cameras/{camera_device_id}/status`

Get status of all methods for a camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "methods": {
    "two_stage": {
      "status": "ready",
      "executions": 145,
      "last_execution": "2025-11-12T10:30:00Z"
    },
    "enhanced_v2": {
      "status": "ready",
      "executions": 87,
      "last_execution": "2025-11-12T10:25:00Z"
    }
  }
}
```

---

#### 68. Get Specific Method Status

**GET** `/method-lifecycle/cameras/{camera_device_id}/methods/{method_name}/status`

Get status of a specific method.

---

#### 69. Get Method Analytics

**GET** `/method-lifecycle/cameras/{camera_device_id}/analytics`

Get analytics for all methods on a camera.

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "methods": {
    "two_stage": {
      "total_executions": 145,
      "success_rate": 0.965,
      "average_processing_time": 13.2,
      "average_faces_detected": 16.5
    }
  }
}
```

---

#### 70. Update Method Configuration

**PUT** `/method-lifecycle/cameras/{camera_device_id}/methods/{method_name}/config`

Update configuration for a method.

**Request Body:**
```json
{
  "confidence_threshold": 0.6,
  "max_faces": 50
}
```

---

#### 71. Reset Method

**POST** `/method-lifecycle/cameras/{camera_device_id}/methods/{method_name}/reset`

Reset a method to default state.

---

#### 72. Method Lifecycle Health

**GET** `/method-lifecycle/health`

Check health of method lifecycle system.

---

#### 73. Get Method Logs

**GET** `/method-lifecycle/cameras/{camera_device_id}/methods/{method_name}/logs`

Get execution logs for a method.

**Query Parameters:**
- `limit` (optional): Number of logs to return
- `start_date` (optional): Filter logs from date

**Response:**
```json
{
  "camera_device_id": "cam-001",
  "method_name": "two_stage",
  "logs": [
    {
      "execution_id": "exec-123",
      "timestamp": "2025-11-12T10:30:00Z",
      "status": "completed",
      "faces_detected": 23,
      "processing_time": 12.5
    }
  ]
}
```

---

### Automation Rules

#### 74. Automation Rules Health

**GET** `/automation/health`

Check health of automation engine.

**Response:**
```json
{
  "status": "healthy",
  "active_rules": 15,
  "executions_today": 234
}
```

---

#### 75. Create Automation Rule

**POST** `/automation/rules`

Create a new automation rule.

**Request Body:**
```json
{
  "name": "Auto-process night recordings",
  "description": "Automatically process recordings made at night",
  "trigger": {
    "type": "time_based",
    "schedule": "0 6 * * *"
  },
  "conditions": [
    {
      "field": "recording_time",
      "operator": "between",
      "value": ["00:00", "06:00"]
    }
  ],
  "actions": [
    {
      "type": "trigger_face_detection",
      "parameters": {
        "methods": ["enhanced_v2"]
      }
    }
  ],
  "enabled": true
}
```

**Response:**
```json
{
  "rule_id": "rule-123",
  "name": "Auto-process night recordings",
  "status": "active",
  "created_at": "2025-11-12T10:30:00Z"
}
```

---

#### 76. List Automation Rules

**GET** `/automation/rules`

List all automation rules.

**Query Parameters:**
- `enabled` (optional): Filter by enabled status
- `type` (optional): Filter by trigger type

**Response:**
```json
{
  "total_rules": 15,
  "rules": [
    {
      "rule_id": "rule-123",
      "name": "Auto-process night recordings",
      "enabled": true,
      "trigger_type": "time_based",
      "executions": 47
    }
  ]
}
```

---

#### 77. Get Automation Rule

**GET** `/automation/rules/{rule_id}`

Get details of a specific rule.

---

#### 78. Execute Automation Rule

**POST** `/automation/rules/{rule_id}/execute`

Manually execute an automation rule.

**Response:**
```json
{
  "rule_id": "rule-123",
  "execution_id": "exec-456",
  "status": "running",
  "started_at": "2025-11-12T10:30:00Z"
}
```

---

#### 79. Update Automation Rule

**PUT** `/automation/rules/{rule_id}`

Update an automation rule.

---

#### 80. Delete Automation Rule

**DELETE** `/automation/rules/{rule_id}`

Delete an automation rule.

---

#### 81. Pause Automation Rule

**POST** `/automation/rules/{rule_id}/pause`

Pause execution of an automation rule.

---

#### 82. Resume Automation Rule

**POST** `/automation/rules/{rule_id}/resume`

Resume execution of a paused rule.

---

#### 83. Get Rule Executions

**GET** `/automation/executions`

Get execution history for automation rules.

**Query Parameters:**
- `rule_id` (optional): Filter by rule
- `status` (optional): Filter by status
- `limit` (optional): Results limit

**Response:**
```json
{
  "total_executions": 234,
  "executions": [
    {
      "execution_id": "exec-456",
      "rule_id": "rule-123",
      "status": "completed",
      "started_at": "2025-11-12T06:00:00Z",
      "completed_at": "2025-11-12T06:05:23Z",
      "actions_executed": 5
    }
  ]
}
```

---

#### 84. Get Automation Status

**GET** `/automation/status`

Get overall automation system status.

**Response:**
```json
{
  "status": "operational",
  "total_rules": 15,
  "active_rules": 12,
  "paused_rules": 3,
  "executions_today": 234,
  "success_rate": 0.978
}
```

---

#### 85. Get Automation Analytics

**GET** `/automation/analytics`

Get automation analytics and insights.

**Response:**
```json
{
  "total_executions": 2340,
  "success_rate": 0.978,
  "by_trigger_type": {
    "time_based": 1500,
    "event_based": 840
  },
  "most_active_rules": [
    {
      "rule_id": "rule-123",
      "name": "Auto-process night recordings",
      "executions": 456
    }
  ],
  "average_execution_time": 15.7
}
```

---

## Data Models

### WorkflowStatus

```json
{
  "workflow_id": "string",
  "status": "initiated | processing | completed | failed",
  "progress": 0.0,
  "completed_items": 0,
  "total_items": 0,
  "started_at": "datetime",
  "completed_at": "datetime"
}
```

### FaceDetectionSession

```json
{
  "session_id": "string",
  "media_id": "string",
  "status": "processing | completed | failed",
  "method": "two_stage | enhanced_v2",
  "faces_detected": 0,
  "processing_time": 0.0,
  "created_at": "datetime"
}
```

### RecordingSession

```json
{
  "session_uuid": "string",
  "camera_device_id": "string",
  "user_id": "string",
  "status": "recording | completed | failed",
  "recording_path": "string",
  "media_uuid": "string",
  "face_detection_triggered": false,
  "face_detection_completed": false,
  "created_at": "datetime",
  "last_heartbeat": "datetime"
}
```

### PersonGroup

```json
{
  "person_uuid": "string",
  "person_id": "string",
  "face_count": 0,
  "representative_faces": [],
  "average_confidence": 0.0,
  "spatial_bounds": {},
  "temporal_span": {},
  "movement_tracking": {}
}
```

### AutomationRule

```json
{
  "rule_id": "string",
  "name": "string",
  "trigger": {
    "type": "time_based | event_based",
    "schedule": "string"
  },
  "conditions": [],
  "actions": [],
  "enabled": true
}
```

---

## Workflow Architecture

### Face Detection Pipeline

1. **Event Reception**: Camera sends storage event
2. **Session Creation**: Recording session created in database
3. **Face Detection**: Vision Service processes video
4. **Result Storage**: Results stored in Vision DB
5. **Person Grouping**: PPL Thread groups faces into persons
6. **Analytics**: Statistics calculated and stored

### Self-Referencing Architecture

The orchestrator can call its own endpoints for consistency:

```
Frontend → Orchestrator (face-detection endpoint)
              ↓
Orchestrator → Orchestrator (internal call)
              ↓
Vision Service → Face Detection
```

### Service Communication Flow

```
Camera Service → Orchestrator → Media Service
                              → Vision Service
                              → VMeta Service
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_type": "ValidationError",
  "workflow_id": "wf-123"
}
```

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created
- **202 Accepted**: Request accepted for processing
- **400 Bad Request**: Invalid request
- **401 Unauthorized**: Authentication failed
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Downstream service unavailable

### Workflow Errors

**Service Unavailable:**
```json
{
  "detail": "Vision Service unavailable",
  "status_code": 503,
  "service": "vision",
  "retry_after": 60
}
```

**Workflow Failed:**
```json
{
  "detail": "Face detection workflow failed",
  "status_code": 500,
  "workflow_id": "wf-123",
  "phase": "face_detection",
  "error_details": "Processing timeout"
}
```

---

## Best Practices

### 1. Workflow Management

**Start workflows asynchronously:**
```python
# Start workflow
response = requests.post(
    'http://localhost:8002/workflows/face-detection/bulk-process',
    json={'media_ids': media_ids},
    headers={'Authorization': f'Bearer {token}'}
)
workflow_id = response.json()['workflow_id']

# Poll for status
while True:
    status = requests.get(
        f'http://localhost:8002/workflows/face-detection/status/{workflow_id}',
        headers={'Authorization': f'Bearer {token}'}
    ).json()
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(5)
```

### 2. Recording Session Tracking

**Maintain heartbeats:**
```python
import time
import threading

def send_heartbeat(session_uuid, token):
    while recording:
        requests.post(
            f'http://localhost:8002/recording-sessions/{session_uuid}/heartbeat',
            headers={'Authorization': f'Bearer {token}'}
        )
        time.sleep(30)  # Every 30 seconds

# Start heartbeat thread
heartbeat_thread = threading.Thread(
    target=send_heartbeat, 
    args=(session_uuid, token)
)
heartbeat_thread.start()
```

### 3. Error Handling

**Implement retries with exponential backoff:**
```python
import time

def trigger_workflow_with_retry(media_ids, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'http://localhost:8002/workflows/face-detection/bulk-process',
                json={'media_ids': media_ids},
                headers={'Authorization': f'Bearer {token}'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if attempt < max_retries - 1 and e.response.status_code >= 500:
                time.sleep(2 ** attempt)
            else:
                raise
```

### 4. Automation Rules

**Create time-based rules for batch processing:**
```python
rule = {
    "name": "Nightly batch processing",
    "trigger": {
        "type": "time_based",
        "schedule": "0 2 * * *"  # 2 AM daily
    },
    "conditions": [
        {
            "field": "camera_device_id",
            "operator": "in",
            "value": ["cam-001", "cam-002"]
        }
    ],
    "actions": [
        {
            "type": "trigger_face_detection",
            "parameters": {"methods": ["enhanced_v2"]}
        }
    ]
}

requests.post(
    'http://localhost:8002/automation/rules',
    json=rule,
    headers={'Authorization': f'Bearer {token}'}
)
```

### 5. Monitoring

**Monitor workflow health:**
```python
def check_system_health():
    health = requests.get('http://localhost:8002/health').json()
    
    if not all(health['service_connections'].values()):
        alert("Service connection issues detected")
    
    if health['workflow_orchestrator']['active_workflows'] > 10:
        alert("High workflow load")
```

### 6. Session Cleanup

**Regular cleanup of stale sessions:**
```python
# Run periodically (e.g., hourly)
requests.post(
    'http://localhost:8002/recording-sessions/monitoring/cleanup-stale',
    json={'threshold_minutes': 10},
    headers={'Authorization': f'Bearer {token}'}
)
```

---

## Performance Considerations

### 1. Bulk Operations

- Use bulk endpoints for processing multiple items
- Workflows handle up to 100 items efficiently
- For larger batches, split into multiple workflows

### 2. Session Heartbeats

- Send heartbeats every 30-60 seconds
- Reduces database load
- Prevents false stale detection

### 3. Webhook vs Polling

- **Webhooks**: Real-time, efficient for frequent events
- **Polling**: Fallback for webhook-incompatible cameras
- Use appropriate polling intervals (5-30 seconds)

### 4. Method Lifecycle

- Initialize methods once per camera
- Reuse initialized methods for multiple recordings
- Reset only when configuration changes

---

## Integration Examples

### Complete Camera Recording Workflow

```python
import requests
import time

TOKEN = "your_jwt_token"
BASE_URL = "http://localhost:8002"

# 1. Create recording session
session = requests.post(
    f"{BASE_URL}/recording-sessions/",
    json={
        "camera_device_id": "cam-001",
        "user_id": "user123",
        "recording_path": "/storage/cam-001/video.mp4"
    },
    headers={"Authorization": f"Bearer {TOKEN}"}
).json()

session_uuid = session['session_uuid']

# 2. Send heartbeats during recording
# (in separate thread - see best practices)

# 3. Complete recording
requests.put(
    f"{BASE_URL}/recording-sessions/{session_uuid}/status",
    json={"status": "completed"},
    headers={"Authorization": f"Bearer {TOKEN}"}
)

# 4. Upload to media service and update session
media_response = upload_to_media_service(recording_path)
requests.put(
    f"{BASE_URL}/recording-sessions/{session_uuid}/media-upload",
    json={"media_uuid": media_response['uuid']},
    headers={"Authorization": f"Bearer {TOKEN}"}
)

# 5. Trigger face detection
requests.post(
    f"{BASE_URL}/recording-sessions/{session_uuid}/face-detection/trigger",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

# 6. Wait for completion
while True:
    session = requests.get(
        f"{BASE_URL}/recording-sessions/{session_uuid}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    ).json()
    
    if session['face_detection_completed']:
        break
    
    time.sleep(5)

# 7. Get results
results = requests.get(
    f"{BASE_URL}/person-objects/{media_response['uuid']}",
    headers={"Authorization": f"Bearer {TOKEN}"}
).json()

print(f"Detected {results['total_persons']} persons")
print(f"Total faces: {results['total_faces']}")
```

---

## Changelog

### Version 1.0.0 (Phase 1-2.4)

**Phase 1:**
- Camera workflow orchestration
- Face detection workflows
- Service client management
- Session tracking

**Phase 2.1:**
- Camera automation
- Recording session database persistence

**Phase 2.2:**
- Event publishing and webhooks
- Real-time event handling

**Phase 2.3:**
- Method lifecycle management
- Per-camera method configuration

**Phase 2.4:**
- Automation engine
- Conditional rule execution
- Advanced analytics

---

## Support & Documentation

- **Interactive API Docs**: `http://localhost:8002/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8002/redoc` (ReDoc)
- **OpenAPI Spec**: `http://localhost:8002/openapi.json`
- **GitHub**: [ppl-meta-platform](https://github.com/nickglezakos/ppl-meta-platform)

---

## Appendix

### Service Configuration

**Default Port:** 8002  
**Base Path:** `/`  
**Documentation:** `/docs`, `/redoc`

### Environment Variables

- `CAMERA_SERVICE_URL`: Camera service URL (default: http://localhost:8005)
- `MEDIA_SERVICE_URL`: Media service URL (default: http://localhost:8000)
- `VISION_SERVICE_URL`: Vision service URL (default: http://localhost:8003)
- `DATABASE_URL`: Database connection string
- `CONSUL_ENABLED`: Enable service discovery (true/false)
- `LOG_LEVEL`: Logging level

### Workflow States

- **initiated**: Workflow created, not yet started
- **processing**: Actively processing
- **completed**: Successfully finished
- **failed**: Encountered error
- **cancelled**: Manually cancelled

### Recording Session States

- **recording**: Currently recording
- **processing**: Processing after recording
- **completed**: Successfully completed
- **failed**: Failed with error
- **stale**: No recent heartbeat

---

**Last Updated:** November 12, 2025  
**API Version:** 1.0.0 (Phase 1-2.4)  
**Document Version:** 1.0
