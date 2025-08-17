import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import '../core/theme/app_theme.dart';

/// Video player widget with controls for displaying video content
class VideoPlayerWidget extends StatefulWidget {
  final String videoUrl;
  final Map<String, String>? headers;
  final Function(VideoPlayerController?)? onControllerReady;

  const VideoPlayerWidget({
    super.key,
    required this.videoUrl,
    this.headers,
    this.onControllerReady,
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
}
