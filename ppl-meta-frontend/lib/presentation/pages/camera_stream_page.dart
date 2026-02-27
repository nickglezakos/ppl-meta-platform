import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/models/camera.dart';
import '../../core/providers/camera_providers.dart';
import '../widgets/camera/camera_stream_player_simple.dart';
import '../../widgets/camera/camera_counter_widget.dart';
import '../../widgets/camera/instant_detection_widget.dart';

/// Full-screen camera stream page with isolated widgets
/// Uses Column layout (not Stack) to prevent control overlays from affecting stream performance
class CameraStreamPage extends ConsumerWidget {
  final Camera camera;

  const CameraStreamPage({
    super.key,
    required this.camera,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 🔍 DEBUG: Log when stream page is built
    debugPrint('🎬 [CameraStreamPage] Building stream page for: ${camera.deviceId}');
    debugPrint('🎬 [CameraStreamPage] Camera name: ${camera.name}');
    
    final recordingState = ref.watch(cameraRecordingProvider(camera.deviceId));
    final isMobileLayout = MediaQuery.sizeOf(context).width < 600;
    
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            // Stream player (isolated with RepaintBoundary)
            // ✅ CRITICAL: RepaintBoundary prevents control widget rebuilds from affecting stream
            Expanded(
              child: RepaintBoundary(
                child: CameraStreamPlayerSimple(
                  key: ValueKey('stream_${camera.deviceId}'), // Stable key prevents rebuilds
                  cameraId: camera.deviceId,
                  width: double.infinity,
                  height: double.infinity,
                ),
              ),
            ),
            
            // Control bar positioned BELOW stream (not overlaid)
            // ✅ CRITICAL: Adjacent widget (sibling), not Stack overlay
            Container(
              color: Colors.black.withOpacity(0.8),
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Recording status (if recording)
                  if (recordingState.isRecording) ...[
                    _RecordingStatusBar(cameraId: camera.deviceId),
                    const SizedBox(height: 8),
                  ],
                  
                  // Counter widgets - responsive layout
                  if (isMobileLayout) ...[
                    CameraCounterWidget(
                      cameraId: camera.deviceId,
                    ),
                    const SizedBox(height: 8),
                    InstantDetectionWidget(
                      cameraId: camera.deviceId,
                    ),
                  ] else
                    Row(
                      children: [
                        Expanded(
                          child: CameraCounterWidget(
                            cameraId: camera.deviceId,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: InstantDetectionWidget(
                            cameraId: camera.deviceId,
                          ),
                        ),
                      ],
                    ),
                  const SizedBox(height: 8),
                  
                  // Control buttons row
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      // Back button
                      IconButton(
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.arrow_back, color: Colors.white),
                        iconSize: 28,
                        tooltip: 'Back',
                      ),
                      
                      // Recording controls for all camera types
                      _StreamRecordingControls(cameraId: camera.deviceId),
                      
                      // Fullscreen toggle (optional - for future enhancement)
                      IconButton(
                        onPressed: () {
                          // TODO: Implement fullscreen
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Fullscreen coming soon'),
                              duration: Duration(seconds: 1),
                            ),
                          );
                        },
                        icon: const Icon(Icons.fullscreen, color: Colors.white),
                        iconSize: 28,
                        tooltip: 'Fullscreen',
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Recording status bar showing timer and info
/// This widget rebuilds independently from the stream player
class _RecordingStatusBar extends ConsumerWidget {
  final String cameraId;

  const _RecordingStatusBar({required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recordingState = ref.watch(cameraRecordingProvider(cameraId));
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Colors.red,
          width: 2,
        ),
      ),
      child: Row(
        children: [
          // Recording indicator (pulsing dot)
          _PulsingDot(),
          const SizedBox(width: 12),
          // Status text
          const Text(
            'RECORDING',
            style: TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(width: 12),
          // Timer (isolated widget)
          _RecordingTimer(startedAt: recordingState.startedAt),
          const Spacer(),
          // File size
          if (recordingState.fileSizeBytes > 0)
            Text(
              '${(recordingState.fileSizeBytes / 1024 / 1024).toStringAsFixed(1)} MB',
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 12,
              ),
            ),
        ],
      ),
    );
  }
}

/// Recording timer that rebuilds every second independently
class _RecordingTimer extends StatefulWidget {
  final DateTime? startedAt;

  const _RecordingTimer({required this.startedAt});

  @override
  State<_RecordingTimer> createState() => _RecordingTimerState();
}

class _RecordingTimerState extends State<_RecordingTimer> {
  late Timer _timer;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    if (widget.startedAt != null) {
      _elapsed = DateTime.now().difference(widget.startedAt!);
    }
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() {
          if (widget.startedAt != null) {
            _elapsed = DateTime.now().difference(widget.startedAt!);
          }
        });
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final minutes = _elapsed.inMinutes.toString().padLeft(2, '0');
    final seconds = (_elapsed.inSeconds % 60).toString().padLeft(2, '0');
    
    return Text(
      '$minutes:$seconds',
      style: const TextStyle(
        color: Colors.white,
        fontSize: 14,
        fontWeight: FontWeight.w600,
        fontFamily: 'monospace',
      ),
    );
  }
}

/// Stream recording controls (start/stop button)
class _StreamRecordingControls extends ConsumerWidget {
  final String cameraId;

  const _StreamRecordingControls({required this.cameraId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recordingState = ref.watch(cameraRecordingProvider(cameraId));
    final recordingNotifier = ref.read(cameraRecordingProvider(cameraId).notifier);

    if (recordingState.isRecording) {
      // Stop button
      return ElevatedButton.icon(
        onPressed: recordingState.isLoading 
            ? null 
            : () => recordingNotifier.stopRecording(),
        icon: recordingState.isLoading
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.stop_circle, size: 24),
        label: Text(recordingState.isLoading ? 'Stopping...' : 'Stop Recording'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.red,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        ),
      );
    } else {
      // Start button
      return ElevatedButton.icon(
        onPressed: recordingState.isLoading 
            ? null 
            : () => recordingNotifier.startRecording(),
        icon: recordingState.isLoading
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.fiber_manual_record, size: 24),
        label: Text(recordingState.isLoading ? 'Starting...' : 'Start Recording'),
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.red,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        ),
      );
    }
  }
}

/// Pulsing dot indicator for recording
class _PulsingDot extends StatefulWidget {
  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    _controller.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: Colors.red.withOpacity(_animation.value),
            shape: BoxShape.circle,
          ),
        );
      },
    );
  }
}

