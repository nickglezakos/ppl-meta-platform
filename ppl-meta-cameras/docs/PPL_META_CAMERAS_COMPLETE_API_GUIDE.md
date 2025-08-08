# PPL Meta Cameras Service - Complete API Guide

**Version**: 1.0.0  
**Service Port**: 8005  
**API Base URL**: `http://localhost:8005/api/v1`  
**Documentation**: `http://localhost:8005/docs` (Swagger UI)  
**Alternative Documentation**: `http://localhost:8005/redoc` (ReDoc)  

---

## 📋 **TABLE OF CONTENTS**

1. [🚀 Service Overview](#-service-overview)
2. [🔧 Environment Setup](#-environment-setup)
3. [🔐 Authentication](#-authentication)
4. [📷 Camera Management APIs](#-camera-management-apis)
5. [🎥 Video Streaming APIs](#-video-streaming-apis)
6. [📸 Snapshot Capture APIs](#-snapshot-capture-apis)
7. [🔗 Complete API Reference](#-complete-api-reference)
8. [💻 Frontend Integration Guide](#-frontend-integration-guide)
9. [🧪 Testing Examples](#-testing-examples)
10. [🛠️ Troubleshooting](#️-troubleshooting)

---

## 🚀 **SERVICE OVERVIEW**

The PPL Meta Cameras Service is a comprehensive microservice providing complete camera management, video streaming, and snapshot capture capabilities. It integrates seamlessly with the PPL Meta Platform's 6-service architecture.

### **Core Capabilities**

- **🔍 Camera Detection**: Automatic USB camera discovery and enumeration
- **📱 Connection Management**: Real-time camera connection and session tracking
- **🎥 Video Streaming**: HTTP-based video streaming with quality controls
- **📸 Snapshot Capture**: High-quality image capture with file management
- **🔐 JWT Authentication**: Cross-service authentication with role-based permissions
- **💾 Database Integration**: PostgreSQL persistence for camera metadata and sessions
- **📊 Health Monitoring**: Comprehensive health checks and metrics

### **Technology Stack**

- **Framework**: FastAPI with async/await support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Camera Processing**: OpenCV for hardware interaction
- **Authentication**: JWT with configurable secrets
- **Documentation**: OpenAPI 3.0 with Swagger UI
- **Deployment**: Uvicorn ASGI server with hot reload

---

## 🔧 **ENVIRONMENT SETUP**

### **Required Environment Variables**

Create a `.env` file in the camera service root directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://nickgklezakos:@localhost:5432/ppl_meta_cameras

# JWT Authentication (CRITICAL - Must match Node service)
NODE_SERVICE_SECRET=RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Service Configuration
HOST=0.0.0.0
PORT=8005
DEBUG=true
ENVIRONMENT=development

# Optional: Service Discovery
CONSUL_HOST=localhost
CONSUL_PORT=8500

# Optional: Monitoring
ENABLE_METRICS=true
ENABLE_HEALTH_CHECKS=true
```

### **Starting the Service**

#### **Option 1: Direct Python Execution**
```bash
cd ppl-meta-cameras
source venv/bin/activate
NODE_SERVICE_SECRET='RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4' \
PYTHONPATH=/path/to/ppl-meta-cameras \
python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload
```

#### **Option 2: Using Platform Tasks**
```bash
# Start all services including cameras
cd /path/to/ppl-meta-code
# Use VS Code task: "🚀 Start All Local Python Services"
```

#### **Option 3: Using Setup Script**
```bash
cd ppl-meta-cameras
chmod +x setup.sh
./setup.sh
```

### **Service Health Verification**

```bash
# Check service health
curl http://localhost:8005/health

# Expected Response:
{
  "status": "healthy",
  "service": "ppl-meta-cameras",
  "version": "1.0.0",
  "timestamp": "2025-08-08T19:18:00.000Z",
  "database": "connected",
  "cameras_detected": 1,
  "active_connections": 0
}
```

---

## 🔐 **AUTHENTICATION**

### **Authentication Flow**

The camera service uses cross-service JWT authentication with the Node service:

```mermaid
graph LR
    A[Client] --> B[Node Service Login]
    B --> C[JWT Token]
    C --> D[Camera Service Request]
    D --> E[Token Validation]
    E --> F[Camera Operations]
```

### **Step 1: Obtain JWT Token from Node Service**

```bash
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 7,
    "email": "fresh.user@example.com",
    "role": "user"
  }
}
```

### **Step 2: Use JWT Token for Camera Service**

Include the JWT token in all camera service requests:

```bash
curl -X GET 'http://localhost:8005/api/v1/cameras/' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

### **Authentication Headers**

All camera service endpoints require:
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### **User Permissions**

- **Node Service Users**: Automatically receive full camera administrator permissions
- **Admin Permissions**: Full access to all camera operations
- **Session Tracking**: All operations logged with user identification

---

## 📷 **CAMERA MANAGEMENT APIs**

### **1. Camera Detection**

Detect and enumerate available cameras on the system.

**Endpoint**: `POST /api/v1/cameras/detect`

```bash
curl -X POST 'http://localhost:8005/api/v1/cameras/detect?save_to_db=true' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json'
```

**Response:**
```json
{
  "status": "success",
  "message": "Camera detection completed",
  "cameras_detected": [
    {
      "device_id": "usb_camera_0",
      "name": "USB Camera 0",
      "camera_type": "USB",
      "status": "AVAILABLE",
      "resolution_width": 1280,
      "resolution_height": 720,
      "max_fps": 30,
      "connection_string": "0",
      "supports_streaming": true,
      "supports_recording": true,
      "device_path": "/dev/video0"
    }
  ],
  "detected_count": 1,
  "saved_count": 1,
  "detection_timestamp": "2025-08-08T19:18:09.044Z"
}
```

**Query Parameters:**
- `save_to_db` (boolean): Save detected cameras to database (default: false)

### **2. List All Cameras**

Retrieve all cameras from the database.

**Endpoint**: `GET /api/v1/cameras/`

```bash
curl -X GET 'http://localhost:8005/api/v1/cameras/' \
  -H 'Authorization: Bearer <jwt_token>'
```

**Response:**
```json
{
  "status": "success",
  "cameras": [
    {
      "device_id": "usb_camera_0",
      "name": "USB Camera 0",
      "camera_type": "USB",
      "status": "AVAILABLE",
      "created_at": "2025-08-08T19:18:09.044Z",
      "updated_at": "2025-08-08T19:18:09.044Z",
      "total_sessions": 2,
      "last_connected": "2025-08-08T19:18:09.217Z"
    }
  ],
  "total_cameras": 1,
  "available_cameras": 1,
  "connected_cameras": 0
}
```

### **3. Camera Connection**

Connect to a specific camera and initiate a session.

**Endpoint**: `POST /api/v1/cameras/{device_id}/connect`

```bash
curl -X POST 'http://localhost:8005/api/v1/cameras/usb_camera_0/connect' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json'
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully connected to camera usb_camera_0",
  "device_id": "usb_camera_0",
  "connection_status": "CONNECTED",
  "session_id": "session_12345",
  "connected_at": "2025-08-08T19:18:09.217Z",
  "capabilities": {
    "resolution_width": 1280,
    "resolution_height": 720,
    "max_fps": 30,
    "formats": ["MJPEG", "YUYV"]
  }
}
```

### **4. List Active Connections**

Get all currently active camera connections.

**Endpoint**: `GET /api/v1/cameras/active`

```bash
curl -X GET 'http://localhost:8005/api/v1/cameras/active' \
  -H 'Authorization: Bearer <jwt_token>'
```

**Response:**
```json
{
  "status": "success",
  "active_connections": [
    {
      "device_id": "usb_camera_0",
      "name": "USB Camera 0",
      "status": "CONNECTED",
      "session_id": "session_12345",
      "connected_at": "2025-08-08T19:18:09.217Z",
      "connection_duration_seconds": 45,
      "user_id": 7
    }
  ],
  "total_active": 1,
  "connection_summary": {
    "usb_cameras": 1,
    "ip_cameras": 0,
    "total_sessions": 1
  }
}
```

### **5. Camera Information**

Get detailed information about a specific camera.

**Endpoint**: `GET /api/v1/cameras/{device_id}/info`

```bash
curl -X GET 'http://localhost:8005/api/v1/cameras/usb_camera_0/info' \
  -H 'Authorization: Bearer <jwt_token>'
```

**Response:**
```json
{
  "device_id": "usb_camera_0",
  "name": "USB Camera 0",
  "status": "CONNECTED",
  "camera_type": "USB",
  "capabilities": {
    "resolution_width": 1280,
    "resolution_height": 720,
    "max_fps": 30,
    "formats": ["MJPEG", "YUYV"],
    "supports_streaming": true,
    "supports_recording": true
  },
  "current_session": {
    "session_id": "session_12345",
    "started_at": "2025-08-08T19:18:09.217Z",
    "duration_seconds": 60,
    "user_id": 7
  },
  "hardware_info": {
    "device_path": "/dev/video0",
    "connection_string": "0",
    "driver": "USB Video Class"
  }
}
```

### **6. Camera Disconnection**

Disconnect from a specific camera and end the session.

**Endpoint**: `POST /api/v1/cameras/{device_id}/disconnect`

```bash
curl -X POST 'http://localhost:8005/api/v1/cameras/usb_camera_0/disconnect' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json'
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully disconnected from camera usb_camera_0",
  "device_id": "usb_camera_0",
  "connection_status": "DISCONNECTED",
  "session_ended": true,
  "session_duration_seconds": 120,
  "disconnected_at": "2025-08-08T19:18:14.423Z"
}
```

### **7. Bulk Disconnect All Cameras**

Disconnect from all active cameras simultaneously.

**Endpoint**: `POST /api/v1/cameras/disconnect-all`

```bash
curl -X POST 'http://localhost:8005/api/v1/cameras/disconnect-all' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json'
```

**Response:**
```json
{
  "status": "success",
  "message": "All cameras disconnected successfully",
  "disconnected_cameras": [
    {
      "device_id": "usb_camera_0",
      "session_duration_seconds": 90
    }
  ],
  "total_disconnected": 1,
  "disconnected_at": "2025-08-08T19:18:14.423Z"
}
```

---

## 🎥 **VIDEO STREAMING APIs**

### **1. Start Video Stream**

Initialize video streaming for a connected camera.

**Endpoint**: `POST /api/v1/streaming/{device_id}/start`

```bash
curl -X POST 'http://localhost:8005/api/v1/streaming/usb_camera_0/start' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "quality": "high",
    "fps": 30,
    "resolution": "1280x720"
  }'
```

**Request Body (Optional):**
```json
{
  "quality": "high",        // "low", "medium", "high"
  "fps": 30,               // Frames per second (1-60)
  "resolution": "1280x720", // "640x480", "1280x720", "1920x1080"
  "format": "MJPEG"        // Video format
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Video stream started for usb_camera_0",
  "device_id": "usb_camera_0",
  "stream_status": "ACTIVE",
  "stream_url": "/api/v1/streaming/usb_camera_0/video",
  "stream_settings": {
    "quality": "high",
    "fps": 30,
    "resolution": "1280x720",
    "format": "MJPEG"
  },
  "started_at": "2025-08-08T19:18:09.223Z"
}
```

### **2. Access Video Stream**

Retrieve the live video stream data.

**Endpoint**: `GET /api/v1/streaming/{device_id}/video`

```bash
curl -X GET 'http://localhost:8005/api/v1/streaming/usb_camera_0/video' \
  -H 'Authorization: Bearer <jwt_token>' \
  --output video_stream.mjpeg
```

**Response**: 
- **Content-Type**: `multipart/x-mixed-replace; boundary=frame`
- **Data**: Continuous MJPEG video stream
- **Format**: Binary video data with MIME boundary markers

**For Web Integration:**
```html
<img src="http://localhost:8005/api/v1/streaming/usb_camera_0/video" 
     style="width: 640px; height: 480px;" />
```

### **3. Stop Video Stream**

Terminate the active video stream.

**Endpoint**: `POST /api/v1/streaming/{device_id}/stop`

```bash
curl -X POST 'http://localhost:8005/api/v1/streaming/usb_camera_0/stop' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json'
```

**Response:**
```json
{
  "status": "success",
  "message": "Video stream stopped for usb_camera_0",
  "device_id": "usb_camera_0",
  "stream_status": "STOPPED",
  "stream_duration_seconds": 45,
  "stopped_at": "2025-08-08T19:18:14.371Z"
}
```

### **4. Stream Status**

Check the current status of a video stream.

**Endpoint**: `GET /api/v1/streaming/{device_id}/status`

```bash
curl -X GET 'http://localhost:8005/api/v1/streaming/usb_camera_0/status' \
  -H 'Authorization: Bearer <jwt_token>'
```

**Response:**
```json
{
  "device_id": "usb_camera_0",
  "stream_status": "ACTIVE",
  "started_at": "2025-08-08T19:18:09.223Z",
  "duration_seconds": 120,
  "current_settings": {
    "quality": "high",
    "fps": 30,
    "resolution": "1280x720",
    "format": "MJPEG"
  },
  "viewer_count": 1,
  "data_transferred_mb": 15.4
}
```

---

## 📸 **SNAPSHOT CAPTURE APIs**

### **1. Capture Snapshot**

Capture a high-quality still image from a connected camera.

**Endpoint**: `GET /api/v1/streaming/{device_id}/snapshot`

```bash
curl -X GET 'http://localhost:8005/api/v1/streaming/usb_camera_0/snapshot' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Accept: application/json'
```

**Response:**
```json
{
  "status": "success",
  "message": "Snapshot captured successfully",
  "device_id": "usb_camera_0",
  "snapshot_data": {
    "filename": "snapshot_usb_camera_0_1754669894.jpg",
    "file_size_bytes": 48152,
    "resolution": {
      "width": 640,
      "height": 480
    },
    "format": "JPEG",
    "quality": 90,
    "captured_at": "2025-08-08T19:18:14.381Z"
  },
  "base64_image": "/9j/4AAQSkZJRgABAQEAYABgAAD...", // Base64 encoded image
  "file_path": "/tmp/cam_test_snapshots/snapshot_usb_camera_0_1754669894.jpg"
}
```

### **2. Capture Snapshot with Custom Settings**

Capture a snapshot with specific quality and format settings.

**Endpoint**: `POST /api/v1/streaming/{device_id}/snapshot`

```bash
curl -X POST 'http://localhost:8005/api/v1/streaming/usb_camera_0/snapshot' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "quality": 95,
    "format": "PNG",
    "resolution": "1280x720",
    "save_to_file": true,
    "filename": "custom_snapshot.png"
  }'
```

**Request Body:**
```json
{
  "quality": 95,              // Image quality (1-100)
  "format": "PNG",            // "JPEG", "PNG", "BMP"
  "resolution": "1280x720",   // Custom resolution
  "save_to_file": true,       // Save to filesystem
  "filename": "custom_snapshot.png", // Custom filename
  "include_metadata": true    // Include EXIF metadata
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Custom snapshot captured successfully",
  "device_id": "usb_camera_0",
  "snapshot_data": {
    "filename": "custom_snapshot.png",
    "file_size_bytes": 892456,
    "resolution": {
      "width": 1280,
      "height": 720
    },
    "format": "PNG",
    "quality": 95,
    "captured_at": "2025-08-08T19:18:14.381Z",
    "metadata": {
      "camera_model": "USB Camera 0",
      "exposure_time": "1/60",
      "iso": 100
    }
  },
  "base64_image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "file_path": "/tmp/cam_test_snapshots/custom_snapshot.png"
}
```

### **3. Download Snapshot File**

Download a previously captured snapshot file.

**Endpoint**: `GET /api/v1/streaming/{device_id}/snapshot/{filename}`

```bash
curl -X GET 'http://localhost:8005/api/v1/streaming/usb_camera_0/snapshot/snapshot_usb_camera_0_1754669894.jpg' \
  -H 'Authorization: Bearer <jwt_token>' \
  --output downloaded_snapshot.jpg
```

**Response**: 
- **Content-Type**: `image/jpeg` or `image/png`
- **Data**: Binary image file
- **Headers**: Content-Disposition with filename

### **4. List Captured Snapshots**

Get a list of all captured snapshots for a camera.

**Endpoint**: `GET /api/v1/streaming/{device_id}/snapshots`

```bash
curl -X GET 'http://localhost:8005/api/v1/streaming/usb_camera_0/snapshots' \
  -H 'Authorization: Bearer <jwt_token>'
```

**Response:**
```json
{
  "device_id": "usb_camera_0",
  "snapshots": [
    {
      "filename": "snapshot_usb_camera_0_1754669894.jpg",
      "file_size_bytes": 48152,
      "resolution": "640x480",
      "format": "JPEG",
      "captured_at": "2025-08-08T19:18:14.381Z",
      "download_url": "/api/v1/streaming/usb_camera_0/snapshot/snapshot_usb_camera_0_1754669894.jpg"
    }
  ],
  "total_snapshots": 1,
  "total_size_bytes": 48152
}
```

---

## 🔗 **COMPLETE API REFERENCE**

### **Service Information**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health status |
| `/` | GET | Service welcome message |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |
| `/openapi.json` | GET | OpenAPI specification |

### **Authentication**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/demo-token` | GET | Generate demo JWT token |

### **Camera Management**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cameras/detect` | POST | Detect available cameras |
| `/api/v1/cameras/` | GET | List all cameras |
| `/api/v1/cameras/active` | GET | List active connections |
| `/api/v1/cameras/{device_id}/connect` | POST | Connect to camera |
| `/api/v1/cameras/{device_id}/disconnect` | POST | Disconnect from camera |
| `/api/v1/cameras/{device_id}/info` | GET | Get camera information |
| `/api/v1/cameras/disconnect-all` | POST | Disconnect all cameras |

### **Video Streaming**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/streaming/{device_id}/start` | POST | Start video stream |
| `/api/v1/streaming/{device_id}/stop` | POST | Stop video stream |
| `/api/v1/streaming/{device_id}/video` | GET | Access video stream |
| `/api/v1/streaming/{device_id}/status` | GET | Get stream status |

### **Snapshot Capture**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/streaming/{device_id}/snapshot` | GET | Capture simple snapshot |
| `/api/v1/streaming/{device_id}/snapshot` | POST | Capture custom snapshot |
| `/api/v1/streaming/{device_id}/snapshots` | GET | List snapshots |
| `/api/v1/streaming/{device_id}/snapshot/{filename}` | GET | Download snapshot |

### **Response Status Codes**

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## 💻 **FRONTEND INTEGRATION GUIDE**

### **React/JavaScript Integration**

#### **Authentication Setup**
```javascript
class CameraService {
  constructor() {
    this.baseURL = 'http://localhost:8005/api/v1';
    this.token = null;
  }

  async authenticate(email, password) {
    // Get JWT token from Node service
    const authResponse = await fetch('http://localhost:8001/api/v1/users/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `username=${email}&password=${password}`
    });
    
    const authData = await authResponse.json();
    this.token = authData.access_token;
    return this.token;
  }

  getHeaders() {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }
}
```

#### **Camera Detection**
```javascript
async function detectCameras() {
  const response = await fetch(`${cameraService.baseURL}/cameras/detect?save_to_db=true`, {
    method: 'POST',
    headers: cameraService.getHeaders()
  });
  
  const data = await response.json();
  console.log('Detected cameras:', data.cameras_detected);
  return data.cameras_detected;
}
```

#### **Video Streaming**
```javascript
// Start video stream
async function startVideoStream(deviceId) {
  const response = await fetch(`${cameraService.baseURL}/streaming/${deviceId}/start`, {
    method: 'POST',
    headers: cameraService.getHeaders(),
    body: JSON.stringify({
      quality: 'high',
      fps: 30,
      resolution: '1280x720'
    })
  });
  
  const data = await response.json();
  
  // Display video in HTML
  const videoElement = document.getElementById('video-stream');
  videoElement.src = `${cameraService.baseURL}/streaming/${deviceId}/video`;
  
  return data;
}

// Stop video stream
async function stopVideoStream(deviceId) {
  const response = await fetch(`${cameraService.baseURL}/streaming/${deviceId}/stop`, {
    method: 'POST',
    headers: cameraService.getHeaders()
  });
  
  return await response.json();
}
```

#### **Snapshot Capture**
```javascript
async function captureSnapshot(deviceId) {
  const response = await fetch(`${cameraService.baseURL}/streaming/${deviceId}/snapshot`, {
    method: 'GET',
    headers: cameraService.getHeaders()
  });
  
  const data = await response.json();
  
  // Display snapshot
  const imageElement = document.getElementById('snapshot-image');
  imageElement.src = `data:image/jpeg;base64,${data.base64_image}`;
  
  return data;
}
```

### **Flutter/Dart Integration**

#### **Camera Service Class**
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class CameraService {
  static const String baseUrl = 'http://localhost:8005/api/v1';
  String? _token;

  Future<void> authenticate(String email, String password) async {
    final response = await http.post(
      Uri.parse('http://localhost:8001/api/v1/users/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'username=$email&password=$password',
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      _token = data['access_token'];
    }
  }

  Map<String, String> get headers => {
    'Authorization': 'Bearer $_token',
    'Content-Type': 'application/json',
  };

  Future<List<Camera>> detectCameras() async {
    final response = await http.post(
      Uri.parse('$baseUrl/cameras/detect?save_to_db=true'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['cameras_detected'] as List)
          .map((camera) => Camera.fromJson(camera))
          .toList();
    }
    
    throw Exception('Failed to detect cameras');
  }

  Future<void> startVideoStream(String deviceId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/streaming/$deviceId/start'),
      headers: headers,
      body: json.encode({
        'quality': 'high',
        'fps': 30,
        'resolution': '1280x720'
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to start video stream');
    }
  }

  String getVideoStreamUrl(String deviceId) {
    return '$baseUrl/streaming/$deviceId/video';
  }

  Future<Snapshot> captureSnapshot(String deviceId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/streaming/$deviceId/snapshot'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return Snapshot.fromJson(data);
    }
    
    throw Exception('Failed to capture snapshot');
  }
}
```

#### **Camera Model**
```dart
class Camera {
  final String deviceId;
  final String name;
  final String cameraType;
  final String status;
  final int resolutionWidth;
  final int resolutionHeight;
  final int maxFps;

  Camera({
    required this.deviceId,
    required this.name,
    required this.cameraType,
    required this.status,
    required this.resolutionWidth,
    required this.resolutionHeight,
    required this.maxFps,
  });

  factory Camera.fromJson(Map<String, dynamic> json) {
    return Camera(
      deviceId: json['device_id'],
      name: json['name'],
      cameraType: json['camera_type'],
      status: json['status'],
      resolutionWidth: json['resolution_width'],
      resolutionHeight: json['resolution_height'],
      maxFps: json['max_fps'],
    );
  }
}

class Snapshot {
  final String filename;
  final int fileSizeBytes;
  final String resolution;
  final String format;
  final String base64Image;
  final DateTime capturedAt;

  Snapshot({
    required this.filename,
    required this.fileSizeBytes,
    required this.resolution,
    required this.format,
    required this.base64Image,
    required this.capturedAt,
  });

  factory Snapshot.fromJson(Map<String, dynamic> json) {
    return Snapshot(
      filename: json['snapshot_data']['filename'],
      fileSizeBytes: json['snapshot_data']['file_size_bytes'],
      resolution: '${json['snapshot_data']['resolution']['width']}x${json['snapshot_data']['resolution']['height']}',
      format: json['snapshot_data']['format'],
      base64Image: json['base64_image'],
      capturedAt: DateTime.parse(json['snapshot_data']['captured_at']),
    );
  }
}
```

#### **Video Stream Widget**
```dart
import 'package:flutter/material.dart';

class VideoStreamWidget extends StatefulWidget {
  final String deviceId;
  final CameraService cameraService;

  const VideoStreamWidget({
    Key? key,
    required this.deviceId,
    required this.cameraService,
  }) : super(key: key);

  @override
  _VideoStreamWidgetState createState() => _VideoStreamWidgetState();
}

class _VideoStreamWidgetState extends State<VideoStreamWidget> {
  bool _isStreaming = false;

  Future<void> _startStream() async {
    try {
      await widget.cameraService.startVideoStream(widget.deviceId);
      setState(() {
        _isStreaming = true;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to start stream: $e')),
      );
    }
  }

  Future<void> _stopStream() async {
    try {
      await widget.cameraService.stopVideoStream(widget.deviceId);
      setState(() {
        _isStreaming = false;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to stop stream: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 640,
          height: 480,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey),
            borderRadius: BorderRadius.circular(8),
          ),
          child: _isStreaming
              ? Image.network(
                  widget.cameraService.getVideoStreamUrl(widget.deviceId),
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return const Center(
                      child: Text('Failed to load video stream'),
                    );
                  },
                )
              : const Center(
                  child: Text('Video stream not active'),
                ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ElevatedButton(
              onPressed: _isStreaming ? null : _startStream,
              child: const Text('Start Stream'),
            ),
            const SizedBox(width: 16),
            ElevatedButton(
              onPressed: _isStreaming ? _stopStream : null,
              child: const Text('Stop Stream'),
            ),
          ],
        ),
      ],
    );
  }
}
```

---

## 🧪 **TESTING EXAMPLES**

### **Complete Integration Test**

```bash
#!/bin/bash
# Complete Camera Service Integration Test

echo "🧪 Starting Camera Service Integration Test..."

# Step 1: Authenticate
echo "Step 1: Authenticating user..."
AUTH_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=fresh.user@example.com&password=NewPassword234!")

JWT_TOKEN=$(echo $AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "✅ Authentication successful"

# Step 2: Detect cameras
echo "Step 2: Detecting cameras..."
DETECTION_RESPONSE=$(curl -s -X POST "http://localhost:8005/api/v1/cameras/detect?save_to_db=true" \
  -H "Authorization: Bearer $JWT_TOKEN")
echo "✅ Camera detection completed: $DETECTION_RESPONSE"

# Step 3: Connect to first camera
echo "Step 3: Connecting to camera..."
CONNECT_RESPONSE=$(curl -s -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/connect" \
  -H "Authorization: Bearer $JWT_TOKEN")
echo "✅ Camera connection: $CONNECT_RESPONSE"

# Step 4: Start video stream
echo "Step 4: Starting video stream..."
STREAM_START=$(curl -s -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/start" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quality": "high", "fps": 30}')
echo "✅ Video stream started: $STREAM_START"

# Step 5: Capture snapshot
echo "Step 5: Capturing snapshot..."
SNAPSHOT_RESPONSE=$(curl -s -X GET "http://localhost:8005/api/v1/streaming/usb_camera_0/snapshot" \
  -H "Authorization: Bearer $JWT_TOKEN")
echo "✅ Snapshot captured"

# Step 6: Stop video stream
echo "Step 6: Stopping video stream..."
STREAM_STOP=$(curl -s -X POST "http://localhost:8005/api/v1/streaming/usb_camera_0/stop" \
  -H "Authorization: Bearer $JWT_TOKEN")
echo "✅ Video stream stopped: $STREAM_STOP"

# Step 7: Disconnect camera
echo "Step 7: Disconnecting camera..."
DISCONNECT_RESPONSE=$(curl -s -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/disconnect" \
  -H "Authorization: Bearer $JWT_TOKEN")
echo "✅ Camera disconnected: $DISCONNECT_RESPONSE"

echo "🎉 Integration test completed successfully!"
```

### **Python Test Script**

```python
#!/usr/bin/env python3
"""
Complete Camera Service Integration Test
"""

import requests
import time
import base64
import json

class CameraServiceTester:
    def __init__(self):
        self.node_base_url = "http://localhost:8001/api/v1"
        self.camera_base_url = "http://localhost:8005/api/v1"
        self.token = None
        
    def authenticate(self):
        """Authenticate with Node service"""
        response = requests.post(
            f"{self.node_base_url}/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="username=fresh.user@example.com&password=NewPassword234!"
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
    
    def get_headers(self):
        """Get authentication headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_camera_detection(self):
        """Test camera detection"""
        response = requests.post(
            f"{self.camera_base_url}/cameras/detect?save_to_db=true",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Camera detection: {data['detected_count']} cameras found")
            return data["cameras_detected"]
        else:
            print(f"❌ Camera detection failed: {response.status_code}")
            return []
    
    def test_camera_connection(self, device_id):
        """Test camera connection"""
        response = requests.post(
            f"{self.camera_base_url}/cameras/{device_id}/connect",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            print(f"✅ Camera connection successful: {device_id}")
            return True
        else:
            print(f"❌ Camera connection failed: {response.status_code}")
            return False
    
    def test_video_streaming(self, device_id):
        """Test video streaming"""
        # Start stream
        start_response = requests.post(
            f"{self.camera_base_url}/streaming/{device_id}/start",
            headers=self.get_headers(),
            json={"quality": "high", "fps": 30}
        )
        
        if start_response.status_code == 200:
            print(f"✅ Video stream started: {device_id}")
            
            # Wait a moment
            time.sleep(2)
            
            # Test stream data
            stream_response = requests.get(
                f"{self.camera_base_url}/streaming/{device_id}/video",
                headers=self.get_headers(),
                stream=True,
                timeout=5
            )
            
            if stream_response.status_code == 200:
                # Read first chunk
                chunk = next(stream_response.iter_content(chunk_size=1024))
                print(f"✅ Video stream data: {len(chunk)} bytes received")
            
            # Stop stream
            stop_response = requests.post(
                f"{self.camera_base_url}/streaming/{device_id}/stop",
                headers=self.get_headers()
            )
            
            if stop_response.status_code == 200:
                print(f"✅ Video stream stopped: {device_id}")
                return True
        
        print(f"❌ Video streaming test failed")
        return False
    
    def test_snapshot_capture(self, device_id):
        """Test snapshot capture"""
        response = requests.get(
            f"{self.camera_base_url}/streaming/{device_id}/snapshot",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            snapshot_data = data["snapshot_data"]
            print(f"✅ Snapshot captured: {snapshot_data['filename']}")
            print(f"   Resolution: {snapshot_data['resolution']['width']}x{snapshot_data['resolution']['height']}")
            print(f"   Size: {snapshot_data['file_size_bytes']} bytes")
            
            # Save base64 image
            with open("test_snapshot.jpg", "wb") as f:
                f.write(base64.b64decode(data["base64_image"]))
            print("   Saved as: test_snapshot.jpg")
            
            return True
        else:
            print(f"❌ Snapshot capture failed: {response.status_code}")
            return False
    
    def test_camera_disconnection(self, device_id):
        """Test camera disconnection"""
        response = requests.post(
            f"{self.camera_base_url}/cameras/{device_id}/disconnect",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            print(f"✅ Camera disconnected: {device_id}")
            return True
        else:
            print(f"❌ Camera disconnection failed: {response.status_code}")
            return False
    
    def run_complete_test(self):
        """Run complete integration test"""
        print("🧪 Starting Complete Camera Service Integration Test")
        print("=" * 60)
        
        # Step 1: Authentication
        if not self.authenticate():
            return False
        
        # Step 2: Camera detection
        cameras = self.test_camera_detection()
        if not cameras:
            print("❌ No cameras detected, cannot continue test")
            return False
        
        device_id = cameras[0]["device_id"]
        print(f"Using camera: {device_id}")
        
        # Step 3: Camera connection
        if not self.test_camera_connection(device_id):
            return False
        
        # Step 4: Video streaming
        if not self.test_video_streaming(device_id):
            return False
        
        # Step 5: Snapshot capture
        if not self.test_snapshot_capture(device_id):
            return False
        
        # Step 6: Camera disconnection
        if not self.test_camera_disconnection(device_id):
            return False
        
        print("=" * 60)
        print("🎉 Complete integration test PASSED!")
        return True

if __name__ == "__main__":
    tester = CameraServiceTester()
    success = tester.run_complete_test()
    exit(0 if success else 1)
```

---

## 🛠️ **TROUBLESHOOTING**

### **Common Issues and Solutions**

#### **1. Authentication Issues**

**Problem**: `401 Unauthorized` errors

**Solutions**:
```bash
# Check NODE_SERVICE_SECRET is set correctly
echo $NODE_SERVICE_SECRET

# Verify token validity
curl -X GET 'http://localhost:8005/api/v1/auth/demo-token' \
  -H 'Authorization: Bearer <jwt_token>'

# Restart cameras service with correct environment variable
NODE_SERVICE_SECRET='RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4' \
python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload
```

#### **2. Camera Detection Issues**

**Problem**: No cameras detected

**Solutions**:
```bash
# Check camera permissions
sudo usermod -a -G video $USER

# List available video devices
ls -la /dev/video*

# Test camera with OpenCV
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera working:', cap.isOpened())"

# Check camera is not used by other applications
lsof /dev/video0
```

#### **3. Service Connection Issues**

**Problem**: Service not responding

**Solutions**:
```bash
# Check service status
curl http://localhost:8005/health

# Check if port is in use
lsof -i:8005

# Restart service
pkill -f "uvicorn.*8005"
cd ppl-meta-cameras
NODE_SERVICE_SECRET='RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4' \
python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload
```

#### **4. Database Connection Issues**

**Problem**: Database connection errors

**Solutions**:
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test database connection
psql -h localhost -p 5432 -U nickgklezakos -d ppl_meta_cameras -c "SELECT 1;"

# Check database URL
echo $DATABASE_URL

# Create database if missing
createdb -h localhost -p 5432 -U nickgklezakos ppl_meta_cameras
```

#### **5. Video Streaming Issues**

**Problem**: Video stream not working

**Solutions**:
```bash
# Check camera is connected first
curl -X POST 'http://localhost:8005/api/v1/cameras/usb_camera_0/connect' \
  -H 'Authorization: Bearer <jwt_token>'

# Test with different quality settings
curl -X POST 'http://localhost:8005/api/v1/streaming/usb_camera_0/start' \
  -H 'Authorization: Bearer <jwt_token>' \
  -H 'Content-Type: application/json' \
  -d '{"quality": "low", "fps": 15}'

# Check stream status
curl -X GET 'http://localhost:8005/api/v1/streaming/usb_camera_0/status' \
  -H 'Authorization: Bearer <jwt_token>'
```

### **Performance Optimization**

#### **1. Stream Quality Settings**
```json
{
  "quality": "low",    // For slow connections
  "fps": 15,          // Reduce frame rate
  "resolution": "640x480"  // Lower resolution
}
```

#### **2. Database Optimization**
```bash
# Index optimization for PostgreSQL
psql -h localhost -p 5432 -U nickgklezakos -d ppl_meta_cameras -c "
CREATE INDEX IF NOT EXISTS idx_cameras_device_id ON cameras(device_id);
CREATE INDEX IF NOT EXISTS idx_sessions_camera_id ON camera_sessions(camera_id);
"
```

#### **3. Resource Monitoring**
```bash
# Monitor service resources
ps aux | grep uvicorn
top -p $(pgrep -f "uvicorn.*8005")

# Monitor database connections
psql -h localhost -p 5432 -U nickgklezakos -d ppl_meta_cameras -c "
SELECT * FROM pg_stat_activity WHERE datname = 'ppl_meta_cameras';
"
```

### **Logging and Debugging**

#### **1. Enable Debug Mode**
```bash
# Start with debug logging
DEBUG=true python -m uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload --log-level debug
```

#### **2. Check Service Logs**
```bash
# View recent logs
tail -f /tmp/ppl-meta-cameras.log

# Search for specific errors
grep -i "error\|exception" /tmp/ppl-meta-cameras.log
```

#### **3. Database Query Debugging**
```sql
-- Check active sessions
SELECT * FROM camera_sessions WHERE ended_at IS NULL;

-- Check camera status
SELECT device_id, name, status, updated_at FROM cameras;

-- Check recent activity
SELECT * FROM camera_sessions ORDER BY created_at DESC LIMIT 10;
```

---

## 📚 **ADDITIONAL RESOURCES**

### **API Documentation Links**

- **Swagger UI**: http://localhost:8005/docs
- **ReDoc**: http://localhost:8005/redoc
- **OpenAPI Spec**: http://localhost:8005/openapi.json

### **Development Tools**

- **Database Admin**: Use pgAdmin or similar for PostgreSQL management
- **API Testing**: Postman collection available for all endpoints
- **Monitoring**: Health endpoint provides comprehensive status information

### **Integration Examples**

- **Node.js**: Express middleware for camera proxy
- **Python**: FastAPI integration examples
- **React**: Camera management component library
- **Flutter**: Complete camera application widgets

---

*Last Updated: August 8, 2025*  
*Version: 1.0.0*  
*Documentation Status: Complete*
