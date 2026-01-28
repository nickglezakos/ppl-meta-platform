import 'package:flutter/material.dart';
import 'package:camera/camera.dart';

/// Camera preview widget with overlay and tap-to-focus
class CameraPreviewWidget extends StatelessWidget {
  final CameraController? controller;
  final bool isInitialized;
  final Function(TapUpDetails)? onTap;
  final String? error;

  const CameraPreviewWidget({
    Key? key,
    required this.controller,
    required this.isInitialized,
    this.onTap,
    this.error,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // Check if controller is ready and initialized
    if (controller == null || !controller!.value.isInitialized) {
      return _buildPlaceholder();
    }

    return GestureDetector(
      onTapUp: onTap,
      child: Stack(
        children: [
          // Camera Preview - Use BoxFit.contain to show entire frame with black bars
          Positioned.fill(
            child: ClipRect(
              child: OverflowBox(
                alignment: Alignment.center,
                child: FittedBox(
                  fit: BoxFit.contain,
                  child: SizedBox(
                    width: controller!.value.previewSize?.height ?? 1,
                    height: controller!.value.previewSize?.width ?? 1,
                    child: CameraPreview(controller!),
                  ),
                ),
              ),
            ),
          ),
          
          // Preview Overlay
          _buildPreviewOverlay(),
          
          // Grid Lines (optional)
          _buildGridLines(),
        ],
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              error != null ? Icons.camera_alt_outlined : Icons.camera_alt_outlined,
              size: 100,
              color: error != null ? Colors.red.withOpacity(0.7) : Colors.white54,
            ),
            const SizedBox(height: 20),
            Text(
              error != null 
                  ? 'Camera Error'
                  : (isInitialized ? 'Starting Camera...' : 'Initializing Camera...'),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 12),
            if (error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32.0),
                child: Text(
                  error!,
                  style: const TextStyle(
                    color: Colors.red,
                    fontSize: 14,
                  ),
                  textAlign: TextAlign.center,
                ),
              )
            else
              const CircularProgressIndicator(
                color: Colors.white54,
                strokeWidth: 2,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreviewOverlay() {
    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          border: Border.all(
            color: Colors.white.withOpacity(0.3),
            width: 2,
          ),
        ),
        child: Stack(
          children: [
            // Corner Indicators
            _buildCornerIndicators(),
            
            // Center Focus Indicator
            _buildCenterFocus(),
          ],
        ),
      ),
    );
  }

  Widget _buildCornerIndicators() {
    const double size = 20;
    const double thickness = 3;
    const Color color = Colors.white;

    return Stack(
      children: [
        // Top Left
        Positioned(
          top: 20,
          left: 20,
          child: Container(
            width: size,
            height: size,
            decoration: const BoxDecoration(
              border: Border(
                top: BorderSide(color: color, width: thickness),
                left: BorderSide(color: color, width: thickness),
              ),
            ),
          ),
        ),
        
        // Top Right
        Positioned(
          top: 20,
          right: 20,
          child: Container(
            width: size,
            height: size,
            decoration: const BoxDecoration(
              border: Border(
                top: BorderSide(color: color, width: thickness),
                right: BorderSide(color: color, width: thickness),
              ),
            ),
          ),
        ),
        
        // Bottom Left
        Positioned(
          bottom: 20,
          left: 20,
          child: Container(
            width: size,
            height: size,
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: color, width: thickness),
                left: BorderSide(color: color, width: thickness),
              ),
            ),
          ),
        ),
        
        // Bottom Right
        Positioned(
          bottom: 20,
          right: 20,
          child: Container(
            width: size,
            height: size,
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: color, width: thickness),
                right: BorderSide(color: color, width: thickness),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCenterFocus() {
    return Center(
      child: Container(
        width: 60,
        height: 60,
        decoration: BoxDecoration(
          border: Border.all(
            color: Colors.white.withOpacity(0.6),
            width: 2,
          ),
          shape: BoxShape.circle,
        ),
        child: Container(
          margin: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.3),
            shape: BoxShape.circle,
          ),
        ),
      ),
    );
  }

  Widget _buildGridLines() {
    return Positioned.fill(
      child: CustomPaint(
        painter: GridPainter(),
      ),
    );
  }
}

/// Custom painter for grid lines (rule of thirds)
class GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.3)
      ..strokeWidth = 1;

    // Vertical lines
    final verticalSpacing = size.width / 3;
    for (int i = 1; i < 3; i++) {
      final x = verticalSpacing * i;
      canvas.drawLine(
        Offset(x, 0),
        Offset(x, size.height),
        paint,
      );
    }

    // Horizontal lines
    final horizontalSpacing = size.height / 3;
    for (int i = 1; i < 3; i++) {
      final y = horizontalSpacing * i;
      canvas.drawLine(
        Offset(0, y),
        Offset(size.width, y),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
