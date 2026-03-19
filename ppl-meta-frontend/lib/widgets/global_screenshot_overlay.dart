import 'package:flutter/material.dart';
import '../services/developer_settings_service.dart';
import '../services/screenshot_service.dart';

/// Global overlay that shows screenshot FAB on all pages when enabled
class GlobalScreenshotOverlay extends StatefulWidget {
  final Widget child;

  const GlobalScreenshotOverlay({
    Key? key,
    required this.child,
  }) : super(key: key);

  @override
  State<GlobalScreenshotOverlay> createState() => _GlobalScreenshotOverlayState();
}

class _GlobalScreenshotOverlayState extends State<GlobalScreenshotOverlay> {
  final GlobalKey _screenshotKey = GlobalKey();
  final DeveloperSettingsService _devSettings = DeveloperSettingsService();
  final ScreenshotService _screenshotService = ScreenshotService();

  @override
  void initState() {
    super.initState();
    _devSettings.initialize();
    // Register the key for screenshots
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _screenshotService.registerPage(_screenshotKey);
    });
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      key: _screenshotKey,
      child: Stack(
        children: [
          widget.child,
          // Global Screenshot FAB Overlay
          ListenableBuilder(
            listenable: _devSettings,
            builder: (context, _) {
              if (!_devSettings.screenshotFabEnabled) {
                return const SizedBox.shrink();
              }

              return Positioned(
                right: 16,
                bottom: 16,
                child: Material(
                  color: Colors.transparent,
                  child: FloatingActionButton(
                    heroTag: 'global_screenshot_fab',
                    onPressed: () async {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('📸 Capturing visible viewport...'),
                          duration: Duration(milliseconds: 800),
                        ),
                      );

                      // Wait for the next frame to ensure painting is complete
                      await Future.delayed(const Duration(milliseconds: 150));
                      
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
                    backgroundColor: Colors.deepPurple,
                    child: const Icon(Icons.camera_alt),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
