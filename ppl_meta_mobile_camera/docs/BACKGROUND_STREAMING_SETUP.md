# Background Streaming - Quick Setup Guide

## 🚀 Installation Steps

### 1. Install Dependencies
```bash
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera
flutter pub get
```

### 2. Verify Configuration

The following files have been updated:
- ✅ `pubspec.yaml` - Added background service dependencies
- ✅ `android/app/src/main/AndroidManifest.xml` - Added permissions and services
- ✅ `lib/services/background_streaming_service.dart` - New service implementation
- ✅ `lib/core/providers/streaming_provider.dart` - Added background mode support
- ✅ `lib/features/camera/screens/platform_connection_screen.dart` - Added UI toggle

### 3. Build and Test

```bash
# Clean build
flutter clean
flutter pub get

# Build for Android (requires physical device)
flutter run
```

**Note**: Background services must be tested on a physical Android device, not an emulator.

## 📱 How to Use

### Step-by-Step Usage

1. **Launch the app** on your Android device

2. **Connect to Platform**
   - Go to Platform Connection screen
   - Enter platform URL or scan QR code
   - Tap "Connect"

3. **Register Camera**
   - Enter camera name (optional)
   - Tap "Register Camera"
   - Wait for success confirmation

4. **Start Streaming**
   - Tap "Start Streaming" button
   - Verify video is streaming

5. **Enable Background Mode**
   - Scroll to "Background Streaming" section
   - Toggle the switch to ON
   - See notification appear in status bar

6. **Minimize App**
   - Press Home button or switch apps
   - Streaming continues in background!
   - Notification shows streaming status

7. **Return to App**
   - Tap notification to return
   - Or open app normally

8. **Stop Background Mode**
   - Toggle switch to OFF
   - Or tap "Stop Streaming" to stop everything

## 🔍 Verification

### Check if Background Service is Running

1. **Notification**: You should see a persistent notification:
   ```
   📱 Camera Streaming Active
   Streaming as [Your Camera Name]
   Frames sent: XXXX
   ```

2. **In App**: The UI shows:
   ```
   ✅ Background Mode Active
   You can now minimize the app safely
   ```

3. **Via ADB** (developer):
   ```bash
   # View logs
   adb logcat | grep -E "Background|Streaming"
   
   # Check running services
   adb shell dumpsys activity services | grep camera_streaming
   ```

## ⚠️ Important Notes

### Battery Considerations
- Background streaming is **battery intensive**
- Service auto-stops if battery < 15%
- Consider plugging in for long sessions
- Device may get warm during extended use

### Permissions Required
- ✅ Camera
- ✅ Notifications (for foreground service)
- ✅ Network access
- ✅ Wake lock

### Limitations
- **Android only** - iOS does not support background camera
- **Android 8.0+** required (API level 26+)
- **Physical device** required for testing
- **Network required** for streaming to platform

## 🔧 Troubleshooting

### Background service won't start
**Solution**: 
- Verify battery > 15%
- Check notification permission is granted
- Ensure you're streaming first before enabling background mode

### Notification doesn't show
**Solution**:
- Go to Settings > Apps > Eyenet Camera > Notifications
- Enable all notification categories
- Restart app and try again

### Streaming stops after minimizing
**Solution**:
- Check if background toggle is ON (blue)
- Verify notification is visible
- Check battery optimization settings:
  - Settings > Apps > Eyenet Camera > Battery
  - Set to "Unrestricted"

### High battery drain
**Solution**:
- Lower video quality in streaming settings
- Reduce FPS (frames per second)
- Use WiFi instead of mobile data
- Plug into charger for extended sessions

## 📊 Expected Behavior

### When Background Mode is Active:
- ✅ Persistent notification visible
- ✅ Can minimize app
- ✅ Can lock screen
- ✅ Streaming continues
- ✅ Wake lock prevents sleep
- ✅ Battery monitoring active

### When You Stop:
- ✅ Notification disappears
- ✅ Wake lock released
- ✅ Camera released
- ✅ Service stopped cleanly

## 🎯 Testing Checklist

- [ ] App connects to platform successfully
- [ ] Camera registers without errors
- [ ] Regular streaming works
- [ ] Background toggle appears when streaming
- [ ] Notification shows when background enabled
- [ ] App can be minimized while streaming
- [ ] Streaming continues after screen lock
- [ ] Can return to app via notification
- [ ] Battery monitoring works (test at low battery if possible)
- [ ] Stopping background mode works cleanly

## 📚 Additional Resources

- Full Documentation: `docs/BACKGROUND_STREAMING.md`
- Service Implementation: `lib/services/background_streaming_service.dart`
- Provider Integration: `lib/core/providers/streaming_provider.dart`

## 🆘 Getting Help

If you encounter issues:

1. **Check Logs**:
   ```bash
   adb logcat | grep -E "Background|Streaming|Eyenet"
   ```

2. **Verify Setup**:
   - All dependencies installed? Run `flutter pub get`
   - Building for Android? Check `android/app/build.gradle`
   - Physical device? Emulator won't work for background services

3. **Common Issues**:
   - Battery too low → Charge device
   - Permission denied → Check app settings
   - Service crashes → Check logs for errors
   - Network errors → Verify platform URL

## ✅ Success Indicators

You'll know it's working when:
1. Notification appears and stays visible
2. You can minimize the app
3. You can lock the screen
4. Platform still receives video stream
5. Frame count in notification increases
6. Device stays awake during streaming

---

**Ready to test!** 🎉

Run `flutter pub get` first, then `flutter run` on a physical Android device.
