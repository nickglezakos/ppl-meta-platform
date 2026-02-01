# Edge Camera Project

## Overview
Lightweight Python application for edge devices (laptop/RPi5) that captures video from USB/CSI cameras and streams to the ppl-meta platform for processing.

## Project Goals
1. Capture video from connected camera (USB on laptop, CSI/USB on RPi5)
2. Stream video to ppl-meta-vision/cameras service
3. Register device with discovery service
4. Minimal resource usage for edge deployment
5. Platform triggers control (future: coordinate with signage app)

## Architecture

### Components
- **Camera Capture**: OpenCV/GStreamer for video acquisition
- **Stream Handler**: Efficient encoding and transmission to platform
- **Registration Client**: Auto-register with discovery service
- **Health Monitor**: Report status to platform

### Platform Integration
- **Streams to**: ppl-meta-cameras service (port 8005)
- **Registers with**: ppl-meta-discovery service (port 8010)
- **Controlled by**: ppl-meta-orchestrator (triggers/commands)

## Development Phases

### Phase 1: Laptop Development & Testing
**Goal**: Working edge camera with USB camera streaming to platform

#### Tasks
1. Project structure setup
2. Camera capture implementation (OpenCV)
3. Stream encoding (MJPEG/H.264)
4. Platform registration
5. Stream transmission to cameras service
6. Health check endpoints
7. Configuration management

#### Testing Environment
- Laptop with USB camera
- Local ppl-meta platform running
- Network connectivity tests

### Phase 2: Signage Integration (Future)
- Communication protocol with signage app
- Resource management (camera priority modes)
- Trigger-based control from platform

### Phase 3: RPi5 Deployment (Future)
- systemd service configuration
- CSI camera support
- Performance optimization
- Multi-device deployment

## Technical Requirements

### Dependencies
```
opencv-python
requests
websockets
pydantic
python-dotenv
uvicorn
fastapi
```

### Configuration
```yaml
device:
  id: edge-camera-001
  name: "Laptop USB Camera"
  location: "test-location"

camera:
  device_id: 0  # USB camera index
  resolution: [1280, 720]
  fps: 15
  format: mjpeg

platform:
  cameras_url: http://localhost:8005
  discovery_url: http://localhost:8010
  health_check_interval: 30

stream:
  encoding: mjpeg
  quality: 80
  buffer_size: 10
```

## Project Structure
```
ppl-meta-edge-camera/
├── src/
│   ├── main.py              # Entry point
│   ├── camera/
│   │   ├── capture.py       # Camera acquisition
│   │   └── encoder.py       # Video encoding
│   ├── streaming/
│   │   ├── client.py        # Stream transmission
│   │   └── buffer.py        # Frame buffering
│   ├── platform/
│   │   ├── registration.py  # Device registration
│   │   └── health.py        # Health checks
│   └── config.py            # Configuration management
├── config/
│   └── default.yaml         # Default configuration
├── requirements.txt
├── README.md
└── tests/
```

## API Endpoints (Local)

### Health Check
```
GET /health
Response: {"status": "ok", "camera": "active", "streaming": true}
```

### Camera Status
```
GET /status
Response: {
  "device_id": "edge-camera-001",
  "camera_active": true,
  "streaming": true,
  "fps": 15,
  "resolution": [1280, 720]
}
```

### Configuration
```
GET /config
PUT /config
```

## Platform Communication

### Registration Flow
1. Edge camera starts → registers with discovery service
2. Discovery service assigns device ID
3. Edge camera opens stream to cameras service
4. Platform validates stream and starts processing

### Streaming Protocol
- **Transport**: HTTP chunked transfer / WebSocket
- **Format**: MJPEG frames or H.264 stream
- **Metadata**: Timestamp, device ID, frame number

## Development Workflow

1. **Setup**: Create project structure and install dependencies
2. **Camera Capture**: Implement basic USB camera capture with OpenCV
3. **Local Testing**: Display captured frames locally
4. **Stream Encoding**: Add MJPEG encoding
5. **Platform Registration**: Implement discovery service registration
6. **Stream Transmission**: Send frames to cameras service
7. **Health Monitoring**: Add health check endpoints
8. **Integration Testing**: Test with full platform running
9. **Configuration**: Externalize settings to config file
10. **Documentation**: Usage and deployment instructions

## Testing Checklist

- [ ] USB camera detection
- [ ] Video capture at configured resolution/fps
- [ ] Frame encoding (MJPEG)
- [ ] Registration with discovery service
- [ ] Stream transmission to cameras service
- [ ] Platform receives and processes stream
- [ ] Health check responses
- [ ] Reconnection on network failure
- [ ] Graceful shutdown
- [ ] Resource cleanup

## Next Steps (Post-Laptop Testing)

1. **Signage Integration**: Add communication layer for signage app
2. **RPi5 Testing**: Test with CSI camera on RPi5
3. **Docker Build**: Create Dockerfile for containerized deployment
4. **systemd Service**: Create service file for native deployment
5. **Multi-Device**: Test with multiple edge cameras
6. **Production**: Deploy to RPi5 devices in field

## Notes

- Keep dependencies minimal for edge deployment
- Prioritize efficiency over features
- Design for network resilience (reconnection, buffering)
- Platform-first: Edge camera is thin client, platform does heavy lifting
- Configuration via environment variables + config file
