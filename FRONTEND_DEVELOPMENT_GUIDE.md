# PPL Meta Frontend - Local Development Guide

## Overview

The PPL Meta Frontend is a Flutter application that provides a modern, cross-platform user interface for the PPL Meta Platform. This guide covers local development setup and integration with the backend services.

## Features

- 🌐 **Cross-Platform**: Web, macOS, iOS, Android support
- 🔐 **Authentication**: JWT-based authentication with backend
- 📱 **Responsive Design**: Adaptive UI for all screen sizes
- 🎨 **Material Design 3**: Modern, consistent UI components
- 🔄 **State Management**: Riverpod for predictable state management
- 🌐 **API Integration**: Seamless integration with PPL Meta services

## Prerequisites

### Required
- **Flutter SDK** (>=3.10.0) - [Installation Guide](https://docs.flutter.dev/get-started/install/macos)
- **Dart SDK** (>=3.0.0) - Included with Flutter
- **VS Code** or **Android Studio**
- **Chrome** (for web development)

### Quick Install
```bash
# Via Homebrew (recommended for macOS)
brew install --cask flutter

# Verify installation
flutter doctor
```

## Setup

### 1. Automatic Setup
```bash
# Run the setup script
./setup-flutter.sh
```

### 2. Manual Setup
```bash
# Navigate to frontend directory
cd ppl-meta-frontend

# Install dependencies
flutter pub get

# Generate code
flutter packages pub run build_runner build --delete-conflicting-outputs
```

## Development

### Backend Integration

The frontend is configured to work with local backend services:

| Service | Local URL | Purpose |
|---------|-----------|---------|
| Gateway | `http://localhost:8080` | API Gateway & routing |
| Node Service | `http://localhost:8001` | User management & auth |
| Media Service | `http://localhost:8000` | Media processing |
| Orchestrator | `http://localhost:8002` | Business logic |

### VS Code Tasks

Use these tasks for efficient development:

#### Frontend Development
- **📱 Install Flutter Dependencies** - Install/update packages
- **📱 Start Frontend (Web)** - Run on Chrome (port 3000)
- **📱 Start Frontend (Desktop)** - Run on macOS desktop
- **📱 Generate Code (Frontend)** - Generate models & serialization
- **📱 Watch Code Generation (Frontend)** - Auto-generate on file changes
- **📱 Test Frontend** - Run unit tests
- **📱 Clean Frontend** - Clean and reinstall dependencies

#### Full Stack Development
- **🚀 Start Full Stack (Backend + Frontend)** - Start all services + frontend

### Running the Frontend

#### Web Development (Recommended)
```bash
flutter run -d chrome --web-port 3000
```

#### Desktop Development
```bash
flutter run -d macos
```

#### Mobile Development
```bash
# iOS (requires Xcode)
flutter run -d ios

# Android (requires Android Studio)
flutter run -d android
```

### Code Generation

The frontend uses code generation for models and serialization:

```bash
# One-time generation
flutter packages pub run build_runner build --delete-conflicting-outputs

# Watch mode (auto-generates on file changes)
flutter packages pub run build_runner watch --delete-conflicting-outputs
```

## Configuration

### Environment Configuration

The frontend uses JSON configuration files in `assets/config/`:

- `env.development.json` - Local development
- `env.staging.json` - Staging environment  
- `env.production.json` - Production environment

### Development Configuration
```json
{
  "API_BASE_URL": "http://localhost:8080",
  "ENVIRONMENT": "development",
  "LOG_LEVEL": "debug",
  "USER_SERVICE_URL": "http://localhost:8001",
  "MEDIA_SERVICE_URL": "http://localhost:8000",
  "ORCHESTRATOR_SERVICE_URL": "http://localhost:8002"
}
```

## Architecture

### Project Structure
```
lib/
├── core/               # Core utilities and configurations
│   ├── api/           # API client and services
│   ├── config/        # App configuration
│   ├── models/        # Data models
│   ├── providers/     # State management providers
│   ├── services/      # Business services
│   └── theme/         # App theming
├── presentation/      # UI layer
│   ├── navigation/    # Routing configuration
│   ├── pages/         # Application pages
│   ├── screens/       # Screen components
│   └── widgets/       # Reusable UI components
└── main.dart         # Application entry point
```

### State Management

The frontend uses **Riverpod** for state management:

- **Providers**: Manage application state
- **Consumers**: Subscribe to state changes
- **Notifiers**: Handle state mutations

## Authentication Flow

1. **User Login**: Frontend sends credentials to Node Service
2. **JWT Token**: Backend returns JWT token
3. **Token Storage**: Frontend securely stores token
4. **API Requests**: Token included in API calls
5. **Auto-Refresh**: Token refreshed automatically

## Nginx Integration

When using nginx proxy (localhost:80), the frontend is served as the main entry point:

- **Frontend**: `http://localhost/` (port 80)
- **API Routes**: `http://localhost/api/...`
- **Direct Access**: `http://localhost:3000/` (development)

## Testing

### Unit Tests
```bash
flutter test
```

### Integration Tests
```bash
flutter test integration_test/
```

### Widget Tests
```bash
flutter test test/widget_test.dart
```

## Building

### Web Build
```bash
flutter build web --release
```

### Desktop Build
```bash
flutter build macos --release
```

### Mobile Builds
```bash
# iOS
flutter build ios --release

# Android
flutter build apk --release
```

## Troubleshooting

### Common Issues

1. **Flutter not found**
   - Install Flutter SDK
   - Add to PATH: `export PATH="$PATH:/path/to/flutter/bin"`

2. **Dependencies issues**
   - Run: `flutter clean && flutter pub get`

3. **Code generation errors**
   - Run: `flutter packages pub run build_runner clean`
   - Then: `flutter packages pub run build_runner build --delete-conflicting-outputs`

4. **Web hot reload not working**
   - Restart with: `flutter run -d chrome --web-port 3000`

5. **Backend connection issues**
   - Ensure backend services are running
   - Check `assets/config/env.development.json` URLs

### Development Tips

1. **Use VS Code Flutter Extension**
   - Install "Flutter" and "Dart" extensions
   - Enable hot reload for faster development

2. **State Management**
   - Use Riverpod providers for shared state
   - Avoid setState for complex state

3. **API Integration**
   - Use the configured API client in `core/api/`
   - Handle errors gracefully with try-catch

4. **UI Development**
   - Follow Material Design guidelines
   - Test on multiple screen sizes
   - Use responsive layouts

## Integration with Backend

### API Endpoints

The frontend integrates with these backend endpoints:

```dart
// Authentication
POST /api/v1/users/login
POST /api/v1/users/register
GET  /api/v1/users/profile

// Media
GET    /api/v1/media/
POST   /api/v1/media/upload
DELETE /api/v1/media/{id}

// Health Checks
GET /api/v1/health
```

### Error Handling

The frontend includes comprehensive error handling:

- **Network Errors**: Retry logic and user feedback
- **Authentication Errors**: Automatic logout and redirect
- **Validation Errors**: Field-level error display
- **Server Errors**: User-friendly error messages

## Next Steps

1. **Complete Authentication Integration** - Finish login/register flows
2. **Media Management UI** - Build file upload and gallery interfaces
3. **Orchestrator Integration** - Add workflow management features
4. **Real-time Features** - Implement WebSocket connections
5. **Offline Support** - Add local caching and sync

---

For more information, see the main [VS Code Tasks Guide](VSCODE_TASKS_GUIDE.md) and [Issue 026](ISSUE-026-FRONTEND-IMPLEMENTATION.md).
