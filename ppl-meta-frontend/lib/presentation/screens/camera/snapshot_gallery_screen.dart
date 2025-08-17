import 'package:flutter/material.dart';
import '../../widgets/camera/snapshot_gallery_widget.dart';

/// Dedicated snapshot gallery screen for Phase 1
class SnapshotGalleryScreen extends StatefulWidget {
  final String? cameraId;
  final String? title;

  const SnapshotGalleryScreen({
    super.key,
    this.cameraId,
    this.title,
  });

  @override
  State<SnapshotGalleryScreen> createState() => _SnapshotGalleryScreenState();
}

class _SnapshotGalleryScreenState extends State<SnapshotGalleryScreen> {
  final GlobalKey<State<SnapshotGalleryWidget>> _galleryKey = GlobalKey();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title ?? (widget.cameraId != null ? 'Camera Snapshots' : 'Snapshot Gallery')),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              // Force refresh by rebuilding the widget
              setState(() {});
            },
            tooltip: 'Refresh',
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => _showInfoDialog(context),
            tooltip: 'About',
          ),
        ],
      ),
      body: SnapshotGalleryWidget(
        key: ValueKey('gallery_${DateTime.now().millisecondsSinceEpoch}'), // Force rebuild on refresh
        cameraId: widget.cameraId,
        showLocalOnly: true, // Phase 1
        showTitle: false, // Already shown in AppBar
      ),
    );
  }

  void _showInfoDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Snapshot Gallery - Phase 1'),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Local Storage',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 4),
              Text(
                'Snapshots are stored locally on your device using SharedPreferences. They will persist between app sessions.',
              ),
              SizedBox(height: 12),
              Text(
                'Features Available:',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 4),
              Text('• Capture snapshots with custom settings'),
              Text('• View snapshot gallery with thumbnails'),
              Text('• Search snapshots by filename or camera'),
              Text('• Delete individual or all snapshots'),
              Text('• Preview with metadata display'),
              SizedBox(height: 12),
              Text(
                'Coming in Phase 2:',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 4),
              Text('• Media service integration'),
              Text('• Cloud storage and synchronization'),
              Text('• Advanced collections and tagging'),
              Text('• Sharing and export functionality'),
              Text('• SQLite database storage'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}
