# PPL Meta Mini Application

## Overview

**PPL Meta Mini** is a fully autonomous, standalone FastAPI application for face analytics and video processing. It is designed to operate independently, requiring no other PPL Meta services to be running. The application exposes a simple REST API for uploading and analyzing video files, providing face detection and grouping analytics without any authentication endpoints.

---

## Key Features

- **Standalone Operation**: No dependencies on external PPL Meta services.
- **FastAPI Backend**: Modern, async Python web framework.
- **No Authentication**: All endpoints are open for ease of integration and testing.
- **Face Detection & Grouping**: Detects faces in video frames and groups them using advanced clustering.
- **Video Preprocessing**: Optionally preprocesses videos for optimal face detection.
- **Temporary File Management**: Automatically cleans up old video files to manage storage.
- **Health & Info Endpoints**: Simple endpoints for service health and metadata.

---

## API Endpoints

### 1. Root Endpoint

- **GET /**  
  Returns service metadata and available endpoints.

  **Response Example:**
  ```json
  {
    "service": "PPL Meta Mini",
    "version": "1.1.0",
    "description": "Standalone Face Analytics with Video Processing",
    "endpoints": {
      "health": "/health",
      "docs": "/docs",
      "upload_and_analyze": "/api/v1/upload-and-analyze"
    }
  }
  ```

---

### 2. Health Check

- **GET /health**  
  Returns a simple health status for monitoring.

  **Response Example:**
  ```json
  {
    "status": "healthy",
    "service": "ppl-meta-mini",
    "version": "1.1.0"
  }
  ```

---

### 3. Upload and Analyze Video

- **POST /api/v1/upload-and-analyze**  
  Upload a video file for face detection and analytics.

  **Parameters:**
  - `file` (form-data): Video file (.mp4, .avi, .mov, .mkv)
  - `max_faces_per_frame` (int, default=10): Max faces to detect per frame
  - `proximity_threshold` (float, default=50.0): Grouping threshold
  - `confidence_threshold` (float, default=0.5): Detection confidence
  - `frame_interval` (int, default=15): Frame sampling interval

  **Process:**
  1. Cleans up old files in storage.
  2. Saves the uploaded video to a local directory.
  3. Optionally preprocesses the video for better detection.
  4. Runs face detection on sampled frames.
  5. Groups detected faces using clustering and quality analysis.
  6. Returns best-quality face data and file info.

  **Response Example:**
  ```json
  {
    "persons": {
      "group_1": {
        "face_id": "frame_15_face_1",
        "age": 28,
        "quality_score": 0.92,
        "bbox": [x1, y1, x2, y2]
      }
    },
    "file_info": {
      "storage_path": "/tmp/ppl-mini-storage/1632423423_video.mp4"
    }
  }
  ```

---

## Internal Architecture

### Core Services

- **MiniFaceDetectionService**: Handles frame-by-frame face detection with configurable confidence thresholds
- **FaceGroupingEngine**: Implements advanced clustering algorithms to group detected faces across frames
- **VideoPreprocessor**: Optimizes video files for improved face detection performance

## FaceGroupingEngine - Detailed Analysis

The `FaceGroupingEngine` is the most sophisticated component of the PPL Meta Mini application, implementing a percentage-based tolerance matching algorithm for accurate face tracking and grouping across video sequences.

### Core Algorithm: Percentage-Based Tracking

The engine employs a three-stage algorithm for optimal face tracking:

#### 1. Quality Scoring System

The engine evaluates face detection quality using multiple metrics:

- **Sharpness Assessment**: Uses Laplacian variance to measure image clarity

  ```python
  sharpness = cv2.Laplacian(gray_image, cv2.CV_64F).var()
  ```

- **Noise Detection**: Analyzes standard deviation to identify noise levels

  ```python
  noise_level = np.std(gray_image)
  ```

- **Exposure Analysis**: Evaluates histogram distribution for optimal lighting

  ```python
  exposure_score = 1.0 / (1.0 + abs(mean_intensity - 128) / 128)
  ```

- **Contrast Measurement**: Calculates dynamic range between light and dark areas

  ```python
  contrast = gray_image.max() - gray_image.min()
  ```

- **Weighted Scoring**: Combines all metrics with configurable weights:
  - Sharpness: 40% weight
  - Exposure: 30% weight
  - Contrast: 20% weight
  - Noise: 10% weight (inverted - lower noise = higher score)

#### 2. Tolerance-Based Position Matching

The algorithm uses percentage-based tolerances for robust face matching:

- **Default Tolerance**: 20% of coordinate values for X/Y position matching
- **Distance Calculations**:
  - X-axis tolerance: `abs(face1_x - face2_x) <= face1_x * 0.20`
  - Y-axis tolerance: `abs(face1_y - face2_y) <= face1_y * 0.20`
  - Euclidean distance: `sqrt((x1-x2)² + (y1-y2)²)`
- **Combined Distance Metric**: Weighted combination of coordinate differences and Euclidean distance

#### 3. Chronological Frame Processing

Sequential processing ensures temporal consistency:

- **Active Track Management**: Maintains real-time dictionary of face tracks with:
  - Current position coordinates
  - Last seen frame number
  - Classification ID
  - Original face detection data
- **Match Ranking**: Ranks potential matches by combined distance score
- **Track Lifecycle**: Creates new tracks for unmatched faces, updates existing tracks for matches

### Algorithm Workflow

```text
Input: Face detection data organized by frame
Process:
1. Initialize empty active_tracks dictionary
2. For each frame (chronologically):
   a. Extract all face detections in current frame
   b. For each face in frame:
      - Calculate distances to all active tracks
      - Find matches within tolerance threshold (20%)
      - Rank matches by combined distance score
      - If match found: update existing track, classify as "tracked"
      - If no match: create new track, classify as "new_track"
   c. Update active tracks with new positions and frame numbers
3. Generate comprehensive results with statistics and quality analysis
```

### Advanced Features

#### Quality Analysis & Best Face Selection

- **Per-Group Analysis**: Identifies highest quality face representation for each tracked individual
- **Age Detection Integration**: Optional DeepFace library integration for demographic analysis
- **Distance Estimation**: Calculates relative camera distance based on face size
- **Dynamic Frame Extraction**: Retrieves specific video frames for quality assessment

#### Performance Characteristics

- **Real-time Processing**: Optimized for minimal latency and memory usage
- **High Accuracy**: Percentage-based matching reduces false positives
- **Scalability**: Efficiently handles multiple simultaneous face tracks
- **Robustness**: Manages temporary occlusions and lighting variations
- **Memory Management**: Automatic cleanup of inactive tracks and temporary data

#### Configuration Parameters

- **Tolerance Percentage**: Adjustable matching threshold (default: 20%)
- **Quality Weights**: Configurable importance for different quality metrics
- **Age Detection**: Optional demographic analysis toggle
- **Frame Sampling**: Configurable processing frequency

### Output Data Structure

The engine produces comprehensive results including:

- **Group Tracking**: Merged group IDs with face counts and positions
- **Classification Results**: Detailed tracking data for every face instance
- **Quality Analysis**: Best quality faces per group with scores
- **Statistics**: Processing metrics and algorithm performance data
- **ID Mapping**: Translation between original detection IDs and merged group IDs

### Data Models

- **FaceDetectionData**: Structured format for storing face detection results including frame number, face ID, and position coordinates

### Storage Management

- **Temporary Storage**: Uses `/tmp/ppl-mini-storage` for uploaded and processed videos
- **Automatic Cleanup**: Maintains only the 3 most recent files to prevent disk space issues
- **File Naming**: Timestamps are used for unique file identification and cleanup ordering

---

## Technical Specifications

### Supported Video Formats
- MP4 (.mp4)
- AVI (.avi) 
- MOV (.mov)
- MKV (.mkv)

### Default Configuration
- **Service Port**: 8004
- **Host**: 0.0.0.0 (all interfaces)
- **CORS**: Enabled for all origins
- **Logging Level**: INFO

### Frame Processing
- **Sampling**: Every 15th frame by default (configurable)
- **Detection Confidence**: 0.5 minimum (configurable)
- **Max Faces**: 10 per frame (configurable)

---

## Usage Notes

- **No Authentication Required**: All endpoints are publicly accessible
- **Local Processing**: All analytics performed locally with no external API dependencies  
- **Private Network Deployment**: Designed for secure, internal network usage
- **Development & Testing**: Ideal for rapid prototyping and demonstration purposes
- **Edge Computing**: Suitable for offline or edge deployment scenarios

---

## Service Information

- **Application Name**: PPL Meta Mini
- **Version**: 1.1.0
- **Framework**: FastAPI with Uvicorn server
- **Runtime**: Python with OpenCV and machine learning libraries
- **Documentation**: Available at `/docs` (Swagger UI) when service is running