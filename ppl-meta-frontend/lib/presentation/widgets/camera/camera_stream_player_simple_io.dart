import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/camera_providers.dart';

class CameraStreamPlayerSimple extends ConsumerStatefulWidget {
  final String cameraId;
  final double? width;
  final double? height;
  final VoidCallback? onError;
  final VoidCallback? onStop;

  const CameraStreamPlayerSimple({
    super.key,
    required this.cameraId,
    this.width,
    this.height,
    this.onError,
    this.onStop,
  });

  @override
  ConsumerState<CameraStreamPlayerSimple> createState() =>
      _CameraStreamPlayerSimpleState();
}

class _CameraStreamPlayerSimpleState
    extends ConsumerState<CameraStreamPlayerSimple> {
  static const Duration _pollInterval = Duration(milliseconds: 250);

  Timer? _pollTimer;
  Uint8List? _latestFrame;
  bool _isStreaming = false;
  bool _isRequestInFlight = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _startStreaming();
  }

  @override
  void dispose() {
    _stopStreaming(notify: false);
    super.dispose();
  }

  void _startStreaming() {
    _error = null;
    _isStreaming = true;
    _pollTimer?.cancel();

    _pollOnce();
    _pollTimer = Timer.periodic(_pollInterval, (_) => _pollOnce());

    if (mounted) {
      setState(() {});
    }
  }

  void _stopStreaming({bool notify = true}) {
    _pollTimer?.cancel();
    _pollTimer = null;
    _isStreaming = false;
    _isRequestInFlight = false;

    if (notify) {
      widget.onStop?.call();
    }

    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _pollOnce() async {
    if (!_isStreaming || _isRequestInFlight || !mounted) return;

    _isRequestInFlight = true;
    try {
      final cameraService = ref.read(cameraServiceProvider);
      final snapshot = await cameraService.captureSnapshot(widget.cameraId);

      if (!mounted || !_isStreaming) return;

      final imageBytes = snapshot.imageBytes;
      if (imageBytes.isEmpty) {
        throw Exception('Empty snapshot frame received');
      }

      setState(() {
        _latestFrame = imageBytes;
        _error = null;
      });
    } catch (e) {
      debugPrint('❌ [IO_STREAM] Snapshot poll error for ${widget.cameraId}: $e');
      if (!mounted || !_isStreaming) return;
      setState(() {
        _error = 'Waiting for camera frames...';
      });
      widget.onError?.call();
    } finally {
      _isRequestInFlight = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width ?? 640,
      height: widget.height ?? 480,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: _isStreaming ? _buildStreamView() : _buildStoppedView(),
      ),
    );
  }

  Widget _buildStoppedView() {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.videocam_off,
              size: 48,
              color: Colors.white54,
            ),
            const SizedBox(height: 12),
            const Text(
              'Camera stopped',
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _startStreaming,
              child: const Text('Start Camera'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStreamView() {
    final hasFrame = _latestFrame != null && _latestFrame!.isNotEmpty;

    return Stack(
      fit: StackFit.expand,
      children: [
        if (hasFrame)
          Image.memory(
            _latestFrame!,
            fit: BoxFit.contain,
            gaplessPlayback: true,
            filterQuality: FilterQuality.low,
          )
        else
          const Center(
            child: CircularProgressIndicator(color: Colors.white),
          ),
        Positioned(
          top: 8,
          left: 8,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: hasFrame ? Colors.red : Colors.grey,
              borderRadius: BorderRadius.circular(4),
            ),
            child: const Text(
              'LIVE',
              style: TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
        if (_error != null && !hasFrame)
          Positioned(
            bottom: 8,
            left: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                _error!,
                style: const TextStyle(color: Colors.white70, fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ),
          ),
      ],
    );
  }
}
