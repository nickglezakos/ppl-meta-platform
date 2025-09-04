import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/offline_fonts.dart';
import 'package:go_router/go_router.dart';
import '../../core/models/camera.dart';
import '../../core/models/rtsp_camera.dart';
import '../../core/models/snapshot_result.dart';
import '../../core/providers/camera_providers.dart';
import '../../core/providers/multi_camera_providers.dart';
import '../../core/theme/app_theme.dart';
import '../../features/cameras/widgets/rtsp_camera_dialog.dart';
import '../../models/media_models.dart';
import '../../presentation/widgets/camera/camera_stream_player_simple.dart';

/// Enhanced camera card with integrated status monitoring
class CameraCard extends ConsumerWidget {
  final Camera camera;
  final bool showStream;

  const CameraCard({
    super.key,
    required this.camera,
    this.showStream = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      color: AppColors.widgetFill,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Camera header
            _buildCameraHeader(context, ref),
            
            if (showStream && (camera.isConnected || camera.isActive)) ...[
              const SizedBox(height: 16),
              _buildStreamSection(),
            ],
            
            const SizedBox(height: 16),
            _buildActionButtons(context, ref),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraHeader(BuildContext context, WidgetRef ref) {
    return Row(
      children: [
        // Camera icon
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: _getStatusColor(camera.status).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            Icons.camera_alt,
            color: _getStatusColor(camera.status),
            size: 24,
          ),
        ),
        
        const SizedBox(width: 16),
        
        // Camera info
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                camera.name,
                style: OfflineFonts.inter(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'ID: ${camera.deviceId}',
                style: OfflineFonts.inter(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 2),
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _getStatusColor(camera.status),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    camera.status.toUpperCase(),
                    style: OfflineFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: _getStatusColor(camera.status),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        
        // Camera specs
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            camera.resolution ?? 'Unknown',
            style: OfflineFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: AppColors.primary,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStreamSection() {
    return SizedBox(
      height: 240,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: CameraStreamPlayerSimple(
          cameraId: camera.deviceId,
          width: double.infinity,
          height: 240,
        ),
      ),
    );
  }

  Widget _buildActionButtons(BuildContext context, WidgetRef ref) {
    final cameraService = ref.read(cameraServiceProvider);
    final isConnected = camera.isConnected;
    final isRTSP = camera.type == CameraType.rtsp;
    
    return Column(
      children: [
        // Main action buttons row
        Row(
          children: [
            // Connect/Disconnect button
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () async {
                  try {
                    if (isConnected) {
                      await cameraService.disconnectCamera(camera.deviceId);
                    } else {
                      await cameraService.connectCamera(camera.deviceId);
                    }
                    // Refresh camera list
                    ref.read(cameraListProvider.notifier).loadCameras();
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Error: $e'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                },
                icon: Icon(
                  isConnected ? Icons.stop : Icons.play_arrow,
                  size: 16,
                ),
                label: Text(isConnected ? 'Disconnect' : 'Connect'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isConnected ? Colors.red : AppColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            
            const SizedBox(width: 12),
            
            // Snapshot button
            Expanded(
              child: ElevatedButton.icon(
                onPressed: isConnected ? () async {
                  try {
                    // Capture snapshot from camera
                    final result = await cameraService.captureSnapshot(camera.deviceId);
                    
                    // Auto-upload to media service and associate with camera collection
                    try {
                          final snapshotCollectionService = ref.read(snapshotCollectionServiceProvider);
                          await snapshotCollectionService.captureAndAssignToCollection(camera.deviceId, result);
                          debugPrint('✅ Snapshot uploaded successfully to camera collection');
                        } catch (uploadError) {
                          debugPrint('⚠️ Snapshot captured locally but upload failed: $uploadError');
                          // Continue to show success - local capture worked
                        }
                        
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: const Text('Snapshot captured successfully!'),
                              backgroundColor: Colors.green,
                              action: SnackBarAction(
                                label: 'View',
                                textColor: Colors.white,
                                onPressed: () {
                                  // Show snapshot preview dialog
                                  _showSnapshotPreview(context, result);
                                },
                              ),
                            ),
                          );
                        }
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('Snapshot failed: $e'),
                              backgroundColor: Colors.red,
                            ),
                          );
                        }
                      }
                    } : null,
                    icon: const Icon(Icons.camera_alt, size: 16),
                    label: const Text('Snapshot'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.secondary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                
                const SizedBox(width: 12),
                
                // Gallery button - Navigate to camera's collection
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      try {
                        final cameraCollectionService = ref.read(cameraCollectionServiceProvider);
                        
                        // Use camera's actual name for better collection matching
                        final collectionId = await cameraCollectionService.getCameraCollectionIdWithName(camera.deviceId, camera.name);
                        if (collectionId != null && context.mounted) {
                          print('🎯 Camera ${camera.name} (${camera.deviceId}) navigating to collection: $collectionId');
                          context.go('/collections?initialCollectionId=$collectionId');
                        } else if (context.mounted) {
                          // Fallback to general collections if no specific collection found
                          print('❌ No collection found for camera ${camera.name} (${camera.deviceId}), falling back to general collections');
                          context.go('/collections');
                        }
                      } catch (e) {
                        print('❌ Error getting collection for camera ${camera.name} (${camera.deviceId}): $e');
                        if (context.mounted) {
                          context.go('/collections');
                        }
                      }
                    },
                    icon: const Icon(Icons.folder, size: 16),
                    label: const Text('Collection'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.accent,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
            
            // RTSP Edit/Delete buttons row (only show for RTSP cameras)
            if (isRTSP) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  // Edit button
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _showEditRTSPDialog(context, ref),
                      icon: const Icon(Icons.edit, size: 16),
                      label: const Text('Edit'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                  
                  const SizedBox(width: 12),
                  
                  // Delete button
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _showDeleteRTSPDialog(context, ref),
                      icon: const Icon(Icons.delete, size: 16),
                      label: const Text('Delete'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        );
      }

      Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'connected':
        return Colors.green;
      case 'disconnected':
        return Colors.grey;
      case 'error':
        return Colors.red;
      case 'connecting':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  /// Show snapshot preview dialog
  void _showSnapshotPreview(BuildContext context, SnapshotResult snapshot) {
    // Convert SnapshotResult to MediaItem for consistent preview experience
    final mediaItem = _snapshotToMediaItem(snapshot);
    
    showDialog(
      context: context,
      builder: (context) => _SnapshotPreviewDialog(
        snapshot: snapshot,
        mediaItem: mediaItem,
      ),
    );
  }

  /// Convert SnapshotResult to MediaItem for preview dialog compatibility
  MediaItem _snapshotToMediaItem(SnapshotResult snapshot) {
    return MediaItem(
      mediaId: snapshot.id,
      uuid: snapshot.id,
      originalFilename: snapshot.filename ?? 'snapshot_${snapshot.capturedAt.millisecondsSinceEpoch}.jpg',
      mediaType: MediaType.image,
      fileSize: snapshot.fileSizeBytes ?? 0,
      filePath: 'snapshots/${snapshot.filename ?? snapshot.id}.jpg',
      uploadedAt: snapshot.capturedAt,
      isPublic: false,
      isArchived: false,
      tags: ['camera_snapshot', 'camera_${snapshot.deviceId}'],
      description: 'Camera snapshot from ${snapshot.deviceId}',
      technicalMetadata: {
        'camera_id': snapshot.deviceId,
        'capture_timestamp': snapshot.capturedAt.toIso8601String(),
        'source': 'camera_snapshot',
        ...?snapshot.metadata,
      },
      thumbnailUrl: snapshot.dataUrl,
      url: snapshot.dataUrl,
      deviceName: snapshot.deviceId,
    );
  }

  /// Show edit RTSP camera dialog
  void _showEditRTSPDialog(BuildContext context, WidgetRef ref) {
    // Convert Camera to RTSPCamera for editing
    final rtspCamera = RTSPCamera(
      id: camera.id.toString(),
      name: camera.name,
      host: camera.streamUrl?.replaceFirst('rtsp://', '')?.split('@').last.split('/').first ?? '',
      port: 554, // Default RTSP port
      username: '', // We don't store credentials in Camera model
      password: '',
      streamPath: camera.streamUrl?.split('/').last ?? '/stream',
      transport: RTSPTransport.tcp,
      profile: RTSPProfile.main,
    );

    showDialog(
      context: context,
      builder: (context) => RTSPCameraDialog(
        camera: rtspCamera,
        isEditing: true,
      ),
    ).then((result) {
      if (result == true) {
        // Refresh camera list after successful edit
        ref.read(cameraListProvider.notifier).loadCameras();
      }
    });
  }

  /// Show delete RTSP camera confirmation dialog
  void _showDeleteRTSPDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete RTSP Camera'),
        content: Text('Are you sure you want to delete "${camera.name}"?\n\nThis action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(context).pop();
              await _deleteRTSPCamera(context, ref);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  /// Delete RTSP camera
  Future<void> _deleteRTSPCamera(BuildContext context, WidgetRef ref) async {
    try {
      final cameraActions = ref.read(cameraActionsProvider);
      final success = await cameraActions.removeRTSPCamera(camera.deviceId);
      
      if (success && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('RTSP camera "${camera.name}" deleted successfully'),
            backgroundColor: Colors.green,
          ),
        );
        // Refresh camera list
        ref.read(cameraListProvider.notifier).loadCameras();
      } else if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to delete RTSP camera "${camera.name}"'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error deleting RTSP camera: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
}

/// Snapshot preview dialog - similar to MediaDetailsDialog but optimized for snapshots
class _SnapshotPreviewDialog extends StatelessWidget {
  final SnapshotResult snapshot;
  final MediaItem mediaItem;

  const _SnapshotPreviewDialog({
    required this.snapshot,
    required this.mediaItem,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Container(
        width: 600,
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.9,
          minHeight: 500,
        ),
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header
              Row(
                children: [
                  Icon(
                    Icons.camera_alt,
                    color: AppColors.primary,
                    size: 28,
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          snapshot.filename ?? 'Camera Snapshot',
                          style: AppTextStyles.h6,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          'CAMERA SNAPSHOT',
                          style: AppTextStyles.overline.copyWith(
                            color: AppColors.primary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Image preview
              Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  border: Border.all(color: AppColors.border),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  child: Image.memory(
                    snapshot.imageBytes,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        height: 200,
                        color: AppColors.gray100,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.broken_image,
                              size: 48,
                              color: AppColors.textTertiary,
                            ),
                            const SizedBox(height: AppSpacing.sm),
                            Text(
                              'Failed to load snapshot',
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: AppColors.textTertiary,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Metadata
              Text(
                'Details',
                style: AppTextStyles.labelLarge,
              ),
              const SizedBox(height: AppSpacing.sm),
              _MetadataRow(
                label: 'Camera',
                value: snapshot.deviceId,
              ),
              _MetadataRow(
                label: 'Captured',
                value: snapshot.formattedCaptureTime,
              ),
              _MetadataRow(
                label: 'File Size',
                value: snapshot.formattedFileSize,
              ),
              if (snapshot.metadata?.isNotEmpty == true) ...[
                const SizedBox(height: AppSpacing.md),
                Text(
                  'Technical Details',
                  style: AppTextStyles.labelLarge,
                ),
                const SizedBox(height: AppSpacing.sm),
                ...snapshot.metadata!.entries.map((entry) => 
                  _MetadataRow(
                    label: entry.key,
                    value: entry.value.toString(),
                  ),
                ),
              ],
              
              const SizedBox(height: AppSpacing.lg),
              
              // Actions
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        // TODO: Implement download functionality
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Download functionality coming soon!'),
                          ),
                        );
                      },
                      icon: const Icon(Icons.download),
                      label: const Text('Download'),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        // TODO: Implement share functionality
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Share functionality coming soon!'),
                          ),
                        );
                      },
                      icon: const Icon(Icons.share),
                      label: const Text('Share'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Simple metadata row widget
class _MetadataRow extends StatelessWidget {
  final String label;
  final String value;

  const _MetadataRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}
