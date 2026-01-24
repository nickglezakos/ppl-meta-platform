# Instant Detection and Recording Pipeline Decoupling - Proposal

**Date**: January 23, 2026  
**Status**: Draft Proposal  
**Author**: System Architecture Team

---

## Executive Summary

This document proposes the architectural changes needed to decouple two currently intertwined functionalities that occur during camera recording:

1. **Instant Detection Pipeline** - Real-time demographic analysis with Redis pub/sub and trigger evaluation
2. **Recording & Continuous Detection Pipeline** - Segment-based recording with continuous face detection, recognition, and batch processing

The goal is to provide **per-camera granular control** through the cameras management UI (`http://localhost:3000/#/cameras`), allowing users to configure each camera independently to enable/disable each pipeline while maintaining backward compatibility (both enabled by default).

---

## Current Architecture

### Recording Start Flow

When a camera starts recording (`POST /api/v1/cameras/{device_id}/record/start`), **both pipelines activate automatically**:

#### 1. Instant Detection Pipeline
```
Camera Recording
    ↓ (Every 5s)
Instant Detection Sampler
    ↓ (Celery Task)
Vision Service Analysis
    ↓ (Redis Pub/Sub)
Media Service Subscriber
    ↓ (Trigger Evaluation)
Actions (Signage, Alerts, Logs)
```

**Key Components:**
- [InstantDetectionSampler](ppl-meta-cameras/src/services/instant_detection.py) - Samples frames every N seconds
- [Celery Task](ppl-meta-cameras/src/tasks/instant_detection_tasks.py) - `process_instant_detection` queue
- Redis Pub/Sub - Channel: `instant-detection`
- [InstantDetectionSubscriber](ppl-meta-media/src/services/redis_subscriber.py) - Evaluates triggers
- Trigger Actions - Signage control, communications alerts, audit logs

**Current Behavior:**
- Always starts when recording starts (hardcoded)
- Runs in parallel with recording
- Updates Redis cache (`instant_detection:{camera_id}`)
- Non-blocking to recording pipeline

#### 2. Recording & Continuous Pipeline
```
Camera Recording (30s segments)
    ↓ (Per Segment)
Upload to Media Service
    ↓ (Auto-trigger)
Face Detection V2 Workflow
    ↓ (Vision Service)
Person Object Creation
    ↓ (VMeta Service)
Face Recognition & Demographics
    ↓ (Batch Processing)
Cross-Video Tracking & Analytics
```

**Key Components:**
- [RecordingSessionService](ppl-meta-cameras/src/services/recording_session_service.py) - Manages segment creation
- [Camera Detection Service](ppl-meta-cameras/src/services/camera_detection.py) - `_rotate_to_next_segment()`
- Media Service Upload - `_upload_segment_background()`
- Face Detection V2 - Vision service workflow trigger
- VMeta Processing - Face recognition and demographic enrichment
- Batch Processing - Cross-video tracking and matching

**Current Behavior:**
- Always enabled when recording with sessions
- Uploads each segment immediately after completion
- Auto-triggers face detection per segment
- Updates VMeta service (`/api/v1/recording/started`)

---

## Problem Statement

### Issues with Current Architecture

1. **Tight Coupling** - No way to disable instant detection without stopping recording
2. **Resource Usage** - Both pipelines run simultaneously, consuming compute resources even when only one is needed
3. **Use Case Limitations**:
   - **Scenario A**: User wants continuous recording for later analysis but doesn't need real-time triggers → Wastes resources on instant detection
   - **Scenario B**: User wants instant demographic triggers but doesn't need archived recordings → Wastes storage on segments
   - **Scenario C**: User wants instant detection only (no storage) → Currently impossible
   - **Scenario D**: User wants recording only (no real-time analysis) → Currently impossible

4. **Configuration Rigidity** - No frontend control over pipeline behavior

---

## Proposed Solution

### High-Level Architecture

Introduce **Per-Camera Recording Pipeline Configuration** settings accessible from the cameras screen (`http://localhost:3000/#/cameras`) that allow independent control of:

1. **Instant Detection** (Enable/Disable per camera)
2. **Recording with Continuous Pipeline** (Enable/Disable per camera)

**Key Design Principle**: Each camera has its own independent pipeline configuration stored in the database, allowing different cameras to operate in different modes simultaneously.

### Configuration Matrix (Per Camera)

Each camera can be configured independently:

| Instant Detection | Recording Pipeline | Behavior | Use Case |
|---|---|---|---|
| ✅ Enabled | ✅ Enabled | **Current behavior** - Both pipelines active (default) | Full monitoring |
| ✅ Enabled | ❌ Disabled | Real-time detection only, no recording/storage | Live triggers only |
| ❌ Disabled | ✅ Enabled | Recording with face detection, no instant triggers | Forensic/archive |
| ❌ Disabled | ❌ Disabled | Invalid configuration - must enable at least one | N/A |

**Example**: Camera A can run instant-detection-only while Camera B records with full pipeline.

---

## Technical Implementation

### 1. Database Schema Changes

#### New Table: `camera_pipeline_settings`

```sql
CREATE TABLE camera_pipeline_settings (
    id SERIAL PRIMARY KEY,
    camera_device_id VARCHAR(255) UNIQUE NOT NULL,
    instant_detection_enabled BOOLEAN DEFAULT TRUE,
    recording_pipeline_enabled BOOLEAN DEFAULT TRUE,
    instant_detection_interval_seconds INTEGER DEFAULT 5,
    segment_duration_seconds INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure at least one pipeline is enabled
    CONSTRAINT at_least_one_pipeline_enabled 
        CHECK (instant_detection_enabled OR recording_pipeline_enabled)
);

CREATE INDEX idx_camera_pipeline_settings_device 
    ON camera_pipeline_settings(camera_device_id);
```

**Alternative Approach**: Add columns to existing `cameras` table instead of new table.

---

### 2. Backend Service Changes

#### A. Cameras Service (`ppl-meta-cameras`)

##### File: `src/models/camera.py`

Add new fields to Camera model:

```python
class Camera(Base):
    __tablename__ = "cameras"
    
    # Existing fields...
    
    # New pipeline configuration fields
    instant_detection_enabled = Column(Boolean, default=True)
    recording_pipeline_enabled = Column(Boolean, default=True)
    instant_detection_interval_seconds = Column(Integer, default=5)
    segment_duration_seconds = Column(Integer, default=30)
```

##### File: `src/api/v1/endpoints/cameras.py`

Add new endpoints for pipeline settings:

```python
@router.get("/{device_id}/pipeline-settings")
async def get_pipeline_settings(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get current pipeline settings for a specific camera.
    
    Args:
        device_id: Camera device ID
        
    Returns:
        Current camera pipeline settings
    """
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {
        "device_id": camera.device_id,
        "camera_name": camera.name,
        "instant_detection_enabled": camera.instant_detection_enabled,
        "recording_pipeline_enabled": camera.recording_pipeline_enabled,
        "instant_detection_interval_seconds": camera.instant_detection_interval_seconds,
        "segment_duration_seconds": camera.segment_duration_seconds,
        "created_at": camera.created_at.isoformat(),
        "updated_at": camera.updated_at.isoformat() if camera.updated_at else None
    }

@router.patch("/{device_id}/pipeline-settings")
async def update_pipeline_settings(
    device_id: str,
    settings: PipelineSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Update pipeline settings for a camera.
    
    Args:
        device_id: Camera device ID
        settings: Pipeline configuration update
        
    Returns:
        Updated camera settings
    """
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Validate: At least one pipeline must be enabled
    if not settings.instant_detection_enabled and not settings.recording_pipeline_enabled:
        raise HTTPException(
            status_code=400,
            detail="At least one pipeline must be enabled"
        )
    
    # Update settings
    camera.instant_detection_enabled = settings.instant_detection_enabled
    camera.recording_pipeline_enabled = settings.recording_pipeline_enabled
    camera.instant_detection_interval_seconds = settings.instant_detection_interval_seconds
    camera.segment_duration_seconds = settings.segment_duration_seconds
    
    db.commit()
    db.refresh(camera)
    
    return {
        "device_id": device_id,
        "instant_detection_enabled": camera.instant_detection_enabled,
        "recording_pipeline_enabled": camera.recording_pipeline_enabled,
        "instant_detection_interval_seconds": camera.instant_detection_interval_seconds,
        "segment_duration_seconds": camera.segment_duration_seconds
    }
```

##### File: `src/services/camera_detection.py`

Modify `start_recording_with_session()`:

```python
async def start_recording_with_session(
    self,
    device_id: str,
    user_id: str,
    quality: str = "high",
    auth_token: Optional[str] = None,
    session_uuid: str = "",
    segment_duration: int = 30,
    enable_instant_detection: bool = None,  # None = use camera settings
) -> Optional[Dict]:
    """
    Start recording with optional instant detection.
    
    If enable_instant_detection is None, uses camera's stored settings.
    """
    
    # Get camera pipeline settings from database
    db_gen = get_db()
    db = next(db_gen)
    try:
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera:
            raise ValueError(f"Camera {device_id} not found")
        
        # Use provided value or fallback to camera settings
        if enable_instant_detection is None:
            enable_instant_detection = camera.instant_detection_enabled
        
        recording_enabled = camera.recording_pipeline_enabled
        
        # Validate: At least one must be enabled
        if not enable_instant_detection and not recording_enabled:
            raise ValueError("At least one pipeline must be enabled")
        
    finally:
        db.close()
    
    # 1. INSTANT DETECTION PIPELINE (Conditional)
    if enable_instant_detection:
        logger.info(f"🔍 Starting instant detection for {device_id}")
        # Existing instant detection startup code...
        from src.api.v1.endpoints.instant_detection import get_instant_detection_manager
        manager = get_instant_detection_manager()
        manager.start_sampling(device_id)
    else:
        logger.info(f"⏭️ Instant detection DISABLED for {device_id}")
    
    # 2. RECORDING PIPELINE (Conditional)
    if recording_enabled:
        logger.info(f"📹 Starting recording pipeline for {device_id}")
        # Existing recording startup code...
        camera_info = self.connected_cameras.get(device_id)
        is_mobile = camera_info.get("source_type") == "mobile"
        
        if is_mobile:
            return await self._start_mobile_recording_with_session(...)
        else:
            return await self._start_regular_recording_with_session(...)
    else:
        logger.info(f"⏭️ Recording pipeline DISABLED for {device_id}")
        
        # Special case: Instant detection only (no recording)
        # Return lightweight session info
        return {
            "recording_id": None,
            "session_uuid": session_uuid,
            "instant_detection_only": True,
            "started_at": datetime.now().isoformat()
        }
```

Modify `stop_recording()`:

```python
async def stop_recording(
    self, 
    device_id: str, 
    user_id: str, 
    auto_stop_instant_detection: bool = True
) -> Optional[Dict]:
    """
    Stop recording and optionally stop instant detection.
    
    If recording pipeline was disabled, only stops instant detection.
    """
    recording_info = self.active_recordings.get(device_id)
    
    # Check if this was instant-detection-only session
    if recording_info and recording_info.get("instant_detection_only"):
        logger.info(f"⏹️ Stopping instant-detection-only session for {device_id}")
        
        # Stop instant detection
        if auto_stop_instant_detection:
            from src.api.v1.endpoints.instant_detection import get_instant_detection_manager
            manager = get_instant_detection_manager()
            manager.stop_sampling(device_id)
        
        # Remove from active recordings
        del self.active_recordings[device_id]
        
        return {
            "message": "Instant detection stopped",
            "instant_detection_only": True
        }
    
    # Normal recording stop flow...
    # (existing code)
```

---

#### B. Frontend Service (`ppl-meta-frontend`)

##### New Widget: Per-Camera Pipeline Settings

**UI Location**: Cameras Screen (`http://localhost:3000/#/cameras`)  
**File Location**: `lib/screens/cameras/camera_pipeline_settings_screen.dart`

**Access Pattern**: 
1. Navigate to Cameras screen (`http://localhost:3000/#/cameras`)
2. Select a camera from the list
3. Click "Pipeline Settings" button/icon
4. Configure pipelines for that specific camera

```dart
class CameraPipelineSettingsScreen extends StatefulWidget {
  final String cameraDeviceId;
  final String cameraName; // Display friendly name
  
  @override
  _CameraPipelineSettingsScreenState createState() => 
      _CameraPipelineSettingsScreenState();
}

class _CameraPipelineSettingsScreenState 
    extends State<CameraPipelineSettingsScreen> {
  
  bool _instantDetectionEnabled = true;
  bool _recordingPipelineEnabled = true;
  int _instantDetectionInterval = 5;
  int _segmentDuration = 30;
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _loadCameraSettings();
  }
  
  Future<void> _loadCameraSettings() async {
    // Load current settings for THIS specific camera
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/cameras/${widget.cameraDeviceId}/pipeline-settings'),
        headers: {'Authorization': 'Bearer $token'},
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _instantDetectionEnabled = data['instant_detection_enabled'];
          _recordingPipelineEnabled = data['recording_pipeline_enabled'];
          _instantDetectionInterval = data['instant_detection_interval_seconds'];
          _segmentDuration = data['segment_duration_seconds'];
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() => _isLoading = false);
      _showError('Failed to load camera settings');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text('Pipeline Settings')),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    
    return Scaffold(
      appBar: AppBar(
        title: Text('Pipeline Settings - ${widget.cameraName}'),
        subtitle: Text(widget.cameraDeviceId),
      ),
      body: ListView(
        padding: EdgeInsets.all(16),
        children: [
          // Camera Info Card
          Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Camera Configuration',
                       style: Theme.of(context).textTheme.headline6),
                  SizedBox(height: 8),
                  Text('Configure recording pipelines for this specific camera.',
                       style: Theme.of(context).textTheme.bodyText2),
                  SizedBox(height: 8),
                  Text('Changes apply only to: ${widget.cameraName}',
                       style: TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ),
          SizedBox(height: 16),
          // Section: Pipeline Control
          Text('Pipeline Control', 
               style: Theme.of(context).textTheme.headline6),
          SizedBox(height: 16),
          
          // Instant Detection Toggle
          SwitchListTile(
            title: Text('Instant Detection'),
            subtitle: Text(
              'Real-time demographic analysis and trigger evaluation'
            ),
            value: _instantDetectionEnabled,
            onChanged: (value) {
              // Validate: At least one must be enabled
              if (!value && !_recordingPipelineEnabled) {
                _showError('At least one pipeline must be enabled');
                return;
              }
              setState(() => _instantDetectionEnabled = value);
            },
          ),
          
          // Recording Pipeline Toggle
          SwitchListTile(
            title: Text('Recording & Continuous Detection'),
            subtitle: Text(
              'Segment recording with face detection and recognition'
            ),
            value: _recordingPipelineEnabled,
            onChanged: (value) {
              // Validate: At least one must be enabled
              if (!value && !_instantDetectionEnabled) {
                _showError('At least one pipeline must be enabled');
                return;
              }
              setState(() => _recordingPipelineEnabled = value);
            },
          ),
          
          Divider(height: 32),
          
          // Section: Advanced Settings
          Text('Advanced Settings', 
               style: Theme.of(context).textTheme.headline6),
          SizedBox(height: 16),
          
          // Instant Detection Interval (only if enabled)
          if (_instantDetectionEnabled) ...[
            ListTile(
              title: Text('Instant Detection Interval'),
              subtitle: Text('$_instantDetectionInterval seconds'),
              trailing: Icon(Icons.chevron_right),
              onTap: () => _showIntervalPicker(),
            ),
          ],
          
          // Segment Duration (only if recording enabled)
          if (_recordingPipelineEnabled) ...[
            ListTile(
              title: Text('Segment Duration'),
              subtitle: Text('$_segmentDuration seconds'),
              trailing: Icon(Icons.chevron_right),
              onTap: () => _showSegmentDurationPicker(),
            ),
          ],
          
          SizedBox(height: 32),
          
          // Save Button
          ElevatedButton(
            onPressed: _saveSettings,
            child: Text('Save Settings'),
          ),
        ],
      ),
    );
  }
  
  Future<void> _saveSettings() async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/api/v1/cameras/${widget.cameraDeviceId}/pipeline-settings'),
        headers: {'Authorization': 'Bearer $token'},
        body: jsonEncode({
          'instant_detection_enabled': _instantDetectionEnabled,
          'recording_pipeline_enabled': _recordingPipelineEnabled,
          'instant_detection_interval_seconds': _instantDetectionInterval,
          'segment_duration_seconds': _segmentDuration,
        }),
      );
      
      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Pipeline settings saved'))
        );
      }
    } catch (e) {
      _showError('Failed to save settings: $e');
    }
  }
}
```

##### Integration into Cameras List Screen

Add pipeline settings access from the cameras list screen (`http://localhost:3000/#/cameras`):

**Option 1: Settings Icon in Camera Card**
```dart
// In cameras_screen.dart - Camera list item
Card(
  child: ListTile(
    title: Text(camera.name),
    subtitle: Text('${camera.status} • ${camera.deviceId}'),
    leading: CircleAvatar(
      child: Icon(camera.isConnected ? Icons.videocam : Icons.videocam_off),
    ),
    trailing: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Pipeline status indicators
        if (camera.instantDetectionEnabled)
          Icon(Icons.flash_on, size: 16, color: Colors.orange),
        if (camera.recordingPipelineEnabled)
          Icon(Icons.fiber_manual_record, size: 16, color: Colors.red),
        SizedBox(width: 8),
        // Settings button
        IconButton(
          icon: Icon(Icons.settings),
          tooltip: 'Pipeline Settings',
          onPressed: () => _openPipelineSettings(camera),
        ),
      ],
    ),
    onTap: () => _openCameraDetails(camera),
  ),
)

void _openPipelineSettings(Camera camera) {
  Navigator.push(
    context,
    MaterialPageRoute(
      builder: (context) => CameraPipelineSettingsScreen(
        cameraDeviceId: camera.deviceId,
        cameraName: camera.name,
      ),
    ),
  );
}
```

**Option 2: Context Menu in Camera Card**
```dart
// In cameras_screen.dart - Add popup menu
trailing: PopupMenuButton<String>(
  onSelected: (value) {
    switch (value) {
      case 'pipeline':
        _openPipelineSettings(camera);
        break;
      case 'details':
        _openCameraDetails(camera);
        break;
    }
  },
  itemBuilder: (context) => [
    PopupMenuItem(
      value: 'pipeline',
      child: ListTile(
        leading: Icon(Icons.tune),
        title: Text('Pipeline Settings'),
      ),
    ),
    PopupMenuItem(
      value: 'details',
      child: ListTile(
        leading: Icon(Icons.info),
        title: Text('Camera Details'),
      ),
    ),
  ],
),
```

---

### 3. API Contract Changes

#### New Endpoint: GET `/api/v1/cameras/{device_id}/pipeline-settings`

**Purpose**: Retrieve current pipeline settings for a specific camera

**Response:**
```json
{
  "device_id": "usb_camera_0",
  "camera_name": "Main Entrance Camera",
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": true,
  "instant_detection_interval_seconds": 5,
  "segment_duration_seconds": 30,
  "created_at": "2026-01-20T08:00:00Z",
  "updated_at": "2026-01-23T10:30:00Z"
}
```

#### New Endpoint: PATCH `/api/v1/cameras/{device_id}/pipeline-settings`

**Purpose**: Update pipeline settings for a specific camera

**Request Body:**
```json
{
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": true,
  "instant_detection_interval_seconds": 5,
  "segment_duration_seconds": 30
}
```

**Response:**
```json
{
  "device_id": "usb_camera_0",
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": true,
  "instant_detection_interval_seconds": 5,
  "segment_duration_seconds": 30,
  "updated_at": "2026-01-23T10:30:00Z"
}
```

**Validation Rules:**
- At least one pipeline must be enabled
- `instant_detection_interval_seconds`: 1-60 seconds
- `segment_duration_seconds`: 5-300 seconds

#### Modified Endpoint: POST `/api/v1/cameras/{device_id}/record/start`

**Request Body (Enhanced):**
```json
{
  "quality": "high",
  "segment_duration_seconds": 30,
  "enable_instant_detection": true,  // Optional: Override camera settings
  "enable_recording_pipeline": true  // Optional: Override camera settings
}
```

If `enable_instant_detection` or `enable_recording_pipeline` are omitted, uses camera's stored settings.

---

## Migration Strategy

### Phase 1: Database Migration (Week 1)

1. **Add columns to cameras table** (or create new table)
2. **Set default values** - All existing cameras get both pipelines enabled
3. **Add validation constraints**
4. **Run migration scripts**

```sql
-- Migration script
ALTER TABLE cameras 
  ADD COLUMN instant_detection_enabled BOOLEAN DEFAULT TRUE,
  ADD COLUMN recording_pipeline_enabled BOOLEAN DEFAULT TRUE,
  ADD COLUMN instant_detection_interval_seconds INTEGER DEFAULT 5,
  ADD COLUMN segment_duration_seconds INTEGER DEFAULT 30;

-- Add constraint
ALTER TABLE cameras
  ADD CONSTRAINT at_least_one_pipeline_enabled
  CHECK (instant_detection_enabled OR recording_pipeline_enabled);
```

### Phase 2: Backend Implementation (Week 2-3)

1. **Update Camera model** in cameras service
2. **Implement pipeline settings endpoint**
3. **Modify recording start logic** to respect settings
4. **Add conditional instant detection startup**
5. **Update logging and telemetry**
6. **Write unit tests**

### Phase 3: Frontend Implementation (Week 3-4)

1. **Create pipeline settings screen**
2. **Add navigation from camera details**
3. **Implement settings persistence**
4. **Add validation and error handling**
5. **Update UI to show active pipelines**

### Phase 4: Testing & Validation (Week 4-5)

1. **Test all configuration combinations**
2. **Verify resource usage improvements**
3. **Validate backward compatibility**
4. **Performance testing under load**
5. **User acceptance testing**

### Phase 5: Documentation & Rollout (Week 5-6)

1. **Update API documentation**
2. **Create user guide**
3. **Add feature flags for gradual rollout**
4. **Monitor metrics post-deployment**

---

## Testing Strategy

### Unit Tests

```python
# test_camera_pipeline_settings.py

def test_both_pipelines_enabled():
    """Test default behavior - both pipelines active"""
    result = start_recording_with_session(
        device_id="test_cam",
        enable_instant_detection=True,
        recording_pipeline_enabled=True
    )
    assert result["instant_detection_active"] == True
    assert result["recording_active"] == True

def test_instant_detection_only():
    """Test instant detection without recording"""
    result = start_recording_with_session(
        device_id="test_cam",
        enable_instant_detection=True,
        recording_pipeline_enabled=False
    )
    assert result["instant_detection_only"] == True
    assert result["recording_id"] is None

def test_recording_only():
    """Test recording without instant detection"""
    result = start_recording_with_session(
        device_id="test_cam",
        enable_instant_detection=False,
        recording_pipeline_enabled=True
    )
    assert result["recording_active"] == True
    assert instant_detection_manager.is_active("test_cam") == False

def test_both_disabled_raises_error():
    """Test validation - at least one must be enabled"""
    with pytest.raises(ValueError):
        start_recording_with_session(
            device_id="test_cam",
            enable_instant_detection=False,
            recording_pipeline_enabled=False
        )
```

### Integration Tests

```bash
# Test instant detection only mode
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instant_detection_enabled": true,
    "recording_pipeline_enabled": false
  }'

curl -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/record/start" \
  -H "Authorization: Bearer $TOKEN"

# Verify: Redis instant-detection events occur
# Verify: No segments uploaded to media service
# Verify: No session records created

# Test recording only mode
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instant_detection_enabled": false,
    "recording_pipeline_enabled": true
  }'

curl -X POST "http://localhost:8005/api/v1/cameras/usb_camera_0/record/start" \
  -H "Authorization: Bearer $TOKEN"

# Verify: Segments uploaded to media service
# Verify: Face detection triggered per segment
# Verify: No Redis instant-detection events
```

---

## Resource Impact Analysis

### Compute Resources

| Configuration | CPU Usage | Memory Usage | Network I/O |
|---|---|---|---|
| Both Enabled (Current) | 100% baseline | 100% baseline | 100% baseline |
| Instant Only | ~40% | ~50% | ~30% |
| Recording Only | ~70% | ~80% | ~90% |
| Impact | **Up to 60% savings** | **Up to 50% savings** | **Up to 70% savings** |

### Storage Resources

| Configuration | Storage Per Hour (720p) |
|---|---|
| Recording Enabled | ~1.5 GB/hour |
| Recording Disabled | ~0 MB/hour (Redis cache only) |
| **Potential Savings** | **100% storage savings when recording disabled** |

### Network Resources

| Configuration | Redis Pub/Sub | HTTP Uploads | Vision API Calls |
|---|---|---|---|
| Both Enabled | High frequency | Segment uploads | Both pipelines |
| Instant Only | High frequency | None | Instant only |
| Recording Only | None | Segment uploads | Continuous only |

---

## Backward Compatibility

### Existing Deployments

All existing cameras will automatically get:
- `instant_detection_enabled = TRUE`
- `recording_pipeline_enabled = TRUE`

This preserves current behavior with **zero breaking changes**.

### API Versioning

The new `enable_instant_detection` and `enable_recording_pipeline` parameters in recording endpoints are **optional**. Existing API clients continue to work without modification.

### Rollback Strategy

Database migration can be rolled back:

```sql
-- Rollback script
ALTER TABLE cameras 
  DROP COLUMN instant_detection_enabled,
  DROP COLUMN recording_pipeline_enabled,
  DROP COLUMN instant_detection_interval_seconds,
  DROP COLUMN segment_duration_seconds;
```

Code changes are feature-flagged and can be disabled via environment variables.

---

## Future Enhancements

### Phase 2 Considerations

1. **Camera Groups** - Apply settings to multiple cameras at once
2. **Default Templates** - Create preset configurations ("Retail", "Security", "Research")
3. **Schedule-Based Pipelines** - Enable/disable pipelines based on time of day
3. **Conditional Logic** - Auto-enable instant detection when triggers are active
4. **Resource-Based Auto-Scaling** - Dynamically disable pipelines under resource pressure
5. **Pipeline Analytics Dashboard** - Visualize resource usage per configuration
6. **Fine-Grained Recording Control** - Toggle face detection separately from recording
7. **Instant Detection Output Options** - Choose between Redis, webhook, or both

---

## Security Considerations

1. **Authorization** - Pipeline settings changes require camera management permissions
2. **Audit Logging** - Log all pipeline configuration changes
3. **Rate Limiting** - Prevent rapid toggling of pipelines
4. **Validation** - Enforce constraints at API and database levels
5. **State Consistency** - Handle edge cases during pipeline transitions

---

## Monitoring & Observability

### New Metrics

```python
# Prometheus metrics
camera_instant_detection_active = Gauge(
    'camera_instant_detection_active',
    'Number of cameras with instant detection enabled'
)

camera_recording_pipeline_active = Gauge(
    'camera_recording_pipeline_active', 
    'Number of cameras with recording pipeline enabled'
)

pipeline_configuration_changes = Counter(
    'pipeline_configuration_changes',
    'Number of pipeline configuration changes',
    ['camera_id', 'pipeline_type']
)
```

### Logging Enhancements

```python
logger.info(
    f"📹 Recording started for {device_id}: "
    f"instant_detection={instant_enabled}, "
    f"recording_pipeline={recording_enabled}"
)

logger.info(
    f"🔍 Pipeline status: {device_id} - "
    f"Instant: {'✅' if instant_enabled else '❌'}, "
    f"Recording: {'✅' if recording_enabled else '❌'}"
)
```

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| Database migration fails | High | Low | Comprehensive testing, rollback scripts |
| Performance regression | Medium | Low | Load testing, gradual rollout |
| User confusion | Medium | Medium | Clear UI, documentation, tooltips |
| State inconsistency | High | Low | Atomic operations, validation constraints |
| Resource leaks | Medium | Low | Proper cleanup in stop_recording() |

---

## Success Criteria

1. ✅ Users can independently toggle instant detection and recording
2. ✅ Default behavior matches current system (both enabled)
3. ✅ Zero downtime during migration
4. ✅ API backward compatible
5. ✅ Resource usage reduced by 40%+ when pipelines disabled
6. ✅ All tests pass with 95%+ coverage
7. ✅ Documentation complete and accessible
8. ✅ User feedback positive (>80% satisfaction)

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|---|---|---|
| Database Migration | 1 week | Schema approval |
| Backend Implementation | 2 weeks | Migration complete |
| Frontend Implementation | 2 weeks | Backend API ready |
| Testing & Validation | 1 week | All implementation complete |
| Documentation & Rollout | 1 week | Testing complete |
| **Total** | **7 weeks** | |

---

## Open Questions

1. **Should we add pipeline settings to camera creation flow?**  
   - Recommendation: Yes, with default values

2. **Should instant detection results be persisted when recording is disabled?**  
   - Recommendation: Optional persistence to separate storage

3. **Should we allow mid-session pipeline toggling?**  
   - Recommendation: Phase 2 enhancement

4. **What happens to active recordings when settings change?**  
   - Recommendation: Settings apply to next recording session only

5. **Should segment duration be configurable per camera or globally?**  
   - Recommendation: Per camera with global defaults

---

## Appendix A: Related Files

### Backend Files to Modify

1. `ppl-meta-cameras/src/models/camera.py` - Add pipeline settings fields
2. `ppl-meta-cameras/src/api/v1/endpoints/cameras.py` - Add settings endpoint
3. `ppl-meta-cameras/src/services/camera_detection.py` - Conditional pipeline startup
4. `ppl-meta-cameras/src/services/instant_detection.py` - Status tracking
5. `ppl-meta-cameras/src/database.py` - Migration scripts

### Frontend Files to Create/Modify

1. `lib/screens/cameras/camera_pipeline_settings_screen.dart` - New per-camera settings screen
2. `lib/screens/cameras/cameras_screen.dart` - Add pipeline settings navigation and status indicators
3. `lib/models/camera_pipeline_settings.dart` - New model for pipeline configuration
4. `lib/models/camera.dart` - Add pipeline settings fields
5. `lib/services/camera_service.dart` - Add settings API calls (GET/PATCH)

### Documentation Files to Update

1. `docs/ALERT_ACTION_INTEGRATION.md` - Update with pipeline settings
2. `docs/camera-instant-detection-to-signage-via-triggers.md` - Add configuration section
3. `docs/guides/developer/instant-detection-implementation.md` - Update integration guide
4. `docs/api/cameras-api.md` - Document new endpoints

---

## Appendix B: UI Mockup - Cameras Screen

### Cameras List View (`http://localhost:3000/#/cameras`)

```
┌─────────────────────────────────────────────────────────────┐
│  Cameras                                     [+ Add Camera]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📹 Main Entrance Camera                      ⚡ 🔴    │   │
│  │    Connected • usb_camera_0                  [⚙️]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📹 Parking Lot Camera                         ⚡       │   │
│  │    Connected • usb_camera_1                  [⚙️]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📹 Back Office Camera                         🔴       │   │
│  │    Connected • usb_camera_2                  [⚙️]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Legend:
⚡ = Instant Detection Enabled
🔴 = Recording Pipeline Enabled
[⚙️] = Pipeline Settings Button
```

### Pipeline Settings Dialog (Per Camera)

```
┌─────────────────────────────────────────────────────────────┐
│  Pipeline Settings - Main Entrance Camera            [✕]    │
│  usb_camera_0                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ℹ️  Camera Configuration                                    │
│  Configure recording pipelines for this specific camera.     │
│  Changes apply only to: Main Entrance Camera                │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  Pipeline Control                                            │
│                                                               │
│  ☑️ Instant Detection                              [Toggle]  │
│     Real-time demographic analysis and trigger evaluation    │
│                                                               │
│  ☑️ Recording & Continuous Detection              [Toggle]  │
│     Segment recording with face detection and recognition    │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│  Advanced Settings                                           │
│                                                               │
│  Instant Detection Interval: 5 seconds            [Change]  │
│  Segment Duration: 30 seconds                     [Change]  │
│                                                               │
│  ─────────────────────────────────────────────────────────  │
│                                                               │
│                          [Cancel]  [Save Settings]           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Appendix C: Configuration Examples

### Example 1: Retail Store (Peak Hours)

**Use Case**: Real-time customer analytics and dynamic signage during business hours

**Configuration**:
- Instant Detection: ✅ Enabled (5s interval)
- Recording Pipeline: ❌ Disabled (save storage costs)

**Benefit**: Real-time triggers without storage overhead

### Example 2: Security Application

**Use Case**: Long-term surveillance and forensic analysis

**Configuration**:
- Instant Detection: ❌ Disabled (not needed)
- Recording Pipeline: ✅ Enabled (30s segments)

**Benefit**: Maximum storage efficiency, post-event analysis

### Example 3: Research & Development

**Use Case**: Comprehensive data collection and analysis

**Configuration**:
- Instant Detection: ✅ Enabled (10s interval)
- Recording Pipeline: ✅ Enabled (60s segments)

**Benefit**: Both real-time and historical data

---

## Conclusion

This proposal provides a comprehensive path to decoupling instant detection from the recording pipeline, offering users granular control while maintaining backward compatibility. The implementation is phased, well-tested, and designed to minimize risk while maximizing value through resource optimization and use case flexibility.

**Recommendation**: Approve for implementation with 7-week timeline.

**Next Steps**:
1. Review and approve proposal
2. Assign development team
3. Begin Phase 1 (Database Migration)
4. Regular progress reviews

---

**Document Status**: Draft for Review  
**Last Updated**: January 23, 2026
