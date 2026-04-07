import 'package:flutter/material.dart';
import '../services/screenshot_service.dart';
import '../services/developer_settings_service.dart';

/// Floating Action Button for triggering screenshots
/// Add this to your Scaffold to enable screenshot capture
/// Visibility controlled by Developer Settings
class ScreenshotFAB extends StatelessWidget {
  final ScreenshotService _screenshotService = ScreenshotService();
  final DeveloperSettingsService _devSettings = DeveloperSettingsService();

  ScreenshotFAB({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _devSettings,
      builder: (context, child) {
        // Only show FAB if enabled in developer settings
        if (!_devSettings.screenshotFabEnabled) {
          return const SizedBox.shrink();
        }

        return FloatingActionButton(
      onPressed: () async {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('📸 Capturing screenshot...'),
            duration: Duration(seconds: 1),
          ),
        );

        final path = await _screenshotService.captureNow();

        if (path != null && context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('✅ Screenshot saved to:\n$path'),
              duration: const Duration(seconds: 3),
              action: SnackBarAction(
                label: 'OK',
                onPressed: () {},
              ),
            ),
          );
            } else if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('❌ Failed to capture screenshot'),
              backgroundColor: Colors.red,
            ),
          );
        }
      },
      tooltip: 'Capture Screenshot',
      child: const Icon(Icons.camera_alt),
    );
      },
    );
  }
}
