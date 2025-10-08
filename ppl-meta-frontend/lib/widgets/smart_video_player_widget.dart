import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../models/media_models.dart';
import '../models/face_detection_models.dart';
import '../services/media_api_client.dart';
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

  const SmartVideoPlayerWidget({
    super.key,
    required this.mediaItem,
    this.headers,
    this.collectionId,
    this.onControllerReady,
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
  String? _workflowError;
  String _faceDataSource = 'none'; // Track data source for color coding
  
  // Frame synchronization for face rectangles
  List<FaceDetection> _currentSyncedFaces = [];
  List<FaceDetection> _allStoredFaces = [];
  String _currentDataSource = 'none';
  
  // EXPERIMENTAL: Smooth transitions
  static const bool _enableSmoothTransitions = true; // Set to false to revert
  Map<FaceDetection, double> _faceOpacities = {}; // Track opacity for each face
  Map<FaceDetection, int> _faceFrameCounters = {}; // Track how long face has been visible
  
  // Cache provider references for safe disposal
  late final FaceDataCache _faceDataCache;
  late final MediaFaceDataNotifier _mediaFaceDataNotifier;

  @override
  void initState() {
    super.initState();
    
    // Cache provider references for safe disposal
    _faceDataCache = ref.read(faceDataCacheProvider);
    _mediaFaceDataNotifier = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid).notifier);
    
    // Trigger face data loading if not already loaded
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        debugPrint('POST-FRAME: Triggering face data load for ${widget.mediaItem.uuid}');
        _mediaFaceDataNotifier.loadFaces();
      }
    });
    
    _initializeSmartPlayback();
  }

  /// Setup frame synchronization for face rectangles
  void _setupFaceFrameSync(List<FaceDetection> facesToDisplay, String dataSource) {
    debugPrint('🎬 FRAME SYNC: Setting up frame synchronization for ${facesToDisplay.length} faces');
    _allStoredFaces = facesToDisplay;
    _currentDataSource = dataSource;
    
    // Add video position listener for frame synchronization
    _videoController?.addListener(_onVideoFrameChanged);
    
    // Initialize with first frame faces
    _updateCurrentFrameFaces();
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
  
  /// Basic frame-based face updates (original behavior)
  void _updateFacesBasic(int currentFrameNumber, int totalFaces) {
    // Simple frame-based filtering: show different faces at different frame intervals
    final facesPerFrame = (totalFaces / 30).ceil(); // Assume 30fps, distribute faces across frames
    final startIndex = (currentFrameNumber % 30) * facesPerFrame;
    final endIndex = (startIndex + facesPerFrame).clamp(0, totalFaces);
    
    final newFrameFaces = startIndex < totalFaces 
        ? _allStoredFaces.sublist(startIndex, endIndex)
        : <FaceDetection>[];

    if (_currentSyncedFaces.length != newFrameFaces.length || 
        !_facesAreEqual(_currentSyncedFaces, newFrameFaces)) {
      setState(() {
        _currentSyncedFaces = newFrameFaces;
      });
      debugPrint('🎬 Frame ${currentFrameNumber}: ${_currentSyncedFaces.length} faces rendered');
    }
  }
  
  /// Smooth transition face updates with fade-in/fade-out
  void _updateFacesWithTransitions(int currentFrameNumber, int totalFaces) {
    const int fadeFrames = 3; // Fade over 3 frames
    const int preShowFrames = 2; // Show 2 frames early
    const int postShowFrames = 2; // Keep 2 frames after
    
    List<FaceDetection> visibleFaces = [];
    Map<FaceDetection, double> newOpacities = {};
    Map<FaceDetection, int> newCounters = Map.from(_faceFrameCounters);
    
    // Calculate which faces should be visible with transitions
    final facesPerFrame = (totalFaces / 30).ceil();
    final baseStartIndex = (currentFrameNumber % 30) * facesPerFrame;
    final baseEndIndex = (baseStartIndex + facesPerFrame).clamp(0, totalFaces);
    
    // Extended window for smooth transitions
    final extendedStartIndex = ((currentFrameNumber - preShowFrames) % 30) * facesPerFrame;
    final extendedEndIndex = ((currentFrameNumber + postShowFrames) % 30) * facesPerFrame;
    
    for (int i = 0; i < totalFaces; i++) {
      final face = _allStoredFaces[i];
      
      // Check if face is in the extended visibility window
      bool shouldShow = false;
      double opacity = 1.0;
      
      if (i >= baseStartIndex && i < baseEndIndex) {
        // Face is in main display window
        shouldShow = true;
        opacity = 1.0;
      } else {
        // Check if face should fade in or out
        final distanceFromStart = (i - baseStartIndex).abs();
        final distanceFromEnd = (i - baseEndIndex).abs();
        
        if (distanceFromStart <= preShowFrames * facesPerFrame) {
          // Fade in phase
          shouldShow = true;
          final fadeProgress = 1.0 - (distanceFromStart / (preShowFrames * facesPerFrame));
          opacity = (fadeProgress * fadeProgress).clamp(0.0, 1.0); // Ease-in curve
        } else if (distanceFromEnd <= postShowFrames * facesPerFrame) {
          // Fade out phase
          shouldShow = true;
          final fadeProgress = 1.0 - (distanceFromEnd / (postShowFrames * facesPerFrame));
          opacity = (fadeProgress * fadeProgress).clamp(0.0, 1.0); // Ease-out curve
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

  /// Convert video position to frame number (assuming 30fps)
  int _positionToFrameNumber(Duration position) {
    return (position.inMilliseconds / 1000 * 30).floor();
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
    // Clean up video controller first
    _videoController?.removeListener(_onVideoFrameChanged);
    _videoController?.dispose();
    _videoController = null;
    
    // Delay provider modifications to after widget tree finalization
    Future.microtask(() {
      try {
        _faceDataCache.clear();
        debugPrint('DISPOSE: Cleared global FaceDataCache');
      } catch (e) {
        debugPrint('DISPOSE: Failed to clear global FaceDataCache: $e');
      }
      
      try {
        _mediaFaceDataNotifier.clearFaces();
        debugPrint('DISPOSE: Cleared MediaFaceDataProvider cache for ${widget.mediaItem.uuid}');
      } catch (e) {
        debugPrint('DISPOSE: Failed to clear MediaFaceDataProvider cache: $e');
      }
    });
    
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
      if (_currentPlaybackMode?.mode == 'stored_data' && _processingStatus?.faceDetectionProcessed == true) {
        await _loadStoredFaceData();
      }

    } catch (e) {
      setState(() {
        _workflowError = 'Failed to initialize smart playback: ${e.toString()}';
      });
      debugPrint('Smart playback initialization error: $e');
      
      // Fallback to basic playback
      _setFallbackPlaybackMode();
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
      
      // 🔧 LOADING FIX: Wait for MediaFaceDataProvider to load data instead of just reading current state
      // First ensure the provider starts loading
      final notifier = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid).notifier);
      notifier.loadFaces();
      
      // Wait for the provider to have data (with timeout)
      var attempts = 0;
      const maxAttempts = 20; // 10 seconds total (500ms * 20)
      
      while (attempts < maxAttempts) {
        final faceDataState = ref.read(mediaFaceDataProvider(widget.mediaItem.uuid));
        
        debugPrint('LOADING ATTEMPT $attempts: hasData=${faceDataState.hasData}, isLoading=${faceDataState.isLoading}, hasError=${faceDataState.hasError}, faces=${faceDataState.hasData ? faceDataState.faces.length : 0}');
        
        if (faceDataState.hasData && faceDataState.faces.isNotEmpty) {
          // Successfully loaded face data
          _storedFaceData = faceDataState.faces;
          _faceDataSource = 'MediaFaceDataProvider_Cache';
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
      
      debugPrint('⏰ LOADING TIMEOUT: MediaFaceDataProvider did not load data within ${maxAttempts * 500}ms, falling back to direct API call');
      
      // Fallback to original stored face data provider if MediaFaceDataProvider failed
      debugPrint('FALLBACK: Loading face data from Vision Service API (embedded endpoint)...');
      debugPrint('YELLOW RECTANGLES DATA SOURCE: Vision Service API (embedded endpoint)');
      final params = StoredFaceDataParams(
        mediaUuid: widget.mediaItem.uuid,
        startFrame: null,
        endFrame: null,
      );
      
      final storedDataAsync = ref.read(storedFaceDataProvider(params));
      await storedDataAsync.when(
        data: (data) async {
          _storedFaceData = data;
          _faceDataSource = 'VisionService_API_Fallback';
          debugPrint('FALLBACK USED: Loaded ${_storedFaceData?.length ?? 0} face records from Vision Service (embedded endpoint)');
          debugPrint('YELLOW RECTANGLES DATA SOURCE: Vision Service API (embedded endpoint)');
          debugPrint('DATA SOURCE TAG: $_faceDataSource');
        },
        loading: () async {
          _storedFaceData = null;
        },
        error: (error, stack) async {
          throw error;
        },
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
    if (useStoredFaceData && facesToDisplay.isNotEmpty) {
      // Workflow 5: Use stored face data for optimized performance
      return _buildOptimizedVideoPlayer(videoUrl, facesToDisplay, dataSource);
    } else {
      // Workflow 4 or real-time: Use session-based or real-time overlay
      return _buildSessionBasedVideoPlayer(videoUrl);
    }
  }

  /// Build optimized video player for Workflow 5 (stored face data)
  Widget _buildOptimizedVideoPlayer(String videoUrl, List<FaceDetection> facesToDisplay, String dataSource) {
    return Stack(
      children: [
        VideoPlayerWidget(
          videoUrl: videoUrl,
          headers: widget.headers,
          collectionId: widget.collectionId,
          onControllerReady: (controller) {
            _videoController = controller;
            if (controller != null) {
              widget.onControllerReady?.call(controller);
              // Set up frame synchronization for face rectangles
              _setupFaceFrameSync(facesToDisplay, dataSource);
            }
          },
        ),
        // 🎯 FACE RECTANGLES OVERLAY - Using EXACT same approach as working yellow rectangles
        if (_videoController != null && _videoController!.value.isInitialized && _currentSyncedFaces.isNotEmpty)
          Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(
                painter: OptimizedFacePainter(
                  faces: _currentSyncedFaces,
                  videoSize: _videoController!.value.size,
                  dataSource: dataSource,
                  faceOpacities: _enableSmoothTransitions ? _faceOpacities : {}, // EXPERIMENTAL: Pass opacity data
                ),
              ),
            ),
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
      child: VideoPlayerWidget(
        videoUrl: videoUrl,
        headers: widget.headers,
        collectionId: widget.collectionId,
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
      onControllerReady: (controller) {
        _videoController = controller;
        if (controller != null) {
          widget.onControllerReady?.call(controller);
        }
      },
    );
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

  /// Build playback mode indicator
  Widget _buildPlaybackModeIndicator() {
    if (_currentPlaybackMode == null) return const SizedBox.shrink();

    return Positioned(
      top: 16,
      left: 16,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: _getPlaybackModeColor().withValues(alpha: 0.9),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _getPlaybackModeIcon(),
              size: 14,
              color: Colors.white,
            ),
            const SizedBox(width: 4),
            Text(
              _getPlaybackModeDisplayName(),
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
    _setupVideoListener();
  }

  /// Setup video controller listener for frame-based face data display
  void _setupVideoListener() {
    widget.videoController?.addListener(_onVideoPositionChanged);
  }

  /// Handle video position changes to show appropriate face data
  void _onVideoPositionChanged() {
    final controller = widget.videoController;
    if (!mounted || controller == null) return;

    final currentPosition = controller.value.position;
    final currentFrameNumber = _positionToFrameNumber(currentPosition);
    
    // Filter faces by current frame number
    // Note: Since FaceDetection doesn't have frameNumber, we need to implement frame-based filtering
    // For now, show a subset of faces based on current frame to simulate synchronization
    final totalFaces = widget.storedFaceData.length;
    if (totalFaces == 0) return;
    
    // Simple frame-based filtering: show different faces at different frame intervals
    final facesPerFrame = (totalFaces / 30).ceil(); // Assume 30fps, distribute faces across frames
    final startIndex = (currentFrameNumber % 30) * facesPerFrame;
    final endIndex = (startIndex + facesPerFrame).clamp(0, totalFaces);
    
    final currentFrameFaces = startIndex < totalFaces 
        ? widget.storedFaceData.sublist(startIndex, endIndex)
        : <FaceDetection>[];

    debugPrint('FRAME SYNC DEBUG: frame=$currentFrameNumber, totalFaces=$totalFaces, startIndex=$startIndex, endIndex=$endIndex, currentFrameFaces=${currentFrameFaces.length}');

    if (!_listsEqual(_currentFrameFaces, currentFrameFaces)) {
      setState(() {
        _currentFrameFaces = currentFrameFaces;
      });
      debugPrint('FACE UPDATE: Updated _currentFrameFaces to ${_currentFrameFaces.length} faces');
    }
  }

  /// Convert video position to frame number (assuming 30fps)
  int _positionToFrameNumber(Duration position) {
    return (position.inMilliseconds / 1000 * 30).floor();
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
            faceOpacities: {}, // Legacy widget - no smooth transitions
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
  final Map<FaceDetection, double> faceOpacities; // EXPERIMENTAL: Opacity mapping

  OptimizedFacePainter({
    required this.faces,
    required this.videoSize,
    required this.dataSource,
    this.faceOpacities = const {}, // Default to empty map for backward compatibility
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (faces.isEmpty || videoSize.width == 0 || videoSize.height == 0) {
      return;
    }

    // Color coding: Green for memory cache/global cache, Yellow for fallback
    final bool isFromMemoryCache = dataSource == 'MediaFaceDataProvider_Cache' || dataSource == 'global_cache';
    final Color rectangleColor = isFromMemoryCache ? Colors.green : Colors.yellow;
    final String colorName = isFromMemoryCache ? 'GREEN' : 'YELLOW';
    
    final paint = Paint()
      ..color = rectangleColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0; // Make thicker for better visibility

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
      
      // EXPERIMENTAL: Get opacity for smooth transitions
      final opacity = faceOpacities[face] ?? 1.0;
      
      // Skip faces with very low opacity
      if (opacity < 0.05) continue;
      
      // Scale face coordinates to match actual video display area (WORKING LOGIC)
      // Convert from left,top,width,height to left,top,right,bottom for Rect.fromLTRB
      final rect = Rect.fromLTRB(
        bbox.left * scaleX + offsetX,
        bbox.top * scaleY + offsetY,
        (bbox.left + bbox.width) * scaleX + offsetX,
        (bbox.top + bbox.height) * scaleY + offsetY,
      );

      // Create paint with opacity for smooth transitions
      final opacityPaint = Paint()
        ..color = rectangleColor.withValues(alpha: opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.0;

      // Draw rectangle with opacity
      canvas.drawRect(rect, opacityPaint);

      // Draw confidence text with opacity
      final confidence = face.confidence;
      textPainter.text = TextSpan(
        text: '${(confidence * 100).toInt()}%',
        style: TextStyle(
          color: rectangleColor.withValues(alpha: opacity),
          fontSize: 14,
          fontWeight: FontWeight.bold,
          shadows: [
            Shadow(
              offset: const Offset(1.0, 1.0),
              blurRadius: 2.0,
              color: Colors.black.withValues(alpha: opacity * 0.8),
            ),
          ],
        ),
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(rect.left, rect.top - 25));
    }

    // Simple success message
    debugPrint('🎨 ${faces.length} $colorName rectangles painted successfully');
  }

  @override
  bool shouldRepaint(OptimizedFacePainter oldDelegate) {
    return faces != oldDelegate.faces || 
           videoSize != oldDelegate.videoSize ||
           dataSource != oldDelegate.dataSource ||
           faceOpacities != oldDelegate.faceOpacities; // EXPERIMENTAL: Include opacity changes
  }
}