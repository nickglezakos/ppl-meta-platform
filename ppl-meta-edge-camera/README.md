# Edge Camera Application

Lightweight Python application for edge devices that captures video from cameras and streams to the ppl-meta platform.

## Features

- USB/CSI camera capture with OpenCV
- MJPEG frame encoding
- Streaming to ppl-meta-cameras service
- Auto-registration with discovery service
- Health monitoring endpoints
- Configurable via YAML

## Requirements

- Python 3.9+
- USB or CSI camera
- Access to ppl-meta platform services

## Installation

1. **Create virtual environment**:
```bash
cd ppl-meta-edge-camera
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure application**:
Edit `config/default.yaml` to match your setup:
```yaml
device:
  id: "edge-camera-001"  # Unique device ID
  name: "My Edge Camera"
  location: "test-location"

camera:
  device_id: 0  # Camera index (0 for default USB camera)
  resolution:
    width: 1280
    height: 720
  fps: 15

platform:
  cameras_url: "http://localhost:8005"      # Cameras service
  discovery_url: "http://localhost:8010"    # Discovery service
```

## Usage

### Start the application:
```bash
cd src
python main.py
```

### Check health:
```bash
curl http://localhost:9001/health
```

### Get detailed status:
```bash
curl http://localhost:9001/status
```

## Testing with Local Platform

1. **Start platform services**:
```bash
# From ppl-meta-code directory
# Start cameras service (port 8005)
# Start discovery service (port 8010)
```

2. **Start edge camera**:
```bash
cd ppl-meta-edge-camera/src
python main.py
```

3. **Verify streaming**:
Check cameras service logs for incoming frames.

## Configuration

### Environment Variables
Override config values with environment variables:
- `DEVICE_ID`: Device identifier
- `PLATFORM_CAMERAS_URL`: Cameras service URL
- `PLATFORM_DISCOVERY_URL`: Discovery service URL

### Camera Settings
- `device_id`: Camera index (0, 1, 2, etc.)
- `resolution`: Frame width and height
- `fps`: Frames per second (15 recommended for edge)
- `format`: Encoding format (mjpeg)

### Stream Settings
- `encoding`: Frame encoding (mjpeg)
- `quality`: JPEG quality 0-100 (80 recommended)
- `chunk_size`: Network chunk size

## Architecture

```
┌─────────────────┐
│  USB Camera     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ CameraCapture   │ ──> Capture frames
└────────┬────────┘
         │
         v
┌─────────────────┐
│ FrameEncoder    │ ──> Encode to MJPEG
└────────┬────────┘
         │
         v
┌─────────────────┐
│ FrameBuffer     │ ──> Buffer frames
└────────┬────────┘
         │
         v
┌─────────────────┐
│StreamingClient  │ ──> Send to platform
└────────┬────────┘
         │
         v
┌─────────────────┐
│ ppl-meta-cameras│
└─────────────────┘
```

## API Endpoints

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "uptime_seconds": 123.45,
  "camera": "active",
  "streaming": "active",
  "registration": "registered"
}
```

### GET /status
Detailed status with statistics.

**Response**:
```json
{
  "status": "ok",
  "camera_stats": {
    "device_id": 0,
    "resolution": {"width": 1280, "height": 720},
    "fps": 15,
    "frame_count": 1500,
    "is_healthy": true
  },
  "streaming_stats": {
    "is_streaming": true,
    "frames_sent": 1450,
    "errors_count": 2
  }
}
```

### GET /config
Get current configuration.

## Troubleshooting

### Camera not detected
```bash
# List available cameras on macOS/Linux
ls /dev/video*

# Test camera with OpenCV
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Connection issues
- Verify platform services are running
- Check URLs in config/default.yaml
- Check network connectivity

### Performance issues
- Reduce resolution (640x480)
- Reduce FPS (10-15)
- Reduce JPEG quality (60-70)

## Next Steps

1. ✅ Test with USB camera on laptop
2. Test integration with cameras service
3. Deploy to Raspberry Pi 5
4. Add CSI camera support
5. Create systemd service for auto-start

## License

Part of ppl-meta-platform
