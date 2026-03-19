import 'package:flutter/material.dart';
import 'screenshot_wrapper.dart';
import '../widgets/screenshot_fab.dart';

/// Example of how to use the screenshot functionality in your pages
class ScreenshotExamplePage extends StatelessWidget {
  const ScreenshotExamplePage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ScreenshotWrapper(
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Screenshot Example'),
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'This page can be captured!',
                style: TextStyle(fontSize: 24),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  // Your page content
                },
                child: const Text('Sample Button'),
              ),
            ],
          ),
        ),
        floatingActionButton: ScreenshotFAB(),
      ),
    );
  }
}

/// Usage Instructions:
/// 
/// 1. Wrap your page/widget with ScreenshotWrapper:
///    return ScreenshotWrapper(
///      child: YourWidget(),
///    );
///
/// 2. Add the ScreenshotFAB to your Scaffold:
///    floatingActionButton: ScreenshotFAB(),
///
/// 3. Or call programmatically:
///    await ScreenshotService().captureNow();
///
/// 4. Screenshots will be saved to: docs/screenshots/
///    with filename: screenshot_YYYY-MM-DDTHH-MM-SS.png
