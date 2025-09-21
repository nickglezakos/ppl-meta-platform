import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../models/media_models.dart';
import '../models/face_detection_models.dart';
import '../services/media_api_client.dart';
import '../widgets/video_player_widget.dart';
import '../widgets/simple_video_face_detection_overlay.dart';
import '../providers/workflow_providers.dart';

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

  @override
  void initState() {
    super.initState();
    _initializeSmartPlayback();
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
          _processingStatus = status;
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
          _currentPlaybackMode = mode;
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
      final params = StoredFaceDataParams(
        mediaUuid: widget.mediaItem.uuid,
        startFrame: null,
        endFrame: null,
      );
      
      final storedDataAsync = ref.read(storedFaceDataProvider(params));
      await storedDataAsync.when(
        data: (data) async {
          _storedFaceData = data;
          debugPrint('📊 Loaded ${_storedFaceData?.length ?? 0} stored face detection records');
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
    final useStoredFaceData = _currentPlaybackMode?.mode == 'stored_data' && 
                              _storedFaceData != null;

    return Stack(
      children: [
        // Video player with smart overlay
        _buildVideoPlayerWithOverlay(videoUrl, useStoredFaceData),
        
        // Playback mode indicator
        _buildPlaybackModeIndicator(),
        
        // Performance indicator
        if (_currentPlaybackMode?.cpuOptimized == true)
          _buildPerformanceIndicator(),
      ],
    );
  }

  /// Build video player with appropriate overlay strategy
  Widget _buildVideoPlayerWithOverlay(String videoUrl, bool useStoredFaceData) {
    if (useStoredFaceData) {
      // Workflow 5: Use stored face data for optimized performance
      return _buildOptimizedVideoPlayer(videoUrl);
    } else {
      // Workflow 4 or real-time: Use session-based or real-time overlay
      return _buildSessionBasedVideoPlayer(videoUrl);
    }
  }

  /// Build optimized video player for Workflow 5 (stored face data)
  Widget _buildOptimizedVideoPlayer(String videoUrl) {
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
            }
          },
        ),
        // Stored face data overlay (only show if video controller is available AND stored data exists)
        if (_videoController != null && _storedFaceData != null && _storedFaceData!.isNotEmpty)
          OptimizedFaceDataOverlay(
            videoController: _videoController,
            storedFaceData: _storedFaceData!,
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
      videoController: _videoController,
      videoUrl: videoUrl,
      enabled: enableOverlay,
      useEmbeddedFaceDetection: false, // Use overlay system, not embedded
      child: VideoPlayerWidget(
        videoUrl: videoUrl,
        headers: widget.headers,
        collectionId: widget.collectionId,
        onControllerReady: (controller) {
          _videoController = controller;
          if (controller != null) {
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
        // Workflow 4: Use Media Service for video + overlay for face detection (Flutter compatibility)
        url = '/api/v1/media/stream/${widget.mediaItem.uuid}';
        debugPrint('🎯 SmartVideoPlayer: Using realtime_with_session Media Service URL with overlay: $url');
        break;
      
      case 'realtime_only':
      default:
        // Basic real-time: Use Media Service for video + overlay for face detection (Flutter compatibility)
        url = '/api/v1/media/stream/${widget.mediaItem.uuid}';
        debugPrint('🎯 SmartVideoPlayer: Using realtime_only Media Service URL with overlay (fixed): $url');
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

  @override
  void dispose() {
    _videoController = null;
    super.dispose();
  }
}

/// Optimized Face Data Overlay for Workflow 5
/// Uses pre-processed face detection data for high-performance playback
class OptimizedFaceDataOverlay extends StatefulWidget {
  final VideoPlayerController? videoController;
  final List<FaceDetection> storedFaceData;
  final MediaItem mediaItem;

  const OptimizedFaceDataOverlay({
    super.key,
    this.videoController,
    required this.storedFaceData,
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
    
    // For now, show all stored faces since we don't have frame-specific data
    // TODO: Update when API provides frame-specific face data
    final currentFrameFaces = widget.storedFaceData;

    if (_currentFrameFaces.length != currentFrameFaces.length) {
      setState(() {
        _currentFrameFaces = currentFrameFaces;
      });
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
      child: CustomPaint(
        painter: OptimizedFacePainter(
          faces: _currentFrameFaces,
          videoSize: videoSize,
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

  OptimizedFacePainter({
    required this.faces,
    required this.videoSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (faces.isEmpty || videoSize.width == 0 || videoSize.height == 0) return;

    final paint = Paint()
      ..color = Colors.green.withValues(alpha: 0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    final textPainter = TextPainter(
      textDirection: TextDirection.ltr,
    );

    for (final face in faces) {
      final x = face.boundingBox.left * size.width / videoSize.width;
      final y = face.boundingBox.top * size.height / videoSize.height;
      final width = face.boundingBox.width * size.width / videoSize.width;
      final height = face.boundingBox.height * size.height / videoSize.height;

      final rect = Rect.fromLTWH(x, y, width, height);
      canvas.drawRect(rect, paint);

      // Draw confidence score if available
      final confidence = face.confidence;
      if (confidence > 0) {
        textPainter.text = TextSpan(
          text: '${(confidence * 100).toStringAsFixed(0)}%',
          style: const TextStyle(
            color: Colors.green,
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        );
        textPainter.layout();
        textPainter.paint(canvas, Offset(x, y - 16));
      }
    }
  }

  @override
  bool shouldRepaint(OptimizedFacePainter oldDelegate) {
    return faces != oldDelegate.faces || videoSize != oldDelegate.videoSize;
  }
}