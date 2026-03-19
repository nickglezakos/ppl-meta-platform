import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/models/camera.dart';
import '../../../core/providers/multi_camera_providers.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../presentation/widgets/camera/camera_stream_player.dart';
import '../../../presentation/widgets/camera/streaming_controls.dart';

/// Camera streaming page with proven streaming components
class CameraStreamingPage extends ConsumerStatefulWidget {
  final Camera camera;

  const CameraStreamingPage({
    super.key,
    required this.camera,
  });

  @override
  ConsumerState<CameraStreamingPage> createState() => _CameraStreamingPageState();
}

class _CameraStreamingPageState extends ConsumerState<CameraStreamingPage> {
  bool _isStreaming = false;
  String? _streamingError;

  @override
  void initState() {
    super.initState();
    // Auto-start streaming when page opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startStreaming();
    });
  }

  @override
  void dispose() {
    // Stop streaming when leaving page
    if (_isStreaming) {
      _stopStreaming();
    }
    super.dispose();
  }

  Future<void> _startStreaming() async {
    print('🎬🎬🎬 [STREAMING_PAGE_V3] _startStreaming called for camera: ${widget.camera.id} 🎬🎬🎬');
    print('🎬 [VERIFY] This is camera_streaming_page.dart with UNIQUE DEBUG V3!');
    try {
      setState(() {
        _streamingError = null;
      });

      final cameraActions = ref.read(cameraActionsProvider);
      print('🎬 [STREAMING_PAGE_V3] Calling cameraActions.startStreaming()...');
      final streamingInfo = await cameraActions.startStreaming(widget.camera.id);
      
      if (streamingInfo != null) {
        setState(() {
          _isStreaming = true;
        });
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Camera streaming started'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        setState(() {
          _streamingError = 'Failed to start streaming';
        });
      }
    } catch (e) {
      setState(() {
        _streamingError = 'Error starting streaming: $e';
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to start streaming: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _stopStreaming() async {
    try {
      final cameraActions = ref.read(cameraActionsProvider);
      await cameraActions.stopStreaming(widget.camera.id);
      
      setState(() {
        _isStreaming = false;
      });
      
      // Also update the stream provider state
      final streamNotifier = ref.read(cameraStreamProvider.notifier);
      streamNotifier.stopStreaming();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Camera streaming stopped'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _streamingError = 'Error stopping streaming: $e';
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to stop streaming: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _takeSnapshot() async {
    try {
      final cameraActions = ref.read(cameraActionsProvider);
      final snapshot = await cameraActions.takeSnapshot(widget.camera.id);
      
      if (snapshot != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Snapshot saved: ${snapshot.filename}'),
            backgroundColor: Colors.blue,
          ),
        );
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to take snapshot'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Snapshot error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final streamingInfo = ref.watch(cameraStreamingInfoProvider(widget.camera.id));
    
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.camera.name),
            Text(
              widget.camera.deviceId,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        actions: [
          // Connection status indicator
          Icon(
            widget.camera.isConnected ? Icons.circle : Icons.circle_outlined,
            color: widget.camera.isConnected ? Colors.green : Colors.grey,
            size: 16,
          ),
          const SizedBox(width: 8),
          Text(
            widget.camera.isConnected ? 'Connected' : 'Disconnected',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: widget.camera.isConnected ? Colors.green : Colors.grey,
            ),
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: Column(
        children: [
          // Main streaming area
          Expanded(
            flex: 3,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              child: Card(
                elevation: 4,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: _buildStreamingArea(),
                ),
              ),
            ),
          ),
          
          // Controls area
          Expanded(
            flex: 1,
            child: Container(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Main control buttons
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      // Start/Stop streaming
                      ElevatedButton.icon(
                        onPressed: _isStreaming ? _stopStreaming : _startStreaming,
                        icon: Icon(
                          _isStreaming ? Icons.stop : Icons.play_arrow,
                          color: Colors.white,
                        ),
                        label: Text(
                          _isStreaming ? 'Stop Stream' : 'Start Stream',
                          style: const TextStyle(color: Colors.white),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _isStreaming ? Colors.red : Colors.green,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24,
                            vertical: 12,
                          ),
                        ),
                      ),
                      
                      // Take snapshot
                      ElevatedButton.icon(
                        onPressed: _isStreaming ? _takeSnapshot : null,
                        icon: const Icon(Icons.camera_alt),
                        label: const Text('Snapshot'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24,
                            vertical: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // Streaming info
                  if (streamingInfo.hasValue && streamingInfo.value != null)
                    _buildStreamingInfo(streamingInfo.value!),
                    
                  if (_streamingError != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red.shade200),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.error, color: Colors.red.shade600, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _streamingError!,
                              style: TextStyle(
                                color: Colors.red.shade800,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
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

  Widget _buildStreamingArea() {
    if (!_isStreaming) {
      return Container(
        color: Colors.black,
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.videocam_off,
                size: 64,
                color: Colors.white54,
              ),
              SizedBox(height: 16),
              Text(
                'Camera not streaming',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 18,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'Tap "Start Stream" to begin',
                style: TextStyle(
                  color: Colors.white60,
                  fontSize: 14,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Use the proven CameraStreamPlayer widget
    return CameraStreamPlayer(
      cameraId: widget.camera.deviceId, // Use device_id for API calls
      width: double.infinity,
      height: double.infinity,
      onError: () {
        setState(() {
          _streamingError = 'Stream connection error';
        });
      },
      onStop: () {
        setState(() {
          _isStreaming = false;
        });
      },
    );
  }

  Widget _buildStreamingInfo(dynamic streamingInfo) {
    // Extract info from streaming info object
    final quality = streamingInfo.quality ?? 'Unknown';
    final fps = streamingInfo.fps?.toString() ?? 'Unknown';
    final resolution = streamingInfo.resolution ?? 'Unknown';
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Stream Status',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _buildStatusChip('Quality', quality, Colors.blue),
              const SizedBox(width: 8),
              _buildStatusChip('FPS', fps, Colors.green),
              const SizedBox(width: 8),
              _buildStatusChip('Resolution', resolution, Colors.orange),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatusChip(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        '$label: $value',
        style: TextStyle(
          fontSize: 12,
          color: color.withOpacity(0.8),
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
