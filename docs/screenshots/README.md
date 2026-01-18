# Screenshots Directory

This directory contains screenshots captured from the Eyenet Vision Flutter frontend.

## Automatic Screenshots

Screenshots are automatically saved here when using the screenshot functionality in the app.

### File Naming Convention
- Format: `screenshot_YYYY-MM-DDTHH-MM-SS.png`
- Example: `screenshot_2026-01-15T14-30-45.png`

### How to Capture Screenshots

#### Method 1: Using the Screenshot FAB (Floating Action Button)
1. Wrap your page with `ScreenshotWrapper`
2. Add `ScreenshotFAB()` to your Scaffold's `floatingActionButton`
3. Click the camera icon to capture

#### Method 2: Programmatic Capture
```dart
import 'package:ppl_meta_frontend/services/screenshot_service.dart';

// Capture current page
final path = await ScreenshotService().captureNow();

// Or with custom filename
final path = await ScreenshotService().captureAndSave(
  fileName: 'my-custom-screenshot.png',
);
```

### Implementation Example

```dart
import 'package:flutter/material.dart';
import 'package:ppl_meta_frontend/utils/screenshot_wrapper.dart';
import 'package:ppl_meta_frontend/widgets/screenshot_fab.dart';

class MyPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ScreenshotWrapper(
      child: Scaffold(
        appBar: AppBar(title: Text('My Page')),
        body: Center(child: Text('Page Content')),
        floatingActionButton: ScreenshotFAB(),
      ),
    );
  }
}
```

## Features

- ✅ High resolution capture (3x pixel ratio)
- ✅ Automatic timestamp in filename
- ✅ Creates directory if it doesn't exist
- ✅ Console logging with file size and dimensions
- ✅ Works on all platforms (Web, Desktop, Mobile)
- ✅ PNG format for quality preservation

## Notes

- Screenshots capture the exact rendered state of the widget tree
- Animations and dynamic content are captured as displayed at capture time
- File size varies based on content complexity (typically 50KB - 2MB)
- High pixel ratio ensures crisp screenshots for documentation
