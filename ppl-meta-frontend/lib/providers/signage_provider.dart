/// State management provider for Signage Simple Player management
/// Handles video lists, devices, sync operations, and playback control state

import 'package:flutter/foundation.dart';
import '../models/signage_models.dart';
import '../services/signage_api_client.dart';

class SignageProvider with ChangeNotifier {
  final SignageApiClient _apiClient;

  // Video Lists State
  List<VideoList> _videoLists = [];
  VideoList? _selectedVideoList;
  bool _isLoadingLists = false;
  String? _listsError;
  int _totalListsCount = 0;
  int _currentPage = 1;

  // Devices State
  List<SignageDevice> _devices = [];
  SignageDevice? _selectedDevice;
  bool _isLoadingDevices = false;
  String? _devicesError;
  Map<String, PlaybackStatus> _deviceStatuses = {};

  // Sync State
  Map<String, SyncResult> _syncResults = {};
  bool _isSyncing = false;
  String? _syncError;

  // Playback Control State
  bool _isControllingPlayback = false;
  String? _playbackError;

  SignageProvider(this._apiClient);

  // ==================== Getters ====================

  List<VideoList> get videoLists => _videoLists;
  VideoList? get selectedVideoList => _selectedVideoList;
  bool get isLoadingLists => _isLoadingLists;
  String? get listsError => _listsError;
  int get totalListsCount => _totalListsCount;
  int get currentPage => _currentPage;

  List<SignageDevice> get devices => _devices;
  List<SignageDevice> get onlineDevices => 
      _devices.where((d) => d.isOnline).toList();
  SignageDevice? get selectedDevice => _selectedDevice;
  bool get isLoadingDevices => _isLoadingDevices;
  String? get devicesError => _devicesError;
  Map<String, PlaybackStatus> get deviceStatuses => _deviceStatuses;

  Map<String, SyncResult> get syncResults => _syncResults;
  bool get isSyncing => _isSyncing;
  String? get syncError => _syncError;

  bool get isControllingPlayback => _isControllingPlayback;
  String? get playbackError => _playbackError;

  // ==================== Video List Operations ====================

  /// Load video lists with pagination
  Future<void> loadVideoLists({
    int page = 1,
    int limit = 20,
    String? search,
    bool? isActive,
  }) async {
    _isLoadingLists = true;
    _listsError = null;
    notifyListeners();

    try {
      final response = await _apiClient.getVideoLists(
        page: page,
        limit: limit,
        search: search,
        isActive: isActive,
      );

      _videoLists = response.results;
      _totalListsCount = response.totalCount;
      _currentPage = page;
      _listsError = null;
    } catch (e) {
      // Handle 404 as empty list (no video lists created yet) - completely silent
      if (e.toString().contains('404') || e.toString().contains('Not Found')) {
        _videoLists = [];
        _totalListsCount = 0;
        _currentPage = 1;
        _listsError = null;
        // Intentionally silent - 404 is expected when no playlists exist
      } else {
        _listsError = 'Failed to load video lists: $e';
        debugPrint('SignageProvider: $_listsError');
      }
    } finally {
      _isLoadingLists = false;
      notifyListeners();
    }
  }

  /// Load a single video list by ID
  Future<void> loadVideoList(String listId) async {
    try {
      final videoList = await _apiClient.getVideoList(listId);
      _selectedVideoList = videoList;
      
      // Update in the list if it exists
      final index = _videoLists.indexWhere((l) => l.id == listId);
      if (index != -1) {
        _videoLists[index] = videoList;
      }
      
      notifyListeners();
    } catch (e) {
      _listsError = 'Failed to load video list: $e';
      print(_listsError);
      notifyListeners();
    }
  }

  /// Create a new video list
  Future<VideoList?> createVideoList(CreateVideoListRequest request) async {
    _isLoadingLists = true;
    _listsError = null;
    notifyListeners();

    try {
      final newList = await _apiClient.createVideoList(request);
      _videoLists.insert(0, newList);
      _selectedVideoList = newList;
      _totalListsCount++;
      _listsError = null;
      notifyListeners();
      return newList;
    } catch (e) {
      _listsError = 'Failed to create video list: $e';
      print(_listsError);
      notifyListeners();
      return null;
    } finally {
      _isLoadingLists = false;
      notifyListeners();
    }
  }

  /// Update an existing video list
  Future<bool> updateVideoList(
    String listId,
    CreateVideoListRequest request,
  ) async {
    _isLoadingLists = true;
    _listsError = null;
    notifyListeners();

    try {
      final updatedList = await _apiClient.updateVideoList(listId, request);
      
      final index = _videoLists.indexWhere((l) => l.id == listId);
      if (index != -1) {
        _videoLists[index] = updatedList;
      }
      
      if (_selectedVideoList?.id == listId) {
        _selectedVideoList = updatedList;
      }
      
      notifyListeners();
      return true;
    } catch (e) {
      _listsError = 'Failed to update video list: $e';
      print(_listsError);
      notifyListeners();
      return false;
    } finally {
      _isLoadingLists = false;
      notifyListeners();
    }
  }

  /// Delete a video list
  Future<bool> deleteVideoList(String listId) async {
    try {
      await _apiClient.deleteVideoList(listId);
      
      _videoLists.removeWhere((l) => l.id == listId);
      if (_selectedVideoList?.id == listId) {
        _selectedVideoList = null;
      }
      _totalListsCount--;
      
      notifyListeners();
      return true;
    } catch (e) {
      _listsError = 'Failed to delete video list: $e';
      print(_listsError);
      notifyListeners();
      return false;
    }
  }

  /// Select a video list
  void selectVideoList(VideoList? videoList) {
    _selectedVideoList = videoList;
    notifyListeners();
  }

  /// Load all playlists that have been synced to a device, newest first
  Future<List<VideoList>> loadSyncedVideoListsForDevice(String deviceId) async {
    try {
      if (_videoLists.isEmpty) {
        await loadVideoLists(limit: 100);
      } else if (_totalListsCount > _videoLists.length) {
        await loadVideoLists(limit: _totalListsCount);
      }

      if (_videoLists.isEmpty) {
        return [];
      }

      final syncHistory = await _apiClient.getDeviceSyncHistory(
        deviceId: deviceId,
        pageSize: 100,
      );

      final orderedPlaylistDbIds = <int>[];
      final seen = <int>{};

      for (final entry in syncHistory) {
        final status = entry['sync_status']?.toString();
        if (status == 'failed') {
          continue;
        }

        final rawId = entry['video_list_id'];
        final playlistDbId = rawId is num ? rawId.toInt() : int.tryParse('$rawId');
        if (playlistDbId == null || seen.contains(playlistDbId)) {
          continue;
        }

        seen.add(playlistDbId);
        orderedPlaylistDbIds.add(playlistDbId);
      }

      if (orderedPlaylistDbIds.isEmpty) {
        return [];
      }

      final byDatabaseId = <int, VideoList>{
        for (final list in _videoLists)
          if (list.databaseId != null) list.databaseId!: list,
      };

      return orderedPlaylistDbIds
          .map((dbId) => byDatabaseId[dbId])
          .whereType<VideoList>()
          .toList();
    } catch (e) {
      debugPrint('Failed to load synced playlists for device $deviceId: $e');
      return [];
    }
  }

  // ==================== Device Operations ====================

  /// Load all signage devices from discovery service
  Future<void> loadDevices() async {
    _isLoadingDevices = true;
    _devicesError = null;
    notifyListeners();

    try {
      _devices = await _apiClient.getSignageDevices();
      print('📱 Loaded ${_devices.length} signage devices');
      for (var device in _devices) {
        print('  Device: ${device.name} - Status: ${device.status} - IsOnline: ${device.isOnline}');
        if (device.lastHeartbeat != null) {
          final age = DateTime.now().toUtc().difference(device.lastHeartbeat!);
          print('    Last heartbeat: ${age.inSeconds}s ago');
        } else {
          print('    Last heartbeat: null');
        }
      }
      print('📱 Online devices: ${onlineDevices.length}');
      _devicesError = null;
    } catch (e) {
      _devicesError = 'Failed to load devices: $e';
      print(_devicesError);
    } finally {
      _isLoadingDevices = false;
      notifyListeners();
    }
  }

  /// Select a device
  void selectDevice(SignageDevice? device) {
    _selectedDevice = device;
    notifyListeners();
  }

  /// Get device status
  Future<void> loadDeviceStatus(String deviceId) async {
    try {
      final status = await _apiClient.getDeviceStatus(deviceId);
      _deviceStatuses[deviceId] = status;
      notifyListeners();
    } catch (e) {
      print('Failed to load device status for $deviceId: $e');
    }
  }

  /// Load status for all devices
  Future<void> loadAllDeviceStatuses() async {
    final deviceIds = _devices.map((d) => d.id).toList(); // Use UUID (id), not device name (deviceId)
    
    for (final deviceId in deviceIds) {
      await loadDeviceStatus(deviceId);
    }
  }

  /// Refresh devices (reload from discovery service)
  Future<void> refreshDevices() async {
    await loadDevices();
    if (_devices.isNotEmpty) {
      await loadAllDeviceStatuses();
    }
  }

  // ==================== Sync Operations ====================

  /// Sync a video list to one or more devices
  Future<bool> syncVideoListToDevices({
    required String videoListId,
    required List<String> deviceIds,
    SyncMode syncMode = SyncMode.incremental,
    bool forceUpdate = false,
  }) async {
    _isSyncing = true;
    _syncError = null;
    notifyListeners();

    try {
      print('🔧 Provider syncVideoListToDevices called with:');
      print('  videoListId: $videoListId');
      print('  deviceIds: $deviceIds');
      
      final result = await _apiClient.syncVideoListToDevices(
        SyncRequest(
          videoListId: videoListId,
          targetDevices: deviceIds,
          syncMode: syncMode,
          forceUpdate: forceUpdate,
        ),
      );

      _syncResults[result.syncJobId] = result;
      _syncError = null;
      notifyListeners();
      return true;
    } catch (e) {
      _syncError = 'Failed to sync video list: $e';
      print(_syncError);
      notifyListeners();
      return false;
    } finally {
      _isSyncing = false;
      notifyListeners();
    }
  }

  /// Sync to all online devices
  Future<bool> syncToAllDevices(String videoListId) async {
    final onlineDeviceIds = onlineDevices.map((d) => d.id).toList();  // Use UUID, not deviceId
    
    if (onlineDeviceIds.isEmpty) {
      _syncError = 'No online devices available';
      notifyListeners();
      return false;
    }

    return await syncVideoListToDevices(
      videoListId: videoListId,
      deviceIds: onlineDeviceIds,
    );
  }

  // ==================== Playback Control ====================

  /// Start playback on a device
  Future<bool> startPlayback({
    required String deviceId,
    required String videoListId,
    int startIndex = 0,
    int volume = 80,
  }) async {
    _isControllingPlayback = true;
    _playbackError = null;
    notifyListeners();

    try {
      await _apiClient.startPlayback(
        deviceId: deviceId,
        videoListId: videoListId,
        startIndex: startIndex,
        volume: volume,
      );

      // DO NOT refresh device status after starting playback
      // Device will update status via heartbeat. Unnecessary status checks
      // can cause connection issues.
      
      _playbackError = null;
      return true;
    } catch (e) {
      _playbackError = 'Failed to start playback: $e';
      print(_playbackError);
      return false;
    } finally {
      _isControllingPlayback = false;
      notifyListeners();
    }
  }

  /// Pause playback on a device
  Future<bool> pausePlayback(String deviceId) async {
    return await _controlPlayback(
      deviceId,
      () => _apiClient.pausePlayback(deviceId),
      'pause',
    );
  }

  /// Resume playback on a device
  Future<bool> resumePlayback(String deviceId) async {
    return await _controlPlayback(
      deviceId,
      () => _apiClient.resumePlayback(deviceId),
      'resume',
    );
  }

  /// Stop playback on a device
  Future<bool> stopPlayback(String deviceId) async {
    return await _controlPlayback(
      deviceId,
      () => _apiClient.stopPlayback(deviceId),
      'stop',
    );
  }

  /// Skip to next video on a device
  Future<bool> nextVideo(String deviceId) async {
    return await _controlPlayback(
      deviceId,
      () => _apiClient.nextVideo(deviceId),
      'next',
    );
  }

  /// Go to previous video on a device
  Future<bool> previousVideo(String deviceId) async {
    return await _controlPlayback(
      deviceId,
      () => _apiClient.previousVideo(deviceId),
      'previous',
    );
  }

  /// Helper method for playback control operations
  Future<bool> _controlPlayback(
    String deviceId,
    Future<void> Function() controlFunction,
    String action,
  ) async {
    _isControllingPlayback = true;
    _playbackError = null;
    notifyListeners();

    try {
      await controlFunction();
      
      // DO NOT refresh device status after control action
      // The control command was sent successfully, and device will update its status
      // via heartbeat. Refreshing here causes unnecessary network calls and can
      // disconnect the device if the endpoint lookup fails.
      // Status will be updated naturally when device sends next heartbeat or
      // when user manually refreshes.
      
      _playbackError = null;
      return true;
    } catch (e) {
      _playbackError = 'Failed to $action playback: $e';
      print(_playbackError);
      return false;
    } finally {
      _isControllingPlayback = false;
      notifyListeners();
    }
  }

  // ==================== Utility Methods ====================

  /// Clear errors
  void clearErrors() {
    _listsError = null;
    _devicesError = null;
    _syncError = null;
    _playbackError = null;
    notifyListeners();
  }

  /// Reset state
  void reset() {
    _videoLists = [];
    _selectedVideoList = null;
    _devices = [];
    _selectedDevice = null;
    _deviceStatuses = {};
    _syncResults = {};
    clearErrors();
  }
}
