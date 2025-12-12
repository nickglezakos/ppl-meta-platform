import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/offline_fonts.dart';
import 'package:go_router/go_router.dart';
import 'dart:convert';
import '../../core/models/camera.dart';
import '../../core/models/rtsp_camera.dart';
import '../../core/models/snapshot_result.dart';
import '../../core/providers/camera_providers.dart';
import '../../core/providers/multi_camera_providers.dart';
import '../../core/theme/app_theme.dart';
import '../../features/cameras/widgets/rtsp_camera_dialog.dart';
import '../../models/api_models.dart';
import '../../models/media_models.dart';
import '../../presentation/widgets/camera/camera_stream_player_simple.dart';
import '../../providers/workflow_providers.dart';
import '../../models/workflow_widget_models.dart';
import '../../services/orchestrator_api_client.dart';
import '../../services/media_api_client.dart';
import 'camera_counter_widget.dart';
import 'instant_detection_widget.dart';

/// Enhanced camera card with integrated status monitoring
class CameraCard extends ConsumerStatefulWidget {
  final Camera camera;
  final bool showStream;

  const CameraCard({
    super.key,
    required this.camera,
    this.showStream = false,
  });

  @override
  ConsumerState<CameraCard> createState() => _CameraCardState();
}

class _CameraCardState extends ConsumerState<CameraCard> {
  // REMOVED: Old counter logic (_mvrPeopleCount, _isLoadingCount, _fetchMVRPeopleCount)
  // Counter is now handled by separate CameraCounterWidget

  @override
  Widget build(BuildContext context) {
    final isMobile = widget.camera.type == CameraType.mobile || widget.camera.isMobileCamera;
    
    return Card(
      margin: EdgeInsets.zero,
      elevation: 4,
      child: Column(  // Changed from Padding to Column for separate widget
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Camera header
                _buildCameraHeader(context, ref),
            
                if (widget.showStream && (widget.camera.isConnected || widget.camera.isActive)) ...[
                  const SizedBox(height: 16),
                  _buildStreamSection(),
                ],
            
                const SizedBox(height: 16),
                _buildActionButtons(context, ref),
              ],
            ),
          ),
          
          // NEW: Separate counter widget (outside camera card padding)
          CameraCounterWidget(
            cameraId: widget.camera.deviceId,
            refreshInterval: const Duration(minutes: 5),
          ),
          
          // NEW: Instant detection widget (real-time face detection)
          InstantDetectionWidget(
            cameraId: widget.camera.deviceId,
            refreshInterval: const Duration(seconds: 3),
          ),
        ],
      ),
    );
  }

  Widget _buildCameraHeader(BuildContext context, WidgetRef ref) {
    final isMobile = widget.camera.type == CameraType.mobile || widget.camera.isMobileCamera;
    
    return Row(
      children: [
        // Camera icon
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: _getStatusColor(widget.camera.status).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            isMobile ? Icons.smartphone : Icons.camera_alt,
            color: _getStatusColor(widget.camera.status),
            size: 24,
          ),
        ),
        
        const SizedBox(width: 16),
        
        // Camera info
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.camera.name,
                      style: OfflineFonts.inter(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  if (isMobile) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: Colors.blue.withOpacity(0.3)),
                      ),
                      child: Text(
                        'MOBILE',
                        style: OfflineFonts.inter(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: Colors.blue.shade700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                  ],
                  // REMOVED: Counter badge moved to separate CameraCounterWidget below
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'ID: ${widget.camera.deviceId}',
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
                      color: _getStatusColor(widget.camera.status),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    widget.camera.status.toUpperCase(),
                    style: OfflineFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: _getStatusColor(widget.camera.status),
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
            widget.camera.resolution ?? 'Unknown',
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

  // REMOVED: _buildDetectedPersonsCounter() - Now using separate CameraCounterWidget

  Widget _buildStreamSection() {
    final isMobile = widget.camera.type == CameraType.mobile || widget.camera.isMobileCamera;
    
    return SizedBox(
      height: isMobile ? 320 : 240, // Taller container for mobile cameras to accommodate portrait aspect ratio
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Container(
          color: Colors.black, // Black background to show letterboxing clearly
          child: CameraStreamPlayerSimple(
            cameraId: widget.camera.deviceId,
            width: double.infinity,
            height: isMobile ? 320 : 240,
          ),
        ),
      ),
    );
  }

  Widget _buildActionButtons(BuildContext context, WidgetRef ref) {
    final cameraService = ref.read(cameraServiceProvider);
    final isConnected = widget.camera.isConnected;
    final isRTSP = widget.camera.type == CameraType.rtsp;
    final isMobile = widget.camera.type == CameraType.mobile || widget.camera.isMobileCamera;
    
    return Column(
      children: [
        // Main action buttons row
        Row(
          children: [
            // Connect/Disconnect button (now available for all camera types including mobile)
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () async {
                  try {
                    if (isConnected) {
                      await cameraService.disconnectCamera(widget.camera.deviceId);
                    } else {
                      await cameraService.connectCamera(widget.camera.deviceId);
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
                  isConnected ? Icons.stop : (isMobile ? Icons.smartphone : Icons.play_arrow),
                  size: 16,
                ),
                label: Text(isConnected ? 'Disconnect' : 'Connect'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isConnected ? Colors.red : (isMobile ? Colors.blue : AppColors.primary),
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
                    final result = await cameraService.captureSnapshot(widget.camera.deviceId);
                    
                    // Auto-upload to media service and associate with camera collection
                    try {
                          final snapshotCollectionService = ref.read(snapshotCollectionServiceProvider);
                          await snapshotCollectionService.captureAndAssignToCollection(widget.camera.deviceId, result);
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
                        final collectionId = await cameraCollectionService.getCameraCollectionIdWithName(widget.camera.deviceId, widget.camera.name);
                        if (collectionId != null && context.mounted) {
                          print('🎯 Camera ${widget.camera.name} (${widget.camera.deviceId}) navigating to collection: $collectionId');
                          context.go('/collections?initialCollectionId=$collectionId');
                        } else if (context.mounted) {
                          // Fallback to general collections if no specific collection found
                          print('❌ No collection found for camera ${widget.camera.name} (${widget.camera.deviceId}), falling back to general collections');
                          context.go('/collections');
                        }
                      } catch (e) {
                        print('❌ Error getting collection for camera ${widget.camera.name} (${widget.camera.deviceId}): $e');
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
            
            // Recording controls (show if camera supports recording and is connected)
            if (isConnected && _cameraSupportsRecording()) ...[
              const SizedBox(height: 8),
              _buildRecordingControls(ref),
            ],
            
            // Phase 2: Face Detection Workflow Controls
            if (isConnected) ...[
              const SizedBox(height: 8),
              _buildWorkflowControls(context, ref),
            ],
            
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

      /// Check if camera supports recording
      bool _cameraSupportsRecording() {
        // Check metadata first for explicit supports_recording flag
        if (widget.camera.metadata?['supports_recording'] == true) {
          return true;
        }
        
        // USB cameras typically support recording
        if (widget.camera.type == CameraType.usb) {
          return true;
        }
        
        // Mobile cameras support recording (H.264 codec)
        if (widget.camera.type == CameraType.mobile || widget.camera.isMobileCamera) {
          return true;
        }
        
        // RTSP cameras support recording (same as USB cameras, direct stream recording)
        if (widget.camera.type == CameraType.rtsp) {
          return true;
        }
        
        // For now, be conservative and only enable for USB, mobile, and RTSP cameras
        return false;
      }

      /// Build recording controls for the camera
      Widget _buildRecordingControls(WidgetRef ref) {
        final recordingState = ref.watch(cameraRecordingProvider(widget.camera.deviceId));
        final recordingNotifier = ref.read(cameraRecordingProvider(widget.camera.deviceId).notifier);

        return Row(
          children: [
            // Recording status and controls
            Expanded(
              flex: 2,
              child: recordingState.isRecording
                ? _buildRecordingActiveControls(recordingState, recordingNotifier)
                : _buildRecordingStartControl(recordingState, recordingNotifier),
            ),
            
            const SizedBox(width: 12),
            
            // Recording status info
            if (recordingState.isRecording)
              Expanded(
                flex: 1,
                child: _buildRecordingStatusInfo(recordingState),
              ),
          ],
        );
      }

      /// Build controls when recording is active
      Widget _buildRecordingActiveControls(CameraRecordingState recordingState, CameraRecordingNotifier recordingNotifier) {
        return ElevatedButton.icon(
          onPressed: recordingState.isLoading ? null : () => recordingNotifier.stopRecording(),
          icon: recordingState.isLoading
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildPulsingDot(),
                  const SizedBox(width: 4),
                  const Icon(Icons.stop_circle, size: 16),
                ],
              ),
          label: Text(recordingState.isLoading ? 'Stopping...' : 'Stop Recording'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 12),
          ),
        );
      }

      /// Build controls when recording is not active
      Widget _buildRecordingStartControl(CameraRecordingState recordingState, CameraRecordingNotifier recordingNotifier) {
        return ElevatedButton.icon(
          onPressed: recordingState.isLoading ? null : () => recordingNotifier.startRecording(),
          icon: recordingState.isLoading
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.fiber_manual_record, size: 16),
          label: Text(recordingState.isLoading ? 'Starting...' : 'Start Recording'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red.shade700,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 12),
          ),
        );
      }

      /// Build recording status information
      Widget _buildRecordingStatusInfo(CameraRecordingState recordingState) {
        final duration = Duration(seconds: recordingState.durationSeconds);
        final minutes = duration.inMinutes;
        final seconds = duration.inSeconds % 60;
        final fileSize = (recordingState.fileSizeBytes / (1024 * 1024)).toStringAsFixed(1);

        return Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.red.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.red.withOpacity(0.3)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Recording: ${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
              Text(
                'Size: ${fileSize}MB',
                style: const TextStyle(fontSize: 10),
              ),
            ],
          ),
        );
      }

      /// Build pulsing red dot for recording indicator
      Widget _buildPulsingDot() {
        return TweenAnimationBuilder<double>(
          duration: const Duration(milliseconds: 1000),
          tween: Tween(begin: 0.3, end: 1.0),
          builder: (context, value, child) {
            return Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(value),
                shape: BoxShape.circle,
              ),
            );
          },
          onEnd: () {
            // This will cause the animation to repeat
          },
        );
      }

      /// Build face detection workflow controls - Phase 2 Enhancement
      Widget _buildWorkflowControls(BuildContext context, WidgetRef ref) {
        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.05),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.primary.withOpacity(0.2)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Workflow section header
              Row(
                children: [
                  Icon(
                    Icons.face_retouching_natural,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Face Detection Workflows',
                    style: OfflineFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.primary,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 8),
              
              // Workflow action buttons
              Row(
                children: [
                  // Start workflow button
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _startFaceDetectionWorkflow(context, ref),
                      icon: const Icon(Icons.play_arrow, size: 16),
                      label: const Text('Start Detection'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                  
                  const SizedBox(width: 8),
                  
                  // Workflow status button
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _showWorkflowStatus(context, ref),
                      icon: const Icon(Icons.analytics, size: 16),
                      label: const Text('View Status'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.secondary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      }

            /// Start face detection workflow for camera recordings
      Future<void> _startFaceDetectionWorkflow(BuildContext context, WidgetRef ref) async {
        try {
          // Show method selection dialog
          final selectedMethod = await _showDetectionMethodDialog(context);
          if (selectedMethod == null) return; // User cancelled
          
          // Always default to two_stage if somehow null is returned
          final method = selectedMethod == 'null' ? 'two_stage' : selectedMethod;
          
          // Show loading indicator
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Row(
                  children: [
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    ),
                    SizedBox(width: 12),
                    Text('Starting face detection workflow...'),
                  ],
                ),
                backgroundColor: AppColors.primary,
                duration: Duration(seconds: 10),
              ),
            );
          }

          // Get orchestrator API client
          final orchestratorClient = ref.read(orchestratorApiClientProvider);
          
          // Instead of using generic workflow creation, use the specific bulk-process endpoint
          // First get recent media files from this camera to process
          final mediaClient = ref.read(mediaApiClientProvider);
          final mediaResponse = await mediaClient.searchMedia(
            query: widget.camera.name,
            mediaType: MediaType.video,
            limit: 5, // Get last 5 videos from this camera
          );

          List<String> mediaIds = [];
          if (mediaResponse.success && mediaResponse.data != null) {
            // Get media IDs from recent recordings
            mediaIds = mediaResponse.data!.items
                .where((media) => media.originalFilename?.contains(widget.camera.deviceId) == true)
                .take(3) // Process last 3 recordings
                .map((media) => media.uuid)
                .toList();
          }

          if (mediaIds.isEmpty) {
            if (context.mounted) {
              ScaffoldMessenger.of(context).clearSnackBars();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('No recent recordings found for this camera. Please record some video first.'),
                  backgroundColor: AppColors.warning,
                ),
              );
            }
            return;
          }

          // Create bulk processing request directly using HTTP client
          try {
            final response = await orchestratorClient.client.post(
              Uri.parse('${orchestratorClient.config.baseUrl}/workflows/face-detection/bulk-process'),
              headers: {
                'Content-Type': 'application/json',
                // Note: In a real implementation, you'd get the auth token from a proper auth provider
              },
              body: json.encode({
                'media_ids': mediaIds,
                'methods': [method], // Use the validated method
                'processing_options': {
                  'confidence_threshold': 0.7,
                  'store_results': true,
                },
                'priority': 'normal',
              }),
            );

            if (response.statusCode == 200 && context.mounted) {
              // Success - refresh workflow status and show success message
              ref.invalidate(activeWorkflowsProvider);
              
              final responseData = json.decode(response.body);
              final workflowId = responseData['workflow_id'];
              
              ScaffoldMessenger.of(context).clearSnackBars();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Face detection workflow started! Processing ${mediaIds.length} videos.'),
                  backgroundColor: AppColors.success,
                  action: SnackBarAction(
                    label: 'View Status',
                    textColor: Colors.white,
                    onPressed: () => _showWorkflowStatus(context, ref),
                  ),
                ),
              );
            } else if (context.mounted) {
              // Error - show error message
              ScaffoldMessenger.of(context).clearSnackBars();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Failed to start workflow: ${response.statusCode}'),
                  backgroundColor: AppColors.error,
                ),
              );
            }
          } catch (e) {
            if (context.mounted) {
              ScaffoldMessenger.of(context).clearSnackBars();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Network error: $e'),
                  backgroundColor: AppColors.error,
                ),
              );
            }
          }
        } catch (e) {
          if (context.mounted) {
            ScaffoldMessenger.of(context).clearSnackBars();
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Failed to start workflow: $e'),
                backgroundColor: AppColors.error,
              ),
            );
          }
        }
      }

      /// Show detection method selection dialog
      Future<String?> _showDetectionMethodDialog(BuildContext context) {
        return showDialog<String>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Select Detection Method'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Choose a face detection method:'),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.auto_awesome),
                  title: const Text('Two-Stage Detection'),
                  subtitle: const Text('Best accuracy - Haar + DLib validation (Recommended)'),
                  onTap: () => Navigator.of(context).pop('two_stage'),
                  tileColor: Colors.blue.shade50,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                    side: BorderSide(color: Colors.blue.shade200),
                  ),
                ),
                const SizedBox(height: 8),
                ListTile(
                  leading: const Icon(Icons.speed),
                  title: const Text('Haar Cascade'),
                  subtitle: const Text('Fast, good for real-time detection'),
                  onTap: () => Navigator.of(context).pop('haar'),
                ),
                ListTile(
                  leading: const Icon(Icons.precision_manufacturing),
                  title: const Text('MTCNN'),
                  subtitle: const Text('High accuracy, multi-stage detection'),
                  onTap: () => Navigator.of(context).pop('mtcnn'),
                ),
                ListTile(
                  leading: const Icon(Icons.high_quality),
                  title: const Text('DLib'),
                  subtitle: const Text('Reliable detection with landmarks'),
                  onTap: () => Navigator.of(context).pop('dlib'),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(context).pop('two_stage'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                ),
                child: const Text('Use Recommended'),
              ),
            ],
          ),
        );
      }

      /// Show workflow status for camera
      Future<void> _showWorkflowStatus(BuildContext context, WidgetRef ref) async {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text('Workflow Status - ${widget.camera.name}'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Camera: ${widget.camera.name}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text('Device ID: ${widget.camera.deviceId}'),
                const SizedBox(height: 16),
                const Text(
                  'Active Workflows:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                
                // Use activeWorkflowsProvider to show real workflow status
                Consumer(
                  builder: (context, ref, child) {
                    final workflowsAsync = ref.watch(activeWorkflowsProvider);
                    
                    return workflowsAsync.when(
                      data: (workflows) {
                        if (workflows.isEmpty) {
                          return Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.grey[100],
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Text(
                              'No active workflows found.\n\nStart a face detection workflow to see status here.',
                              style: TextStyle(fontStyle: FontStyle.italic),
                            ),
                          );
                        } else {
                          // Show active workflows
                          return Column(
                            children: workflows.map((workflow) => Container(
                              margin: const EdgeInsets.only(bottom: 8),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: _getWorkflowStatusColor(workflow.status),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    _getWorkflowStatusIcon(workflow.status),
                                    size: 20,
                                    color: Colors.white,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          workflow.name,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            color: Colors.white,
                                          ),
                                        ),
                                        Text(
                                          'Status: ${workflow.status.name}',
                                          style: const TextStyle(
                                            color: Colors.white70,
                                            fontSize: 12,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            )).toList(),
                          );
                        }
                      },
                      loading: () => const Center(
                        child: CircularProgressIndicator(),
                      ),
                      error: (error, stack) => Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.red[50],
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          'Error loading workflows: ${error.toString()}',
                          style: TextStyle(
                            color: Colors.red[700],
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Close'),
              ),
              ElevatedButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  _startFaceDetectionWorkflow(context, ref);
                },
                child: const Text('Start Workflow'),
              ),
            ],
          ),
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

  /// Get color for workflow status
  Color _getWorkflowStatusColor(WorkflowStatus status) {
    switch (status) {
      case WorkflowStatus.running:
        return Colors.blue;
      case WorkflowStatus.completed:
        return Colors.green;
      case WorkflowStatus.failed:
        return Colors.red;
      case WorkflowStatus.cancelled:
        return Colors.orange;
      case WorkflowStatus.pending:
      default:
        return Colors.grey;
    }
  }

  /// Get icon for workflow status
  IconData _getWorkflowStatusIcon(WorkflowStatus status) {
    switch (status) {
      case WorkflowStatus.running:
        return Icons.sync;
      case WorkflowStatus.completed:
        return Icons.check_circle;
      case WorkflowStatus.failed:
        return Icons.error;
      case WorkflowStatus.cancelled:
        return Icons.cancel;
      case WorkflowStatus.pending:
      default:
        return Icons.schedule;
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
      id: widget.camera.id.toString(),
      name: widget.camera.name,
      host: widget.camera.streamUrl?.replaceFirst('rtsp://', '').split('@').last.split('/').first ?? '',
      port: 554, // Default RTSP port
      username: '', // We don't store credentials in Camera model
      password: '',
      streamPath: widget.camera.streamUrl?.split('/').last ?? '/stream',
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
        content: Text('Are you sure you want to delete "${widget.camera.name}"?\n\nThis action cannot be undone.'),
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
      final success = await cameraActions.removeRTSPCamera(widget.camera.deviceId);
      
      if (success && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('RTSP camera "${widget.camera.name}" deleted successfully'),
            backgroundColor: Colors.green,
          ),
        );
        // Refresh camera list
        ref.read(cameraListProvider.notifier).loadCameras();
      } else if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to delete RTSP camera "${widget.camera.name}"'),
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
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Download functionality coming soon!'),
                            ),
                          );
                        }
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
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Share functionality coming soon!'),
                            ),
                          );
                        }
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
