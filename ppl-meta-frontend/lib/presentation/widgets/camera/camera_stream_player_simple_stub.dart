import 'package:flutter/material.dart';

class CameraStreamPlayerSimple extends StatelessWidget {
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
  Widget build(BuildContext context) {
    return Container(
      width: width ?? 640,
      height: height ?? 480,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.videocam_off, size: 48, color: Colors.white70),
            SizedBox(height: 12),
            Text(
              'Live camera stream is available on web.',
              style: TextStyle(color: Colors.white70),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
