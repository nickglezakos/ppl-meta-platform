import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/media_api_client.dart';
import '../models/api_models.dart';
import '../core/providers/features_providers.dart';
import '../providers/face_data_providers.dart';

/// Face detection overlay for static images
/// Overlays yellow rectangles on detected faces in static images
class FaceDetectionOverlay extends ConsumerStatefulWidget {
  final Widget child;
  final Uint8List? imageBytes;
  final double confidenceThreshold;

  const FaceDetectionOverlay({
    super.key,
    required this.child,
    this.imageBytes,
    this.confidenceThreshold = 0.5,
  });

  @override
  ConsumerState<FaceDetectionOverlay> createState() => _FaceDetectionOverlayState();
}

class _FaceDetectionOverlayState extends ConsumerState<FaceDetectionOverlay> {
  List<FaceDetection> _detectedFaces = [];
  bool _isProcessing = false;
  Size? _imageSize;

  @override
  void initState() {
    super.initState();
    _processImage();
  }

  @override
  void didUpdateWidget(FaceDetectionOverlay oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.imageBytes != oldWidget.imageBytes) {
      _processImage();
    }
  }

  Future<void> _processImage() async {
    if (widget.imageBytes == null || !mounted) return;
    
    final features = ref.read(featuresProvider);
    if (!features.visionCapability || !features.faceDetectionEnabled) return;

    setState(() {
      _isProcessing = true;
      _detectedFaces = [];
    });

    try {
      // Note: Static image face detection temporarily disabled
      // Focus is on video face detection through Orchestrator providers
      debugPrint('🖼️ Static image face detection: Using Orchestrator session-based system');
      
      // For now, mark as no faces detected
      setState(() {
        _detectedFaces = [];
      });
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

  @override
  Widget build(BuildContext context) {
    final features = ref.watch(featuresProvider);
    
    return Stack(
      children: [
        // Original image
        widget.child,
        
        // Face detection overlay
        if (features.visionCapability && features.faceDetectionEnabled)
          Positioned.fill(
            child: CustomPaint(
              painter: StaticFaceDetectionPainter(
                faces: _detectedFaces,
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
        
        // Face count indicator
        if (_detectedFaces.isNotEmpty)
          Positioned(
            top: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.yellow.withOpacity(0.9),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                '${_detectedFaces.length} face${_detectedFaces.length == 1 ? '' : 's'}',
                style: TextStyle(
                  color: Colors.black,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// Custom painter for drawing face detection rectangles on static images
class StaticFaceDetectionPainter extends CustomPainter {
  final List<FaceDetection> faces;

  StaticFaceDetectionPainter({
    required this.faces,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (faces.isEmpty) return;

    // Paint for face rectangles
    final paint = Paint()
      ..color = Colors.green
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    for (final face in faces) {
      // Use face coordinates directly (assuming they're already scaled for display)
      final bbox = face.boundingBox;
      final rect = Rect.fromLTWH(
        bbox.left,
        bbox.top,
        bbox.width,
        bbox.height,
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
  bool shouldRepaint(StaticFaceDetectionPainter oldDelegate) {
    return faces != oldDelegate.faces;
  }
}
