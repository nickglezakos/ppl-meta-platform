import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import 'dart:async';
import '../core/theme/app_theme.dart';

/// Video player widget with controls for displaying video content
class VideoPlayerWidget extends StatefulWidget {
  final String videoUrl;
  final Map<String, String>? headers;
  final Function(VideoPlayerController?)? onControllerReady;
  final String? collectionId; // Add collection ID to determine mobile camera source
  final Map<String, dynamic>? technicalMetadata; // Video metadata for playback correction
  final int? videoDuration; // Video duration in seconds

  const VideoPlayerWidget({
    super.key,
    required this.videoUrl,
    this.headers,
    this.onControllerReady,
    this.collectionId, // Make collection ID available
    this.technicalMetadata, // For calculating actual FPS
    this.videoDuration, // Duration from MediaItem
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
  
  // Playback monitoring variables
  Timer? _playbackMonitorTimer;
  DateTime? _playbackStartTime;
  Duration? _lastPosition;
  int _speedCheckCount = 0;

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
    
    // Cancel playback monitoring timer
    _playbackMonitorTimer?.cancel();
    _playbackMonitorTimer = null;
    
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
    
    String? videoUrl; // Declare outside try block for error logging
    
    try {
      // Debug: Log initial inputs
      debugPrint('🎥 VideoPlayerWidget._initializeVideo() started');
      debugPrint('🎥 Input URL: ${widget.videoUrl}');
      debugPrint('🎥 Input Headers: ${widget.headers}');
      
      // Check if this is an embedded streaming URL (no token conversion needed)
      if (widget.videoUrl.contains('/stream/video/')) {
        // Embedded streaming - ensure correct v1 API path to Gateway with authorization header
        final correctedPath = widget.videoUrl.startsWith('/api/v1/') 
            ? widget.videoUrl 
            : '/api/v1${widget.videoUrl.startsWith('/') ? widget.videoUrl : '/' + widget.videoUrl}';
        videoUrl = 'http://localhost:8080${correctedPath}';
        debugPrint('🎥 Detected GATEWAY embedded streaming URL: $videoUrl');
      } else {
        // All other media streaming - use token-based URL for web compatibility
        final authHeader = widget.headers?['Authorization'];
        if (authHeader != null && authHeader.startsWith('Bearer ')) {
          final token = authHeader.substring(7); // Remove 'Bearer ' prefix
          
          // Extract media ID from the URL path - handle both UUID and numeric formats
          // Match pattern: /stream/{uuid} or /stream/{uuid}?params
          final mediaIdMatch = RegExp(r'/stream/([a-f0-9\-]+)(?:\?|$)').firstMatch(widget.videoUrl);
          if (mediaIdMatch != null) {
            final mediaId = mediaIdMatch.group(1);
            // Preserve query parameters if present
            final queryStart = widget.videoUrl.indexOf('?');
            final existingParams = queryStart != -1 ? widget.videoUrl.substring(queryStart + 1) : '';
            
            if (existingParams.isNotEmpty) {
              videoUrl = 'http://localhost:8080/api/v1/media/stream-token/$mediaId?token=$token&$existingParams';
            } else {
              videoUrl = 'http://localhost:8080/api/v1/media/stream-token/$mediaId?token=$token';
            }
            debugPrint('🎥 Constructed token-based streaming URL: $videoUrl');
          } else {
            throw Exception('Could not extract media ID from URL: ${widget.videoUrl}');
          }
        } else {
          // Fall back to original URL construction
          videoUrl = widget.videoUrl.startsWith('/') 
              ? 'http://localhost:8080${widget.videoUrl}' 
              : widget.videoUrl;
          debugPrint('🎥 Detected FALLBACK URL: $videoUrl');
        }
      }
      
      // Use appropriate headers based on streaming type
      final httpHeaders = widget.videoUrl.contains('/stream/video/')
          ? widget.headers ?? {} // Embedded streaming uses Authorization header
          : <String, String>{}; // Token-based streaming doesn't need headers
      
      debugPrint('🎥 Final Video URL: $videoUrl');
      debugPrint('🎥 Final Headers: $httpHeaders');
      
      print('🎥 Initializing video player with URL: $videoUrl');
      print('🔑 Headers: ${widget.headers}');
      
      _controller = VideoPlayerController.networkUrl(
        Uri.parse(videoUrl),
        httpHeaders: httpHeaders,
      );

      // Create and store the listener
      _controllerListener = () {
        if (_isDisposed || !mounted) return;
        
        if (_controller!.value.hasError) {
          debugPrint('❌ VideoPlayerWidget ERROR DETECTED:');
          debugPrint('❌ Error Description: ${_controller!.value.errorDescription}');
          debugPrint('❌ Video URL: $videoUrl');
          debugPrint('❌ Headers Used: $httpHeaders');
          debugPrint('❌ Controller State: isInitialized=${_controller!.value.isInitialized}, hasError=${_controller!.value.hasError}');
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
      
      debugPrint('✅ VideoPlayerWidget INITIALIZATION SUCCESS:');
      debugPrint('✅ Video URL: $videoUrl');
      debugPrint('✅ Headers Used: $httpHeaders');
      debugPrint('✅ Duration: ${_controller!.value.duration}');
      debugPrint('✅ Size: ${_controller!.value.size}');
      debugPrint('✅ Initial Speed: ${_controller!.value.playbackSpeed}x');
      
      print('✅ Video initialized successfully');
      print('📹 Video info: ${_controller!.value.duration}, ${_controller!.value.size}');
      print('🎬 Initial playback speed: ${_controller!.value.playbackSpeed}x');
      
      // Mobile camera frame rate correction
      await _applyMobileCameraSpeedCorrection();
      
      print('🎬 Final playback speed: ${_controller!.value.playbackSpeed}x');
      
      // Start playback monitoring to detect speed issues
      _startPlaybackMonitoring();
      
      if (mounted && !_isDisposed) {
        setState(() {
          _isInitialized = true;
        });
        // Notify parent about controller availability
        widget.onControllerReady?.call(_controller);
      }
    } catch (e) {
      debugPrint('❌ VideoPlayerWidget INITIALIZATION EXCEPTION:');
      debugPrint('❌ Exception: $e');
      debugPrint('❌ Exception Type: ${e.runtimeType}');
      debugPrint('❌ Video URL: ${videoUrl ?? 'Unknown'}');
      debugPrint('❌ Input URL: ${widget.videoUrl}');
      debugPrint('❌ Headers: ${widget.headers}');
      
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

  /// Apply metadata-based playback speed correction
  /// Uses actual frame_count and duration from video metadata to calculate precise correction
  Future<void> _applyMobileCameraSpeedCorrection() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    
    try {
      print('📊 Applying metadata-based playback speed correction...');
      
      // Try to get metadata from widget parameters
      final metadata = widget.technicalMetadata;
      final duration = widget.videoDuration;
      
      if (metadata == null || duration == null || duration == 0) {
        print('⚠️ No metadata available for correction - using normal speed');
        await _controller!.setPlaybackSpeed(1.0);
        return;
      }
      
      // Extract total frames from metadata
      final totalFrames = metadata['total_frames'] as int?;
      final frameRate = metadata['frame_rate'] as num? ?? metadata['fps'] as num?;
      
      if (totalFrames == null || totalFrames == 0) {
        print('⚠️ No frame count in metadata - using normal speed');
        await _controller!.setPlaybackSpeed(1.0);
        return;
      }
      
      // Calculate actual FPS from metadata
      final durationSeconds = duration.toDouble();
      final actualFps = totalFrames / durationSeconds;
      
      // Get declared FPS (what the video claims)
      final declaredFps = (frameRate?.toDouble() ?? 30.0);
      
      // Calculate correction factor
      // If video has more frames than it should (e.g., 37 FPS written but claims 30 FPS),
      // we need to slow down: correction = declaredFps / actualFps
      final correction = declaredFps / actualFps;
      
      print('📊 Metadata-based correction:');
      print('   Total frames: $totalFrames');
      print('   Duration: ${durationSeconds.toStringAsFixed(2)}s');
      print('   Actual FPS: ${actualFps.toStringAsFixed(2)}');
      print('   Declared FPS: $declaredFps');
      print('   Correction factor: ${correction.toStringAsFixed(4)}x');
      
      // Only apply correction if it's significantly different from 1.0
      // (avoid correcting videos that don't need it)
      if ((correction - 1.0).abs() > 0.02) {
        await _controller!.setPlaybackSpeed(correction);
        print('✅ Applied playback speed correction: ${correction.toStringAsFixed(4)}x');
      } else {
        await _controller!.setPlaybackSpeed(1.0);
        print('✅ Video frame rate matches declared rate - no correction needed');
      }
      
    } catch (e) {
      print('⚠️ Error applying metadata-based speed correction: $e');
      // Fallback to normal speed if correction fails
      await _controller?.setPlaybackSpeed(1.0);
    }
  }
  
  /// Start monitoring playback speed to detect timing issues
  void _startPlaybackMonitoring() {
    if (_controller == null) return;
    
    print('⏱️ Starting playback speed monitoring...');
    _playbackMonitorTimer?.cancel();
    
    _playbackMonitorTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (_controller == null || !_controller!.value.isInitialized || _isDisposed) {
        timer.cancel();
        return;
      }
      
      _speedCheckCount++;
      final currentPosition = _controller!.value.position;
      final now = DateTime.now();
      
      if (_playbackStartTime == null && _controller!.value.isPlaying) {
        _playbackStartTime = now;
        _lastPosition = currentPosition;
        print('⏱️ Playback started - monitoring initialized');
        return;
      }
      
      if (_playbackStartTime != null && _lastPosition != null && _controller!.value.isPlaying) {
        final realTimeElapsed = now.difference(_playbackStartTime!).inMilliseconds / 1000.0;
        final videoTimeElapsed = (currentPosition.inMilliseconds - _lastPosition!.inMilliseconds) / 1000.0;
        
        if (realTimeElapsed > 0.1) { // Avoid division by zero
          final actualPlaybackSpeed = videoTimeElapsed / realTimeElapsed;
          final expectedSpeed = _controller!.value.playbackSpeed;
          final speedRatio = actualPlaybackSpeed / expectedSpeed;
          
          print('⏱️ Playback monitoring (#$_speedCheckCount):');
          print('   Real time elapsed: ${realTimeElapsed.toStringAsFixed(2)}s');
          print('   Video time elapsed: ${videoTimeElapsed.toStringAsFixed(2)}s');
          print('   Actual playback speed: ${actualPlaybackSpeed.toStringAsFixed(3)}x');
          print('   Expected speed: ${expectedSpeed.toStringAsFixed(3)}x');
          print('   Speed ratio: ${speedRatio.toStringAsFixed(3)}x');
          
          if (speedRatio > 1.2) {
            print('🚨 FAST PLAYBACK DETECTED! Video playing ${speedRatio.toStringAsFixed(2)}x faster than expected!');
          } else if (speedRatio < 0.8) {
            print('🐌 SLOW PLAYBACK DETECTED! Video playing ${speedRatio.toStringAsFixed(2)}x slower than expected!');
          }
          
          _playbackStartTime = now;
          _lastPosition = currentPosition;
        }
      }
      
      // Stop monitoring after 30 seconds to avoid spam
      if (_speedCheckCount >= 15) {
        print('⏱️ Playback monitoring completed after ${_speedCheckCount} checks');
        timer.cancel();
      }
    });
  }
}
