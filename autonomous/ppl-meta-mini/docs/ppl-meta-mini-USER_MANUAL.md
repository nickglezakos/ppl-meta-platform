# PPL Meta Mini Age Estimation Backend - User Manual

## Overview

The **PPL Meta Mini Age Estimation Backend** is a headless application designed to analyze short video clips (1-3 seconds) and provide age estimation results to determine whether detected individuals are adults or underaged persons.

## Application Scope

- **Input**: Short video files (1-3 seconds duration recommended)
- **Output**: Age estimation analysis with adult/underaged classification
- **Deployment**: Dockerized headless service with REST API
- **Platform**: Linux containers (compatible with Windows Docker Desktop VM)

---

## Installation & Setup

### Prerequisites
- Docker Desktop installed and running
- Minimum 2GB RAM available for the container
- Port 8004 (or custom port) available

### Download & Installation

1. **Download the application:**
   - Download from: https://we.tl/t-5SGZZtgCrl
   - Available until: Fri 31 Jul 2025 (link will be updated)
   - File: `ppl-meta-mini-beta085.tar` (1.5GB)

2. **Load the Docker image:**

   **Linux/macOS:**
   ```bash
   docker load -i ppl-meta-mini-beta085.tar
   ```

   **Windows Command Prompt:**
   ```cmd
   docker load < ppl-meta-mini-beta085.tar
   ```

3. **Run the application:**

   **Command Line:**
   ```bash
   docker run -d --name ppl-meta-mini -p 8004:8004 nickglezakos/ppl-meta-mini-beta085:latest
   ```

   **Docker Desktop GUI:**
   - Navigate to Images → `nickglezakos/ppl-meta-mini-beta085:latest`
   - Click "Run"
   - Set Host Port: `8004` (or your preferred port like `8005`)
   - Click "Run"

4. **Access the application:**
   - Swagger UI: `http://localhost:8004/docs`
   - API Base URL: `http://localhost:8004/api/v1/`

---

## API Usage

### Primary Endpoint

**POST** `/api/v1/upload-and-analyze`

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

## Response Format

### Successful Response Example

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
- **Sampling (frame insterval)**: frame interval 3 or close. Use > 3 only for very "weak" machines
- **Quality**: Good lighting, minimal motion blur
- **Format**: MP4 recommended
- **Resolution**: Standard definition sufficient
- **Content**: Clear facial visibility

### Performance Optimization

- Use recommended parameter values
- Shorter videos process faster
- Good lighting improves accuracy
- Stable camera reduces false detections

### Integration Guidelines

- **Primary person**: Use the person with the smallest `distance` value
- **Multiple detections**: Same person may appear multiple times; use closest detection
- **Confidence threshold**: Combine `quality_score`, `distance`, and `estimated_age` for decisions

---

## Data Management

### Automatic Cleanup

- Application automatically stores processed videos at `storage_path`
- **Auto-deletion**: Only the 3 most recent videos are retained
- **Cleanup trigger**: Runs on each new video upload

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
# Use different port
docker run -d --name ppl-meta-mini -p 8005:8004 nickglezakos/ppl-meta-mini-beta085:latest
# Access at http://localhost:8005/docs
```

**Container won't start:**
```bash
# Check logs
docker logs ppl-meta-mini

# Restart container
docker restart ppl-meta-mini
```

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
{"status": "healthy", "service": "ppl-meta-mini"}
```

---

## Technical Specifications

- **Container Size**: ~1.5GB
- **Memory Usage**: ~512MB-1GB during processing
- **Platform**: Linux AMD64 (Windows Docker Desktop compatible)

---

## Support & Updates

- **Current Version**: Beta085
- **Download Link**: https://we.tl/t-5SGZZtgCrl (expires Fri 31 Jul 2025)
- **API Documentation**: Available at `/docs` endpoint when running
- **Updates**: Link will be refreshed before expiration

---

*For technical support or algorithm training data submission, please provide the processed video files and their corresponding JSON responses.*
