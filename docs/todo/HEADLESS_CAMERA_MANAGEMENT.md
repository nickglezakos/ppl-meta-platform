# Headless Camera Management Guide

**Document Version:** 1.1  
**Date:** October 19, 2025  
**Purpose:** Complete guide for managing cameras from the backend without UI dependencies

## Overviewthe ehald

This document provides the authoritative guide for programmatically managing cameras in the PPL Meta platform through REST API endpoints. This is essential for automated workflows, testing, and backend integrations.

## Service Architecture

### Core Services
- **Gateway Service** (Port 8080): Main entry point via nginx proxy at `http://localhost/`
- **Cameras Service** (Port 8005): Direct camera management service
- **Orchestrator Service** (Port 8002): Workflow and session management

### API Routing
All camera operations should go through the Gateway service which routes to the appropriate backend service:
- Gateway: `http://localhost/api/v1/` (via nginx)
- Direct Cameras: `http://localhost:8005/api/v1/` (for debugging only)

## Authentication

### Required Headers
```bash
Authorization: Bearer <JWT_TOKEN>
```

### Getting a Token
```bash
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Camera Management Workflow

### 1. Camera Detection and Discovery

#### Detect Available Cameras
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/cameras/detect"
```

Response:
```json
{
  "detected_count": 1,
  "cameras": [{
    "device_id": "usb_camera_0",
    "name": "USB Camera 0",
    "camera_type": "USB",
    "status": "available",
    "resolution_width": 1280,
    "resolution_height": 720,
    "max_fps": 30,
    "connection_string": "0",
    "supports_streaming": true,
    "supports_recording": true,
    "index": 0
  }],
  "saved_to_db": true,
  "saved_count": 1
}
```

#### List Available Cameras
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/cameras"
```

### 2. Camera Connection Management

#### Connect to Camera
**REQUIRED BEFORE STREAMING OR RECORDING**
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/cameras/{device_id}/connect"
```

Success Response:
```json
{
  "device_id": "usb_camera_0",
  "status": "connected",
  "message": "Successfully connected to camera usb_camera_0"
}
```

#### Disconnect Camera
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/cameras/{device_id}/disconnect"
```

### 3. Camera Streaming

#### Start Streaming
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/streaming/{device_id}/start"
```

Response:
```json
{
  "device_id": "usb_camera_0",
  "status": "streaming",
  "message": "Stream started for camera usb_camera_0",
  "stream_url": "/cameras/api/v1/streaming/usb_camera_0/video"
}
```

#### Check Streaming Status
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/streaming/{device_id}/status"
```

#### Stop Streaming
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/streaming/{device_id}/stop"
```

### 4. Camera Recording

#### Start Recording
**REQUIRES: Camera connected AND streaming**
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/streaming/{device_id}/record/start"
```

#### Check Recording Status
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/streaming/{device_id}/record/status"
```

Response:
```json
{
  "device_id": "usb_camera_0",
  "is_recording": false,
  "recording_id": null,
  "started_at": null,
  "duration_seconds": 0,
  "file_size_bytes": 0
}
```

#### Stop Recording
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/v1/streaming/{device_id}/record/stop"
```

## Complete Workflow Example

### Basic Recording Session
```bash
# 1. Get authentication token
TOKEN=$(curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Detect cameras
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/cameras/detect"

# 3. Connect to camera
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/cameras/usb_camera_0/connect"

# 4. Start streaming
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/streaming/usb_camera_0/start"

# 5. Start recording
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/streaming/usb_camera_0/record/start"

# 6. Wait for recording...
sleep 10

# 7. Stop recording
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/streaming/usb_camera_0/record/stop"

# 8. Stop streaming
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/streaming/usb_camera_0/stop"

# 9. Disconnect camera
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/cameras/usb_camera_0/disconnect"
```

## Recording Session Management

### Session-Based Recording
The platform supports advanced session-based recording with UUID tracking:

#### Create Recording Session (Orchestrator)
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  "http://localhost:8002/api/v1/recording-sessions" \
  -d '{
    "camera_device_id": "usb_camera_0",
    "user_id": "user_123",
    "recording_config": {
      "quality": "high",
      "segment_duration_seconds": 30,
      "auto_face_detection_enabled": true
    }
  }'
```

#### Query Recording Sessions
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8002/api/v1/recording-sessions/camera/usb_camera_0"
```

## Troubleshooting

### Common Issues

#### 1. "Failed to connect to camera"
- Ensure camera is detected first: `/api/v1/cameras/detect`
- Check camera is not in use by another application
- Verify camera permissions

#### 2. "Camera is already recording" but status shows not recording
- **ISSUE RESOLVED**: State management inconsistency between in-memory `active_recordings` and database session state
- **Root Cause**: Stale database sessions marked as "active" after service restart or crash
- **Solution**: Use debug endpoints to identify and clear stale state

**Debug Commands:**
```bash
# Check recording state inconsistency
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/cameras/api/v1/streaming/{device_id}/record/debug"

# Clear stale recording state
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/cameras/api/v1/streaming/{device_id}/record/clear-state"
```

**Example Debug Output:**
```json
{
  "device_id": "usb_camera_0",
  "has_active_recording_memory": false,
  "has_active_session_db": true,
  "active_recording_keys": [],
  "memory_recording_id": null,
  "db_session_uuid": "414d74d6-4244-4cc6-9102-e34be967badf",
  "db_session_status": "active"
}
```

If `has_active_recording_memory` is false but `has_active_session_db` is true, clear the stale state.

#### 3. Authentication Issues
- Ensure fresh token is obtained before each session
- Check token expiration time
- Verify user credentials are correct

### Debug Commands

#### Check Service Health
```bash
curl "http://localhost/health/cameras"
```

#### Direct Service Access (Debug Only)
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8005/api/v1/cameras"
```

#### Service Restart
```bash
# Restart cameras service to clear stuck states
pkill -f 'ppl-meta-cameras.*uvicorn.*main:app'
# Service will auto-restart via task runner
```

## Complete Recording Test Example

### Full Backend Recording Test (63-Second Success)

**Date:** October 19, 2025  
**Status:** ✅ VERIFIED WORKING - 63-SECOND RECORDING  
**Test Result:** EXCEEDED 38-SECOND TARGET

This is the complete, verified workflow for conducting a full recording test from detection to completion:

#### Step-by-Step Test Procedure

```bash
# Step 1: Get authentication token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Token obtained: ${TOKEN:0:20}..."

# Step 2: Detect cameras (via Gateway)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/cameras/detect"
# Expected: {"detected_count":1,"cameras":[{"device_id":"usb_camera_0"...}]}

# Step 3: Connect to camera (via Gateway)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/cameras/usb_camera_0/connect"
# Expected: {"device_id":"usb_camera_0","status":"connected"...}

# Step 4: Start streaming (via Gateway)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/streaming/usb_camera_0/start"
# Expected: {"device_id":"usb_camera_0","status":"streaming"...}

# Step 5: Check for recording state issues (CRITICAL STEP)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/streaming/usb_camera_0/record/debug"
# Look for: "has_active_recording_memory": false, "has_active_session_db": true

# Step 6: Clear stale state if needed (based on debug output)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/streaming/usb_camera_0/record/clear-state"
# Expected: {"cleared":[]} or {"cleared":["database_session"]}

# Step 7: Start recording (Direct Camera Service - most reliable)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/streaming/usb_camera_0/record/start"
# Expected: {"status":"success",...} or {"detail":"Camera usb_camera_0 is already recording"}

# Step 8: Verify recording is active
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/streaming/usb_camera_0/record/status"
# Expected: {"is_recording":true,"recording_id":"..","duration_seconds":X,...}

# Step 9: Monitor recording progress (repeat as needed)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/streaming/usb_camera_0/record/status"

# Step 10: Stop recording after desired duration
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/streaming/usb_camera_0/record/stop"

# Step 11: Cleanup (optional)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/streaming/usb_camera_0/stop"
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/cameras/usb_camera_0/disconnect"
```

#### Successful Test Results (October 19, 2025)

**Recording Metrics:**
- ✅ **Duration:** 63 seconds (exceeded 38-second target by 165%)
- ✅ **Recording ID:** `6d89581f-173a-4682-abc0-2d5d4536cc47`
- ✅ **Session UUID:** `d72d7707-90d5-4054-917a-505367a8e6db`
- ✅ **Collection ID:** `76241fb0-fc86-4859-b442-f7f2979a5c53`
- ✅ **File Size:** ~36.75 MB (final size)

**Segmented Recording Features:**
- ✅ **Segment Count:** 3 automatic segments
- ✅ **Segment Files:**
  - `segment_001_20251019_115200.mp4`
  - `segment_002_20251019_115231.mp4`
  - `segment_003_20251019_115301.mp4`
- ✅ **Session Directory:** `recordings/usb_camera_0/d72d7707-90d5-4054-917a-505367a8e6db`
- ✅ **Segment Duration:** 30 seconds (configurable)

**Stop Recording Response:**
```json
{
  "status": "success",
  "message": "Recording stopped for camera usb_camera_0",
  "device_id": "usb_camera_0",
  "recording_id": "6d89581f-173a-4682-abc0-2d5d4536cc47",
  "session_uuid": "d72d7707-90d5-4054-917a-505367a8e6db",
  "duration_seconds": 63,
  "collection_id": "76241fb0-fc86-4859-b442-f7f2979a5c53",
  "segment_count": 3,
  "segment_files": [
    "segment_001_20251019_115200.mp4",
    "segment_002_20251019_115231.mp4", 
    "segment_003_20251019_115301.mp4"
  ],
  "session_dir": "recordings/usb_camera_0/d72d7707-90d5-4054-917a-505367a8e6db",
  "stopped_at": "2025-10-19T11:53:04.499489"
}
```

#### Critical Success Factors

1. **State Management:** Always check and clear stale recording states using debug endpoints
2. **Service Routing:** Use Gateway for detect/connect/stream, Direct Camera Service for recording
3. **State Verification:** Verify `is_recording: true` after start command
4. **Segmentation:** Recordings automatically segment every 30 seconds with timestamped files
5. **Session Tracking:** Each recording gets unique session UUID and recording ID

#### Why This Approach Works

- **Gateway Routing:** Reliable for camera management operations (detect, connect, stream)
- **Direct Camera Service:** More reliable for recording operations (bypasses gateway complexity)
- **State Debugging:** Resolves common "already recording" but `is_recording: false` issues
- **Segmentation:** Prevents large file issues and provides better file management

## Future Improvements

### Planned Features
- [ ] Automatic state recovery on service restart
- [ ] Bulk camera operations
- [ ] Advanced recording profiles
- [ ] Real-time recording metrics
- [ ] Automatic session cleanup

### Known Limitations
- Single recording session per camera at a time
- State management consistency issues (under investigation)
- Manual camera detection required after service restart

---

**Last Updated:** October 19, 2025 - Added Complete 63-Second Recording Test Results  
**Next Review:** November 19, 2025