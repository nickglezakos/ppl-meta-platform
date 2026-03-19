import 'dart:async';
import 'package:flutter/material.dart';
import 'package:logger/logger.dart';
import 'package:video_player/video_player.dart';
import 'package:signage_simple_player/database/playlist_database.dart';
import 'package:signage_simple_player/models/video_list.dart';
import 'package:signage_simple_player/models/playback_models.dart';

/// Video player engine for signage playback
/// 
/// Manages video playback with features:
/// - Playlist management (load, play, pause, stop, next, previous)
/// - Seamless transitions with pre-loading
/// - Multiple loop modes
/// - Database integration
/// - Error handling and recovery
class SignagePlayerEngine extends ChangeNotifier {
  final PlaylistDatabase _database;
  final Logger _logger;
  final int preloadCount;

  // Current state
  VideoPlayerController? _currentController;
  VideoPlayerController? _nextController;
  VideoList? _currentPlaylist;
  int _currentIndex = 0;
  PlaybackState _state = PlaybackState.stopped;
  LoopMode _loopMode = LoopMode.continuous;
  String? _errorMessage;
  bool _isTransitioning = false;  // Guard against multiple completion calls
  
  // Listeners
  StreamSubscription<void>? _positionListener;
  StreamSubscription<void>? _errorListener;

  SignagePlayerEngine({
    required PlaylistDatabase database,
    required Logger logger,
    this.preloadCount = 2,
  })  : _database = database,
        _logger = logger;

  // Getters
  VideoPlayerController? get currentController => _currentController;
  VideoList? get currentPlaylist => _currentPlaylist;
  int get currentIndex => _currentIndex;
  PlaybackState get state => _state;
  LoopMode get loopMode => _loopMode;
  String? get errorMessage => _errorMessage;
  
  VideoItem? get currentVideo {
    if (_currentPlaylist == null || _currentIndex >= _currentPlaylist!.videos.length) {
      return null;
    }
    return _currentPlaylist!.videos[_currentIndex];
  }
  
  VideoItem? get nextVideo {
    if (_currentPlaylist == null || _currentIndex + 1 >= _currentPlaylist!.videos.length) {
      return null;
    }
    return _currentPlaylist!.videos[_currentIndex + 1];
  }

  Duration get currentPosition {
    return _currentController?.value.position ?? Duration.zero;
  }

  Duration get currentDuration {
    return _currentController?.value.duration ?? Duration.zero;
  }

  double get progressPercent {
    if (_currentController == null || !_currentController!.value.isInitialized) {
      return 0.0;
    }
    final duration = currentDuration.inMilliseconds;
    final position = currentPosition.inMilliseconds;
    if (duration <= 0) return 0.0;
    return (position / duration * 100).clamp(0.0, 100.0);
  }

  bool get isPlaying => _state == PlaybackState.playing;
  bool get isPaused => _state == PlaybackState.paused;
  bool get isStopped => _state == PlaybackState.stopped;
  bool get isLoading => _state == PlaybackState.loading;
  bool get hasError => _state == PlaybackState.error;

  /// Load a playlist from the database
  /// Tries backend source_list_id (UUID) first, then falls back to local ID
  Future<bool> loadPlaylist(String playlistId) async {
    try {
      _logger.i('Loading playlist: $playlistId');
      _setState(PlaybackState.loading);

      // Try to load by source_list_id (backend UUID) first
      var playlist = await _database.getPlaylistBySourceId(playlistId);
      
      // If not found, try by local ID for backwards compatibility
      if (playlist == null) {
        _logger.i('Not found by source_list_id, trying local ID...');
        playlist = await _database.getPlaylist(playlistId);
      }

      if (playlist == null) {
        _logger.w('Playlist not found: $playlistId');
        _setState(PlaybackState.error);
        return false;
      }

      if (playlist.videos.isEmpty) {
        _logger.w('Playlist is empty: ${playlist.name}');
        _setState(PlaybackState.error);
        return false;
      }

      // Clean up current controllers
      await _disposeControllers();

      _currentPlaylist = playlist;
      _currentIndex = 0;
      _setState(PlaybackState.stopped);

      _logger.i('Playlist loaded successfully: ${playlist.name} (${playlist.videos.length} videos)');
      return true;
    } catch (e, stack) {
      _logger.e('Failed to load playlist', error: e, stackTrace: stack);
      _setState(PlaybackState.error, errorMessage: 'Failed to load playlist: $e');
      return false;
    }
  }

  /// Load a playlist from the database by backend source_list_id (UUID)
  /// This is used when backend sends playlist switch commands
  Future<bool> loadPlaylistBySourceId(String sourceListId) async {
    try {
      _logger.i('Loading playlist by source ID: $sourceListId');
      _setState(PlaybackState.loading);

      final playlist = await _database.getPlaylistBySourceId(sourceListId);
      if (playlist == null) {
        _logger.w('Playlist not found by source ID: $sourceListId');
        _setState(PlaybackState.error, errorMessage: 'Playlist not found. ID may not be synced.');
        return false;
      }

      if (playlist.videos.isEmpty) {
        _logger.w('Playlist is empty: ${playlist.name} (source: $sourceListId)');
        _setState(PlaybackState.error, errorMessage: 'Playlist is empty');
        return false;
      }

      // Clean up current controllers
      await _disposeControllers();

      _currentPlaylist = playlist;
      _currentIndex = 0;
      _setState(PlaybackState.stopped);

      _logger.i('Playlist loaded by source ID: ${playlist.name} (${playlist.videos.length} videos)');
      return true;
    } catch (e, stack) {
      _logger.e('Failed to load playlist by source ID', error: e, stackTrace: stack);
      _setState(PlaybackState.error, errorMessage: 'Failed to load playlist: $e');
      return false;
    }
  }

  /// Start playback
  Future<bool> play() async {
    try {
      if (_currentPlaylist == null || _currentPlaylist!.videos.isEmpty) {
        _logger.w('Cannot play: No playlist loaded');
        return false;
      }

      if (_state == PlaybackState.paused && _currentController != null) {
        // Resume from pause
        _logger.i('Resuming playback');
        await _currentController!.play();
        _setState(PlaybackState.playing);
        return true;
      }

      // Start fresh playback
      _logger.i('Starting playback at index $_currentIndex');
      _setState(PlaybackState.loading);

      final success = await _playVideoAtIndex(_currentIndex);
      if (success) {
        _setState(PlaybackState.playing);
        // Pre-load next video
        _preloadNextVideo();
      } else {
        _setState(PlaybackState.error);
      }

      return success;
    } catch (e, stack) {
      _logger.e('Failed to start playback', error: e, stackTrace: stack);
      _setState(PlaybackState.error);
      return false;
    }
  }

  /// Pause playback
  Future<void> pause() async {
    try {
      if (_currentController == null || !isPlaying) {
        return;
      }

      _logger.i('Pausing playback');
      await _currentController!.pause();
      _setState(PlaybackState.paused);
    } catch (e, stack) {
      _logger.e('Failed to pause playback', error: e, stackTrace: stack);
    }
  }

  /// Resume playback
  Future<void> resume() async {
    try {
      if (_currentController == null || !isPaused) {
        return;
      }

      _logger.i('Resuming playback');
      await _currentController!.play();
      _setState(PlaybackState.playing);
    } catch (e, stack) {
      _logger.e('Failed to resume playback', error: e, stackTrace: stack);
    }
  }

  /// Stop playback
  Future<void> stop() async {
    try {
      _logger.i('Stopping playback');
      
      await _disposeControllers();
      _currentIndex = 0;
      _setState(PlaybackState.stopped);
    } catch (e, stack) {
      _logger.e('Failed to stop playback', error: e, stackTrace: stack);
    }
  }

  /// Play next video
  Future<bool> next() async {
    try {
      if (_currentPlaylist == null || _currentPlaylist!.videos.isEmpty) {
        _logger.w('Cannot skip: No playlist loaded');
        return false;
      }

      final nextIndex = _getNextIndex();
      _logger.i('Playing next video (current: $_currentIndex, next: $nextIndex, total: ${_currentPlaylist!.videos.length})');
      
      if (nextIndex == -1) {
        // No more videos
        _logger.i('End of playlist reached');
        await stop();
        return false;
      }

      _currentIndex = nextIndex;
      
      // If we pre-loaded, use that controller
      if (_nextController != null && _nextController!.value.isInitialized) {
        _logger.d('Using pre-loaded video');
        
        // Remove listener from old controller before disposing
        _currentController?.removeListener(_onVideoPositionChanged);
        await _currentController?.dispose();
        
        _currentController = _nextController;
        _nextController = null;
        
        // CRITICAL: Add listener to the new controller
        _currentController!.addListener(_onVideoPositionChanged);
        
        await _currentController!.play();
        _setState(PlaybackState.playing);
        
        // Pre-load next
        _preloadNextVideo();
        return true;
      } else {
        // Load fresh
        final success = await _playVideoAtIndex(_currentIndex);
        if (success) {
          _preloadNextVideo();
        }
        return success;
      }
    } catch (e, stack) {
      _logger.e('Failed to play next video', error: e, stackTrace: stack);
      _setState(PlaybackState.error);
      return false;
    }
  }

  /// Play previous video
  Future<bool> previous() async {
    try {
      if (_currentPlaylist == null || _currentPlaylist!.videos.isEmpty) {
        _logger.w('Cannot go back: No playlist loaded');
        return false;
      }

      if (_currentIndex == 0) {
        _logger.w('Already at first video');
        return false;
      }

      _logger.i('Playing previous video');
      _currentIndex--;

      final success = await _playVideoAtIndex(_currentIndex);
      if (success) {
        _preloadNextVideo();
      }
      
      return success;
    } catch (e, stack) {
      _logger.e('Failed to play previous video', error: e, stackTrace: stack);
      _setState(PlaybackState.error);
      return false;
    }
  }

  /// Seek to position
  Future<void> seekTo(Duration position) async {
    try {
      if (_currentController == null || !_currentController!.value.isInitialized) {
        return;
      }

      _logger.d('Seeking to ${position.inSeconds}s');
      await _currentController!.seekTo(position);
    } catch (e, stack) {
      _logger.e('Failed to seek', error: e, stackTrace: stack);
    }
  }

  /// Set loop mode
  void setLoopMode(LoopMode mode) {
    _logger.i('Setting loop mode to $mode');
    _loopMode = mode;
    
    // Update current controller looping
    if (_currentController != null && mode == LoopMode.single) {
      _currentController!.setLooping(true);
    } else if (_currentController != null) {
      _currentController!.setLooping(false);
    }
    
    notifyListeners();
  }

  /// Play video at specific index
  Future<bool> _playVideoAtIndex(int index) async {
    try {
      if (_currentPlaylist == null || index >= _currentPlaylist!.videos.length) {
        return false;
      }

      final video = _currentPlaylist!.videos[index];
      _logger.i('Playing video: ${video.title} (${video.url})');

      _setState(PlaybackState.loading);

      // Dispose current controller
      await _currentController?.dispose();
      _positionListener?.cancel();

      // Create new controller
      _currentController = VideoPlayerController.networkUrl(Uri.parse(video.url));
      
      // Initialize
      await _currentController!.initialize();
      
      // Set looping for single mode
      if (_loopMode == LoopMode.single) {
        _currentController!.setLooping(true);
      }

      // Listen for completion
      _currentController!.addListener(_onVideoPositionChanged);

      // Start playback
      await _currentController!.play();
      
      _setState(PlaybackState.playing);
      notifyListeners();
      return true;
    } catch (e, stack) {
      _logger.e('Failed to play video at index $index', error: e, stackTrace: stack);
      _setState(PlaybackState.error, errorMessage: 'Failed to play video: $e');
      return false;
    }
  }

  /// Pre-load next video for seamless transition
  Future<void> _preloadNextVideo() async {
    try {
      final nextIndex = _getNextIndex();
      if (nextIndex == -1 || _currentPlaylist == null) {
        return;
      }

      final video = _currentPlaylist!.videos[nextIndex];
      _logger.d('Pre-loading next video: ${video.title}');

      await _nextController?.dispose();
      _nextController = VideoPlayerController.networkUrl(Uri.parse(video.url));
      await _nextController!.initialize();
      
      _logger.d('Next video pre-loaded successfully');
    } catch (e, stack) {
      _logger.w('Failed to pre-load next video', error: e, stackTrace: stack);
      // Non-fatal, just means no seamless transition
    }
  }

  /// Handle video position changes
  void _onVideoPositionChanged() {
    if (_currentController == null || !_currentController!.value.isInitialized) {
      return;
    }

    final position = _currentController!.value.position;
    final duration = _currentController!.value.duration;

    // Check if video finished (within 500ms of end to catch it reliably)
    if (!_isTransitioning && 
        duration.inMilliseconds > 0 && 
        (duration - position).inMilliseconds < 500) {
      _onVideoCompleted();
    }

    notifyListeners();
  }

  /// Handle video completion
  void _onVideoCompleted() {
    if (_isTransitioning) {
      return;  // Already handling completion
    }
    
    _isTransitioning = true;
    _logger.i('Video completed - transitioning to next');

    if (_loopMode == LoopMode.single) {
      // Single loop mode - controller handles this automatically
      _isTransitioning = false;
      return;
    }

    if (_loopMode == LoopMode.once && _currentIndex >= _currentPlaylist!.videos.length - 1) {
      // Play once mode and at end
      _logger.i('Playlist completed (once mode)');
      _isTransitioning = false;
      stop();
      return;
    }

    // Continuous mode or more videos - must await to handle errors properly
    _logger.i('Auto-advancing to next video (current: $_currentIndex)');
    next().then((success) {
      _isTransitioning = false;
      if (!success) {
        _logger.e('Failed to advance to next video');
        _setState(PlaybackState.error, errorMessage: 'Failed to load next video');
      }
    }).catchError((e) {
      _isTransitioning = false;
      _logger.e('Error advancing to next video: $e');
      _setState(PlaybackState.error, errorMessage: 'Error loading next video: $e');
    });
  }

  /// Get next index based on loop mode
  int _getNextIndex() {
    if (_currentPlaylist == null || _currentPlaylist!.videos.isEmpty) {
      return -1;
    }

    final nextIndex = _currentIndex + 1;

    if (nextIndex >= _currentPlaylist!.videos.length) {
      if (_loopMode == LoopMode.continuous) {
        return 0; // Loop back to start
      } else {
        return -1; // End of playlist
      }
    }

    return nextIndex;
  }

  /// Update playback state
  void _setState(PlaybackState newState, {String? errorMessage}) {
    if (_state != newState) {
      _state = newState;
      if (newState == PlaybackState.error) {
        _errorMessage = errorMessage ?? 'Unknown error occurred';
      } else {
        _errorMessage = null;
      }
      notifyListeners();
    }
  }

  /// Dispose controllers
  Future<void> _disposeControllers() async {
    await _positionListener?.cancel();
    await _errorListener?.cancel();
    
    await _currentController?.dispose();
    await _nextController?.dispose();
    
    _currentController = null;
    _nextController = null;
    _positionListener = null;
    _errorListener = null;
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  /// Get current playback status
  PlaybackStatus getPlaybackStatus(String deviceId) {
    CurrentVideoInfo? currentVideoInfo;
    PlaylistInfo? playlistInfo;

    if (currentVideo != null && _currentController != null) {
      currentVideoInfo = CurrentVideoInfo(
        videoId: currentVideo!.videoId,
        title: currentVideo!.title,
        positionMs: currentPosition.inMilliseconds,
        durationMs: currentDuration.inMilliseconds,
        progressPercent: progressPercent,
      );
    }

    if (_currentPlaylist != null) {
      playlistInfo = PlaylistInfo(
        id: _currentPlaylist!.id,
        name: _currentPlaylist!.name,
        totalVideos: _currentPlaylist!.videos.length,
        currentIndex: _currentIndex,
      );
    }

    return PlaybackStatus(
      deviceId: deviceId,
      playbackState: _state,
      currentVideo: currentVideoInfo,
      playlist: playlistInfo,
    );
  }
}
