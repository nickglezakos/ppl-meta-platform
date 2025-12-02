# PPL Meta Signage Simple Player

A Flutter-based digital signage player application for the PPL Meta platform. This app runs on macOS (development) and Android devices, providing remote playlist management, synchronized video playback, and comprehensive monitoring capabilities.

## Features

- **Video Playlist Playback**: Seamless playback of video playlists with pre-loading and smooth transitions
- **Manual Playlist Sync**: On-demand synchronization with backend ETL endpoint (no automatic syncing)
- **Remote Control**: Start, pause, stop, and navigate playlists remotely via backend API
- **Service Discovery**: Auto-registration with ppl-meta-discovery service for zero-configuration deployment
- **Playback History**: Comprehensive tracking of all video playback with batch reporting
- **Embedded HTTP Server**: Built-in server for health checks, status reporting, and control endpoints (port 8009)
- **Local Storage**: SQLite database for offline playlist caching and history persistence
- **Real-time Status**: Continuous reporting of playback status to backend services
- **Full-Screen Player UI**: Dedicated player screen with playlist info, progress indicators, and controls

## Architecture

The application follows a clean architecture pattern with clear separation of concerns:

### Core Services

1. **SignagePlayerEngine** - Video playback management with video_player
2. **SyncService** - Manual playlist synchronization with backend
3. **HistoryTrackingService** - Playback completion tracking and batch reporting
4. **SignageHttpServer** - Embedded HTTP server for remote control
5. **SignageDiscoveryService** - Auto-registration with discovery service
6. **PlaylistDatabase** - SQLite storage for playlists and metadata
7. **SignageApiClient** - Backend API communication with Dio

### Project Structure

```
lib/
├── main.dart                          # Application entry point with Provider setup
├── config/
│   └── app_config.dart                # Configuration (backend URLs, ports, device info)
├── models/
│   ├── video_list.dart                # VideoList and VideoItem models
│   ├── device_info_model.dart         # Device registration model
│   └── playback_history_model.dart    # Playback tracking model
├── services/
│   ├── player_engine.dart             # Video player engine (23 tests)
│   ├── sync_service.dart              # Manual playlist sync (23 tests)
│   ├── history_tracking_service.dart  # History tracking (18 tests)
│   ├── http_server.dart               # Embedded HTTP server (25 tests)
│   └── discovery_service.dart         # Service discovery (15 tests)
├── database/
│   └── playlist_database.dart         # SQLite database layer (20 tests)
├── api/
│   ├── signage_api_client.dart        # Backend API client
│   └── api_exceptions.dart            # API error handling
├── screens/
│   └── player_screen.dart             # Full-screen player UI
└── widgets/
    └── video_player_widget.dart       # Video player widget component

test/
├── services/                           # Unit tests for services
├── database/                           # Database tests
├── api/                                # API client tests
└── integration/                        # Integration tests
    └── full_workflow_test.dart         # End-to-end workflow tests
```

## Getting Started

### Prerequisites

- Flutter SDK 3.8.1 or higher
- macOS (for development) or Android device/emulator
- PPL Meta backend services running:
  - ppl-meta-discovery (port 8006) - Service registration
  - ppl-meta-media (port 8000) - Playlist management
  - ppl-meta-gateway (port 8080) - API gateway

### Installation

```bash
# Navigate to project directory
cd ppl-meta-signage-simple-player

# Install Flutter dependencies
flutter pub get

# Generate JSON serialization and mock code
flutter pub run build_runner build --delete-conflicting-outputs

# Run tests to verify setup
flutter test
```

### Configuration

Configure the application in `lib/config/app_config.dart`:

```dart
class AppConfig {
  // Backend service URLs
  static const String discoveryServiceUrl = 'http://localhost:8006';
  static const String mediaServiceUrl = 'http://localhost:8000';
  static const String gatewayUrl = 'http://localhost:8080';
  
  // Device configuration
  static String deviceId = 'signage-player-${Platform.localHostname}';
  static const String deviceName = 'Signage Player';
  static const int httpServerPort = 8009;
  
  // Sync configuration
  static const Duration syncInterval = Duration(hours: 1); // Informational only
  static const int maxHistoryBatchSize = 100;
}
```

### Running the Application

```bash
# Run on macOS (development)
flutter run -d macos

# Run on Android device
flutter run -d android

# Run with specific device ID
flutter run -d <device-id>

# Build release version for Android
flutter build apk --release
```

### First-Time Setup

1. **Start Backend Services**: Ensure ppl-meta-discovery and ppl-meta-media are running
2. **Launch Application**: The app will auto-register with discovery service
3. **Assign Playlist**: Use backend API to assign a playlist to this device
4. **Manual Sync**: Trigger sync from the UI or via HTTP endpoint
5. **Playback**: Playlist will automatically start playing

## API Endpoints

The embedded HTTP server runs on **port 8009** and provides the following endpoints:

### Health & Status

#### `GET /health`
Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "signage-simple-player",
  "version": "1.0.0",
  "timestamp": "2025-12-02T10:30:00Z"
}
```

#### `GET /api/v1/status`
Returns detailed playback status.

**Response:**
```json
{
  "device_id": "signage-player-macbook",
  "is_playing": true,
  "current_playlist": {
    "id": "playlist-123",
    "name": "Store Front Display",
    "video_count": 5
  },
  "current_video": {
    "index": 2,
    "id": "video-456",
    "title": "Product Showcase",
    "progress": 0.65
  },
  "last_sync": "2025-12-02T10:15:00Z"
}
```

#### `GET /api/v1/history`
Returns playback history.

**Query Parameters:**
- `limit` (optional): Number of records to return (default: 50)
- `playlist_id` (optional): Filter by playlist ID

**Response:**
```json
{
  "total": 150,
  "history": [
    {
      "video_id": "video-456",
      "playlist_id": "playlist-123",
      "started_at": "2025-12-02T10:20:00Z",
      "completed_at": "2025-12-02T10:22:30Z",
      "completion_status": "completed",
      "actual_duration_ms": 150000
    }
  ]
}
```

### Control Commands

#### `POST /api/v1/control`
Send control commands to the player.

**Request Body:**
```json
{
  "command": "play|pause|stop|next|previous|load",
  "playlist_id": "playlist-123"  // Required for 'load' command
}
```

**Response:**
```json
{
  "success": true,
  "message": "Command executed successfully",
  "new_state": {
    "is_playing": true,
    "current_index": 3
  }
}
```

**Supported Commands:**
- `play` - Resume playback
- `pause` - Pause playback
- `stop` - Stop playback and reset
- `next` - Skip to next video
- `previous` - Go to previous video
- `load` - Load a specific playlist by ID

#### `POST /api/v1/sync`
Trigger manual playlist synchronization.

**Request Body:**
```json
{
  "playlist_id": "playlist-123"  // Optional: sync specific playlist
}
```

**Response:**
```json
{
  "success": true,
  "playlists_synced": 1,
  "videos_added": 3,
  "videos_updated": 2,
  "videos_removed": 1
}
```

## Backend Integration

### Service Discovery

The app automatically registers with **ppl-meta-discovery** service on startup:

**Registration Payload:**
```json
{
  "service_id": "signage-player-macbook",
  "service_name": "Signage Simple Player",
  "service_type": "signage_player",
  "host": "192.168.1.100",
  "port": 8009,
  "metadata": {
    "platform": "macos",
    "version": "1.0.0",
    "capabilities": ["video_playback", "remote_control", "history_tracking"]
  }
}
```

**Keepalive**: Sends heartbeat every 30 seconds to maintain registration.

### ETL Synchronization

Syncs playlists from **ppl-meta-media** ETL endpoint:

**Endpoint**: `POST /api/v1/signage/etl/sync`

**Request:**
```json
{
  "device_id": "signage-player-macbook",
  "last_sync_version": 5,
  "capabilities": ["video_playback"]
}
```

**Response:**
```json
{
  "playlist": {
    "id": "playlist-123",
    "name": "Store Display",
    "source_list_id": "list-456",
    "sync_version": 6,
    "loop_mode": "continuous",
    "is_active": true,
    "videos": [
      {
        "id": "video-1",
        "video_id": "vid-123",
        "title": "Product Demo",
        "url": "https://cdn.example.com/video1.mp4",
        "sequence_order": 0,
        "duration_ms": 60000
      }
    ]
  }
}
```

**Sync Behavior:**
- **Manual Only**: Sync triggered manually via UI or API (no automatic syncing)
- **Version Tracking**: Compares `sync_version` to detect changes
- **Conflict Resolution**: Automatically handles video additions, removals, and updates
- **Database Persistence**: Saves synced playlists to local SQLite database

### Playback History Reporting

Submits playback history to **ppl-meta-media** in batches:

**Endpoint**: `POST /api/v1/signage/history/batch`

**Request:**
```json
{
  "device_id": "signage-player-macbook",
  "history": [
    {
      "video_id": "video-1",
      "playlist_id": "playlist-123",
      "started_at": "2025-12-02T10:00:00Z",
      "completed_at": "2025-12-02T10:01:00Z",
      "completion_status": "completed",
      "actual_duration_ms": 60000
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "processed": 1
}
```

## Development

### Running Tests

```bash
# Run all tests
flutter test

# Run specific test file
flutter test test/services/player_engine_test.dart

# Run with coverage
flutter test --coverage

# Run integration tests
flutter test test/integration/

# Watch mode for code generation
flutter pub run build_runner watch --delete-conflicting-outputs
```

**Test Coverage:**
- Player Engine: 23/23 tests passing
- Sync Service: 23/23 tests passing  
- History Tracking: 18/18 tests passing
- HTTP Server: 25/25 tests passing
- Discovery Service: 15/15 tests passing
- Database: 20/20 tests passing
- Integration Tests: 6 end-to-end workflow tests

### Code Generation

The project uses code generation for:
- **JSON Serialization**: `json_serializable` for model serialization
- **Mocking**: `mockito` for test mocks

Regenerate when models or mock annotations change:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### Project Guidelines

1. **Service Pattern**: Each major feature is a service in `lib/services/`
2. **State Management**: Uses Provider for reactive state
3. **Database**: SQLite with migrations for schema changes
4. **Testing**: Comprehensive unit tests for all services
5. **Error Handling**: Custom exceptions with user-friendly messages
6. **Logging**: Logger package with configurable levels

## Usage Examples

### Manual Playlist Sync

```dart
// Get sync service from Provider
final syncService = context.read<SyncService>();

// Trigger manual sync
final result = await syncService.syncPlaylists();

if (result.success) {
  print('Synced ${result.playlistsSynced} playlists');
  print('Added ${result.videosAdded} videos');
  print('Updated ${result.videosUpdated} videos');
  print('Removed ${result.videosRemoved} videos');
} else {
  print('Sync failed: ${result.errorMessage}');
}
```

### Load and Play Playlist

```dart
// Get player engine from Provider
final playerEngine = context.read<SignagePlayerEngine>();

// Load playlist by ID
await playerEngine.loadPlaylist('playlist-123');

// Start playback
await playerEngine.play();

// Navigate
playerEngine.playNext();
playerEngine.playPrevious();
playerEngine.skipToVideo(2);
```

### Track Playback History

```dart
// Get history service from Provider
final historyService = context.read<HistoryTrackingService>();

// Track video start
historyService.trackVideoStart(
  playlistId: 'playlist-123',
  videoId: 'video-1',
);

// Track completion
historyService.trackVideoComplete(
  playlistId: 'playlist-123',
  videoId: 'video-1',
  actualDurationMs: 60000,
);

// Submit batch to backend
await historyService.submitPendingHistory();
```

### Query Local Database

```dart
// Get database from Provider
final database = context.read<PlaylistDatabase>();

// Get all playlists
final playlists = await database.getAllPlaylists();

// Get specific playlist
final playlist = await database.getPlaylist('playlist-123');

// Search playlists
final results = await database.searchPlaylists('product');
```

## Troubleshooting

### Common Issues

**Issue**: App fails to register with discovery service  
**Solution**: Ensure ppl-meta-discovery is running on port 8006 and accessible

**Issue**: Playlist sync returns no data  
**Solution**: Check that a playlist is assigned to this device in the backend

**Issue**: Videos fail to play  
**Solution**: Verify video URLs are accessible and in supported format (MP4, MOV)

**Issue**: History not submitting  
**Solution**: Check ppl-meta-media API is accessible and authentication is valid

### Debug Mode

Enable verbose logging in `main.dart`:
```dart
final logger = Logger(
  level: Level.debug, // Change to Level.debug
  printer: PrettyPrinter(),
);
```

### Database Inspection

Access SQLite database for debugging:
```bash
# macOS
sqlite3 ~/Library/Application\ Support/signage-simple-player/database.db

# Android
adb shell
run-as com.pplmeta.signage_simple_player
cd databases/
```

## Deployment

### Android Release Build

```bash
# Build release APK
flutter build apk --release

# Build app bundle for Play Store
flutter build appbundle --release

# Install on device
flutter install --release
```

### Configuration for Production

1. Update `lib/config/app_config.dart` with production URLs
2. Configure signing in `android/app/build.gradle`
3. Set appropriate permissions in `android/app/src/main/AndroidManifest.xml`
4. Test on target hardware before deployment

## Architecture Decisions

### Why Manual Sync Only?

- **Control**: Operators explicitly trigger updates
- **Bandwidth**: Reduces unnecessary network usage
- **Testing**: Easier to test and debug sync behavior
- **Reliability**: No background task failures

### Why Embedded HTTP Server?

- **Zero Dependencies**: No external web server required
- **Remote Control**: Enables API-based control from backend
- **Monitoring**: Provides real-time status for dashboards
- **Simplicity**: Single application handles everything

### Why SQLite Database?

- **Offline Support**: Works without network connectivity
- **Performance**: Fast local queries for playlists
- **Reliability**: ACID transactions for data integrity
- **Cross-Platform**: Works on macOS, Android, iOS

## Contributing

This is an internal PPL Meta Platform project. For questions or issues, contact the development team.

## License

Copyright © 2025 PPL Meta Platform. All rights reserved.
