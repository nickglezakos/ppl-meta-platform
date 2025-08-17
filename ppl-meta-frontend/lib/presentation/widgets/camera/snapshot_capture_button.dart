import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/snapshot_settings.dart';
import '../../../core/models/snapshot_result.dart';
import '../../../core/services/camera_service.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/services/snapshot_storage_service.dart';
import 'snapshot_settings_dialog.dart';

/// Enhanced snapshot capture button with settings support
class SnapshotCaptureButton extends ConsumerStatefulWidget {
  final String cameraId;
  final VoidCallback? onSnapshotCaptured;
  final bool showSettings;

  const SnapshotCaptureButton({
    super.key,
    required this.cameraId,
    this.onSnapshotCaptured,
    this.showSettings = true,
  });

  @override
  ConsumerState<SnapshotCaptureButton> createState() => _SnapshotCaptureButtonState();
}

class _SnapshotCaptureButtonState extends ConsumerState<SnapshotCaptureButton>
    with TickerProviderStateMixin {
  bool _isCapturing = false;
  CameraCapabilities? _capabilities;
  SnapshotSettings _currentSettings = const SnapshotSettings();
  
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  
  // Add storage service for Phase 1
  final SnapshotStorageService _storageService = SnapshotStorageService();

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 0.95,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));
    
    _loadCameraCapabilities();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  Future<void> _loadCameraCapabilities() async {
    try {
      final cameraService = ref.read(cameraServiceProvider);
      final capabilities = await cameraService.getCameraCapabilities(widget.cameraId);
      setState(() {
        _capabilities = capabilities;
      });
    } catch (e) {
      debugPrint('Failed to load camera capabilities: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Main capture button
        AnimatedBuilder(
          animation: _scaleAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: _scaleAnimation.value,
              child: GestureDetector(
                onTapDown: (_) => _animationController.forward(),
                onTapUp: (_) => _animationController.reverse(),
                onTapCancel: () => _animationController.reverse(),
                onTap: _isCapturing ? null : _captureQuickSnapshot,
                child: Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _isCapturing ? Colors.grey.shade400 : Colors.blue,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        blurRadius: 8,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: _isCapturing
                      ? const Center(
                          child: SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2,
                            ),
                          ),
                        )
                      : const Icon(
                          Icons.camera_alt,
                          color: Colors.white,
                          size: 28,
                        ),
                ),
              ),
            );
          },
        ),
        
        // Settings button (if enabled and capabilities loaded)
        if (widget.showSettings && _capabilities != null) ...[
          const SizedBox(width: 12),
          IconButton(
            onPressed: _isCapturing ? null : _showSettingsDialog,
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.9),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: const Icon(
                Icons.settings,
                size: 20,
                color: Colors.grey,
              ),
            ),
            tooltip: 'Snapshot Settings',
          ),
        ],
      ],
    );
  }

  Future<void> _captureQuickSnapshot() async {
    await _captureSnapshot(_currentSettings);
  }

  Future<void> _showSettingsDialog() async {
    if (_capabilities == null) return;

    final settings = await showSnapshotSettingsDialog(
      context,
      capabilities: _capabilities!,
      initialSettings: _currentSettings,
      onCapture: () {
        // This will be called when the dialog capture button is pressed
        _captureSnapshot(_currentSettings);
      },
    );

    if (settings != null) {
      setState(() {
        _currentSettings = settings;
      });
      await _captureSnapshot(settings);
    }
  }

  Future<void> _captureSnapshot(SnapshotSettings settings) async {
    if (_isCapturing) return;

    setState(() {
      _isCapturing = true;
    });

    try {
      final cameraService = ref.read(cameraServiceProvider);
      
      // Show capture feedback
      _showCaptureFlash();
      
      // Capture enhanced snapshot
      final result = await cameraService.captureEnhancedSnapshot(
        widget.cameraId,
        settings: settings,
      );

      // Convert enhanced result to basic snapshot result for Phase 1 storage
      final snapshotResult = SnapshotResult.fromBinary(
        deviceId: result.deviceId,
        base64Image: result.base64Image,
        filename: result.filename,
        metadata: {
          'resolution': result.resolution.toString(),
          'format': result.format,
          'quality': result.quality,
          'file_size': result.fileSizeBytes,
          'captured_at': result.capturedAt,
        },
      );

      debugPrint('💾 Saving snapshot for camera: ${widget.cameraId}');
      debugPrint('📁 Snapshot device ID: ${snapshotResult.deviceId}');
      debugPrint('🆔 Camera ID match: ${widget.cameraId == snapshotResult.deviceId}');

      // Save to local storage (Phase 1)
      final saved = await _storageService.saveSnapshot(snapshotResult);
      
      // 🚀 CAM-FLUTTER-004B: Automatic collection assignment and upload
      try {
        final snapshotCollectionService = ref.read(snapshotCollectionServiceProvider);
        await snapshotCollectionService.captureAndAssignToCollection(
          widget.cameraId,
          snapshotResult,
          additionalMetadata: {
            'enhanced_capture': true,
            'settings': {
              'resolution': settings.resolution,
              'quality': settings.quality,
              'format': settings.format,
            },
          },
        );
        debugPrint('✅ CAM-FLUTTER-004B: Automatic assignment completed for ${widget.cameraId}');
      } catch (e) {
        debugPrint('⚠️ CAM-FLUTTER-004B: Automatic assignment failed (non-critical): $e');
        // Don't fail the entire capture process if auto-upload fails
      }
      
      if (saved) {
        // Show success feedback with storage confirmation
        _showSuccessSnackBar(result, saved: true);
      } else {
        // Show success for capture but warn about storage
        _showSuccessSnackBar(result, saved: false);
      }
      
      // Notify callback
      widget.onSnapshotCaptured?.call();

    } catch (e) {
      // Show error feedback
      _showErrorSnackBar(e.toString());
    } finally {
      if (mounted) {
        setState(() {
          _isCapturing = false;
        });
      }
    }
  }

  void _showCaptureFlash() {
    // Create a flash effect overlay
    final overlay = Overlay.of(context);
    late OverlayEntry overlayEntry;
    
    overlayEntry = OverlayEntry(
      builder: (context) => Positioned.fill(
        child: AnimatedOpacity(
          opacity: 0.0,
          duration: const Duration(milliseconds: 100),
          child: Container(
            color: Colors.white,
          ),
        ),
      ),
    );
    
    overlay.insert(overlayEntry);
    
    // Flash animation
    Future.delayed(const Duration(milliseconds: 50), () {
      overlayEntry.markNeedsBuild();
    });
    
    Future.delayed(const Duration(milliseconds: 200), () {
      overlayEntry.remove();
    });
  }

  void _showSuccessSnackBar(EnhancedSnapshotResult result, {required bool saved}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    saved ? 'Snapshot Saved to Gallery!' : 'Snapshot Captured!',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  Text(
                    '${result.resolution} • ${result.formattedFileSize} • ${result.format}${!saved ? ' (Storage failed)' : ''}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
        backgroundColor: saved ? Colors.green : Colors.orange,
        duration: const Duration(seconds: 3),
        action: SnackBarAction(
          label: 'View',
          textColor: Colors.white,
          onPressed: () {
            _showSnapshotPreview(result);
          },
        ),
      ),
    );
  }

  void _showErrorSnackBar(String error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.error, color: Colors.white),
            const SizedBox(width: 8),
            Expanded(
              child: Text('Failed to capture snapshot: $error'),
            ),
          ],
        ),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: 'Retry',
          textColor: Colors.white,
          onPressed: _captureQuickSnapshot,
        ),
      ),
    );
  }

  void _showSnapshotPreview(EnhancedSnapshotResult result) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 600, maxHeight: 700),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(8),
                    topRight: Radius.circular(8),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.photo),
                    const SizedBox(width: 8),
                    Text(
                      result.filename,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              
              // Image
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  child: Image.memory(
                    _decodeBase64Image(result.base64Image),
                    fit: BoxFit.contain,
                  ),
                ),
              ),
              
              // Metadata
              Container(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _buildMetadataItem('Resolution', '${result.resolution}'),
                        ),
                        Expanded(
                          child: _buildMetadataItem('Size', result.formattedFileSize),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: _buildMetadataItem('Format', result.format),
                        ),
                        Expanded(
                          child: _buildMetadataItem('Quality', '${result.quality}%'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetadataItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Uint8List _decodeBase64Image(String base64String) {
    // Remove data URL prefix if present
    final base64Data = base64String.replaceFirst(RegExp(r'data:image/[^;]+;base64,'), '');
    return base64Decode(base64Data);
  }
}
