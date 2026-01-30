# PPL Meta Mobile Camera

**Eyenet Vision** - Transform Android devices into intelligent network cameras with background streaming support.

## 🎯 Features

### Core Functionality
- 📹 **Live Camera Streaming** - Real-time MJPEG video streaming
- 🌐 **Platform Integration** - Seamless connection to PPL Meta platform
- 📱 **Mobile Camera Registration** - Automatic device registration and management
- 🎨 **Adaptive UI** - Material Design 3 with light/dark theme support
- 🔐 **Secure Authentication** - JWT-based authentication with platform services

### ⭐ Background Streaming (NEW!)
- 🔄 **Background Mode** - Continue streaming when app is minimized
- 🔋 **Battery Monitoring** - Auto-stops if battery < 15%
- 📲 **Persistent Notification** - Always visible streaming status
- 🔓 **Screen Lock Support** - Streams even when screen is locked
- ⚡ **Wake Lock** - Prevents device sleep during streaming

## 🚀 Quick Start

### Prerequisites
- Flutter SDK 3.8.1 or higher
- Android device (Android 8.0+ / API 26+)
- PPL Meta Platform instance

### Installation

```bash
# Clone the repository
cd ppl_meta_mobile_camera

# Install dependencies
flutter pub get

# Run on Android device
flutter run
```

### Basic Usage

1. **Connect to Platform**
   - Enter platform URL or scan QR code
   - Authenticate with credentials

2. **Register Camera**
   - Set camera name (optional - auto-generated if skipped)
   - Tap "Register Camera"

3. **Start Streaming**
   - Tap "Start Streaming"
   - Video begins streaming to platform

4. **Enable Background Mode** (Optional)
   - Toggle "Background Streaming" switch
   - Minimize app - streaming continues!

## 📖 Documentation

- [Background Streaming Guide](docs/BACKGROUND_STREAMING.md) - Complete implementation details
- [Quick Setup Guide](docs/BACKGROUND_STREAMING_SETUP.md) - Step-by-step installation and usage
- [Automatic Naming](AUTOMATIC_NAMING_IMPLEMENTATION_COMPLETE.md) - Camera naming system

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Flutter App UI                │
│  - Camera Screen                        │
│  - Platform Connection Screen           │
│  - Settings & Controls                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      PlatformStreamingProvider          │
│  - Connection management                │
│  - Registration handling                │
│  - Streaming orchestration              │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌─────▼──────────────┐
│  Regular     │  │  Background        │
│  Streaming   │  │  Streaming Service │
│              │  │  (Foreground)      │
└──────┬───────┘  └──────┬─────────────┘
       │                 │
       │  ┌──────────────▼──────────┐
       └─►│  MJPEG Streaming        │
          │  - Frame capture        │
          │  - HTTP streaming       │
          └─────────────────────────┘
```

## 🔧 Configuration

### Android Permissions
The app requires the following permissions:
- Camera access
- Internet connectivity
- Network state
- Foreground service (for background streaming)
- Wake lock
- Notifications

### Platform Requirements
- PPL Meta Platform v2.x or higher
- Media Service endpoint accessible
- Camera Service endpoint accessible

## 🛠️ Development

### Project Structure
```
lib/
├── core/
│   ├── models/          # Data models
│   ├── providers/       # State management
│   └── services/        # Core services
├── features/
│   ├── authentication/  # Login & auth
│   └── camera/          # Camera features
├── services/
│   ├── background_streaming_service.dart  # Background mode
│   ├── mjpeg_streaming_service.dart       # MJPEG server
│   └── ...
└── main.dart
```

### Key Dependencies
- `camera` - Camera access and control
- `provider` - State management
- `http` - Network requests
- `flutter_background_service` - Background execution
- `flutter_local_notifications` - Notification support
- `wakelock_plus` - Wake lock management
- `battery_plus` - Battery monitoring

### Building

```bash
# Development build
flutter run

# Release build
flutter build apk --release

# Release bundle
flutter build appbundle --release
```

## 📊 Performance

### Resource Usage
- **CPU**: 15-30% (varies by resolution)
- **Memory**: 100-200 MB
- **Battery**: 30-50% per hour when streaming
- **Network**: 1-5 Mbps (depends on quality)

### Streaming Quality Options
- Low: 320x240 @ 15fps
- Medium: 640x480 @ 30fps (default)
- High: 1280x720 @ 30fps
- Ultra: 1920x1080 @ 30fps

## ⚠️ Known Limitations

### Platform Support
- ✅ **Android**: Full background streaming support
- ❌ **iOS**: No background camera access (privacy restrictions)
  - Alternative: Keep app in foreground

### Battery & Performance
- High battery consumption during streaming
- Device may get warm with extended use
- Recommend charging for sessions > 1 hour

## 🐛 Troubleshooting

### Common Issues

**Background service won't start**
- Check battery level > 15%
- Verify notification permissions
- Ensure streaming is active first

**High battery drain**
- Lower streaming quality
- Reduce FPS
- Use WiFi instead of mobile data

**Connection issues**
- Verify platform URL is correct
- Check network connectivity
- Ensure firewall allows connections

See [Setup Guide](docs/BACKGROUND_STREAMING_SETUP.md) for detailed troubleshooting.

## 🤝 Contributing

This is part of the PPL Meta Platform project. For issues or contributions:
1. Check existing issues
2. Create feature branch
3. Submit pull request

## 📝 Version History

### v1.1.0 (Current)
- ✨ Added background streaming support
- ✨ Battery monitoring and auto-stop
- ✨ Persistent notification system
- ✨ Wake lock management
- 🐛 Bug fixes and stability improvements

### v1.0.0
- 🎉 Initial release
- 📹 Basic camera streaming
- 🌐 Platform integration
- 📱 Camera registration

## 📄 License

Part of PPL Meta Platform - All rights reserved

## 🔗 Related Projects

- [PPL Meta Platform](../) - Main platform
- [PPL Meta Cameras](../ppl-meta-cameras) - Camera service
- [PPL Meta Frontend](../ppl-meta-frontend) - Web interface

---

**Status**: ✅ Production Ready  
**Platform**: Android 8.0+ (API 26+)  
**Last Updated**: January 30, 2026
