import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../../../shared/navigation/app_navigation.dart';
import '../../../services/app_logger.dart';

/// Camera controls widget with capture, flash, zoom, and gallery
class CameraControls extends StatefulWidget {
  final VoidCallback onCapturePhoto;
  final VoidCallback onSwitchCamera;
  final VoidCallback onToggleFlash;
  final Function(double) onZoomChanged;
  final VoidCallback onOpenGallery;
  final VoidCallback onVideoTap; // NEW: Video icon handler for simplified streaming
  final bool isFlashOn;
  final double zoomLevel;
  final bool isFrontCamera;
  final int galleryItemCount;

  const CameraControls({
    Key? key,
    required this.onCapturePhoto,
    required this.onSwitchCamera,
    required this.onToggleFlash,
    required this.onZoomChanged,
    required this.onOpenGallery,
    required this.onVideoTap, // NEW: Video icon handler
    required this.isFlashOn,
    required this.zoomLevel,
    required this.isFrontCamera,
    required this.galleryItemCount,
  }) : super(key: key);

  @override
  State<CameraControls> createState() => _CameraControlsState();
}

class _CameraControlsState extends State<CameraControls>
    with TickerProviderStateMixin {
  late AnimationController _captureAnimationController;
  late AnimationController _zoomAnimationController;
  bool _showZoomSlider = false;

  @override
  void initState() {
    super.initState();
    _captureAnimationController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _zoomAnimationController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
  }

  @override
  void dispose() {
    _captureAnimationController.dispose();
    _zoomAnimationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [
            Colors.black.withOpacity(0.8),
            Colors.transparent,
          ],
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Zoom Slider
          _buildZoomSlider(),
          
          const SizedBox(height: 16),
          
          // Main Controls Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              // Gallery Button
              _buildGalleryButton(),
              
              // Video Button (NEW: Simplified streaming workflow)
              _buildVideoButton(),
              
              // Capture Button
              _buildCaptureButton(),
              
              // Switch Camera Button
              _buildSwitchCameraButton(),
            ],
          ),
          
          const SizedBox(height: 20),
          
          // Secondary Controls Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              // Flash Toggle
              _buildFlashButton(),
              
              // Zoom Button
              _buildZoomButton(),
              
              // Timer Button (Future feature)
              _buildTimerButton(),
              
              // Aspect Ratio Button (Future feature)
              _buildAspectRatioButton(),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildZoomSlider() {
    return AnimatedBuilder(
      animation: _zoomAnimationController,
      builder: (context, child) {
        if (!_showZoomSlider) {
          return const SizedBox.shrink();
        }
        
        return Transform.scale(
          scale: _zoomAnimationController.value,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.7),
              borderRadius: BorderRadius.circular(25),
              border: Border.all(
                color: Colors.white.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Column(
              children: [
                Text(
                  '${widget.zoomLevel.toStringAsFixed(1)}x',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: 200,
                  child: SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      activeTrackColor: Theme.of(context).colorScheme.primary,
                      inactiveTrackColor: Colors.white.withOpacity(0.3),
                      thumbColor: Theme.of(context).colorScheme.primary,
                      overlayColor: Theme.of(context).colorScheme.primary.withOpacity(0.2),
                      trackHeight: 4,
                      thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
                    ),
                    child: Slider(
                      value: widget.zoomLevel,
                      min: 1.0,
                      max: 8.0,
                      divisions: 70,
                      onChanged: widget.onZoomChanged,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildGalleryButton() {
    return GestureDetector(
      onTap: () => AppNavigation.toGallery(context),
      child: Container(
        width: 50,
        height: 50,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 2,
          ),
        ),
        child: Stack(
          children: [
            const Center(
              child: Icon(
                Icons.photo_library,
                color: Colors.white,
                size: 24,
              ),
            ),
            if (widget.galleryItemCount > 0)
              Positioned(
                top: 2,
                right: 2,
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(
                    color: Colors.red,
                    shape: BoxShape.circle,
                  ),
                  constraints: const BoxConstraints(
                    minWidth: 16,
                    minHeight: 16,
                  ),
                  child: Text(
                    widget.galleryItemCount > 99 
                        ? '99+' 
                        : widget.galleryItemCount.toString(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildVideoButton() {
    return GestureDetector(
      onTap: () {
        CameraLogger.setup('Red video button tapped!');
        CameraLogger.setup('Calling onVideoTap callback...');
        if (widget.onVideoTap != null) {
          widget.onVideoTap!();
          CameraLogger.setup('onVideoTap callback executed');
        } else {
          CameraLogger.error('onVideoTap callback is null!');
        }
      },
      child: Container(
        width: 50,
        height: 50,
        decoration: BoxDecoration(
          color: Colors.red.withOpacity(0.8),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 2,
          ),
        ),
        child: const Center(
          child: Icon(
            Icons.videocam,
            color: Colors.white,
            size: 24,
          ),
        ),
      ),
    );
  }

  Widget _buildCaptureButton() {
    return GestureDetector(
      onTap: () => _handleCapture(),
      child: AnimatedBuilder(
        animation: _captureAnimationController,
        builder: (context, child) {
          final scale = 1.0 - (_captureAnimationController.value * 0.1);
          
          return Transform.scale(
            scale: scale,
            child: Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white,
                  width: 4,
                ),
              ),
              child: Container(
                margin: const EdgeInsets.all(8),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.camera_alt,
                  color: Colors.black,
                  size: 32,
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSwitchCameraButton() {
    return GestureDetector(
      onTap: widget.onSwitchCamera,
      child: Container(
        width: 50,
        height: 50,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 2,
          ),
        ),
        child: Icon(
          widget.isFrontCamera 
              ? Icons.camera_front 
              : Icons.camera_rear,
          color: Colors.white,
          size: 24,
        ),
      ),
    );
  }

  Widget _buildFlashButton() {
    return GestureDetector(
      onTap: widget.onToggleFlash,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: widget.isFlashOn 
              ? Theme.of(context).colorScheme.primary
              : Colors.white.withOpacity(0.2),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 1,
          ),
        ),
        child: Icon(
          widget.isFlashOn ? Icons.flash_on : Icons.flash_off,
          color: Colors.white,
          size: 20,
        ),
      ),
    );
  }

  Widget _buildZoomButton() {
    return GestureDetector(
      onTap: _toggleZoomSlider,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: _showZoomSlider 
              ? Theme.of(context).colorScheme.primary
              : Colors.white.withOpacity(0.2),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 1,
          ),
        ),
        child: const Icon(
          Icons.zoom_in,
          color: Colors.white,
          size: 20,
        ),
      ),
    );
  }

  Widget _buildTimerButton() {
    return GestureDetector(
      onTap: () {
        // Future: Timer functionality
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Timer feature coming soon!'),
            duration: Duration(seconds: 2),
          ),
        );
      },
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 1,
          ),
        ),
        child: const Icon(
          Icons.timer,
          color: Colors.white,
          size: 20,
        ),
      ),
    );
  }

  Widget _buildAspectRatioButton() {
    return GestureDetector(
      onTap: () {
        // Future: Aspect ratio functionality
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Aspect ratio feature coming soon!'),
            duration: Duration(seconds: 2),
          ),
        );
      },
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withOpacity(0.5),
            width: 1,
          ),
        ),
        child: const Icon(
          Icons.aspect_ratio,
          color: Colors.white,
          size: 20,
        ),
      ),
    );
  }

  void _handleCapture() {
    _captureAnimationController.forward().then((_) {
      _captureAnimationController.reverse();
    });
    widget.onCapturePhoto();
  }

  void _toggleZoomSlider() {
    setState(() {
      _showZoomSlider = !_showZoomSlider;
    });
    
    if (_showZoomSlider) {
      _zoomAnimationController.forward();
      // Auto-hide after 5 seconds
      Future.delayed(const Duration(seconds: 5), () {
        if (_showZoomSlider) {
          _toggleZoomSlider();
        }
      });
    } else {
      _zoomAnimationController.reverse();
    }
  }
}
