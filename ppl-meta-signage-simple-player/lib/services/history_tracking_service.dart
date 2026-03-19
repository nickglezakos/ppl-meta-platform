import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/services/player_engine.dart';
import 'package:signage_simple_player/models/playback_models.dart';
import 'package:signage_simple_player/models/playback_history.dart';
import 'package:signage_simple_player/models/video_list.dart' show VideoItem;
import 'package:uuid/uuid.dart';

/// Service for tracking and recording playback history
/// 
/// Monitors the player engine and automatically records:
/// - Playback start events
/// - Playback completion (with percentage)
/// - Playback interruptions
/// - Playback errors
/// - Duration played
class HistoryTrackingService {
  final PlaylistDatabase _database;
  final SignagePlayerEngine _playerEngine;
  final Logger _logger;
  final String _deviceId;
  final Uuid _uuid = const Uuid();

  // Current tracking state
  PlaybackSession? _currentSession;
  Timer? _progressUpdateTimer;
  bool _isTracking = false;

  HistoryTrackingService({
    required PlaylistDatabase database,
    required SignagePlayerEngine playerEngine,
    required Logger logger,
    required String deviceId,
  })  : _database = database,
        _playerEngine = playerEngine,
        _logger = logger,
        _deviceId = deviceId;

  bool get isTracking => _isTracking;
  PlaybackSession? get currentSession => _currentSession;

  /// Start tracking playback events
  void startTracking() {
    if (_isTracking) {
      _logger.w('History tracking already started');
      return;
    }

    _logger.i('Starting playback history tracking');
    _isTracking = true;

    // Listen to player engine state changes
    _playerEngine.addListener(_onPlayerStateChanged);

    // Start periodic progress updates
    _startProgressTimer();
  }

  /// Stop tracking playback events
  Future<void> stopTracking() async {
    if (!_isTracking) {
      return;
    }

    _logger.i('Stopping playback history tracking');
    _isTracking = false;

    // Stop listening to player engine
    _playerEngine.removeListener(_onPlayerStateChanged);

    // Stop progress timer
    _stopProgressTimer();

    // Finalize current session if exists
    if (_currentSession != null) {
      await _finalizeSession(interrupted: true);
    }
  }

  /// Handle player state changes
  void _onPlayerStateChanged() {
    if (!_isTracking) return;

    final state = _playerEngine.isPlaying 
        ? PlaybackState.playing 
        : _playerEngine.isPaused 
            ? PlaybackState.paused 
            : _playerEngine.isStopped 
                ? PlaybackState.stopped 
                : _playerEngine.isLoading 
                    ? PlaybackState.loading 
                    : _playerEngine.hasError
                        ? PlaybackState.error
                        : PlaybackState.stopped;

    final currentVideo = _playerEngine.currentVideo;

    // Handle state transitions
    if (state == PlaybackState.playing && currentVideo != null) {
      _handlePlaybackStart(currentVideo);
    } else if (state == PlaybackState.stopped) {
      if (_currentSession != null) {
        _finalizeSession(completed: true);
      }
    } else if (state == PlaybackState.error) {
      if (_currentSession != null) {
        _finalizeSession(errorMessage: 'Playback error occurred');
      }
    } else if (state == PlaybackState.paused) {
      if (_currentSession != null) {
        _currentSession!.pauseCount++;
        _logger.d('Playback paused (total pauses: ${_currentSession!.pauseCount})');
      }
    }

    // Check for video completion
    if (currentVideo != null && _currentSession != null) {
      if (_currentSession!.videoId != currentVideo.videoId) {
        // Video changed - finalize previous session
        _finalizeSession(completed: true);
        _handlePlaybackStart(currentVideo);
      }
    }
  }

  /// Handle playback start event
  void _handlePlaybackStart(VideoItem video) {
    // If there's an active session for a different video, finalize it
    if (_currentSession != null && _currentSession!.videoId != video.videoId) {
      _finalizeSession(completed: true);
    }

    // If already tracking this video, don't create a new session
    if (_currentSession != null && _currentSession!.videoId == video.videoId) {
      // Already tracking this video - silently return (no log spam)
      return;
    }

    _logger.i('Starting new playback session for video: ${video.title}');

    _currentSession = PlaybackSession(
      id: _uuid.v4(),
      videoId: video.videoId,
      videoTitle: video.title,
      playlistId: _playerEngine.currentPlaylist?.id ?? 'unknown',
      playlistName: _playerEngine.currentPlaylist?.name,
      videoDurationMs: video.durationMs ?? 0,
      startedAt: DateTime.now(),
      deviceId: _deviceId,
    );
  }

  /// Finalize current playback session
  Future<void> _finalizeSession({
    bool completed = false,
    bool interrupted = false,
    String? errorMessage,
  }) async {
    if (_currentSession == null) return;

    final session = _currentSession!;
    _currentSession = null;

    try {
      final completedAt = DateTime.now();
      final totalDurationMs = completedAt.difference(session.startedAt).inMilliseconds;
      
      // Calculate actual playback duration (excluding pause time)
      final durationPlayedMs = session.lastPositionMs > 0 
          ? session.lastPositionMs 
          : totalDurationMs;

      // Calculate completion percentage
      double completionPercent = 0.0;
      if (session.videoDurationMs > 0) {
        completionPercent = (durationPlayedMs / session.videoDurationMs * 100).clamp(0, 100);
      }

      // Determine if this was a successful completion
      final isCompleted = completed && completionPercent >= 95.0;

      _logger.i(
        'Finalizing session: ${session.videoTitle} - '
        '${completionPercent.toStringAsFixed(1)}% complete, '
        'duration: ${durationPlayedMs}ms, '
        'pauses: ${session.pauseCount}, '
        'interrupted: $interrupted',
      );

      // Create history entry
      final historyEntry = PlaybackHistoryEntry(
        id: session.id,
        videoId: session.videoId,
        videoTitle: session.videoTitle,
        playlistId: session.playlistId,
        playlistName: session.playlistName,
        startedAt: session.startedAt,
        completedAt: isCompleted ? completedAt : null,
        durationPlayedMs: durationPlayedMs,
        completionPercent: completionPercent,
        interruptions: session.pauseCount + (interrupted ? 1 : 0),
        errorOccurred: errorMessage != null || session.errorOccurred,
        errorMessage: errorMessage ?? session.errorMessage,
        deviceId: session.deviceId,
        createdAt: DateTime.now(),
      );

      // Save to database
      await _database.insertHistory(historyEntry);

      _logger.d('History entry saved: ${historyEntry.id}');
    } catch (e, stack) {
      _logger.e('Failed to finalize playback session', error: e, stackTrace: stack);
    }
  }

  /// Start periodic progress updates
  void _startProgressTimer() {
    _stopProgressTimer(); // Ensure no duplicate timers

    _progressUpdateTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _updateSessionProgress(),
    );
  }

  /// Stop progress update timer
  void _stopProgressTimer() {
    _progressUpdateTimer?.cancel();
    _progressUpdateTimer = null;
  }

  /// Update current session progress
  void _updateSessionProgress() {
    if (_currentSession == null || !_playerEngine.isPlaying) {
      return;
    }

    final currentPosition = _playerEngine.currentPosition;
    _currentSession!.lastPositionMs = currentPosition.inMilliseconds;

    // Check for completion based on position
    if (_currentSession!.videoDurationMs > 0) {
      final percent = (currentPosition.inMilliseconds / _currentSession!.videoDurationMs * 100);
      
      if (percent >= 99.0 && !_currentSession!.markedAsComplete) {
        _currentSession!.markedAsComplete = true;
        _logger.d('Video reached 99% completion: ${_currentSession!.videoTitle}');
      }
    }
  }

  /// Record an error event
  Future<void> recordError(String errorMessage) async {
    _logger.w('Recording playback error: $errorMessage');

    if (_currentSession != null) {
      _currentSession!.errorOccurred = true;
      _currentSession!.errorMessage = errorMessage;
    }

    // If there's an active session, finalize it with error
    if (_currentSession != null) {
      await _finalizeSession(errorMessage: errorMessage);
    }
  }

  /// Get statistics for current device
  Future<Map<String, dynamic>> getStatistics({
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    try {
      final summary = await _database.getPlaybackSummary(
        startDate: startDate,
        endDate: endDate,
      );

      return {
        'total_playback_time_ms': summary.totalPlaybackTimeMs,
        'unique_videos_played': summary.uniqueVideosPlayed,
        'average_completion_rate': summary.averageCompletionRate,
        'most_played_video': summary.mostPlayedVideo?.toJson(),
        'current_session_active': _currentSession != null,
      };
    } catch (e, stack) {
      _logger.e('Failed to get statistics', error: e, stackTrace: stack);
      return {};
    }
  }

  /// Dispose resources
  Future<void> dispose() async {
    await stopTracking();
  }
}

/// Internal class to track active playback session
class PlaybackSession {
  final String id;
  final String videoId;
  final String videoTitle;
  final String playlistId;
  final String? playlistName;
  final int videoDurationMs;
  final DateTime startedAt;
  final String deviceId;

  int lastPositionMs = 0;
  int pauseCount = 0;
  bool errorOccurred = false;
  String? errorMessage;
  bool markedAsComplete = false;

  PlaybackSession({
    required this.id,
    required this.videoId,
    required this.videoTitle,
    required this.playlistId,
    this.playlistName,
    required this.videoDurationMs,
    required this.startedAt,
    required this.deviceId,
  });
}
