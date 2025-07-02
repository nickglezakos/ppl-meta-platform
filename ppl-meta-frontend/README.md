# PPL Meta Platform - Flutter Frontend

A Flutter frontend microservice for the PPL Meta Platform, providing cross-platform user interfaces for web, mobile, and desktop applications.

## Features

- 🌐 **Cross-Platform**: Web, iOS, Android, Desktop support
- 🔐 **Authentication**: JWT-based authentication with PPL Meta Node
- 📱 **Responsive Design**: Adaptive UI for all screen sizes
- 🎨 **Material Design**: Modern, consistent UI components
- 🔄 **State Management**: Riverpod for predictable state management
- 🌐 **API Integration**: Seamless integration with PPL Meta services
- 📊 **Analytics**: User interaction tracking and analytics
- 🌙 **Theming**: Light/dark mode support

## Architecture

### Frontend Architecture
```
lib/
├── core/               # Core utilities and configurations
│   ├── config/        # Environment and API configurations
│   ├── constants/     # App constants and enums
│   ├── theme/         # App theming and styling
│   └── utils/         # Utility functions and helpers
├── data/              # Data layer
│   ├── models/        # Data models and DTOs
│   ├── repositories/  # Data repositories
│   └── services/      # API services and data sources
├── domain/            # Business logic layer
│   ├── entities/      # Domain entities
│   ├── repositories/ # Repository interfaces
│   └── usecases/      # Business use cases
├── presentation/      # Presentation layer
│   ├── pages/         # Application screens/pages
│   ├── widgets/       # Reusable UI components
│   ├── providers/     # State management providers
│   └── navigation/    # Navigation configuration
└── main.dart         # Application entry point
```

### API Integration
- **Gateway**: `http://localhost:8080` - API Gateway service
- **Authentication**: `http://localhost:8001` - User management
- **Media**: `http://localhost:8000` - Media processing
- **Orchestrator**: `http://localhost:8002` - Business logic

## Development

### Prerequisites
- Flutter SDK (>=3.10.0)
- Dart SDK (>=3.0.0)
- VS Code or Android Studio
- Chrome (for web development)

### Setup
```bash
# Install dependencies
flutter pub get

# Generate code (models, etc.)
flutter packages pub run build_runner build

# Run on web
flutter run -d chrome

# Run on mobile (with device/emulator connected)
flutter run

# Run tests
flutter test
```

### Environment Configuration
Create environment-specific configuration files:

```bash
# Development
cp assets/config/env.example.json assets/config/env.development.json

# Staging
cp assets/config/env.example.json assets/config/env.staging.json

# Production
cp assets/config/env.example.json assets/config/env.production.json
```

### Code Generation
```bash
# Generate models and serialization
flutter packages pub run build_runner build

# Watch for changes during development
flutter packages pub run build_runner watch
```

## Deployment

### Web Deployment
```bash
# Build for web
flutter build web --release

# Deploy to static hosting (Nginx, AWS S3, etc.)
# Files will be in build/web/
```

### Mobile Deployment
```bash
# Android
flutter build apk --release
flutter build appbundle --release

# iOS
flutter build ios --release
```

### Docker Deployment
```bash
# Build Docker image
docker build -t ppl-meta-frontend:latest .

# Run container
docker run -p 3000:80 ppl-meta-frontend:latest
```

## Testing

### Unit Tests
```bash
flutter test test/unit/
```

### Integration Tests
```bash
flutter test test/integration/
```

### Widget Tests
```bash
flutter test test/widget/
```

### E2E Tests
```bash
flutter drive --target=test_driver/app.dart
```

## API Documentation

### Authentication Flow
1. User enters credentials on login screen
2. Frontend sends POST to `/api/v1/auth/login` via Gateway
3. Gateway forwards to User Management service
4. JWT token returned and stored locally
5. Token included in subsequent API requests

### API Endpoints
```dart
// Authentication
POST /api/v1/auth/login
POST /api/v1/auth/register
POST /api/v1/auth/refresh
DELETE /api/v1/auth/logout

// User Management
GET /api/v1/users/profile
PUT /api/v1/users/profile
GET /api/v1/users

// Media
POST /api/v1/media/upload
GET /api/v1/media/{id}
DELETE /api/v1/media/{id}

// Health
GET /api/v1/health
```

## Configuration

### Environment Variables
```json
{
  "API_BASE_URL": "http://localhost:8080",
  "ENVIRONMENT": "development",
  "LOG_LEVEL": "debug",
  "CACHE_ENABLED": true,
  "ANALYTICS_ENABLED": false
}
```

### Build Flavors
- **Development**: Local development with debug features
- **Staging**: Pre-production testing environment
- **Production**: Live production environment

## Contributing

1. Follow Flutter style guide and conventions
2. Write tests for new features
3. Update documentation
4. Ensure all lints pass: `flutter analyze`
5. Format code: `flutter format .`

## Project Structure

### Key Files
- `lib/main.dart` - Application entry point
- `lib/core/config/app_config.dart` - App configuration
- `lib/presentation/navigation/app_router.dart` - Navigation setup
- `lib/data/services/api_service.dart` - API communication
- `assets/config/` - Environment configurations

### Dependencies
- **http/dio**: HTTP client for API communication
- **riverpod**: State management solution
- **go_router**: Declarative navigation
- **hive**: Local storage and caching
- **jwt_decoder**: JWT token handling

## Monitoring

### Performance
- Flutter Inspector for widget debugging
- Performance overlay for frame rate monitoring
- Memory usage tracking

### Analytics
- User interaction tracking
- Error reporting and crash analytics
- Performance metrics collection

---

**Port**: 3000 (when served via HTTP server)  
**Technology**: Flutter/Dart  
**Platforms**: Web, iOS, Android, Desktop  
**State Management**: Riverpod  
**Navigation**: go_router
