# Camera Video and Data Objects Management

**Document Version:** 1.0  
**Last Updated:** November 12, 2025  
**Service:** ppl-meta-cameras  
**Port:** 8005

---

## Table of Contents

1. [Camera Recording Functionalities](#camera-recording-functionalities)
   - [Recording Architecture Overview](#recording-architecture-overview)
   - [Video Segmentation System](#video-segmentation-system)
   - [Recording Session Lifecycle](#recording-session-lifecycle)
   - [Face Detection Integration](#face-detection-integration)
   - [Data Flow Diagram](#data-flow-diagram)
   - [Database Schema](#database-schema)
   - [Recording Profiles](#recording-profiles)
   - [Storage and Media Service Integration](#storage-and-media-service-integration)

---

## Camera Recording Functionalities

### Recording Architecture Overview

The PPL Meta camera recording system implements a sophisticated multi-service architecture that handles continuous video recording, automatic segmentation, and real-time face detection. The system is designed around the concept of **recording sessions** that manage the entire lifecycle of a camera recording from start to completion.

#### Key Components

1. **Camera Detection Service** (`camera_detection.py`): Manages camera discovery, connections, and recording operations
2. **Recording Session Service** (`recording_session_service.py`): Business logic for session management
3. **Orchestrator Client** (`orchestrator_client.py`): Event publishing to orchestrator service
4. **Database Models**: SQLAlchemy models for persistence
5. **Media Service Integration**: Upload and storage coordination

---

### Video Segmentation System

#### Overview

Cameras record video in **segments** of predefined duration rather than single continuous files. This segmentation approach provides several benefits:

- **Memory Management**: Prevents single file from growing too large
- **Processing Efficiency**: Smaller segments are easier to process for face detection
- **Parallel Processing**: Multiple segments can be processed simultaneously
- **Failure Recovery**: If recording fails, only current segment is lost
- **Storage Optimization**: Individual segments can be archived or deleted independently

#### Segment Configuration

Segments are configured through `RecordingMetadata` with two key parameters:

```python
class RecordingMetadata:
    segment_interval_seconds = Column(Integer, nullable=True)
    segment_duration_seconds = Column(Integer, default=30)
```

**Parameters:**

- **`segment_duration_seconds`** (default: 30):
  - Duration of each video segment in seconds
  - Each segment is saved as separate file
  - Typical values: 15-60 seconds
  - Default: 30 seconds provides good balance between file size and processing overhead

- **`segment_interval_seconds`** (optional):
  - Interval between automatic segment captures
  - If `null`: Manual segmentation only
  - If set: Automatic periodic segmentation
  - Minimum: 5 seconds
  - Maximum: 3600 seconds (1 hour)

#### Segment File Naming

Each segment is saved with a unique identifier:

```python
file_name = f"camera_{device_id}_{segment_number}.mp4"
# Example: camera_usb_camera_0_001.mp4
#          camera_usb_camera_0_002.mp4
```

---

### Recording Session Lifecycle

#### 1. Session Creation

When a recording starts, a `RecordingSession` is created:

```python
session = RecordingSession(
    session_uuid=str(uuid.uuid4()),
    camera_id=camera.id,
    user_id=user_id,
    status="active",
    recording_quality="high",
    started_at=datetime.utcnow()
)
```

**Initial State:**
- **Status**: `active`
- **Session UUID**: Unique identifier for entire recording session
- **Camera Reference**: Links to camera in database
- **User Context**: Tracks which user initiated recording
- **Timestamp**: Records exact start time

#### 2. Metadata Configuration

Associated metadata is created with recording parameters:

```python
metadata = RecordingMetadata(
    session_uuid=session_uuid,
    segment_duration_seconds=30,
    auto_face_detection_enabled=True,
    video_codec="h264",
    audio_enabled=False,
    resolution_width=1920,
    resolution_height=1080,
    fps=30,
    face_detection_method="enhanced-v2",
    quality_preset="balanced"
)
```

**Key Configuration:**
- **Codec Settings**: Video/audio codec selection
- **Resolution**: Frame dimensions
- **FPS**: Frames per second capture rate
- **Face Detection**: Method and automation settings
- **Quality Preset**: Balanced, high, or low quality

#### 3. Video Capture and Segmentation

The system captures frames continuously and creates segments:

```python
# Frame capture loop
while recording_active:
    ret, frame = camera.read()
    
    if ret:
        # Write frame to current segment
        video_writer.write(frame)
        frame_count += 1
        
        # Check if segment duration reached
        current_duration = (time.time() - segment_start_time)
        
        if current_duration >= segment_duration_seconds:
            # Finalize current segment
            video_writer.release()
            
            # Save segment to database
            recording_file = RecordingFile(
                session_uuid=session_uuid,
                file_uuid=str(uuid.uuid4()),
                file_path=segment_path,
                file_size_bytes=os.path.getsize(segment_path),
                duration_seconds=current_duration,
                created_at=datetime.utcnow()
            )
            
            # Upload to media service
            media_uuid = await upload_segment_to_media(segment_path)
            
            # Trigger face detection
            await trigger_face_detection(media_uuid)
            
            # Start new segment
            segment_number += 1
            segment_start_time = time.time()
```

#### 4. Real-Time Monitoring

During recording, the session is updated with real-time metrics:

```python
# Heartbeat updates
session.current_duration_seconds = (datetime.utcnow() - session.started_at).total_seconds()
session.estimated_file_size_bytes = calculate_estimated_size()
session.frames_recorded = total_frame_count
session.average_fps = total_frame_count / session.current_duration_seconds
session.last_heartbeat = datetime.utcnow()
```

**Tracked Metrics:**
- Current recording duration
- Estimated total file size
- Total frames recorded
- Average FPS (quality indicator)
- Last heartbeat timestamp (for monitoring)

#### 5. Segment Upload to Media Service

Each completed segment is uploaded to the media service:

```python
async def upload_segment_to_media(
    file_path: str,
    device_id: str,
    user_id: str,
    camera_name: str,
    metadata: Dict
) -> str:
    """Upload video segment to media service."""
    
    # Prepare form data
    data = aiohttp.FormData()
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
        
    data.add_field('file', file_content, 
                   filename=os.path.basename(file_path),
                   content_type='video/mp4')
    
    # Metadata fields
    data.add_field('media_type', 'video')
    data.add_field('user_id', user_id)
    data.add_field('title', f'Camera Recording - {device_id}')
    data.add_field('description', f'Segment from camera {camera_name}')
    data.add_field('device_name', camera_name)
    data.add_field('tags', f'["camera","recording","{device_id}"]')
    data.add_field('is_public', 'false')
    
    # Upload via HTTP POST
    async with session.post(
        f'{MEDIA_SERVICE_URL}/api/v1/media/upload',
        data=data,
        headers={'Authorization': f'Bearer {token}'},
        timeout=aiohttp.ClientTimeout(total=60)
    ) as response:
        if response.status == 200:
            result = await response.json()
            media_uuid = result['uuid']
            logger.info(f'✅ Uploaded segment as media {media_uuid}')
            return media_uuid
        else:
            raise Exception(f'Upload failed: {response.status}')
```

**Upload Process:**
1. Read segment file into memory
2. Create multipart form data with file and metadata
3. POST to media service `/api/v1/media/upload` endpoint
4. Receive `media_uuid` in response
5. Store `media_uuid` in `RecordingFile` record

#### 6. Camera Collection Assignment

Each camera has an associated collection for organizing recordings:

```python
async def find_or_create_camera_collection(
    device_id: str,
    user_id: str
) -> str:
    """Find existing camera collection or create new one."""
    
    # Search for existing collection
    search_response = await session.get(
        f'{MEDIA_SERVICE_URL}/api/v1/collections/search',
        params={
            'user_id': user_id,
            'collection_name': f'Camera: {camera_name}'
        }
    )
    
    if search_response.status == 200:
        collections = await search_response.json()
        if collections:
            return collections[0]['id']
    
    # Create new collection
    collection_data = {
        'name': f'Camera: {camera_name}',
        'description': f'Recordings from camera {device_id}',
        'user_id': user_id,
        'is_public': False,
        'tags': ['camera', device_id]
    }
    
    create_response = await session.post(
        f'{MEDIA_SERVICE_URL}/api/v1/collections',
        json=collection_data
    )
    
    result = await create_response.json()
    return result['id']
```

**Collection Organization:**
- One collection per camera
- Named: `"Camera: {camera_name}"`
- Contains all segments from that camera
- Organized by user
- Enables easy retrieval of all recordings from specific camera

#### 7. Session Completion

When recording stops:

```python
# Stop recording
session.status = 'completed'
session.stopped_at = datetime.utcnow()

# Calculate final statistics
total_duration = (session.stopped_at - session.started_at).total_seconds()
total_segments = len(session.files)
total_size = sum(f.file_size_bytes for f in session.files)

logger.info(
    f"Recording completed: {total_segments} segments, "
    f"{total_duration:.1f}s total, {total_size} bytes"
)
```

**Final State:**
- **Status**: Changed to `completed`
- **Stopped Timestamp**: Recorded
- **File Count**: Total number of segments
- **Total Duration**: Calculated from start/stop times
- **Total Size**: Sum of all segment sizes

---

### Face Detection Integration

#### Parallel Processing Architecture

**IMPORTANT**: Face detection operates in **parallel** with ongoing video recording. This means:

- **Video Recording Lifecycle**: Continues producing new segments every 30 seconds
- **Face Detection Lifecycle**: Processes previously uploaded segments asynchronously
- **Non-Blocking**: Face detection does NOT wait for recording to complete
- **Concurrent Sessions**: Multiple face detection sessions can run simultaneously for different segments

**Example Timeline:**

```
Time    Recording                   Face Detection
-----------------------------------------------------------
0:00    Start recording
0:30    Segment 1 saved & uploaded → Face Detection Session 1 starts
1:00    Segment 2 saved & uploaded → Face Detection Session 2 starts
        ↓ (still recording)          ↓ (Session 1 still processing)
1:30    Segment 3 saved & uploaded → Face Detection Session 3 starts
2:00    Segment 4 saved & uploaded → Face Detection Session 4 starts
        ↓ (still recording)          Session 1 completes (60s processing)
2:30    Segment 5 saved & uploaded → Face Detection Session 5 starts
3:00    Stop recording               Sessions 2-5 continue processing
3:10                                 Session 2 completes
3:20                                 Session 3 completes
3:30                                 Session 4 completes
3:40                                 Session 5 completes
```

**Key Points:**

1. **Asynchronous Processing**: Face detection happens in the background while recording continues
2. **No Recording Delay**: Segment production is NOT blocked by face detection
3. **Independent Services**: Camera Service and Vision Service operate independently
4. **Queue Management**: Orchestrator manages multiple concurrent face detection sessions
5. **Resource Isolation**: Face detection uses separate compute resources (Vision Service)

#### Automatic Face Detection on Save

The system implements **automatic face detection** that triggers immediately after each segment is uploaded:

```python
async def check_and_trigger_face_detection(
    media_uuid: str
) -> None:
    """Check global setting and trigger face detection if enabled."""
    
    # Check face_detection_on_save setting
    setting_url = f'{NODE_SERVICE_URL}/api/v1/settings/face_detection_on_save'
    
    response = await session.get(setting_url)
    
    if response.status == 200:
        setting_data = await response.json()
        is_enabled = setting_data.get('value') == 'true'
        
        if is_enabled:
            logger.info(f'🎯 Face detection enabled, triggering for {media_uuid}')
            await trigger_face_detection_workflow(media_uuid)
        else:
            logger.info(f'🎯 Face detection disabled, skipping for {media_uuid}')
```

#### Face Detection Workflow

When enabled, face detection uses **Enhanced Logic V2**:

```python
async def trigger_face_detection_workflow(
    media_uuid: str
) -> None:
    """Trigger Enhanced Logic V2 face detection workflow."""
    
    # Call orchestrator service
    orchestrator_url = (
        f'{ORCHESTRATOR_SERVICE_URL}/api/v1/media/'
        f'{media_uuid}/faces/enhanced-v2'
    )
    
    response = await session.get(orchestrator_url)
    
    if response.status == 200:
        result = await response.json()
        
        session_uuid = result['session_uuid']
        total_faces = result['total_faces']
        source = result['source']
        processing_time = result['processing_time']
        
        logger.info(
            f'🎯 ✅ Enhanced Logic V2 completed: '
            f'{total_faces} faces found '
            f'({source}, {processing_time:.3f}s, '
            f'session: {session_uuid})'
        )
```

**Face Detection Process:**
1. **Trigger**: Automatic after segment upload (if enabled)
2. **Service**: Orchestrator service coordinates detection
3. **Method**: Enhanced Logic V2 (advanced face detection algorithm)
4. **Output**: Face bounding boxes, confidence scores, timestamps
5. **Storage**: Results stored in vision service database
6. **Session Tracking**: Unique session UUID for each detection run

#### Enhanced Logic V2 Features

The face detection method provides:

- **High Accuracy**: Advanced neural network models
- **Multiple Faces**: Detects multiple faces per frame
- **Confidence Scores**: Each face has confidence rating (0.0-1.0)
- **Bounding Boxes**: Precise face location in frame
- **Frame-by-Frame**: Processes every frame for maximum detection
- **Distance Calculation**: Estimates distance from camera (optional)
- **Quality Metrics**: Face quality scores for best face selection

#### Face Detection Configuration

Configuration through `RecordingMetadata`:

```python
metadata = RecordingMetadata(
    auto_face_detection_enabled=True,      # Enable/disable automatic detection
    face_detection_method='enhanced-v2',   # Detection algorithm
    # ... other fields
)
```

**Available Methods:**
- `two_stage`: Two-stage detection (faster, less accurate)
- `enhanced-v2`: Enhanced Logic V2 (slower, more accurate) [**DEFAULT**]

#### Detection Results Storage

Face detection results are stored separately from video data:

```
RecordingSession (Camera DB)
    └── RecordingFile (segment)
            └── media_uuid → Media Service
                               └── Face Detection Results (Vision DB)
                                     └── Face bounding boxes
                                     └── Confidence scores
                                     └── Frame timestamps
                                     └── Person groupings
```

---

### Concurrent Lifecycle Architecture

#### Two Parallel Lifecycles

The system operates with **two independent, concurrent lifecycles**:

##### 1. Video Segment Production Lifecycle (Camera Service)

```
┌─────────────────────────────────────────────────────┐
│         VIDEO SEGMENT PRODUCTION LIFECYCLE          │
│              (Continuous, Non-Blocking)             │
└─────────────────────────────────────────────────────┘

Loop while recording:
  1. Capture frames from camera
  2. Write frames to current segment
  3. Monitor segment duration
  4. When duration >= 30 seconds:
     a. Finalize segment file
     b. Save to local storage
     c. Create RecordingFile record
     d. Trigger upload (async)
     e. Start new segment
  5. Repeat step 1

✓ This loop runs continuously
✓ Does NOT wait for uploads to complete
✓ Does NOT wait for face detection
✓ Only stops when user stops recording
```

##### 2. Face Detection Processing Lifecycle (Vision Service)

```
┌─────────────────────────────────────────────────────┐
│      FACE DETECTION PROCESSING LIFECYCLE            │
│           (Per Segment, Asynchronous)               │
└─────────────────────────────────────────────────────┘

For each uploaded segment:
  1. Upload completes → media_uuid received
  2. Check face_detection_on_save setting
  3. If enabled:
     a. Call Orchestrator Service
     b. Orchestrator creates face detection session
     c. Orchestrator calls Vision Service
     d. Vision Service processes video:
        - Loads video from media service
        - Extracts frames
        - Runs face detection AI model
        - Generates bounding boxes
        - Calculates confidence scores
        - Stores results in Vision DB
     e. Returns results to Orchestrator
     f. Session marked complete
  4. Process completes (typically 30-120 seconds)

✓ Multiple sessions run concurrently
✓ Independent of recording process
✓ Uses separate compute resources
✓ Results stored separately from video
```

#### Service Communication During Parallel Processing

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Camera Service  │     │   Orchestrator   │     │  Vision Service  │
│    (Port 8005)   │     │   (Port 8002)    │     │   (Port 8003)    │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │ Recording continues... │                        │
         │                        │                        │
         │ Segment 1 uploaded     │                        │
         ├────────────────────────►                        │
         │ POST /media/upload     │                        │
         │                        │                        │
         │ Segment 2 capturing... │ GET /media/{uuid}/    │
         │ (30s duration)         │     faces/enhanced-v2  │
         │                        ├───────────────────────►│
         │                        │                        │
         │                        │                        │ Processing
         │ Segment 2 uploaded     │                        │ Segment 1
         ├────────────────────────►                        │ (frames 0-900)
         │ POST /media/upload     │                        │
         │                        │                        │
         │                        │ GET /media/{uuid}/    │
         │ Segment 3 capturing... │     faces/enhanced-v2  │
         │ (30s duration)         ├───────────────────────►│
         │                        │                        │
         │                        │                        │ Processing
         │                        │                        │ Segment 2
         │                        │                        │ (frames 0-900)
         │                        │                        │
         │ Segment 3 uploaded     │ Segment 1 complete    │
         ├────────────────────────►◄───────────────────────┤
         │ POST /media/upload     │ 23 faces detected     │
         │                        │                        │
         │ User stops recording   │                        │
         │ ✓ Recording complete   │                        │
         │                        │ Segment 2 complete    │
         │                        │◄───────────────────────┤
         │                        │ 19 faces detected     │
         │                        │                        │
         │                        │ Segment 3 complete    │
         │                        │◄───────────────────────┤
         │                        │ 31 faces detected     │
         │                        │                        │
```

#### Why Parallel Processing is Essential

**Performance Benefits:**

1. **No Recording Interruption**: Camera continues capturing frames without delays
2. **User Experience**: Recording feels smooth and responsive
3. **Resource Efficiency**: Utilizes separate CPU/GPU resources for face detection
4. **Scalability**: Can process multiple segments simultaneously
5. **Fault Tolerance**: Face detection failure doesn't affect recording

**Implementation Details:**

```python
# In Camera Service - Non-blocking upload and face detection trigger

async def save_and_process_segment(segment_path: str):
    """Save segment and trigger processing asynchronously."""
    
    # 1. Save file locally (fast, <1 second)
    recording_file = create_recording_file_record(segment_path)
    
    # 2. Start upload in background (non-blocking)
    asyncio.create_task(
        upload_segment_async(recording_file)
    )
    
    # 3. Continue recording immediately
    # (Don't wait for upload or face detection)
    return  # Returns immediately, recording continues


async def upload_segment_async(recording_file: RecordingFile):
    """Upload segment asynchronously - runs in background."""
    
    try:
        # Upload to media service
        media_uuid = await upload_to_media_service(recording_file.file_path)
        
        # Update database
        recording_file.media_uuid = media_uuid
        recording_file.is_uploaded_to_media = True
        
        # Trigger face detection (also non-blocking)
        if face_detection_enabled:
            asyncio.create_task(
                trigger_face_detection(media_uuid)
            )
            
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Recording continues even if upload fails
```

```python
# In Orchestrator Service - Manages face detection queue

class FaceDetectionQueue:
    """Manages concurrent face detection sessions."""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.active_sessions = {}
        self.queue = asyncio.Queue()
    
    async def add_job(self, media_uuid: str):
        """Add face detection job to queue."""
        await self.queue.put(media_uuid)
    
    async def process_jobs(self):
        """Process jobs concurrently up to max_concurrent."""
        while True:
            if len(self.active_sessions) < self.max_concurrent:
                media_uuid = await self.queue.get()
                
                # Start face detection task
                task = asyncio.create_task(
                    self._detect_faces(media_uuid)
                )
                self.active_sessions[media_uuid] = task
    
    async def _detect_faces(self, media_uuid: str):
        """Run face detection for one segment."""
        try:
            # Call Vision Service (may take 30-120 seconds)
            results = await vision_service.detect_faces(media_uuid)
            logger.info(f"Detected {results.total_faces} faces")
        finally:
            del self.active_sessions[media_uuid]
```

#### Resource Management

**Camera Service Resources:**
- CPU: Frame capture and encoding (~20-40%)
- Disk I/O: Writing video segments
- Network: Upload to media service

**Vision Service Resources (Separate):**
- GPU: Face detection neural network inference
- CPU: Video decoding and frame extraction
- Memory: Model weights and frame buffers

**Result**: No resource contention between recording and face detection

#### Typical Timing Example

For a 5-minute recording session:

```
Segment Production:
- 10 segments × 30 seconds = 300 seconds (5 minutes)
- Produced at: t=0:30, 1:00, 1:30, 2:00, 2:30, 3:00, 3:30, 4:00, 4:30, 5:00

Face Detection Processing:
- Segment 1: Started at 0:30, completed at 1:30 (60s processing)
- Segment 2: Started at 1:00, completed at 2:00 (60s processing)
- Segment 3: Started at 1:30, completed at 2:30 (60s processing)
- ...
- Segment 10: Started at 5:00, completed at 6:00 (60s processing)

Total Time:
- Recording Duration: 5 minutes
- Last Face Detection Completes: 6 minutes (1 minute after recording stops)
- User sees progress in real-time as segments complete
```

---

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMERA RECORDING DATA FLOW                     │
└─────────────────────────────────────────────────────────────────┘

1. RECORDING START
   ┌──────────────┐
   │   Camera     │
   │   Service    │
   └──────┬───────┘
          │
          │ Create RecordingSession
          ↓
   ┌──────────────────┐
   │  RecordingSession│
   │  status: active  │
   │  session_uuid    │
   └──────────────────┘

2. VIDEO SEGMENTATION (Every 30 seconds)
   ┌──────────────┐
   │   Camera     │ Capture frames
   │   Capture    │ ────────────┐
   └──────────────┘             │
                                 ↓
                          ┌──────────────┐
                          │ Video Writer │
                          │  segment_N   │
                          └──────┬───────┘
                                 │
                                 │ segment_duration reached
                                 ↓
                          ┌──────────────┐
                          │  Save File   │
                          │segment_N.mp4 │
                          └──────┬───────┘
                                 │
                                 ↓
                          ┌──────────────┐
                          │RecordingFile │
                          │  file_uuid   │
                          │  file_path   │
                          └──────┬───────┘
                                 │
                                 ↓

3. UPLOAD TO MEDIA SERVICE
   ┌─────────────────────┐
   │   HTTP POST         │
   │  /api/v1/media/     │
   │     upload          │
   └──────────┬──────────┘
              │
              │ multipart/form-data
              │ - file (video bytes)
              │ - metadata
              │ - device_name
              ↓
   ┌─────────────────────┐
   │  Media Service      │
   │  Port 8000          │
   └──────────┬──────────┘
              │
              │ Returns media_uuid
              ↓
   ┌─────────────────────┐
   │ RecordingFile       │
   │ media_uuid = uuid   │
   │ is_uploaded = true  │
   └──────────┬──────────┘
              │
              ↓

4. FACE DETECTION TRIGGER (if enabled)
   ┌─────────────────────┐
   │ Check Setting       │
   │ face_detection_     │
   │   on_save           │
   └──────────┬──────────┘
              │
              │ if true
              ↓
   ┌─────────────────────┐
   │  HTTP GET           │
   │  /api/v1/media/     │
   │  {uuid}/faces/      │
   │  enhanced-v2        │
   └──────────┬──────────┘
              │
              ↓
   ┌─────────────────────┐
   │ Orchestrator        │
   │ Service             │
   │ Port 8002           │
   └──────────┬──────────┘
              │
              │ Coordinates detection
              ↓
   ┌─────────────────────┐
   │  Vision Service     │
   │  Port 8003          │
   │  Enhanced Logic V2  │
   └──────────┬──────────┘
              │
              │ Process video
              │ Detect faces
              ↓
   ┌─────────────────────┐
   │ Face Detection      │
   │    Results          │
   │ - bounding boxes    │
   │ - confidence scores │
   │ - frame timestamps  │
   └──────────┬──────────┘
              │
              ↓

5. COLLECTION ASSIGNMENT
   ┌─────────────────────┐
   │ Find/Create         │
   │  Camera Collection  │
   │ "Camera: {name}"    │
   └──────────┬──────────┘
              │
              ↓
   ┌─────────────────────┐
   │  Assign Media       │
   │  to Collection      │
   └──────────┬──────────┘
              │
              ↓
   ┌─────────────────────┐
   │   Collection        │
   │ - All segments      │
   │ - Organized by cam  │
   └─────────────────────┘

6. REPEAT STEPS 2-5 FOR EACH SEGMENT

7. RECORDING STOP
   ┌──────────────┐
   │   Camera     │
   │   Service    │
   └──────┬───────┘
          │
          │ Stop recording
          ↓
   ┌──────────────────┐
   │  RecordingSession│
   │ status: completed│
   │ stopped_at: time │
   └──────┬───────────┘
          │
          │ Final statistics
          ↓
   ┌─────────────────────────────┐
   │ Session Summary             │
   │ - Total segments: N         │
   │ - Total duration: X seconds │
   │ - Total size: Y bytes       │
   │ - Total faces: Z            │
   └─────────────────────────────┘
```

---

### Database Schema

#### RecordingSession Table

Primary table for tracking recording sessions:

```sql
CREATE TABLE recording_sessions (
    -- Primary key
    id                          INTEGER PRIMARY KEY,
    session_uuid                VARCHAR(36) UNIQUE NOT NULL,
    
    -- References
    camera_id                   INTEGER NOT NULL REFERENCES cameras(id),
    user_id                     VARCHAR(100) NOT NULL,
    
    -- Status tracking
    status                      VARCHAR(20) NOT NULL DEFAULT 'active',
                                -- 'active', 'completed', 'failed', 'stopped'
    started_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at                  TIMESTAMP NULL,
    
    -- Configuration
    recording_quality           VARCHAR(20) DEFAULT 'high',
                                -- 'low', 'medium', 'high'
    
    -- Real-time metrics
    current_duration_seconds    FLOAT DEFAULT 0.0,
    estimated_file_size_bytes   BIGINT DEFAULT 0,
    frames_recorded             INTEGER DEFAULT 0,
    average_fps                 FLOAT NULL,
    last_heartbeat              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message               TEXT NULL,
    
    -- Timestamps
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_recording_sessions_camera_id ON recording_sessions(camera_id);
CREATE INDEX idx_recording_sessions_user_id ON recording_sessions(user_id);
CREATE INDEX idx_recording_sessions_status ON recording_sessions(status);
CREATE INDEX idx_recording_sessions_session_uuid ON recording_sessions(session_uuid);
```

#### RecordingMetadata Table

Configuration and technical metadata (one-to-one with RecordingSession):

```sql
CREATE TABLE recording_metadata (
    -- Primary key
    id                              INTEGER PRIMARY KEY,
    
    -- References
    session_uuid                    VARCHAR(36) UNIQUE NOT NULL 
                                    REFERENCES recording_sessions(session_uuid) 
                                    ON DELETE CASCADE,
    recording_profile_id            INTEGER NULL,
    
    -- Segmentation configuration
    segment_interval_seconds        INTEGER NULL,
                                    -- null = manual only, otherwise auto-segment interval
    segment_duration_seconds        INTEGER DEFAULT 30 NOT NULL,
                                    -- Duration of each video segment
    
    -- Processing configuration
    auto_face_detection_enabled     BOOLEAN DEFAULT TRUE,
    video_codec                     VARCHAR(20) DEFAULT 'h264',
    audio_enabled                   BOOLEAN DEFAULT FALSE,
    
    -- Technical specifications
    resolution_width                INTEGER NULL,
    resolution_height               INTEGER NULL,
    fps                             INTEGER NULL,
    bitrate                         INTEGER NULL,
    
    -- Face detection settings
    face_detection_method           VARCHAR(20) DEFAULT 'two_stage',
                                    -- 'two_stage' or 'enhanced-v2'
    quality_preset                  VARCHAR(20) DEFAULT 'balanced',
                                    -- 'low', 'balanced', 'high'
    
    -- Timestamps
    created_at                      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_recording_metadata_session_uuid 
    ON recording_metadata(session_uuid);
```

#### RecordingFile Table

Tracks individual video segment files:

```sql
CREATE TABLE recording_files (
    -- Primary key
    id                          INTEGER PRIMARY KEY,
    
    -- References
    session_uuid                VARCHAR(36) NOT NULL 
                                REFERENCES recording_sessions(session_uuid) 
                                ON DELETE CASCADE,
    file_uuid                   VARCHAR(36) UNIQUE NOT NULL,
    
    -- File information
    file_path                   VARCHAR(500) NOT NULL,
    relative_path               VARCHAR(500) NOT NULL,
    file_name                   VARCHAR(255) NOT NULL,
    file_size_bytes             BIGINT DEFAULT 0,
    
    -- Media properties
    mime_type                   VARCHAR(100) DEFAULT 'video/mp4',
    video_codec                 VARCHAR(20) NULL,
    audio_codec                 VARCHAR(20) NULL,
    duration_seconds            FLOAT DEFAULT 0.0,
    
    -- Storage information
    storage_type                VARCHAR(20) DEFAULT 'local',
                                -- 'local', 's3', 'gcs', 'azure'
    storage_bucket              VARCHAR(100) NULL,
    storage_region              VARCHAR(50) NULL,
    
    -- File integrity
    checksum_md5                VARCHAR(32) NULL,
    checksum_sha256             VARCHAR(64) NULL,
    file_verified_at            TIMESTAMP NULL,
    
    -- Media service integration
    is_uploaded_to_media        BOOLEAN DEFAULT FALSE,
    media_collection_id         VARCHAR(36) NULL,
    media_uuid                  VARCHAR(36) NULL,
                                -- UUID from media service
    media_upload_attempted_at   TIMESTAMP NULL,
    media_upload_completed_at   TIMESTAMP NULL,
    
    -- Lifecycle management
    is_archived                 BOOLEAN DEFAULT FALSE,
    archived_at                 TIMESTAMP NULL,
    is_deleted                  BOOLEAN DEFAULT FALSE,
    deleted_at                  TIMESTAMP NULL,
    retention_until             TIMESTAMP NULL,
    
    -- Timestamps
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_recording_files_session_uuid ON recording_files(session_uuid);
CREATE INDEX idx_recording_files_file_uuid ON recording_files(file_uuid);
CREATE INDEX idx_recording_files_media_uuid ON recording_files(media_uuid);
CREATE INDEX idx_recording_files_is_uploaded ON recording_files(is_uploaded_to_media);
```

#### RecordingStatus Table

Real-time recording status and performance metrics:

```sql
CREATE TABLE recording_status (
    -- Primary key
    id                          INTEGER PRIMARY KEY,
    
    -- References
    session_uuid                VARCHAR(36) NOT NULL 
                                REFERENCES recording_sessions(session_uuid) 
                                ON DELETE CASCADE,
    
    -- Real-time metrics
    current_duration_seconds    FLOAT DEFAULT 0.0,
    current_file_size_bytes     BIGINT DEFAULT 0,
    frames_recorded             INTEGER DEFAULT 0,
    frames_dropped              INTEGER DEFAULT 0,
    average_fps                 FLOAT NULL,
    
    -- Performance metrics
    cpu_usage_percent           FLOAT NULL,
    memory_usage_mb             FLOAT NULL,
    disk_write_speed_mbps       FLOAT NULL,
    
    -- Network metrics (if applicable)
    network_bandwidth_mbps      FLOAT NULL,
    network_latency_ms          FLOAT NULL,
    packet_loss_percent         FLOAT NULL,
    
    -- Timestamps
    recorded_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_recording_status_session_uuid ON recording_status(session_uuid);
CREATE INDEX idx_recording_status_recorded_at ON recording_status(recorded_at);
```

#### Relationships

```
Camera
  └── RecordingSession (1:many)
        ├── RecordingMetadata (1:1)
        ├── RecordingFile (1:many) ────┐
        └── RecordingStatus (1:many)   │
                                       │
                                       └─→ media_uuid
                                             │
                                             ↓
                                       Media Service
                                             │
                                             ├── Media Record
                                             └── Collection
                                                   │
                                                   ↓
                                             Vision Service
                                                   │
                                                   └── Face Detection Results
```

---

### Recording Profiles

Recording profiles provide reusable configuration templates:

```python
class RecordingProfile:
    """Predefined recording configuration template."""
    
    profile_name: str               # e.g., "High Quality 1080p"
    description: str
    
    # Segmentation
    segment_interval_seconds: int   # Auto-segment interval
    segment_duration_seconds: int   # Segment duration (default: 30)
    auto_segment_recording: bool    # Enable auto-segmentation
    
    # Video settings
    video_codec: str                # h264, h265, vp9
    resolution_width: int           # 1920, 1280, 640
    resolution_height: int          # 1080, 720, 480
    fps: int                        # 15, 24, 30, 60
    bitrate: int                    # Video bitrate in kbps
    
    # Audio settings
    audio_enabled: bool
    audio_codec: str                # aac, opus
    audio_bitrate: int
    
    # Face detection
    face_detection_on_save: bool    # Auto-detect faces
    face_detection_method: str      # two_stage, enhanced-v2
```

**Common Profiles:**

1. **High Quality 1080p**
   - Resolution: 1920x1080
   - FPS: 30
   - Bitrate: 5000 kbps
   - Segment: 30 seconds

2. **Balanced 720p**
   - Resolution: 1280x720
   - FPS: 24
   - Bitrate: 2500 kbps
   - Segment: 30 seconds

3. **Low Bandwidth 480p**
   - Resolution: 640x480
   - FPS: 15
   - Bitrate: 1000 kbps
   - Segment: 60 seconds

---

### Storage and Media Service Integration

#### Local Storage

Video segments are initially stored locally:

```
/recordings/
  ├── camera_{device_id}/
  │     ├── session_{uuid}/
  │     │     ├── segment_001.mp4
  │     │     ├── segment_002.mp4
  │     │     └── segment_003.mp4
  │     └── session_{uuid2}/
  │           └── segment_001.mp4
  └── camera_{device_id2}/
        └── ...
```

**Local Storage Benefits:**
- **Immediate Access**: No network latency
- **Reliability**: Recording continues during network issues
- **Processing**: Local processing before upload
- **Backup**: Local copy retained as backup

#### Media Service Upload

Each segment is uploaded asynchronously:

```python
# Upload process per segment
1. Segment completes (duration reached)
2. File saved to local storage
3. RecordingFile record created in database
4. Upload initiated to media service
5. media_uuid received and stored
6. Local file marked as uploaded
7. Face detection triggered (if enabled)
8. Collection assignment completed
```

**Upload Retry Logic:**

```python
async def upload_with_retry(file_path: str, max_retries: int = 3):
    """Upload with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            media_uuid = await upload_segment(file_path)
            return media_uuid
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f'Upload failed, retrying in {wait_time}s...')
                await asyncio.sleep(wait_time)
            else:
                logger.error(f'Upload failed after {max_retries} attempts')
                raise
```

#### File Lifecycle Management

```
1. RECORDING → Local file created
              ↓
2. UPLOAD    → Copied to media service
              ↓
3. VERIFIED  → Upload confirmed, checksum validated
              ↓
4. ARCHIVED  → Local file moved to archive (optional)
              ↓
5. DELETED   → Local file removed (after retention period)
```

**Retention Policy:**
- Uploaded segments: Retained locally for 7 days (default)
- Failed uploads: Retained indefinitely until successful
- Archived segments: Moved to cold storage
- Deleted segments: Permanently removed after retention expires

---

## Summary

The PPL Meta camera recording system provides:

✅ **Continuous Recording** with automatic video segmentation  
✅ **Configurable Segments** (default 30 seconds per segment)  
✅ **Automatic Upload** to media service for each segment  
✅ **Real-time Face Detection** using Enhanced Logic V2  
✅ **Collection Organization** per camera device  
✅ **Database Persistence** with comprehensive session tracking  
✅ **Retry Logic** for reliable uploads  
✅ **Performance Monitoring** with real-time metrics  
✅ **Flexible Configuration** via recording profiles  
✅ **Lifecycle Management** for storage optimization  

This architecture enables scalable, reliable camera recording with integrated face detection and organized media storage.

---

**Next Sections (To Be Documented):**

2. Data Object Management
3. Media Service Integration Details
4. Face Detection Result Processing
5. Collection and Tagging System
6. Storage Backend Configuration
7. Performance Optimization
8. Troubleshooting Guide

---

**Document Version:** 1.0  
**Last Updated:** November 12, 2025  
**Author:** PPL Meta Development Team
