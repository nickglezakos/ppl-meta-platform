import 'package:flutter/material.dart';
import '../services/screenshot_service.dart';

/// Wrapper widget that enables screenshot capability for any page
class ScreenshotWrapper extends StatefulWidget {
  final Widget child;
  final bool enableScreenshot;

  const ScreenshotWrapper({
    Key? key,
    required this.child,
    this.enableScreenshot = true,
  }) : super(key: key);

  @override
  State<ScreenshotWrapper> createState() => _ScreenshotWrapperState();
}

class _ScreenshotWrapperState extends State<ScreenshotWrapper> {
  final GlobalKey _repaintBoundaryKey = GlobalKey();
  final ScreenshotService _screenshotService = ScreenshotService();

  @override
  void initState() {
    super.initState();
    if (widget.enableScreenshot) {
      // Register this page for screenshot after first frame
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _screenshotService.registerPage(_repaintBoundaryKey);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.enableScreenshot) {
      return widget.child;
    }

    return RepaintBoundary(
      key: _repaintBoundaryKey,
      child: widget.child,
    );
  }
}
