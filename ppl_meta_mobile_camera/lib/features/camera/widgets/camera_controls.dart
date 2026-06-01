import 'package:flutter/material.dart';
import '../../../services/app_logger.dart';

/// Camera controls widget with capture, flash, zoom, and gallery
class CameraControls extends StatefulWidget {
  final VoidCallback onCapturePhoto;
  final VoidCallback onSwitchCamera;
  final VoidCallback onToggleFlash;
  final Function(double) onZoomChanged;
  final VoidCallback onVideoTap; // NEW: Video icon handler for simplified streaming
  final VoidCallback onPresenceQrTap;
  final VoidCallback onPresenceCameraTap;
  final VoidCallback onPresenceVerifiedTap;
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
    required this.onVideoTap, // NEW: Video icon handler
    required this.onPresenceQrTap,
    required this.onPresenceCameraTap,
    required this.onPresenceVerifiedTap,
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

  @override
  void initState() {
    super.initState();
    _captureAnimationController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
  }

  @override
  void dispose() {
    _captureAnimationController.dispose();
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
          // Main Controls Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              // Snapshot Button (smaller, left)
              _buildSnapshotButton(),
              
              // Video Button (center - streaming)
              _buildVideoButton(),
              
              // Switch Camera Button (right)
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
              
              // Presence QR button
              _buildPresenceQrButton(),
              
              // Presence Camera button
              _buildPresenceCameraButton(),
              
              // Combined Presence button
              _buildPresenceVerifiedButton(),
            ],
          ),
        ],
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

  Widget _buildSnapshotButton() {
    return GestureDetector(
      onTap: () => _handleCapture(),
      child: AnimatedBuilder(
        animation: _captureAnimationController,
        builder: (context, child) {
          final scale = 1.0 - (_captureAnimationController.value * 0.1);
          
          return Transform.scale(
            scale: scale,
            child: Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.9),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white,
                  width: 2,
                ),
              ),
              child: const Icon(
                Icons.camera_alt,
                color: Colors.black,
                size: 24,
              ),
            ),
          );
        },
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
      onTap: widget.onPresenceCameraTap,
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
          Icons.videocam,
          color: Colors.white,
          size: 20,
        ),
      ),
    );
  }

  Widget _buildPresenceQrButton() {
    return GestureDetector(
      onTap: widget.onPresenceQrTap,
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
          Icons.qr_code_scanner,
          color: Colors.white,
          size: 20,
        ),
      ),
    );
  }

  Widget _buildPresenceCameraButton() {
    return _buildZoomButton();
  }

  Widget _buildPresenceVerifiedButton() {
    return GestureDetector(
      onTap: widget.onPresenceVerifiedTap,
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
          Icons.verified_user,
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
}
