# PPL Meta Signage Management System

## Overview

The PPL Meta Signage Management System provides comprehensive control over digital signage devices, enabling playlist creation, device management, content synchronization, and real-time playback control through a unified web interface.

## Architecture

### Frontend Components

**Location:** `ppl-meta-frontend/lib/`

#### Main Screen
- **File:** `screens/signage_management_screen.dart`
- **Route:** `http://localhost:3000/#/signage`
- **Purpose:** Main container with 3-tab interface (Playlists, Devices, Control)

#### Key Widgets
1. **VideoListBuilder** (`widgets/signage/video_list_builder.dart`)
   - Create and edit video playlists
   - Manage video order and sequencing
   - Configure loop modes and transitions

2. **DeviceManager** (`widgets/signage/device_manager.dart`)
   - Grid view of all registered signage devices
   - Device status monitoring
   - Quick actions (sync, details)

3. **PlaybackControls** (`widgets/signage/playback_controls.dart`)
   - Full remote control interface
   - Real-time playback status display
   - Volume control and playlist selection

#### State Management
- **Provider:** `providers/signage_provider.dart`
- **Models:** `models/signage_models.dart`
- **API Client:** `services/signage_api_client.dart`

### Backend Services

#### Discovery Service
- **Port:** 8006
- **Purpose:** Service registration and heartbeat monitoring
- **Health Check:** `http://localhost:8006/health`

#### Media Service  
- **Port:** 8000
- **Purpose:** Video playlist management and ETL operations
- **Health Check:** `http://localhost:8000/health`

#### Gateway Service
- **Port:** 8080
- **Purpose:** API gateway and request routing
- **Health Check:** `http://localhost:8080/health`

---

## Feature Documentation

### 1. Playlists Tab

#### Functionality
- Create, edit, and delete video playlists
- Search and filter playlists
- View playlist metadata (video count, duration)
- Sync playlists to devices

#### User Actions

**Create Playlist**
1. Click "New Playlist" FAB
2. Enter playlist name and description
3. Select video collections
4. Configure video order and sequencing
5. Set loop mode (once, continuous, shuffle)
6. Set transition duration

**Edit Playlist**
1. Click playlist card
2. Modify playlist properties
3. Reorder videos via drag-and-drop
4. Save changes

**Sync to Devices**
1. Click playlist menu (⋮)
2. Select "Sync to Devices"
3. Choose target devices
4. Confirm sync operation

#### Backend Endpoints

**Get Playlists**
```http
GET /api/v1/signage/video-lists?page=1&limit=20&search={query}&is_active={bool}
```
Response:
```json
{
  "results": [
    {
      "uuid": "playlist-uuid",
      "name": "My Playlist",
      "description": "Description",
      "video_count": 10,
      "total_duration_ms": 300000,
      "loop_mode": "continuous",
      "transition_duration_ms": 1000,
      "is_active": true,
      "created_at": "2025-12-09T10:00:00Z",
      "updated_at": "2025-12-09T10:00:00Z"
    }
  ],
  "total_count": 50,
  "page": 1,
  "limit": 20,
  "total_pages": 3
}
```

**Get Playlist Details**
```http
GET /api/v1/signage/video-lists/{list_id}
```
Response: Single playlist object with full video items array

**Create Playlist**
```http
POST /api/v1/signage/video-lists
Content-Type: application/json

{
  "name": "New Playlist",
  "description": "Optional description",
  "collection_ids": ["col-uuid-1", "col-uuid-2"],
  "video_order": [
    {
      "collection_id": "col-uuid-1",
      "video_id": "vid-uuid-1",
      "sequence": 0
    }
  ],
  "loop_mode": "continuous",
  "transition_duration": 1000
}
```

**Update Playlist**
```http
PUT /api/v1/signage/video-lists/{list_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description",
  "video_order": [...],
  "loop_mode": "shuffle"
}
```

**Delete Playlist**
```http
DELETE /api/v1/signage/video-lists/{list_id}
```

---

### 2. Devices Tab

#### Functionality
- View all registered signage devices
- Monitor device online/offline status
- Sync playlists to devices
- View device details
- Navigate to device control interface

#### Device Status Indicators
- **🟢 Green:** Device online (heartbeat < 2 minutes)
- **🔴 Red:** Device offline (heartbeat > 2 minutes or not responding)

#### User Actions

**View Devices**
- Automatic refresh every 10 seconds
- Pull-to-refresh for manual update
- Device cards show:
  - Device name
  - IP address and port
  - Online/offline status
  - Current playback info (if available)

**Sync Playlist**
1. Click "Sync" button on device card
2. Select playlist from dialog
3. System syncs playlist to device
4. Success/failure notification shown

**View Device Details**
1. Click "Details" button
2. View full device metadata:
   - Device ID (UUID)
   - Service type
   - Host and port
   - Last heartbeat timestamp
   - Registration time
   - Metadata fields

**Go to Control**
1. Click "Control" button
2. Automatically switches to Control tab
3. Device is pre-selected for immediate control

#### Backend Endpoints

**Get Devices (via Discovery Service)**
```http
GET http://localhost:8006/api/v1/services?service_type=edge
```
Response:
```json
{
  "services": [
    {
      "service_id": "device-uuid",
      "name": "signage-simple-android-MODEL",
      "service_type": "edge",
      "host": "192.168.1.66",
      "port": 8009,
      "status": "healthy",
      "last_seen": "2025-12-09T18:00:00Z",
      "registered_at": "2025-12-09T10:00:00Z",
      "metadata": {
        "device_id": "android-MODEL",
        "platform": "android",
        "version": "1.0.0"
      }
    }
  ],
  "total_count": 1,
  "healthy_count": 1
}
```

**Get Device Status (Direct to Device)**
```http
GET http://{device.host}:{device.port}/api/v1/status
```
Response:
```json
{
  "playback_state": "playing",
  "current_video": {
    "video_id": "vid-uuid",
    "title": "Video Title",
    "duration": 60000,
    "current_position": 15000,
    "progress_percent": 25.0
  },
  "playlist": {
    "id": "playlist-uuid",
    "name": "My Playlist",
    "current_index": 2,
    "total_videos": 10,
    "loop_mode": "continuous"
  },
  "volume": 80,
  "history_count": 15
}
```

**Sync Playlist to Device**
```http
POST /api/v1/signage/sync
Content-Type: application/json

{
  "video_list_id": "playlist-uuid",
  "target_devices": ["device-uuid-1", "device-uuid-2"],
  "sync_mode": "full",
  "force_update": false,
  "notify_on_complete": true
}
```
Response:
```json
{
  "sync_id": "sync-job-uuid",
  "status": "in_progress",
  "target_device_count": 2,
  "started_at": "2025-12-09T18:00:00Z"
}
```

---

### 3. Control Tab

#### Functionality
- Full remote control of selected device
- Real-time playback status monitoring
- Volume adjustment
- Playlist selection and switching
- Playback history viewing

#### Device Selection
- Select device from Devices tab (via "Control" button)
- Or click device in Control tab dropdown
- Selected device persists across tab switches

#### Playback Controls

**Main Control Buttons**
- **Play/Start:** Start playback or resume from paused state
- **Pause:** Pause current video
- **Stop:** Stop playback completely
- **Previous:** Jump to previous video in playlist
- **Next:** Skip to next video in playlist

**Status Display (Auto-refreshes every 3 seconds)**
- Current video title
- Playlist name
- Playback progress bar with percentage
- Current position / Total duration
- Video X of Y in playlist
- Loop mode indicator

**Playlist Selector**
- Dropdown showing all available playlists
- Switch playlist on-the-fly
- "Start Playback" button to begin selected playlist

**Volume Control**
- Slider from 0-100%
- Apply volume to device

#### Backend Endpoints

**Start Playback**
```http
POST /api/v1/signage/playback/start
Content-Type: application/json

{
  "device_ids": ["device-uuid"],
  "video_list_id": "playlist-uuid",
  "start_index": 0,
  "volume": 80
}
```

**Playback Control (Pause/Resume/Stop)**
```http
POST /api/v1/signage/playback/control
Content-Type: application/json

{
  "device_ids": ["device-uuid"],
  "command": "pause"  // or "resume", "stop"
}
```

**Next/Previous Video**
```http
POST /api/v1/signage/playback/control
Content-Type: application/json

{
  "device_ids": ["device-uuid"],
  "command": "next"  // or "previous"
}
```

**Direct Device Control**
The backend sends HTTP requests to the device itself:
```http
POST http://{device.host}:{device.port}/api/v1/control
Content-Type: application/json

{
  "action": "play",  // or "pause", "stop", "next", "previous"
  "playlist_id": "playlist-uuid",
  "start_index": 0,
  "volume": 80
}
```

---

## Technical Implementation Details

### Endpoint Caching Strategy

**Problem:** Repeated discovery service lookups caused performance issues and false device offline marking.

**Solution:** Implemented endpoint caching in `signage_api_client.dart`

```dart
// Cache device endpoints by service ID
Map<String, String> _deviceEndpointCache = {};

// Cache populated when devices are discovered
final endpoint = 'http://${device.host}:${device.port}';
_deviceEndpointCache[device.id] = endpoint;

// Lookups check cache first, then fall back to discovery
final deviceEndpoint = _deviceEndpointCache[deviceId] ?? 
    await _getDeviceEndpointFromDiscovery(deviceId);
```

**Benefits:**
- Reduces network calls by ~90%
- Faster control response times
- Prevents false offline states
- Device endpoints remain valid throughout session

### Device ID Architecture

**Two ID Fields:**
1. **`id`** (UUID): Service ID from discovery service
   - Used for all backend API calls
   - Used for control commands
   - Unique identifier for the service instance

2. **`deviceId`** (String): Device name from metadata
   - Human-readable device identifier
   - Example: "android-TKQ1.221114.001"
   - Used for display purposes only

**Critical:** Always use `device.id` (UUID) for API calls, never `device.deviceId`.

### State Management Flow

**Device List Refresh:**
```
User Action → loadDevices() → Discovery Service API → 
Parse Response → Create SignageDevice objects → 
Cache endpoints → Update provider state → notifyListeners() → 
UI rebuilds with new device data
```

**Playback Control:**
```
User clicks Play → Check device status → 
Determine if stopped or paused →
Call appropriate API (start vs resume) →
Backend routes to device →
Device executes command →
Status auto-refreshes (3s interval) →
UI updates with new state
```

### Periodic Refresh Mechanism

**Devices Tab:**
- Timer-based refresh every 10 seconds
- Calls `loadDevices()` from discovery service
- Updates online/offline status automatically
- Does NOT load individual device statuses (performance optimization)

**Control Tab:**
- Auto-refresh every 3 seconds when device selected
- Calls `loadDeviceStatus(deviceId)` directly to device
- Updates playback progress, current video, playlist info
- Stops when user navigates away (disposed in cleanup)

### Theme Integration

All UI elements use Material 3 color scheme:
- `colorScheme.primary` - Primary brand color (buttons, active states)
- `colorScheme.onSurface` - Main text color
- `colorScheme.onSurfaceVariant` - Secondary text (subtitles, timestamps)
- `colorScheme.surfaceVariant` - Background for secondary surfaces
- `disabledColor: Colors.grey[400]` - Disabled icon states

This ensures proper visibility in both light and dark themes.

---

## API Authentication

All backend API calls require authentication:

**Headers:**
```http
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

JWT tokens obtained from:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password"
}
```

Token automatically included by `signage_api_client.dart` via Dio interceptors.

---

## Error Handling

### Frontend Error States

**No Devices Found:**
- Shows empty state with refresh button
- Message: "No devices found. Make sure signage devices are online"

**Device Offline:**
- Red status indicator
- Control buttons disabled
- Message shown when attempting action

**Sync Failure:**
- SnackBar notification: "Sync failed"
- Retry by clicking sync again

**Playlist Load Failure:**
- Error message in playlist tab
- Retry button available

### Backend Error Responses

**400 Bad Request:**
```json
{
  "detail": "Invalid request parameters"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "device_ids"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error occurred"
}
```

---

## Performance Considerations

### Optimizations Implemented

1. **Endpoint Caching:** Reduces discovery service calls
2. **Lazy Status Loading:** Devices tab doesn't load all statuses
3. **Pagination:** Playlist lists paginated (default 20 per page)
4. **Debounced Search:** Search only triggers on submit/enter
5. **Auto-refresh Intervals:** Balanced between freshness and load
   - Devices: 10 seconds
   - Control status: 3 seconds

### Scalability Metrics

- **Devices:** Tested with 1-10 devices, UI scales to grid layout
- **Playlists:** Pagination handles 100+ playlists
- **Videos per Playlist:** No hard limit, UI handles large lists
- **Concurrent Users:** Backend supports multiple simultaneous control sessions

---

## Development Guidelines

### Adding New Features

**Frontend:**
1. Add model to `signage_models.dart`
2. Add API method to `signage_api_client.dart`
3. Add provider method to `signage_provider.dart`
4. Create/update widget in `widgets/signage/`
5. Integrate into `signage_management_screen.dart`

**Backend:**
1. Add endpoint to appropriate service
2. Update request/response models
3. Add validation logic
4. Document in API docs

### Testing Checklist

**Device Management:**
- [ ] Devices appear when online
- [ ] Status indicator updates correctly
- [ ] Sync operation completes successfully
- [ ] Device details show all metadata

**Playlist Management:**
- [ ] Create playlist with videos
- [ ] Edit existing playlist
- [ ] Delete playlist
- [ ] Search playlists

**Playback Control:**
- [ ] Play starts playlist
- [ ] Pause/Resume works
- [ ] Stop ends playback
- [ ] Next/Previous navigate videos
- [ ] Status updates in real-time
- [ ] Volume changes apply

### Common Issues

**Icons Not Rendering:**
- Use `colorScheme` instead of hardcoded colors
- Set `disabledColor` explicitly on IconButton

**Device Shows Offline When Actually Online:**
- Check endpoint cache
- Verify heartbeat timestamp parsing (UTC vs local time)
- Confirm lastSeen < 2 minutes

**Control Commands Don't Work:**
- Verify using `device.id` (UUID) not `device.deviceId`
- Check device is actually online
- Verify endpoint is reachable
- Check backend logs for routing errors

**Sync Fails:**
- Confirm device has network connectivity
- Verify playlist exists and has videos
- Check device storage space
- Review backend ETL logs

---

## Future Enhancements

### Planned Features

1. **Bulk Operations**
   - Sync to all devices
   - Control multiple devices simultaneously
   - Batch playlist operations

2. **Advanced Scheduling**
   - Time-based playlist switching
   - Day-of-week schedules
   - Event-triggered playback

3. **Analytics Dashboard**
   - Playback statistics
   - Device uptime tracking
   - Content engagement metrics

4. **Enhanced Playlist Features**
   - Dynamic playlists based on tags
   - A/B testing support
   - Priority video insertion

5. **Device Groups**
   - Organize devices by location/purpose
   - Group-based sync and control
   - Hierarchical device management

---

## Related Documentation

- [Signage Quick Start Guide](../SIGNAGE_MANAGEMENT_QUICK_START.md)
- [Backend API Documentation](../../api/)
- [Discovery Service Documentation](../../architecture/discovery-service.md)
- [Android Signage Player Documentation](../../mobile/signage-simple-player.md)

---

## Support & Troubleshooting

**Check Service Health:**
```bash
# Discovery Service
curl http://localhost:8006/health

# Media Service  
curl http://localhost:8000/health

# Gateway Service
curl http://localhost:8080/health

# Device Direct
curl http://{device-ip}:{device-port}/health
```

**View Service Logs:**
- Backend services: Check console output in running terminal
- Frontend: Browser DevTools console
- Device: Android Logcat

**Reset Device Connection:**
1. Stop all services
2. Clear endpoint cache (restart frontend)
3. Restart device
4. Start services
5. Wait for device heartbeat (within 30 seconds)

---

*Last Updated: December 9, 2025*
*Version: 1.0*
