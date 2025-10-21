# PPL Meta Mini Age Estimation Backend - Local Development User Manual

## Overview

The **PPL Meta Mini Age Estimation Backend** is a local development application designed to analyze short video clips (1-3 seconds) and provide age estimation results to determine whether detected individuals are adults or underaged persons. This version also includes enhanced camera detection and connection capabilities with graceful cancellation support.

## Application Scope

- **Input**: Short video files (1-3 seconds duration recommended) or live camera feeds
- **Output**: Age estimation analysis with adult/underaged classification
- **Deployment**: Local Python service with REST API
- **Platform**: Cross-platform (Linux, macOS, Windows)
- **Enhanced Features**: Camera detection, live streaming, graceful cancellation

---

## Installation & Setup

### Prerequisites
- Python 3.8+ installed
- Minimum 2GB RAM available
- Port 8004 available
- Camera access permissions (for camera features)

### Local Development Setup

1. **Navigate to the project directory:**
   ```bash
   cd /Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-mini
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   cd src
   python main.py
   ```

4. **Access the application:**
   - Swagger UI: `http://localhost:8004/docs`
   - API Base URL: `http://localhost:8004/api/v1/`
   - Health Check: `http://localhost:8004/health`

---

## API Endpoints

### Primary Video Analysis Endpoint

**POST** `/api/v1/upload-and-analyze`

Upload and analyze video files for age estimation.

### Enhanced Camera Endpoints

**POST** `/api/v1/camera/detect-and-connect`

Detect available cameras and establish connection.

**POST** `/api/v1/camera/record-and-analyze`

Record video from connected camera and analyze for age estimation.

### Graceful Cancellation Support

All long-running operations support graceful cancellation:
- Camera detection and connection
- Video upload and analysis
- Live camera recording and analysis

Operations can be cancelled by the client, with proper resource cleanup and structured cancellation responses.

---

## Video Analysis Usage

### Example Request

```bash
curl -X 'POST' \
  'http://localhost:8004/api/v1/upload-and-analyze?max_faces_per_frame=10&proximity_threshold=50&confidence_threshold=0.5&frame_interval=5' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your-video.mp4;type=video/mp4'
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_faces_per_frame` | int | 10 | Maximum faces to detect per frame. **Recommended: Keep at 10** |
| `proximity_threshold` | float | 50 | Placeholder parameter (no effect on processing) |
| `confidence_threshold` | float | 0.5 | Face detection confidence. **Recommended: 0.5** |
| `frame_interval` | int | 15 | Frame sampling interval. **Recommended: 3-5 for 1-2 second videos** |
| `file` | file | - | Video file (MP4 recommended, 1-2 seconds duration) |

### Parameter Guidelines

- **confidence_threshold**:
  - `< 0.5`: May produce false positives
  - `0.5`: Recommended balance
  - `> 0.6`: May miss faces in lower quality frames

- **frame_interval**:
  - For 1-2 second videos: Use `3-5`
  - Higher values = faster processing, fewer samples
  - Lower values = more thorough analysis, slower processing

---

## Camera Features Usage

### Camera Detection

**Example Request:**
```bash
curl -X 'POST' \
  'http://localhost:8004/api/v1/camera/detect-and-connect' \
  -H 'accept: application/json'
```

**Response:**
```json
{
  "status": "success",
  "connection_status": "connected",
  "camera_info": {
    "device_index": 0,
    "resolution": "640x480",
    "fps": 30.0
  },
  "message": "Camera connected successfully"
}
```

### Live Camera Analysis

**Example Request:**
```bash
curl -X 'POST' \
  'http://localhost:8004/api/v1/camera/record-and-analyze?duration=2&max_faces_per_frame=10&confidence_threshold=0.5&frame_interval=3' \
  -H 'accept: application/json'
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `duration` | int | 2 | Recording duration in seconds |
| `max_faces_per_frame` | int | 10 | Maximum faces to detect per frame |
| `confidence_threshold` | float | 0.5 | Face detection confidence |
| `frame_interval` | int | 3 | Frame sampling interval |

---

## Response Format

### Successful Analysis Response

```json
{
  "persons": {
    "1": {
      "face_id": "frame_120_face_1",
      "frame_number": 120,
      "quality_score": 0.83,
      "bbox": [88, 410, 413, 735],
      "age_detection": {
        "estimated_age": 37
      },
      "distance": 9.47
    },
    "2": {
      "face_id": "frame_165_face_1",
      "frame_number": 165,
      "quality_score": 0.786,
      "bbox": [44, 409, 388, 753],
      "age_detection": {
        "estimated_age": 36
      },
      "distance": 8.45
    }
  },
  "file_info": {
    "storage_path": "/tmp/ppl_mini_video_processing/preprocessed_1753891163_video.mp4"
  }
}
```

### Cancellation Response

When operations are cancelled gracefully:

```json
{
  "status": "cancelled",
  "message": "Operation cancelled by client",
  "cleanup_status": "completed"
}
```

### Response Fields

| Field | Description |
|-------|-------------|
| `face_id` | Unique identifier for detected face |
| `frame_number` | Frame where face was detected |
| `quality_score` | Face quality assessment (0.0-1.0) |
| `bbox` | Bounding box coordinates [x1, y1, x2, y2] |
| `estimated_age` | Predicted age in years |
| `distance` | Relative distance from camera (analogous units) |
| `storage_path` | Temporary file location |

---

## Age Classification Logic

### Underaged Detection Criteria

**Trigger an underaged alert when ALL conditions are met:**

1. `estimated_age < 30`
2. `distance ≤ 10` AND `distance > 2`
3. `quality_score > 0.250`

### Important Notes

- **Distance < 2**: Likely false positive (too close/distorted)
- **Distance > 10**: Low confidence due to distance
- **Quality Score < 0.250**: Insufficient image quality for reliable estimation

### Age Estimation Accuracy

- **Optimal conditions**: Near camera, good lighting, no motion blur
- **Real-world deviation**: Age estimates deviate from actual age based on:
  - Distance from camera
  - Lighting conditions
  - Motion blur
  - Frame quality
  - Facial angle and expression
  - Women (heavy) makeup

---

## Best Practices

### Video Recommendations

- **Duration**: 1-2 seconds optimal
- **Sampling (frame interval)**: frame interval 3 or close. Use > 3 only for very "weak" machines
- **Quality**: Good lighting, minimal motion blur
- **Format**: MP4 recommended
- **Resolution**: Standard definition sufficient
- **Content**: Clear facial visibility

### Camera Usage Guidelines

- **Permissions**: Ensure camera access permissions are granted
- **Lighting**: Good lighting improves detection accuracy
- **Positioning**: Position camera for clear facial visibility
- **Distance**: Maintain appropriate distance (2-10 units for best results)

### Performance Optimization

- Use recommended parameter values
- Shorter videos process faster
- Good lighting improves accuracy
- Stable camera reduces false detections
- Operations can be cancelled if taking too long

### Integration Guidelines

- **Primary person**: Use the person with the smallest `distance` value
- **Multiple detections**: Same person may appear multiple times; use closest detection
- **Confidence threshold**: Combine `quality_score`, `distance`, and `estimated_age` for decisions
- **Cancellation**: Implement cancel buttons for long-running operations in your UI

---

## Graceful Cancellation Features

### How It Works

- **Client Disconnection**: Operations detect when clients disconnect and stop processing
- **Resource Cleanup**: Cameras are released, temporary files cleaned up
- **Structured Responses**: Clear cancellation status messages returned
- **Service Stability**: Service remains healthy after cancellation events

### Supported Operations

1. **Camera Detection**: Can be cancelled during device scanning
2. **Camera Connection**: Can be cancelled during connection establishment
3. **Video Analysis**: Can be cancelled during frame-by-frame processing
4. **Live Recording**: Can be cancelled during recording and analysis

### Testing Cancellation

You can test cancellation functionality using the provided test script:

```bash
python test_cancellation.py
```

This will validate that all cancellation scenarios work properly.

---

## Data Management

### Automatic Cleanup

- Application automatically stores processed videos at `storage_path`
- **Auto-deletion**: Only the 3 most recent videos are retained
- **Cleanup trigger**: Runs on each new video upload
- **Camera resources**: Automatically released on cancellation or completion

### Quality Assurance & Training

For algorithm improvement and feedback:

1. **Retain**: Last 3 processed videos and their JSON responses
2. **Provide feedback**: Submit videos with actual age verification
3. **Include**: Both `storage_path` files and corresponding API responses

---

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Check what's using port 8004
lsof -i :8004

# Kill existing process if needed
pkill -f "python.*main.py"
```

**Service won't start:**
```bash
# Check Python dependencies
pip install -r requirements.txt

# Check if all imports work
python -c "from src.main import app"
```

**Camera not detected:**
- Check camera permissions in system settings
- Ensure camera is not used by another application
- Try different camera indices if multiple cameras available
- Check camera connection and drivers

**No faces detected:**
- Check video quality and lighting
- Reduce `confidence_threshold` to 0.4
- Ensure faces are clearly visible
- Try shorter `frame_interval` (e.g., 2)

### Health Check

Test the service is running:
```bash
curl http://localhost:8004/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "ppl-meta-mini",
  "version": "1.1.0"
}
```

### Debug Mode

For detailed logging, modify the service startup or check logs for debugging information.

---

## Development Features

### Testing Suite

The application includes comprehensive testing capabilities:

- **Cancellation Tests**: Validate graceful cancellation behavior
- **Health Monitoring**: Continuous service health validation
- **Camera Integration**: Test camera detection and connection
- **API Validation**: Verify response structures and error handling

### API Documentation

- **Interactive Docs**: Available at `/docs` endpoint
- **OpenAPI Schema**: Available at `/openapi.json`
- **Real-time Testing**: Use Swagger UI for interactive API testing

---

## Technical Specifications

- **Language**: Python 3.8+
- **Framework**: FastAPI
- **Memory Usage**: ~512MB-1GB during processing
- **Platform**: Cross-platform (Linux, macOS, Windows)
- **Dependencies**: See `requirements.txt`

### Enhanced Features (Version 2.19.17+)

- ✅ **Graceful Cancellation**: All long-running operations support cancellation
- ✅ **Camera Integration**: Live camera detection and analysis
- ✅ **Resource Management**: Automatic cleanup of cameras and temporary files
- ✅ **Error Handling**: Structured error responses with proper status codes
- ✅ **Performance Monitoring**: Built-in health checks and status reporting

---

## Version History

- **Version 1.1.0**: Core video analysis functionality
- **Version 2.19.17**: Enhanced camera support, graceful cancellation, improved resource management

---

## Support & Development

- **Current Version**: 2.19.17 (Local Development)
- **API Documentation**: Available at `/docs` endpoint when running
- **Source Code**: Local development environment
- **Testing**: Comprehensive test suite included

---

*For technical support, development questions, or algorithm training data submission, please provide the processed video files and their corresponding JSON responses along with system logs.*