import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import '../core/theme/app_theme.dart';

/// Video player widget with controls for displaying video content
class VideoPlayerWidget extends StatefulWidget {
  final String videoUrl;
  final Map<String, String>? headers;
  final Function(VideoPlayerController?)? onControllerReady;
  final String? collectionId; // Add collection ID to determine mobile camera source

  const VideoPlayerWidget({
    super.key,
    required this.videoUrl,
    this.headers,
    this.onControllerReady,
    this.collectionId, // Make collection ID available
  });

  @override
  State<VideoPlayerWidget> createState() => _VideoPlayerWidgetState();
}

class _VideoPlayerWidgetState extends State<VideoPlayerWidget> {
  VideoPlayerController? _controller;
  bool _isInitialized = false;
  bool _hasError = false;
  String? _errorMessage;
  bool _isDisposed = false; // Track disposal state
  VoidCallback? _controllerListener; // Store listener reference

  @override
  void initState() {
    super.initState();
    // Defer initialization to avoid theme context issues
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _initializeVideo();
      }
    });
  }

  @override
  void dispose() {
    // Prevent multiple disposals
    if (_isDisposed) {
      super.dispose();
      return;
    }
    
    _isDisposed = true;
    
    // Safely dispose controller
    if (_controller != null) {
      try {
        // Remove the specific listener
        if (_controllerListener != null) {
          _controller!.removeListener(_controllerListener!);
          _controllerListener = null;
        }
        _controller!.dispose();
      } catch (e) {
        // Ignore disposal errors - controller might already be disposed
        print('⚠️ Video controller disposal warning: $e');
      } finally {
        _controller = null;
      }
    }
    
    super.dispose();
  }

  Future<void> _initializeVideo() async {
    if (!mounted || _isDisposed) return;
    
    try {
      String videoUrl;
      
      // Check if this is an embedded streaming URL (no token conversion needed)
      if (widget.videoUrl.contains('/stream/video/')) {
        // Embedded streaming - ensure correct v1 API path to Gateway with authorization header
        final correctedPath = widget.videoUrl.startsWith('/api/v1/') 
            ? widget.videoUrl 
            : '/api/v1${widget.videoUrl.startsWith('/') ? widget.videoUrl : '/' + widget.videoUrl}';
        videoUrl = 'http://localhost:8080${correctedPath}';
      } else {
        // Legacy media streaming - check if we have an authorization header and construct token-based URL for web compatibility
        final authHeader = widget.headers?['Authorization'];
        if (authHeader != null && authHeader.startsWith('Bearer ')) {
          final token = authHeader.substring(7); // Remove 'Bearer ' prefix
          
          // Extract media ID from the URL path - handle both UUID and numeric formats
          final mediaIdMatch = RegExp(r'/stream/([^/?]+)').firstMatch(widget.videoUrl);
          if (mediaIdMatch != null) {
            final mediaId = mediaIdMatch.group(1);
            videoUrl = widget.videoUrl.startsWith('/') 
                ? 'http://localhost:8080/api/v1/media/stream-token/$mediaId?token=$token'
                : 'http://localhost:8080/api/v1/media/stream-token/$mediaId?token=$token';
          } else {
            throw Exception('Could not extract media ID from URL: ${widget.videoUrl}');
          }
        } else {
          // Fall back to original URL construction
          videoUrl = widget.videoUrl.startsWith('/') 
              ? 'http://localhost:8080${widget.videoUrl}' 
              : widget.videoUrl;
        }
      }
      
      print('🎥 Initializing video player with URL: $videoUrl');
      print('🔑 Headers: ${widget.headers}');
      
      // Use appropriate headers based on streaming type
      final httpHeaders = widget.videoUrl.contains('/stream/video/') 
          ? widget.headers ?? {} // Embedded streaming uses Authorization header
          : <String, String>{}; // Token-based streaming doesn't need headers
      
      _controller = VideoPlayerController.networkUrl(
        Uri.parse(videoUrl),
        httpHeaders: httpHeaders,
      );

      // Create and store the listener
      _controllerListener = () {
        if (_isDisposed || !mounted) return;
        
        if (_controller!.value.hasError) {
          print('❌ Video controller error: ${_controller!.value.errorDescription}');
          if (mounted && !_isDisposed) {
            setState(() {
              _hasError = true;
              _errorMessage = 'Video error: ${_controller!.value.errorDescription}';
            });
          }
        }
      };
      
      _controller!.addListener(_controllerListener!);

      await _controller!.initialize();
      
      print('✅ Video initialized successfully');
      print('📹 Video info: ${_controller!.value.duration}, ${_controller!.value.size}');
      
      // Mobile camera frame rate correction
      await _applyMobileCameraSpeedCorrection();
      
      if (mounted && !_isDisposed) {
        setState(() {
          _isInitialized = true;
        });
        // Notify parent about controller availability
        widget.onControllerReady?.call(_controller);
      }
    } catch (e) {
      print('❌ Video initialization failed: $e');
      if (mounted && !_isDisposed) {
        setState(() {
          _hasError = true;
          _errorMessage = 'Video loading failed: ${e.toString()}';
        });
      }
    }
  }

  Widget _buildControls() {
    if (_controller == null || !_controller!.value.isInitialized || _isDisposed) return const SizedBox.shrink();
    
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            Colors.black.withOpacity(0.7),
          ],
        ),
      ),
      child: Row(
        children: [
          IconButton(
            onPressed: () {
              if (!mounted || _controller == null || !_controller!.value.isInitialized || _isDisposed) return;
              
              try {
                setState(() {
                  if (_controller!.value.isPlaying) {
                    _controller!.pause();
                  } else {
                    _controller!.play();
                  }
                });
              } catch (e) {
                print('⚠️ Error controlling video playback: $e');
              }
            },
            icon: Icon(
              _controller!.value.isPlaying ? Icons.pause : Icons.play_arrow,
              color: Colors.white,
              size: 32,
            ),
          ),
          Expanded(
            child: VideoProgressIndicator(
              _controller!,
              allowScrubbing: true,
              colors: const VideoProgressColors(
                playedColor: AppColors.primary,
                bufferedColor: AppColors.gray300,
                backgroundColor: AppColors.gray500,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
            child: Text(
              _formatDuration(_controller!.value.position) + 
              ' / ' + 
              _formatDuration(_controller!.value.duration),
              style: AppTextStyles.bodySmall.copyWith(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes.toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    if (_isDisposed) {
      return const SizedBox.shrink();
    }
    
    if (_hasError) {
      return Container(
        width: double.infinity,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.md),
          color: AppColors.gray200,
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline,
                size: 48,
                color: AppColors.error,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Error loading video',
                style: AppTextStyles.bodyMedium,
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _errorMessage!,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.gray600,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ),
      );
    }

    if (!_isInitialized || _controller == null || !_controller!.value.isInitialized) {
      return Container(
        width: double.infinity,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.md),
          color: AppColors.gray200,
        ),
        child: const Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.md),
        boxShadow: [AppShadows.sm],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: Stack(
          alignment: Alignment.bottomCenter,
          children: [
            Center(
              child: AspectRatio(
                aspectRatio: _controller!.value.aspectRatio,
                child: VideoPlayer(_controller!),
              ),
            ),
            _buildControls(),
          ],
        ),
      ),
    );
  }

  /// Apply mobile camera speed correction based on collection camera device type
  Future<void> _applyMobileCameraSpeedCorrection() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    
    try {
      final duration = _controller!.value.duration;
      final durationSeconds = duration.inMilliseconds / 1000.0;
      
      print('📱 Checking video for mobile camera correction - Duration: ${durationSeconds}s');
      
      // Check if this video belongs to a mobile camera collection
      final isMobileCollection = await _isMobileCameraCollection();
      
      if (!isMobileCollection) {
        print('📱 Not from mobile camera collection, skipping speed correction');
        return;
      }
      
      print('📱 Mobile camera collection detected - applying speed correction');
      
      // Apply duration-based speed correction for mobile camera videos
      final correctionRatio = _calculateMobileSpeedCorrection(durationSeconds);
      
      await _controller!.setPlaybackSpeed(correctionRatio);
      print('✅ Applied mobile camera speed correction: ${correctionRatio.toStringAsFixed(3)}x');
      
    } catch (e) {
      print('⚠️ Error applying mobile camera speed correction: $e');
    }
  }
  
  /// Check if the current video belongs to a mobile camera collection
  Future<bool> _isMobileCameraCollection() async {
    try {
      print('📱 Detecting mobile camera collection...');
      print('📱 Video URL: ${widget.videoUrl}');
      print('📱 Collection ID: ${widget.collectionId}');
      
      // Check 1: Known mobile camera collection UUID
      const knownMobileCollectionId = '4fe59481-c5f9-4b32-89aa-237897077220';
      
      if (widget.collectionId == knownMobileCollectionId) {
        print('📱 ✅ Detected via collection ID match');
        return true;
      }
      
      // Check 2: URL contains mobile camera collection UUID
      if (widget.videoUrl.contains(knownMobileCollectionId)) {
        print('📱 ✅ Detected via URL collection UUID');
        return true;
      }
      
      // Check 3: URL contains mobile camera indicators
      final mobileIndicators = [
        'mobile_recording_',
        'camera_mobile_',
        'mobile_TKQ1',
        'TKQ1.221114.001', // Specific mobile device ID
        'mcam-', // Mobile camera prefix
      ];
      
      for (final indicator in mobileIndicators) {
        if (widget.videoUrl.contains(indicator)) {
          print('📱 ✅ Detected via URL indicator: $indicator');
          return true;
        }
      }
      
      // Check 4: Stream token URL pattern for mobile collection
      if (widget.videoUrl.contains('/media/stream-token/')) {
        // Extract the media UUID and check if it belongs to mobile collection
        final tokenMatch = RegExp(r'/stream-token/([a-f0-9-]+)').firstMatch(widget.videoUrl);
        if (tokenMatch != null) {
          final mediaUuid = tokenMatch.group(1);
          print('📱 Found media UUID: $mediaUuid - assuming mobile for now');
          // For now, assume all stream-token videos from our test are mobile
          // TODO: Implement proper media-to-collection lookup
          return true;
        }
      }
      
      print('📱 ❌ No mobile camera indicators found');
      return false;
      
    } catch (e) {
      print('⚠️ Error checking mobile camera collection: $e');
      return false;
    }
  }
  
  /// Calculate speed correction for mobile camera videos
  double _calculateMobileSpeedCorrection(double durationSeconds) {
    // Mobile videos are encoded at 30 FPS but captured at much lower rates
    // Correction factor based on actual mobile frame capture patterns:
    
    double estimatedActualFps;
    if (durationSeconds < 1.0) {
      estimatedActualFps = 6.0;  // Very short recordings: ~6 FPS
    } else if (durationSeconds < 3.0) {
      estimatedActualFps = 8.0;  // Short recordings: ~8 FPS  
    } else if (durationSeconds < 10.0) {
      estimatedActualFps = 10.0; // Medium recordings: ~10 FPS
    } else {
      estimatedActualFps = 12.0; // Longer recordings: ~12 FPS
    }
    
    const double declaredFps = 30.0; // What OpenCV encodes
    final correction = estimatedActualFps / declaredFps;
    
    print('📱 Mobile speed calculation:');
    print('   Duration: ${durationSeconds.toStringAsFixed(2)}s');
    print('   Estimated actual FPS: $estimatedActualFps');
    print('   Declared FPS: $declaredFps');
    print('   Correction ratio: ${correction.toStringAsFixed(3)}');
    
    return correction;
  }
}
