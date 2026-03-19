import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/api/signage_api_client.dart';
import 'package:signage_simple_player/api/api_exceptions.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/models/video_list.dart';

/// Sync status for tracking synchronization state
enum SyncStatus {
  idle,
  syncing,
  success,
  error,
}

/// Result of a sync operation
class SyncResult {
  final bool success;
  final String? errorMessage;
  final int playlistsSynced;
  final int videosAdded;
  final int videosUpdated;
  final int videosRemoved;
  final DateTime timestamp;

  SyncResult({
    required this.success,
    this.errorMessage,
    this.playlistsSynced = 0,
    this.videosAdded = 0,
    this.videosUpdated = 0,
    this.videosRemoved = 0,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  @override
  String toString() {
    if (!success) {
      return 'Sync failed: $errorMessage';
    }
    return 'Synced $playlistsSynced playlists: '
        '+$videosAdded videos, ~$videosUpdated updated, -$videosRemoved removed';
  }
}

/// Playlist synchronization service
/// 
/// Features:
/// - Manual sync trigger (no automatic/periodic syncing)
/// - Downloads playlists from backend via API client
/// - Saves to local SQLite database
/// - Version tracking and conflict resolution
/// - Detailed sync statistics and status reporting
/// - Error handling with informative messages
class SyncService extends ChangeNotifier {
  final SignageApiClient _apiClient;
  final PlaylistDatabase _database;
  final Logger _logger;

  SyncStatus _status = SyncStatus.idle;
  SyncResult? _lastResult;
  DateTime? _lastSyncTime;
  bool _isSyncing = false;

  SyncService({
    required SignageApiClient apiClient,
    required PlaylistDatabase database,
    required Logger logger,
  })  : _apiClient = apiClient,
        _database = database,
        _logger = logger;

  // Getters
  SyncStatus get status => _status;
  SyncResult? get lastResult => _lastResult;
  DateTime? get lastSyncTime => _lastSyncTime;
  bool get isSyncing => _isSyncing;
  bool get canSync => !_isSyncing;

  /// Manually trigger playlist synchronization
  /// 
  /// Downloads all active playlists from backend and updates local database.
  /// Returns SyncResult with detailed statistics.
  Future<SyncResult> syncPlaylists() async {
    if (_isSyncing) {
      _logger.w('Sync already in progress, skipping request');
      return SyncResult(
        success: false,
        errorMessage: 'Sync already in progress',
      );
    }

    _isSyncing = true;
    _status = SyncStatus.syncing;
    notifyListeners();

    try {
      _logger.i('Starting manual playlist sync');

      // Fetch playlist from backend (API returns single playlist or null)
      final playlist = await _apiClient.syncPlaylist();
      
      if (playlist == null) {
        _logger.i('No playlist received from backend (device may not be assigned)');
        final result = SyncResult(
          success: true,
          playlistsSynced: 0,
        );
        
        _completeSync(SyncStatus.success, result);
        return result;
      }

      _logger.d('Received playlist from backend: ${playlist.name} (${playlist.videos.length} videos)');

      // Track statistics
      int playlistsSynced = 0;
      int videosAdded = 0;
      int videosUpdated = 0;
      int videosRemoved = 0;

      // Get existing playlist from database
      final existingPlaylist = await _database.getPlaylist(playlist.id);

      if (existingPlaylist == null) {
        // New playlist - insert
        _logger.d('Inserting new playlist: ${playlist.name} (${playlist.id})');
        await _database.upsertPlaylist(playlist);
        playlistsSynced = 1;
        videosAdded = playlist.videos.length;
      } else {
        // Existing playlist - check for updates
        final updateNeeded = _shouldUpdatePlaylist(existingPlaylist, playlist);
        
        if (updateNeeded) {
          _logger.d('Updating playlist: ${playlist.name} (${playlist.id})');
          
          // Calculate video changes
          final oldVideoIds = existingPlaylist.videos.map((v) => v.id).toSet();
          final newVideoIds = playlist.videos.map((v) => v.id).toSet();
          
          final added = newVideoIds.difference(oldVideoIds).length;
          final removed = oldVideoIds.difference(newVideoIds).length;
          final updated = newVideoIds.intersection(oldVideoIds).length;
          
          videosAdded = added;
          videosRemoved = removed;
          videosUpdated = updated;
          
          // Update in database
          await _database.upsertPlaylist(playlist);
          playlistsSynced = 1;
        } else {
          _logger.d('Playlist unchanged: ${playlist.name} (${playlist.id})');
        }
      }

      // Create success result
      final result = SyncResult(
        success: true,
        playlistsSynced: playlistsSynced,
        videosAdded: videosAdded,
        videosUpdated: videosUpdated,
        videosRemoved: videosRemoved,
      );

      _logger.i('Sync completed successfully: $result');
      _completeSync(SyncStatus.success, result);
      return result;

    } catch (e, stackTrace) {
      _logger.e('Playlist sync failed', error: e, stackTrace: stackTrace);
      
      final result = SyncResult(
        success: false,
        errorMessage: _getErrorMessage(e),
      );
      
      _completeSync(SyncStatus.error, result);
      return result;
    }
  }

  /// Sync a specific playlist by ID
  /// 
  /// Useful for targeted updates without syncing all playlists.
  Future<SyncResult> syncPlaylistById(String playlistId) async {
    if (_isSyncing) {
      _logger.w('Sync already in progress, skipping request');
      return SyncResult(
        success: false,
        errorMessage: 'Sync already in progress',
      );
    }

    _isSyncing = true;
    _status = SyncStatus.syncing;
    notifyListeners();

    try {
      _logger.i('Starting sync for playlist: $playlistId');

      // Fetch the assigned playlist from backend
      final playlist = await _apiClient.syncPlaylist();

      if (playlist == null) {
        final result = SyncResult(
          success: false,
          errorMessage: 'No playlist assigned to this device',
        );
        _completeSync(SyncStatus.error, result);
        return result;
      }

      // Check if it matches the requested ID
      if (playlist.id != playlistId) {
        final result = SyncResult(
          success: false,
          errorMessage: 'Requested playlist $playlistId not assigned to this device (assigned: ${playlist.id})',
        );
        _completeSync(SyncStatus.error, result);
        return result;
      }

      // Get existing playlist
      final existingPlaylist = await _database.getPlaylist(playlist.id);

      int videosAdded = 0;
      int videosUpdated = 0;
      int videosRemoved = 0;

      if (existingPlaylist == null) {
        // New playlist
        await _database.upsertPlaylist(playlist);
        videosAdded = playlist.videos.length;
      } else {
        // Calculate video changes
        final oldVideoIds = existingPlaylist.videos.map((v) => v.id).toSet();
        final newVideoIds = playlist.videos.map((v) => v.id).toSet();
        
        videosAdded = newVideoIds.difference(oldVideoIds).length;
        videosRemoved = oldVideoIds.difference(newVideoIds).length;
        videosUpdated = newVideoIds.intersection(oldVideoIds).length;
        
        // Update playlist
        await _database.upsertPlaylist(playlist);
      }

      final result = SyncResult(
        success: true,
        playlistsSynced: 1,
        videosAdded: videosAdded,
        videosUpdated: videosUpdated,
        videosRemoved: videosRemoved,
      );

      _logger.i('Playlist sync completed: $result');
      _completeSync(SyncStatus.success, result);
      return result;

    } catch (e, stackTrace) {
      _logger.e('Playlist sync failed for $playlistId', error: e, stackTrace: stackTrace);
      
      final result = SyncResult(
        success: false,
        errorMessage: _getErrorMessage(e),
      );
      
      _completeSync(SyncStatus.error, result);
      return result;
    }
  }

  /// Check if sync is needed based on last sync time
  /// 
  /// This is informational only - sync is never automatic.
  bool shouldSyncBasedOnTime(Duration threshold) {
    if (_lastSyncTime == null) {
      return true; // Never synced
    }
    
    final timeSinceSync = DateTime.now().difference(_lastSyncTime!);
    return timeSinceSync > threshold;
  }

  /// Get human-readable sync status message
  String getStatusMessage() {
    switch (_status) {
      case SyncStatus.idle:
        if (_lastSyncTime != null) {
          return 'Last sync: ${_formatTimeSince(_lastSyncTime!)}';
        }
        return 'Ready to sync';
      
      case SyncStatus.syncing:
        return 'Syncing playlists...';
      
      case SyncStatus.success:
        return _lastResult?.toString() ?? 'Sync successful';
      
      case SyncStatus.error:
        return _lastResult?.errorMessage ?? 'Sync failed';
    }
  }

  /// Determine if playlist should be updated
  bool _shouldUpdatePlaylist(VideoList existing, VideoList updated) {
    // Check sync version
    if (updated.syncVersion > existing.syncVersion) {
      return true;
    }

    // Check if video list changed
    if (existing.videos.length != updated.videos.length) {
      return true;
    }

    // Check video IDs
    final existingIds = existing.videos.map((v) => v.id).toSet();
    final updatedIds = updated.videos.map((v) => v.id).toSet();
    if (!existingIds.containsAll(updatedIds) || !updatedIds.containsAll(existingIds)) {
      return true;
    }

    // Check other fields
    if (existing.name != updated.name ||
        existing.loopMode != updated.loopMode ||
        existing.isActive != updated.isActive) {
      return true;
    }

    return false;
  }

  /// Complete sync operation
  void _completeSync(SyncStatus status, SyncResult result) {
    _status = status;
    _lastResult = result;
    _lastSyncTime = DateTime.now();
    _isSyncing = false;
    notifyListeners();
  }

  /// Extract user-friendly error message from exception
  String _getErrorMessage(dynamic error) {
    if (error is ApiException) {
      return error.message;
    }
    return error.toString();
  }

  /// Format time since a given timestamp
  String _formatTimeSince(DateTime time) {
    final duration = DateTime.now().difference(time);
    
    if (duration.inMinutes < 1) {
      return 'just now';
    } else if (duration.inHours < 1) {
      return '${duration.inMinutes}m ago';
    } else if (duration.inDays < 1) {
      return '${duration.inHours}h ago';
    } else {
      return '${duration.inDays}d ago';
    }
  }

  /// Reset sync state
  void reset() {
    _status = SyncStatus.idle;
    _lastResult = null;
    _isSyncing = false;
    notifyListeners();
  }
}
