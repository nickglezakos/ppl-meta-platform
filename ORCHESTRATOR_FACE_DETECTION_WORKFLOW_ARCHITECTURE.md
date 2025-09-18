# 🎯 PPL Meta Platform - Orchestrator-Based Face Detection Workflow Architecture with Camera Service Integration & Complete Traceability

## 📋 **Document Overview**

This document outlines the comprehensive architecture for automated face detection workflow management using the PPL Meta Platform's Orchestrator service, integrated with Camera Service for automated recording-triggered processing. The design leverages the existing decoupled service architecture while providing centralized workflow coordination for Camera→Media→Vision face detection pipelines with **comprehensive end-to-end traceability** and **method-specific processing lifecycles**.

**Key Focus**: 
- **Camera Service Integration** - Automated face detection workflows triggered by camera recording events and user-defined time intervals
- **Complete Traceability** - Every camera recording, video source, session lifecycle, processing step, and cross-service operation is fully traceable with audit trails
- **Method-Specific Lifecycles** - Each face detection method/model maintains separate processing lifecycles, allowing multiple detection approaches per video with independent versioning
- **Automated Processing** - User-configurable time intervals for automatic face detection on camera-generated videos

**Created**: September 17, 2025  
**Status**: Architectural Proposal  
**Target Services**: Orchestrator (8002), Camera (8005), Media (8000), Vision (8003)  
**Traceability Scope**: Camera devices, video recordings, session lifecycles, processing workflows, cross-service operations  
**Lifecycle Scope**: Method-specific detection cycles, camera-triggered workflows, automated interval processing

---

## 🏗️ **Architecture Overview with Camera Service Integration**

### **✅ Current Service Responsibilities (Enhanced for Camera Integration)**

#### **1. Camera Service (Port 8005) - Recording & Device Management**

- **Primary Role**: Camera device control and automated video recording
- **Recording Functions**: Start/stop recording via user interaction or scheduled intervals
- **Video Storage**: Automated video storage based on user-defined time intervals
- **Device Management**: Camera discovery, connection, and configuration
- **Traceability Features**:
  - **Camera Device Tracking**: Complete device metadata (ID, model, location, capabilities)
  - **Recording Session Logs**: Full audit trail of start/stop recording events with timestamps
  - **User Interaction Tracking**: Attribution of manual recording triggers to specific users
  - **Automated Interval Logs**: Complete history of scheduled recording events with interval settings
  - **Video File Provenance**: Direct linkage from video files to originating camera device and session
  - **Storage Event Tracking**: Detailed logs of video file creation, storage location, file metadata
- **Integration Points**: Triggers Orchestrator workflows upon video storage completion
- **User Configuration**: Time interval settings for automated recording and face detection triggers

#### **2. Media Service (Port 8000) - Streaming & Session Tracking**

- **Primary Role**: Real-time video streaming with embedded face detection
- **Face Detection**: Embedded service for yellow overlay rectangles during streaming
- **Database Storage**: ❌ **NO** - Does not store faces to database
- **Camera Integration**: Processes videos from Camera Service for streaming
- **Traceability Features**:
  - **Session Lifecycle Tracking**: Complete streaming session records with start/end timestamps
  - **Video Source Provenance**: Full metadata about video origin, camera device, recording session
  - **Camera Source Attribution**: Direct tracking of videos originating from specific camera devices
  - **Real-time Session IDs**: Unique session identifiers for every streaming instance
  - **Client Connection Logs**: Track frontend clients, IP addresses, session duration
  - **Stream Quality Metrics**: Frame rates, bandwidth, connection stability tracking
- **Performance**: Optimized for real-time streaming with 30+ FPS
- **Architecture**: Completely decoupled and independent with full audit trail

#### **3. Vision Service (Port 8003) - Analytics & Persistent Traceability**

- **Primary Role**: Advanced face analytics and database operations
- **Face Detection**: Multiple methods (Haar, Dlib, MTCNN, Two-Stage)
- **Database Storage**: ✅ **YES** - Stores faces with comprehensive metadata
- **Traceability Features**:
  - **Processing Provenance**: Complete audit trail of every face detection operation
  - **Source Video Tracking**: Direct linkage to original media files and sessions
  - **Frame-Level Traceability**: Exact frame timestamps, coordinates, detection method used
  - **Session Correlation**: Links processed faces back to original Media Service sessions
  - **Processing History**: Complete log of detection algorithms, confidence scores, parameters
  - **Cross-Video Face Tracking**: Maintains identity correlations across multiple videos
  - **Bulk Processing Audit**: Detailed logs of batch operations with success/failure tracking
- **Analytics**: Cross-video face tracking, bulk processing, session management
- **Architecture**: Independent database with complete processing lineage

#### **3. Orchestrator Service (Port 8002) - Workflow & Cross-Service Traceability**

- **Current Role**: Basic service coordination and health management
- **Proposed Enhancement**: Centralized workflow management hub with complete traceability
- **Traceability Features**:
  - **End-to-End Workflow Tracking**: Complete audit trail from initiation to completion
  - **Cross-Service Session Correlation**: Links Media sessions to Vision processing jobs
  - **Workflow Provenance**: Full history of workflow decisions, routing, and execution
  - **Service Communication Logs**: All inter-service API calls with timestamps and payloads
  - **User Action Attribution**: Track which user initiated which workflows when
  - **Processing Chain Visibility**: Complete visibility into Media→Vision data flow
  - **Error & Retry Tracking**: Detailed failure analysis with root cause traceability
- **Perfect Fit**: Already designed for cross-service coordination with audit capabilities
- **Architecture**: Ideal for programmatic workflow orchestration with complete observability

---

## � **Method-Specific Processing Lifecycles**

### **🎯 Core Principle: Separate Lifecycles per Detection Method/Model**

The PPL Meta Platform implements **method-specific processing lifecycles** where each face detection method or model maintains completely separate processing histories, metadata, and analytics results for each video. This allows multiple detection approaches to coexist independently while maintaining complete traceability for each method.

### **📋 Lifecycle Separation Rules**

#### **1. Same Method/Model Processing**
```text
When user processes video with SAME method/model:
┌─────────────────────────────────────────────────────────────────┐
│ Video: "sample_video.mp4"                                      │
│ Method: "MTCNN" + Confidence: 0.7                             │
│ ├─ First Processing: 2025-09-17 10:00:00                      │
│ ├─ Second Processing: 2025-09-17 15:30:00                     │
│ └─ Result: UPDATE existing lifecycle, UPDATE last_modified    │
│           NO new detection lifecycle created                   │
└─────────────────────────────────────────────────────────────────┘
```

#### **2. Different Method/Model Processing**
```text
When user processes video with DIFFERENT method/model:
┌─────────────────────────────────────────────────────────────────┐
│ Video: "sample_video.mp4"                                      │
│ ├─ Lifecycle #1: "MTCNN" + Confidence: 0.7                   │
│ │  ├─ Processing: 2025-09-17 10:00:00                        │
│ │  ├─ Results: 15 faces detected                             │
│ │  └─ Status: COMPLETE                                       │
│ │                                                             │
│ ├─ Lifecycle #2: "Two-Stage" + Confidence: 0.5              │
│ │  ├─ Processing: 2025-09-17 15:30:00                        │
│ │  ├─ Results: 18 faces detected                             │
│ │  └─ Status: COMPLETE                                       │
│ │                                                             │
│ └─ Result: SEPARATE lifecycles maintained independently      │
└─────────────────────────────────────────────────────────────────┘
```

### **🔧 Method/Model Identification System**

#### **Detection Method Signature**
```json
{
  "method_signature": {
    "media_service_method": "embedded_detection",
    "vision_service_method": "two_stage",
    "confidence_threshold": 0.5,
    "model_version": "v2.1.0",
    "processing_parameters": {
      "frame_interval": 1,
      "min_face_size": 20,
      "max_face_size": 300
    },
    "algorithm_hash": "sha256:abc123..."
  }
}
```

#### **Lifecycle Key Generation**
```python
def generate_lifecycle_key(media_id: str, method_signature: Dict) -> str:
    """Generate unique lifecycle key for method/model combination"""
    
    # Create deterministic hash from method signature
    signature_string = json.dumps(method_signature, sort_keys=True)
    method_hash = hashlib.sha256(signature_string.encode()).hexdigest()[:16]
    
    # Combine media ID with method hash
    lifecycle_key = f"{media_id}::{method_hash}"
    
    return lifecycle_key

# Examples:
# video_001::mtcnn_v2_conf07 -> MTCNN v2.0 with confidence 0.7
# video_001::twostage_v1_conf05 -> Two-Stage v1.0 with confidence 0.5
# video_001::haar_v3_conf08 -> Haar Cascade v3.0 with confidence 0.8
```

### **📊 Lifecycle Database Schema**

#### **Detection Lifecycles Table**
```sql
CREATE TABLE detection_lifecycles (
    lifecycle_id UUID PRIMARY KEY,
    lifecycle_key VARCHAR(255) UNIQUE NOT NULL, -- media_id::method_hash
    media_id VARCHAR(255) NOT NULL,
    method_signature JSONB NOT NULL,
    
    -- Lifecycle Status
    status VARCHAR(50) NOT NULL, -- pending, processing, completed, failed
    created_at TIMESTAMP NOT NULL,
    last_modified TIMESTAMP NOT NULL,
    processing_count INTEGER DEFAULT 0,
    
    -- Processing Results Summary
    total_faces_detected INTEGER DEFAULT 0,
    total_frames_processed INTEGER DEFAULT 0,
    average_confidence DECIMAL(5,4),
    processing_duration_seconds INTEGER,
    
    -- Traceability
    initiated_by_user_id VARCHAR(255),
    workflow_ids JSONB, -- Array of workflow IDs that used this lifecycle
    session_correlation_ids JSONB, -- Array of session IDs
    
    -- Versioning
    method_version VARCHAR(50),
    platform_version VARCHAR(50),
    
    INDEX idx_media_id (media_id),
    INDEX idx_lifecycle_key (lifecycle_key),
    INDEX idx_method_signature_hash ((method_signature->>'algorithm_hash')),
    INDEX idx_status (status),
    INDEX idx_last_modified (last_modified)
);
```

#### **Face Detections Table (Enhanced)**
```sql
CREATE TABLE face_detections (
    detection_id UUID PRIMARY KEY,
    lifecycle_id UUID NOT NULL REFERENCES detection_lifecycles(lifecycle_id),
    
    -- Face Detection Data
    media_id VARCHAR(255) NOT NULL,
    frame_timestamp DECIMAL(10,6) NOT NULL,
    bbox_x INTEGER NOT NULL,
    bbox_y INTEGER NOT NULL,
    bbox_width INTEGER NOT NULL,
    bbox_height INTEGER NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    
    -- Method-Specific Metadata
    detection_method VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    processing_parameters JSONB,
    
    -- Traceability
    detected_at TIMESTAMP NOT NULL,
    processing_session_id VARCHAR(255),
    workflow_id VARCHAR(255),
    
    -- Face Analytics (when processed by Vision Service)
    face_encoding BYTEA, -- Face embedding for comparison
    landmarks JSONB, -- Facial landmarks
    attributes JSONB, -- Age, gender, emotion, etc.
    
    INDEX idx_lifecycle_id (lifecycle_id),
    INDEX idx_media_frame (media_id, frame_timestamp),
    INDEX idx_method_version (detection_method, model_version),
    INDEX idx_confidence (confidence),
    INDEX idx_detected_at (detected_at)
);
```

---

## �🚀 **Proposed Orchestrator Workflow Architecture**

### **🚀 Workflow Management Hub Design with Complete Traceability**

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR SERVICE (Port 8002)                │
│              Workflow Management Hub with Full Traceability        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  WORKFLOW ORCHESTRATION                      │  │
│  │                                                               │  │
│  │  1. Media→Vision Pipeline Coordination + Session Tracking    │  │
│  │  2. Bulk Face Processing Automation + Provenance Logs        │  │
│  │  3. Workflow Status & Progress Tracking + Audit Trail        │  │
│  │  4. Cross-Service Data Flow Management + Correlation IDs     │  │
│  │  5. Analytics Result Aggregation + Source Attribution        │  │
│  │  6. Programmatic Processing Triggers + User Attribution      │  │
│  │  7. Enterprise-Scale Workflow Scheduling + Complete History  │  │
│  │  8. End-to-End Traceability + Session Lifecycle Management   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │  Media Service  │  │ Vision Service  │  │ Frontend Client │
    │   (Port 8000)   │  │   (Port 8003)   │  │  (Flutter)      │
    │                 │  │                 │  │                 │
    │ • Real-time     │  │ • Database      │  │ • User Controls │
    │   Detection     │  │   Storage       │  │ • Status UI     │
    │ • Streaming     │  │ • Analytics     │  │ • Progress      │
    │ • Session IDs   │  │ • Provenance    │  │ • Traceability  │
    │ • Source Track  │  │ • Frame Links   │  │ • Audit Views   │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### **🔄 Workflow Data Flow with Complete Traceability**

```text
1. FRONTEND REQUEST (User ID + Session ID + Request ID)
   ↓
2. ORCHESTRATOR COORDINATION (Workflow ID + Correlation ID)
   ├─→ Get Media Info + Session History (Media Service)
   ├─→ Trigger Processing + Source Attribution (Vision Service)
   ├─→ Monitor Progress + Audit Logging
   ├─→ Track Cross-Service Communication
   └─→ Aggregate Results + Provenance Chain
   ↓
3. UNIFIED RESPONSE WITH COMPLETE LINEAGE TO FRONTEND
   - Original video source information
   - Complete processing chain history
   - Session correlation across services
   - Audit trail for compliance
```

---

## � **Camera Service Integration & Automated Workflows**

### **🎯 Camera-Triggered Face Detection Workflows**

The PPL Meta Platform's Orchestrator service provides comprehensive integration with the Camera Service (Port 8005) to enable automated face detection workflows triggered by camera recording events and user-defined time intervals. This creates a fully automated pipeline from camera recording to face detection analytics.

### **📋 Camera Integration Components**

#### **1. Camera Recording Events**

```yaml
Camera Recording Lifecycle:
1. User Interaction:
   ├─ Manual Start Recording (via frontend tap)
   ├─ Manual Stop Recording (via frontend tap)
   └─ Automated Interval Recording (user-configured)

2. Camera Service Events:
   ├─ Recording Started Event → Camera Session Created
   ├─ Recording Stopped Event → Video File Stored
   └─ Video Storage Complete → Trigger Orchestrator Workflow

3. Orchestrator Response:
   ├─ Receive Camera Video Storage Event
   ├─ Create Face Detection Workflow
   ├─ Process Video through Media→Vision Pipeline
   └─ Store Results with Camera Device Attribution
```

#### **2. User-Defined Time Intervals**

```yaml
Automated Recording & Processing:
1. User Settings Configuration:
   ├─ Recording Interval: 5min, 10min, 30min, 1hr, 4hr, 24hr
   ├─ Face Detection Enabled: true/false per camera
   ├─ Detection Method: user-selected (MTCNN, Haar, etc.)
   └─ Processing Priority: immediate/scheduled/off-peak

2. Automated Workflow Triggers:
   ├─ Timer Expires → Camera Starts Recording
   ├─ Recording Duration Complete → Camera Stops Recording
   ├─ Video File Saved → Event Sent to Orchestrator
   └─ Face Detection Workflow Initiated Automatically

3. Continuous Operation:
   ├─ Process Video with User's Chosen Method
   ├─ Store Results with Camera/Time Interval Attribution
   ├─ Reset Timer for Next Interval
   └─ Maintain Complete Audit Trail
```

### **🏗️ Enhanced Service Architecture with Camera Integration**

#### **📹 Camera Service (Port 8005) → Orchestrator Integration**

```python
# Camera Service Event Publishing
class CameraRecordingEventPublisher:
    """Publishes camera recording events to Orchestrator"""
    
    async def publish_video_storage_complete(
        self,
        camera_device_id: str,
        video_file_path: str,
        recording_session_id: str,
        recording_trigger: str,  # "manual"|"interval"|"scheduled"
        recording_duration: float,
        user_settings: Dict
    ):
        """Notify Orchestrator when camera video is stored and ready for processing"""
        
        event_payload = {
            "event_type": "camera_video_stored",
            "camera_metadata": {
                "device_id": camera_device_id,
                "device_name": await self.get_camera_name(camera_device_id),
                "device_location": await self.get_camera_location(camera_device_id),
                "device_model": await self.get_camera_model(camera_device_id)
            },
            "recording_metadata": {
                "session_id": recording_session_id,
                "video_file_path": video_file_path,
                "file_size": await self.get_file_size(video_file_path),
                "duration_seconds": recording_duration,
                "trigger_type": recording_trigger,
                "recorded_at": datetime.utcnow().isoformat()
            },
            "user_settings": {
                "face_detection_enabled": user_settings.get("face_detection_enabled", False),
                "detection_method": user_settings.get("detection_method", "two_stage"),
                "confidence_threshold": user_settings.get("confidence_threshold", 0.7),
                "processing_priority": user_settings.get("processing_priority", "normal"),
                "user_id": user_settings.get("user_id")
            },
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid.uuid4())
        }
        
        # Send to Orchestrator's camera event endpoint
        async with aiohttp.ClientSession() as session:
            await session.post(
                "http://localhost:8002/workflows/camera-events/video-stored",
                json=event_payload,
                headers={"X-Event-Type": "camera_video_stored"}
            )
```

#### **🎼 Orchestrator Camera Event Handler**

```python
# ppl-meta-orchestrator/src/workflows/camera_workflows.py

class CameraFaceDetectionWorkflowOrchestrator:
    """Handles camera-triggered face detection workflows with complete traceability"""
    
    def __init__(self):
        self.camera_client = CameraServiceClient()
        self.media_client = MediaServiceClient()
        self.vision_client = VisionServiceClient()
        self.workflow_db = WorkflowDatabase()
        self.audit_logger = AuditLogger()
        self.lifecycle_manager = MethodSpecificLifecycleManager()
        
    async def handle_camera_video_stored_event(
        self,
        camera_event: Dict
    ) -> Dict:
        """Process camera video storage event and trigger face detection workflow"""
        
        correlation_id = camera_event.get("correlation_id")
        camera_metadata = camera_event["camera_metadata"]
        recording_metadata = camera_event["recording_metadata"]
        user_settings = camera_event["user_settings"]
        
        # Step 1: Create camera-attributed workflow
        workflow_id = str(uuid.uuid4())
        
        await self.audit_logger.log_camera_workflow_initiated({
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "camera_device_id": camera_metadata["device_id"],
            "recording_session_id": recording_metadata["session_id"],
            "trigger_type": recording_metadata["trigger_type"],
            "user_id": user_settings["user_id"],
            "initiated_at": datetime.utcnow().isoformat()
        })
        
        # Step 2: Check if face detection is enabled for this camera
        if not user_settings.get("face_detection_enabled", False):
            await self.audit_logger.log_workflow_skipped({
                "workflow_id": workflow_id,
                "reason": "face_detection_disabled_for_camera",
                "camera_device_id": camera_metadata["device_id"]
            })
            return {"status": "skipped", "reason": "face_detection_disabled"}
        
        # Step 3: Register video with Media Service (with camera attribution)
        media_registration = await self.media_client.register_camera_video(
            file_path=recording_metadata["video_file_path"],
            camera_metadata=camera_metadata,
            recording_metadata=recording_metadata,
            correlation_id=correlation_id
        )
        
        media_id = media_registration["media_id"]
        
        # Step 4: Generate method signature for lifecycle tracking
        workflow_config = {
            "method": user_settings["detection_method"],
            "confidence_threshold": user_settings["confidence_threshold"],
            "frame_interval": 1,  # Full frame processing for camera videos
            "store_to_database": True
        }
        
        method_signature = await self.lifecycle_manager.generate_method_signature(
            workflow_config=workflow_config,
            camera_source=True,
            camera_device_id=camera_metadata["device_id"]
        )
        
        # Step 5: Create or update method-specific lifecycle
        lifecycle_result = await self.lifecycle_manager.handle_camera_lifecycle(
            media_id=media_id,
            method_signature=method_signature,
            camera_metadata=camera_metadata,
            recording_metadata=recording_metadata,
            workflow_id=workflow_id,
            correlation_id=correlation_id
        )
        
        # Step 6: Trigger face detection workflow with camera attribution
        workflow_result = await self.coordinate_camera_face_processing(
            media_id=media_id,
            workflow_config=workflow_config,
            lifecycle_id=lifecycle_result["lifecycle_id"],
            camera_metadata=camera_metadata,
            recording_metadata=recording_metadata,
            user_id=user_settings["user_id"],
            workflow_id=workflow_id,
            correlation_id=correlation_id
        )
        
        # Step 7: Update camera statistics and user analytics
        await self.update_camera_processing_stats(
            camera_device_id=camera_metadata["device_id"],
            workflow_result=workflow_result
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "lifecycle_id": lifecycle_result["lifecycle_id"],
            "media_id": media_id,
            "camera_attribution": {
                "device_id": camera_metadata["device_id"],
                "device_name": camera_metadata["device_name"],
                "recording_trigger": recording_metadata["trigger_type"]
            },
            "processing_status": workflow_result["status"],
            "traceability": {
                "camera_source": True,
                "recording_session_id": recording_metadata["session_id"],
                "automated_trigger": recording_metadata["trigger_type"] == "interval"
            }
        }
```

### **⚙️ User Settings Integration**

#### **📱 Frontend Camera Settings Configuration**

```yaml
Camera Settings Panel:
├─ Camera Device List
│  ├─ Device Name & Status
│  ├─ Current Recording State
│  └─ Last Activity Timestamp
│
├─ Recording Configuration
│  ├─ Manual Recording: Enable/Disable
│  ├─ Automated Intervals: 5min/10min/30min/1hr/4hr/24hr
│  ├─ Recording Duration: Fixed/Until-Stopped
│  └─ Storage Location: Local/Cloud
│
├─ Face Detection Settings
│  ├─ Enable Face Detection: true/false
│  ├─ Detection Method: MTCNN/Haar/Dlib/Two-Stage
│  ├─ Confidence Threshold: 0.1-1.0 slider
│  ├─ Processing Priority: Immediate/Scheduled/Off-Peak
│  └─ Notification Settings: Email/Push/None
│
└─ Analytics & History
   ├─ Processing Statistics per Camera
   ├─ Face Detection Results History
   ├─ Storage Usage per Camera
   └─ Performance Metrics Dashboard
```

#### **🗄️ Camera Settings Database Schema**

```sql
-- Camera settings and automation configuration
CREATE TABLE camera_user_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    camera_device_id VARCHAR(255) NOT NULL,
    
    -- Recording settings
    manual_recording_enabled BOOLEAN DEFAULT true,
    automated_recording_enabled BOOLEAN DEFAULT false,
    recording_interval_minutes INTEGER DEFAULT 60, -- 5,10,30,60,240,1440
    recording_duration_seconds INTEGER DEFAULT 300, -- 5 minutes default
    
    -- Face detection settings
    face_detection_enabled BOOLEAN DEFAULT false,
    detection_method VARCHAR(50) DEFAULT 'two_stage',
    confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
    frame_interval INTEGER DEFAULT 1,
    processing_priority VARCHAR(20) DEFAULT 'normal', -- immediate/normal/scheduled
    
    -- Notification settings
    notify_on_completion BOOLEAN DEFAULT false,
    notification_method VARCHAR(20) DEFAULT 'none', -- email/push/none
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    
    UNIQUE(user_id, camera_device_id),
    INDEX idx_camera_user_settings_user_camera (user_id, camera_device_id),
    INDEX idx_camera_user_settings_automated (automated_recording_enabled, recording_interval_minutes)
);

-- Camera processing statistics
CREATE TABLE camera_processing_statistics (
    id SERIAL PRIMARY KEY,
    camera_device_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    
    -- Processing counts
    total_videos_recorded INTEGER DEFAULT 0,
    total_videos_processed INTEGER DEFAULT 0,
    total_faces_detected INTEGER DEFAULT 0,
    
    -- Trigger breakdown
    manual_recordings INTEGER DEFAULT 0,
    automated_recordings INTEGER DEFAULT 0,
    
    -- Performance metrics
    average_processing_time_seconds DECIMAL(10,2),
    last_processing_timestamp TIMESTAMP,
    
    -- Storage metrics
    total_storage_used_bytes BIGINT DEFAULT 0,
    
    -- Metadata
    first_recording_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(camera_device_id, user_id),
    INDEX idx_camera_stats_device (camera_device_id),
    INDEX idx_camera_stats_user (user_id)
);
```

### **🔄 Automated Workflow Triggers**

#### **⏰ Time-Based Recording Automation**

```python
# ppl-meta-orchestrator/src/automation/camera_interval_scheduler.py

class CameraIntervalScheduler:
    """Manages automated camera recording based on user-defined intervals"""
    
    def __init__(self):
        self.camera_client = CameraServiceClient()
        self.settings_db = CameraSettingsDatabase()
        self.scheduler = AsyncIOScheduler()
        
    async def initialize_automated_recording_schedules(self):
        """Set up automated recording schedules for all users and cameras"""
        
        # Get all users with automated recording enabled
        automated_settings = await self.settings_db.get_automated_recording_settings()
        
        for setting in automated_settings:
            await self.schedule_camera_recording(
                user_id=setting["user_id"],
                camera_device_id=setting["camera_device_id"],
                interval_minutes=setting["recording_interval_minutes"],
                duration_seconds=setting["recording_duration_seconds"]
            )
    
    async def schedule_camera_recording(
        self,
        user_id: str,
        camera_device_id: str,
        interval_minutes: int,
        duration_seconds: int
    ):
        """Schedule automated recording for a specific camera"""
        
        job_id = f"camera_recording_{user_id}_{camera_device_id}"
        
        # Schedule recurring job
        self.scheduler.add_job(
            func=self.trigger_automated_recording,
            trigger=IntervalTrigger(minutes=interval_minutes),
            args=[user_id, camera_device_id, duration_seconds],
            id=job_id,
            replace_existing=True,
            max_instances=1
        )
        
        await self.audit_logger.log_schedule_created({
            "job_id": job_id,
            "user_id": user_id,
            "camera_device_id": camera_device_id,
            "interval_minutes": interval_minutes,
            "duration_seconds": duration_seconds,
            "scheduled_at": datetime.utcnow().isoformat()
        })
    
    async def trigger_automated_recording(
        self,
        user_id: str,
        camera_device_id: str,
        duration_seconds: int
    ):
        """Execute automated recording and trigger face detection workflow"""
        
        correlation_id = str(uuid.uuid4())
        
        try:
            # Step 1: Start camera recording
            recording_result = await self.camera_client.start_automated_recording(
                camera_device_id=camera_device_id,
                duration_seconds=duration_seconds,
                trigger_type="interval",
                user_id=user_id,
                correlation_id=correlation_id
            )
            
            # Step 2: Wait for recording completion (handled by Camera Service)
            # Camera Service will automatically send video_stored event to Orchestrator
            # when recording is complete
            
            await self.audit_logger.log_automated_recording_triggered({
                "user_id": user_id,
                "camera_device_id": camera_device_id,
                "recording_session_id": recording_result["session_id"],
                "correlation_id": correlation_id,
                "triggered_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            await self.audit_logger.log_automated_recording_failed({
                "user_id": user_id,
                "camera_device_id": camera_device_id,
                "correlation_id": correlation_id,
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
```

### **📊 Enhanced Traceability with Camera Attribution**

#### **🔍 Camera-Specific Audit Trail**

```python
# Enhanced audit logging for camera-originated workflows
camera_audit_trail = {
    "workflow_id": "uuid",
    "correlation_id": "uuid",
    "traceability_type": "camera_triggered_workflow",
    
    # Camera source attribution
    "camera_source": {
        "device_id": "camera_001",
        "device_name": "Living Room Camera",
        "device_location": "Living Room",
        "device_model": "PPL-CAM-HD-001"
    },
    
    # Recording attribution
    "recording_source": {
        "session_id": "recording_session_uuid",
        "trigger_type": "interval", # manual|interval|scheduled
        "recording_duration": 300, # seconds
        "recorded_at": "2025-09-17T10:00:00Z",
        "file_path": "/storage/camera_001/2025-09-17_10-00-00.mp4",
        "file_size_bytes": 52428800
    },
    
    # User attribution
    "user_attribution": {
        "user_id": "user_123",
        "automation_configured": true,
        "interval_setting": 60, # minutes
        "face_detection_enabled": true,
        "detection_method": "MTCNN",
        "confidence_threshold": 0.8
    },
    
    # Processing workflow
    "processing_workflow": {
        "lifecycle_id": "lifecycle_uuid",
        "method_signature": "sha256_hash",
        "media_registration_timestamp": "2025-09-17T10:05:00Z",
        "vision_processing_start": "2025-09-17T10:05:30Z",
        "vision_processing_complete": "2025-09-17T10:08:45Z",
        "faces_detected": 3,
        "processing_duration_seconds": 195
    },
    
    # Complete audit chain
    "audit_chain": [
        {
            "timestamp": "2025-09-17T10:00:00Z",
            "event": "automated_recording_triggered",
            "service": "orchestrator_scheduler",
            "details": "Timer expired, starting 5min recording"
        },
        {
            "timestamp": "2025-09-17T10:00:01Z",
            "event": "camera_recording_started",
            "service": "camera_service",
            "details": "Recording session initiated"
        },
        {
            "timestamp": "2025-09-17T10:05:00Z",
            "event": "camera_recording_completed",
            "service": "camera_service",
            "details": "Video file saved to storage"
        },
        {
            "timestamp": "2025-09-17T10:05:01Z",
            "event": "video_stored_event_published",
            "service": "camera_service",
            "details": "Event sent to Orchestrator"
        },
        {
            "timestamp": "2025-09-17T10:05:02Z",
            "event": "face_detection_workflow_initiated",
            "service": "orchestrator",
            "details": "Camera workflow handler triggered"
        },
        {
            "timestamp": "2025-09-17T10:05:30Z",
            "event": "media_service_registration",
            "service": "media_service",
            "details": "Video registered with camera attribution"
        },
        {
            "timestamp": "2025-09-17T10:05:31Z",
            "event": "vision_processing_started",
            "service": "vision_service",
            "details": "MTCNN face detection initiated"
        },
        {
            "timestamp": "2025-09-17T10:08:45Z",
            "event": "faces_stored_to_database",
            "service": "vision_service",
            "details": "3 faces detected and stored"
        },
        {
            "timestamp": "2025-09-17T10:08:46Z",
            "event": "workflow_completed",
            "service": "orchestrator",
            "details": "Camera face detection workflow finished"
        }
    ]
}
```

---

## �🛠️ **Implementation Design**

### **📋 Orchestrator Service Extensions**

#### **1. Workflow Management Classes**

```python
# ppl-meta-orchestrator/src/workflows/face_detection_workflows.py

class FaceDetectionWorkflowOrchestrator:
    """Orchestrator for programmatic face detection workflows with complete traceability and method-specific lifecycles"""
    
    def __init__(self):
        self.media_client = MediaServiceClient()
        self.vision_client = VisionServiceClient()
        self.workflow_db = WorkflowDatabase()
        self.audit_logger = AuditLogger()
        self.traceability_manager = TraceabilityManager()
        self.lifecycle_manager = MethodSpecificLifecycleManager()
        
    async def coordinate_bulk_face_processing(
        self, 
        media_id: str, 
        workflow_config: Dict,
        user_id: str = None,
        session_context: Dict = None
    ) -> WorkflowResult:
        """
        Programmatically coordinate Media→Vision bulk processing with method-specific lifecycle management:
        1. Check existing lifecycles for this method/model combination
        2. Create new lifecycle OR update existing based on method signature
        3. Get media metadata from Media Service with source provenance
        4. Create comprehensive workflow tracking with session correlation
        5. Trigger Vision Service bulk processing with lifecycle attribution
        6. Monitor progress with complete lineage tracking
        7. Aggregate results with provenance chain and lifecycle updates
        """
        
        # Generate correlation ID for end-to-end traceability
        correlation_id = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())
        
        # Step 1: Generate method signature and check for existing lifecycle
        method_signature = await self.lifecycle_manager.generate_method_signature(
            workflow_config=workflow_config,
            media_service_method="embedded_detection"  # From Media Service
        )
        
        lifecycle_key = self.lifecycle_manager.generate_lifecycle_key(
            media_id=media_id,
            method_signature=method_signature
        )
        
        # Step 2: Check if lifecycle already exists for this method/model
        existing_lifecycle = await self.lifecycle_manager.get_existing_lifecycle(
            lifecycle_key=lifecycle_key
        )
        
        if existing_lifecycle:
            # Same method/model: Update existing lifecycle metadata
            lifecycle_id = existing_lifecycle['lifecycle_id']
            await self.lifecycle_manager.update_lifecycle_metadata(
                lifecycle_id=lifecycle_id,
                last_modified=datetime.utcnow(),
                processing_count=existing_lifecycle['processing_count'] + 1,
                user_id=user_id,
                workflow_id=workflow_id
            )
            
            # Log lifecycle reuse
            await self.audit_logger.log_lifecycle_reuse({
                "lifecycle_id": lifecycle_id,
                "lifecycle_key": lifecycle_key,
                "media_id": media_id,
                "method_signature": method_signature,
                "previous_processing_count": existing_lifecycle['processing_count'],
                "reused_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "workflow_id": workflow_id,
                "correlation_id": correlation_id
            })
        else:
            # Different method/model: Create new lifecycle
            lifecycle_id = await self.lifecycle_manager.create_new_lifecycle(
                lifecycle_key=lifecycle_key,
                media_id=media_id,
                method_signature=method_signature,
                initiated_by_user_id=user_id,
                workflow_id=workflow_id,
                correlation_id=correlation_id
            )
            
            # Log new lifecycle creation
            await self.audit_logger.log_lifecycle_creation({
                "lifecycle_id": lifecycle_id,
                "lifecycle_key": lifecycle_key,
                "media_id": media_id,
                "method_signature": method_signature,
                "created_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "workflow_id": workflow_id,
                "correlation_id": correlation_id
            })
        
        # Create audit entry for workflow initiation
        await self.audit_logger.log_workflow_start({
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "lifecycle_id": lifecycle_id,
            "lifecycle_key": lifecycle_key,
            "user_id": user_id,
            "media_id": media_id,
            "workflow_type": "bulk_face_processing",
            "method_signature": method_signature,
            "initiated_at": datetime.utcnow().isoformat(),
            "session_context": session_context,
            "config": workflow_config
        })
        
        try:
            # Step 3: Get media info from Media Service with session history
            media_info = await self.media_client.get_media_info_with_sessions(
                media_id, 
                correlation_id=correlation_id
            )
            
            # Log media source information for traceability
            await self.traceability_manager.log_media_source({
                "correlation_id": correlation_id,
                "lifecycle_id": lifecycle_id,
                "media_id": media_id,
                "original_source": media_info.get('source_path'),
                "upload_session_id": media_info.get('upload_session_id'),
                "upload_timestamp": media_info.get('upload_timestamp'),
                "file_metadata": media_info.get('file_metadata'),
                "previous_sessions": media_info.get('streaming_sessions', [])
            })
            
            # Step 4: Create comprehensive workflow tracking entry
            workflow_record = await self._create_workflow_record(
                workflow_id=workflow_id,
                lifecycle_id=lifecycle_id,
                correlation_id=correlation_id,
                media_id=media_id,
                media_source_info=media_info,
                workflow_config=workflow_config,
                method_signature=method_signature,
                user_id=user_id,
                session_context=session_context
            )
            
            # Step 5: Initiate bulk processing in Vision Service with lifecycle tracking
            processing_job = await self.vision_client.start_bulk_processing_with_lifecycle(
                media_id=media_id,
                media_url=media_info['stream_url'],
                config=workflow_config,
                workflow_id=workflow_id,
                lifecycle_id=lifecycle_id,
                correlation_id=correlation_id,
                method_signature=method_signature,
                source_session_ids=media_info.get('streaming_sessions', []),
                original_source_path=media_info.get('source_path')
            )
            
            # Log processing initiation with lifecycle context
            await self.audit_logger.log_processing_start({
                "workflow_id": workflow_id,
                "lifecycle_id": lifecycle_id,
                "correlation_id": correlation_id,
                "vision_job_id": processing_job['job_id'],
                "processing_method": workflow_config.get('method'),
                "confidence_threshold": workflow_config.get('confidence_threshold'),
                "method_signature": method_signature,
                "initiated_at": datetime.utcnow().isoformat()
            })
            
            # Step 6: Track progress and coordinate with audit trail
            await self._monitor_processing_progress_with_lifecycle(
                workflow_id=workflow_id,
                lifecycle_id=lifecycle_id,
                correlation_id=correlation_id,
                processing_job_id=processing_job['job_id']
            )
            
            # Step 7: Aggregate and return results with complete provenance and lifecycle
            results = await self._get_workflow_results_with_lifecycle(
                workflow_id=workflow_id, 
                lifecycle_id=lifecycle_id,
                correlation_id=correlation_id
            )
            
            # Update lifecycle with processing results
            await self.lifecycle_manager.update_lifecycle_results(
                lifecycle_id=lifecycle_id,
                total_faces_detected=results.get('total_faces', 0),
                total_frames_processed=results.get('total_frames', 0),
                average_confidence=results.get('average_confidence', 0.0),
                processing_duration_seconds=results.get('processing_duration', 0)
            )
            
            # Log successful completion
            await self.audit_logger.log_workflow_completion({
                "workflow_id": workflow_id,
                "lifecycle_id": lifecycle_id,
                "correlation_id": correlation_id,
                "completed_at": datetime.utcnow().isoformat(),
                "total_faces_detected": results.get('total_faces', 0),
                "processing_duration": results.get('processing_duration'),
                "method_signature": method_signature,
                "success": True
            })
            
            return results
            
        except Exception as e:
            # Log failure with complete context including lifecycle
            await self.audit_logger.log_workflow_failure({
                "workflow_id": workflow_id,
                "lifecycle_id": lifecycle_id,
                "correlation_id": correlation_id,
                "failed_at": datetime.utcnow().isoformat(),
                "error_message": str(e),
                "error_context": traceback.format_exc(),
                "media_id": media_id,
                "method_signature": method_signature,
                "user_id": user_id
            })
            raise
        
    async def get_media_face_analytics_with_lineage(
        self, 
        media_id: str,
        include_session_history: bool = True
    ) -> AnalyticsResultWithProvenance:
        """Get comprehensive face analytics with complete source lineage"""
        
        correlation_id = str(uuid.uuid4())
        
        # Check processing status with session correlation
        processing_status = await self.vision_client.get_processing_status_with_sessions(
            media_id, 
            correlation_id=correlation_id
        )
        
        if processing_status['face_detection_processed']:
            # Get stored analytics with complete provenance chain
            analytics = await self.vision_client.get_stored_faces_with_lineage(
                media_id, 
                include_source_sessions=include_session_history,
                correlation_id=correlation_id
            )
            
            # Add traceability metadata
            analytics['provenance'] = await self.traceability_manager.get_complete_lineage(
                media_id=media_id,
                include_processing_history=True,
                include_session_correlation=True
            )
            
            return analytics
        else:
            # Trigger processing workflow with traceability
            return await self.coordinate_bulk_face_processing(
                media_id, 
                {"method": "two_stage", "confidence_threshold": 0.5},
                session_context={"triggered_by": "analytics_request", "correlation_id": correlation_id}
            )
        
    async def coordinate_progressive_analysis_with_audit(
        self, 
        media_ids: List[str],
        batch_config: Dict,
        user_id: str = None
    ) -> BatchWorkflowResultWithTraceability:
        """Coordinate bulk analysis across multiple videos with complete audit trail"""
        
        workflow_batch_id = str(uuid.uuid4())
        batch_correlation_id = str(uuid.uuid4())
        results = []
        
        # Log batch initiation
        await self.audit_logger.log_batch_workflow_start({
            "batch_id": workflow_batch_id,
            "batch_correlation_id": batch_correlation_id,
            "user_id": user_id,
            "total_media_count": len(media_ids),
            "media_ids": media_ids,
            "batch_config": batch_config,
            "initiated_at": datetime.utcnow().isoformat()
        })
        
        for i, media_id in enumerate(media_ids):
            try:
                # Create session context for this media
                session_context = {
                    "batch_id": workflow_batch_id,
                    "batch_correlation_id": batch_correlation_id,
                    "batch_position": i + 1,
                    "total_in_batch": len(media_ids)
                }
                
                result = await self.coordinate_bulk_face_processing(
                    media_id=media_id, 
                    workflow_config=batch_config,
                    user_id=user_id,
                    session_context=session_context
                )
                results.append(result)
                
                # Update batch progress with traceability
                await self._update_batch_progress_with_audit(
                    batch_id=workflow_batch_id,
                    batch_correlation_id=batch_correlation_id,
                    completed_count=len(results),
                    total_count=len(media_ids),
                    current_media_id=media_id,
                    processing_result=result
                )
                
            except Exception as e:
                # Log individual processing failure
                await self.audit_logger.log_batch_item_failure({
                    "batch_id": workflow_batch_id,
                    "batch_correlation_id": batch_correlation_id,
                    "media_id": media_id,
                    "failed_at": datetime.utcnow().isoformat(),
                    "error_message": str(e),
                    "batch_position": i + 1
                })
                continue
                
        # Log batch completion
        await self.audit_logger.log_batch_workflow_completion({
            "batch_id": workflow_batch_id,
            "batch_correlation_id": batch_correlation_id,
            "completed_at": datetime.utcnow().isoformat(),
            "total_requested": len(media_ids),
            "successful_processing": len(results),
            "failed_processing": len(media_ids) - len(results)
        })
                
        return BatchWorkflowResultWithTraceability(
            batch_id=workflow_batch_id,
            batch_correlation_id=batch_correlation_id,
            total_media=len(media_ids),
            successful_processing=len(results),
            results=results,
            complete_audit_trail=await self.audit_logger.get_batch_audit_trail(workflow_batch_id)
        )
        
    async def get_workflow_traceability_report(
        self, 
        workflow_id: str = None,
        media_id: str = None,
        user_id: str = None,
        time_range: Dict = None
    ) -> TraceabilityReport:
        """Generate comprehensive traceability report for audit purposes"""
        
        return await self.traceability_manager.generate_comprehensive_report({
            "workflow_id": workflow_id,
            "media_id": media_id,
            "user_id": user_id,
            "time_range": time_range,
            "include_cross_service_calls": True,
            "include_session_correlation": True,
            "include_processing_lineage": True,
            "include_user_attribution": True,
            "include_source_provenance": True
        })
        
    async def schedule_automated_processing(
        self,
        schedule_config: ScheduleConfig
    ) -> ScheduledWorkflow:
        """Schedule automated face detection workflows"""
        
        # Create scheduled workflow
        scheduled_workflow = ScheduledWorkflow(
            schedule_config=schedule_config,
            workflow_type="bulk_face_processing",
            status="scheduled"
        )
        
        # Store in workflow database
        await self.workflow_db.store_scheduled_workflow(scheduled_workflow)
        
        return scheduled_workflow


class MethodSpecificLifecycleManager:
    """Manager for method-specific face detection lifecycles"""
    
    def __init__(self):
        self.db = LifecycleDatabase()
        
    async def generate_method_signature(
        self, 
        workflow_config: Dict,
        media_service_method: str = "embedded_detection"
    ) -> Dict:
        """Generate deterministic method signature for lifecycle identification"""
        
        # Extract core method parameters
        method_signature = {
            "media_service_method": media_service_method,
            "vision_service_method": workflow_config.get("method", "two_stage"),
            "confidence_threshold": workflow_config.get("confidence_threshold", 0.5),
            "model_version": workflow_config.get("model_version", "v2.1.0"),
            "processing_parameters": {
                "frame_interval": workflow_config.get("frame_interval", 1),
                "min_face_size": workflow_config.get("min_face_size", 20),
                "max_face_size": workflow_config.get("max_face_size", 300),
                "detection_threshold": workflow_config.get("detection_threshold", 0.5)
            }
        }
        
        # Generate deterministic hash for method signature
        signature_string = json.dumps(method_signature, sort_keys=True)
        algorithm_hash = hashlib.sha256(signature_string.encode()).hexdigest()
        method_signature["algorithm_hash"] = algorithm_hash
        
        return method_signature
        
    def generate_lifecycle_key(self, media_id: str, method_signature: Dict) -> str:
        """Generate unique lifecycle key for method/model combination"""
        
        # Create short hash from algorithm hash
        method_hash = method_signature["algorithm_hash"][:16]
        
        # Combine media ID with method hash
        lifecycle_key = f"{media_id}::{method_hash}"
        
        return lifecycle_key
        
    async def get_existing_lifecycle(self, lifecycle_key: str) -> Dict:
        """Check if lifecycle already exists for this method/model combination"""
        
        query = """
        SELECT lifecycle_id, media_id, method_signature, status, created_at,
               last_modified, processing_count, total_faces_detected,
               total_frames_processed, average_confidence, processing_duration_seconds
        FROM detection_lifecycles 
        WHERE lifecycle_key = %s
        """
        
        result = await self.db.fetch_one(query, (lifecycle_key,))
        return result
        
    async def create_new_lifecycle(
        self,
        lifecycle_key: str,
        media_id: str,
        method_signature: Dict,
        initiated_by_user_id: str,
        workflow_id: str,
        correlation_id: str
    ) -> str:
        """Create new lifecycle for different method/model combination"""
        
        lifecycle_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO detection_lifecycles (
            lifecycle_id, lifecycle_key, media_id, method_signature,
            status, created_at, last_modified, processing_count,
            initiated_by_user_id, workflow_ids, session_correlation_ids,
            method_version, platform_version
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        await self.db.execute(query, (
            lifecycle_id,
            lifecycle_key,
            media_id,
            json.dumps(method_signature),
            "pending",
            datetime.utcnow(),
            datetime.utcnow(),
            0,
            initiated_by_user_id,
            json.dumps([workflow_id]),
            json.dumps([correlation_id]),
            method_signature.get("model_version", "v2.1.0"),
            "v1.0.0"  # Platform version
        ))
        
        return lifecycle_id
        
    async def update_lifecycle_metadata(
        self,
        lifecycle_id: str,
        last_modified: datetime,
        processing_count: int,
        user_id: str,
        workflow_id: str
    ) -> None:
        """Update existing lifecycle metadata for same method/model processing"""
        
        # Get current workflow IDs
        current_workflows = await self.db.fetch_one(
            "SELECT workflow_ids FROM detection_lifecycles WHERE lifecycle_id = %s",
            (lifecycle_id,)
        )
        
        workflow_ids = json.loads(current_workflows['workflow_ids']) if current_workflows else []
        workflow_ids.append(workflow_id)
        
        query = """
        UPDATE detection_lifecycles 
        SET last_modified = %s, 
            processing_count = %s,
            workflow_ids = %s,
            status = 'processing'
        WHERE lifecycle_id = %s
        """
        
        await self.db.execute(query, (
            last_modified,
            processing_count,
            json.dumps(workflow_ids),
            lifecycle_id
        ))
        
    async def update_lifecycle_results(
        self,
        lifecycle_id: str,
        total_faces_detected: int,
        total_frames_processed: int,
        average_confidence: float,
        processing_duration_seconds: int
    ) -> None:
        """Update lifecycle with processing results"""
        
        query = """
        UPDATE detection_lifecycles 
        SET total_faces_detected = %s,
            total_frames_processed = %s,
            average_confidence = %s,
            processing_duration_seconds = %s,
            status = 'completed',
            last_modified = %s
        WHERE lifecycle_id = %s
        """
        
        await self.db.execute(query, (
            total_faces_detected,
            total_frames_processed,
            average_confidence,
            processing_duration_seconds,
            datetime.utcnow(),
            lifecycle_id
        ))
        
    async def get_all_lifecycles_for_media(self, media_id: str) -> List[Dict]:
        """Get all processing lifecycles for a media file (all methods/models)"""
        
        query = """
        SELECT lifecycle_id, lifecycle_key, method_signature, status,
               created_at, last_modified, processing_count,
               total_faces_detected, total_frames_processed,
               average_confidence, processing_duration_seconds
        FROM detection_lifecycles 
        WHERE media_id = %s
        ORDER BY created_at ASC
        """
        
        results = await self.db.fetch_all(query, (media_id,))
        return results
        
    async def get_lifecycle_comparison_report(self, media_id: str) -> Dict:
        """Generate comparison report across all methods/models for a media file"""
        
        lifecycles = await self.get_all_lifecycles_for_media(media_id)
        
        comparison_report = {
            "media_id": media_id,
            "total_lifecycles": len(lifecycles),
            "methods_used": [],
            "performance_comparison": {},
            "detection_comparison": {},
            "processing_history": []
        }
        
        for lifecycle in lifecycles:
            method_sig = json.loads(lifecycle['method_signature'])
            method_name = f"{method_sig['vision_service_method']}_conf{method_sig['confidence_threshold']}"
            
            comparison_report["methods_used"].append(method_name)
            
            comparison_report["performance_comparison"][method_name] = {
                "processing_duration": lifecycle.get('processing_duration_seconds', 0),
                "processing_count": lifecycle.get('processing_count', 0),
                "last_processed": lifecycle.get('last_modified')
            }
            
            comparison_report["detection_comparison"][method_name] = {
                "total_faces": lifecycle.get('total_faces_detected', 0),
                "total_frames": lifecycle.get('total_frames_processed', 0),
                "average_confidence": lifecycle.get('average_confidence', 0.0),
                "faces_per_frame": (
                    lifecycle.get('total_faces_detected', 0) / 
                    max(lifecycle.get('total_frames_processed', 1), 1)
                )
            }
            
            comparison_report["processing_history"].append({
                "lifecycle_id": lifecycle['lifecycle_id'],
                "method": method_name,
                "created_at": lifecycle['created_at'],
                "last_modified": lifecycle['last_modified'],
                "status": lifecycle['status']
            })
        
        return comparison_report
```

#### **2. HTTP Service Clients**

```python
# ppl-meta-orchestrator/src/clients/media_service_client.py

class MediaServiceClient:
    """HTTP client for Media Service communication with session traceability"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = aiohttp.ClientSession()
        self.tracer = ServiceCallTracer("media_service")
        
    async def get_media_info_with_sessions(
        self, 
        media_id: str,
        correlation_id: str = None
    ) -> Dict:
        """Get media metadata, streaming URLs, and complete session history"""
        
        # Log service call for traceability
        call_id = await self.tracer.log_call_start({
            "method": "get_media_info_with_sessions",
            "media_id": media_id,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        try:
            headers = {"X-Correlation-ID": correlation_id} if correlation_id else {}
            
            async with self.session.get(
                f"{self.base_url}/api/v1/media/{media_id}/info-with-sessions",
                headers=headers
            ) as response:
                result = await response.json()
                
                # Add session history and source traceability
                result['traceability'] = {
                    "service_call_id": call_id,
                    "correlation_id": correlation_id,
                    "response_timestamp": datetime.utcnow().isoformat(),
                    "source_service": "media_service"
                }
                
                await self.tracer.log_call_success(call_id, result)
                return result
                
        except Exception as e:
            await self.tracer.log_call_failure(call_id, str(e))
            raise
            
    async def get_session_lifecycle_history(self, media_id: str) -> List[Dict]:
        """Get complete session lifecycle history for media"""
        async with self.session.get(
            f"{self.base_url}/api/v1/media/{media_id}/session-history"
        ) as response:
            return await response.json()
            
    async def get_media_source_provenance(self, media_id: str) -> Dict:
        """Get complete source provenance information"""
        async with self.session.get(
            f"{self.base_url}/api/v1/media/{media_id}/source-provenance"
        ) as response:
            return await response.json()


# ppl-meta-orchestrator/src/clients/vision_service_client.py

class VisionServiceClient:
    """HTTP client for Vision Service communication with processing traceability"""
    
    def __init__(self):
        self.base_url = "http://localhost:8003"
        self.session = aiohttp.ClientSession()
        self.tracer = ServiceCallTracer("vision_service")
        
    async def start_bulk_processing_with_lifecycle(
        self,
        media_id: str,
        media_url: str,
        config: Dict,
        workflow_id: str = None,
        correlation_id: str = None,
        source_session_ids: List[str] = None,
        original_source_path: str = None,
        lifecycle_id: str = None,
        method_signature: str = None
    ) -> Dict:
        """Trigger bulk face processing with lifecycle tracking"""
        
        call_id = await self.tracer.log_call_start({
            "method": "start_bulk_processing_with_lifecycle",
            "media_id": media_id,
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "source_session_ids": source_session_ids,
            "lifecycle_id": lifecycle_id,
            "method_signature": method_signature
        })
        
        payload = {
            "media_id": media_id,
            "media_url": media_url,
            "method": config.get("method", "two_stage"),
            "confidence_threshold": config.get("confidence_threshold", 0.5),
            "frame_interval": config.get("frame_interval", 1),
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "lifecycle_tracking": {
                "lifecycle_id": lifecycle_id,
                "method_signature": method_signature,
                "source_session_ids": source_session_ids or [],
                "original_source_path": original_source_path,
                "initiated_by_workflow": workflow_id,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
        }
        
        try:
            headers = {"X-Correlation-ID": correlation_id} if correlation_id else {}
            
            async with self.session.post(
                f"{self.base_url}/faces/media/{media_id}/bulk-process-with-lifecycle",
                json=payload,
                headers=headers
            ) as response:
                result = await response.json()
                await self.tracer.log_call_success(call_id, result)
                return result
                
        except Exception as e:
            await self.tracer.log_call_failure(call_id, str(e))
            raise
            
    async def get_stored_faces_with_lifecycle(
        self, 
        media_id: str,
        lifecycle_id: str = None,
        include_source_sessions: bool = True,
        correlation_id: str = None
    ) -> Dict:
        """Get all stored face detections with lifecycle tracking"""
        
        params = {
            "include_source_sessions": include_source_sessions,
            "include_processing_lineage": True,
            "include_session_correlation": True,
            "include_lifecycle_tracking": True
        }
        
        if lifecycle_id:
            params["lifecycle_id"] = lifecycle_id
        
        headers = {"X-Correlation-ID": correlation_id} if correlation_id else {}
        
        async with self.session.get(
            f"{self.base_url}/faces/media/{media_id}/with-lifecycle",
            params=params,
            headers=headers
        ) as response:
            return await response.json()
            
    async def get_processing_status_with_sessions(
        self, 
        media_id: str,
        correlation_id: str = None
    ) -> Dict:
        """Check processing status with session correlation"""
        
        headers = {"X-Correlation-ID": correlation_id} if correlation_id else {}
        
        async with self.session.get(
            f"{self.base_url}/processing-status/{media_id}/with-sessions",
            headers=headers
        ) as response:
            return await response.json()
            
    async def get_face_detection_audit_trail(
        self, 
        media_id: str = None,
        workflow_id: str = None
    ) -> Dict:
        """Get complete audit trail for face detection operations"""
        
        params = {}
        if media_id:
            params['media_id'] = media_id
        if workflow_id:
            params['workflow_id'] = workflow_id
            
        async with self.session.get(
            f"{self.base_url}/audit/face-detection-trail",
            params=params
        ) as response:
            return await response.json()
```

#### **3. Enhanced Orchestrator API Endpoints with Camera Integration**

```python
# ppl-meta-orchestrator/src/main.py (additions)

from workflows.face_detection_workflows import FaceDetectionWorkflowOrchestrator
from workflows.camera_workflows import CameraFaceDetectionWorkflowOrchestrator

# Initialize workflow orchestrators
workflow_orchestrator = FaceDetectionWorkflowOrchestrator()
camera_workflow_orchestrator = CameraFaceDetectionWorkflowOrchestrator()

# === CAMERA EVENT ENDPOINTS ===

@app.post("/workflows/camera-events/video-stored")
async def handle_camera_video_stored_event(camera_event: Dict):
    """
    Handle camera video storage completion events and trigger face detection workflows
    
    Event Payload from Camera Service:
    {
        "event_type": "camera_video_stored",
        "camera_metadata": {
            "device_id": "camera_001",
            "device_name": "Living Room Camera",
            "device_location": "Living Room",
            "device_model": "PPL-CAM-HD-001"
        },
        "recording_metadata": {
            "session_id": "recording_session_uuid",
            "video_file_path": "/storage/camera_001/video.mp4",
            "file_size": 52428800,
            "duration_seconds": 300,
            "trigger_type": "manual|interval|scheduled",
            "recorded_at": "ISO timestamp"
        },
        "user_settings": {
            "face_detection_enabled": true,
            "detection_method": "MTCNN",
            "confidence_threshold": 0.8,
            "processing_priority": "normal",
            "user_id": "user_123"
        },
        "timestamp": "ISO timestamp",
        "correlation_id": "uuid"
    }
    
    Response:
    {
        "success": true,
        "workflow_id": "uuid",
        "correlation_id": "uuid",
        "lifecycle_id": "uuid",
        "media_id": "string",
        "camera_attribution": {
            "device_id": "camera_001",
            "device_name": "Living Room Camera",
            "recording_trigger": "interval"
        },
        "processing_status": "initiated|processing|completed",
        "traceability": {
            "camera_source": true,
            "recording_session_id": "uuid",
            "automated_trigger": true
        }
    }
    """
    try:
        result = await camera_workflow_orchestrator.handle_camera_video_stored_event(
            camera_event=camera_event
        )
        
        return result
        
    except Exception as e:
        await audit_logger.log_camera_event_failure({
            "event": camera_event,
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Camera event processing failed: {str(e)}"
        )

@app.get("/workflows/camera-events/status/{workflow_id}")
async def get_camera_workflow_status(workflow_id: str):
    """
    Get status of camera-triggered face detection workflow
    
    Response includes camera attribution and processing details
    """
    try:
        status = await camera_workflow_orchestrator.get_camera_workflow_status(
            workflow_id=workflow_id
        )
        
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Camera workflow not found: {str(e)}"
        )

# === CAMERA SETTINGS ENDPOINTS ===

@app.post("/workflows/camera-settings/configure")
async def configure_camera_settings(settings_request: CameraSettingsRequest):
    """
    Configure camera automation and face detection settings
    
    Request:
    {
        "user_id": "string",
        "camera_device_id": "string",
        "settings": {
            "automated_recording_enabled": true,
            "recording_interval_minutes": 60,
            "recording_duration_seconds": 300,
            "face_detection_enabled": true,
            "detection_method": "MTCNN",
            "confidence_threshold": 0.8,
            "processing_priority": "normal",
            "notify_on_completion": false
        }
    }
    """
    try:
        result = await camera_workflow_orchestrator.configure_camera_settings(
            user_id=settings_request.user_id,
            camera_device_id=settings_request.camera_device_id,
            settings=settings_request.settings
        )
        
        return {"success": True, "settings_updated": result}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Camera settings configuration failed: {str(e)}"
        )

@app.get("/workflows/camera-settings/{user_id}")
async def get_user_camera_settings(user_id: str):
    """
    Get all camera settings for a specific user
    
    Response:
    {
        "user_id": "string",
        "cameras": [
            {
                "camera_device_id": "camera_001",
                "device_name": "Living Room Camera",
                "settings": {...},
                "statistics": {
                    "total_recordings": 150,
                    "total_faces_detected": 423,
                    "last_processing": "ISO timestamp"
                }
            }
        ]
    }
    """
    try:
        settings = await camera_workflow_orchestrator.get_user_camera_settings(
            user_id=user_id
        )
        
        return settings
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"User camera settings not found: {str(e)}"
        )

# === CAMERA ANALYTICS ENDPOINTS ===

@app.get("/workflows/camera-analytics/{camera_device_id}")
async def get_camera_analytics(
    camera_device_id: str,
    time_range: str = "7d",  # 1d, 7d, 30d, 90d
    include_face_details: bool = False
):
    """
    Get comprehensive analytics for a specific camera
    
    Response:
    {
        "camera_device_id": "string",
        "device_info": {...},
        "time_range": "7d",
        "recording_statistics": {
            "total_recordings": 48,
            "manual_recordings": 12,
            "automated_recordings": 36,
            "total_duration_hours": 24.5,
            "average_recording_duration": 305
        },
        "face_detection_statistics": {
            "total_faces_detected": 127,
            "unique_faces": 8,
            "detection_methods_used": ["MTCNN", "Haar"],
            "average_confidence": 0.82,
            "processing_success_rate": 0.96
        },
        "timeline": [
            {
                "timestamp": "ISO",
                "event_type": "recording|processing|faces_detected",
                "details": {...}
            }
        ],
        "performance_metrics": {...}
    }
    """
    try:
        analytics = await camera_workflow_orchestrator.get_camera_analytics(
            camera_device_id=camera_device_id,
            time_range=time_range,
            include_face_details=include_face_details
        )
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Camera analytics not found: {str(e)}"
        )

# === EXISTING ENDPOINTS (Enhanced with Camera Support) ===

@app.post("/workflows/face-detection/bulk-process")
async def orchestrate_bulk_face_processing(request: BulkProcessingRequest):
    """
    Orchestrate Media→Vision bulk face processing workflow with method-specific lifecycle tracking
    
    Request:
    {
        "media_id": "string",
        "workflow_config": {
            "method": "two_stage",
            "confidence_threshold": 0.5,
            "frame_interval": 1,
            "store_to_database": true
        },
        "priority": "normal|high|low",
        "callback_url": "optional webhook URL",
        "user_id": "string (for audit trail)",
        "session_context": {
            "client_session_id": "string",
            "frontend_version": "string",
            "request_source": "string"
        }
    }
    
    Response includes complete lifecycle tracking:
    {
        "success": true,
        "workflow_id": "uuid",
        "correlation_id": "uuid",
        "lifecycle_id": "uuid",
        "method_signature": "sha256_hash",
        "lifecycle_status": "new|existing",
        "status": "initiated|processing|completed",
        "estimated_completion": "ISO timestamp",
        "progress_url": "/workflows/face-detection/status/{workflow_id}",
        "lifecycle_comparison": {
            "existing_lifecycles": [
                {
                    "lifecycle_id": "uuid",
                    "method_signature": "sha256_hash",
                    "method_config": {...},
                    "last_processed": "ISO timestamp",
                    "face_count": 42
                }
            ],
            "is_new_method": true,
            "method_differences": ["confidence_threshold", "frame_interval"]
        },
        "traceability": {
            "media_source_path": "string",
            "session_correlation_ids": ["session_id1", "session_id2"],
            "initiated_by_user": "user_id",
            "initiated_at": "ISO timestamp",
            "audit_trail_url": "/workflows/traceability/{workflow_id}"
        }
    }
    """
    try:
        # Generate correlation ID for end-to-end traceability
        correlation_id = str(uuid.uuid4())
        
        result = await workflow_orchestrator.coordinate_bulk_face_processing(
            media_id=request.media_id,
            workflow_config=request.workflow_config,
            user_id=request.user_id,
            session_context={
                **request.session_context,
                "correlation_id": correlation_id,
                "api_endpoint": "bulk-process",
                "initiated_at": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "success": True,
            "workflow_id": result.workflow_id,
            "correlation_id": correlation_id,
            "lifecycle_id": result.lifecycle_id,
            "method_signature": result.method_signature,
            "lifecycle_status": result.lifecycle_status,
            "status": result.status,
            "estimated_completion": result.estimated_completion,
            "progress_url": f"/workflows/face-detection/status/{result.workflow_id}",
            "lifecycle_comparison": result.lifecycle_comparison,
            "traceability": {
                "media_source_path": result.media_source_path,
                "session_correlation_ids": result.session_correlation_ids,
                "initiated_by_user": request.user_id,
                "initiated_at": result.initiated_at,
                "audit_trail_url": f"/workflows/traceability/{result.workflow_id}",
                "lifecycle_history_url": f"/workflows/lifecycles/{result.lifecycle_id}"
            }
        }
        
    except Exception as e:
        # Log failure with complete context for audit trail
        await audit_logger.log_api_failure({
            "endpoint": "bulk-process",
            "media_id": request.media_id,
            "user_id": request.user_id,
            "error": str(e),
            "request_context": request.session_context,
            "failed_at": datetime.utcnow().isoformat()
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Workflow orchestration failed: {str(e)}"
        )

@app.get("/workflows/face-detection/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Get comprehensive workflow status with method-specific lifecycle tracking
    
    Response:
    {
        "workflow_id": "string",
        "correlation_id": "string",
        "lifecycle_id": "string",
        "method_signature": "string",
        "status": "pending|processing|completed|failed",
        "progress_percentage": 0-100,
        "current_phase": "string",
        "estimated_completion": "ISO timestamp",
        "results_preview": {...},
        "performance_metrics": {...},
        "lifecycle_metadata": {
            "is_new_lifecycle": true,
            "existing_faces_count": 42,
            "previous_processing_timestamp": "ISO timestamp",
            "method_changes_from_previous": ["confidence_threshold"]
        },
        "method_comparison": {
            "current_method": {...},
            "other_lifecycles": [...],
            "performance_comparison": {...}
        },
        "traceability": {
            "original_media_source": "string",
            "processing_history": [...],
            "session_correlations": [...],
            "cross_service_calls": [...],
            "user_attribution": "string",
            "complete_audit_trail": [...],
            "lifecycle_history": [...]
        }
    }
    """
    try:
        status = await workflow_orchestrator.get_workflow_status_with_lifecycle(workflow_id)
        
        # Include complete lifecycle and traceability information
        lifecycle_report = await workflow_orchestrator.get_lifecycle_comparison_report(
            workflow_id=workflow_id
        )
        
        return {
            **status,
            "lifecycle_comparison": lifecycle_report.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow not found: {str(e)}"
        )

@app.get("/workflows/face-detection/analytics/{media_id}")
async def get_media_analytics(
    media_id: str,
    include_session_history: bool = True,
    include_processing_lineage: bool = True,
    lifecycle_id: str = None
):
    """
    Get aggregated face analytics with lifecycle-specific filtering and complete source lineage
    
    Response:
    {
        "media_id": "string",
        "processing_status": "processed|unprocessed|processing",
        "lifecycle_summary": {
            "total_lifecycles": 3,
            "active_lifecycle_id": "uuid",
            "method_signatures": [...],
            "method_comparison": {...}
        },
        "total_faces": 0,
        "faces_by_lifecycle": {
            "lifecycle_id_1": {"count": 15, "method": "two_stage", "confidence": 0.8},
            "lifecycle_id_2": {"count": 12, "method": "single_stage", "confidence": 0.6}
        },
        "faces_by_frame": {...},
        "analytics_summary": {...},
        "processing_metadata": {...},
        "traceability": {
            "original_source_info": {
                "file_path": "string",
                "upload_session_id": "string",
                "upload_timestamp": "ISO timestamp",
                "uploader_user_id": "string"
            },
            "streaming_sessions": [...],
            "processing_sessions": [...],
            "detection_lineage": [...],
            "cross_video_correlations": [...],
            "lifecycle_history": [...]
        }
    }
    """
    try:
        analytics = await workflow_orchestrator.get_media_face_analytics_with_lifecycle(
            media_id=media_id,
            include_session_history=include_session_history,
            lifecycle_id=lifecycle_id
        )
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analytics retrieval failed: {str(e)}"
        )

@app.get("/workflows/lifecycles/{lifecycle_id}")
async def get_lifecycle_details(lifecycle_id: str):
    """
    Get detailed information about a specific method lifecycle
    
    Response:
    {
        "lifecycle_id": "uuid",
        "method_signature": "sha256_hash",
        "method_config": {
            "method": "two_stage",
            "confidence_threshold": 0.8,
            "frame_interval": 1
        },
        "media_id": "string",
        "created_at": "ISO timestamp",
        "last_updated": "ISO timestamp",
        "processing_history": [...],
        "total_faces_detected": 42,
        "performance_metrics": {...},
        "method_comparison": {
            "other_lifecycles_for_media": [...],
            "performance_comparison": {...}
        },
        "traceability": {...}
    }
    """
    try:
        lifecycle = await workflow_orchestrator.get_lifecycle_details(lifecycle_id)
        return lifecycle.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Lifecycle not found: {str(e)}"
        )

@app.get("/workflows/traceability/{workflow_id}")
async def get_workflow_traceability_report(workflow_id: str):
    """
    Get comprehensive traceability report for audit and compliance
    
    Response:
    {
        "workflow_id": "string",
        "correlation_id": "string",
        "lifecycle_id": "string",
        "complete_audit_trail": [...],
        "media_source_provenance": {...},
        "session_lifecycle_history": [...],
        "cross_service_communication_log": [...],
        "processing_decision_trail": [...],
        "user_attribution_chain": [...],
        "compliance_metadata": {...},
        "data_lineage_graph": {...},
        "method_lifecycle_tracking": {...}
    }
    """
    try:
        report = await workflow_orchestrator.get_workflow_traceability_report(
            workflow_id=workflow_id
        )
        
        return report.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Traceability report not found: {str(e)}"
        )

@app.get("/workflows/traceability/media/{media_id}")
async def get_media_traceability_report(
    media_id: str,
    include_all_sessions: bool = True
):
    """
    Get complete traceability report for specific media across all workflows
    
    Response includes:
    - Complete upload and source history
    - All streaming sessions with client details
    - All processing workflows and results
    - Cross-service communication logs
    - User interaction history
    """
    try:
        report = await workflow_orchestrator.get_workflow_traceability_report(
            media_id=media_id,
            include_cross_service_calls=True,
            include_session_correlation=include_all_sessions
        )
        
        return report.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Media traceability report not found: {str(e)}"
        )

@app.get("/workflows/audit/user/{user_id}")
async def get_user_activity_audit(
    user_id: str,
    time_range_start: str = None,
    time_range_end: str = None
):
    """
    Get complete audit trail for user activities across all workflows
    
    For compliance and audit purposes - shows all user-initiated workflows,
    processing decisions, and system interactions with complete traceability
    """
    try:
        time_range = None
        if time_range_start and time_range_end:
            time_range = {
                "start": time_range_start,
                "end": time_range_end
            }
            
        report = await workflow_orchestrator.get_workflow_traceability_report(
            user_id=user_id,
            time_range=time_range,
            include_user_attribution=True,
            include_cross_service_calls=True
        )
        
        return report.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"User audit trail retrieval failed: {str(e)}"
        )

@app.post("/workflows/face-detection/batch-process")
async def orchestrate_batch_processing(request: BatchProcessingRequest):
    """
    Coordinate processing across multiple media files
    
    Request:
    {
        "media_ids": ["string", "string", ...],
        "batch_config": {
            "method": "two_stage",
            "confidence_threshold": 0.5,
            "parallel_processing": 3
        },
        "priority": "normal|high|low"
    }
    """
    try:
        result = await workflow_orchestrator.coordinate_progressive_analysis(
            media_ids=request.media_ids,
            batch_config=request.batch_config
        )
        
        return {
            "success": True,
            "batch_id": result.batch_id,
            "total_media": result.total_media,
            "status": "processing",
            "progress_url": f"/workflows/face-detection/batch-status/{result.batch_id}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )

@app.post("/workflows/face-detection/schedule")
async def schedule_processing_workflow(request: ScheduleRequest):
    """
    Schedule automated face detection workflows
    
    Request:
    {
        "schedule_type": "daily|weekly|on_upload",
        "workflow_config": {...},
        "target_criteria": {
            "media_types": ["video"],
            "min_duration": 30,
            "tags": ["unprocessed"]
        }
    }
    """
    try:
        scheduled_workflow = await workflow_orchestrator.schedule_automated_processing(
            schedule_config=request.schedule_config
        )
        
        return {
            "success": True,
            "schedule_id": scheduled_workflow.schedule_id,
            "next_execution": scheduled_workflow.next_execution,
            "status": "scheduled"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow scheduling failed: {str(e)}"
        )
```

---

## 🎯 **Workflow Types & Use Cases with Camera Integration**

### **1. Camera-Triggered Automated Processing**
**Trigger**: Camera recording completion event  
**Flow**: Camera Service → Storage Event → Orchestrator → Media Registration → Vision Processing → Results  
**Use Cases**: 
- **Interval Recording**: User sets 30-minute intervals, camera automatically records and processes faces
- **Manual Recording**: User taps start/stop record, face detection automatically triggered on completion
- **Security Monitoring**: Continuous automated recording with face detection for security analysis

### **2. User-Configured Automated Workflows**
**Trigger**: User-defined time intervals and settings  
**Flow**: Scheduler → Camera Recording → Storage → Orchestrator → Processing Pipeline  
**Use Cases**:
- **Daily Home Monitoring**: 4-hour intervals during daytime, MTCNN processing, email notifications
- **Business Security**: 1-hour intervals 24/7, high confidence threshold, immediate processing priority
- **Pet/Child Monitoring**: 10-minute intervals, gentle notification settings, low-priority processing

### **3. Immediate Bulk Processing**
**Trigger**: User requests face analytics for specific video  
**Flow**: Frontend → Orchestrator → Media Service (info) → Vision Service (processing) → Results  
**Use Cases**: 
- **User Upload Analysis**: User wants to analyze faces in a newly uploaded video
- **Historical Camera Video**: User selects past camera recording for retroactive analysis

### **4. Scheduled Batch Processing**  
**Trigger**: Automated schedule (daily/weekly)  
**Flow**: Orchestrator → Query unprocessed media → Bulk processing → Status updates  
**Use Cases**: 
- **Nightly Processing**: Automated processing of all unanalyzed videos including camera recordings
- **Weekly Camera Analytics**: Comprehensive analysis of all camera recordings from past week

### **5. Progressive Analytics**
**Trigger**: User selects multiple videos/cameras for analysis  
**Flow**: Orchestrator coordinates parallel processing across multiple media files  
**Use Cases**:
- **Multi-Camera Analysis**: Process recordings from multiple cameras simultaneously
- **Cross-Camera Face Tracking**: Identify same person across different camera feeds

### **6. Real-time Integration with Camera Events**
**Trigger**: Live camera events and user interactions  
**Flow**: Real-time event stream → Orchestrator → Immediate processing decisions  
**Use Cases**:
- **Motion-Triggered Recording**: Camera detects motion → starts recording → triggers face detection
- **Manual Control Override**: User manually starts recording → immediate processing with custom settings

### **7. Camera-Specific Analytics Workflows**
**Trigger**: Camera performance analysis requests  
**Flow**: Analytics Engine → Historical Data → Camera-specific insights  
**Use Cases**:
- **Camera Performance Reports**: Weekly analytics per camera showing face detection effectiveness
- **Coverage Analysis**: Identify optimal camera positioning based on face detection success rates
- **User Behavior Analytics**: Track user interaction patterns with camera recording features

### **📊 Enhanced Workflow Architecture Diagram**

```yaml
🎯 PPL Meta Platform - Camera-Integrated Face Detection Workflows

📹 CAMERA SERVICE (Port 8005)
├─ User Actions
│  ├─ Manual Start/Stop Recording
│  ├─ Configure Automation Settings
│  └─ Review Recording History
├─ Automated Operations
│  ├─ Interval-Based Recording
│  ├─ Scheduled Recording Events
│  └─ Storage Management
└─ Event Publishing
   ├─ Video Storage Complete Events
   ├─ Recording Session Metadata
   └─ Device Status Updates

🎼 ORCHESTRATOR SERVICE (Port 8002)
├─ Camera Event Handling
│  ├─ Video Storage Event Processing
│  ├─ User Settings Integration
│  └─ Automated Workflow Triggers
├─ Workflow Coordination
│  ├─ Media Service Registration
│  ├─ Vision Service Processing
│  └─ Lifecycle Management
├─ Automation Management
│  ├─ Interval Scheduling
│  ├─ Priority Queue Management
│  └─ Resource Optimization
└─ Analytics & Reporting
   ├─ Camera Performance Metrics
   ├─ Cross-Camera Correlations
   └─ User Interaction Analytics

📺 MEDIA SERVICE (Port 8000)
├─ Camera Video Registration
│  ├─ File Path Management
│  ├─ Camera Attribution
│  └─ Metadata Enrichment
├─ Streaming Integration
│  ├─ Real-time Preview
│  ├─ Historical Playback
│  └─ Session Tracking
└─ Storage Management
   ├─ File Organization
   ├─ Backup Coordination
   └─ Cleanup Automation

🔍 VISION SERVICE (Port 8003)
├─ Camera-Optimized Processing
│  ├─ Method-Specific Lifecycles
│  ├─ Camera-Aware Analytics
│  └─ Device Performance Tracking
├─ Automated Processing
│  ├─ Priority Queue Handling
│  ├─ Batch Optimization
│  └─ Resource Scheduling
└─ Results Integration
   ├─ Camera Attribution
   ├─ Timeline Correlation
   └─ Cross-Device Analytics

📱 FRONTEND INTEGRATION
├─ Camera Controls
│  ├─ Manual Recording Interface
│  ├─ Settings Configuration
│  └─ Real-time Status Display
├─ Automation Dashboard
│  ├─ Interval Configuration
│  ├─ Processing Status
│  └─ Analytics Visualization
└─ Results Display
   ├─ Camera-Specific Analytics
   ├─ Timeline Views
   └─ Cross-Camera Insights

🔄 COMPLETE WORKFLOW EXAMPLES:

Example 1: Manual Recording with Immediate Processing
┌─────────────────────────────────────────────────────────────────┐
│ 1. User taps "Start Record" in frontend                        │
│ 2. Camera Service starts recording session                     │
│ 3. User taps "Stop Record" after 2 minutes                    │
│ 4. Camera Service saves video to storage                       │
│ 5. Camera Service publishes "video_stored" event              │
│ 6. Orchestrator receives event with user settings             │
│ 7. Orchestrator registers video with Media Service            │
│ 8. Orchestrator triggers Vision Service processing            │
│ 9. Vision Service processes with user's method (MTCNN)        │
│ 10. Results stored with camera and session attribution        │
│ 11. Frontend notified of completion                           │
└─────────────────────────────────────────────────────────────────┘

Example 2: Automated Interval Recording
┌─────────────────────────────────────────────────────────────────┐
│ 1. User configures 30-minute intervals with MTCNN processing   │
│ 2. Orchestrator schedules recurring camera recording           │
│ 3. Timer expires → Orchestrator triggers camera recording      │
│ 4. Camera records for configured duration (5 minutes)         │
│ 5. Recording completes → Camera publishes storage event        │
│ 6. Orchestrator processes event with saved user settings      │
│ 7. Automated workflow processes video through pipeline        │
│ 8. Results stored with interval attribution                   │
│ 9. Cycle repeats every 30 minutes                            │
│ 10. User receives periodic analytics summaries               │
└─────────────────────────────────────────────────────────────────┘

Example 3: Multi-Camera Synchronized Processing
┌─────────────────────────────────────────────────────────────────┐
│ 1. Multiple cameras finish recording simultaneously            │
│ 2. All cameras publish storage events to Orchestrator         │
│ 3. Orchestrator batches events for parallel processing        │
│ 4. Media Service registers all videos with camera attribution │
│ 5. Vision Service processes all videos with optimal resource  │
│    allocation and camera-specific method lifecycles           │
│ 6. Results aggregated with cross-camera correlation analysis  │
│ 7. Frontend displays unified multi-camera analytics           │
└─────────────────────────────────────────────────────────────────┘
```  
**Use Case**: Analyzing entire video library for face analytics

### **4. Real-time Integration**
**Trigger**: New media upload  
**Flow**: Upload → Media Service → Orchestrator notification → Auto-processing  
**Use Case**: Automatic face detection for new content

### **5. Cross-Video Analytics**
**Trigger**: Advanced analytics request  
**Flow**: Orchestrator → Vision Service → Cross-reference faces across videos  
**Use Case**: Finding the same person across multiple videos

---

## 🔗 **Integration Benefits**

### **✅ Architecture Advantages**

### **1. Centralized Workflow Management with Complete Audit Trail**
   - Single point of coordination for all Media↔Vision workflows with comprehensive logging
   - Unified status tracking and progress monitoring with session correlation
   - Simplified frontend integration with complete traceability visibility

### **2. Programmatic Automation with Provenance Tracking**
   - Automated bulk processing workflows with source attribution
   - Scheduled background processing with complete audit trails
   - Event-driven processing triggers with user activity tracking

### **3. Enterprise Scalability with Session Lifecycle Management**
   - Coordinate processing across multiple videos with cross-correlation
   - Queue management for large-scale operations with progress visibility
   - Resource optimization and load balancing with performance traceability

### **4. Service Decoupling Maintained with Cross-Service Traceability**
   - Media Service remains focused on streaming with session tracking
   - Vision Service focuses on analytics with processing lineage
   - Orchestrator adds coordination without changing core responsibilities while maintaining complete audit trails

### **5. Frontend Simplification with End-to-End Visibility**
   - Single API for all workflow operations with traceability reports
   - Unified progress tracking with session correlation
   - Consolidated result aggregation with complete source attribution

### **✅ Implementation Benefits**

1. **Development Efficiency**
   - Reuse existing service APIs
   - No changes to Media/Vision service core functionality
   - Clear separation of concerns

2. **Operational Excellence**
   - Centralized monitoring and logging
   - Workflow status visibility
   - Error handling and recovery

3. **User Experience**
   - Simplified workflow controls
   - Real-time progress updates
   - Unified analytics dashboard

---

## 📊 **Frontend Integration**

### **🎯 Simplified Frontend Architecture**

```dart
// Frontend calls ONLY the Orchestrator service
class WorkflowApiClient {
  final Dio _dio;
  
  // Single endpoint for all workflow operations
  Future<WorkflowResult> triggerBulkProcessing(String mediaId) async {
    final response = await _dio.post(
      '/workflows/face-detection/bulk-process',
      data: {
        'media_id': mediaId,
        'workflow_config': {
          'method': 'two_stage',
          'confidence_threshold': 0.5
        }
      }
    );
    return WorkflowResult.fromJson(response.data);
  }
  
  // Get unified workflow status
  Future<WorkflowStatus> getWorkflowStatus(String workflowId) async {
    final response = await _dio.get(
      '/workflows/face-detection/status/$workflowId'
    );
    return WorkflowStatus.fromJson(response.data);
  }
  
  // Get comprehensive analytics
  Future<MediaAnalytics> getMediaAnalytics(String mediaId) async {
    final response = await _dio.get(
      '/workflows/face-detection/analytics/$mediaId'
    );
    return MediaAnalytics.fromJson(response.data);
  }
}
```

### **🎨 UI Components**

```dart
class WorkflowControlsPopup extends StatefulWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Trigger bulk processing
        ElevatedButton(
          onPressed: () => _triggerBulkProcessing(),
          child: Text('Analyze Faces'),
        ),
        
        // Show workflow status
        if (_workflowId != null)
          WorkflowStatusIndicator(workflowId: _workflowId),
          
        // Display results
        if (_analyticsResults != null)
          AnalyticsResultsWidget(results: _analyticsResults),
      ],
    );
  }
  
  Future<void> _triggerBulkProcessing() async {
    final workflow = await _workflowClient.triggerBulkProcessing(widget.mediaId);
    setState(() => _workflowId = workflow.workflowId);
    
    // Monitor progress
    _monitorWorkflowProgress(workflow.workflowId);
  }
}
```

---

## 🚀 **Implementation Roadmap with Camera Integration**

### **Phase 1: Core Orchestrator Extensions with Camera Support**
1. **Service Clients**: Create HTTP clients for Camera, Media, and Vision services
2. **Workflow Classes**: Implement FaceDetectionWorkflowOrchestrator and CameraFaceDetectionWorkflowOrchestrator
3. **Camera Event Handling**: Add camera video storage event processing endpoints
4. **Basic Endpoints**: Add bulk processing, status endpoints, and camera workflow triggers
5. **Database Integration**: Add workflow tracking, camera settings, and processing statistics storage

### **Phase 2: Camera Automation & User Settings**
1. **Camera Settings Management**: User configuration for automated recording and face detection
2. **Interval Scheduling**: Automated camera recording based on user-defined time intervals
3. **Event Publishing**: Camera Service integration for recording completion events
4. **Method Lifecycle Management**: Separate processing lifecycles for each detection method per camera
5. **Automation Engine**: Time-based triggers and automated workflow execution

### **Phase 3: Advanced Camera Analytics & Multi-Device Coordination**
1. **Multi-Camera Processing**: Parallel processing coordination across multiple camera devices
2. **Cross-Camera Analytics**: Face tracking and correlation across different camera feeds
3. **Performance Optimization**: Camera-specific processing queues and resource allocation
4. **Real-time Integration**: Live camera event processing and immediate workflow triggers
5. **Advanced Scheduling**: Complex automation rules and conditional processing

### **Phase 4: Frontend Integration with Camera Controls**
1. **Camera Control Interface**: Manual start/stop recording controls in frontend
2. **Settings Configuration**: User interface for camera automation and detection settings
3. **Real-time Status**: Live camera status and processing progress indicators
4. **Analytics Dashboard**: Camera-specific analytics and multi-camera insights visualization
5. **Notification System**: User alerts for processing completion and camera events

### **Phase 5: Enterprise Camera Management**
1. **Advanced Camera Analytics**: Historical performance, coverage analysis, and optimization recommendations
2. **Centralized Device Management**: Multi-user camera administration and permissions
3. **Compliance & Audit**: Complete camera activity logging and regulatory compliance features
4. **Scalability Features**: Enterprise-scale camera fleet management and processing coordination
5. **Integration APIs**: Third-party camera system integration and extended automation

### **📋 Camera Integration Implementation Priorities**

#### **High Priority (Phase 1-2)**
- ✅ **Camera Event Processing**: Core video storage event handling and workflow triggers
- ✅ **User Settings**: Basic automation configuration and face detection preferences
- ✅ **Method Lifecycles**: Separate processing tracking for each detection method per camera
- ✅ **Basic Automation**: Time interval recording and automated processing triggers

#### **Medium Priority (Phase 3-4)**  
- ⚙️ **Multi-Camera Coordination**: Parallel processing and cross-camera analytics
- ⚙️ **Frontend Controls**: User interface for camera management and settings
- ⚙️ **Advanced Analytics**: Performance metrics and optimization insights
- ⚙️ **Real-time Integration**: Live event processing and immediate responses

#### **Future Enhancements (Phase 5)**
- 🔮 **Enterprise Features**: Advanced fleet management and compliance tools
- 🔮 **AI Optimization**: Automatic camera positioning and detection method selection
- 🔮 **Third-party Integration**: External camera system compatibility
- 🔮 **Advanced Automation**: Smart scheduling based on usage patterns and performance

---

## 🎯 **Success Metrics with Camera Integration**

### **Technical Metrics**

- ✅ **Workflow Completion Rate**: >95% successful processing with complete audit trail (including camera-triggered workflows)
- ✅ **Response Time**: <2s for workflow initiation with traceability setup, <1s for camera event processing
- ✅ **Processing Throughput**: 10+ videos/minute bulk processing with lineage tracking, optimized camera queue handling
- ✅ **Error Recovery**: <1% failed workflows requiring manual intervention, all with detailed failure analysis
- ✅ **Traceability Coverage**: 100% end-to-end traceability for all workflows, camera events, and session correlations

### **Camera-Specific Metrics**

- 📹 **Camera Event Processing**: >99% camera video storage events processed successfully within 1 second
- 📹 **Automation Reliability**: >98% automated interval recordings trigger face detection workflows correctly
- 📹 **Multi-Camera Coordination**: Support for 20+ simultaneous camera processing with resource optimization
- 📹 **Settings Persistence**: 100% user camera settings maintained and applied correctly across automated workflows
- 📹 **Device Attribution**: Complete camera device traceability for every processed video and detected face

### **User Experience Metrics**

- ✅ **Integration Simplicity**: Single API for all workflow operations with built-in traceability and camera controls
- ✅ **Status Visibility**: Real-time progress updates with complete session history and camera attribution
- ✅ **Result Quality**: Comprehensive face analytics with source attribution and camera device information
- ✅ **Performance**: <5s to start processing, predictable completion times with progress lineage
- ✅ **Audit Access**: Complete workflow history and session correlation available instantly
- 📹 **Camera Control**: Intuitive start/stop recording with automated face detection trigger integration
- 📹 **Settings Management**: Easy configuration of automated recording intervals and detection preferences

### **Architecture Metrics**

- ✅ **Service Decoupling**: No changes to Media/Vision core functionality, added traceability layer and camera integration
- ✅ **Scalability**: Handle 100+ concurrent workflows with complete audit logging and multi-camera processing
- ✅ **Maintainability**: Clear separation of workflow logic with comprehensive traceability and camera automation
- ✅ **Extensibility**: Easy addition of new workflow types with built-in audit support and camera event handling
- ✅ **Compliance**: Complete audit trail for regulatory requirements and data governance
- 📹 **Camera Integration**: Seamless camera service integration without disrupting existing workflows

### **Traceability & Automation Metrics**

- ✅ **Session Correlation**: 100% correlation between Media sessions, Vision processing, and camera recording sessions
- ✅ **Source Attribution**: Complete video source provenance for every detected face including camera device details
- ✅ **User Attribution**: Full user activity tracking across all workflow operations and camera interactions
- ✅ **Cross-Service Visibility**: Complete inter-service communication logging including camera events
- ✅ **Audit Trail Completeness**: End-to-end workflow lineage with no gaps, including automated triggers
- 📹 **Camera Device Tracking**: Complete camera device lifecycle and processing history per device
- 📹 **Automation Traceability**: Full audit trail of automated recordings and interval-triggered processing

---

## 📝 **Conclusion**

The Orchestrator-based workflow architecture with **Camera Service Integration** and **complete traceability** provides the **comprehensive solution** for automated face detection management in the PPL Meta Platform:

1. **✅ Maintains Service Decoupling**: Media and Vision services keep their focused responsibilities with added session tracking
2. **✅ Adds Centralized Coordination**: Orchestrator manages complex cross-service workflows with complete audit trails
3. **📹 Enables Camera Automation**: Seamless integration with Camera Service for automated recording and processing workflows
4. **✅ Provides Method-Specific Lifecycles**: Separate processing tracking for each detection method/model combination
5. **✅ Enables Enterprise Scalability**: Bulk processing, scheduling, and advanced analytics with full traceability
6. **✅ Simplifies Frontend Integration**: Single API for all workflow operations with built-in audit capabilities and camera controls
7. **✅ Preserves Architecture Integrity**: No breaking changes to existing services while adding comprehensive traceability
8. **✅ Ensures Complete Traceability**: End-to-end audit trails, session correlation, and source attribution for compliance
9. **📹 Supports User-Defined Automation**: Configurable time intervals and automated processing triggers
10. **📹 Provides Multi-Camera Analytics**: Cross-camera face tracking and device-specific performance insights

This approach leverages the platform's existing strengths while adding sophisticated workflow management capabilities needed for enterprise-scale face detection operations, with the crucial additions of **Camera Service integration** and **complete traceability** throughout the entire system.

**Key Camera Integration Benefits**:

- **🎯 Automated Workflows**: User-configured time intervals automatically trigger recording and face detection
- **📱 Manual Controls**: Start/stop recording via frontend with immediate face detection processing
- **🔄 Event-Driven Processing**: Camera recording completion automatically triggers workflow orchestration
- **📊 Device Attribution**: Complete camera device tracking and performance analytics per camera
- **⚙️ User Settings**: Granular configuration of automation, detection methods, and notification preferences

**Key Traceability Benefits**:

- **100% Session Correlation**: Every face detection links back to original Media sessions and camera recordings
- **Complete Source Attribution**: Full provenance chain from camera recording to face detection results  
- **Comprehensive Audit Trails**: Every workflow action, camera event, user interaction, and cross-service call logged
- **Camera Device Tracking**: Complete device lifecycle, recording sessions, and processing history per camera
- **Compliance Ready**: Full audit capabilities for regulatory requirements and data governance
- **Real-time Visibility**: Complete workflow lineage available instantly for debugging and analysis

**Next Steps**: Begin Phase 1 implementation with core Orchestrator extensions, Camera Service integration, service client development, and comprehensive traceability infrastructure.
