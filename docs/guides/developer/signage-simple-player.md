# Signage Simple Player - Developer Guide

**Document Version:** 1.0  
**Date:** 2 December 2025  
**Status:** Planning & Architecture

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Service Components](#service-components)
4. [Implementation Plan](#implementation-plan)
5. [API Specifications](#api-specifications)
6. [Data Models](#data-models)
7. [Integration Points](#integration-points)
8. [Security & Authentication](#security--authentication)
9. [Deployment](#deployment)
10. [Testing Strategy](#testing-strategy)

---

## 1. Overview

### 1.1 Purpose

The **Signage Simple Player** is a new microservice in the PPL Meta platform designed to provide digital signage capabilities. It enables remote playlist management, synchronized video playback, and comprehensive playback monitoring across distributed Android devices.

### 1.2 Key Features

- **Video List Management**: Create and manage playlists from user collections
- **Remote Playback Control**: Start, pause, and stop playlists remotely
- **ETL Synchronization**: Automated video list syncing between services
- **Playback Monitoring**: Real-time status and comprehensive history tracking
- **Service Discovery**: Full integration with ppl-meta-discovery service
- **Gateway Routing**: Centralized access through ppl-meta-gateway
- **Session Management**: Orchestrator-based endpoint monitoring

### 1.3 Technology Stack

- **Backend Services**: Python 3.11+ with FastAPI
- **Frontend (Signage Player)**: Flutter for Android
- **Video Player**: video_player package with custom controls
- **Service Discovery**: Integration with ppl-meta-discovery
- **API Gateway**: ppl-meta-gateway routing
- **Session Management**: ppl-meta-orchestrator
- **Database**: PostgreSQL for media service, SQLite for local storage

---

## 2. Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PPL Meta Platform                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Gateway    │◄─────┤ Orchestrator │─────►│  Discovery   │ │
│  │   (8080)     │      │   (8002)     │      │   (8006)     │ │
│  └──────┬───────┘      └──────────────┘      └──────────────┘ │
│         │                                                       │
│  ┌──────▼───────────────────────────────────────────────────┐  │
│  │              Service Layer                               │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  ┌──────────────┐         ┌──────────────┐             │  │
│  │  │ Media Service│◄────────┤   Flutter    │             │  │
│  │  │   (8000)     │         │   Frontend   │             │  │
│  │  │              │         │   (3000)     │             │  │
│  │  │ ┌──────────┐ │         └──────────────┘             │  │
│  │  │ │Video List│ │                                      │  │
│  │  │ │Management│ │                                      │  │
│  │  │ └──────────┘ │                                      │  │
│  │  │              │                                      │  │
│  │  │ ┌──────────┐ │         ┌──────────────┐             │  │
│  │  │ │   ETL    │ │◄────────┤   Signage    │             │  │
│  │  │ │ Endpoint │ │         │   Simple     │             │  │
│  │  │ └──────────┘ │         │   Player     │             │  │
│  │  │              │         │  (Android)   │             │  │
│  │  │ ┌──────────┐ │         │              │             │  │
│  │  │ │ Remote   │ │────────►│ ┌──────────┐ │             │  │
│  │  │ │ Control  │ │         │ │  Player  │ │             │  │
│  │  │ └──────────┘ │         │ │  Engine  │ │             │  │
│  │  └──────────────┘         │ └──────────┘ │             │  │
│  │                           │              │             │  │
│  │                           │ ┌──────────┐ │             │  │
│  │                           │ │ History  │ │             │  │
│  │                           │ │ Service  │ │             │  │
│  │                           │ └──────────┘ │             │  │
│  │                           └──────────────┘             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Interactions

```
┌──────────────┐     1. Create Video List      ┌──────────────┐
│   Flutter    │────────────────────────────────►│    Media     │
│   Frontend   │                                │   Service    │
└──────────────┘                                └──────┬───────┘
                                                       │
                                                       │ 2. ETL Sync
                                                       │
┌──────────────┐     3. Sync Request           ┌──────▼───────┐
│   Signage    │◄───────────────────────────────┤    Media     │
│   Simple     │                                │   Service    │
└──────┬───────┘                                └──────────────┘
       │
       │ 4. Register
       │
┌──────▼───────┐     5. Monitor Sessions       ┌──────────────┐
│  Discovery   │◄───────────────────────────────┤ Orchestrator │
│   Service    │                                └──────────────┘
└──────────────┘
```

### 2.3 Data Flow

1. **Video List Creation**: User creates video list in Flutter frontend → Media service
2. **ETL Synchronization**: Media service pushes video list → Signage Simple player
3. **Playback Control**: Media service sends control commands → Signage Simple player
4. **Status Reporting**: Signage Simple continuously reports status → Media service
5. **History Tracking**: Signage Simple logs all playback events locally
6. **Gateway Routing**: All external requests route through ppl-meta-gateway
7. **Session Monitoring**: Orchestrator monitors all endpoint sessions

---

## 3. Service Components

### 3.1 Media Service Enhancements

#### 3.1.1 Video List Management

**Endpoint**: `POST /api/v1/signage/video-lists`

**Purpose**: Create and manage video lists from user collections

**Features**:
- Aggregate videos from multiple user collections
- User-defined video list names
- Order management for playlist sequence
- Metadata association (duration, resolution, etc.)
- Version control for list updates

**Database Schema Addition**:
```sql
CREATE TABLE video_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    loop_mode VARCHAR(50) DEFAULT 'continuous',
    transition_duration INTEGER DEFAULT 0
);

CREATE TABLE video_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_list_id UUID NOT NULL REFERENCES video_lists(id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES collections(id),
    video_id UUID NOT NULL,
    sequence_order INTEGER NOT NULL,
    duration_override INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE video_list_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_list_id UUID NOT NULL REFERENCES video_lists(id),
    signage_device_id UUID NOT NULL,
    sync_status VARCHAR(50) NOT NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);
```

#### 3.1.2 ETL Synchronization Endpoint

**Endpoint**: `POST /api/v1/signage/etl/sync`

**Purpose**: Load/sync video lists to signage devices

**Features**:
- Push-based synchronization
- Incremental updates (only changed videos)
- Batch video metadata transfer
- Resume capability for interrupted syncs
- Conflict resolution strategies

**Sync Process**:
1. Calculate diff between media service list and device list
2. Prepare video metadata package
3. Transfer new/updated video information
4. Verify sync integrity
5. Update sync history
6. Trigger device cache update

**Request/Response**:
```json
// Request
{
    "video_list_id": "uuid",
    "signage_device_id": "uuid",
    "sync_mode": "full|incremental",
    "force_update": false
}

// Response
{
    "sync_id": "uuid",
    "status": "completed|partial|failed",
    "videos_synced": 15,
    "videos_failed": 0,
    "sync_duration_ms": 1250,
    "next_sync_recommended_at": "2025-12-02T10:30:00Z"
}
```

#### 3.1.3 Remote Playback Control Endpoint

**Endpoint**: `POST /api/v1/signage/playback/control`

**Purpose**: Control playlist playback remotely

**Features**:
- Start playlist with specific video
- Pause/resume playback
- Stop and reset playlist
- Skip to next/previous video
- Adjust playback speed
- Volume control

**Control Commands**:
```json
{
    "device_id": "uuid",
    "video_list_id": "uuid",
    "command": "start|pause|resume|stop|next|previous",
    "parameters": {
        "start_index": 0,
        "volume": 80,
        "speed": 1.0
    }
}
```

---

### 3.2 Flutter Frontend Enhancements

#### 3.2.1 Signage Management Screen

**Location**: `lib/screens/signage/signage_management_screen.dart`

**UI Components**:

1. **Video List Management Panel**
   - List all video lists
   - Create new video list button
   - Edit/delete existing lists
   - Search and filter

2. **Collection Selector**
   - Multi-select collections
   - Preview collection videos
   - Drag-and-drop ordering

3. **Playlist Builder**
   - Visual timeline of videos
   - Reorder videos within list
   - Set transitions and durations
   - Preview mode

4. **Device Manager**
   - List connected signage devices
   - Device status indicators
   - Sync controls per device
   - Batch operations

5. **Playback Controller**
   - Remote play/pause/stop controls
   - Current playback status
   - Device-specific controls
   - Volume and speed adjustments

**State Management**:
```dart
class SignageManagementState extends ChangeNotifier {
  List<VideoList> _videoLists = [];
  List<SignageDevice> _devices = [];
  VideoList? _selectedList;
  SignageDevice? _selectedDevice;
  PlaybackStatus? _currentStatus;
  
  // Video List Operations
  Future<void> createVideoList(String name, List<String> collectionIds);
  Future<void> updateVideoList(String listId, VideoListUpdate update);
  Future<void> deleteVideoList(String listId);
  
  // Sync Operations
  Future<void> syncToDevice(String listId, String deviceId);
  Future<void> syncToAllDevices(String listId);
  
  // Playback Control
  Future<void> startPlayback(String deviceId, String listId);
  Future<void> pausePlayback(String deviceId);
  Future<void> stopPlayback(String deviceId);
  
  // Status Monitoring
  Stream<PlaybackStatus> watchPlaybackStatus(String deviceId);
}
```

#### 3.2.2 API Service Layer

**Location**: `lib/services/signage_api_service.dart`

```dart
class SignageApiService {
  final Dio _dio;
  final String _baseUrl;
  
  // Video List Endpoints
  Future<VideoList> createVideoList(CreateVideoListRequest request);
  Future<List<VideoList>> getVideoLists();
  Future<VideoList> getVideoList(String id);
  Future<VideoList> updateVideoList(String id, UpdateVideoListRequest request);
  Future<void> deleteVideoList(String id);
  
  // ETL Endpoints
  Future<SyncResult> syncVideoList(String listId, String deviceId);
  Future<List<SyncHistory>> getSyncHistory(String listId);
  
  // Playback Control Endpoints
  Future<void> controlPlayback(PlaybackControlRequest request);
  Future<PlaybackStatus> getPlaybackStatus(String deviceId);
  
  // Device Management
  Future<List<SignageDevice>> getSignageDevices();
  Future<SignageDevice> getDeviceStatus(String deviceId);
}
```

---

### 3.3 Signage Simple Microservice (Android Flutter App)

#### 3.3.1 Service Discovery Integration

**Implementation**: Auto-registration with ppl-meta-discovery

```dart
class SignageDiscoveryService {
  final DiscoveryClient _client;
  final DeviceInfoService _deviceInfo;
  Timer? _heartbeatTimer;
  
  Future<void> register() async {
    final serviceInfo = ServiceRegistration(
      name: 'signage-simple-${_deviceInfo.deviceId}',
      serviceType: 'signage',
      host: await _getLocalIpAddress(),
      port: 8009,
      metadata: {
        'device_id': _deviceInfo.deviceId,
        'device_name': _deviceInfo.deviceName,
        'android_version': _deviceInfo.androidVersion,
        'screen_resolution': _deviceInfo.screenResolution,
        'capabilities': ['video_playback', 'remote_control', 'history_tracking'],
      },
      healthCheckEndpoint: '/health',
      version: '1.0.0',
    );
    
    await _client.register(serviceInfo);
    _startHeartbeat();
  }
  
  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(
      Duration(seconds: 30),
      (_) => _client.sendHeartbeat(),
    );
  }
  
  Future<void> deregister() async {
    _heartbeatTimer?.cancel();
    await _client.deregister();
  }
}
```

#### 3.3.2 Video Player Engine

**Features**:
- Full-screen video playback
- Seamless transitions between videos
- Loop management
- Buffering optimization
- Error recovery

**Implementation**:
```dart
class SignagePlayerEngine extends ChangeNotifier {
  VideoPlayerController? _currentController;
  VideoPlayerController? _nextController;
  
  PlaylistState _state = PlaylistState.stopped;
  int _currentIndex = 0;
  List<VideoItem> _playlist = [];
  
  // Playback Control
  Future<void> loadPlaylist(List<VideoItem> videos);
  Future<void> play();
  Future<void> pause();
  Future<void> stop();
  Future<void> next();
  Future<void> previous();
  
  // Advanced Features
  void setLoopMode(LoopMode mode);
  void setPlaybackSpeed(double speed);
  void setVolume(double volume);
  
  // Pre-loading Strategy
  Future<void> _preloadNext() async {
    if (_currentIndex + 1 < _playlist.length) {
      final nextVideo = _playlist[_currentIndex + 1];
      _nextController = VideoPlayerController.network(nextVideo.url);
      await _nextController!.initialize();
    }
  }
  
  // Seamless Transition
  Future<void> _transitionToNext() async {
    if (_nextController != null) {
      await _currentController?.dispose();
      _currentController = _nextController;
      _nextController = null;
      _currentIndex++;
      
      await _currentController!.play();
      await _preloadNext();
      
      _logPlaybackEvent('video_started', _playlist[_currentIndex]);
      notifyListeners();
    }
  }
}
```

#### 3.3.3 Local Playlist Synchronization

**Database**: SQLite for local storage

```dart
class PlaylistDatabase {
  static const String _dbName = 'signage_playlists.db';
  Database? _db;
  
  Future<void> init() async {
    _db = await openDatabase(
      join(await getDatabasesPath(), _dbName),
      onCreate: (db, version) {
        return db.execute('''
          CREATE TABLE playlists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_list_id TEXT NOT NULL,
            last_synced_at TEXT,
            sync_version INTEGER,
            is_active INTEGER DEFAULT 1
          );
          
          CREATE TABLE playlist_videos (
            id TEXT PRIMARY KEY,
            playlist_id TEXT NOT NULL,
            video_id TEXT NOT NULL,
            sequence_order INTEGER NOT NULL,
            video_url TEXT NOT NULL,
            video_title TEXT,
            duration_ms INTEGER,
            metadata TEXT,
            FOREIGN KEY (playlist_id) REFERENCES playlists (id)
          );
        ''');
      },
      version: 1,
    );
  }
  
  Future<void> syncPlaylist(VideoList remoteList) async {
    final batch = _db!.batch();
    
    // Upsert playlist
    batch.insert(
      'playlists',
      remoteList.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    
    // Delete old videos
    batch.delete(
      'playlist_videos',
      where: 'playlist_id = ?',
      whereArgs: [remoteList.id],
    );
    
    // Insert new videos
    for (var video in remoteList.videos) {
      batch.insert('playlist_videos', video.toMap());
    }
    
    await batch.commit(noResult: true);
  }
}
```

#### 3.3.4 Health Endpoints

**Implementation**: Embedded HTTP server

```dart
class SignageHttpServer {
  HttpServer? _server;
  final int port = 8009;
  
  Future<void> start() async {
    _server = await HttpServer.bind(InternetAddress.anyIPv4, port);
    print('Signage HTTP server listening on port $port');
    
    await for (HttpRequest request in _server!) {
      _handleRequest(request);
    }
  }
  
  void _handleRequest(HttpRequest request) {
    final path = request.uri.path;
    
    switch (path) {
      case '/health':
        _handleHealth(request);
        break;
      case '/api/v1/status':
        _handleStatus(request);
        break;
      case '/api/v1/history':
        _handleHistory(request);
        break;
      case '/api/v1/control':
        _handleControl(request);
        break;
      default:
        _send404(request);
    }
  }
  
  void _handleHealth(HttpRequest request) {
    final response = {
      'status': 'healthy',
      'service': 'signage-simple',
      'timestamp': DateTime.now().toIso8601String(),
      'uptime_seconds': _getUptimeSeconds(),
      'player_state': _playerEngine.state.toString(),
    };
    
    _sendJson(request, response);
  }
}
```

#### 3.3.5 Status Endpoint

**Endpoint**: `GET /api/v1/status`

**Response**:
```json
{
  "device_id": "uuid",
  "current_video": {
    "video_id": "uuid",
    "title": "Video Title",
    "position_ms": 45000,
    "duration_ms": 120000,
    "progress_percent": 37.5
  },
  "playlist": {
    "id": "uuid",
    "name": "Playlist Name",
    "total_videos": 10,
    "current_index": 3
  },
  "playback_state": "playing|paused|stopped",
  "recently_played": [
    {
      "video_id": "uuid",
      "title": "Previous Video 1",
      "completed_at": "2025-12-02T10:15:00Z"
    }
  ],
  "upcoming_videos": [
    {
      "video_id": "uuid",
      "title": "Next Video 1",
      "sequence_order": 4
    }
  ],
  "history_count": 5,
  "upcoming_count": 6
}
```

**Configuration**:
```dart
class StatusConfiguration {
  static const int recentlyPlayedLimit = 5;
  static const int upcomingVideosLimit = 10;
}
```

#### 3.3.6 History & Reporting Service

**Endpoint**: `GET /api/v1/history`

**Query Parameters**:
- `start_date`: ISO 8601 date
- `end_date`: ISO 8601 date
- `video_id`: Filter by specific video
- `playlist_id`: Filter by playlist
- `page`: Pagination page number
- `limit`: Results per page
- `sort`: `asc|desc`

**Response**:
```json
{
  "total_count": 250,
  "page": 1,
  "page_size": 50,
  "total_pages": 5,
  "results": [
    {
      "id": "uuid",
      "video_id": "uuid",
      "video_title": "Video Title",
      "playlist_id": "uuid",
      "playlist_name": "Playlist Name",
      "started_at": "2025-12-02T10:00:00Z",
      "completed_at": "2025-12-02T10:02:30Z",
      "duration_played_ms": 150000,
      "completion_percent": 100,
      "playback_quality": "1080p",
      "interruptions": 0,
      "error_occurred": false
    }
  ],
  "summary": {
    "total_playback_time_ms": 3600000,
    "unique_videos_played": 15,
    "average_completion_rate": 98.5,
    "most_played_video": {
      "video_id": "uuid",
      "play_count": 10
    }
  }
}
```

**Database Schema**:
```sql
CREATE TABLE playback_history (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    video_title TEXT,
    playlist_id TEXT,
    playlist_name TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_played_ms INTEGER,
    completion_percent REAL,
    playback_quality TEXT,
    interruptions INTEGER DEFAULT 0,
    error_occurred INTEGER DEFAULT 0,
    error_message TEXT,
    device_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_playback_started_at ON playback_history(started_at);
CREATE INDEX idx_playback_video_id ON playback_history(video_id);
CREATE INDEX idx_playback_playlist_id ON playback_history(playlist_id);
```

**History Service Implementation**:
```dart
class PlaybackHistoryService {
  final PlaylistDatabase _db;
  
  Future<void> logPlaybackStart(VideoItem video, String playlistId) async {
    final entry = PlaybackHistoryEntry(
      id: Uuid().v4(),
      videoId: video.id,
      videoTitle: video.title,
      playlistId: playlistId,
      startedAt: DateTime.now(),
      deviceId: await _getDeviceId(),
    );
    
    await _db.insertHistory(entry);
  }
  
  Future<void> logPlaybackComplete(String entryId, Duration played) async {
    await _db.updateHistory(entryId, {
      'completed_at': DateTime.now().toIso8601String(),
      'duration_played_ms': played.inMilliseconds,
      'completion_percent': 100.0,
    });
  }
  
  Future<HistoryQueryResult> queryHistory({
    DateTime? startDate,
    DateTime? endDate,
    String? videoId,
    String? playlistId,
    int page = 1,
    int limit = 50,
    String sort = 'desc',
  }) async {
    final results = await _db.queryHistory(
      startDate: startDate,
      endDate: endDate,
      videoId: videoId,
      playlistId: playlistId,
      offset: (page - 1) * limit,
      limit: limit,
      orderBy: 'started_at $sort',
    );
    
    final totalCount = await _db.countHistory(
      startDate: startDate,
      endDate: endDate,
      videoId: videoId,
      playlistId: playlistId,
    );
    
    return HistoryQueryResult(
      results: results,
      totalCount: totalCount,
      page: page,
      pageSize: limit,
    );
  }
  
  Future<PlaybackSummary> getSummary({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    return await _db.getPlaybackSummary(
      startDate: startDate,
      endDate: endDate,
    );
  }
}
```

---

## 4. Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### Week 1: Media Service Enhancements
- [ ] Design and implement database schema for video lists
- [ ] Create video list CRUD endpoints
- [ ] Implement collection aggregation logic
- [ ] Add unit tests for video list management
- [ ] Document API endpoints

#### Week 2: ETL & Control Endpoints
- [ ] Implement ETL synchronization endpoint
- [ ] Create diff calculation algorithm
- [ ] Add remote playback control endpoint
- [ ] Implement WebSocket for real-time updates
- [ ] Integration tests for sync process

### Phase 2: Frontend Development (Week 3-4)

#### Week 3: Signage Management UI
- [ ] Create signage management screen layout
- [ ] Implement video list builder UI
- [ ] Add collection selector component
- [ ] Create device manager panel
- [ ] Implement state management

#### Week 4: Playback Control UI
- [ ] Create remote control interface
- [ ] Add status monitoring dashboard
- [ ] Implement real-time sync status display
- [ ] Add error handling and notifications
- [ ] UI/UX testing and refinement

### Phase 3: Signage Simple Microservice (Week 5-7)

#### Week 5: Core Infrastructure
- [ ] Set up Flutter Android project
- [ ] Implement service discovery integration
- [ ] Create embedded HTTP server
- [ ] Add health endpoint
- [ ] Implement local SQLite database

#### Week 6: Video Player Engine
- [ ] Integrate video_player package
- [ ] Implement playlist management
- [ ] Create seamless transition logic
- [ ] Add pre-loading optimization
- [ ] Implement loop modes

#### Week 7: Sync & History
- [ ] Implement playlist sync from media service
- [ ] Create status endpoint
- [ ] Build history tracking system
- [ ] Add history query endpoint with search
- [ ] Implement local data cleanup policies

### Phase 4: Integration & Gateway (Week 8)

- [ ] Configure gateway routing for all endpoints
- [ ] Integrate orchestrator session monitoring
- [ ] End-to-end integration testing
- [ ] Load testing and optimization
- [ ] Security audit and fixes

### Phase 5: Testing & Deployment (Week 9-10)

#### Week 9: Testing
- [ ] Unit tests (target: >80% coverage)
- [ ] Integration tests
- [ ] E2E tests with real devices
- [ ] Performance testing
- [ ] User acceptance testing

#### Week 10: Deployment
- [ ] Prepare deployment documentation
- [ ] Create Docker containers (if applicable)
- [ ] Set up CI/CD pipelines
- [ ] Deploy to staging environment
- [ ] Production deployment
- [ ] Post-deployment monitoring

---

## 5. API Specifications

### 5.1 Media Service APIs

#### 5.1.1 Create Video List

**Endpoint**: `POST /api/v1/signage/video-lists`

**Request**:
```json
{
  "name": "Morning Playlist",
  "description": "Videos for morning display",
  "collection_ids": [
    "collection-uuid-1",
    "collection-uuid-2"
  ],
  "video_order": [
    {"collection_id": "uuid", "video_id": "uuid", "sequence": 1},
    {"collection_id": "uuid", "video_id": "uuid", "sequence": 2}
  ],
  "loop_mode": "continuous",
  "transition_duration_ms": 1000
}
```

**Response**: `201 Created`
```json
{
  "id": "video-list-uuid",
  "name": "Morning Playlist",
  "description": "Videos for morning display",
  "video_count": 15,
  "total_duration_ms": 1800000,
  "created_at": "2025-12-02T10:00:00Z",
  "updated_at": "2025-12-02T10:00:00Z"
}
```

#### 5.1.2 Get Video Lists

**Endpoint**: `GET /api/v1/signage/video-lists`

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Results per page (default: 20)
- `search`: Search by name
- `is_active`: Filter by active status

**Response**: `200 OK`
```json
{
  "total_count": 50,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": "uuid",
      "name": "Morning Playlist",
      "video_count": 15,
      "total_duration_ms": 1800000,
      "is_active": true,
      "last_synced_at": "2025-12-02T09:00:00Z"
    }
  ]
}
```

#### 5.1.3 Update Video List

**Endpoint**: `PUT /api/v1/signage/video-lists/{list_id}`

**Request**: Same as create

**Response**: `200 OK` with updated object

#### 5.1.4 Delete Video List

**Endpoint**: `DELETE /api/v1/signage/video-lists/{list_id}`

**Response**: `204 No Content`

#### 5.1.5 Sync Video List to Device

**Endpoint**: `POST /api/v1/signage/etl/sync`

**Request**:
```json
{
  "video_list_id": "uuid",
  "target_devices": ["device-uuid-1", "device-uuid-2"],
  "sync_mode": "incremental",
  "force_update": false,
  "notify_on_complete": true
}
```

**Response**: `202 Accepted`
```json
{
  "sync_job_id": "uuid",
  "status": "in_progress",
  "target_device_count": 2,
  "estimated_completion_at": "2025-12-02T10:05:00Z"
}
```

#### 5.1.6 Remote Playback Control

**Endpoint**: `POST /api/v1/signage/playback/control`

**Request**:
```json
{
  "device_ids": ["device-uuid"],
  "command": "start",
  "video_list_id": "uuid",
  "parameters": {
    "start_index": 0,
    "volume": 80,
    "speed": 1.0
  }
}
```

**Response**: `200 OK`
```json
{
  "command_id": "uuid",
  "status": "executed",
  "affected_devices": 1,
  "executed_at": "2025-12-02T10:00:00Z"
}
```

### 5.2 Signage Simple APIs

#### 5.2.1 Health Check

**Endpoint**: `GET /health`

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "signage-simple",
  "version": "1.0.0",
  "device_id": "uuid",
  "timestamp": "2025-12-02T10:00:00Z",
  "uptime_seconds": 86400,
  "player_state": "playing"
}
```

#### 5.2.2 Playback Status

**Endpoint**: `GET /api/v1/status`

**Response**: See section 3.3.5

#### 5.2.3 Playback History

**Endpoint**: `GET /api/v1/history`

**Query Parameters**: See section 3.3.6

**Response**: See section 3.3.6

#### 5.2.4 Local Control

**Endpoint**: `POST /api/v1/control`

**Request**:
```json
{
  "command": "pause",
  "timestamp": "2025-12-02T10:00:00Z"
}
```

**Response**: `200 OK`
```json
{
  "status": "success",
  "command": "pause",
  "executed_at": "2025-12-02T10:00:00Z",
  "new_state": "paused"
}
```

---

## 6. Data Models

### 6.1 Video List Model

```python
# Media Service
class VideoList(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    user_id: UUID
    collection_ids: List[UUID]
    video_items: List[VideoListItem]
    loop_mode: LoopMode
    transition_duration_ms: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
class VideoListItem(BaseModel):
    id: UUID
    video_id: UUID
    collection_id: UUID
    sequence_order: int
    duration_override: Optional[int]
    metadata: Dict[str, Any]
```

### 6.2 Sync Models

```python
class SyncRequest(BaseModel):
    video_list_id: UUID
    target_devices: List[UUID]
    sync_mode: SyncMode  # full, incremental
    force_update: bool = False
    
class SyncResult(BaseModel):
    sync_job_id: UUID
    video_list_id: UUID
    device_id: UUID
    status: SyncStatus  # completed, partial, failed
    videos_synced: int
    videos_failed: int
    sync_duration_ms: int
    error_message: Optional[str]
```

### 6.3 Playback Models

```python
class PlaybackControlRequest(BaseModel):
    device_ids: List[UUID]
    command: PlaybackCommand  # start, pause, resume, stop, next, previous
    video_list_id: Optional[UUID]
    parameters: PlaybackParameters
    
class PlaybackParameters(BaseModel):
    start_index: int = 0
    volume: int = 80
    speed: float = 1.0
    
class PlaybackStatus(BaseModel):
    device_id: UUID
    current_video: Optional[CurrentVideoInfo]
    playlist: Optional[PlaylistInfo]
    playback_state: PlaybackState
    recently_played: List[VideoHistoryItem]
    upcoming_videos: List[VideoListItem]
```

### 6.4 Flutter/Dart Models

```dart
// Signage Simple
class VideoList {
  final String id;
  final String name;
  final String? description;
  final List<VideoItem> videos;
  final LoopMode loopMode;
  final DateTime lastSyncedAt;
  
  VideoList({...});
  
  factory VideoList.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}

class VideoItem {
  final String id;
  final String videoId;
  final String title;
  final String url;
  final int sequenceOrder;
  final Duration duration;
  final Map<String, dynamic> metadata;
  
  VideoItem({...});
}

class PlaybackHistoryEntry {
  final String id;
  final String videoId;
  final String videoTitle;
  final String playlistId;
  final DateTime startedAt;
  final DateTime? completedAt;
  final Duration durationPlayed;
  final double completionPercent;
  final bool errorOccurred;
  
  PlaybackHistoryEntry({...});
}
```

---

## 7. Integration Points

### 7.1 Gateway Routing Configuration

**File**: `ppl-meta-gateway/src/config/routes.py`

```python
# Signage-related routes
signage_routes = [
    # Media Service - Video List Management
    Route(
        path="/api/v1/signage/video-lists",
        methods=["GET", "POST"],
        target="http://ppl-meta-media:8000",
        auth_required=True,
        rate_limit="100/minute"
    ),
    Route(
        path="/api/v1/signage/video-lists/{list_id}",
        methods=["GET", "PUT", "DELETE"],
        target="http://ppl-meta-media:8000",
        auth_required=True
    ),
    
    # Media Service - ETL & Control
    Route(
        path="/api/v1/signage/etl/sync",
        methods=["POST"],
        target="http://ppl-meta-media:8000",
        auth_required=True,
        timeout=300  # 5 minutes for sync
    ),
    Route(
        path="/api/v1/signage/playback/control",
        methods=["POST"],
        target="http://ppl-meta-media:8000",
        auth_required=True
    ),
    
    # Signage Simple Device Endpoints
    Route(
        path="/api/v1/signage/devices/{device_id}/status",
        methods=["GET"],
        target_resolver=resolve_device_endpoint,
        auth_required=True
    ),
    Route(
        path="/api/v1/signage/devices/{device_id}/history",
        methods=["GET"],
        target_resolver=resolve_device_endpoint,
        auth_required=True
    ),
    Route(
        path="/api/v1/signage/devices/{device_id}/health",
        methods=["GET"],
        target_resolver=resolve_device_endpoint,
        auth_required=False  # Health check is public
    ),
]

def resolve_device_endpoint(device_id: str) -> str:
    """Query discovery service for device endpoint"""
    device = discovery_client.get_service(f"signage-simple-{device_id}")
    return f"http://{device.host}:{device.port}"
```

### 7.2 Orchestrator Session Monitoring

**File**: `ppl-meta-orchestrator/src/monitors/signage_monitor.py`

```python
class SignageEndpointMonitor:
    """Monitor all signage-related endpoints with session tracking"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.monitored_endpoints = [
            "/api/v1/signage/video-lists",
            "/api/v1/signage/etl/sync",
            "/api/v1/signage/playback/control",
            "/api/v1/signage/devices/{device_id}/status",
            "/api/v1/signage/devices/{device_id}/history",
        ]
    
    async def track_request(self, request: Request):
        """Track signage-related request in session"""
        session = await self.session_manager.create_session(
            user_id=request.user.id,
            endpoint=request.url.path,
            service="signage",
            metadata={
                "device_id": request.path_params.get("device_id"),
                "video_list_id": request.query_params.get("video_list_id"),
            }
        )
        
        return session.id
    
    async def track_response(self, session_id: str, response: Response):
        """Complete session tracking with response"""
        await self.session_manager.complete_session(
            session_id=session_id,
            status_code=response.status_code,
            response_time_ms=response.elapsed_ms,
        )
    
    async def monitor_device_health(self):
        """Background task to monitor device health"""
        while True:
            devices = await discovery_client.get_services(service_type="signage")
            
            for device in devices:
                try:
                    health = await self.check_device_health(device)
                    await self.log_health_status(device.id, health)
                except Exception as e:
                    await self.handle_unhealthy_device(device, e)
            
            await asyncio.sleep(60)  # Check every minute
```

### 7.3 Discovery Service Registration

**Configuration**:
```dart
// In Signage Simple app
class SignageServiceConfig {
  static const String serviceName = 'signage-simple';
  static const String serviceType = 'signage';
  static const int servicePort = 8009;
  static const Duration heartbeatInterval = Duration(seconds: 30);
  static const Duration registrationRetryDelay = Duration(seconds: 10);
  
  static Map<String, dynamic> getServiceMetadata(DeviceInfo device) {
    return {
      'device_id': device.id,
      'device_name': device.name,
      'android_version': device.androidVersion,
      'app_version': packageInfo.version,
      'screen_width': device.screenWidth,
      'screen_height': device.screenHeight,
      'capabilities': [
        'video_playback',
        'remote_control',
        'playlist_sync',
        'history_tracking',
      ],
      'max_video_resolution': '1920x1080',
      'supported_codecs': ['h264', 'vp9'],
    };
  }
}
```

---

## 8. Security & Authentication

### 8.1 Authentication Flow

1. **Flutter Frontend → Media Service**
   - Use existing PPL Meta authentication (JWT tokens)
   - Token refresh mechanism
   - Role-based access control (admin, operator, viewer)

2. **Media Service → Signage Simple**
   - API key authentication for device registration
   - Mutual TLS for production deployments
   - Signed sync requests to prevent tampering

3. **Gateway → All Services**
   - Centralized authentication verification
   - Rate limiting per user/device
   - Request signing for internal communication

### 8.2 Authorization Levels

**User Roles**:
- **Admin**: Full control over video lists, devices, and playback
- **Operator**: Can control playback, view status, manage playlists
- **Viewer**: Read-only access to status and history

**Device Permissions**:
- Signage devices have limited API access
- Cannot create/modify video lists
- Can only report status and sync assigned playlists

### 8.3 Security Best Practices

```python
# Media Service security configuration
SECURITY_CONFIG = {
    "api_key_rotation_days": 90,
    "max_sync_retries": 3,
    "sync_timeout_seconds": 300,
    "device_token_expiry_days": 365,
    "require_https": True,
    "allowed_origins": [
        "http://localhost:3000",  # Development
        "https://ppl-meta.example.com",  # Production
    ],
}

# Rate limiting
RATE_LIMITS = {
    "/api/v1/signage/video-lists": "100/minute",
    "/api/v1/signage/etl/sync": "10/minute",  # Expensive operation
    "/api/v1/signage/playback/control": "50/minute",
}
```

---

## 9. Deployment

### 9.1 Service Deployment

#### Media Service Updates
```bash
# Update requirements.txt
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart service
cd ppl-meta-media
source venv/bin/activate
python src/main.py
```

#### Flutter Frontend Updates
```bash
cd ppl-meta-frontend
flutter pub get
flutter build web --release
# Deploy to hosting
```

#### Signage Simple App
```bash
cd signage-simple
flutter pub get
flutter build apk --release
# Distribute APK to Android devices
```

### 9.2 Infrastructure Requirements

**Media Service**:
- CPU: +10% for video list processing
- Memory: +256MB for ETL operations
- Storage: Negligible (metadata only)
- Network: Moderate (sync operations)

**Signage Simple**:
- Android 8.0+ (API level 26+)
- Minimum 2GB RAM
- 4GB storage for video caching
- Stable network connection (WiFi recommended)
- 1080p display support

### 9.3 Monitoring & Observability

**Metrics to Track**:
- Video list creation/update rate
- Sync success/failure rate
- Average sync duration
- Playback uptime per device
- History query performance
- Device offline duration

**Alerting**:
- Device offline > 5 minutes
- Sync failure rate > 10%
- Playback errors > 5% of attempts
- History database size > 80% capacity

**Logging**:
```python
# Structured logging example
logger.info(
    "video_list_created",
    extra={
        "video_list_id": list_id,
        "user_id": user_id,
        "video_count": len(videos),
        "collections": collection_ids,
    }
)

logger.error(
    "sync_failed",
    extra={
        "video_list_id": list_id,
        "device_id": device_id,
        "error": str(e),
        "retry_count": retry_count,
    }
)
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Media Service**:
```python
# tests/test_video_list_service.py
def test_create_video_list_with_multiple_collections():
    service = VideoListService()
    request = CreateVideoListRequest(
        name="Test Playlist",
        collection_ids=["col1", "col2"],
    )
    result = service.create_video_list(request)
    assert result.video_count == expected_count

def test_sync_incremental_update():
    service = ETLService()
    result = service.sync_video_list(
        list_id="list1",
        device_id="device1",
        mode=SyncMode.INCREMENTAL
    )
    assert result.videos_synced < total_videos
```

**Signage Simple**:
```dart
// test/player_engine_test.dart
void main() {
  group('SignagePlayerEngine', () {
    test('loads playlist successfully', () async {
      final engine = SignagePlayerEngine();
      final videos = [VideoItem(...)];
      
      await engine.loadPlaylist(videos);
      
      expect(engine.playlist.length, equals(videos.length));
      expect(engine.state, equals(PlaylistState.loaded));
    });
    
    test('transitions to next video seamlessly', () async {
      final engine = SignagePlayerEngine();
      await engine.loadPlaylist(mockVideos);
      await engine.play();
      
      await engine.next();
      
      expect(engine.currentIndex, equals(1));
      expect(engine.isPlaying, isTrue);
    });
  });
}
```

### 10.2 Integration Tests

```python
# tests/integration/test_signage_flow.py
@pytest.mark.integration
async def test_complete_signage_workflow():
    """Test end-to-end signage workflow"""
    # 1. Create video list
    video_list = await media_client.create_video_list({
        "name": "Test List",
        "collection_ids": [collection_id],
    })
    
    # 2. Sync to device
    sync_result = await media_client.sync_to_device(
        video_list.id,
        device_id
    )
    assert sync_result.status == "completed"
    
    # 3. Verify device has playlist
    device_status = await signage_client.get_status(device_id)
    assert device_status.playlist.id == video_list.id
    
    # 4. Start playback
    await media_client.control_playback(
        device_id,
        command="start",
        video_list_id=video_list.id
    )
    
    # 5. Verify playback started
    await asyncio.sleep(2)
    status = await signage_client.get_status(device_id)
    assert status.playback_state == "playing"
```

### 10.3 E2E Tests

```dart
// integration_test/signage_e2e_test.dart
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  
  testWidgets('Complete signage management flow', (tester) async {
    // Launch app
    app.main();
    await tester.pumpAndSettle();
    
    // Navigate to signage management
    await tester.tap(find.byIcon(Icons.video_library));
    await tester.pumpAndSettle();
    
    // Create video list
    await tester.tap(find.text('Create Playlist'));
    await tester.pumpAndSettle();
    
    await tester.enterText(
      find.byKey(Key('playlist_name')),
      'E2E Test Playlist'
    );
    
    await tester.tap(find.text('Add Collections'));
    await tester.tap(find.text('Collection 1'));
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    
    // Verify playlist created
    expect(find.text('E2E Test Playlist'), findsOneWidget);
    
    // Sync to device
    await tester.tap(find.byIcon(Icons.sync));
    await tester.pumpAndSettle();
    
    // Verify sync success
    expect(find.text('Synced'), findsWidgets);
  });
}
```

### 10.4 Performance Tests

```python
# tests/performance/test_load.py
import locust

class SignageUserBehavior(locust.HttpUser):
    wait_time = locust.between(1, 3)
    
    @locust.task(3)
    def get_video_lists(self):
        self.client.get("/api/v1/signage/video-lists")
    
    @locust.task(1)
    def create_video_list(self):
        self.client.post(
            "/api/v1/signage/video-lists",
            json={
                "name": f"Load Test {uuid.uuid4()}",
                "collection_ids": [self.collection_id],
            }
        )
    
    @locust.task(2)
    def get_device_status(self):
        device_id = random.choice(self.device_ids)
        self.client.get(f"/api/v1/signage/devices/{device_id}/status")

# Run: locust -f test_load.py --host=http://localhost:8000
```

---

## 11. Additional Considerations

### 11.1 Video Caching Strategy

Signage devices should implement intelligent caching:
- Cache videos locally after first playback
- Pre-fetch upcoming videos in playlist
- Manage cache size (max 10GB by default)
- Clear old videos using LRU policy

### 11.2 Network Resilience

- Offline playback support for cached videos
- Queue sync operations when network unavailable
- Resume interrupted syncs automatically
- Graceful degradation when media service unreachable

### 11.3 Analytics & Insights

Consider adding analytics endpoints:
- Device uptime statistics
- Video engagement metrics (most/least played)
- Playback quality analytics
- Network performance metrics

### 11.4 Future Enhancements

**Phase 2 Features**:
- Multi-zone playback (different playlists per screen region)
- Interactive content support
- Scheduled playlist changes (time-based)
- A/B testing for content
- Real-time content updates without sync
- Content approval workflows
- Advanced scheduling (date/time/day-of-week rules)

**Phase 3 Features**:
- AI-powered content recommendations
- Dynamic content insertion (weather, news, etc.)
- Touch interaction support
- Multi-device synchronization (play same video on multiple screens)
- Emergency broadcast system
- Content analytics dashboard

---

## 12. Conclusion

The Signage Simple Player represents a significant expansion of the PPL Meta platform, adding comprehensive digital signage capabilities. By following this implementation guide, developers can create a robust, scalable, and feature-rich signage solution that integrates seamlessly with the existing platform infrastructure.

### Key Success Factors

1. **Robust Synchronization**: Reliable ETL process ensures content is always up-to-date
2. **Seamless Playback**: Optimized video player with pre-loading prevents interruptions
3. **Comprehensive Monitoring**: Real-time status and history tracking enable proactive management
4. **Platform Integration**: Full integration with discovery, gateway, and orchestrator services
5. **User-Friendly Management**: Intuitive Flutter UI for playlist and device management

### Next Steps

1. Review and approve architecture
2. Set up development environment
3. Create detailed technical specifications for each component
4. Begin Phase 1 implementation
5. Establish testing and deployment pipelines

---

**Document Maintainers**: PPL Meta Development Team  
**Last Updated**: 2 December 2025  
**Review Schedule**: Weekly during development, monthly post-deployment

