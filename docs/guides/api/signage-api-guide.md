# Signage Simple Player API Guide

## Overview

The Signage Simple Player API provides endpoints for managing digital signage video playlists, device synchronization, and remote playback control. This guide covers all available endpoints with examples and best practices.

**Base URL**: `http://localhost:8000/api/v1/signage`

**Authentication**: JWT Bearer token required for all endpoints

---

## Table of Contents

1. [Video List Management](#video-list-management)
2. [ETL Synchronization](#etl-synchronization)
3. [Playback Control](#playback-control)
4. [Device Management](#device-management)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)

---

## Video List Management

### Create Video List

Create a new video playlist from existing media collections.

**Endpoint**: `POST /video-lists`

**Request Body**:
```json
{
  "name": "Morning Lobby Display",
  "description": "Playlist for lobby signage during morning hours",
  "collection_ids": [1, 2, 3],
  "loop_mode": "continuous",
  "transition_duration": 1000,
  "is_published": true,
  "video_order": [
    {
      "collection_id": 1,
      "video_id": 10,
      "sequence": 1
    },
    {
      "collection_id": 2,
      "video_id": 15,
      "sequence": 2
    }
  ]
}
```

**Parameters**:
- `name` (required): Display name for the playlist
- `description` (optional): Detailed description
- `collection_ids` (required): List of media collection IDs to include
- `loop_mode` (optional): `"continuous"`, `"once"`, or `"shuffle"` (default: `"continuous"`)
- `transition_duration` (optional): Milliseconds between videos (default: 0)
- `is_published` (optional): Whether playlist is active (default: false)
- `video_order` (optional): Manual video ordering. If omitted, videos are added in collection order

**Response**: `201 Created`
```json
{
  "id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Morning Lobby Display",
  "description": "Playlist for lobby signage during morning hours",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "loop_mode": "continuous",
  "transition_duration": 1000,
  "is_published": true,
  "video_count": 2,
  "total_duration_ms": 180000,
  "created_at": "2025-12-02T10:00:00Z",
  "updated_at": "2025-12-02T10:00:00Z"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/video-lists \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Lobby Display",
    "collection_ids": [1, 2, 3],
    "loop_mode": "continuous"
  }'
```

---

### List Video Lists

Retrieve all video lists for the authenticated user with pagination and filtering.

**Endpoint**: `GET /video-lists`

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `search` (optional): Search by name or description
- `is_published` (optional): Filter by published status
- `loop_mode` (optional): Filter by loop mode

**Response**: `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Morning Lobby Display",
      "video_count": 5,
      "total_duration_ms": 300000,
      "is_published": true,
      "created_at": "2025-12-02T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/v1/signage/video-lists?page=1&page_size=10&is_published=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### Get Video List

Retrieve detailed information about a specific video list.

**Endpoint**: `GET /video-lists/{video_list_uuid}`

**Path Parameters**:
- `video_list_uuid`: UUID of the video list

**Query Parameters**:
- `include_items` (optional): Include full video item details (default: false)

**Response**: `200 OK`
```json
{
  "id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Morning Lobby Display",
  "description": "Playlist for lobby signage during morning hours",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "loop_mode": "continuous",
  "transition_duration": 1000,
  "is_published": true,
  "video_count": 2,
  "total_duration_ms": 180000,
  "video_items": [
    {
      "id": 1,
      "video_id": 10,
      "collection_id": 1,
      "sequence": 1,
      "duration_ms": 90000,
      "video_title": "Welcome Video",
      "video_filename": "welcome.mp4"
    },
    {
      "id": 2,
      "video_id": 15,
      "collection_id": 2,
      "sequence": 2,
      "duration_ms": 90000,
      "video_title": "Promotional Content",
      "video_filename": "promo.mp4"
    }
  ],
  "created_at": "2025-12-02T10:00:00Z",
  "updated_at": "2025-12-02T10:00:00Z"
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/v1/signage/video-lists/550e8400-e29b-41d4-a716-446655440000?include_items=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### Update Video List

Update an existing video list's properties.

**Endpoint**: `PUT /video-lists/{video_list_uuid}`

**Path Parameters**:
- `video_list_uuid`: UUID of the video list

**Request Body** (all fields optional):
```json
{
  "name": "Updated Morning Display",
  "description": "Updated description",
  "loop_mode": "shuffle",
  "transition_duration": 2000,
  "is_published": true
}
```

**Response**: `200 OK`
```json
{
  "id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Updated Morning Display",
  "description": "Updated description",
  "loop_mode": "shuffle",
  "transition_duration": 2000,
  "is_published": true,
  "video_count": 2,
  "total_duration_ms": 180000,
  "updated_at": "2025-12-02T11:00:00Z"
}
```

**cURL Example**:
```bash
curl -X PUT http://localhost:8000/api/v1/signage/video-lists/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Morning Display",
    "is_published": true
  }'
```

---

### Delete Video List

Delete a video list and all associated items.

**Endpoint**: `DELETE /video-lists/{video_list_uuid}`

**Path Parameters**:
- `video_list_uuid`: UUID of the video list

**Response**: `204 No Content`

**cURL Example**:
```bash
curl -X DELETE http://localhost:8000/api/v1/signage/video-lists/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## ETL Synchronization

### Sync Video List to Device

Push a video list to one or more signage devices via HTTP ETL.

**Endpoint**: `POST /etl/sync`

**Request Body**:
```json
{
  "video_list_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_ids": [
    "device-uuid-1",
    "device-uuid-2"
  ],
  "sync_mode": "full",
  "priority": 1
}
```

**Parameters**:
- `video_list_id` (required): UUID of the video list to sync
- `device_ids` (required): List of device UUIDs to sync to
- `sync_mode` (required): `"full"` (complete sync) or `"incremental"` (delta only)
- `priority` (optional): Sync priority 1-5 (default: 3)

**Response**: `200 OK`
```json
{
  "sync_id": "sync-uuid-123",
  "video_list_id": "550e8400-e29b-41d4-a716-446655440000",
  "devices_synced": 2,
  "sync_mode": "full",
  "status": "in_progress",
  "initiated_at": "2025-12-02T12:00:00Z",
  "results": [
    {
      "device_id": "device-uuid-1",
      "status": "success",
      "synced_at": "2025-12-02T12:00:05Z"
    },
    {
      "device_id": "device-uuid-2",
      "status": "success",
      "synced_at": "2025-12-02T12:00:06Z"
    }
  ]
}
```

**Sync Modes**:
- **Full Sync**: Sends complete video list with all metadata. Use for initial sync or major updates.
- **Incremental Sync**: Sends only changes since last sync. More efficient for minor updates.

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/etl/sync \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "video_list_id": "550e8400-e29b-41d4-a716-446655440000",
    "device_ids": ["device-uuid-1", "device-uuid-2"],
    "sync_mode": "full"
  }'
```

---

### Get Sync History

Retrieve synchronization history for a video list.

**Endpoint**: `GET /etl/sync-history`

**Query Parameters**:
- `video_list_id` (optional): Filter by video list UUID
- `device_id` (optional): Filter by device UUID
- `status` (optional): Filter by status (`in_progress`, `completed`, `failed`)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Response**: `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "video_list_id": "550e8400-e29b-41d4-a716-446655440000",
      "device_id": "device-uuid-1",
      "sync_mode": "full",
      "sync_status": "completed",
      "videos_synced": 5,
      "sync_duration_ms": 5000,
      "initiated_at": "2025-12-02T12:00:00Z",
      "completed_at": "2025-12-02T12:00:05Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/v1/signage/etl/sync-history?video_list_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Playback Control

### Control Device Playback

Send playback commands to one or more signage devices.

**Endpoint**: `POST /playback/control`

**Request Body**:
```json
{
  "device_ids": [
    "device-uuid-1",
    "device-uuid-2"
  ],
  "command": "START",
  "video_list_id": "550e8400-e29b-41d4-a716-446655440000",
  "parameters": {
    "volume": 80,
    "start_index": 0
  }
}
```

**Parameters**:
- `device_ids` (required): List of device UUIDs to control
- `command` (required): Playback command (see below)
- `video_list_id` (optional): UUID of video list to play (required for START)
- `parameters` (optional): Command-specific parameters

**Available Commands**:
- `START`: Begin playback of specified video list
- `PAUSE`: Pause current playback
- `RESUME`: Resume paused playback
- `STOP`: Stop playback and return to idle
- `NEXT`: Skip to next video
- `PREVIOUS`: Go to previous video
- `RESTART`: Restart current video list from beginning

**Response**: `200 OK`
```json
{
  "command": "START",
  "affected_devices": 2,
  "total_devices": 2,
  "results": [
    {
      "device_id": "device-uuid-1",
      "status": "success",
      "message": "Playback started"
    },
    {
      "device_id": "device-uuid-2",
      "status": "success",
      "message": "Playback started"
    }
  ],
  "executed_at": "2025-12-02T13:00:00Z"
}
```

**cURL Examples**:

**Start Playback**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/playback/control \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device-uuid-1"],
    "command": "START",
    "video_list_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Pause Playback**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/playback/control \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device-uuid-1"],
    "command": "PAUSE"
  }'
```

**Stop All Devices**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/playback/control \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ids": ["device-uuid-1", "device-uuid-2", "device-uuid-3"],
    "command": "STOP"
  }'
```

---

## Device Management

### Register Device

Register a new signage device or update existing registration.

**Endpoint**: `POST /devices`

**Request Body**:
```json
{
  "device_id": "device-uuid-1",
  "device_name": "Lobby Display #1",
  "ip_address": "192.168.1.100",
  "port": 8009,
  "location": "Main Lobby",
  "capabilities": {
    "max_resolution": "1920x1080",
    "supported_codecs": ["h264", "h265"],
    "audio_output": true
  }
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "device_id": "device-uuid-1",
  "device_name": "Lobby Display #1",
  "ip_address": "192.168.1.100",
  "port": 8009,
  "is_active": true,
  "is_online": true,
  "location": "Main Lobby",
  "last_heartbeat": "2025-12-02T14:00:00Z",
  "registered_at": "2025-12-02T14:00:00Z"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/devices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device-uuid-1",
    "device_name": "Lobby Display #1",
    "ip_address": "192.168.1.100",
    "port": 8009
  }'
```

---

### List Devices

Retrieve all registered signage devices.

**Endpoint**: `GET /devices`

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)
- `is_online` (optional): Filter by online status
- `is_active` (optional): Filter by active status
- `location` (optional): Filter by location

**Response**: `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "device_id": "device-uuid-1",
      "device_name": "Lobby Display #1",
      "ip_address": "192.168.1.100",
      "is_online": true,
      "is_active": true,
      "playback_state": "playing",
      "current_video_list_id": "550e8400-e29b-41d4-a716-446655440000",
      "last_heartbeat": "2025-12-02T14:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/v1/signage/devices?is_online=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### Get Device

Retrieve detailed information about a specific device.

**Endpoint**: `GET /devices/{device_id}`

**Path Parameters**:
- `device_id`: UUID of the device

**Response**: `200 OK`
```json
{
  "id": 1,
  "device_id": "device-uuid-1",
  "device_name": "Lobby Display #1",
  "ip_address": "192.168.1.100",
  "port": 8009,
  "is_active": true,
  "is_online": true,
  "location": "Main Lobby",
  "playback_state": "playing",
  "current_video_list_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_video_index": 2,
  "last_heartbeat": "2025-12-02T14:00:00Z",
  "registered_at": "2025-12-02T10:00:00Z",
  "capabilities": {
    "max_resolution": "1920x1080",
    "supported_codecs": ["h264", "h265"]
  }
}
```

**cURL Example**:
```bash
curl -X GET http://localhost:8000/api/v1/signage/devices/device-uuid-1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### Update Device

Update device properties.

**Endpoint**: `PUT /devices/{device_id}`

**Path Parameters**:
- `device_id`: UUID of the device

**Request Body** (all fields optional):
```json
{
  "device_name": "Updated Lobby Display",
  "location": "Reception Area",
  "is_active": true
}
```

**Response**: `200 OK`

**cURL Example**:
```bash
curl -X PUT http://localhost:8000/api/v1/signage/devices/device-uuid-1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "Updated Lobby Display",
    "is_active": true
  }'
```

---

### Device Heartbeat

Update device heartbeat to indicate it's online and responsive.

**Endpoint**: `POST /devices/{device_id}/heartbeat`

**Path Parameters**:
- `device_id`: UUID of the device

**Response**: `200 OK`
```json
{
  "device_id": "device-uuid-1",
  "last_heartbeat": "2025-12-02T14:05:00Z",
  "is_online": true
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/signage/devices/device-uuid-1/heartbeat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Note**: Devices should send heartbeats every 30-60 seconds. Devices without heartbeats for >2 minutes are marked offline.

---

## Error Handling

### HTTP Status Codes

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Video list not found or unauthorized",
  "error_code": "RESOURCE_NOT_FOUND",
  "timestamp": "2025-12-02T15:00:00Z"
}
```

### Common Error Codes

- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `UNAUTHORIZED`: Authentication required or invalid
- `FORBIDDEN`: User lacks permission
- `VALIDATION_ERROR`: Request data validation failed
- `DEVICE_OFFLINE`: Target device is not online
- `SYNC_FAILED`: Synchronization to device failed
- `PLAYBACK_ERROR`: Playback command failed

---

## Code Examples

### Python Client Example

```python
import requests
import json

class SignageClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def create_video_list(self, name, collection_ids, loop_mode="continuous"):
        """Create a new video list"""
        payload = {
            "name": name,
            "collection_ids": collection_ids,
            "loop_mode": loop_mode,
            "is_published": True
        }
        
        response = requests.post(
            f"{self.base_url}/video-lists",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def sync_to_devices(self, video_list_id, device_ids, sync_mode="full"):
        """Sync video list to devices"""
        payload = {
            "video_list_id": video_list_id,
            "device_ids": device_ids,
            "sync_mode": sync_mode
        }
        
        response = requests.post(
            f"{self.base_url}/etl/sync",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def start_playback(self, device_ids, video_list_id):
        """Start playback on devices"""
        payload = {
            "device_ids": device_ids,
            "command": "START",
            "video_list_id": video_list_id
        }
        
        response = requests.post(
            f"{self.base_url}/playback/control",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

# Usage
client = SignageClient("http://localhost:8000/api/v1/signage", "YOUR_JWT_TOKEN")

# Create playlist
video_list = client.create_video_list(
    name="Morning Display",
    collection_ids=[1, 2, 3]
)

# Sync to devices
sync_result = client.sync_to_devices(
    video_list_id=video_list["uuid"],
    device_ids=["device-uuid-1", "device-uuid-2"]
)

# Start playback
playback_result = client.start_playback(
    device_ids=["device-uuid-1", "device-uuid-2"],
    video_list_id=video_list["uuid"]
)
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

class SignageClient {
  constructor(baseUrl, token) {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }

  async createVideoList(name, collectionIds, loopMode = 'continuous') {
    const response = await this.client.post('/video-lists', {
      name,
      collection_ids: collectionIds,
      loop_mode: loopMode,
      is_published: true
    });
    return response.data;
  }

  async syncToDevices(videoListId, deviceIds, syncMode = 'full') {
    const response = await this.client.post('/etl/sync', {
      video_list_id: videoListId,
      device_ids: deviceIds,
      sync_mode: syncMode
    });
    return response.data;
  }

  async controlPlayback(deviceIds, command, videoListId = null) {
    const payload = {
      device_ids: deviceIds,
      command
    };
    
    if (videoListId) {
      payload.video_list_id = videoListId;
    }
    
    const response = await this.client.post('/playback/control', payload);
    return response.data;
  }
}

// Usage
const client = new SignageClient(
  'http://localhost:8000/api/v1/signage',
  'YOUR_JWT_TOKEN'
);

(async () => {
  // Create playlist
  const videoList = await client.createVideoList(
    'Morning Display',
    [1, 2, 3]
  );

  // Sync to devices
  const syncResult = await client.syncToDevices(
    videoList.uuid,
    ['device-uuid-1', 'device-uuid-2']
  );

  // Start playback
  const playbackResult = await client.controlPlayback(
    ['device-uuid-1', 'device-uuid-2'],
    'START',
    videoList.uuid
  );
})();
```

---

## Best Practices

### 1. Authentication
- Always use HTTPS in production
- Store JWT tokens securely
- Implement token refresh logic
- Never expose tokens in client-side code

### 2. Pagination
- Use pagination for large result sets
- Keep `page_size` reasonable (20-100 items)
- Cache results when appropriate

### 3. Device Management
- Implement regular heartbeat mechanism (every 30-60 seconds)
- Handle device offline scenarios gracefully
- Use device UUIDs, not IP addresses, as primary identifiers

### 4. Synchronization
- Use incremental sync for frequent updates
- Use full sync for major changes or after errors
- Monitor sync history for failures
- Implement retry logic with exponential backoff

### 5. Playback Control
- Verify devices are online before sending commands
- Handle partial success scenarios (some devices succeed, others fail)
- Implement timeout handling for unresponsive devices

### 6. Error Handling
- Always check HTTP status codes
- Parse error responses for detailed messages
- Log errors for debugging
- Implement user-friendly error messages

---

## Rate Limits

- **Video List Operations**: 100 requests/minute per user
- **ETL Sync**: 10 sync operations/minute per user
- **Playback Control**: 50 commands/minute per user
- **Device Heartbeat**: No limit

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/ppl-meta-platform/issues
- Documentation: https://docs.ppl-meta-platform.com
- Email: support@ppl-meta-platform.com

---

## Changelog

### Version 1.0.0 (2025-12-02)
- Initial release
- Video list management endpoints
- ETL synchronization
- Playback control
- Device management
