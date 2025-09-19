import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../services/vision_api_client.dart';
import '../services/media_api_client.dart';
import '../models/api_models.dart';
import '../core/providers/features_providers.dart';
import '../core/providers/features_provider.dart';
import '../core/theme/app_theme.dart';

/// Real-time face detection overlay for video content
/// Overlays yellow rectangles on detected faces during video playback
class VideoFaceDetectionOverlay extends ConsumerStatefulWidget {
  final Widget child;
  final VideoPlayerController controller;
  final double confidenceThreshold;

  const VideoFaceDetectionOverlay({
    super.key,
    required this.child,
    required this.controller,
    this.confidenceThreshold = 0.5,
  });

  @override
  ConsumerState<VideoFaceDetectionOverlay> createState() => _VideoFaceDetectionOverlayState();
}

class _VideoFaceDetectionOverlayState extends ConsumerState<VideoFaceDetectionOverlay> {
  Timer? _detectionTimer;
  List<FaceDetection> _detectedFaces = [];
  final Map<int, List<FaceDetection>> _frameCache = {};
  bool _isProcessing = false;
  Size? _videoSize;
  
  @override
  void initState() {
    super.initState();
    _initializeDetection();
  }

  @override
  void dispose() {
    _detectionTimer?.cancel();
    super.dispose();
  }

  void _initializeDetection() {
    // Start detection loop when video is playing
    widget.controller.addListener(_onVideoStateChanged);
    if (widget.controller.value.isPlaying) {
      _startDetectionLoop();
    }
  }

  void _onVideoStateChanged() {
    if (widget.controller.value.isPlaying && _detectionTimer == null) {
      _startDetectionLoop();
    } else if (!widget.controller.value.isPlaying) {
      _stopDetectionLoop();
    }
    
    // Update video size
    if (widget.controller.value.isInitialized && widget.controller.value.size != Size.zero) {
      setState(() {
        _videoSize = widget.controller.value.size;
      });
    }
  }

  void _startDetectionLoop() {
    _detectionTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      _processCurrentFrame();
    });
  }

  void _stopDetectionLoop() {
    _detectionTimer?.cancel();
    _detectionTimer = null;
  }

  Future<void> _processCurrentFrame() async {
    if (_isProcessing || !widget.controller.value.isInitialized || !mounted) return;
    
    final features = ref.read(featuresProvider);
    if (!features.visionCapability || !features.faceDetectionEnabled) return;

    setState(() {
      _isProcessing = true;
    });

    try {
      // Get current video position for caching
      final position = widget.controller.value.position.inMilliseconds;
      final cacheKey = (position / 1000).round(); // Cache by second

      // Check cache first
      if (_frameCache.containsKey(cacheKey)) {
        setState(() {
          _detectedFaces = _frameCache[cacheKey]!;
          _isProcessing = false;
        });
        return;
      }

      // Extract current frame
      final frameBytes = await _extractCurrentFrame();
      if (frameBytes == null || !mounted) return;

      // Send to Vision service
      final visionClient = VisionApiClient();
      final base64Image = base64Encode(frameBytes);
      final result = await visionClient.detectFaces(
        imageBase64: base64Image,
        confidenceThreshold: widget.confidenceThreshold,
      );
      
      if (result != null && mounted) {
        // Filter by confidence threshold
        final filteredFaces = result.faces
            .where((face) => face.confidence >= widget.confidenceThreshold)
            .toList();

        setState(() {
          _detectedFaces = filteredFaces;
          _frameCache[cacheKey] = filteredFaces; // Cache result
        });

        // Limit cache size
        if (_frameCache.length > 50) {
          final oldestKey = _frameCache.keys.first;
          _frameCache.remove(oldestKey);
        }
      }
    } catch (e) {
      debugPrint('⚠️ Face detection error: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  Future<Uint8List?> _extractCurrentFrame() async {
    try {
      // Get the RenderRepaintBoundary from the video player
      final boundary = context.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) return null;

      // Capture the current frame
      final image = await boundary.toImage(pixelRatio: 1.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      
      return byteData?.buffer.asUint8List();
    } catch (e) {
      debugPrint('⚠️ Frame extraction error: $e');
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final features = ref.watch(featuresProvider);
    
    return RepaintBoundary(
      child: Stack(
        children: [
          // Original video player
          widget.child,
          
          // Face detection overlay
          if (features.visionCapability && features.faceDetectionEnabled)
            Positioned.fill(
              child: CustomPaint(
                painter: FaceDetectionPainter(
                  faces: _detectedFaces,
                  videoSize: _videoSize ?? Size.zero,
                ),
              ),
            ),
          
          // Processing indicator
          if (_isProcessing)
            Positioned(
              top: 8,
              left: 8,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.yellow),
                      ),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Detecting faces...',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Custom painter for drawing face detection rectangles
class FaceDetectionPainter extends CustomPainter {
  final List<FaceDetection> faces;
  final Size videoSize;

  FaceDetectionPainter({
    required this.faces,
    required this.videoSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (faces.isEmpty || videoSize == Size.zero) return;

    // Calculate video display area within container (handle letterbox/pillarbox)
    final videoAspectRatio = videoSize.width / videoSize.height;
    final containerAspectRatio = size.width / size.height;
    
    double actualVideoWidth, actualVideoHeight, offsetX = 0, offsetY = 0;
    
    if (videoAspectRatio > containerAspectRatio) {
      // Horizontal letterbox - video fills width
      actualVideoWidth = size.width;
      actualVideoHeight = size.width / videoAspectRatio;
      offsetY = (size.height - actualVideoHeight) / 2;
    } else {
      // Vertical pillarbox - video fills height  
      actualVideoWidth = size.height * videoAspectRatio;
      actualVideoHeight = size.height;
      offsetX = (size.width - actualVideoWidth) / 2;
    }

    // Calculate scaling factors
    final scaleX = actualVideoWidth / videoSize.width;
    final scaleY = actualVideoHeight / videoSize.height;

    // Paint for face rectangles
    final paint = Paint()
      ..color = Colors.yellow
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    // Paint for confidence labels
    final textPaint = Paint()..color = Colors.yellow;
    
    for (final face in faces) {
      // Transform face coordinates to display coordinates
      final bbox = face.boundingBox;
      final rect = Rect.fromLTWH(
        (bbox.left * scaleX) + offsetX,
        (bbox.top * scaleY) + offsetY,
        bbox.width * scaleX,
        bbox.height * scaleY,
      );

      // Draw face rectangle
      canvas.drawRect(rect, paint);

      // Draw confidence score
      final textSpan = TextSpan(
        text: '${(face.confidence * 100).toInt()}%',
        style: TextStyle(
          color: Colors.yellow,
          fontSize: 12,
          fontWeight: FontWeight.bold,
          shadows: [
            Shadow(
              offset: Offset(1, 1),
              blurRadius: 2,
              color: Colors.black54,
            ),
          ],
        ),
      );

      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      );
      
      textPainter.layout();
      textPainter.paint(
        canvas, 
        Offset(rect.left, rect.top - textPainter.height - 2),
      );
    }
  }

  @override
  bool shouldRepaint(FaceDetectionPainter oldDelegate) {
    return faces != oldDelegate.faces || videoSize != oldDelegate.videoSize;
  }
}
