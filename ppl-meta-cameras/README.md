# PPL Meta Cameras - Camera Detection and Management Microservice

A specialized microservice for detecting, connecting, and managing cameras in the PPL Meta Platform. Provides comprehensive camera management capabilities with authentication and video streaming support.

## Features

- **Camera Detection**: Automatic detection of USB/Webcam cameras
- **Connection Management**: Connect/disconnect cameras with session tracking
- **Video Streaming**: Real-time video streaming with quality controls
- **Authentication**: JWT-based authentication with role-based permissions
- **Database Integration**: PostgreSQL for camera metadata and session tracking
- **REST API**: Comprehensive RESTful API with OpenAPI documentation

## API Endpoints

### Authentication
- `POST /api/v1/auth/demo-token` - Create demo authentication token
- `GET /api/v1/auth/permissions` - List available permissions and roles
- `POST /api/v1/auth/validate-token` - Validate JWT token

### Camera Management
- `GET /api/v1/cameras/` - List all cameras
- `POST /api/v1/cameras/detect` - Detect available cameras
- `POST /api/v1/cameras/{device_id}/connect` - Connect to camera
- `POST /api/v1/cameras/{device_id}/disconnect` - Disconnect from camera
- `GET /api/v1/cameras/{device_id}/info` - Get camera information
- `GET /api/v1/cameras/active` - List active connections
- `POST /api/v1/cameras/disconnect-all` - Disconnect all cameras (admin)

### Video Streaming
- `POST /api/v1/streaming/{device_id}/start` - Start video stream
- `GET /api/v1/streaming/{device_id}/video` - Get video stream
- `GET /api/v1/streaming/{device_id}/snapshot` - Capture snapshot
- `POST /api/v1/streaming/{device_id}/stop` - Stop video stream

### Health Monitoring
- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed health with authentication
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

## Authentication & Permissions

The service uses JWT-based authentication with role-based access control:

### Roles
- **Viewer**: View cameras and streams (read-only)
- **Operator**: Connect/disconnect cameras, control streaming
- **Administrator**: Full access including camera detection and admin functions

### Quick Start Authentication

```bash
# Get a demo token for testing
curl -X POST "http://localhost:8005/api/v1/auth/demo-token?role=administrator"

# Use the token in requests
curl -H "Authorization: Bearer <token>" "http://localhost:8005/api/v1/cameras/"
```

## Installation & Setup

### Environment Variables

```bash
# Service Configuration
PORT=8005
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/ppl_meta_cameras

# Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_EXPIRE_MINUTES=60

# Camera Settings
CAMERA_SCAN_TIMEOUT=30
MAX_SIMULTANEOUS_CAMERAS=10
DEFAULT_CAMERA_RESOLUTION=1280x720
DEFAULT_CAMERA_FPS=30
```

### Docker Deployment

1. **Build Image**:
```bash
docker build -t ppl-meta-cameras .
```

2. **Run Container**:
```bash
docker run -d \\
  --name ppl-meta-cameras \\
  -p 8005:8005 \\
  -e DATABASE_URL=postgresql://postgres:password@host:5432/ppl_meta_cameras \\
  -e JWT_SECRET_KEY=your-secret-key \\
  --device /dev/video0 \\
  ppl-meta-cameras
```

### Local Development

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set Environment Variables**:
```bash
export DATABASE_URL=postgresql://postgres:password@localhost:5432/ppl_meta_cameras
export JWT_SECRET_KEY=your-secret-key
```

3. **Run Service**:
```bash
cd src
python main.py
```

The service will start on `http://localhost:8005`

## Camera Detection

The service automatically detects available cameras:

### USB/Webcam Detection
- Scans camera indices 0-9
- Tests camera connectivity
- Extracts resolution and FPS capabilities
- Stores camera metadata in database

### Future IP Camera Support
- ONVIF device discovery
- RTSP stream detection
- Network camera scanning

## Video Streaming

### Stream Quality Options
- **Low**: 320x240 @ 15fps
- **Medium**: 640x480 @ 30fps (default)
- **High**: 1280x720 @ 30fps
- **Ultra**: 1920x1080 @ 30fps

### Streaming Formats
- **Video Stream**: Multipart MJPEG over HTTP
- **Snapshots**: Base64 encoded JPEG images

## Database Schema

### Tables
- **cameras**: Camera metadata and specifications
- **camera_sessions**: Active connection tracking
- **camera_capabilities**: Detailed camera features

### Key Models
- `Camera`: Main camera entity with type, status, capabilities
- `CameraSession`: Session tracking for active connections
- `CameraCapability`: Detailed technical specifications

## Security Features

- JWT token validation on all endpoints
- Role-based permission system
- Request rate limiting
- CORS configuration
- Trusted host middleware
- Comprehensive audit logging

## Monitoring & Health

- Prometheus metrics endpoint (`/metrics`)
- Health check endpoints for Kubernetes
- System resource monitoring
- Database connection health
- Active session tracking

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8005/docs`
- ReDoc: `http://localhost:8005/redoc`
- OpenAPI JSON: `http://localhost:8005/openapi.json`

## 📋 Development Status

✅ **COMPLETE IMPLEMENTATION - READY FOR TESTING**

All core features have been implemented and documented:
- Complete FastAPI microservice architecture
- JWT authentication with role-based permissions (3 roles, 15 permissions)
- Camera detection and management using OpenCV
- Video streaming with quality controls
- PostgreSQL database integration
- Comprehensive API documentation
- Health monitoring and metrics
- Development and testing tools

📝 **See [Development Issues Document](docs/archive/PPL_META_CAMERAS_DEVELOPMENT_ISSUES.md) for detailed implementation status and achievements.**

## Example Usage

### Basic Camera Operations

```bash
# Get demo token
TOKEN=$(curl -s -X POST "http://localhost:8005/api/v1/auth/demo-token" | jq -r '.access_token')

# Detect cameras
curl -H "Authorization: Bearer $TOKEN" \\
     -X POST "http://localhost:8005/api/v1/cameras/detect"

# List cameras
curl -H "Authorization: Bearer $TOKEN" \\
     "http://localhost:8005/api/v1/cameras/"

# Connect to camera
curl -H "Authorization: Bearer $TOKEN" \\
     -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/connect"

# Start streaming
curl -H "Authorization: Bearer $TOKEN" \\
     -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/start"

# View stream in browser
open "http://localhost:8005/api/v1/streaming/usb_camera_0/video"
```

## Integration

This microservice integrates with the PPL Meta Platform:

- **Service Discovery**: Consul registration
- **Gateway Routing**: API Gateway integration
- **Shared Logging**: Centralized logging system
- **Metrics Collection**: Prometheus monitoring
- **Database**: Shared PostgreSQL cluster

## Development

### Project Structure
```
src/
├── api/                    # API endpoints
│   ├── health.py          # Health check endpoints
│   └── v1/                # API version 1
│       ├── routes.py      # Main router
│       └── endpoints/     # Individual endpoint modules
├── models/                # Database models
├── security/             # Authentication & authorization
├── services/             # Business logic services
├── config.py            # Configuration management
├── database.py          # Database connection
└── main.py             # Application entry point
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Type checking
mypy src/

# Code formatting
black src/
flake8 src/
```

## License

Part of the PPL Meta Platform ecosystem.
