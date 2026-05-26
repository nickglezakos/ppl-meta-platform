import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../models/media_models.dart';
import '../models/face_detection_models.dart';
import '../services/media_api_client.dart';
import '../services/orchestrator_api_client.dart'; // Import for Enhanced Logic V2 API
import '../services/distance_color_service.dart';
import '../widgets/video_player_widget.dart';
import '../widgets/simple_video_face_detection_overlay.dart';
import '../providers/workflow_providers.dart';
import '../providers/face_data_providers.dart';
import '../providers/face_memory_manager.dart';

/// EXPERIMENTAL SMOOTH TRANSITIONS: 
/// To revert to basic frame sync, change _enableSmoothTransitions to false on line ~55

/// Smart Video Player Widget for Workflows 4 & 5
/// Intelligently selects playback mode based on processing status
/// and implements optimized face detection overlay strategies
class SmartVideoPlayerWidget extends ConsumerStatefulWidget {
  final MediaItem mediaItem;
  final Map<String, String>? headers;
  final String? collectionId;
  final Function(VideoPlayerController)? onControllerReady;
  final VoidCallback? onDetailsPressed;
  final List<FaceDetection>? initialFaceData;
  final String initialFaceDataSource;
  final bool enableWorkflowIntegration;

  const SmartVideoPlayerWidget({
    super.key,
    required this.mediaItem,
    this.headers,
    this.collectionId,
    this.onControllerReady,
    this.onDetailsPressed,
    this.initialFaceData,
    this.initialFaceDataSource = 'external_mvr_data',
    this.enableWorkflowIntegration = true,
  });

  @override
  ConsumerState<SmartVideoPlayerWidget> createState() => _SmartVideoPlayerWidgetState();
}

class _SmartVideoPlayerWidgetState extends ConsumerState<SmartVideoPlayerWidget> {
  VideoPlayerController? _videoController;
  PlaybackMode? _currentPlaybackMode;
  ProcessingStatus? _processingStatus;
  List<FaceDetection>? _storedFaceData;
  bool _isLoadingWorkflowData = true;
  bool _isLoadingFaces = false; // Track face loading state
  int _faceLoadAttempts = 0;
  DateTime? _lastFaceLoadAttemptAt;
  static const int _maxFaceLoadAttempts = 4;
  static const Duration _faceLoadRetryCooldown = Duration(seconds: 3);
  String? _workflowError;
  String _faceDataSource = 'none'; // Track data source for color coding
  
  // Frame synchronization for face rectangles
  List<FaceDetection> _currentSyncedFaces = [];
  List<FaceDetection> _allStoredFaces = [];
  String _currentDataSource = 'none';
  
  // Frame-based synchronization variables
  Map<int, List<FaceDetection>>? _facesByFrame; // Frame number -> List of faces detected in that frame
  Map<FaceDetection, int> _faceFirstSeenFrame = {}; // Track when each face first appeared
  bool _hasPlaybackStarted = false; // Track if video has started playing
  
  // DISABLED: Smooth transitions - now using frame-based synchronization
  static const bool _enableSmoothTransitions = false; // DISABLED for frame-based sync
  Map<FaceDetection, double> _faceOpacities = {}; // Track opacity for each face
  Map<FaceDetection, int> _faceFrameCounters = {}; // Track how long face has been visible
  bool _isLoadingStoredFaces = false;
  
  // Cache provider references for safe disposal
  late final FaceDataCache _faceDataCache;
  late final MediaFaceDataNotifier _mediaFaceDataNotifier;

  @override
  void initState() {
    super.initState();

    final hasExternalFaceData =
        widget.initialFaceData != null && widget.initialFaceData!.isNotEmpty;
    
    // Cache provider references for safe disposal
    _faceDataCache = ref.read(faceDataCacheProvider);
    _mediaFaceDataNotifier = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid).notifier);

    if (hasExternalFaceData) {
      _storedFaceData = widget.initialFaceData;
      _faceDataSource = widget.initialFaceDataSource;
      debugPrint('🎯 EXTERNAL FACE DATA: Loaded ${widget.initialFaceData!.length} faces for ${widget.mediaItem.uuid}');
    }
    
    // [FIX] DISABLED automatic provider face loading - the overlay now handles this directly
    // The overlay calls Enhanced Logic V2 API directly in _checkForStoredFaces()
    // Old code was causing duplicate API calls:
    // WidgetsBinding.instance.addPostFrameCallback((_) {
    //   if (mounted) {
    //     debugPrint('POST-FRAME: Triggering face data load for ${widget.mediaItem.uuid}');
    //     _mediaFaceDataNotifier.loadFaces();
    //   }
    // });
    
    if (!widget.enableWorkflowIntegration) {
      _setFallbackPlaybackMode();
      _isLoadingWorkflowData = false;
      _startPreviewStoredFaceLoad();
    } else if (hasExternalFaceData) {
      _setFallbackPlaybackMode();
      _isLoadingWorkflowData = false;
    } else {
      _initializeSmartPlayback();
    }
  }

  @override
  void didUpdateWidget(covariant SmartVideoPlayerWidget oldWidget) {
    super.didUpdateWidget(oldWidget);

    final nextFaceData = widget.initialFaceData;
    final previousFaceData = oldWidget.initialFaceData;
    final hasNewExternalFaces = nextFaceData != null && nextFaceData.isNotEmpty;
    final externalFacesChanged = !identical(nextFaceData, previousFaceData);

    if (hasNewExternalFaces && externalFacesChanged) {
      debugPrint('🔄 EXTERNAL FACE DATA UPDATED: Loaded ${nextFaceData.length} faces for ${widget.mediaItem.uuid}');

      _storedFaceData = nextFaceData;
      _faceDataSource = widget.initialFaceDataSource;

      if (_videoController != null) {
        _videoController!.removeListener(_onVideoFrameChanged);
      }

      _setupFaceFrameSync(nextFaceData, _faceDataSource);

      if (_isLoadingWorkflowData || _workflowError != null) {
        setState(() {
          _isLoadingWorkflowData = false;
          _workflowError = null;
        });
      }
    }

    if (!widget.enableWorkflowIntegration &&
        widget.initialFaceData == null &&
        !identical(oldWidget.mediaItem.uuid, widget.mediaItem.uuid)) {
      _startPreviewStoredFaceLoad();
    }
  }

  void _startPreviewStoredFaceLoad() {
    final hasExternalFaceData =
        widget.initialFaceData != null && widget.initialFaceData!.isNotEmpty;
    if (_isLoadingStoredFaces || hasExternalFaceData) {
      return;
    }

    _isLoadingStoredFaces = true;
    debugPrint('📦 PREVIEW FLOW: Starting direct stored face data load for ${widget.mediaItem.uuid}');
    Future.microtask(() async {
      if (!mounted || _storedFaceData?.isNotEmpty == true) {
        _isLoadingStoredFaces = false;
        return;
      }

      debugPrint('📦 PREVIEW FLOW: Queueing stored face data load for ${widget.mediaItem.uuid}');
      await _loadStoredFaceData();

      _isLoadingStoredFaces = false;

      if (!mounted) {
        return;
      }

      debugPrint('📦 PREVIEW FLOW: Stored face load complete for ${widget.mediaItem.uuid} -> ${_storedFaceData?.length ?? 0} faces from $_faceDataSource');
      setState(() {});
    });
  }

  /// Setup frame synchronization for face rectangles
  void _setupFaceFrameSync(List<FaceDetection> facesToDisplay, String dataSource) {
    debugPrint('🎬 FRAME SYNC: Setting up frame synchronization for ${facesToDisplay.length} faces');
    debugPrint('🧪 OVERLAY DEBUG: media=${widget.mediaItem.uuid}, source=$dataSource, incoming_faces=${facesToDisplay.length}');
    _allStoredFaces = facesToDisplay;
    _currentDataSource = dataSource;
    
    // Load frame-based face data from global cache for proper synchronization
    final globalManager = FaceDataMemoryManager.instance;
    _facesByFrame = globalManager.getMemoryCache(widget.mediaItem.uuid);
    
    // Fallback: build frame map directly from FaceDetection metadata when global cache isn't hydrated
    if (_facesByFrame == null || _facesByFrame!.isEmpty) {
      final generatedFrameMap = _buildFrameMapFromFaces(facesToDisplay);
      if (generatedFrameMap.isNotEmpty) {
        _facesByFrame = generatedFrameMap;
        debugPrint('🧩 FRAME MAP GENERATED: Built ${generatedFrameMap.keys.length} frames from FaceDetection metadata');
      }
    }
    
    if (_facesByFrame != null && _facesByFrame!.isNotEmpty) {
      final sortedFrames = _facesByFrame!.keys.toList()..sort();
      final minFrame = sortedFrames.first;
      final maxFrame = sortedFrames.last;
      final totalFacesInCache = _facesByFrame!.values.fold(0, (sum, faces) => sum + faces.length);
      final sampleFrames = sortedFrames.take(8).toList();
      
      debugPrint('✅ FRAME DATA LOADED for sync: ${_facesByFrame!.keys.length} frames with face data');
      debugPrint('📊 Frame range: $minFrame to $maxFrame (total $totalFacesInCache faces)');
      debugPrint('🧪 OVERLAY DEBUG: media=${widget.mediaItem.uuid}, frame_count=${_facesByFrame!.keys.length}, sample_frames=$sampleFrames');
      
      // Debug: Show ALL frames with faces
      debugPrint('📋 COMPLETE FRAME LIST:');
      for (final frame in sortedFrames) {
        debugPrint('  Frame $frame: ${_facesByFrame![frame]!.length} faces');
      }
    } else {
      debugPrint('❌ NO FRAME-BASED DATA AVAILABLE!');
      debugPrint('   _facesByFrame is null: ${_facesByFrame == null}');
      debugPrint('   _facesByFrame is empty: ${_facesByFrame?.isEmpty ?? true}');
      debugPrint('   Available faces in list: ${facesToDisplay.length}');
      debugPrint('   Media UUID: ${widget.mediaItem.uuid}');
    }
    
    // Add video position listener for frame synchronization
    _videoController?.addListener(_onVideoFrameChanged);
    
    // Don't initialize with any faces - wait for playback to start
    setState(() {
      _currentSyncedFaces = [];
      _faceFirstSeenFrame.clear();
      _hasPlaybackStarted = false;
    });
  }

  Map<int, List<FaceDetection>> _buildFrameMapFromFaces(List<FaceDetection> faces) {
    final frameMap = <int, List<FaceDetection>>{};

    for (final face in faces) {
      final metadata = face.metadata;
      if (metadata == null) {
        continue;
      }

      final dynamic rawFrame = metadata['frame_number'] ?? metadata['frame'] ?? metadata['frameNumber'];
      int? frameNumber;

      if (rawFrame is int) {
        frameNumber = rawFrame;
      } else if (rawFrame is String) {
        frameNumber = int.tryParse(rawFrame);
      } else if (rawFrame is num) {
        frameNumber = rawFrame.toInt();
      }

      if (frameNumber == null || frameNumber < 0) {
        continue;
      }

      frameMap.putIfAbsent(frameNumber, () => <FaceDetection>[]).add(face);
    }

    return frameMap;
  }

  /// Handle video position changes to sync face rectangles
  void _onVideoFrameChanged() {
    if (!mounted || _videoController == null) return;
    
    // If stored face data isn't loaded yet but video is playing, try to load it
    if (_allStoredFaces.isEmpty && _videoController!.value.isPlaying && _storedFaceData != null) {
      _setupFaceFrameSync(_storedFaceData!, _faceDataSource);
    }
    
    _updateCurrentFrameFaces();
  }

  /// Update faces based on current video frame
  void _updateCurrentFrameFaces() {
    if (_videoController == null || !_videoController!.value.isInitialized) return;

    // Track when playback actually starts (position moves from 0 or video is playing)
    if (_videoController!.value.isPlaying && _videoController!.value.position.inMilliseconds > 0) {
      _hasPlaybackStarted = true;
    }

    // Don't show any faces until video has actually started playing
    if (!_hasPlaybackStarted) {
      if (_currentSyncedFaces.isNotEmpty || _faceFirstSeenFrame.isNotEmpty) {
        setState(() {
          _currentSyncedFaces = [];
          _faceFirstSeenFrame.clear();
        });
        debugPrint('🚫 Playback not started - clearing faces');
      }
      return;
    }

    final currentPosition = _videoController!.value.position;
    final currentFrameNumber = _positionToFrameNumber(currentPosition);
    final totalFaces = _allStoredFaces.length;
    
    // 🔧 FIRST-PLAY FIX: If video is playing but no faces loaded, try emergency data load
    if (totalFaces == 0 && _videoController!.value.isPlaying && !_isLoadingWorkflowData) {
      debugPrint('🚨 EMERGENCY LOAD: Video playing but no faces loaded, trying immediate MediaFaceDataProvider read...');
      final faceDataState = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid));
      if (faceDataState.hasData && faceDataState.faces.isNotEmpty) {
        debugPrint('🚨 EMERGENCY SUCCESS: Found ${faceDataState.faces.length} faces in MediaFaceDataProvider cache');
        _setupFaceFrameSync(faceDataState.faces, 'Emergency_MediaFaceDataProvider_Cache');
        return; // Restart the method now that faces are loaded
      }
    }
    
    if (totalFaces == 0) {
      setState(() {
        _currentSyncedFaces = [];
        if (_enableSmoothTransitions) {
          _faceOpacities.clear();
          _faceFrameCounters.clear();
        }
      });
      return;
    }
    
    if (_enableSmoothTransitions) {
      _updateFacesWithTransitions(currentFrameNumber, totalFaces);
    } else {
      _updateFacesBasic(currentFrameNumber, totalFaces);
    }
  }
  
  /// Basic frame-based face updates using actual frame data from cache
  void _updateFacesBasic(int currentFrameNumber, int totalFaces) {
    // Use frame-based cache if available for proper synchronization
    List<FaceDetection> visibleFaces = [];
    
    // Scale display window and tolerance to actual FPS (~0.5s, matching USB camera timers)
    final actualFps = _getActualFps();
    final displayWindowFrames = (0.5 * actualFps).ceil().clamp(1, 30); // ~0.5s visibility
    final frameRange = (0.1 * actualFps).round().clamp(1, 3); // ~0.1s tolerance
    
    if (_facesByFrame != null && _facesByFrame!.isNotEmpty) {
      // Debug: Log current frame and what data exists (every 30 frames to avoid spam)
      if (currentFrameNumber % 30 == 0) {
        final hasDataForFrame = _facesByFrame!.containsKey(currentFrameNumber);
        final nearbyFramesWithData = _facesByFrame!.keys.where((f) => (f - currentFrameNumber).abs() <= 5).toList();
        debugPrint('🎯 Frame $currentFrameNumber: hasData=$hasDataForFrame, nearbyFrames=$nearbyFramesWithData');
      }
      
      // Check for faces in nearby frames (scaled tolerance for frame timing variations)
      for (int checkFrame = currentFrameNumber - frameRange; checkFrame <= currentFrameNumber + frameRange; checkFrame++) {
        if (_facesByFrame!.containsKey(checkFrame)) {
          final facesAtFrame = _facesByFrame![checkFrame]!;
          for (final face in facesAtFrame) {
            // Record when this face was first seen (use the actual detection frame, not current frame)
            if (!_faceFirstSeenFrame.containsKey(face)) {
              _faceFirstSeenFrame[face] = checkFrame;
              debugPrint('🆕 Frame $currentFrameNumber: Found face at frame $checkFrame (within range)');
            }
          }
        }
      }
      
      // Collect all faces that should still be visible (within ~0.5s window)
      final facesToRemove = <FaceDetection>[];
      _faceFirstSeenFrame.forEach((face, firstSeenFrame) {
        final framesSinceFirstSeen = currentFrameNumber - firstSeenFrame;
        if (framesSinceFirstSeen >= 0 && framesSinceFirstSeen < displayWindowFrames) {
          // Face is within display window
          visibleFaces.add(face);
        } else if (framesSinceFirstSeen >= displayWindowFrames) {
          // Face has exceeded display window, mark for removal
          facesToRemove.add(face);
          debugPrint('⏱️ Frame $currentFrameNumber: Removing face (shown for $framesSinceFirstSeen frames)');
        }
      });
      
      // Clean up expired faces from tracking
      for (final face in facesToRemove) {
        _faceFirstSeenFrame.remove(face);
      }
      
      if (visibleFaces.isNotEmpty || _currentSyncedFaces.isNotEmpty) {
        debugPrint('👁️ Frame $currentFrameNumber: Showing ${visibleFaces.length} faces (tracking ${_faceFirstSeenFrame.length} active)');
      }
    } else {
      // Fallback: No frame-based data available
      if (currentFrameNumber % 30 == 0) {
        debugPrint('❌ Frame $currentFrameNumber: No frame-based cache available');
      }
      visibleFaces = [];
    }

    if (_currentSyncedFaces.length != visibleFaces.length || 
        !_facesAreEqual(_currentSyncedFaces, visibleFaces)) {
      setState(() {
        _currentSyncedFaces = visibleFaces;
      });
    }
  }
  
  /// Smooth transition face updates with instant appearance and smooth fade-out
  void _updateFacesWithTransitions(int currentFrameNumber, int totalFaces) {
    final actualFps = _getActualFps().round();
    const int preShowFrames = 0; // No fade in - instant appearance
    final int postShowFrames = (actualFps * 0.6).round(); // ~600ms fade out scaled to actual FPS
    
    List<FaceDetection> visibleFaces = [];
    Map<FaceDetection, double> newOpacities = {};
    Map<FaceDetection, int> newCounters = Map.from(_faceFrameCounters);
    
    // Calculate which faces should be visible with transitions
    final facesPerFrame = (totalFaces / actualFps).ceil();
    final baseStartIndex = (currentFrameNumber % actualFps) * facesPerFrame;
    final baseEndIndex = (baseStartIndex + facesPerFrame).clamp(0, totalFaces);
    
    for (int i = 0; i < totalFaces; i++) {
      final face = _allStoredFaces[i];
      
      // Check if face is in the extended visibility window
      bool shouldShow = false;
      double opacity = 1.0;
      
      if (i >= baseStartIndex && i < baseEndIndex) {
        // Face is in main display window - INSTANT FULL OPACITY
        shouldShow = true;
        opacity = 1.0;
      } else {
        // Check if face should fade out (no fade in)
        final distanceFromEnd = (i - baseEndIndex).abs();
        
        if (i < baseStartIndex && distanceFromEnd <= postShowFrames * facesPerFrame) {
          // Fade out phase only - smooth gradual disappearance
          shouldShow = true;
          final fadeProgress = 1.0 - (distanceFromEnd / (postShowFrames * facesPerFrame));
          // Cubic easing for smoother, more gradual fade out
          opacity = (fadeProgress * fadeProgress * fadeProgress).clamp(0.0, 1.0);
        }
      }
      
      if (shouldShow && opacity > 0.05) { // Only show if opacity is meaningful
        visibleFaces.add(face);
        newOpacities[face] = opacity;
        newCounters[face] = (newCounters[face] ?? 0) + 1;
      } else {
        newCounters.remove(face);
      }
    }
    
    // Check if update is needed
    bool needsUpdate = !_facesAreEqual(visibleFaces, _currentSyncedFaces);
    
    // Check if opacities changed significantly
    if (!needsUpdate) {
      for (final face in visibleFaces) {
        final oldOpacity = _faceOpacities[face] ?? 0.0;
        final newOpacity = newOpacities[face] ?? 0.0;
        if ((oldOpacity - newOpacity).abs() > 0.05) {
          needsUpdate = true;
          break;
        }
      }
    }
    
    if (needsUpdate) {
      setState(() {
        _currentSyncedFaces = visibleFaces;
        _faceOpacities = newOpacities;
        _faceFrameCounters = newCounters;
      });
      debugPrint('🎬 Frame ${currentFrameNumber}: ${_currentSyncedFaces.length} smooth faces rendered');
    }
  }

  /// Compute actual FPS from video metadata (same approach as VideoPlayerWidget)
  double _getActualFps() {
    final metadata = widget.mediaItem.technicalMetadata;
    if (metadata == null) return 30.0;

    final nested = metadata['video'];
    final videoMeta = nested is Map<String, dynamic> ? nested : metadata;

    final totalFrames = (videoMeta['total_frames'] as num?)?.toInt() ??
        (metadata['total_frames'] as num?)?.toInt();
    final durationSec = (videoMeta['duration_seconds'] as num?)?.toDouble() ??
        (metadata['duration_seconds'] as num?)?.toDouble() ??
        widget.mediaItem.duration?.toDouble();

    if (totalFrames != null && totalFrames > 0 && durationSec != null && durationSec > 0) {
      return totalFrames / durationSec;
    }

    final frameRate = (videoMeta['frame_rate'] as num?)?.toDouble() ??
        (videoMeta['fps'] as num?)?.toDouble() ??
        (metadata['frame_rate'] as num?)?.toDouble() ??
        (metadata['fps'] as num?)?.toDouble();
    return frameRate ?? 30.0;
  }

  /// Convert video position to frame number using actual FPS from metadata
  int _positionToFrameNumber(Duration position) {
    return (position.inMilliseconds / 1000 * _getActualFps()).floor();
  }

  /// Check if two face lists are equal
  bool _facesAreEqual(List<FaceDetection> a, List<FaceDetection> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i].boundingBox.left != b[i].boundingBox.left || 
          a[i].boundingBox.top != b[i].boundingBox.top || 
          a[i].boundingBox.width != b[i].boundingBox.width || 
          a[i].boundingBox.height != b[i].boundingBox.height) {
        return false;
      }
    }
    return true;
  }

  @override
  void dispose() {
    // VideoPlayerWidget owns the controller lifecycle; only detach our listener.
    _videoController?.removeListener(_onVideoFrameChanged);
    _videoController = null;

    debugPrint('ACTIVE OVERLAY PATH: SMART_WIDGET_DISPOSE_PRESERVE_CACHE for ${widget.mediaItem.uuid}');
    debugPrint('DISPOSE: Preserving face caches for ${widget.mediaItem.uuid} to avoid preview reload races');
    
    // Clear stored face data
    _storedFaceData?.clear();
    _storedFaceData = null;
    
    super.dispose();
  }

  /// Initialize smart playback by determining optimal playback mode
  Future<void> _initializeSmartPlayback() async {
    if (!mounted) return;
    
    setState(() {
      _isLoadingWorkflowData = true;
      _workflowError = null;
    });

    try {
      // Load processing status
      final processingStatusAsync = ref.read(processingStatusProvider(widget.mediaItem.uuid));
      await processingStatusAsync.when(
        data: (status) async {
          _processingStatus = status as ProcessingStatus?;
          // Determine optimal playback mode
          await _determinePlaybackMode();
        },
        loading: () async {
          // Use fallback mode while loading
          _setFallbackPlaybackMode();
        },
        error: (error, stack) async {
          throw error;
        },
      );

      // Load stored face data if using optimized mode
      if ((widget.initialFaceData == null || widget.initialFaceData!.isEmpty) &&
          _currentPlaybackMode?.mode == 'stored_data' &&
          _processingStatus?.faceDetectionProcessed == true) {
        await _loadStoredFaceData();
      }

    } catch (e) {
      debugPrint('⚠️ Smart playback initialization error (workflow APIs unavailable): $e');
      debugPrint('🔄 Falling back to smart realtime mode (overlay stays enabled)');

      // Keep smart player active even if workflow APIs are down
      _setFallbackPlaybackMode();

      if (mounted) {
        setState(() {
          _workflowError = null;
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingWorkflowData = false;
        });
      }
    }
  }

  /// Determine optimal playback mode based on processing status
  Future<void> _determinePlaybackMode() async {
    try {
      final playbackModeAsync = ref.read(optimalPlaybackModeProvider(widget.mediaItem.uuid));
      await playbackModeAsync.when(
        data: (mode) async {
          _currentPlaybackMode = mode as PlaybackMode?;
        },
        loading: () async {
          _setFallbackPlaybackMode();
        },
        error: (error, stack) async {
          throw error;
        },
      );
    } catch (e) {
      debugPrint('Failed to get optimal playback mode, using fallback: $e');
      _setFallbackPlaybackMode();
    }
  }

  /// Set fallback playback mode when workflow APIs are unavailable
  void _setFallbackPlaybackMode() {
    _currentPlaybackMode = const PlaybackMode(
      mode: 'realtime_only',
      description: 'Real-time face detection (fallback mode)',
      cpuOptimized: false,
      expectedCpuReduction: null,
    );
  }

  /// Load stored face detection data for optimized playback
  Future<void> _loadStoredFaceData() async {
    try {
      debugPrint('_loadStoredFaceData() called - ensuring MediaFaceDataProvider data is loaded...');
      if (!mounted) {
        return;
      }
      
      // 🔧 LOADING FIX: Wait for MediaFaceDataProvider to load data instead of just reading current state
      // 🔥 CACHE FIX: Force refresh to bypass old cached data (5 representative faces) and fetch all faces
      final notifier = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid).notifier);
      await notifier.loadFaces(forceRefresh: true);  // Force refresh to get updated faces_by_frame data

      if (!mounted) {
        return;
      }
      
      // Wait for the provider to have data (with timeout)
      var attempts = 0;
      const maxAttempts = 20; // 10 seconds total (500ms * 20)
      
      while (attempts < maxAttempts) {
        if (!mounted) {
          return;
        }

        final faceDataState = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid));
        
        debugPrint('LOADING ATTEMPT $attempts: hasData=${faceDataState.hasData}, isLoading=${faceDataState.isLoading}, hasError=${faceDataState.hasError}, faces=${faceDataState.hasData ? faceDataState.faces.length : 0}');
        
        if (faceDataState.hasData && faceDataState.faces.isNotEmpty) {
          // Successfully loaded face data
          _storedFaceData = faceDataState.faces;
          _faceDataSource = 'MediaFaceDataProvider_Cache';
          
          // Ensure frame-based sync data is available even when data came from provider cache path
          final generatedFrameMap = _buildFrameMapFromFaces(faceDataState.faces);
          if (generatedFrameMap.isNotEmpty) {
            _facesByFrame = generatedFrameMap;
            debugPrint('📦 FRAME CACHE READY: Generated ${generatedFrameMap.keys.length} frames from provider face metadata');
            debugPrint('🧪 OVERLAY DEBUG: media=${widget.mediaItem.uuid}, provider_faces=${faceDataState.faces.length}, generated_frames=${generatedFrameMap.keys.length}');
          }
          
          debugPrint('✅ LOADING SUCCESS: Loaded ${_storedFaceData?.length ?? 0} faces from MediaFaceDataProvider after $attempts attempts');
          return;
        }
        
        if (faceDataState.hasError) {
          debugPrint('❌ MediaFaceDataProvider error: ${faceDataState.error}');
          break;
        }
        
        // Wait before next attempt
        await Future.delayed(const Duration(milliseconds: 500));
        attempts++;
      }
      
      throw Exception(
        'MediaFaceDataProvider did not return full Enhanced V2 per-frame detections within ${maxAttempts * 500}ms; refusing fallback data source',
      );
    } catch (e) {
      debugPrint('Failed to load stored face data: $e');
      _storedFaceData = null;
      _faceDataSource = 'error';
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingWorkflowData) {
      return _buildLoadingIndicator();
    }

    if (_workflowError != null) {
      return _buildErrorFallback();
    }

    return _buildSmartVideoPlayer();
  }

  /// Build loading indicator while initializing smart playback
  Widget _buildLoadingIndicator() {
    return Container(
      color: Colors.black,
      child: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
            ),
            SizedBox(height: 16),
            Text(
              'Initializing smart playback...',
              style: TextStyle(color: Colors.white),
            ),
          ],
        ),
      ),
    );
  }

  /// Build error fallback with basic video player
  Widget _buildErrorFallback() {
    return Column(
      children: [
        // Error banner
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(8),
          color: Colors.orange[700],
          child: Row(
            children: [
              const Icon(Icons.warning, color: Colors.white, size: 16),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Smart playback unavailable - using basic mode',
                  style: TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
              TextButton(
                onPressed: _initializeSmartPlayback,
                child: const Text(
                  'Retry',
                  style: TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ),
        ),
        // Basic video player
        Expanded(child: _buildBasicVideoPlayer()),
      ],
    );
  }

  /// Build smart video player with workflow-optimized features
  Widget _buildSmartVideoPlayer() {
    final videoUrl = _buildOptimalVideoUrl();
    
    // 🎯 ARCHITECTURAL FIX: MediaFaceDataProvider should NOT be used for video overlays
    // It flattens frame-based data into a continuous list, causing inappropriate real-time display
    // MediaFaceDataProvider is for counts/statistics only, NOT for frame-synchronized video overlays
    
    debugPrint('=== FACE OVERLAY ARCHITECTURE FIX ===');
    debugPrint('mediaItem.uuid: ${widget.mediaItem.uuid}');
    debugPrint('_storedFaceData: ${_storedFaceData?.length ?? "null"}');
    debugPrint('_faceDataSource: $_faceDataSource');
    debugPrint('=====================================');
    
    // 🔧 CORRECTED LOGIC: Only use frame-based stored face data for overlays
    // MediaFaceDataProvider is excluded from overlay logic to prevent continuous display
    List<FaceDetection> facesToDisplay = [];
    String dataSource = 'none';
    bool hasStoredFaceData = _storedFaceData != null && _storedFaceData!.isNotEmpty;
    
    // Only use stored face data that preserves frame timing
    if (hasStoredFaceData) {
      facesToDisplay = _storedFaceData!;
      dataSource = _faceDataSource;
      debugPrint('FRAME-SYNCHRONIZED RECTANGLES: ${facesToDisplay.length} faces from $_faceDataSource');
    } else {
      // 🔧 GLOBAL CACHE CHECK: Check if data is available in global cache from previous overlay loading
      try {
        final globalManager = FaceDataMemoryManager.instance;
        final mediaId = widget.mediaItem.uuid;
        
        if (globalManager.hasFaceData(mediaId)) {
          final globalStoredFaces = globalManager.getStoredFaces(mediaId);
          if (globalStoredFaces != null && globalStoredFaces.isNotEmpty) {
            // Convert stored faces map to flat list for overlay display
            final List<FaceDetection> globalFacesList = [];
            globalStoredFaces.forEach((frameKey, faces) {
              globalFacesList.addAll(faces);
            });
            
            if (globalFacesList.isNotEmpty) {
              facesToDisplay = globalFacesList;
              dataSource = 'global_cache';
              debugPrint('GLOBAL CACHE HIT: Using ${globalFacesList.length} faces from global cache for GREEN rectangles');
            }
          }
        }
        
        if (facesToDisplay.isEmpty) {
          debugPrint('NO FRAME DATA: No stored face data available for frame synchronization');
        }
      } catch (e) {
        debugPrint('GLOBAL CACHE ERROR: Failed to check global cache: $e');
        debugPrint('NO FRAME DATA: No stored face data available for frame synchronization');
      }
    }
    
    // Use overlay only if we have frame-synchronized data
    final useStoredFaceData = facesToDisplay.isNotEmpty;

    debugPrint('OVERLAY DEBUG: useStoredFaceData=$useStoredFaceData, facesToDisplay.length=${facesToDisplay.length}, dataSource=$dataSource');

    return Stack(
      children: [
        // Video player with smart overlay
        _buildVideoPlayerWithOverlay(videoUrl, useStoredFaceData, facesToDisplay, dataSource),
        
        // Playback mode indicator
        _buildPlaybackModeIndicator(),
        
        // Performance indicator
        if (_currentPlaybackMode?.cpuOptimized == true)
          _buildPerformanceIndicator(),
      ],
    );
  }

  /// Build video player with appropriate overlay strategy
  Widget _buildVideoPlayerWithOverlay(String videoUrl, bool useStoredFaceData, List<FaceDetection> facesToDisplay, String dataSource) {
    // [FIX] ALWAYS use OptimizedFacePainter to prevent SimpleFaceDetectionOverlay cache issues
    // The old logic switched between paths based on cache state, causing inconsistent rendering
    // Now we ALWAYS use OptimizedFacePainter (multicolor GREEN rectangles)
    // If no faces available yet, we'll make the API call first
    
    if (facesToDisplay.isEmpty) {
      final hasExternalFaceData =
          widget.initialFaceData != null && widget.initialFaceData!.isNotEmpty;
      if (hasExternalFaceData) {
        return _buildBasicVideoPlayerForLoading(videoUrl);
      }
      if (!widget.enableWorkflowIntegration) {
        if (!_isLoadingStoredFaces && _storedFaceData?.isNotEmpty != true) {
          debugPrint('[OVERLAY STRATEGY] No stored faces yet in preview flow; starting direct stored-face load');
          _startPreviewStoredFaceLoad();
        } else {
          debugPrint('[OVERLAY STRATEGY] No stored faces yet in preview flow; waiting for direct stored-face load');
        }
        return _buildBasicVideoPlayerForLoading(videoUrl);
      }
      // No faces in cache yet - need to load them first
      debugPrint('[OVERLAY STRATEGY] No faces available, loading via Enhanced Logic V2...');
      _loadFacesViaEnhancedLogicV2();
      // Show video player without overlay while loading
      return _buildBasicVideoPlayerForLoading(videoUrl);
    }
    
    // We have faces - delegate to the simpler frame-based overlay path.
    debugPrint('ACTIVE OVERLAY PATH: SMART_WIDGET -> OPTIMIZED_FACE_DATA_OVERLAY with ${facesToDisplay.length} faces from $dataSource');
    return _buildOptimizedVideoPlayer(videoUrl, facesToDisplay, dataSource);
  }

  /// Build optimized video player for Workflow 5 (stored face data)
  Widget _buildOptimizedVideoPlayer(String videoUrl, List<FaceDetection> facesToDisplay, String dataSource) {
    return Stack(
      children: [
        VideoPlayerWidget(
          videoUrl: videoUrl,
          headers: widget.headers,
          collectionId: widget.collectionId,
          technicalMetadata: widget.mediaItem.technicalMetadata,
          videoDuration: widget.mediaItem.duration,
          onControllerReady: (controller) {
            _videoController = controller;
            if (controller != null) {
              widget.onControllerReady?.call(controller);
              // Set up frame synchronization for face rectangles
              _setupFaceFrameSync(facesToDisplay, dataSource);
            }
          },
        ),
        if (_videoController != null)
          OptimizedFaceDataOverlay(
            videoController: _videoController,
            storedFaceData: facesToDisplay,
            dataSource: dataSource,
            mediaItem: widget.mediaItem,
          ),
      ],
    );
  }

  /// Build session-based video player for Workflow 4
  Widget _buildSessionBasedVideoPlayer(String videoUrl) {
    // For realtime modes, enable face detection overlay since we're using Media Service URL
    final enableOverlay = _currentPlaybackMode?.mode == 'realtime_with_session' || 
                         _currentPlaybackMode?.mode == 'realtime_only';
    
    return SimpleFaceDetectionOverlay(
      videoController: _videoController, // Will be null initially, updated when controller is ready
      videoUrl: videoUrl,
      enabled: enableOverlay,
      useEmbeddedFaceDetection: false, // Use overlay system, not embedded
      actualFps: _getActualFps(),
      child: VideoPlayerWidget(
        videoUrl: videoUrl,
        headers: widget.headers,
        collectionId: widget.collectionId,
        technicalMetadata: widget.mediaItem.technicalMetadata, // Pass metadata for speed correction
        videoDuration: widget.mediaItem.duration, // Pass duration for speed correction
        onControllerReady: (controller) {
          debugPrint('🔧 CONTROLLER READY: About to call setState to trigger overlay rebuild');
          setState(() {
            _videoController = controller; // This will trigger a rebuild with the controller
          });
          if (controller != null) {
            debugPrint('🔧 CONTROLLER FIX: Video controller ready, rebuilding overlay with controller');
            debugPrint('🔧 CONTROLLER FIX: setState completed, overlay should now have controller');
            widget.onControllerReady?.call(controller);
          }
        },
      ),
    );
  }

  /// Build basic video player for fallback
  Widget _buildBasicVideoPlayer() {
    final basicVideoUrl = '/api/v1/media/stream/${widget.mediaItem.uuid}';
    
    return VideoPlayerWidget(
      videoUrl: basicVideoUrl,
      headers: widget.headers,
      collectionId: widget.collectionId,
      technicalMetadata: widget.mediaItem.technicalMetadata, // Pass metadata for speed correction
      videoDuration: widget.mediaItem.duration, // Pass duration for speed correction
      onControllerReady: (controller) {
        _videoController = controller;
        if (controller != null) {
          widget.onControllerReady?.call(controller);
        }
      },
    );
  }

  /// Build basic video player while faces are loading
  Widget _buildBasicVideoPlayerForLoading(String videoUrl) {
    return VideoPlayerWidget(
      videoUrl: videoUrl,
      headers: widget.headers,
      collectionId: widget.collectionId,
      technicalMetadata: widget.mediaItem.technicalMetadata,
      videoDuration: widget.mediaItem.duration,
      onControllerReady: (controller) {
        _videoController = controller;
        if (controller != null) {
          widget.onControllerReady?.call(controller);
        }
      },
    );
  }

  /// Load faces via Enhanced Logic V2 API and update state
  Future<void> _loadFacesViaEnhancedLogicV2() async {
    if (_isLoadingFaces) {
      debugPrint('[LOAD FACES] Already loading, skipping duplicate call');
      return;
    }

    if (_faceLoadAttempts >= _maxFaceLoadAttempts) {
      debugPrint('[LOAD FACES] Retry limit reached ($_faceLoadAttempts/$_maxFaceLoadAttempts) for ${widget.mediaItem.uuid}');
      return;
    }

    if (_lastFaceLoadAttemptAt != null &&
        DateTime.now().difference(_lastFaceLoadAttemptAt!) < _faceLoadRetryCooldown) {
      debugPrint('[LOAD FACES] Cooldown active, skipping immediate retry');
      return;
    }
    
    try {
      if (mounted) {
        setState(() {
          _isLoadingFaces = true;
        });
      }
      _lastFaceLoadAttemptAt = DateTime.now();
      _faceLoadAttempts++;
      
      debugPrint('[LOAD FACES] Calling Enhanced Logic V2 for ${widget.mediaItem.uuid}');

      final orchestratorClient = ref.read(orchestratorApiClientProvider);
      final response = await orchestratorClient.getEnhancedLogicV2Response(widget.mediaItem.uuid);

      if (response.isSuccess && response.data != null) {
        final enhancedData = response.data!;
        if (enhancedData.faces.isEmpty) {
          debugPrint('[LOAD FACES] ⚠️ Enhanced Logic V2 returned success but faces list is empty for ${widget.mediaItem.uuid}');
        }
        
        debugPrint('[LOAD FACES] 📊 Enhanced Logic V2 Response:');
        debugPrint('[LOAD FACES]    Total faces: ${enhancedData.totalFaces}');
        debugPrint('[LOAD FACES]    Faces array length: ${enhancedData.faces.length} (representative faces only)');
        debugPrint('[LOAD FACES]    Source: ${enhancedData.source}');
        
        // 🔥 CRITICAL FIX: Use detection_result.faces_by_frame to get ALL 72 faces!
        // - enhancedData.facesByFrame only has 5 representative frames (690, 700, 710, 720, 730)
        // - enhancedData.detectionResult['faces_by_frame'] has ALL 72 faces across all frames
        Map<String, dynamic>? allFacesByFrame;
        
        if (enhancedData.detectionResult != null && 
            enhancedData.detectionResult!.containsKey('faces_by_frame')) {
          allFacesByFrame = enhancedData.detectionResult!['faces_by_frame'] as Map<String, dynamic>;
          debugPrint('[LOAD FACES] 🎯 Using detection_result.faces_by_frame with ${allFacesByFrame.keys.length} frames (ALL faces)');
        } else {
          // Fallback to top-level faces_by_frame (only representative faces)
          debugPrint('[LOAD FACES] ⚠️ detection_result not available, falling back to representative faces_by_frame');
          allFacesByFrame = {};
          for (final entry in enhancedData.facesByFrame.entries) {
            allFacesByFrame[entry.key] = entry.value.map((f) => {
              'bbox': f.bbox,
              'confidence': f.confidence,
              'method': f.method,
            }).toList();
          }
        }
        
        debugPrint('[LOAD FACES] 🔥 Processing ${allFacesByFrame.keys.length} frames from faces_by_frame');
        
        // Flatten faces_by_frame into a single list of ALL faces
        final List<FaceDetection> faces = [];
        for (final entry in allFacesByFrame.entries) {
          final facesList = entry.value as List<dynamic>;
          for (final faceData in facesList) {
            final Map<String, dynamic> faceMap = faceData is Map<String, dynamic> 
                ? faceData 
                : {
                    'bbox': (faceData as dynamic).bbox,
                    'confidence': (faceData as dynamic).confidence,
                    'method': (faceData as dynamic).method,
                  };
            
            final bbox = faceMap['bbox'] as List<dynamic>;
            faces.add(FaceDetection(
              boundingBox: FaceBoundingBox(
                left: (bbox[0] as num).toDouble(),
                top: (bbox[1] as num).toDouble(),
                width: (bbox[2] as num).toDouble() - (bbox[0] as num).toDouble(),
                height: (bbox[3] as num).toDouble() - (bbox[1] as num).toDouble(),
              ),
              confidence: (faceMap['confidence'] as num?)?.toDouble() ?? 0.9,
              method: faceMap['method'] as String? ?? 'unknown',
            ));
          }
        }
        
        debugPrint('[LOAD FACES] ✅ Converted ${faces.length} faces from faces_by_frame (ALL detections)');

        if (faces.isEmpty) {
          debugPrint('[LOAD FACES] ⚠️ Enhanced payload has no usable faces_by_frame detections');
        }
        
        // Store in global cache
        // Convert to frame-based structure for memory cache using ALL faces_by_frame data
        final globalManager = FaceDataMemoryManager.instance;
        final memoryCache = <int, List<FaceDetection>>{};
        final storedFacesByFrame = <String, List<FaceDetection>>{};
        
        // Use ALL faces_by_frame data for frame-based cache
        for (final entry in allFacesByFrame.entries) {
          final frameNum = int.parse(entry.key);
          final frameKey = 'frame_$frameNum';
          final frameFaces = <FaceDetection>[];
          final facesList = entry.value as List<dynamic>;
          
          for (final faceData in facesList) {
            final Map<String, dynamic> faceMap = faceData is Map<String, dynamic> 
                ? faceData 
                : {
                    'bbox': (faceData as dynamic).bbox,
                    'confidence': (faceData as dynamic).confidence,
                    'method': (faceData as dynamic).method,
                  };
            
            final bbox = faceMap['bbox'] as List<dynamic>;
            final faceDetection = FaceDetection(
              boundingBox: FaceBoundingBox(
                left: (bbox[0] as num).toDouble(),
                top: (bbox[1] as num).toDouble(),
                width: (bbox[2] as num).toDouble() - (bbox[0] as num).toDouble(),
                height: (bbox[3] as num).toDouble() - (bbox[1] as num).toDouble(),
              ),
              confidence: (faceMap['confidence'] as num?)?.toDouble() ?? 0.9,
              method: faceMap['method'] as String? ?? 'unknown',
            );
            
            frameFaces.add(faceDetection);
          }
          
          memoryCache[frameNum] = frameFaces;
          storedFacesByFrame[frameKey] = frameFaces;
        }
        
        globalManager.storeFaceData(widget.mediaItem.uuid, memoryCache, storedFacesByFrame);
        debugPrint('[LOAD FACES] 📦 Stored ${memoryCache.keys.length} frames in global cache');
        
        if (mounted) {
          setState(() {
            _storedFaceData = faces;
            _faceDataSource = 'enhanced_logic_v2_api';
            _isLoadingFaces = false;
          });
        }
        
        if (faces.isNotEmpty) {
          _faceLoadAttempts = 0;
        }

        debugPrint('[LOAD FACES] ✅ Loaded ${faces.length} faces from Enhanced Logic V2');
      } else {
        debugPrint('[LOAD FACES] ❌ Enhanced Logic V2 request failed: ${response.error?.message}');
        if (mounted) {
          setState(() {
            _isLoadingFaces = false;
          });
        }
      }
    } catch (e) {
      debugPrint('[LOAD FACES] ❌ Error loading faces for ${widget.mediaItem.uuid}: $e');
      if (mounted) {
        setState(() {
          _isLoadingFaces = false;
        });
      }
    }
  }

  /// Build optimal video URL based on playback mode
  String _buildOptimalVideoUrl() {
    String url;
    
    if (_currentPlaybackMode == null) {
      // Default to Media Service streaming for better compatibility
      url = '/api/v1/media/stream/${widget.mediaItem.uuid}';
      debugPrint('🎯 SmartVideoPlayer: Using default Media Service URL: $url');
      return url;
    }

    switch (_currentPlaybackMode!.mode) {
      case 'stored_data':
        // Workflow 5: Use Media Service direct streaming (no live face detection)
        // Face data will come from stored detections in database
        url = '/api/v1/media/stream/${widget.mediaItem.uuid}';
        debugPrint('🎯 SmartVideoPlayer: Using stored_data Media Service URL: $url');
        break;
      
      case 'realtime_with_session':
        // Workflow 4: Use Media Service for video WITHOUT face detection + overlay for face detection (Flutter compatibility)
        url = '/api/v1/media/stream/${widget.mediaItem.uuid}?face_detection=false';
        debugPrint('🎯 SmartVideoPlayer: Using realtime_with_session Media Service URL with overlay (clean video): $url');
        break;
      
      case 'realtime_only':
      default:
        // Basic real-time: Use Media Service for video WITHOUT face detection + overlay for face detection (Flutter compatibility)
        // Disable embedded yellow rectangles so we can use green Enhanced Logic V2 overlay
        url = '/api/v1/media/stream/${widget.mediaItem.uuid}?face_detection=false';
        debugPrint('🎯 SmartVideoPlayer: Using realtime_only Media Service URL with overlay (clean video): $url');
        break;
    }
    
    return url;
  }

  /// Build details indicator
  Widget _buildPlaybackModeIndicator() {
    if (widget.onDetailsPressed == null) {
      return const SizedBox.shrink();
    }

    return Positioned(
      top: 16,
      left: 16,
      child: GestureDetector(
        onTap: widget.onDetailsPressed,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.blue[700]!.withValues(alpha: 0.9),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.info_outline,
                size: 14,
                color: Colors.white,
              ),
              const SizedBox(width: 4),
              Text(
                'Details',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Build performance indicator for optimized playback
  Widget _buildPerformanceIndicator() {
    final cpuReduction = _currentPlaybackMode?.expectedCpuReduction ?? 0.9;
    
    return Positioned(
      top: 56, // Below playback mode indicator
      left: 16,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.green[600]!.withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.trending_down,
              size: 14,
              color: Colors.white,
            ),
            const SizedBox(width: 4),
            Text(
              '${(cpuReduction * 100).toStringAsFixed(0)}% CPU ↓',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Get playback mode color
  Color _getPlaybackModeColor() {
    switch (_currentPlaybackMode?.mode) {
      case 'stored_data':
        return Colors.blue[700]!;
      case 'realtime_with_session':
        return Colors.purple[700]!;
      case 'realtime_only':
      default:
        return Colors.grey[700]!;
    }
  }

  /// Get playback mode icon
  IconData _getPlaybackModeIcon() {
    switch (_currentPlaybackMode?.mode) {
      case 'stored_data':
        return Icons.flash_on;
      case 'realtime_with_session':
        return Icons.play_circle;
      case 'realtime_only':
      default:
        return Icons.memory;
    }
  }

  /// Get playback mode display name
  String _getPlaybackModeDisplayName() {
    switch (_currentPlaybackMode?.mode) {
      case 'stored_data':
        return 'Optimized';
      case 'realtime_with_session':
        return 'Session';
      case 'realtime_only':
        return 'Real-time';
      default:
        return 'Unknown';
    }
  }
}

/// Optimized Face Data Overlay for Workflow 5
/// Uses pre-processed face detection data for high-performance playback
class OptimizedFaceDataOverlay extends StatefulWidget {
  final VideoPlayerController? videoController;
  final List<FaceDetection> storedFaceData;
  final String dataSource;
  final MediaItem mediaItem;

  const OptimizedFaceDataOverlay({
    super.key,
    this.videoController,
    required this.storedFaceData,
    required this.dataSource,
    required this.mediaItem,
  });

  @override
  State<OptimizedFaceDataOverlay> createState() => _OptimizedFaceDataOverlayState();
}

class _OptimizedFaceDataOverlayState extends State<OptimizedFaceDataOverlay> {
  List<FaceDetection> _currentFrameFaces = [];
  Map<int, List<FaceDetection>>? _facesByFrame;
  final Map<FaceDetection, int> _faceFirstSeenFrame = {}; // Track when each face first appeared
  int _lastFrameNumber = -1; // Track last processed frame to prevent showing faces before video starts
  bool _hasPlaybackStarted = false; // Track if playback has ever started

  /// Compute actual FPS from video metadata
  double _getActualFpsForOverlay() {
    final metadata = widget.mediaItem.technicalMetadata;
    if (metadata == null) return 30.0;

    final nested = metadata['video'];
    final videoMeta = nested is Map<String, dynamic> ? nested : metadata;

    final totalFrames = (videoMeta['total_frames'] as num?)?.toInt() ??
        (metadata['total_frames'] as num?)?.toInt();
    final durationSec = (videoMeta['duration_seconds'] as num?)?.toDouble() ??
        (metadata['duration_seconds'] as num?)?.toDouble() ??
        widget.mediaItem.duration?.toDouble();

    if (totalFrames != null && totalFrames > 0 && durationSec != null && durationSec > 0) {
      return totalFrames / durationSec;
    }

    final frameRate = (videoMeta['frame_rate'] as num?)?.toDouble() ??
        (videoMeta['fps'] as num?)?.toDouble() ??
        (metadata['frame_rate'] as num?)?.toDouble() ??
        (metadata['fps'] as num?)?.toDouble();
    return frameRate ?? 30.0;
  }

  @override
  void initState() {
    super.initState();
    debugPrint('=== OVERLAY INIT DEBUG ===');
    debugPrint('OptimizedFaceDataOverlay INITIALIZED');
    debugPrint('storedFaceData.length: ${widget.storedFaceData.length}');
    debugPrint('dataSource: ${widget.dataSource}');
    debugPrint('mediaItem.uuid: ${widget.mediaItem.uuid}');
    debugPrint('=========================');
    
    if (widget.dataSource == 'MediaFaceDataProvider_Cache') {
      debugPrint('VERIFICATION CONFIRMED: GREEN rectangles using MEMORY CACHE (not embedded endpoint)');
    } else {
      debugPrint('VERIFICATION WARNING: YELLOW rectangles using FALLBACK source: ${widget.dataSource}');
    }
    
    // Load frame-based face data from global cache
    _loadFrameBasedFaceData();
    _setupVideoListener();
  }

  @override
  void didUpdateWidget(OptimizedFaceDataOverlay oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Rebuild frame map when storedFaceData arrives/changes after initial mount.
    // The overlay is often first mounted with empty storedFaceData (controller ready
    // before face data load completes), so we must rebuild the tracking map when
    // faces become available; otherwise _facesByFrame stays empty and painter draws nothing.
    final oldLen = oldWidget.storedFaceData.length;
    final newLen = widget.storedFaceData.length;
    final identityChanged = !identical(oldWidget.storedFaceData, widget.storedFaceData);
    if (oldLen != newLen || identityChanged) {
      debugPrint('🔄 OptimizedFaceDataOverlay.didUpdateWidget: storedFaceData $oldLen -> $newLen, rebuilding frame map');
      _faceFirstSeenFrame.clear();
      _currentFrameFaces = const [];
      _loadFrameBasedFaceData();
    }
    // If the underlying video controller instance changes, re-attach listener.
    if (oldWidget.videoController != widget.videoController) {
      oldWidget.videoController?.removeListener(_onVideoPositionChanged);
      _setupVideoListener();
    }
  }

  /// Load frame-based face data: prefer the per-frame map carried by widget.storedFaceData,
  /// fall back to the global cache only as a secondary source.
  void _loadFrameBasedFaceData() {
    final fromStored = _buildFrameMapFromStoredFaces(widget.storedFaceData);

    if (fromStored.isNotEmpty) {
      _facesByFrame = fromStored;
      final keys = _facesByFrame!.keys.toList()..sort();
      debugPrint('📦 FRAME DATA LOADED (from storedFaceData): ${keys.length} frames, '
          'range ${keys.first}-${keys.last}, total faces=${widget.storedFaceData.length}');
      return;
    }

    final globalManager = FaceDataMemoryManager.instance;
    _facesByFrame = globalManager.getMemoryCache(widget.mediaItem.uuid);

    if (_facesByFrame != null && _facesByFrame!.isNotEmpty) {
      final keys = _facesByFrame!.keys.toList()..sort();
      debugPrint('📦 FRAME DATA LOADED (from global cache): ${keys.length} frames, '
          'range ${keys.first}-${keys.last}');
    } else {
      debugPrint('⚠️ NO FRAME DATA: storedFaceData has ${widget.storedFaceData.length} faces '
          'but no per-frame metadata, and global cache is empty for ${widget.mediaItem.uuid}');
    }
  }

  /// Build a frame_number -> List<FaceDetection> map from a flat list using
  /// metadata['frame_number'] / metadata['frame'] as written by MediaFaceDataNotifier.
  Map<int, List<FaceDetection>> _buildFrameMapFromStoredFaces(List<FaceDetection> faces) {
    final Map<int, List<FaceDetection>> frameMap = {};
    for (final face in faces) {
      final metadata = face.metadata;
      if (metadata == null) continue;

      final dynamic raw = metadata['frame_number'] ?? metadata['frame'] ?? metadata['frameNumber'];
      int? frameNumber;
      if (raw is int) {
        frameNumber = raw;
      } else if (raw is num) {
        frameNumber = raw.toInt();
      } else if (raw is String) {
        frameNumber = int.tryParse(raw);
      }
      if (frameNumber == null || frameNumber < 0) continue;

      frameMap.putIfAbsent(frameNumber, () => <FaceDetection>[]).add(face);
    }
    return frameMap;
  }

  /// Setup video controller listener for frame-based face data display
  void _setupVideoListener() {
    widget.videoController?.addListener(_onVideoPositionChanged);
  }

  /// Handle video position changes to show appropriate face data
  /// Faces are displayed for 10 frames (0.33 seconds at 30fps) from when they first appear
  void _onVideoPositionChanged() {
    final controller = widget.videoController;
    if (!mounted || controller == null || !controller.value.isInitialized) return;

    // Track when playback actually starts (position moves from 0 or video is playing)
    if (controller.value.isPlaying && controller.value.position.inMilliseconds > 0) {
      _hasPlaybackStarted = true;
    }

    // Don't show any faces until video has actually started playing
    // This prevents faces from showing during initial load/pause at frame 0
    if (!_hasPlaybackStarted) {
      if (_currentFrameFaces.isNotEmpty || _faceFirstSeenFrame.isNotEmpty) {
        if (mounted) {
          setState(() {
            _currentFrameFaces = [];
            _faceFirstSeenFrame.clear();
          });
        }
        debugPrint('🚫 Playback not started - clearing faces');
      }
      return;
    }

    final currentPosition = controller.value.position;
    final fps = _getActualFpsForOverlay();

    // Calculate current frame number from elapsed time (NOT from a duration ratio,
    // which truncates because duration.inSeconds is integer-rounded and breaks the scale).
    final currentFrameNumber = (currentPosition.inMilliseconds / 1000.0 * fps).floor();

    _lastFrameNumber = currentFrameNumber;

    // Collect faces that should be visible:
    // 1. Faces detected in current frame (add to tracking)
    // 2. Faces from previous frames still within the display window
    List<FaceDetection> visibleFaces = [];

    // Display window scaled to actual FPS (~0.5s, matching USB camera timers).
    final displayWindowFrames = (0.5 * fps).ceil().clamp(1, 30);

    if (_facesByFrame != null) {
      // Faces are stored at sparse frame keys (e.g. every ~10 frames from Enhanced V2 vision).
      // Use a frame-range tolerance so the playhead doesn't have to land on the exact stored
      // key for a face to register. Tolerance scales with FPS and matches the parent overlay.
      final frameTolerance = (fps / 6).ceil().clamp(2, 10);
      for (int checkFrame = currentFrameNumber - frameTolerance;
           checkFrame <= currentFrameNumber + frameTolerance;
           checkFrame++) {
        final framesAtKey = _facesByFrame![checkFrame];
        if (framesAtKey == null) continue;
        for (final face in framesAtKey) {
          // Record when this face was first seen (anchor on the actual detection frame so
          // the display-window logic measures real on-screen lifetime).
          if (!_faceFirstSeenFrame.containsKey(face)) {
            _faceFirstSeenFrame[face] = checkFrame;
            debugPrint('🆕 NEW FACE picked up: detection frame=$checkFrame, playhead frame=$currentFrameNumber');
          }
        }
      }
      
      // Collect all faces that should still be visible (within ~0.5s window)
      final facesToRemove = <FaceDetection>[];
      _faceFirstSeenFrame.forEach((face, firstSeenFrame) {
        final framesSinceFirstSeen = currentFrameNumber - firstSeenFrame;
        if (framesSinceFirstSeen >= 0 && framesSinceFirstSeen < displayWindowFrames) {
          // Face is within display window
          visibleFaces.add(face);
        } else if (framesSinceFirstSeen >= displayWindowFrames) {
          // Face has exceeded display window, mark for removal
          facesToRemove.add(face);
        }
      });
      
      // Clean up expired faces from tracking
      for (final face in facesToRemove) {
        _faceFirstSeenFrame.remove(face);
      }
      
      debugPrint('🎯 FRAME $currentFrameNumber: Showing ${visibleFaces.length} faces (tracking ${_faceFirstSeenFrame.length} active)');
    }

    if (!_listsEqual(_currentFrameFaces, visibleFaces)) {
      setState(() {
        _currentFrameFaces = visibleFaces;
      });
    }
  }

  /// Convert video position to frame number using actual FPS from metadata
  int _positionToFrameNumber(Duration position) {
    return (position.inMilliseconds / 1000 * _getActualFpsForOverlay()).floor();
  }

  /// Check if two lists of faces are equal
  bool _listsEqual(List<FaceDetection> a, List<FaceDetection> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i].boundingBox.left != b[i].boundingBox.left || 
          a[i].boundingBox.top != b[i].boundingBox.top || 
          a[i].boundingBox.width != b[i].boundingBox.width || 
          a[i].boundingBox.height != b[i].boundingBox.height) {
        return false;
      }
    }
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.videoController;
    if (controller == null || !controller.value.isInitialized) {
      return const SizedBox.shrink();
    }

    final videoSize = controller.value.size;
    
    return Positioned.fill(
      child: IgnorePointer(
        child: CustomPaint(
          painter: OptimizedFacePainter(
            faces: _currentFrameFaces,
            videoSize: videoSize,
            dataSource: widget.dataSource,
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    widget.videoController?.removeListener(_onVideoPositionChanged);
    super.dispose();
  }
}

/// Custom painter for optimized face detection rectangles
class OptimizedFacePainter extends CustomPainter {
  final List<FaceDetection> faces;
  final Size videoSize;
  final String dataSource;

  OptimizedFacePainter({
    required this.faces,
    required this.videoSize,
    required this.dataSource,
  });

  @override
  void paint(Canvas canvas, Size size) {

    final textPainter = TextPainter(
      textDirection: TextDirection.ltr,
    );

    // Calculate actual video display area within the container (WORKING LOGIC FROM YELLOW RECTANGLES)
    // This accounts for aspect ratio preservation (BoxFit.contain behavior)
    final containerAspectRatio = size.width / size.height;
    final videoAspectRatio = videoSize.width / videoSize.height;
    
    double videoDisplayWidth;
    double videoDisplayHeight;
    double offsetX = 0;
    double offsetY = 0;
    
    if (containerAspectRatio > videoAspectRatio) {
      // Container is wider than video - video will be letterboxed horizontally
      videoDisplayHeight = size.height;
      videoDisplayWidth = videoDisplayHeight * videoAspectRatio;
      offsetX = (size.width - videoDisplayWidth) / 2;
    } else {
      // Container is taller than video - video will be letterboxed vertically
      videoDisplayWidth = size.width;
      videoDisplayHeight = videoDisplayWidth / videoAspectRatio;
      offsetY = (size.height - videoDisplayHeight) / 2;
    }
    
    // Calculate scaling factors based on actual video display area
    final scaleX = videoDisplayWidth / videoSize.width;
    final scaleY = videoDisplayHeight / videoSize.height;

    for (int i = 0; i < faces.length; i++) {
      final face = faces[i];
      final bbox = face.boundingBox;
      
      // 🎯 DISTANCE-BASED COLOR CODING: Calculate distance from face area
      final faceArea = bbox.width * bbox.height;
      final distance = _calculateDistanceFromArea(faceArea);
      final distanceColor = DistanceColorService.getDistanceColor(distance);
      
      // Scale face coordinates to match actual video display area (WORKING LOGIC)
      // Convert from left,top,width,height to left,top,right,bottom for Rect.fromLTRB
      final rect = Rect.fromLTRB(
        bbox.left * scaleX + offsetX,
        bbox.top * scaleY + offsetY,
        (bbox.left + bbox.width) * scaleX + offsetX,
        (bbox.top + bbox.height) * scaleY + offsetY,
      );

      // Create paint with distance-based color at full opacity (no animations)
      final paint = Paint()
        ..color = distanceColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.0;

      // Draw rectangle with distance-based color
      canvas.drawRect(rect, paint);

      // Draw confidence and distance text with matching color
      final confidence = face.confidence;
      textPainter.text = TextSpan(
        children: [
          TextSpan(
            text: '${(confidence * 100).toInt()}%',
            style: TextStyle(
              color: distanceColor,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
          TextSpan(
            text: '\n${distance.toStringAsFixed(1)}m',
            style: TextStyle(
              color: distanceColor,
              fontSize: 10,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
        style: TextStyle(
          shadows: [
            Shadow(
              offset: const Offset(1.0, 1.0),
              blurRadius: 2.0,
              color: Colors.black.withValues(alpha: 0.8),
            ),
          ],
        ),
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(rect.left, rect.top - 35)); // Moved up to accommodate distance text
    }

    // Success message with distance-based color coding
    debugPrint('🎨 ${faces.length} distance-colored rectangles painted successfully');
  }

  /// Calculate distance from camera based on face area using PPL Meta methodology
  /// Based on the autonomous system formula: distance = (baseline_face_size / face_area) * baseline_distance
  double _calculateDistanceFromArea(double faceArea) {
    // PPL Meta standard constants (from distance_calculator.py)
    const double baselineFaceSize = 1000000.0; // 1,000,000 pixels for baseline
    const double baselineDistance = 1.0; // 1 meter baseline distance
    
    // Avoid division by zero
    if (faceArea <= 0) return 100.0; // Default far distance
    
    // Calculate distance using autonomous methodology
    final distance = (baselineFaceSize / faceArea) * baselineDistance;
    
    // Clamp to reasonable range (0.5m to 100m)
    return distance.clamp(0.5, 100.0);
  }

  @override
  bool shouldRepaint(OptimizedFacePainter oldDelegate) {
    return faces != oldDelegate.faces || 
           videoSize != oldDelegate.videoSize ||
           dataSource != oldDelegate.dataSource;
  }
}