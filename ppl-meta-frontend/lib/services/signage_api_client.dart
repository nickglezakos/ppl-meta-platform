/// API client for Signage Simple Player management operations
/// Handles video lists, device management, sync operations, and playback control

import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../core/config/app_config.dart';
import '../models/signage_models.dart';
import 'discovery_service_client.dart';

class SignageApiClient {
  late final ApiClient _apiClient;
  final DiscoveryServiceClient? _discoveryClient;
  
  /// Cache device endpoints to avoid repeated discovery lookups
  /// Key: device ID (UUID), Value: endpoint URL (http://host:port)
  final Map<String, String> _deviceEndpointCache = {};

  SignageApiClient([ApiClient? apiClient, this._discoveryClient]) {
    _apiClient = apiClient ?? ApiClient(AppConfig.instance);
  }

  // ==================== Video List Management ====================

  /// Get all video lists with pagination
  Future<VideoListsResponse> getVideoLists({
    int page = 1,
    int limit = 20,
    String? search,
    bool? isActive,
  }) async {
    final effectiveLimit = limit.clamp(1, 100);

    final queryParams = {
      'page': page,
      'page_size': effectiveLimit,
      'limit': effectiveLimit,
      if (search != null) 'search': search,
      if (isActive != null) 'is_active': isActive,
    };

    final response = await _apiClient.get(
      '/api/v1/signage/video-lists',
      queryParameters: queryParams,
    );

    return VideoListsResponse.fromJson(response.data);
  }

  /// Get a single video list by ID
  Future<VideoList> getVideoList(String listId) async {
    final response = await _apiClient.get(
      '/api/v1/signage/video-lists/$listId',
    );

    return VideoList.fromJson(response.data);
  }

  /// Create a new video list
  Future<VideoList> createVideoList(CreateVideoListRequest request) async {
    final response = await _apiClient.post(
      '/api/v1/signage/video-lists',
      data: request.toJson(),
    );

    return VideoList.fromJson(response.data);
  }

  /// Update an existing video list
  Future<VideoList> updateVideoList(
    String listId,
    CreateVideoListRequest request,
  ) async {
    final response = await _apiClient.put(
      '/api/v1/signage/video-lists/$listId',
      data: request.toJson(),
    );

    return VideoList.fromJson(response.data);
  }

  /// Delete a video list
  Future<void> deleteVideoList(String listId) async {
    await _apiClient.delete('/api/v1/signage/video-lists/$listId');
  }

  // ==================== ETL Sync Operations ====================

  /// Sync a video list to one or more devices
  Future<SyncResult> syncVideoListToDevices(SyncRequest request) async {
    try {
      final url = '/api/v1/signage/etl/sync';
      print('🔄 Syncing video list to devices:');
      print('  URL: $url');
      print('  Video List ID: ${request.videoListId}');
      print('  Target Devices: ${request.targetDevices}');
      print('  Sync Mode: ${request.syncMode}');
      print('  Payload: ${request.toJson()}');
      
      final response = await _apiClient.post(
        url,
        data: request.toJson(),
      );

      print('✅ Sync request successful');
      return SyncResult.fromJson(response.data);
    } catch (e, stackTrace) {
      print('❌ Sync request failed:');
      print('  Error: $e');
      if (e is DioException && e.response != null) {
        print('  Response status: ${e.response?.statusCode}');
        print('  Response data: ${e.response?.data}');
      }
      rethrow;
    }
  }

  /// Get sync history for a video list
  Future<List<Map<String, dynamic>>> getSyncHistory(String listId) async {
    final response = await _apiClient.get(
      '/api/v1/signage/etl/sync-history/$listId',
    );

    return List<Map<String, dynamic>>.from(response.data['history'] ?? []);
  }

  /// Get sync history for a specific device
  Future<List<Map<String, dynamic>>> getDeviceSyncHistory({
    required String deviceId,
    int page = 1,
    int pageSize = 100,
  }) async {
    final effectivePageSize = pageSize.clamp(1, 100);

    final response = await _apiClient.get(
      '/api/v1/signage/etl/sync-history',
      queryParameters: {
        'device_id': deviceId,
        'page': page,
        'page_size': effectivePageSize,
      },
    );

    return List<Map<String, dynamic>>.from(response.data['results'] ?? []);
  }

  // ==================== Playback Control ====================

  /// Send playback control command to device(s)
  Future<Map<String, dynamic>> controlPlayback(
    PlaybackControlRequest request,
  ) async {
    final response = await _apiClient.post(
      '/api/v1/signage/playback/control',
      data: request.toJson(),
    );

    return response.data;
  }

  /// Start playback on a device
  Future<void> startPlayback({
    required String deviceId,
    required String videoListId,
    int startIndex = 0,
    int volume = 80,
  }) async {
    await controlPlayback(
      PlaybackControlRequest(
        deviceIds: [deviceId],
        command: PlaybackCommand.start,
        videoListId: videoListId,
        parameters: PlaybackParameters(
          startIndex: startIndex,
          volume: volume,
        ),
      ),
    );
  }

  /// Pause playback on a device
  /// deviceId should be the UUID (device.id), not the device name (device.deviceId)
  Future<void> pausePlayback(String deviceId) async {
    await controlPlayback(
      PlaybackControlRequest(
        deviceIds: [deviceId],
        command: PlaybackCommand.pause,
      ),
    );
  }

  /// Resume playback on a device
  /// deviceId should be the UUID (device.id), not the device name (device.deviceId)
  Future<void> resumePlayback(String deviceId) async {
    await controlPlayback(
      PlaybackControlRequest(
        deviceIds: [deviceId],
        command: PlaybackCommand.resume,
      ),
    );
  }

  /// Stop playback on a device
  /// deviceId should be the UUID (device.id), not the device name (device.deviceId)
  Future<void> stopPlayback(String deviceId) async {
    await controlPlayback(
      PlaybackControlRequest(
        deviceIds: [deviceId],
        command: PlaybackCommand.stop,
      ),
    );
  }

  /// Skip to next video on a device
  /// deviceId should be the UUID (device.id), not the device name (device.deviceId)
  Future<void> nextVideo(String deviceId) async {
    await controlPlayback(
      PlaybackControlRequest(
        deviceIds: [deviceId],
        command: PlaybackCommand.next,
      ),
    );
  }

  /// Go to previous video on a device
  /// deviceId should be the UUID (device.id), not the device name (device.deviceId)
  Future<void> previousVideo(String deviceId) async {
    await controlPlayback(
      PlaybackControlRequest(
        deviceIds: [deviceId],
        command: PlaybackCommand.previous,
      ),
    );
  }

  // ==================== Device Management ====================

  /// Get all signage devices from discovery service
  Future<List<SignageDevice>> getSignageDevices() async {
    if (_discoveryClient == null) {
      throw Exception('Discovery client not available');
    }

    try {
      final response = await _discoveryClient!.discoverServices(
        serviceType: 'edge', // Signage devices register as 'edge' type
      );
      final services = response.services;

      // Filter for signage devices
      final signageServices = services.where((s) => s.name.startsWith('signage-simple-')).toList();
      print('🔍 Found ${signageServices.length} signage services from discovery');
      
      for (var s in signageServices) {
        print('  Service: ${s.name}');
        print('    serviceId: ${s.serviceId}');
        print('    status: ${s.status}');
        print('    lastSeen: ${s.lastSeen}');
        print('    registeredAt: ${s.registeredAt}');
      }
      
      return signageServices.map((s) {
            final deviceId = s.metadata['device_id'] ?? s.name.replaceFirst('signage-simple-', '');
            
            // Backend sends UTC timestamps without 'Z' suffix, so Dart parses them as local time
            // We need to treat them as UTC by creating new DateTime objects in UTC
            DateTime? parseAsUtc(DateTime? dt) {
              if (dt == null) return null;
              return DateTime.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.millisecond, dt.microsecond);
            }
            
            final lastHeartbeat = parseAsUtc(s.lastSeen);
            final registeredAt = parseAsUtc(s.registeredAt);
            
            print('  Mapping device: ${s.name}');
            print('    lastSeen raw: ${s.lastSeen}');
            print('    lastHeartbeat (UTC corrected): $lastHeartbeat');
            if (lastHeartbeat != null) {
              final now = DateTime.now().toUtc();
              final age = now.difference(lastHeartbeat);
              print('    Current UTC: $now');
              print('    Age: ${age.inSeconds}s');
            }
            
            final device = SignageDevice(
              id: s.serviceId,
              name: s.name,
              deviceId: deviceId,
              serviceType: s.serviceType,
              host: s.host,
              port: s.port,
              status: s.status,
              metadata: s.metadata,
              lastHeartbeat: lastHeartbeat,
              registeredAt: registeredAt,
            );
            
            // Cache device endpoint to avoid repeated discovery lookups. Prefer
            // the device's dynamic mesh (Tailscale VPN) IP when advertised — the
            // LAN host is often unreachable from the platform for NAT'd/offsite
            // devices. The mesh IP is refreshed on the player's heartbeat; host
            // stays the stale LAN address.

            final meshIpTrou = (s.metadata['tailscale_ip'] as String?);
            final reachableHost = (meshIpTrou != null && meshIpTrou!.trim().isNotEmpty)
                ? meshIpTrou!
                : s.host;
            final endpoint = 'http://$reachableHost:${s.port}';
            _deviceEndpointCache[device.id] = endpoint;
            print('  Cached endpoint for ${device.id}: $endpoint');
            
            return device;
          })
          .toList();
    } catch (e) {
      print('Error fetching signage devices: $e');
      return [];
    }
  }

  /// Get device status
  /// Note: Device host and port should already be cached from discovery service discovery
  Future<PlaybackStatus> getDeviceStatus(String deviceId) async {
    // Get device endpoint from discovery service with fallback caching
    final deviceEndpoint = await _getDeviceEndpoint(deviceId);
    
    final response = await _apiClient.get(
      '$deviceEndpoint/api/v1/status',
    );

    return PlaybackStatus.fromJson(response.data);
  }

  /// Get device health
  Future<Map<String, dynamic>> getDeviceHealth(String deviceId) async {
    final deviceEndpoint = await _getDeviceEndpoint(deviceId);
    
    final response = await _apiClient.get(
      '$deviceEndpoint/health',
    );

    return response.data;
  }

  /// Get device playback history
  Future<Map<String, dynamic>> getDeviceHistory({
    required String deviceId,
    DateTime? startDate,
    DateTime? endDate,
    String? videoId,
    String? playlistId,
    int page = 1,
    int limit = 50,
    String sort = 'desc',
  }) async {
    final deviceEndpoint = await _getDeviceEndpoint(deviceId);
    
    final queryParams = {
      if (startDate != null) 'start_date': startDate.toIso8601String(),
      if (endDate != null) 'end_date': endDate.toIso8601String(),
      if (videoId != null) 'video_id': videoId,
      if (playlistId != null) 'playlist_id': playlistId,
      'page': page,
      'limit': limit,
      'sort': sort,
    };

    final response = await _apiClient.get(
      '$deviceEndpoint/api/v1/history',
      queryParameters: queryParams,
    );

    return response.data;
  }

  // ==================== Helper Methods ====================

  /// Get device endpoint URL from discovery service or construct from device info
  Future<String> _getDeviceEndpoint(String deviceId) async {
    // First check if endpoint is cached
    if (_deviceEndpointCache.containsKey(deviceId)) {
      print('✅ Using cached endpoint for $deviceId: ${_deviceEndpointCache[deviceId]}');
      return _deviceEndpointCache[deviceId]!;
    }
    
    // Fall back to discovery service lookup
    if (_discoveryClient != null) {
      try {
        final response = await _discoveryClient!.discoverServices(
          serviceType: 'edge',
        );
        final services = response.services;
        
        // First try to match by serviceId (UUID format)
        final device = services.cast<dynamic>().firstWhere(
          (s) => s.serviceId == deviceId,
          orElse: () {
            // If not found by serviceId, try by device name or metadata
            return services.firstWhere(
              (s) => s.name == 'signage-simple-$deviceId' ||
                     s.metadata?['device_id'] == deviceId,
              orElse: () => throw Exception('Device not found: $deviceId'),
            );
          },
        );

        // Prefer the device's dynamic mesh (Tailscale VPN) IP when advertised — the
        // LAN host is often unreachable from the platform for NAT'd/offsite devices.
        // The mesh IP is fresh (refreshed each player heartbeat); host is the stale
        // LAN address.

        final meshIpTrou2 = (device.metadata?['tailscale_ip'] as String?);
        final reachableHost = (meshIpTrou2 != null && meshIpTrou2!.trim().isNotEmpty)
            ? meshIpTrou2!
            : device.host;
        final endpoint = 'http://$reachableHost:${device.port}';
        _deviceEndpointCache[deviceId] = endpoint;
        print('✅ Discovered and cached endpoint for $deviceId: $endpoint');
        return endpoint;
      } catch (e) {
        throw Exception('Failed to get device endpoint: $e');
      }
    }
    
    throw Exception('Discovery client not available');
  }

  /// Batch sync multiple playlists to multiple devices
  Future<List<SyncResult>> batchSync({
    required List<String> videoListIds,
    required List<String> deviceIds,
    SyncMode syncMode = SyncMode.incremental,
  }) async {
    final results = <SyncResult>[];
    
    for (final listId in videoListIds) {
      try {
        final result = await syncVideoListToDevices(
          SyncRequest(
            videoListId: listId,
            targetDevices: deviceIds,
            syncMode: syncMode,
          ),
        );
        results.add(result);
      } catch (e) {
        print('Batch sync error for list $listId: $e');
        // Continue with other lists even if one fails
      }
    }
    
    return results;
  }

  /// Get aggregated status for multiple devices
  Future<Map<String, PlaybackStatus>> getMultipleDeviceStatus(
    List<String> deviceIds,
  ) async {
    final statusMap = <String, PlaybackStatus>{};
    
    await Future.wait(
      deviceIds.map((deviceId) async {
        try {
          final status = await getDeviceStatus(deviceId);
          statusMap[deviceId] = status;
        } catch (e) {
          print('Error getting status for device $deviceId: $e');
        }
      }),
    );
    
    return statusMap;
  }
}
