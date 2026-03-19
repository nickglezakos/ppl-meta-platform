/// PPL Meta Signage Simple Player Configuration
class AppConfig {
  // Service Information
  static const String serviceName = 'signage-simple';
  static const String serviceType = 'edge';
  static const String version = '1.0.0';
  
  // Network Configuration
  static const int httpServerPort = 8009;
  static const Duration heartbeatInterval = Duration(seconds: 30);
  static const Duration registrationRetryDelay = Duration(seconds: 10);
  static const Duration syncTimeout = Duration(minutes: 5);
  
  // Backend Service URLs (default for local development)
  static const String mediaServiceUrl = 'http://localhost:8000';
  static const String discoveryServiceUrl = 'http://localhost:8006';
  static const String gatewayUrl = 'http://localhost:8080';
  
  // Database Configuration
  static const String databaseName = 'signage_playlists.db';
  static const int databaseVersion = 1;
  
  // Playback Configuration
  static const int maxCachedVideos = 10;
  static const int maxCacheSizeMB = 10240; // 10GB
  static const int preloadCount = 2;
  static const Duration transitionDuration = Duration(milliseconds: 500);
  
  // History Configuration
  static const int historyRetentionDays = 90;
  static const int historyPageSize = 50;
  static const int recentlyPlayedLimit = 5;
  static const int upcomingVideosLimit = 10;
  
  // Device Capabilities
  static const List<String> capabilities = [
    'video_playback',
    'remote_control',
    'playlist_sync',
    'history_tracking',
  ];
  
  static const String maxVideoResolution = '1920x1080';
  static const List<String> supportedCodecs = ['h264', 'vp9'];
  
  // API Endpoints
  static String get videoListsEndpoint => '$mediaServiceUrl/api/v1/signage/video-lists';
  static String get etlSyncEndpoint => '$mediaServiceUrl/api/v1/signage/etl/sync';
  static String get playbackControlEndpoint => '$mediaServiceUrl/api/v1/signage/playback/control';
  static String get discoveryRegisterEndpoint => '$discoveryServiceUrl/api/v1/services';
  static String get discoveryHeartbeatEndpoint => '$discoveryServiceUrl/api/v1/services/heartbeat';
}
