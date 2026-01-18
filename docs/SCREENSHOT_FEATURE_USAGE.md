# Screenshot Feature with Developer Settings

## Overview
The screenshot feature includes a toggle in the app settings to enable/disable the floating camera button. This allows you to activate it for marketing campaigns and deactivate it later without removing the code.

## How to Use

### 1. Enable Screenshot Feature
1. Open the app
2. Navigate to **Profile** (bottom navigation)
3. Tap on **Developer Settings**
4. Toggle **Screenshot Capture Button** to ON
5. A camera floating action button will appear on supported pages

### 2. Capture Screenshots
- Click the floating camera button (📸) on any page
- Screenshot is automatically saved to `docs/screenshots/`
- Filename format: `screenshot_YYYY-MM-DDTHH-MM-SS.png`
- You'll see a success notification with the file path

### 3. Disable After Marketing Cycle
1. Go back to **Profile → Developer Settings**
2. Toggle **Screenshot Capture Button** to OFF
3. The camera button disappears from all pages

## Technical Implementation

### Files Created
- `lib/services/developer_settings_service.dart` - Manages settings with SharedPreferences
- `lib/presentation/pages/developer_settings_page.dart` - UI for toggling features
- `lib/widgets/screenshot_fab.dart` - Updated to check settings
- Profile page updated with Developer Settings menu item

### Features
- ✅ Persistent setting (survives app restarts)
- ✅ Clean UI toggle in settings
- ✅ No code removal needed
- ✅ Instant enable/disable
- ✅ Works across all pages with `ScreenshotFAB()`

## For Developers

### Adding Screenshot Capability to a Page
```dart
import 'package:ppl_meta_frontend/utils/screenshot_wrapper.dart';
import 'package:ppl_meta_frontend/widgets/screenshot_fab.dart';

class MyPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ScreenshotWrapper(
      child: Scaffold(
        appBar: AppBar(title: Text('My Page')),
        body: MyContent(),
        floatingActionButton: ScreenshotFAB(), // Auto-hides when disabled
      ),
    );
  }
}
```

### The FAB will:
- Show only when enabled in Developer Settings
- Hide automatically when disabled
- No additional code needed per page

## Dependencies Required

Add to `pubspec.yaml` if not already present:
```yaml
dependencies:
  shared_preferences: ^2.2.2  # For persistent settings
```

Run: `flutter pub get`

## Use Cases
- **Marketing Campaigns**: Enable to create promotional screenshots
- **Documentation**: Capture app screens for user guides
- **Presentations**: Get clean screenshots for demos
- **After Campaign**: Disable to keep production UI clean

The setting persists across app restarts, so you don't need to re-enable it every time during your marketing cycle.
