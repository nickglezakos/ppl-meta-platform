import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../services/media_api_client.dart'; // Import for FaceDetection class
import '../core/providers/features_provider.dart';
import '../core/api/api_client.dart';
import '../providers/face_data_providers.dart'; // Import face data providers
import '../providers/face_memory_manager.dart'; // Import global cache

/// Simplified face detection overlay with pre-processing approach
/// 
/// Workflow:
/// 1. Check if face rectangles are stored in database
/// 2. If stored: Load all faces and play video with overlay
/// 3. If not stored: 
///    a. Show loading indicator with progress
///    b. Process entire video for face detection (store in memory)
///    c. Play video with faces from memory
///    d. Save all faces to database after completion
/// 
/// NEW: Embedded Face Detection Mode
/// When useEmbeddedFaceDetection=true, the video stream already contains
/// yellow face rectangles embedded by the Media service, eliminating the need
/// for cross-service API calls and providing real-time face detection.
class SimpleFaceDetectionOverlay extends ConsumerStatefulWidget {
  final Widget child;
  final VideoPlayerController? videoController;
  final String? videoUrl;
  final bool enabled;
  final bool useEmbeddedFaceDetection;

  const SimpleFaceDetectionOverlay({
    super.key,
    required this.child,
    this.videoController,
    this.videoUrl,
    this.enabled = true,
    this.useEmbeddedFaceDetection = false,
  });

  @override
  ConsumerState<SimpleFaceDetectionOverlay> createState() => _SimpleFaceDetectionOverlayState();
}

/// Time-based face with automatic disappearance
class TimedFaceDetection {
  final FaceDetection face;
  final DateTime appearanceTime;
  final Timer disappearanceTimer;
  final String id; // Unique identifier for this timed face

  TimedFaceDetection({
    required this.face,
    required this.appearanceTime,
    required this.disappearanceTimer,
    required this.id,
  });
}

class _SimpleFaceDetectionOverlayState extends ConsumerState<SimpleFaceDetectionOverlay> {
  // Current state
  List<FaceDetection> _currentFaceDetections = [];
  String? _mediaId;
  
  // [FIX] DEBUG: Instance tracking
  static int _instanceCounter = 0;
  late final int _instanceId;
  
  // [TARGET] NEW: Time-based face tracking for 0.5-second automatic disappearance
  Map<String, TimedFaceDetection> _timedFaces = {};
  int _faceIdCounter = 0;
  
  // Processing states
  bool _isProcessingVideo = false;
  bool _isVideoReady = false;
  bool _hasStoredFaces = false;
  double _processingProgress = 0.0;
  int _totalFramesToProcess = 0;
  int _processedFrames = 0;
  
  // Face storage
  Map<int, List<FaceDetection>> _memoryCache = {}; // Cache faces during processing
  Map<String, List<FaceDetection>> _allStoredFaces = {};
  
  // Media API client for optimized workflow
  MediaApiClient? _mediaApi;
  
  // Playback timer for synchronized face display
  Timer? _playbackTimer;

  @override
  void initState() {
    super.initState();
    _instanceId = ++_instanceCounter;
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId CREATED for media: ${widget.videoUrl}');
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Total instances created so far: $_instanceCounter');
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Controller available: ${widget.videoController != null}');
    _initializeFaceDetection();
  }

  @override
  void didUpdateWidget(SimpleFaceDetectionOverlay oldWidget) {
    super.didUpdateWidget(oldWidget);
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: didUpdateWidget called');
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Old controller: ${oldWidget.videoController != null}, New controller: ${widget.videoController != null}');
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Old URL: ${oldWidget.videoUrl}, New URL: ${widget.videoUrl}');
    
    // Check if video URL changed (switching videos)
    if (oldWidget.videoUrl != widget.videoUrl) {
      debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Video URL changed, clearing cache and reinitializing...');
      
      // Clear global cache for the previous video
      final oldMediaId = _extractMediaIdFromUrl(oldWidget.videoUrl ?? '');
      if (oldMediaId != null) {
        final globalManager = FaceDataMemoryManager();
        globalManager.clearMediaData(oldMediaId);
        debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Cleared global cache for previous media $oldMediaId');
      }
      
      // Clear all cached data for the previous video
      _memoryCache.clear();
      _allStoredFaces.clear();
      _currentFaceDetections.clear();
      _cleanupAllTimedFaces();
      
      // Reset state
      setState(() {
        _hasStoredFaces = false;
        _isVideoReady = false;
        _isProcessingVideo = false;
      });
      
      // Extract new media ID and reinitialize
      final newMediaId = _extractMediaIdFromUrl(widget.videoUrl ?? '');
      if (newMediaId != _mediaId) {
        debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Media ID changed from $_mediaId to $newMediaId');
        _mediaId = newMediaId;
      }
      
      _initializeFaceDetection();
      return;
    }
    
    // Check if video controller became available
    if (oldWidget.videoController == null && widget.videoController != null) {
      debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Controller became available, reinitializing...');
      _initializeFaceDetection();
    }
  }

  @override
  void dispose() {
    debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId DISPOSED');
    _playbackTimer?.cancel();
    
    // [TARGET] Clean up all timed faces and their timers
    _cleanupAllTimedFaces();
    
    // Remove video controller listener
    if (widget.videoController != null) {
      widget.videoController!.removeListener(_onVideoPositionChanged);
    }
    
    super.dispose();
  }

  /// [TARGET] NEW: Clean up all timed faces and cancel their timers
  void _cleanupAllTimedFaces() {
    for (final timedFace in _timedFaces.values) {
      timedFace.disappearanceTimer.cancel();
    }
    _timedFaces.clear();
  }

  /// [TARGET] NEW: Add faces with 0.5-second auto-disappearance timers
  void _addTimedFaces(List<FaceDetection> faces) {
    if (faces.isEmpty) return;
    
    final currentTime = DateTime.now();
    
    for (final face in faces) {
      // Create unique ID for this face
      final faceId = 'face_${_faceIdCounter++}_${currentTime.millisecondsSinceEpoch}';
      
      // Create timer that will remove this face after 0.5 seconds
      final timer = Timer(const Duration(milliseconds: 500), () {
        _removeTimedFace(faceId);
      });
      
      // Create timed face object
      final timedFace = TimedFaceDetection(
        face: face,
        appearanceTime: currentTime,
        disappearanceTimer: timer,
        id: faceId,
      );
      
      // Add to timed faces map
      _timedFaces[faceId] = timedFace;
      
      debugPrint('🟡 ADDED TIMED FACE: $faceId at ${currentTime.millisecondsSinceEpoch} (will disappear in 0.5s)');
    }
    
    // Update the current display list
    _updateCurrentFaceDisplay();
  }

  /// [TARGET] NEW: Remove a specific timed face when its timer expires
  void _removeTimedFace(String faceId) {
    if (_timedFaces.containsKey(faceId)) {
      _timedFaces[faceId]!.disappearanceTimer.cancel();
      _timedFaces.remove(faceId);
      
      debugPrint('🔴 REMOVED TIMED FACE: $faceId after 0.5 seconds');
      
      // Update the current display list
      _updateCurrentFaceDisplay();
    }
  }

  /// [TARGET] NEW: Update current face display from active timed faces
  void _updateCurrentFaceDisplay() {
    if (!mounted) return;
    
    // Extract all faces from active timed faces
    final activeFaces = _timedFaces.values.map((timedFace) => timedFace.face).toList();
    
    setState(() {
      _currentFaceDetections = activeFaces;
    });
    
    debugPrint('👤 FACE DISPLAY UPDATED: ${activeFaces.length} active faces');
  }

  /// Initialize face detection system
  Future<void> _initializeFaceDetection() async {
    
    if (!widget.enabled) {
      return;
    }
    
    // If using embedded face detection, skip complex processing
    // The video stream already contains yellow face rectangles
    if (widget.useEmbeddedFaceDetection) {
      debugPrint('[TARGET] Using embedded face detection - no overlay processing needed');
      setState(() {
        _isVideoReady = true;
        _hasStoredFaces = true; // Treat as having faces since they're embedded
      });
      return;
    }
    
    if (widget.videoController == null) {
      return;
    }
    
    // Wait for video controller to be initialized
    if (!widget.videoController!.value.isInitialized) {
      // Add listener to wait for initialization
      void checkInitialization() {
        if (widget.videoController!.value.isInitialized) {
          widget.videoController!.removeListener(checkInitialization);
          _initializeFaceDetectionAfterVideoReady();
        }
      }
      widget.videoController!.addListener(checkInitialization);
      return;
    }
    
    await _initializeFaceDetectionAfterVideoReady();
  }

  /// Initialize face detection after video controller is ready
  Future<void> _initializeFaceDetectionAfterVideoReady() async {
    try {
      // Initialize Media API client for optimized workflow
      final apiClient = ref.read(apiClientProvider);
      _mediaApi = MediaApiClient(apiClient);
      
      // Extract media ID from video URL
      _mediaId = _extractMediaIdFromUrl(widget.videoUrl ?? '');
      debugPrint('🔗 Video URL: ${widget.videoUrl}');
      debugPrint('🆔 Extracted media ID: $_mediaId');
      if (_mediaId == null) {
        debugPrint('❌ Failed to extract media ID from URL');
        return;
      }
      
      
      // Check for stored faces first
      await _checkForStoredFaces();
    } catch (e) {
    }
  }

  /// Extract media ID from video URL
  String? _extractMediaIdFromUrl(String url) {
    try {
      final uri = Uri.parse(url);
      final pathSegments = uri.pathSegments;
      
      // Extract media ID from URL like /api/v1/media/stream/{media_id}
      if (pathSegments.length >= 4 && pathSegments[3] == 'stream') {
        return pathSegments[4];
      }
    } catch (e) {
    }
    return null;
  }

  /// Check if faces are already stored in database
  Future<void> _checkForStoredFaces() async {
    try {
      debugPrint('[DEBUG] OVERLAY INSTANCE #$_instanceId: Checking for stored faces for media ID: $_mediaId');
      
      // For embedded face detection, skip all API calls - faces are in the video stream
      if (widget.useEmbeddedFaceDetection) {
        debugPrint('[TARGET] Using embedded face detection - skipping API calls');
        setState(() {
          _hasStoredFaces = false;
          _isVideoReady = true;
          _isProcessingVideo = false;
        });
        return;
      }
      
      // [FIX] FIRST-PLAY FIX: Check global face cache first
      if (_mediaId != null) {
        final globalManager = FaceDataMemoryManager();
        debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Checking global cache for $_mediaId');
        if (globalManager.hasFaceData(_mediaId!)) {
          debugPrint('[TARGET] OVERLAY INSTANCE #$_instanceId: GLOBAL CACHE HIT: Found face data in global cache');
          
          final globalMemoryCache = globalManager.getMemoryCache(_mediaId!);
          final globalStoredFaces = globalManager.getStoredFaces(_mediaId!);
          
          if (globalMemoryCache != null && globalMemoryCache.isNotEmpty) {
            _memoryCache = Map.from(globalMemoryCache);
            if (globalStoredFaces != null) {
              _allStoredFaces = Map.from(globalStoredFaces);
            }
            
            debugPrint('✅ OVERLAY INSTANCE #$_instanceId: GLOBAL CACHE: Loaded ${_memoryCache.length} frames with faces from global cache');
            debugPrint('✅ OVERLAY INSTANCE #$_instanceId: GLOBAL CACHE: Total cached faces: ${_memoryCache.values.fold(0, (sum, faces) => sum + faces.length)}');
            
            setState(() {
              _hasStoredFaces = true;
              _isVideoReady = true;
            });
            _startStoredFacePlayback();
            return;
          }
        } else {
          debugPrint('🔍 OVERLAY INSTANCE #$_instanceId: GLOBAL CACHE MISS: No face data in global cache, checking providers...');
        }
        
        // Check global face data providers
        final faceDataState = ref.read(mediaFaceDataProvider(_mediaId!));
        if (faceDataState.hasData && faceDataState.faces.isNotEmpty) {
          debugPrint('[TARGET] OVERLAY INSTANCE #$_instanceId: GLOBAL PROVIDER HIT: Found ${faceDataState.faces.length} faces in global provider cache');
          await _storeCachedFacesInProvider(faceDataState.faces);
          return;
        } else {
          debugPrint('🔍 OVERLAY INSTANCE #$_instanceId: GLOBAL PROVIDER MISS: No face data in global provider, trying Vision API...');
        }
      }
      
      // Try to load face data using Orchestrator-based providers
      debugPrint('🔍 OVERLAY INSTANCE #$_instanceId: Loading faces via Orchestrator providers...');
      
      // Trigger face loading through provider (wrapped in Future.microtask to avoid lifecycle conflicts)
      Future.microtask(() async {
        try {
          final notifier = ref.read(mediaFaceDataProvider(_mediaId!).notifier);
          await notifier.loadFaces();
          
          // Wait a moment for provider to update, then check for the data
          await Future.delayed(const Duration(milliseconds: 500));
          
          // Get the loaded face data
          final faceData = ref.read(mediaFaceDataProvider(_mediaId!));
          debugPrint('📊 Orchestrator Provider Response: success=${!faceData.hasError}, totalFaces=${faceData.totalCount}');
          
          if (faceData.hasData && faceData.faces.isNotEmpty) {
            // Store in global cache and update overlay
            await _storeCachedFacesInProvider(faceData.faces);
            debugPrint('✅ OVERLAY INSTANCE #$_instanceId: Successfully processed ${faceData.faces.length} Enhanced Logic V2 faces');
          } else {
            debugPrint('❌ OVERLAY INSTANCE #$_instanceId: No face data available after Enhanced Logic V2 call');
            // Set video ready even without faces so video can play
            setState(() {
              _hasStoredFaces = false;
              _isVideoReady = true;
              _isProcessingVideo = false;
            });
          }
        } catch (e) {
          debugPrint('🔍 OVERLAY INSTANCE #$_instanceId: Provider loading error: $e');
          // Set video ready even on error so video can play
          setState(() {
            _hasStoredFaces = false;
            _isVideoReady = true;
            _isProcessingVideo = false;
          });
        }
      });
      
    } catch (e) {
      debugPrint('[ERROR] OVERLAY INSTANCE #$_instanceId: Error checking stored faces: $e');
      setState(() {
        _hasStoredFaces = false;
        _isVideoReady = true;
        _isProcessingVideo = false;
      });
    }
  }

  /// Store cached faces in provider and update overlay state
  Future<void> _storeCachedFacesInProvider(List<FaceDetection> faces) async {
    if (_mediaId == null || faces.isEmpty) return;
    
    try {
      debugPrint('[TARGET] OVERLAY INSTANCE #$_instanceId: Processing ${faces.length} Enhanced Logic V2 faces...');
      
      // Clear memory cache and repopulate
      _memoryCache.clear();
      
      // Group faces by frame number (Enhanced Logic V2 provides frame_number directly)
      for (final face in faces) {
        int frameNumber = 0;
        
        // Enhanced Logic V2 provides frame_number in metadata
        if (face.metadata != null && face.metadata!.containsKey('frame_number')) {
          frameNumber = (face.metadata!['frame_number'] as num?)?.toInt() ?? 0;
        } else if (face.metadata != null && face.metadata!.containsKey('frame')) {
          frameNumber = (face.metadata!['frame'] as num?)?.toInt() ?? 0;
        } else {
          // Fallback: estimate frame number from timestamp (if available)
          // Assume 30 FPS: frame = timestamp * 30
          final timestamp = face.timestamp;
          if (timestamp != null) {
            frameNumber = (timestamp.millisecondsSinceEpoch ~/ 1000 * 30);
          }
        }
        
        if (!_memoryCache.containsKey(frameNumber)) {
          _memoryCache[frameNumber] = [];
        }
        _memoryCache[frameNumber]!.add(face);
        
        debugPrint('[TARGET] Frame $frameNumber: bbox=${face.boundingBox}, confidence=${face.confidence}');
      }
      
      debugPrint('[TARGET] Enhanced Logic V2: Loaded ${faces.length} faces across ${_memoryCache.keys.length} frames');
      
      // Create faces_by_frame format for compatibility 
      final facesByFrame = <String, List<FaceDetection>>{};
      _memoryCache.forEach((frameNum, faces) {
        facesByFrame[frameNum.toString()] = faces;
        debugPrint('[TARGET] Frame $frameNum: ${faces.length} faces');
      });
      
      // Store in global cache for persistence
      final globalManager = FaceDataMemoryManager();
      globalManager.storeFaceData(_mediaId!, _memoryCache, facesByFrame);
      debugPrint('[FIX] OVERLAY INSTANCE #$_instanceId: Stored ${faces.length} Enhanced Logic V2 faces in global cache for $_mediaId');
      
      setState(() {
        _hasStoredFaces = true;
        _allStoredFaces = facesByFrame;
        _isVideoReady = true;
        _isProcessingVideo = false;
      });
      
      debugPrint('✅ OVERLAY INSTANCE #$_instanceId: Enhanced Logic V2 overlay ready with ${faces.length} faces!');
      _startStoredFacePlayback();
      
    } catch (e) {
      debugPrint('[ERROR] OVERLAY INSTANCE #$_instanceId: Error storing Enhanced Logic V2 faces: $e');
      setState(() {
        _hasStoredFaces = false;
        _isVideoReady = true;
        _isProcessingVideo = false;
      });
    }
  }

  /// Process entire video for face detection before playback
  Future<void> _processEntireVideo() async {
    if (_mediaId == null || widget.videoController == null) return;

    // For embedded face detection, skip bulk processing - faces are in the video stream
    if (widget.useEmbeddedFaceDetection) {
      debugPrint('[TARGET] Using embedded face detection - skipping bulk processing');
      setState(() {
        _isVideoReady = true;
        _isProcessingVideo = false;
        _hasStoredFaces = false; // No stored faces needed - they're embedded
      });
      return;
    }

    // [FIX] CRITICAL BUG FIX: Removed progress bar complexity - process video directly
    // setState(() {
    //   _isProcessingVideo = true;
    //   _processingProgress = 0.0;
    //   _processedFrames = 0;
    // });

    try {
      debugPrint('[TARGET] Starting optimized video processing with Media Service workflow...');
      
      // Get user's face detection preferences
      final features = ref.read(featuresNotifierProvider).value;
      final selectedMethod = features?.selectedDetectionMethod ?? 'two_stage';
      final confidenceThreshold = features?.confidenceThreshold ?? 0.5;
      final frameInterval = features?.frameInterval ?? 15;
      
      // ✅ PRIORITY 2 FIX: Use optimized Media Service workflow instead of direct Vision Service
      // Convert frameInterval to framesPerSecond (30 FPS base / frameInterval)
      final framesPerSecond = frameInterval > 0 ? (30.0 / frameInterval) : 3.0;
      
      debugPrint('[TARGET] Using optimized workflow with $framesPerSecond FPS (frame interval: $frameInterval)');
      
      if (_mediaApi == null) {
        throw Exception('MediaApiClient not initialized');
      }
      
      // Start optimized bulk face detection workflow
      final workflowResult = await _mediaApi!.startBulkFaceDetectionWorkflow(
        mediaId: _mediaId!,
        framesPerSecond: framesPerSecond,
        method: selectedMethod,
        confidenceThreshold: confidenceThreshold,
        storeResults: true,
      );
      
      debugPrint('[TARGET] Workflow started: ${workflowResult.workflowId}, status: ${workflowResult.status}');
      
      // Wait for workflow completion (with timeout)
      int maxAttempts = 30; // 30 seconds max
      int attempts = 0;
      
      while (attempts < maxAttempts && !workflowResult.isCompleted && !workflowResult.isFailed) {
        await Future.delayed(Duration(seconds: 1));
        attempts++;
        
        final statusResult = await _mediaApi!.getBulkFaceDetectionWorkflowStatus(
          workflowId: workflowResult.workflowId,
        );
        
        debugPrint('[TARGET] Workflow status check #$attempts: ${statusResult.status}');
        
        if (statusResult.isCompleted) {
          debugPrint('[TARGET] Workflow completed successfully!');
          break;
        } else if (statusResult.isFailed) {
          throw Exception('Workflow failed: ${statusResult.errorMessage}');
        }
      }
      
      if (attempts >= maxAttempts) {
        throw Exception('Workflow timeout after 30 seconds');
      }
      
      // Now fetch the results from Orchestrator Provider (workflow stores them there)
      debugPrint('[TARGET] Fetching processed face results from Orchestrator Provider after workflow...');
      
      // Trigger face loading through provider (this uses Orchestrator session-based detection)
      final notifier = ref.read(mediaFaceDataProvider(_mediaId!).notifier);
      await notifier.loadFaces(forceRefresh: true); // Force refresh to get new results
      
      // Get the loaded face data
      final faceData = ref.read(mediaFaceDataProvider(_mediaId!));
      
      if (!faceData.hasError && faceData.faces.isNotEmpty) {
        debugPrint('[TARGET] Retrieved ${faceData.totalCount} faces from Orchestrator Provider');
        
        // Convert to memory cache format (group by frame number)
        _memoryCache.clear();
        for (final face in faceData.faces) {
          // Extract frame number from face metadata or use default
          int frameNumber = 0;
          if (face.metadata != null && face.metadata!.containsKey('frame')) {
            frameNumber = (face.metadata!['frame'] as num?)?.toInt() ?? 0;
          }
          
          if (!_memoryCache.containsKey(frameNumber)) {
            _memoryCache[frameNumber] = [];
          }
          _memoryCache[frameNumber]!.add(face);
        }
        
        debugPrint('[TARGET] Memory cache populated with ${_memoryCache.length} frames from Orchestrator Provider');
        
      } else {
        throw Exception('No face detection results returned from Orchestrator Provider: ${faceData.error}');
      }

      // [FIX] CRITICAL FIX: Set states properly and start face display immediately
      debugPrint('[TARGET] Setting up video for immediate face display...');
      setState(() {
        _isProcessingVideo = false;
        _isVideoReady = true;
        _hasStoredFaces = false; // Use memory cache, not stored faces
      });
      
      // [FIX] CRITICAL FIX: Immediately set up video position listener and trigger face display
      await _setupVideoFaceDisplay();
      
      // 🚫 DISABLED: Save to database in background (real-time detection should not store frames)
      // await _saveFacesToDatabase(); // DISABLED: Real-time detection for visual feedback only

    } catch (e) {
      debugPrint('❌ Processing failed: $e');
      // Even if processing fails, show yellow rectangle overlay (may be empty but overlay is there)
      setState(() {
        _isProcessingVideo = false;
        _isVideoReady = true;
        _hasStoredFaces = false; // Use memory cache
      });
      
      // Try to start playback with whatever faces we might have
      await _setupVideoFaceDisplay();
    }
  }

  /// Start playback using stored faces from database
  void _startStoredFacePlayback() {
    
    // Listen to video controller position changes for frame-based sync
    if (widget.videoController != null) {
      widget.videoController!.addListener(_onVideoPositionChanged);
      
      // Trigger immediate face update for current position
      if (widget.videoController!.value.isInitialized) {
        _onVideoPositionChanged();
      }
    }
  }

  /// Start playback using cached faces from memory
  Future<void> _startCachedFacePlayback() async {
    
    // Wait a moment for video controller to stabilize
    await Future.delayed(const Duration(milliseconds: 500));
    
    if (!mounted) return;
    
    // Listen to video controller position changes for frame-based sync
    if (widget.videoController != null) {
      widget.videoController!.addListener(_onVideoPositionChanged);
      
      // Trigger immediate face update for current position
      if (widget.videoController!.value.isInitialized) {
        _onVideoPositionChanged();
      }
    }
  }

  /// [FIX] CRITICAL FIX: New method to properly set up video face display
  Future<void> _setupVideoFaceDisplay() async {
    debugPrint('[TARGET] Setting up video face display...');
    
    if (!mounted || widget.videoController == null) {
      debugPrint('❌ Cannot setup face display - widget not mounted or no video controller');
      return;
    }
    
    // Remove any existing listeners to avoid duplicates
    widget.videoController!.removeListener(_onVideoPositionChanged);
    
    // Add the position listener
    widget.videoController!.addListener(_onVideoPositionChanged);
    debugPrint('[TARGET] Video position listener added');
    
    // Start backup timer for face overlay updates (in case position listener doesn't fire)
    _startBackupOverlayTimer();
    
    // If video is initialized, immediately trigger face update
    if (widget.videoController!.value.isInitialized) {
      debugPrint('[TARGET] Video is initialized, triggering immediate face update');
      _onVideoPositionChanged();
    } else {
      debugPrint('⚠️ Video not yet initialized, face display will start when video loads');
    }
    
    // Small delay to ensure everything is properly set up
    await Future.delayed(const Duration(milliseconds: 100));
    debugPrint('[TARGET] Video face display setup complete');
  }

  /// Start backup timer to ensure faces are displayed even if position listener fails
  void _startBackupOverlayTimer() {
    // Cancel any existing timer
    _playbackTimer?.cancel();
    
    debugPrint('🔄 Starting backup overlay timer for face display');
    
    // Update overlay every 100ms for smooth face clearing/showing
    _playbackTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
      if (!mounted || widget.videoController == null || !widget.videoController!.value.isInitialized) {
        timer.cancel();
        return;
      }
      
      // Update if video is playing - regardless of cache status to allow clearing
      if (widget.videoController!.value.isPlaying) {
        final position = widget.videoController!.value.position;
        final fps = 30.0;
        final currentFrameNumber = (position.inMilliseconds / 1000.0 * fps).round();
        
        // Use the same update logic as position changed handler
        if (_memoryCache.isNotEmpty) {
          _updateFacesFromMemoryCache(position);
        } else if (_hasStoredFaces && _allStoredFaces.isNotEmpty) {
          _updateFacesFromStoredData(position);
        } else {
          // Clear faces if no data available - using timed approach
          _cleanupAllTimedFaces();
        }
      }
    });
  }

  /// Handle video position changes - frame-based synchronization
  void _onVideoPositionChanged() {
    if (!mounted || widget.videoController == null || !widget.videoController!.value.isInitialized) {
      return;
    }
    
    try {
      final position = widget.videoController!.value.position;
      final fps = 30.0;
      final currentFrameNumber = (position.inMilliseconds / 1000.0 * fps).round();
      
      // [TARGET] ENHANCED DEBUG: Only log when playing and show current face count
      if (widget.videoController!.value.isPlaying) {
        debugPrint('🎬 PLAYING at ${position.inSeconds.toStringAsFixed(1)}s (frame $currentFrameNumber) - Current faces: ${_currentFaceDetections.length}');
        
        // [FIX] FIRST-PLAY FIX: If video is playing but no faces are loaded, check if face data became available
        if (_currentFaceDetections.isEmpty && !_hasStoredFaces && _memoryCache.isEmpty) {
          debugPrint('🚨 EMERGENCY CHECK: Video playing but no faces - checking if face data is now available...');
          // Trigger an emergency check without async/await to avoid blocking
          _emergencyCheckForFaces();
        }
        
        // [FIX] CRITICAL FIX: Always check memory cache first, then stored faces
        if (_memoryCache.isNotEmpty) {
          _updateFacesFromMemoryCache(position);
        } else if (_hasStoredFaces && _allStoredFaces.isNotEmpty) {
          _updateFacesFromStoredData(position);
        } else {
          // Clear faces if no data available - using timed approach
          _cleanupAllTimedFaces();
        }
      }
    } catch (e) {
      debugPrint('❌ Error in video position changed: $e');
    }
  }

  /// 🚨 Emergency check for face data that may have loaded after video started playing
  void _emergencyCheckForFaces() {
    // Don't use async/await to avoid blocking the video position callback
    (() async {
      try {
        if (_mediaId == null) return;
        
        debugPrint('🚨 EMERGENCY: Checking Orchestrator Provider for face data...');
        
        // Try to load faces through provider
        final notifier = ref.read(mediaFaceDataProvider(_mediaId!).notifier);
        await notifier.loadFaces();
        final faceData = ref.read(mediaFaceDataProvider(_mediaId!));
        
        if (faceData.hasData && faceData.faces.isNotEmpty && _memoryCache.isEmpty) {
          debugPrint('🚨 EMERGENCY SUCCESS: Found ${faceData.totalCount} faces, setting up emergency playback');
          
          // Populate memory cache from provider face data
          _memoryCache.clear();
          for (final face in faceData.faces) {
            // Extract frame number from face metadata or use default
            int frameNumber = 0;
            if (face.metadata != null && face.metadata!.containsKey('frame')) {
              frameNumber = (face.metadata!['frame'] as num?)?.toInt() ?? 0;
            }
            
            if (!_memoryCache.containsKey(frameNumber)) {
              _memoryCache[frameNumber] = [];
            }
            _memoryCache[frameNumber]!.add(face);
          }
          
          // Update stored faces data structure for compatibility
          final facesByFrame = <String, List<FaceDetection>>{};
          _memoryCache.forEach((frameNum, faces) {
            facesByFrame[frameNum.toString()] = faces;
          });
          _allStoredFaces = facesByFrame;
          
          debugPrint('🚨 EMERGENCY: Loaded ${_memoryCache.length} frames into memory cache');
          debugPrint('🚨 EMERGENCY: Total faces: ${_memoryCache.values.fold(0, (sum, faces) => sum + faces.length)}');
          
          if (mounted) {
            setState(() {
              _hasStoredFaces = true;
              _isVideoReady = true;
            });
            
            // Immediately trigger face update for current video position
            _onVideoPositionChanged();
          }
        }
      } catch (e) {
        debugPrint('🚨 EMERGENCY CHECK FAILED: $e');
      }
    })();
  }

  /// Update faces display from stored database data
  void _updateFacesFromStoredData(Duration position) {
    if (_allStoredFaces.isEmpty) return;
    
    // Calculate approximate frame number from video position and typical frame rate
    final videoInfo = widget.videoController?.value;
    if (videoInfo == null || !videoInfo.isInitialized) return;
    
    // Use 30 FPS as baseline (this should ideally come from video metadata)
    final fps = 30.0;
    final currentFrameNumber = (position.inMilliseconds / 1000.0 * fps).round();
    
    // Find the closest frame in our stored data
    String? closestFrameKey;
    int minDistance = 9999;
    
    for (final frameKey in _allStoredFaces.keys) {
      final storedFrameNumber = int.tryParse(frameKey);
      if (storedFrameNumber != null) {
        final distance = (storedFrameNumber - currentFrameNumber).abs();
        if (distance < minDistance) {
          minDistance = distance;
          closestFrameKey = frameKey;
        }
      }
    }
    
    // Update faces if we found a close match (within 5 frames tolerance)
    if (closestFrameKey != null && minDistance <= 5) {
      final frameFaces = _allStoredFaces[closestFrameKey] ?? [];
      
      if (frameFaces.isNotEmpty) {
        debugPrint('👤 Found ${frameFaces.length} faces for frame $closestFrameKey (current: $currentFrameNumber, distance: $minDistance)');
      }
      
      if (frameFaces.length != _currentFaceDetections.length || 
          !_areFaceListsEqual(frameFaces, _currentFaceDetections)) {
        debugPrint('Adding timed faces: ${frameFaces.length} faces');
        _addTimedFaces(frameFaces);
      }
    } else {
      // Clear faces if no close match - using timed approach
      _cleanupAllTimedFaces();
    }
  }

  /// Check if two face detection lists are equal
  bool _areFaceListsEqual(List<FaceDetection> list1, List<FaceDetection> list2) {
    if (list1.length != list2.length) return false;
    
    for (int i = 0; i < list1.length; i++) {
      final face1 = list1[i];
      final face2 = list2[i];
      
      // Compare bounding boxes using the current FaceBoundingBox structure
      final bbox1 = face1.boundingBox;
      final bbox2 = face2.boundingBox;
      
      if ((bbox1.left - bbox2.left).abs() > 1) return false;
      if ((bbox1.top - bbox2.top).abs() > 1) return false;
      if ((bbox1.width - bbox2.width).abs() > 1) return false;
      if ((bbox1.height - bbox2.height).abs() > 1) return false;
    }
    
    return true;
  }

  /// Update faces display from memory cache
  void _updateFacesFromMemoryCache(Duration position) {
    if (_memoryCache.isEmpty) {
      if (_currentFaceDetections.isNotEmpty) {
        debugPrint('🧹 CLEARING FACES: Memory cache is empty');
        setState(() {
          _currentFaceDetections = [];
        });
      }
      return;
    }
    
    // Calculate approximate frame number from video position
    final videoInfo = widget.videoController?.value;
    if (videoInfo == null || !videoInfo.isInitialized) return;
    
    final fps = 30.0;
    final currentFrameNumber = (position.inMilliseconds / 1000.0 * fps).round();
    
    // Find closest cached frame
    int? closestFrame;
    int minDistance = 9999;
    
    for (final cachedFrame in _memoryCache.keys) {
      final distance = (cachedFrame - currentFrameNumber).abs();
      if (distance < minDistance) {
        minDistance = distance;
        closestFrame = cachedFrame;
      }
    }
    
    // [TARGET] TIGHTER TOLERANCE: Use much tighter frame tolerance (3 frames = 0.1 seconds)
    // This ensures faces disappear when they should instead of staying visible
    const int frameToleranceThreshold = 3;
    
    if (closestFrame != null && minDistance <= frameToleranceThreshold) {
      final frameFaces = _memoryCache[closestFrame] ?? [];
      
      // Only log significant changes to reduce noise
      if (frameFaces.length != _currentFaceDetections.length) {
        debugPrint('[TARGET] FRAME $currentFrameNumber → CACHED FRAME $closestFrame (distance: $minDistance)');
        debugPrint('👤 FACE UPDATE: ${_currentFaceDetections.length} → ${frameFaces.length} faces');
      }
      
      if (frameFaces.length != _currentFaceDetections.length ||
          !_areFaceListsEqual(frameFaces, _currentFaceDetections)) {
        _addTimedFaces(frameFaces);
        
        if (frameFaces.isEmpty) {
          debugPrint('🧹 FACES CLEARED: No faces in cached frame $closestFrame');
        } else {
          debugPrint('🟡 FACES DISPLAYED: ${frameFaces.length} faces shown for frame $closestFrame');
        }
      }
    } else {
      // Clear faces if no close match - using timed approach
      _cleanupAllTimedFaces();
    }
  }

  /// Save cached faces to database
  Future<void> _saveFacesToDatabase() async {
    if (_mediaId == null || _memoryCache.isEmpty) return;

    try {
      // Get user-selected face detection method
      final features = await ref.read(featuresNotifierProvider.future);
      final selectedMethod = features.selectedDetectionMethod;
      
      // Count total faces for logging
      int totalFaces = 0;
      _memoryCache.values.forEach((faces) => totalFaces += faces.length);
      
      
      // Convert memory cache to database format expected by backend
      final facesByFrame = <String, List<Map<String, dynamic>>>{};
      
      _memoryCache.forEach((frameNumber, faces) {
        final frameKey = frameNumber.toString();
        facesByFrame[frameKey] = faces.map((face) => {
          'bbox': [
            face.boundingBox.left,
            face.boundingBox.top,
            face.boundingBox.left + face.boundingBox.width,  // right = left + width
            face.boundingBox.top + face.boundingBox.height,  // bottom = top + height
          ],
          'confidence': face.confidence,
          'method': face.method,
          'timestamp': (frameNumber / 30.0 * 1000).round(), // Convert to milliseconds
        }).toList();
      });

      // Store faces in bulk with correct data structure for backend
      final facesData = {
        'faces_by_frame': facesByFrame,
        'total_frames': _memoryCache.length,
        'duration': widget.videoController?.value.duration?.inMilliseconds?.toDouble() ?? 0.0,
        'fps': 30.0,
        'metadata': {
          'processing_method': selectedMethod,
          'timestamp': DateTime.now().toIso8601String(),
          'total_faces_detected': totalFaces,
        },
      };

      // Note: Face storage is now handled by the Orchestrator session-based system
      // The faces are automatically persisted when the session completes
      debugPrint('💾 Face storage: Handled by Orchestrator session-based system');
      
      // Always mark as successful since Orchestrator handles persistence
      setState(() {
        _hasStoredFaces = true;
      });
    } catch (e) {
    }
  }

  /// Get total number of stored faces in database
  int _getTotalStoredFaces() {
    return _allStoredFaces.values.fold(0, (sum, faces) => sum + faces.length);
  }

  /// Get total number of cached faces in memory
  int _getTotalCachedFaces() {
    return _memoryCache.values.fold(0, (sum, faces) => sum + faces.length);
  }

  @override
  Widget build(BuildContext context) {
    final features = ref.watch(featuresNotifierProvider);
    final faceDetectionEnabled = features.when(
      data: (state) => state.faceDetectionEnabled,
      loading: () => false,
      error: (_, __) => false,
    );
    
    // Watch for Enhanced Logic V2 data updates
    if (_mediaId != null) {
      final faceData = ref.watch(mediaFaceDataProvider(_mediaId!));
      if (faceData.hasData && faceData.faces.isNotEmpty && _memoryCache.isEmpty && !_isProcessingVideo) {
        debugPrint('🎯 OVERLAY INSTANCE #$_instanceId: Enhanced Logic V2 data available in provider, loading to overlay...');
        WidgetsBinding.instance.addPostFrameCallback((_) async {
          if (mounted) {
            await _storeCachedFacesInProvider(faceData.faces);
          }
        });
      }
    }
    
    debugPrint('🎛️ BUILD: Face detection enabled: $faceDetectionEnabled, widget enabled: ${widget.enabled}');
    debugPrint('🎛️ BUILD: Video ready: $_isVideoReady, processing: $_isProcessingVideo, stored faces: $_hasStoredFaces');
    debugPrint('🎛️ BUILD: Current faces: ${_currentFaceDetections.length}, memory cache: ${_memoryCache.length} frames');
    debugPrint('🎛️ BUILD: Total cached faces: ${_getTotalCachedFaces()}, stored faces: ${_getTotalStoredFaces()}');
    debugPrint('🎛️ BUILD: Using embedded face detection: ${widget.useEmbeddedFaceDetection}');
    
    // 🔧 EMERGENCY GLOBAL CACHE CHECK: Ensure second instance picks up cached data
    if (_mediaId != null && _memoryCache.isEmpty && !_isProcessingVideo && widget.videoController != null && widget.videoController!.value.isInitialized) {
      final globalManager = FaceDataMemoryManager.instance;
      debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Checking emergency cache for $_mediaId (controller ready: ${widget.videoController!.value.isInitialized})');
      if (globalManager.hasFaceData(_mediaId!)) {
        debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Found cached data in build method, loading...');
        final globalMemoryCache = globalManager.getMemoryCache(_mediaId!);
        final globalStoredFaces = globalManager.getStoredFaces(_mediaId!);
        
        if (globalMemoryCache != null && globalMemoryCache.isNotEmpty) {
          debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Emergency cache has ${globalMemoryCache.length} frames');
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              setState(() {
                _memoryCache = Map.from(globalMemoryCache);
                if (globalStoredFaces != null) {
                  _allStoredFaces = Map.from(globalStoredFaces);
                }
                _hasStoredFaces = true;
                _isVideoReady = true;
              });
              _startStoredFacePlayback();
              debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Emergency cache load complete - ${_memoryCache.length} frames');
            }
          });
        }
      } else {
        debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: No cached data found in emergency check (controller ready, but cache empty)');
        // 🔧 DELAYED EMERGENCY CHECK: Try again after a short delay to allow async loading to complete
        if (widget.videoController!.value.isInitialized) {
          Future.delayed(Duration(milliseconds: 100), () {
            if (mounted && _memoryCache.isEmpty && !_isProcessingVideo) {
              debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Delayed emergency check for $_mediaId');
              if (globalManager.hasFaceData(_mediaId!)) {
                debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Delayed emergency check found cached data!');
                final globalMemoryCache = globalManager.getMemoryCache(_mediaId!);
                final globalStoredFaces = globalManager.getStoredFaces(_mediaId!);
                
                if (globalMemoryCache != null && globalMemoryCache.isNotEmpty) {
                  debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Delayed emergency cache has ${globalMemoryCache.length} frames');
                  if (mounted) {
                    setState(() {
                      _memoryCache = Map.from(globalMemoryCache);
                      if (globalStoredFaces != null) {
                        _allStoredFaces = Map.from(globalStoredFaces);
                      }
                      _hasStoredFaces = true;
                      _isVideoReady = true;
                    });
                    _startStoredFacePlayback();
                    debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Delayed emergency cache load complete - ${_memoryCache.length} frames');
                  }
                }
              } else {
                debugPrint('[EMERGENCY] OVERLAY INSTANCE #$_instanceId: Delayed emergency check also found no cached data');
              }
            }
          });
        }
      }
    }
    
    if (!widget.enabled || !faceDetectionEnabled) {
      return widget.child;
    }

    // If using embedded face detection, don't show overlay widgets
    // The face rectangles are already embedded in the video stream
    if (widget.useEmbeddedFaceDetection) {
      return widget.child;
    }

    return Stack(
      children: [
        widget.child,
        
        // [TARGET] DEDICATED FACE RECTANGLES OVERLAY - Only for yellow rectangles
        if (_isVideoReady)
          Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(
                painter: FaceDetectionPainter(
                  faceDetections: _currentFaceDetections,
                  videoController: widget.videoController,
                ),
              ),
            ),
          ),

        // [TARGET] DEDICATED INFORMATION OVERLAY - Separate from face rectangles
        if (_isVideoReady)
          Positioned(
            top: 10,
            left: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.face,
                    color: Colors.green,
                    size: 16,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${_currentFaceDetections.length} faces (${_getTotalCachedFaces()} total)',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),

        // [TARGET] DEDICATED DEBUG OVERLAY - Shows current frame and cached frame status
        if (_isVideoReady && _memoryCache.isNotEmpty)
          Positioned(
            top: 40,
            left: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.7),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'Cache: ${_memoryCache.length} frames',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// Custom painter for drawing face detection rectangles
class FaceDetectionPainter extends CustomPainter {
  final List<FaceDetection> faceDetections;
  final VideoPlayerController? videoController;

  FaceDetectionPainter({
    required this.faceDetections,
    this.videoController,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (videoController == null || !videoController!.value.isInitialized) {
      return;
    }

    if (faceDetections.isEmpty) {
      return;
    }

    debugPrint('🎨 Painting ${faceDetections.length} face rectangles on canvas (${size.width}x${size.height})');
    
    final paint = Paint()
      ..color = Colors.green
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0; // Make thicker for better visibility

    final textPainter = TextPainter(
      textDirection: TextDirection.ltr,
    );

    // Get video dimensions for scaling
    final videoSize = videoController!.value.size;
    debugPrint('🎥 Video size: ${videoSize.width}x${videoSize.height}');
    
    // Calculate actual video display area within the container
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
    
    debugPrint('📐 Display area: ${videoDisplayWidth}x${videoDisplayHeight}, offset: ($offsetX, $offsetY)');
    
    // Calculate scaling factors based on actual video display area
    final scaleX = videoDisplayWidth / videoSize.width;
    final scaleY = videoDisplayHeight / videoSize.height;
    
    debugPrint('⚖️ Scale factors: scaleX=$scaleX, scaleY=$scaleY');

    for (int i = 0; i < faceDetections.length; i++) {
      final face = faceDetections[i];
      final bbox = face.boundingBox;
      
      debugPrint('👤 Face $i: boundingBox=(${bbox.left}, ${bbox.top}, ${bbox.width}, ${bbox.height}), confidence=${face.confidence}, method=${face.method}');
      
      // Scale face coordinates to match actual video display area
      // Convert from left,top,width,height to left,top,right,bottom for Rect.fromLTRB
      final rect = Rect.fromLTRB(
        bbox.left * scaleX + offsetX,
        bbox.top * scaleY + offsetY,
        (bbox.left + bbox.width) * scaleX + offsetX,
        (bbox.top + bbox.height) * scaleY + offsetY,
      );

      debugPrint('📦 Scaled rect: ${rect.left}, ${rect.top}, ${rect.right}, ${rect.bottom}');

      // Draw rectangle
      canvas.drawRect(rect, paint);

      // Draw confidence text
      final confidence = face.confidence;
      textPainter.text = TextSpan(
        text: '${(confidence * 100).toInt()}%',
        style: const TextStyle(
          color: Colors.green,
          fontSize: 14,
          fontWeight: FontWeight.bold,
          shadows: [
            Shadow(
              offset: Offset(1.0, 1.0),
              blurRadius: 2.0,
              color: Colors.black,
            ),
          ],
        ),
      );
      textPainter.layout();
      textPainter.paint(canvas, Offset(rect.left, rect.top - 25));
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
