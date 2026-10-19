import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

/// Captures a single front-camera still for enroll or verify.
class FaceCaptureScreen extends StatefulWidget {
  const FaceCaptureScreen({super.key, this.title = 'Capture face'});

  final String title;

  @override
  State<FaceCaptureScreen> createState() => _FaceCaptureScreenState();
}

class _FaceCaptureScreenState extends State<FaceCaptureScreen> {
  CameraController? _controller;
  bool _ready = false;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final status = await Permission.camera.request();
    if (!status.isGranted) {
      setState(() => _error = 'Camera permission is required');
      return;
    }
    try {
      final cameras = await availableCameras();
      final front = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        front,
        ResolutionPreset.medium,
        enableAudio: false,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
        _ready = true;
      });
    } catch (e) {
      setState(() => _error = 'Camera init failed: $e');
    }
  }

  Future<void> _capture() async {
    final controller = _controller;
    if (controller == null || !_ready || _busy) return;
    setState(() => _busy = true);
    try {
      final file = await controller.takePicture();
      if (!mounted) return;
      Navigator.of(context).pop(File(file.path));
    } catch (e) {
      setState(() {
        _error = 'Capture failed: $e';
        _busy = false;
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          Expanded(
            child: _error != null
                ? Center(child: Text(_error!))
                : !_ready
                    ? const Center(child: CircularProgressIndicator())
                    : CameraPreview(_controller!),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: FilledButton.icon(
              onPressed: _ready && !_busy ? _capture : null,
              icon: const Icon(Icons.camera_alt),
              label: Text(_busy ? 'Capturing…' : 'Capture'),
            ),
          ),
        ],
      ),
    );
  }
}
