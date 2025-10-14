# Camera Segment Recording - Complete Implementation Guide

This document provides comprehensive details on implementing camera segment recording functionality across the PPL Meta platform, including endpoints, video storage, orchestrator integration, and configurable segment intervals.

## 1. Current Recording Endpoints

### 1.1 Camera Service Endpoints (Port 8005)

#### **Start Recording**
```http
POST /api/v1/streaming/{device_id}/record/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "quality": "high",
  "duration": 30,
  "format": "mp4"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Recording started for camera {device_id}",
  "device_id": "camera_device_123",
  "recording_id": "rec_uuid_456",
  "started_at": "2025-10-13T10:00:00Z"
}
```

#### **Stop Recording**
```http
POST /api/v1/streaming/{device_id}/record/stop
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Recording stopped for camera {device_id}",
  "device_id": "camera_device_123",
  "recording_id": "rec_uuid_456",
  "file_path": "/recordings/recording_camera_device_123_20251013_100000.mp4",
  "media_id": "media_uuid_789",
  "stopped_at": "2025-10-13T10:00:30Z"
}
```

#### **Recording Status**
```http
GET /api/v1/streaming/{device_id}/record/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "device_id": "camera_device_123",
  "is_recording": true,
  "recording_id": "rec_uuid_456",
  "started_at": "2025-10-13T10:00:00Z",
  "duration_seconds": 15,
  "file_size_bytes": 1024000
}
```

### 1.2 Gateway Service Proxy Endpoints (Port 8080)

The Gateway service automatically proxies camera recording requests to the Camera service:

```http
POST /api/v1/streaming/{device_id}/record/start
POST /api/v1/streaming/{device_id}/record/stop
GET /api/v1/streaming/{device_id}/record/status
```

### 1.3 Flutter Frontend Integration

#### **Current Frontend Service Integration**

```dart
// ppl-meta-frontend/lib/services/camera_service.dart

class CameraService {
  /// Start recording for a camera
  Future<RecordingResult?> startRecording(String deviceId) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/streaming/$deviceId/record/start'),
      headers: _authService.getAuthHeaders(),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return RecordingResult.fromJson(data);
    }
    return null;
  }

  /// Stop recording for a camera
  Future<RecordingResult?> stopRecording(String deviceId) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/streaming/$deviceId/record/stop'),
      headers: _authService.getAuthHeaders(),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return RecordingResult.fromJson(data);
    }
    return null;
  }
}
```

#### **Orchestrator API Client (Enhanced)**

```dart
// ppl-meta-frontend/lib/services/orchestrator_api_client.dart

class OrchestratorApiClient {
  /// Start recording via orchestrator for session tracking
  Future<ApiResponse<RecordingSession>> startRecording(
    String cameraId, 
    RecordingRequest request
  ) async {
    return _makeRequest<RecordingSession>(
      'POST',
      '/api/v1/cameras/$cameraId/recording/start',
      body: request.toJson(),
      fromJson: (json) => RecordingSession.fromJson(json),
    );
  }

  /// Stop recording via orchestrator
  Future<ApiResponse<void>> stopRecording(String cameraId, String sessionId) async {
    return _makeRequest<void>(
      'POST',
      '/api/v1/cameras/$cameraId/recording/$sessionId/stop',
      fromJson: (json) => null,
    );
  }

  /// Get all recordings for a camera
  Future<ApiResponse<List<RecordingSession>>> getRecordings(String cameraId) async {
    return _makeRequest<List<RecordingSession>>(
      'GET',
      '/api/v1/cameras/$cameraId/recordings',
      fromJson: (json) => (json as List)
          .map((item) => RecordingSession.fromJson(item))
          .toList(),
    );
  }
}
```

## 2. Video Storage in Media Service and Event Triggers

### 2.1 Video Storage Process

When a camera recording completes, the following sequence occurs:

1. **Camera Service** → Records video locally in `/recordings/{device_id}/`
2. **Upload to Media Service** → Video transferred to Media service for storage
3. **Collection Assignment** → Video assigned to camera-specific collection
4. **Event Publication** → Recording completion event sent to Orchestrator
5. **Face Detection Trigger** → Automatic face detection initiated (if enabled)

### 2.2 Media Service Storage Structure

```python
# ppl-meta-cameras/src/services/camera_detection.py

async def _upload_recording_to_collection(self, recording_info: Dict, user_id: str) -> Optional[str]:
    """Upload recorded video to media service and assign to collection."""
    
    # Step 1: Upload video file to Media service
    media_response = await session.post(
        f"{MEDIA_SERVICE_URL}/api/v1/media/upload",
        data=upload_data,
        headers=headers
    )
    
    if media_response.status == 200:
        media_data = await media_response.json()
        media_id = media_data.get("id")
        media_uuid = media_data.get("uuid")
        
        # Step 2: Check if automatic face detection is enabled
        await self._check_and_trigger_face_detection(media_uuid, session, headers)
        
        # Step 3: Find or create camera collection
        collection_id = await self._find_or_create_camera_collection(
            device_id, user_id, session, headers
        )
        
        # Step 4: Assign video to collection
        await self._assign_media_to_collection(
            media_id, collection_id, user_id, session, headers
        )
        
        return media_uuid
```

### 2.3 Automatic Face Detection Event Trigger

```python
# ppl-meta-cameras/src/services/camera_detection.py

async def _check_and_trigger_face_detection(self, media_uuid: str, session, headers: Dict):
    """Check global setting and trigger face detection if enabled."""
    
    # Check the global face detection on save setting
    setting_url = f"{NODE_SERVICE_URL}/api/v1/settings/face_detection_on_save"
    
    async with session.get(setting_url, headers=headers) as response:
        if response.status == 200:
            setting_data = await response.json()
            is_enabled = setting_data.get("value") == "true"
            
            if is_enabled:
                logger.info(f"🎯 Face detection enabled, triggering for media {media_uuid}")
                await self._trigger_face_detection_workflow(media_uuid, session, headers)

async def _trigger_face_detection_workflow(self, media_uuid: str, session, headers: Dict):
    """Trigger Enhanced Logic V2 face detection workflow for uploaded media."""
    
    # Trigger via Orchestrator Enhanced Logic V2 endpoint
    orchestrator_url = f"{ORCHESTRATOR_SERVICE_URL}/api/v1/media/{media_uuid}/faces/enhanced-v2"
    
    async with session.get(orchestrator_url, headers=headers) as response:
        if response.status == 200:
            result = await response.json()
            session_uuid = result.get("session_uuid")
            total_faces = result.get("total_faces", 0)
            logger.info(f"🎯 ✅ Face detection completed: {total_faces} faces found")
```

### 2.4 Storage Events and Database Updates

When videos are stored, the following database updates occur:

**Media Service Database:**
- New media record created with camera attribution
- File metadata stored (size, duration, format)
- Collection assignment recorded

**Camera Service Database:**
- Recording session updated with completion status
- File path and media UUID linkage stored

**Orchestrator Database:**
- Workflow execution record created for face detection
- Session tracking for processing status
- Event audit trail maintained

## 3. Orchestrator Recording Endpoints for Session Tracking

### 3.1 New Orchestrator Recording Endpoints

To implement proper session tracking through the Orchestrator, we need to create new endpoints:

#### **File:** `ppl-meta-orchestrator/src/camera_recording_endpoints.py`

```python
"""
Camera Recording Endpoints for Orchestrator Service with Session Tracking
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from service_clients import CameraServiceClient
from workflow_orchestrator import CameraFaceDetectionWorkflowOrchestrator
from models import WorkflowExecution, TraceabilityLog

logger = logging.getLogger(__name__)
recording_router = APIRouter(prefix="/cameras", tags=["camera-recording"])


class RecordingStartRequest(BaseModel):
    """Request model for starting camera recording with session tracking."""
    
    quality: str = Field(default="high", description="Recording quality: low, medium, high")
    duration: Optional[int] = Field(default=None, description="Recording duration in seconds")
    format: str = Field(default="mp4", description="Video format")
    auto_face_detection: bool = Field(default=True, description="Enable automatic face detection")
    segment_interval: Optional[int] = Field(default=None, description="Segment interval in seconds")


class RecordingStopRequest(BaseModel):
    """Request model for stopping camera recording."""
    
    session_uuid: str = Field(..., description="Recording session UUID")


class RecordingResponse(BaseModel):
    """Response model for recording operations."""
    
    session_uuid: str
    camera_device_id: str
    recording_id: str
    status: str
    started_at: datetime
    workflow_id: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class RecordingEndpoints:
    """Camera recording endpoints with orchestrator session tracking."""
    
    def __init__(self, orchestrator: CameraFaceDetectionWorkflowOrchestrator):
        self.orchestrator = orchestrator
        self.camera_client = CameraServiceClient()
    
    async def start_recording_with_session(
        self, 
        camera_device_id: str, 
        request: RecordingStartRequest,
        user_id: str
    ) -> RecordingResponse:
        """Start camera recording with orchestrator session tracking."""
        
        # Generate session UUID for tracking
        session_uuid = str(uuid4())
        
        # Create workflow execution for tracking
        workflow = await self.orchestrator.create_workflow_execution(
            workflow_type="camera_recording",
            media_id=None,  # Will be set when recording completes
            camera_device_id=camera_device_id,
            user_id=user_id,
            metadata={
                "session_uuid": session_uuid,
                "recording_request": request.dict(),
                "auto_face_detection": request.auto_face_detection,
                "segment_interval": request.segment_interval
            }
        )
        
        # Start recording via Camera service
        recording_settings = {
            "quality": request.quality,
            "duration": request.duration,
            "format": request.format,
            "session_uuid": session_uuid,  # Pass session UUID to camera service
            "segment_interval": request.segment_interval
        }
        
        camera_response = await self.camera_client.start_recording(
            trace_ctx=workflow.get_trace_context(),
            camera_device_id=camera_device_id,
            recording_settings=recording_settings
        )
        
        if not camera_response.success:
            await self.orchestrator.mark_workflow_failed(
                workflow.workflow_id, 
                f"Camera service error: {camera_response.error_message}"
            )
            raise HTTPException(status_code=500, detail=camera_response.error_message)
        
        # Update workflow with recording details
        recording_data = camera_response.data
        await self.orchestrator.update_workflow_metadata(
            workflow.workflow_id,
            {
                "recording_id": recording_data.get("recording_id"),
                "camera_recording_started": True,
                "camera_response": recording_data
            }
        )
        
        return RecordingResponse(
            session_uuid=session_uuid,
            camera_device_id=camera_device_id,
            recording_id=recording_data.get("recording_id"),
            status="recording",
            started_at=datetime.now(),
            workflow_id=workflow.workflow_id,
            estimated_completion=None  # Calculate based on duration if provided
        )
    
    async def stop_recording_with_session(
        self, 
        camera_device_id: str, 
        request: RecordingStopRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """Stop camera recording and complete session tracking."""
        
        # Find workflow by session UUID
        workflow = await self.orchestrator.get_workflow_by_metadata(
            "session_uuid", request.session_uuid
        )
        
        if not workflow:
            raise HTTPException(
                status_code=404, 
                detail=f"Recording session {request.session_uuid} not found"
            )
        
        # Stop recording via Camera service
        camera_response = await self.camera_client.stop_recording(
            trace_ctx=workflow.get_trace_context(),
            camera_device_id=camera_device_id,
            session_id=request.session_uuid
        )
        
        if camera_response.success:
            recording_data = camera_response.data
            
            # Update workflow with completion details
            await self.orchestrator.update_workflow_metadata(
                workflow.workflow_id,
                {
                    "recording_completed": True,
                    "media_uuid": recording_data.get("media_uuid"),
                    "file_path": recording_data.get("file_path"),
                    "duration_seconds": recording_data.get("duration_seconds"),
                    "file_size_bytes": recording_data.get("file_size_bytes"),
                    "completion_response": recording_data
                }
            )
            
            # Mark workflow as completed
            await self.orchestrator.mark_workflow_completed(
                workflow.workflow_id,
                result_summary=f"Recording completed: {recording_data.get('file_path')}"
            )
            
            # Trigger face detection if enabled
            if workflow.metadata.get("auto_face_detection", True):
                media_uuid = recording_data.get("media_uuid")
                if media_uuid:
                    face_detection_workflow = await self.orchestrator.trigger_face_detection_workflow(
                        media_uuid=media_uuid,
                        camera_device_id=camera_device_id,
                        user_id=user_id,
                        parent_workflow_id=workflow.workflow_id
                    )
            
            return {
                "session_uuid": request.session_uuid,
                "status": "completed",
                "workflow_id": workflow.workflow_id,
                "recording_data": recording_data
            }
        else:
            await self.orchestrator.mark_workflow_failed(
                workflow.workflow_id,
                f"Failed to stop recording: {camera_response.error_message}"
            )
            raise HTTPException(status_code=500, detail=camera_response.error_message)


# Create endpoints instance (will be initialized in main.py)
recording_endpoints = None


@recording_router.post("/{camera_device_id}/recording/start")
async def start_camera_recording(
    camera_device_id: str,
    request: RecordingStartRequest,
    current_user: Dict = Depends(get_current_user)
) -> RecordingResponse:
    """Start camera recording with orchestrator session tracking."""
    
    if recording_endpoints is None:
        raise HTTPException(status_code=503, detail="Recording endpoints not initialized")
    
    return await recording_endpoints.start_recording_with_session(
        camera_device_id=camera_device_id,
        request=request,
        user_id=current_user.get("sub")
    )


@recording_router.post("/{camera_device_id}/recording/{session_uuid}/stop")
async def stop_camera_recording(
    camera_device_id: str,
    session_uuid: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Stop camera recording and complete session tracking."""
    
    if recording_endpoints is None:
        raise HTTPException(status_code=503, detail="Recording endpoints not initialized")
    
    request = RecordingStopRequest(session_uuid=session_uuid)
    return await recording_endpoints.stop_recording_with_session(
        camera_device_id=camera_device_id,
        request=request,
        user_id=current_user.get("sub")
    )


@recording_router.get("/{camera_device_id}/recordings")
async def get_camera_recordings(
    camera_device_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all recording sessions for a camera."""
    
    if recording_endpoints is None:
        raise HTTPException(status_code=503, detail="Recording endpoints not initialized")
    
    # Get workflows for this camera
    workflows = await recording_endpoints.orchestrator.get_workflows_by_camera(
        camera_device_id=camera_device_id,
        workflow_type="camera_recording",
        user_id=current_user.get("sub")
    )
    
    return {
        "camera_device_id": camera_device_id,
        "recordings": [
            {
                "session_uuid": w.metadata.get("session_uuid"),
                "workflow_id": w.workflow_id,
                "status": w.status,
                "started_at": w.created_at,
                "completed_at": w.completed_at,
                "recording_id": w.metadata.get("recording_id"),
                "media_uuid": w.metadata.get("media_uuid"),
                "duration_seconds": w.metadata.get("duration_seconds"),
                "file_size_bytes": w.metadata.get("file_size_bytes")
            }
            for w in workflows
        ]
    }
```

### 3.2 Gateway Integration for Orchestrator Recording Endpoints

Add the following routes to `ppl-meta-gateway/src/api/v1/router.py`:

```python
# Camera Recording Routes via Orchestrator (for session tracking)
@api_router.post("/orchestrator/cameras/{camera_device_id}/recording/start")
async def start_camera_recording_with_session(request: Request):
    """Proxy start camera recording with session tracking to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)

@api_router.post("/orchestrator/cameras/{camera_device_id}/recording/{session_uuid}/stop")
async def stop_camera_recording_with_session(request: Request):
    """Proxy stop camera recording with session tracking to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)

@api_router.get("/orchestrator/cameras/{camera_device_id}/recordings")
async def get_camera_recordings(request: Request):
    """Proxy get camera recordings to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)
```

## 4. Camera Recording Profile Implementation

### 4.1 Camera Recording Profile Entity

Instead of storing recording parameters directly on the camera, we introduce a dedicated "Camera Recording Profile" entity that provides reusable recording configurations.

#### **Camera Recording Profile Model**

```python
# ppl-meta-cameras/src/models/recording_profile.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from src.database import Base

class CameraRecordingProfile(Base):
    """Camera Recording Profile - Reusable recording configuration templates."""
    
    __tablename__ = "camera_recording_profiles"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Profile Identity
    name = Column(String(100), nullable=False, comment="User-friendly profile name")
    description = Column(Text, nullable=True, comment="Profile description and use case")
    is_system_default = Column(Boolean, default=False, comment="System-provided default profile")
    is_active = Column(Boolean, default=True, comment="Profile is available for use")
    
    # Recording Configuration
    segment_interval_seconds = Column(
        Integer, 
        default=None, 
        nullable=True,
        comment="Automatic recording segment interval in seconds. None = manual recording only"
    )
    
    segment_duration_seconds = Column(
        Integer, 
        default=30,
        nullable=False,
        comment="Duration of each recording segment in seconds"
    )
    
    max_segment_duration_seconds = Column(
        Integer, 
        default=300,
        nullable=False,
        comment="Maximum allowed duration for segments in seconds"
    )
    
    auto_segment_recording = Column(
        Boolean, 
        default=False,
        comment="Enable automatic interval-based recording"
    )
    
    recording_quality = Column(
        String(20), 
        default="medium",
        comment="Default recording quality: low, medium, high"
    )
    
    recording_format = Column(
        String(10), 
        default="mp4",
        comment="Video format for recordings"
    )
    
    auto_face_detection = Column(
        Boolean, 
        default=True,
        comment="Automatically trigger face detection on recorded videos"
    )
    
    storage_retention_days = Column(
        Integer, 
        default=30,
        comment="Number of days to retain recordings (0 = indefinite)"
    )
    
    # Metadata
    created_by = Column(String(100), nullable=False, comment="User ID who created this profile")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cameras = relationship("Camera", back_populates="recording_profile")

    def to_dict(self):
        """Convert profile to dictionary for API responses."""
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "name": self.name,
            "description": self.description,
            "is_system_default": self.is_system_default,
            "is_active": self.is_active,
            "segment_interval_seconds": self.segment_interval_seconds,
            "segment_duration_seconds": self.segment_duration_seconds,
            "max_segment_duration_seconds": self.max_segment_duration_seconds,
            "auto_segment_recording": self.auto_segment_recording,
            "recording_quality": self.recording_quality,
            "recording_format": self.recording_format,
            "auto_face_detection": self.auto_face_detection,
            "storage_retention_days": self.storage_retention_days,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
```

#### **Updated Camera Model**

```python
# ppl-meta-cameras/src/models/camera.py

class Camera(Base):
    """Camera model representing detected cameras."""
    
    __tablename__ = "cameras"
    
    # ... existing fields ...
    
    # Recording Profile Association
    recording_profile_id = Column(
        Integer, 
        ForeignKey('camera_recording_profiles.id'),
        nullable=True,
        comment="Associated recording profile ID"
    )
    
    # Relationships
    recording_profile = relationship("CameraRecordingProfile", back_populates="cameras")
    
    @property
    def effective_recording_config(self):
        """Get effective recording configuration from profile or defaults."""
        if self.recording_profile:
            return self.recording_profile.to_dict()
        else:
            # Return default configuration if no profile assigned
            return {
                "segment_interval_seconds": None,
                "segment_duration_seconds": 30,
                "max_segment_duration_seconds": 300,
                "auto_segment_recording": False,
                "recording_quality": "medium",
                "recording_format": "mp4",
                "auto_face_detection": True,
                "storage_retention_days": 30
            }
```

#### **Create Migration for Recording Profiles**

```python
# ppl-meta-cameras/alembic/versions/add_recording_profiles.py

"""Add camera recording profiles and update cameras table

Revision ID: recording_profiles_001
Create Date: 2025-10-13 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    """Create recording profiles table and update cameras table."""
    
    # Create camera_recording_profiles table
    op.create_table(
        'camera_recording_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('uuid', UUID(as_uuid=True), unique=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system_default', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('segment_interval_seconds', sa.Integer(), nullable=True),
        sa.Column('segment_duration_seconds', sa.Integer(), default=30),
        sa.Column('max_segment_duration_seconds', sa.Integer(), default=300),
        sa.Column('auto_segment_recording', sa.Boolean(), default=False),
        sa.Column('recording_quality', sa.String(20), default='medium'),
        sa.Column('recording_format', sa.String(10), default='mp4'),
        sa.Column('auto_face_detection', sa.Boolean(), default=True),
        sa.Column('storage_retention_days', sa.Integer(), default=30),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime())
    )
    
    # Add recording_profile_id to cameras table
    op.add_column('cameras', sa.Column('recording_profile_id', sa.Integer()))
    op.create_foreign_key(
        'fk_cameras_recording_profile',
        'cameras', 'camera_recording_profiles',
        ['recording_profile_id'], ['id']
    )
    
    # Insert default system profiles
    op.execute("""
        INSERT INTO camera_recording_profiles (
            name, description, is_system_default, segment_interval_seconds,
            segment_duration_seconds, auto_segment_recording, created_by
        ) VALUES 
        ('Manual Recording Only', 'Manual recording on-demand, no automatic segments', true, NULL, 30, false, 'system'),
        ('Security Monitor', 'Record 60s segments every 5 minutes for security', true, 300, 60, true, 'system'),
        ('Activity Logger', 'Frequent 15s segments every 30s for detailed tracking', true, 30, 15, true, 'system'),
        ('Event Detection', 'Balanced 30s segments every minute for general use', true, 60, 30, true, 'system'),
        ('High Traffic', 'Short 10s segments every 15s for busy areas', true, 15, 10, true, 'system')
    """)

def downgrade():
    """Remove recording profiles and revert cameras table."""
    op.drop_constraint('fk_cameras_recording_profile', 'cameras', type_='foreignkey')
    op.drop_column('cameras', 'recording_profile_id')
    op.drop_table('camera_recording_profiles')
```

### 4.2 Recording Profile API Endpoints

#### **Recording Profile Schemas**

```python
# ppl-meta-cameras/src/schemas/recording_profile.py

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class RecordingProfileBase(BaseModel):
    """Base recording profile schema."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Profile name")
    description: Optional[str] = Field(None, description="Profile description")
    segment_interval_seconds: Optional[int] = Field(
        None, ge=5, le=3600, description="Recording interval in seconds"
    )
    segment_duration_seconds: int = Field(
        30, ge=5, le=300, description="Duration of each segment"
    )
    max_segment_duration_seconds: int = Field(
        300, ge=30, le=7200, description="Maximum segment duration"
    )
    auto_segment_recording: bool = Field(
        False, description="Enable automatic interval recording"
    )
    recording_quality: str = Field(
        "medium", description="Recording quality: low, medium, high"
    )
    recording_format: str = Field(
        "mp4", description="Video format"
    )
    auto_face_detection: bool = Field(
        True, description="Auto-trigger face detection"
    )
    storage_retention_days: int = Field(
        30, ge=0, le=365, description="Days to retain recordings (0=indefinite)"
    )
    
    @validator('recording_quality')
    def validate_quality(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('Quality must be: low, medium, or high')
        return v
    
    @validator('recording_format')
    def validate_format(cls, v):
        if v not in ['mp4', 'avi', 'mov']:
            raise ValueError('Format must be: mp4, avi, or mov')
        return v

class RecordingProfileCreate(RecordingProfileBase):
    """Schema for creating new recording profile."""
    pass

class RecordingProfileUpdate(BaseModel):
    """Schema for updating recording profile."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    segment_interval_seconds: Optional[int] = Field(None, ge=5, le=3600)
    segment_duration_seconds: Optional[int] = Field(None, ge=5, le=300)
    max_segment_duration_seconds: Optional[int] = Field(None, ge=30, le=7200)
    auto_segment_recording: Optional[bool] = None
    recording_quality: Optional[str] = None
    recording_format: Optional[str] = None
    auto_face_detection: Optional[bool] = None
    storage_retention_days: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None

class RecordingProfileResponse(RecordingProfileBase):
    """Schema for recording profile API responses."""
    
    id: int
    uuid: str
    is_system_default: bool
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

#### **Recording Profile API Endpoints**

```python
# ppl-meta-cameras/src/api/v1/endpoints/recording_profiles.py

"""
Recording Profile Management API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

from src.database import get_db
from src.models.recording_profile import CameraRecordingProfile
from src.models.camera import Camera
from src.schemas.recording_profile import (
    RecordingProfileCreate, RecordingProfileUpdate, RecordingProfileResponse
)
from src.security.auth import get_current_user

router = APIRouter(prefix="/recording-profiles", tags=["recording-profiles"])

@router.get("/", response_model=List[RecordingProfileResponse])
async def list_recording_profiles(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_system: bool = Query(True, description="Include system default profiles"),
    active_only: bool = Query(True, description="Only return active profiles")
) -> List[RecordingProfileResponse]:
    """List all available recording profiles."""
    
    query = db.query(CameraRecordingProfile)
    
    if active_only:
        query = query.filter(CameraRecordingProfile.is_active == True)
    
    if not include_system:
        query = query.filter(CameraRecordingProfile.is_system_default == False)
        query = query.filter(CameraRecordingProfile.created_by == current_user.get("sub"))
    
    profiles = query.order_by(
        CameraRecordingProfile.is_system_default.desc(),
        CameraRecordingProfile.name
    ).all()
    
    return profiles

@router.get("/{profile_id}", response_model=RecordingProfileResponse)
async def get_recording_profile(
    profile_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RecordingProfileResponse:
    """Get a specific recording profile by ID."""
    
    profile = db.query(CameraRecordingProfile).filter(
        CameraRecordingProfile.id == profile_id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording profile {profile_id} not found"
        )
    
    # Check permissions for non-system profiles
    if not profile.is_system_default and profile.created_by != current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this recording profile"
        )
    
    return profile

@router.post("/", response_model=RecordingProfileResponse)
async def create_recording_profile(
    profile_data: RecordingProfileCreate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RecordingProfileResponse:
    """Create a new custom recording profile."""
    
    # Check for duplicate name for this user
    existing = db.query(CameraRecordingProfile).filter(
        CameraRecordingProfile.name == profile_data.name,
        CameraRecordingProfile.created_by == current_user.get("sub")
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recording profile '{profile_data.name}' already exists"
        )
    
    # Create new profile
    profile = CameraRecordingProfile(
        **profile_data.dict(),
        created_by=current_user.get("sub"),
        is_system_default=False
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return profile

@router.put("/{profile_id}", response_model=RecordingProfileResponse)
async def update_recording_profile(
    profile_id: int,
    profile_data: RecordingProfileUpdate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RecordingProfileResponse:
    """Update an existing recording profile."""
    
    profile = db.query(CameraRecordingProfile).filter(
        CameraRecordingProfile.id == profile_id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording profile {profile_id} not found"
        )
    
    # Only allow updates to user's own profiles or if admin
    if profile.is_system_default or profile.created_by != current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system profiles or profiles owned by other users"
        )
    
    # Update fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile

@router.delete("/{profile_id}")
async def delete_recording_profile(
    profile_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete a recording profile."""
    
    profile = db.query(CameraRecordingProfile).filter(
        CameraRecordingProfile.id == profile_id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording profile {profile_id} not found"
        )
    
    if profile.is_system_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system default profiles"
        )
    
    if profile.created_by != current_user.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete profiles owned by other users"
        )
    
    # Check if profile is in use by any cameras
    cameras_using_profile = db.query(Camera).filter(
        Camera.recording_profile_id == profile_id
    ).count()
    
    if cameras_using_profile > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete profile: {cameras_using_profile} cameras are using this profile"
        )
    
    db.delete(profile)
    db.commit()
    
    return {"message": f"Recording profile '{profile.name}' deleted successfully"}

@router.post("/{profile_id}/clone", response_model=RecordingProfileResponse)
async def clone_recording_profile(
    profile_id: int,
    new_name: str = Query(..., description="Name for the cloned profile"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RecordingProfileResponse:
    """Clone an existing recording profile."""
    
    source_profile = db.query(CameraRecordingProfile).filter(
        CameraRecordingProfile.id == profile_id
    ).first()
    
    if not source_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recording profile {profile_id} not found"
        )
    
    # Check for duplicate name
    existing = db.query(CameraRecordingProfile).filter(
        CameraRecordingProfile.name == new_name,
        CameraRecordingProfile.created_by == current_user.get("sub")
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recording profile '{new_name}' already exists"
        )
    
    # Clone the profile
    cloned_profile = CameraRecordingProfile(
        name=new_name,
        description=f"Cloned from '{source_profile.name}'",
        segment_interval_seconds=source_profile.segment_interval_seconds,
        segment_duration_seconds=source_profile.segment_duration_seconds,
        max_segment_duration_seconds=source_profile.max_segment_duration_seconds,
        auto_segment_recording=source_profile.auto_segment_recording,
        recording_quality=source_profile.recording_quality,
        recording_format=source_profile.recording_format,
        auto_face_detection=source_profile.auto_face_detection,
        storage_retention_days=source_profile.storage_retention_days,
        created_by=current_user.get("sub"),
        is_system_default=False,
        is_active=True
    )
    
    db.add(cloned_profile)
    db.commit()
    db.refresh(cloned_profile)
    
    return cloned_profile
```

### 4.3 Camera Assignment to Recording Profiles

#### **Camera Profile Assignment Endpoints**

```python
# ppl-meta-cameras/src/api/v1/endpoints/camera_settings.py

"""
Camera Settings API Endpoints with Recording Profile Integration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Optional

from src.database import get_db
from src.models.camera import Camera
from src.models.recording_profile import CameraRecordingProfile
from src.security.auth import get_current_user

router = APIRouter()

@router.get("/{device_id}/recording-profile")
async def get_camera_recording_profile(
    device_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Get the recording profile assigned to a camera."""
    
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {device_id} not found"
        )
    
    effective_config = camera.effective_recording_config
    
    return {
        "device_id": device_id,
        "recording_profile_id": camera.recording_profile_id,
        "recording_profile_name": camera.recording_profile.name if camera.recording_profile else "Default",
        "effective_config": effective_config,
        "supports_recording": camera.supports_recording
    }

@router.put("/{device_id}/recording-profile")
async def assign_recording_profile(
    device_id: str,
    profile_id: Optional[int] = None,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Assign a recording profile to a camera."""
    
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera {device_id} not found"
        )
    
    if not camera.supports_recording:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Camera {device_id} does not support recording"
        )
    
    if profile_id is not None:
        # Verify profile exists and is accessible
        profile = db.query(CameraRecordingProfile).filter(
            CameraRecordingProfile.id == profile_id,
            CameraRecordingProfile.is_active == True
        ).first()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recording profile {profile_id} not found or inactive"
            )
        
        # Check permissions for non-system profiles
        if not profile.is_system_default and profile.created_by != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign recording profile owned by another user"
            )
    
    # Update camera profile assignment
    camera.recording_profile_id = profile_id
    db.commit()
    db.refresh(camera)
    
    # If auto segment recording is enabled, start the scheduler
    if camera.recording_profile and camera.recording_profile.auto_segment_recording:
        await _schedule_automatic_recording_for_camera(camera)
    else:
        await _unschedule_automatic_recording_for_camera(device_id)
    
    return {
        "message": "Recording profile assigned successfully",
        "device_id": device_id,
        "recording_profile_id": camera.recording_profile_id,
        "recording_profile_name": camera.recording_profile.name if camera.recording_profile else "Default",
        "effective_config": camera.effective_recording_config
    }

async def _schedule_automatic_recording_for_camera(camera: Camera):
    """Schedule automatic recording based on camera's profile settings."""
    
    if not camera.recording_profile or not camera.recording_profile.auto_segment_recording:
        return
    
    profile = camera.recording_profile
    
    if profile.segment_interval_seconds:
        logger.info(
            f"Scheduling automatic recording for camera {camera.device_id}: "
            f"every {profile.segment_interval_seconds}s for {profile.segment_duration_seconds}s each"
        )
        
        from src.services.recording_scheduler import recording_scheduler
        
        job_id = f"camera_{camera.device_id}_auto_recording"
        
        recording_scheduler.add_job(
            func=_trigger_profile_based_recording,
            trigger="interval",
            seconds=profile.segment_interval_seconds,
            args=[camera.device_id, profile.id],
            id=job_id,
            replace_existing=True
        )

async def _unschedule_automatic_recording_for_camera(device_id: str):
    """Remove scheduled automatic recording for a camera."""
    
    from src.services.recording_scheduler import recording_scheduler
    
    job_id = f"camera_{device_id}_auto_recording"
    
    try:
        recording_scheduler.remove_job(job_id)
        logger.info(f"Unscheduled automatic recording for camera {device_id}")
    except:
        # Job may not exist, which is fine
        pass

async def _trigger_profile_based_recording(device_id: str, profile_id: int):
    """Trigger recording based on the camera's assigned profile."""
    
    from src.services.camera_detection import camera_service
    from src.database import SessionLocal
    
    db = SessionLocal()
    try:
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if not camera or not camera.recording_profile or camera.recording_profile.id != profile_id:
            logger.warning(f"Camera {device_id} profile mismatch, skipping scheduled recording")
            return
        
        profile = camera.recording_profile
        
        logger.info(f"Auto-triggering {profile.segment_duration_seconds}s recording for camera {device_id}")
        
        # Start recording with profile settings
        recording_info = await camera_service.start_recording(
            device_id=device_id,
            user_id="system",  # System-initiated recording
            quality=profile.recording_quality,
            duration=profile.segment_duration_seconds,
            format=profile.recording_format,
            auto_face_detection=profile.auto_face_detection
        )
        
        if recording_info:
            logger.info(f"Auto recording started for camera {device_id}: {recording_info['recording_id']}")
        else:
            logger.error(f"Failed to start auto recording for camera {device_id}")
    
    finally:
        db.close()
```

### 4.3.1 Custom Profile Storage and Retrieval

#### **User Profile Persistence Service**

```python
# ppl-meta-cameras/src/services/profile_storage_service.py

"""
Custom Recording Profile Storage and Retrieval Service
Handles user-specific profile templates and sharing functionality
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from uuid import uuid4

from src.database import get_db
from src.models.recording_profile import CameraRecordingProfile
from src.models.profile_templates import UserProfileTemplate, SharedProfileTemplate

logger = logging.getLogger(__name__)

class ProfileStorageService:
    """Service for managing user's custom recording profile storage and retrieval."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def save_user_profile_template(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any],
        template_name: str,
        description: Optional[str] = None,
        is_favorite: bool = False
    ) -> str:
        """Save a user's custom profile configuration as a reusable template."""
        
        # Create template record
        template = UserProfileTemplate(
            uuid=str(uuid4()),
            user_id=user_id,
            template_name=template_name,
            description=description,
            is_favorite=is_favorite,
            profile_config=profile_data,
            created_at=datetime.utcnow()
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Saved profile template '{template_name}' for user {user_id}")
        return template.uuid
    
    async def get_user_profile_templates(
        self, 
        user_id: str,
        favorites_only: bool = False,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all profile templates saved by a user."""
        
        query = self.db.query(UserProfileTemplate).filter(
            UserProfileTemplate.user_id == user_id
        )
        
        if favorites_only:
            query = query.filter(UserProfileTemplate.is_favorite == True)
        
        if search_query:
            query = query.filter(
                UserProfileTemplate.template_name.ilike(f"%{search_query}%")
            )
        
        templates = query.order_by(
            UserProfileTemplate.is_favorite.desc(),
            UserProfileTemplate.created_at.desc()
        ).all()
        
        return [
            {
                "uuid": template.uuid,
                "template_name": template.template_name,
                "description": template.description,
                "is_favorite": template.is_favorite,
                "profile_config": template.profile_config,
                "created_at": template.created_at.isoformat(),
                "last_used": template.last_used.isoformat() if template.last_used else None,
                "usage_count": template.usage_count
            }
            for template in templates
        ]
    
    async def load_profile_template(
        self, 
        user_id: str, 
        template_uuid: str
    ) -> Optional[Dict[str, Any]]:
        """Load a specific profile template and update usage statistics."""
        
        template = self.db.query(UserProfileTemplate).filter(
            UserProfileTemplate.uuid == template_uuid,
            UserProfileTemplate.user_id == user_id
        ).first()
        
        if not template:
            return None
        
        # Update usage statistics
        template.usage_count += 1
        template.last_used = datetime.utcnow()
        self.db.commit()
        
        return {
            "uuid": template.uuid,
            "template_name": template.template_name,
            "description": template.description,
            "profile_config": template.profile_config,
            "created_at": template.created_at.isoformat(),
            "is_favorite": template.is_favorite
        }
    
    async def update_profile_template(
        self,
        user_id: str,
        template_uuid: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing profile template."""
        
        template = self.db.query(UserProfileTemplate).filter(
            UserProfileTemplate.uuid == template_uuid,
            UserProfileTemplate.user_id == user_id
        ).first()
        
        if not template:
            return False
        
        # Update allowed fields
        allowed_fields = [
            'template_name', 'description', 'is_favorite', 'profile_config'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(template, field, value)
        
        template.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    async def delete_profile_template(
        self,
        user_id: str,
        template_uuid: str
    ) -> bool:
        """Delete a user's profile template."""
        
        template = self.db.query(UserProfileTemplate).filter(
            UserProfileTemplate.uuid == template_uuid,
            UserProfileTemplate.user_id == user_id
        ).first()
        
        if not template:
            return False
        
        self.db.delete(template)
        self.db.commit()
        
        logger.info(f"Deleted profile template '{template.template_name}' for user {user_id}")
        return True
    
    async def create_profile_from_template(
        self,
        user_id: str,
        template_uuid: str,
        profile_name: str,
        profile_description: Optional[str] = None
    ) -> Optional[CameraRecordingProfile]:
        """Create a new recording profile from a saved template."""
        
        template = await self.load_profile_template(user_id, template_uuid)
        if not template:
            return None
        
        config = template['profile_config']
        
        # Create new recording profile from template
        profile = CameraRecordingProfile(
            name=profile_name,
            description=profile_description or template['description'],
            segment_interval_seconds=config.get('segment_interval_seconds'),
            segment_duration_seconds=config.get('segment_duration_seconds', 30),
            max_segment_duration_seconds=config.get('max_segment_duration_seconds', 300),
            auto_segment_recording=config.get('auto_segment_recording', False),
            recording_quality=config.get('recording_quality', 'medium'),
            recording_format=config.get('recording_format', 'mp4'),
            auto_face_detection=config.get('auto_face_detection', True),
            storage_retention_days=config.get('storage_retention_days', 30),
            created_by=user_id,
            is_system_default=False
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    async def export_profile_template(
        self,
        user_id: str,
        template_uuid: str
    ) -> Optional[Dict[str, Any]]:
        """Export a profile template for sharing or backup."""
        
        template = self.db.query(UserProfileTemplate).filter(
            UserProfileTemplate.uuid == template_uuid,
            UserProfileTemplate.user_id == user_id
        ).first()
        
        if not template:
            return None
        
        return {
            "template_name": template.template_name,
            "description": template.description,
            "profile_config": template.profile_config,
            "export_version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "original_author": user_id
        }
    
    async def import_profile_template(
        self,
        user_id: str,
        import_data: Dict[str, Any],
        custom_name: Optional[str] = None
    ) -> str:
        """Import a profile template from exported data."""
        
        template_name = custom_name or f"{import_data['template_name']} (Imported)"
        
        template = UserProfileTemplate(
            uuid=str(uuid4()),
            user_id=user_id,
            template_name=template_name,
            description=f"Imported: {import_data.get('description', '')}",
            is_favorite=False,
            profile_config=import_data['profile_config'],
            created_at=datetime.utcnow(),
            imported_from=import_data.get('original_author')
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template.uuid

# Template storage models
class UserProfileTemplate(Base):
    """User's saved profile configuration templates."""
    
    __tablename__ = "user_profile_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    template_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    profile_config = Column(JSON, nullable=False)  # Store complete profile configuration
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    imported_from = Column(String(100), nullable=True)  # Original author if imported
```

#### **Profile Template API Endpoints**

```python
# ppl-meta-cameras/src/api/v1/endpoints/profile_templates.py

"""
Profile Template Storage and Retrieval API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json

from src.database import get_db
from src.services.profile_storage_service import ProfileStorageService
from src.security.auth import get_current_user

router = APIRouter(prefix="/profile-templates", tags=["profile-templates"])

@router.post("/save")
async def save_profile_template(
    template_data: Dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Save current profile configuration as a reusable template."""
    
    storage_service = ProfileStorageService(db)
    
    template_uuid = await storage_service.save_user_profile_template(
        user_id=current_user.get("sub"),
        profile_data=template_data.get("profile_config"),
        template_name=template_data.get("template_name"),
        description=template_data.get("description"),
        is_favorite=template_data.get("is_favorite", False)
    )
    
    return {
        "message": "Profile template saved successfully",
        "template_uuid": template_uuid,
        "template_name": template_data.get("template_name")
    }

@router.get("/", response_model=List[Dict])
async def get_user_profile_templates(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    favorites_only: bool = Query(False, description="Only return favorite templates"),
    search: Optional[str] = Query(None, description="Search templates by name")
) -> List[Dict]:
    """Get all profile templates saved by the current user."""
    
    storage_service = ProfileStorageService(db)
    
    templates = await storage_service.get_user_profile_templates(
        user_id=current_user.get("sub"),
        favorites_only=favorites_only,
        search_query=search
    )
    
    return templates

@router.get("/{template_uuid}")
async def get_profile_template(
    template_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Load a specific profile template."""
    
    storage_service = ProfileStorageService(db)
    
    template = await storage_service.load_profile_template(
        user_id=current_user.get("sub"),
        template_uuid=template_uuid
    )
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile template {template_uuid} not found"
        )
    
    return template

@router.put("/{template_uuid}")
async def update_profile_template(
    template_uuid: str,
    updates: Dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Update an existing profile template."""
    
    storage_service = ProfileStorageService(db)
    
    success = await storage_service.update_profile_template(
        user_id=current_user.get("sub"),
        template_uuid=template_uuid,
        updates=updates
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile template {template_uuid} not found"
        )
    
    return {"message": "Profile template updated successfully"}

@router.delete("/{template_uuid}")
async def delete_profile_template(
    template_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete a profile template."""
    
    storage_service = ProfileStorageService(db)
    
    success = await storage_service.delete_profile_template(
        user_id=current_user.get("sub"),
        template_uuid=template_uuid
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile template {template_uuid} not found"
        )
    
    return {"message": "Profile template deleted successfully"}

@router.post("/{template_uuid}/create-profile")
async def create_profile_from_template(
    template_uuid: str,
    profile_data: Dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Create a new recording profile from a saved template."""
    
    storage_service = ProfileStorageService(db)
    
    profile = await storage_service.create_profile_from_template(
        user_id=current_user.get("sub"),
        template_uuid=template_uuid,
        profile_name=profile_data.get("profile_name"),
        profile_description=profile_data.get("profile_description")
    )
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile template {template_uuid} not found"
        )
    
    return {
        "message": "Recording profile created from template",
        "profile_id": profile.id,
        "profile_uuid": str(profile.uuid),
        "profile_name": profile.name
    }

@router.get("/{template_uuid}/export")
async def export_profile_template(
    template_uuid: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """Export a profile template for sharing or backup."""
    
    storage_service = ProfileStorageService(db)
    
    export_data = await storage_service.export_profile_template(
        user_id=current_user.get("sub"),
        template_uuid=template_uuid
    )
    
    if not export_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile template {template_uuid} not found"
        )
    
    return export_data

@router.post("/import")
async def import_profile_template(
    import_file: UploadFile = File(...),
    custom_name: Optional[str] = Query(None, description="Custom name for imported template"),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Import a profile template from exported JSON file."""
    
    try:
        content = await import_file.read()
        import_data = json.loads(content.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file format"
        )
    
    # Validate required fields
    required_fields = ['template_name', 'profile_config']
    if not all(field in import_data for field in required_fields):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields in import data"
        )
    
    storage_service = ProfileStorageService(db)
    
    template_uuid = await storage_service.import_profile_template(
        user_id=current_user.get("sub"),
        import_data=import_data,
        custom_name=custom_name
    )
    
    return {
        "message": "Profile template imported successfully",
        "template_uuid": template_uuid,
        "template_name": import_data['template_name']
    }

@router.put("/{template_uuid}/favorite")
async def toggle_template_favorite(
    template_uuid: str,
    is_favorite: bool,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Toggle favorite status for a profile template."""
    
    storage_service = ProfileStorageService(db)
    
    success = await storage_service.update_profile_template(
        user_id=current_user.get("sub"),
        template_uuid=template_uuid,
        updates={"is_favorite": is_favorite}
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile template {template_uuid} not found"
        )
    
    return {
        "message": f"Template {'added to' if is_favorite else 'removed from'} favorites"
    }
```

### 4.4 Flutter Frontend Integration for Recording Profiles

#### **Camera Settings UI Component**

```dart
// ppl-meta-frontend/lib/presentation/pages/camera_settings_page.dart

class CameraSegmentSettingsWidget extends StatefulWidget {
  final String cameraId;
  final Function(CameraSegmentConfig) onConfigUpdated;
  
  const CameraSegmentSettingsWidget({
    Key? key,
    required this.cameraId,
    required this.onConfigUpdated,
  }) : super(key: key);

  @override
  _CameraSegmentSettingsWidgetState createState() => _CameraSegmentSettingsWidgetState();
}

class _CameraSegmentSettingsWidgetState extends State<CameraSegmentSettingsWidget> {
  final CameraService _cameraService = CameraService();
  
  bool _autoSegmentRecording = false;
  int _segmentInterval = 5; // Default 5 seconds
  int _segmentDuration = 30; // Default 30 seconds duration
  bool _isLoading = false;
  
  @override
  void initState() {
    super.initState();
    _loadCurrentConfig();
  }
  
  Future<void> _loadCurrentConfig() async {
    setState(() => _isLoading = true);
    
    try {
      final config = await _cameraService.getCameraSegmentConfig(widget.cameraId);
      if (config != null) {
        setState(() {
          _autoSegmentRecording = config.autoSegmentRecording;
          _segmentInterval = config.segmentIntervalSeconds ?? 5;
          _segmentDuration = config.maxSegmentDuration ?? 30;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load camera settings: $e'))
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
  
  Future<void> _updateConfig() async {
    setState(() => _isLoading = true);
    
    try {
      final config = CameraSegmentConfigRequest(
        segmentIntervalSeconds: _autoSegmentRecording ? _segmentInterval : null,
        autoSegmentRecording: _autoSegmentRecording,
        segmentDuration: _segmentDuration,
      );
      
      final result = await _cameraService.updateCameraSegmentConfig(widget.cameraId, config);
      
      if (result != null) {
        widget.onConfigUpdated(result);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Camera segment settings updated successfully'))
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update settings: $e'))
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Segment Recording Configuration',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            
            SwitchListTile(
              title: const Text('Enable Automatic Segment Recording'),
              subtitle: const Text('Record video segments at regular intervals'),
              value: _autoSegmentRecording,
              onChanged: (value) {
                setState(() => _autoSegmentRecording = value);
              },
            ),
            
            if (_autoSegmentRecording) ...[
              const SizedBox(height: 16),
              
              Text(
                'Recording Interval: $_segmentInterval seconds',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Slider(
                value: _segmentInterval.toDouble(),
                min: 5,
                max: 300,
                divisions: 59,
                label: '$_segmentInterval seconds',
                onChanged: (value) {
                  setState(() => _segmentInterval = value.round());
                },
              ),
              const Text(
                'How often to start a new recording (5 seconds = new recording every 5 seconds)',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
              
              const SizedBox(height: 16),
              
              Text(
                'Segment Duration: $_segmentDuration seconds',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Slider(
                value: _segmentDuration.toDouble(),
                min: 5,
                max: 300,
                divisions: 59,
                label: '$_segmentDuration seconds',
                onChanged: (value) {
                  setState(() => _segmentDuration = value.round());
                },
              ),
              const Text(
                'Duration of each recording segment',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
            
            const SizedBox(height: 24),
            
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _loadCurrentConfig,
                  child: const Text('Reset'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _updateConfig,
                  child: const Text('Save Settings'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
```

#### **Camera Service Extension**

```dart
// ppl-meta-frontend/lib/services/camera_service.dart

class CameraService {
  // ... existing methods ...
  
  /// Get camera segment recording configuration
  Future<CameraSegmentConfig?> getCameraSegmentConfig(String deviceId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/cameras/$deviceId/segment-config'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return CameraSegmentConfig.fromJson(data);
      }
      return null;
    } catch (e) {
      _logger.e('Error getting camera segment config: $e');
      return null;
    }
  }

  /// Update camera segment recording configuration
  Future<CameraSegmentConfig?> updateCameraSegmentConfig(
    String deviceId, 
    CameraSegmentConfigRequest config
  ) async {
    try {
      final response = await http.put(
        Uri.parse('$_baseUrl/api/v1/cameras/$deviceId/segment-config'),
        headers: _authService.getAuthHeaders(),
        body: json.encode(config.toJson()),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return CameraSegmentConfig.fromJson(data);
      }
      return null;
    } catch (e) {
      _logger.e('Error updating camera segment config: $e');
      return null;
    }
  }
}

/// Camera segment configuration model
class CameraSegmentConfig {
  final String deviceId;
  final int? segmentIntervalSeconds;
  final bool autoSegmentRecording;
  final int maxSegmentDuration;
  final bool supportsRecording;

  CameraSegmentConfig({
    required this.deviceId,
    this.segmentIntervalSeconds,
    required this.autoSegmentRecording,
    required this.maxSegmentDuration,
    required this.supportsRecording,
  });

  factory CameraSegmentConfig.fromJson(Map<String, dynamic> json) {
    return CameraSegmentConfig(
      deviceId: json['device_id'],
      segmentIntervalSeconds: json['segment_interval_seconds'],
      autoSegmentRecording: json['auto_segment_recording'] ?? false,
      maxSegmentDuration: json['max_segment_duration'] ?? 300,
      supportsRecording: json['supports_recording'] ?? false,
    );
  }
}

/// Request model for segment configuration updates
class CameraSegmentConfigRequest {
  final int? segmentIntervalSeconds;
  final bool autoSegmentRecording;
  final int segmentDuration;

  CameraSegmentConfigRequest({
    this.segmentIntervalSeconds,
    required this.autoSegmentRecording,
    required this.segmentDuration,
  });

  Map<String, dynamic> toJson() {
    return {
      'segment_interval_seconds': segmentIntervalSeconds,
      'auto_segment_recording': autoSegmentRecording,
      'segment_duration': segmentDuration,
    };
  }
}
```

#### **Custom Profile Template Service**

```dart
// ppl-meta-frontend/lib/services/recording_profile_template_service.dart

class RecordingProfileTemplateService {
  final String _baseUrl;
  final AuthService _authService;
  final Logger _logger = Logger('RecordingProfileTemplateService');

  RecordingProfileTemplateService({
    required String baseUrl,
    required AuthService authService,
  })  : _baseUrl = baseUrl,
        _authService = authService;

  /// Save current profile configuration as a template
  Future<ProfileTemplate?> saveProfileTemplate({
    required String templateName,
    required Map<String, dynamic> profileConfig,
    String? description,
    bool isFavorite = false,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/profile-templates/save'),
        headers: _authService.getAuthHeaders(),
        body: json.encode({
          'template_name': templateName,
          'description': description,
          'profile_config': profileConfig,
          'is_favorite': isFavorite,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _logger.i('Profile template saved: ${data['template_name']}');
        return ProfileTemplate.fromSaveResponse(data);
      }
      return null;
    } catch (e) {
      _logger.e('Error saving profile template: $e');
      return null;
    }
  }

  /// Get all user's profile templates
  Future<List<ProfileTemplate>?> getUserProfileTemplates({
    bool favoritesOnly = false,
    String? searchQuery,
  }) async {
    try {
      final queryParams = <String, String>{};
      if (favoritesOnly) queryParams['favorites_only'] = 'true';
      if (searchQuery?.isNotEmpty == true) queryParams['search'] = searchQuery!;

      final uri = Uri.parse('$_baseUrl/api/v1/profile-templates/')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await http.get(uri, headers: _authService.getAuthHeaders());

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        return data.map((item) => ProfileTemplate.fromJson(item)).toList();
      }
      return null;
    } catch (e) {
      _logger.e('Error getting profile templates: $e');
      return null;
    }
  }

  /// Load a specific profile template
  Future<ProfileTemplate?> getProfileTemplate(String templateUuid) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/profile-templates/$templateUuid'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return ProfileTemplate.fromJson(data);
      }
      return null;
    } catch (e) {
      _logger.e('Error loading profile template: $e');
      return null;
    }
  }

  /// Update a profile template
  Future<bool> updateProfileTemplate(
    String templateUuid,
    Map<String, dynamic> updates,
  ) async {
    try {
      final response = await http.put(
        Uri.parse('$_baseUrl/api/v1/profile-templates/$templateUuid'),
        headers: _authService.getAuthHeaders(),
        body: json.encode(updates),
      );

      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Error updating profile template: $e');
      return false;
    }
  }

  /// Delete a profile template
  Future<bool> deleteProfileTemplate(String templateUuid) async {
    try {
      final response = await http.delete(
        Uri.parse('$_baseUrl/api/v1/profile-templates/$templateUuid'),
        headers: _authService.getAuthHeaders(),
      );

      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Error deleting profile template: $e');
      return false;
    }
  }

  /// Create a recording profile from a template
  Future<RecordingProfile?> createProfileFromTemplate(
    String templateUuid,
    String profileName, {
    String? profileDescription,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/profile-templates/$templateUuid/create-profile'),
        headers: _authService.getAuthHeaders(),
        body: json.encode({
          'profile_name': profileName,
          'profile_description': profileDescription,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Return the created profile data
        return RecordingProfile.fromCreateResponse(data);
      }
      return null;
    } catch (e) {
      _logger.e('Error creating profile from template: $e');
      return null;
    }
  }

  /// Export a profile template for sharing
  Future<Map<String, dynamic>?> exportProfileTemplate(String templateUuid) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/profile-templates/$templateUuid/export'),
        headers: _authService.getAuthHeaders(),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      _logger.e('Error exporting profile template: $e');
      return null;
    }
  }

  /// Import a profile template from JSON
  Future<ProfileTemplate?> importProfileTemplate(
    String jsonData, {
    String? customName,
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/api/v1/profile-templates/import'),
      );

      request.headers.addAll(_authService.getAuthHeaders());
      
      if (customName?.isNotEmpty == true) {
        request.fields['custom_name'] = customName!;
      }

      request.files.add(http.MultipartFile.fromString(
        'import_file',
        jsonData,
        filename: 'profile_template.json',
      ));

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return ProfileTemplate.fromImportResponse(data);
      }
      return null;
    } catch (e) {
      _logger.e('Error importing profile template: $e');
      return null;
    }
  }

  /// Toggle favorite status for a template
  Future<bool> toggleTemplateFavorite(String templateUuid, bool isFavorite) async {
    try {
      final response = await http.put(
        Uri.parse('$_baseUrl/api/v1/profile-templates/$templateUuid/favorite?is_favorite=$isFavorite'),
        headers: _authService.getAuthHeaders(),
      );

      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Error toggling template favorite: $e');
      return false;
    }
  }
}

/// Profile Template Model
class ProfileTemplate {
  final String uuid;
  final String templateName;
  final String? description;
  final bool isFavorite;
  final Map<String, dynamic> profileConfig;
  final DateTime createdAt;
  final DateTime? lastUsed;
  final int usageCount;
  final String? importedFrom;

  ProfileTemplate({
    required this.uuid,
    required this.templateName,
    this.description,
    required this.isFavorite,
    required this.profileConfig,
    required this.createdAt,
    this.lastUsed,
    required this.usageCount,
    this.importedFrom,
  });

  factory ProfileTemplate.fromJson(Map<String, dynamic> json) {
    return ProfileTemplate(
      uuid: json['uuid'],
      templateName: json['template_name'],
      description: json['description'],
      isFavorite: json['is_favorite'] ?? false,
      profileConfig: json['profile_config'] as Map<String, dynamic>,
      createdAt: DateTime.parse(json['created_at']),
      lastUsed: json['last_used'] != null ? DateTime.parse(json['last_used']) : null,
      usageCount: json['usage_count'] ?? 0,
      importedFrom: json['imported_from'],
    );
  }

  factory ProfileTemplate.fromSaveResponse(Map<String, dynamic> json) {
    return ProfileTemplate(
      uuid: json['template_uuid'],
      templateName: json['template_name'],
      description: null,
      isFavorite: false,
      profileConfig: {},
      createdAt: DateTime.now(),
      usageCount: 0,
    );
  }

  factory ProfileTemplate.fromImportResponse(Map<String, dynamic> json) {
    return ProfileTemplate(
      uuid: json['template_uuid'],
      templateName: json['template_name'],
      description: null,
      isFavorite: false,
      profileConfig: {},
      createdAt: DateTime.now(),
      usageCount: 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'uuid': uuid,
      'template_name': templateName,
      'description': description,
      'is_favorite': isFavorite,
      'profile_config': profileConfig,
      'created_at': createdAt.toIso8601String(),
      'last_used': lastUsed?.toIso8601String(),
      'usage_count': usageCount,
      'imported_from': importedFrom,
    };
  }

  /// Get a user-friendly summary of the template configuration
  String getConfigSummary() {
    final config = profileConfig;
    final autoRecording = config['auto_segment_recording'] == true;
    
    if (autoRecording && config['segment_interval_seconds'] != null) {
      return 'Auto: every ${config['segment_interval_seconds']}s, ${config['segment_duration_seconds'] ?? 30}s segments';
    } else {
      return 'Manual recording, ${config['segment_duration_seconds'] ?? 30}s duration';
    }
  }

  /// Check if template matches search query
  bool matchesSearch(String query) {
    final lowerQuery = query.toLowerCase();
    return templateName.toLowerCase().contains(lowerQuery) ||
           (description?.toLowerCase().contains(lowerQuery) ?? false);
  }
}
```

#### **Profile Template Management UI**

```dart
// ppl-meta-frontend/lib/presentation/pages/profile_templates_page.dart

class ProfileTemplatesPage extends StatefulWidget {
  const ProfileTemplatesPage({Key? key}) : super(key: key);

  @override
  _ProfileTemplatesPageState createState() => _ProfileTemplatesPageState();
}

class _ProfileTemplatesPageState extends State<ProfileTemplatesPage> {
  final RecordingProfileTemplateService _templateService = RecordingProfileTemplateService(
    baseUrl: Config.apiBaseUrl,
    authService: AuthService(),
  );
  
  List<ProfileTemplate> _templates = [];
  List<ProfileTemplate> _filteredTemplates = [];
  bool _isLoading = true;
  bool _showFavoritesOnly = false;
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  
  @override
  void initState() {
    super.initState();
    _loadTemplates();
  }
  
  Future<void> _loadTemplates() async {
    setState(() => _isLoading = true);
    
    try {
      final templates = await _templateService.getUserProfileTemplates(
        favoritesOnly: _showFavoritesOnly,
        searchQuery: _searchQuery.isEmpty ? null : _searchQuery,
      );
      
      setState(() {
        _templates = templates ?? [];
        _filteredTemplates = _templates;
        _filterTemplates();
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load profile templates: $e'))
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
  
  void _filterTemplates() {
    setState(() {
      _filteredTemplates = _templates.where((template) {
        final matchesSearch = _searchQuery.isEmpty || template.matchesSearch(_searchQuery);
        final matchesFavorite = !_showFavoritesOnly || template.isFavorite;
        return matchesSearch && matchesFavorite;
      }).toList();
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile Templates'),
        actions: [
          IconButton(
            icon: const Icon(Icons.file_upload),
            onPressed: _showImportDialog,
            tooltip: 'Import Template',
          ),
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showSaveTemplateDialog,
            tooltip: 'Save New Template',
          ),
        ],
      ),
      body: Column(
        children: [
          // Search and Filter Bar
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: const InputDecoration(
                      labelText: 'Search templates...',
                      prefixIcon: Icon(Icons.search),
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (value) {
                      _searchQuery = value;
                      _filterTemplates();
                    },
                  ),
                ),
                const SizedBox(width: 16),
                FilterChip(
                  label: const Text('Favorites'),
                  selected: _showFavoritesOnly,
                  onSelected: (selected) {
                    setState(() => _showFavoritesOnly = selected);
                    _filterTemplates();
                  },
                ),
              ],
            ),
          ),
          
          // Templates List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _filteredTemplates.isEmpty
                    ? _buildEmptyState()
                    : ListView.builder(
                        itemCount: _filteredTemplates.length,
                        itemBuilder: (context, index) {
                          final template = _filteredTemplates[index];
                          return ProfileTemplateCard(
                            template: template,
                            onTap: () => _useTemplate(template),
                            onEdit: () => _editTemplate(template),
                            onExport: () => _exportTemplate(template),
                            onDelete: () => _deleteTemplate(template),
                            onToggleFavorite: () => _toggleFavorite(template),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.bookmark_border,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            _searchQuery.isNotEmpty
                ? 'No templates match your search'
                : 'No profile templates saved yet',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _searchQuery.isNotEmpty
                ? 'Try a different search term'
                : 'Save your first recording profile as a template',
            style: TextStyle(
              color: Colors.grey[500],
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _showSaveTemplateDialog,
            icon: const Icon(Icons.add),
            label: const Text('Save Template'),
          ),
        ],
      ),
    );
  }
  
  Future<void> _useTemplate(ProfileTemplate template) async {
    // Navigate to profile creation page with template data
    final profileName = await _showProfileNameDialog(
      'Create Profile from Template',
      'Enter name for new recording profile:',
      defaultName: '${template.templateName} Profile',
    );
    
    if (profileName != null && profileName.isNotEmpty) {
      try {
        final profile = await _templateService.createProfileFromTemplate(
          template.uuid,
          profileName,
        );
        
        if (profile != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Created profile "$profileName" from template'))
          );
          // Navigate to profile management or camera assignment
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to create profile: $e'))
        );
      }
    }
  }
  
  Future<void> _editTemplate(ProfileTemplate template) async {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ProfileTemplateEditPage(
          template: template,
          onSaved: () {
            _loadTemplates();
            Navigator.pop(context);
          },
        ),
      ),
    );
  }
  
  Future<void> _exportTemplate(ProfileTemplate template) async {
    try {
      final exportData = await _templateService.exportProfileTemplate(template.uuid);
      
      if (exportData != null) {
        final jsonString = json.encode(exportData);
        
        // Show export dialog with copy/save options
        await showDialog(
          context: context,
          builder: (context) => ExportTemplateDialog(
            templateName: template.templateName,
            exportData: jsonString,
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to export template: $e'))
      );
    }
  }
  
  Future<void> _deleteTemplate(ProfileTemplate template) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Template'),
        content: Text('Are you sure you want to delete "${template.templateName}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    
    if (confirmed == true) {
      try {
        final success = await _templateService.deleteProfileTemplate(template.uuid);
        
        if (success) {
          _loadTemplates();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Template deleted successfully'))
          );
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete template: $e'))
        );
      }
    }
  }
  
  Future<void> _toggleFavorite(ProfileTemplate template) async {
    try {
      final success = await _templateService.toggleTemplateFavorite(
        template.uuid,
        !template.isFavorite,
      );
      
      if (success) {
        _loadTemplates();
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update favorite status: $e'))
      );
    }
  }
  
  void _showSaveTemplateDialog() {
    // Navigate to template creation page
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => SaveTemplateFromProfilePage(
          onSaved: () {
            _loadTemplates();
            Navigator.pop(context);
          },
        ),
      ),
    );
  }
  
  void _showImportDialog() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ImportTemplatePage(
          onImported: () {
            _loadTemplates();
            Navigator.pop(context);
          },
        ),
      ),
    );
  }
  
  Future<String?> _showProfileNameDialog(String title, String hint, {String? defaultName}) async {
    String? result;
    await showDialog(
      context: context,
      builder: (context) {
        final controller = TextEditingController(text: defaultName);
        return AlertDialog(
          title: Text(title),
          content: TextField(
            controller: controller,
            decoration: InputDecoration(hintText: hint),
            autofocus: true,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                result = controller.text;
                Navigator.pop(context);
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    );
    return result;
  }
}

class ProfileTemplateCard extends StatelessWidget {
  final ProfileTemplate template;
  final VoidCallback? onTap;
  final VoidCallback? onEdit;
  final VoidCallback? onExport;
  final VoidCallback? onDelete;
  final VoidCallback? onToggleFavorite;
  
  const ProfileTemplateCard({
    Key? key,
    required this.template,
    this.onTap,
    this.onEdit,
    this.onExport,
    this.onDelete,
    this.onToggleFavorite,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Template Icon and Favorite Star
              Stack(
                children: [
                  CircleAvatar(
                    backgroundColor: Colors.blue,
                    child: Icon(
                      template.importedFrom != null ? Icons.file_download : Icons.bookmark,
                      color: Colors.white,
                    ),
                  ),
                  if (template.isFavorite)
                    Positioned(
                      top: -2,
                      right: -2,
                      child: Container(
                        padding: const EdgeInsets.all(2),
                        decoration: const BoxDecoration(
                          color: Colors.amber,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.star,
                          size: 12,
                          color: Colors.white,
                        ),
                      ),
                    ),
                ],
              ),
              
              const SizedBox(width: 16),
              
              // Template Details
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      template.templateName,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    if (template.description?.isNotEmpty == true) ...[
                      const SizedBox(height: 4),
                      Text(
                        template.description!,
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 14,
                        ),
                      ),
                    ],
                    const SizedBox(height: 4),
                    Text(
                      template.getConfigSummary(),
                      style: const TextStyle(
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.schedule, size: 12, color: Colors.grey[500]),
                        const SizedBox(width: 4),
                        Text(
                          'Used ${template.usageCount} times',
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey[500],
                          ),
                        ),
                        if (template.lastUsed != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            'Last: ${_formatDate(template.lastUsed!)}',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey[500],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              
              // Actions Menu
              PopupMenuButton(
                itemBuilder: (context) => [
                  PopupMenuItem(
                    value: 'favorite',
                    child: Row(
                      children: [
                        Icon(template.isFavorite ? Icons.star_border : Icons.star),
                        const SizedBox(width: 8),
                        Text(template.isFavorite ? 'Remove from Favorites' : 'Add to Favorites'),
                      ],
                    ),
                  ),
                  if (onEdit != null)
                    const PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(Icons.edit),
                          SizedBox(width: 8),
                          Text('Edit Template'),
                        ],
                      ),
                    ),
                  if (onExport != null)
                    const PopupMenuItem(
                      value: 'export',
                      child: Row(
                        children: [
                          Icon(Icons.file_download),
                          SizedBox(width: 8),
                          Text('Export'),
                        ],
                      ),
                    ),
                  if (onDelete != null)
                    const PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete, color: Colors.red),
                          SizedBox(width: 8),
                          Text('Delete', style: TextStyle(color: Colors.red)),
                        ],
                      ),
                    ),
                ],
                onSelected: (value) {
                  switch (value) {
                    case 'favorite':
                      onToggleFavorite?.call();
                      break;
                    case 'edit':
                      onEdit?.call();
                      break;
                    case 'export':
                      onExport?.call();
                      break;
                    case 'delete':
                      onDelete?.call();
                      break;
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);
    
    if (difference.inDays == 0) {
      return 'Today';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else {
      return '${date.day}/${date.month}/${date.year}';
    }
  }
}
```

## 5. Implementation Summary

### 5.1 Complete Architecture Flow with Custom Profile Templates

1. **Profile Templates** → Users save custom recording configurations as reusable templates
2. **Profile Management** → Create, edit, clone, and share recording profiles from templates
3. **Camera Assignment** → Assign recording profiles to cameras for automated configuration
4. **Recording Scheduler** → Profile settings drive automatic recording intervals and durations
5. **Camera Service** → Records video segments according to profile specifications
6. **Media Service** → Stores videos with automatic face detection triggers based on profile settings
7. **Orchestrator** → Tracks sessions with profile context and workflow management
8. **Frontend Management** → Complete UI for template and profile management with import/export

### 5.2 Database Schema Enhancements

- **camera_recording_profiles table**: Complete profile entity with all recording parameters
- **user_profile_templates table**: User's custom profile configuration templates with usage tracking
- **cameras table**: Foreign key reference to assigned recording profile
- **orchestrator workflows table**: Enhanced session tracking with profile context
- **System default profiles**: Pre-populated profiles for common use cases

### 5.3 Enhanced Service Components

- **Recording Profile Service**: CRUD operations for profile management with system defaults
- **Profile Storage Service**: Custom template storage, retrieval, and sharing functionality
- **Profile Template API**: Complete endpoints for template management and import/export
- **Profile-Based Scheduler**: Automatic recording driven by profile configurations
- **Camera Profile Assignment**: API endpoints for assigning profiles to cameras
- **Frontend Profile Management**: Complete UI for profiles, templates, and camera configuration

### 5.4 Default Values and Validation

#### **Parameter Logic and Design Rationale**

The default values for camera segment recording parameters are carefully chosen based on performance considerations, storage efficiency, and practical use cases:

##### **Segment Interval (`segment_interval_seconds`)**
- **Default**: `null` (disabled)
- **Minimum**: 5 seconds
- **Maximum**: 3600 seconds (1 hour)

**Logic Behind Defaults:**
- **`null` by default**: Automatic segment recording is disabled by default to prevent unexpected storage consumption and system load. Users must explicitly enable this feature.
- **5-second minimum**: Below 5 seconds creates excessive overhead with file I/O operations, video encoding startup/shutdown cycles, and database writes. This minimum ensures each recording has meaningful content and reduces system strain.
- **3600-second maximum**: One-hour intervals provide a reasonable upper bound for automatic recording while preventing extremely long gaps that could miss important events. Beyond this, users should consider manual recording or motion-triggered recording instead.

##### **Segment Duration (`segment_duration`)**
- **Default**: 30 seconds
- **Minimum**: 5 seconds  
- **Maximum**: 300 seconds (5 minutes)

**Logic Behind Defaults:**
- **30-second default**: This duration captures enough context for most events (person entering/leaving, package delivery, brief interactions) while keeping file sizes manageable. It's long enough to be useful but short enough for quick review.
- **5-second minimum**: Very short segments are inefficient due to video encoding overhead and provide insufficient context. This minimum ensures practical utility.
- **300-second maximum**: 5-minute segments balance storage efficiency with usability. Longer segments become unwieldy for review and analysis, and increase the risk of losing entire recordings if encoding fails.

##### **Technical Constraints and Performance Considerations**

1. **Storage Efficiency**: 
   - 30-second segments at medium quality ≈ 5-10MB per file
   - Predictable storage consumption for capacity planning
   - Efficient for face detection processing (not too short, not overwhelming)

2. **System Stability**:
   - Conservative defaults prevent system overload from aggressive recording schedules
   - Minimum intervals prevent rapid file creation that could exhaust disk I/O
   - Maximum durations prevent memory issues during encoding

3. **User Experience**:
   - 30-second segments are quick to review and share
   - Reasonable defaults work for most security and monitoring scenarios
   - Easy to adjust based on specific needs without risking system stability

4. **Face Detection Integration**:
   - 30-second segments provide optimal batch size for face detection algorithms
   - Not too short (inefficient processing) or too long (memory intensive)
   - Allows for real-time processing without overwhelming the vision service

##### **Validation Rules Implementation**

```python
# Parameter validation logic
def validate_segment_config(interval_seconds: Optional[int], duration_seconds: int) -> Dict[str, str]:
    errors = {}
    
    if interval_seconds is not None:
        if interval_seconds < 5:
            errors['interval'] = "Minimum interval is 5 seconds to prevent system overload"
        elif interval_seconds > 3600:
            errors['interval'] = "Maximum interval is 1 hour for practical recording schedules"
    
    if duration_seconds < 5:
        errors['duration'] = "Minimum duration is 5 seconds for meaningful content"
    elif duration_seconds > 300:
        errors['duration'] = "Maximum duration is 5 minutes for optimal file management"
        
    return errors
```

##### **Recommended Usage Patterns**

- **Security Monitoring**: interval=300s (5min), duration=60s → Captures key events without excessive storage
- **Activity Logging**: interval=30s, duration=15s → Frequent short captures for detailed timeline
- **Event Detection**: interval=60s, duration=30s → Balanced approach for general surveillance
- **High-Traffic Areas**: interval=15s, duration=10s → More frequent capture for busy locations

These defaults ensure the system remains stable, storage-efficient, and user-friendly while providing flexibility for various use cases through the configurable parameters.

## 6. Custom Profile Template Benefits

### 6.1 User-Centric Features

- **Template Persistence**: Save favorite recording configurations for reuse across multiple cameras
- **Template Library**: Personal collection of custom templates with search and favorite functionality
- **Usage Analytics**: Track template usage frequency and last used dates for optimization
- **Import/Export**: Share templates between users and backup configurations

### 6.2 Advanced Template Management

- **Template Favorites**: Mark frequently used templates for quick access
- **Template Search**: Find templates by name or description with real-time filtering
- **Template Cloning**: Create variations of existing templates easily
- **Profile Generation**: Convert templates into recording profiles with one click

### 6.3 Collaborative Features

- **Template Sharing**: Export templates as JSON for sharing with other users
- **Import Workflows**: Import shared templates with custom naming
- **Version Control**: Track original authors for imported templates
- **Configuration Validation**: Ensure imported templates meet system requirements

This implementation provides complete camera segment recording functionality with reusable recording profiles, custom user templates, proper session tracking, automatic face detection triggers, and comprehensive profile management through the Flutter frontend, enabling users to store and retrieve their own personalized recording configurations.

---

## 7. Implementation Roadmap

This section outlines the recommended implementation phases for deploying the complete camera segment recording functionality with custom profile templates.

### 7.1 Phase 1: Core Recording Infrastructure (2-3 weeks)

#### **🎯 Objective**: Establish basic camera recording capabilities

#### **Backend Components**
- **Camera Service Recording Endpoints**
  - [ ] Implement `/api/v1/streaming/{device_id}/record/start`
  - [ ] Implement `/api/v1/streaming/{device_id}/record/stop`
  - [ ] Implement `/api/v1/streaming/{device_id}/record/status`
  - [ ] Add recording session management
  - [ ] Implement video file storage and cleanup

- **Media Service Integration**
  - [ ] Enhance video upload endpoints for camera recordings
  - [ ] Implement camera-specific collection management
  - [ ] Add automatic face detection trigger system
  - [ ] Create recording metadata storage

- **Gateway Service Updates**
  - [ ] Add recording endpoint proxying
  - [ ] Implement request routing to camera service
  - [ ] Add authentication and authorization checks

#### **Database Changes**
- [ ] Add recording session tracking tables
- [ ] Implement camera recording metadata storage
- [ ] Create recording file path management
- [ ] Add recording status and duration tracking

#### **Testing & Validation**
- [ ] Unit tests for recording endpoints
- [ ] Integration tests for video upload flow
- [ ] End-to-end recording workflow tests
- [ ] Performance testing with concurrent recordings

#### **Success Criteria**
- ✅ Manual camera recording start/stop functionality
- ✅ Video files stored and accessible via Media service
- ✅ Recording status tracking and session management
- ✅ Basic face detection trigger on recording completion

---

### 7.2 Phase 2: Recording Profiles Foundation (2-3 weeks) ✅ COMPLETED

#### **🎯 Objective**: Implement reusable recording profile system

#### **Backend Components**
- **Recording Profile Model & Database**
  - [x] Create `CameraRecordingProfile` model with all configuration parameters
  - [x] Implement database migration for recording profiles table
  - [x] Add system default profile seeding
  - [x] Create profile validation and constraint logic

- **Recording Profile API Endpoints**
  - [x] Implement CRUD operations for recording profiles
  - [x] Add profile cloning functionality
  - [x] Implement profile assignment to cameras
  - [x] Create profile validation and permissions system

- **Camera-Profile Integration**
  - [x] Update `Camera` model with profile relationship
  - [x] Implement `effective_recording_config` property
  - [x] Add profile-based recording scheduler
  - [x] Create automatic recording trigger system

#### **System Default Profiles**
- [x] **Manual Recording Only**: Basic on-demand recording
- [x] **Security Monitor**: 60s segments every 5 minutes
- [x] **Activity Logger**: 15s segments every 30s
- [x] **Event Detection**: 30s segments every minute
- [x] **High Traffic**: 10s segments every 15s

#### **Testing & Validation**
- [x] Profile CRUD operation tests
- [x] Profile assignment and validation tests
- [x] System default profile verification
- [x] Profile-based recording schedule tests

#### **Success Criteria**
- ✅ Complete recording profile management system
- ✅ System default profiles available and functional
- ✅ Camera-profile assignment working
- ✅ Profile-driven automatic recording schedules

#### **Implementation Summary**

**Files Created/Modified:**
- `ppl-meta-cameras/src/models/recording_profile.py` - Core recording profile model
- `ppl-meta-cameras/migrations/create_recording_profiles.sql` - Database schema
- `ppl-meta-cameras/src/services/recording_profile_service.py` - Business logic service
- `ppl-meta-cameras/src/api/v1/endpoints/recording_profiles.py` - REST API endpoints
- `ppl-meta-cameras/src/models/camera.py` - Updated with profile relationship
- `ppl-meta-cameras/src/services/recording_scheduler.py` - Automatic recording scheduler
- `ppl-meta-cameras/tests/test_recording_profiles.py` - Comprehensive test suite

**Key Features Implemented:**
1. **Complete Profile Model** with validation, cloning, and usage tracking
2. **5 System Default Profiles** for common use cases
3. **Full CRUD API** with permissions and access control
4. **Camera-Profile Assignment** with automatic recording triggers
5. **Recording Scheduler Service** for profile-based automation
6. **Database Migration** with proper indexes and constraints
7. **Comprehensive Testing** with unit and integration test structure

---

### 7.3 Phase 3: Custom Profile Templates ✅ **COMPLETED** (3-4 weeks)

#### **🎯 Objective**: Enable users to create and manage custom recording templates

#### **Backend Components**
- **Profile Template Storage Service**
  - ✅ Create `UserProfileTemplate` model and database table
  - ✅ Implement `ProfileStorageService` with CRUD operations
  - ✅ Add template usage tracking and analytics
  - ✅ Create template favorite and search functionality

- **Profile Template API Endpoints**
  - ✅ Implement template save/load endpoints
  - ✅ Add template CRUD operations with user permissions
  - ✅ Create template-to-profile conversion functionality
  - ✅ Implement template import/export system

- **Template Management Features**
  - ✅ Template search and filtering functionality
  - ✅ Usage analytics and statistics tracking
  - ✅ Template favorite marking system
  - ✅ Template sharing and collaboration features

#### **Advanced Features**
- ✅ **Template Validation**: Ensure configuration compatibility
- ✅ **Batch Operations**: Bulk template management
- ✅ **Template Categories**: Organize templates by use case
- ✅ **Template Versioning**: Track template evolution

#### **Testing & Validation**
- ✅ Template storage and retrieval tests
- ✅ Template import/export functionality tests
- ✅ User permission and security tests
- ✅ Template usage analytics validation

#### **✅ Implementation Summary**

**Phase 3 has been successfully implemented with the following components:**

1. **UserProfileTemplate Model** (`ppl-meta-cameras/src/models/profile_template.py`):
   - Complete template model with 25+ configuration parameters
   - Template validation, cloning, and metadata management
   - Support for categories, tags, and version tracking
   - Usage analytics and favorite count tracking

2. **Database Schema** (`ppl-meta-cameras/migrations/create_profile_templates.sql`):
   - `user_profile_templates` table with comprehensive configuration
   - `user_template_favorites` table for user favorites
   - `template_usage_analytics` table for detailed analytics
   - 5 featured system templates pre-loaded
   - Complete indexes and constraints for performance

3. **ProfileStorageService** (`ppl-meta-cameras/src/services/profile_storage_service.py`):
   - Full CRUD operations with user permission checks
   - Advanced search with filters and pagination
   - Template cloning and favorite management
   - Template-to-profile conversion functionality
   - Usage analytics and popularity tracking

4. **Template Import/Export Service** (`ppl-meta-cameras/src/services/template_import_export_service.py`):
   - JSON-based import/export with version compatibility
   - Conflict resolution strategies (skip, rename, overwrite)
   - Import preview functionality
   - Batch operations support
   - Data validation and error handling

5. **REST API Endpoints** (`ppl-meta-cameras/src/api/v1/endpoints/profile_templates.py`):
   - 15+ comprehensive endpoints for template management
   - Template CRUD operations with validation
   - Search, filtering, and pagination support
   - Import/export endpoints with preview functionality
   - Favorite management and analytics endpoints

6. **Comprehensive Testing** (`ppl-meta-cameras/tests/test_profile_templates.py`):
   - Unit tests for models, services, and functionality
   - Import/export testing with validation
   - Template lifecycle and analytics testing
   - Mock-based testing for database operations

**Key Features Delivered:**
- ✅ User template storage and sharing capabilities
- ✅ Template library with search, favorites, and analytics
- ✅ Template import/export for configuration sharing
- ✅ Template-to-profile conversion working seamlessly
- ✅ Advanced search and filtering functionality
- ✅ Usage analytics and popularity tracking
- ✅ Template validation and conflict resolution
- ✅ 5 pre-loaded system templates for common use cases

**Ready for Phase 4**: Orchestrator Integration for comprehensive session tracking and workflow management.

#### **Success Criteria**
- ✅ Users can save custom recording configurations as templates
- ✅ Template library with search, favorites, and analytics
- ✅ Template import/export for sharing configurations
- ✅ Template-to-profile conversion working seamlessly

---

### 7.4 Phase 4: Orchestrator Integration (2-3 weeks)

#### **🎯 Objective**: Add comprehensive session tracking and workflow management

#### **📋 Phase 4 Implementation Notes & Current State Analysis**

**Current Implementation Status:**
- ✅ **Orchestrator Recording Endpoints**: Mostly implemented in `camera_endpoints.py` and `camera_event_publisher.py`
- ⚠️ **Session Database Storage**: Missing - sessions not persisted to database (scheduled for future)
- ✅ **Face Detection Workflow Links**: Already traceable via existing data objects (camera source linkage works)
- ⚠️ **Face Detection Triggers**: Implemented but needs consolidation - currently two methods, need to standardize on `enhanced-v2`
- ⚠️ **Session Tracking**: In-memory only, needs database persistence for reliability
- ✅ **Workflow Integration**: Basic workflow execution already exists

**Key Findings from Analysis:**
1. **Camera Event Publisher** (`ppl-meta-orchestrator/src/camera_event_publisher.py`): Handles recording completion webhooks
2. **Camera Endpoints** (`ppl-meta-orchestrator/src/camera_endpoints.py`): Event handling with workflow triggers
3. **Face Detection**: Two methods exist, need to consolidate to `/api/v1/media/{media_uuid}/faces/enhanced-v2`
4. **Database Schema**: Recording session tables defined in docs but not implemented in code

**Implementation Priorities:**
1. **Database Session Storage**: Implement recording session persistence (highest priority)
2. **Face Detection Consolidation**: Standardize on `enhanced-v2` method only
3. **Session UUID Integration**: Add UUID-based session tracking throughout
4. **Gateway Routing**: Ensure orchestrator endpoints accessible via gateway
5. **Error Handling**: Enhance error tracking and recovery for recording sessions

#### **Backend Components**
- **Orchestrator Recording Endpoints**
  - ✅ Create camera recording endpoints with session tracking (mostly done)
  - [ ] Implement workflow execution for recording sessions (enhance existing)
  - [ ] Add recording completion workflow triggers (enhance existing)
  - ⚠️ Create session-based face detection workflows (consolidate to enhanced-v2)

- **Session Tracking System**
  - [ ] **HIGH PRIORITY**: Implement UUID-based session management with database persistence
  - [ ] Add workflow metadata and traceability to database
  - [ ] Create session status and progress tracking in database
  - [ ] Implement session-based event publishing (enhance existing)

- **Enhanced Workflow Integration**
  - ✅ Link recording sessions to face detection workflows (already traceable)
  - [ ] Add profile context to workflow executions
  - ⚠️ **CONSOLIDATION NEEDED**: Implement automatic face detection triggers (standardize on enhanced-v2)
  - [ ] Create workflow completion notifications (enhance existing)

#### **Gateway Integration**
- [ ] Add orchestrator recording endpoint routing (verify current routes)
- [ ] Implement session-aware request proxying
- [ ] Create unified recording API through gateway
- [ ] Add session tracking for frontend integration

#### **Testing & Validation**
- [ ] Session tracking and workflow execution tests
- [ ] Orchestrator-camera service integration tests
- [ ] Face detection workflow trigger tests (enhanced-v2 only)
- [ ] End-to-end session lifecycle tests

#### **Success Criteria**
- ✅ Complete session tracking for all recordings (database persistence required)
- ✅ Workflow-based face detection automation (consolidate to enhanced-v2)
- ✅ Orchestrator-driven recording management (enhance existing)
- ✅ Session context preserved throughout recording lifecycle (database required)

---

### 7.5 Phase 5: Flutter Frontend Integration ✅ **COMPILATION COMPLETE** (3-4 weeks)

#### **🎯 Objective**: Complete user interface for recording profile management

#### **✅ Implementation Status** *(Updated October 14, 2025)*
- **Flutter Compilation**: ✅ Successfully compiles without errors
- **Navigation Integration**: ✅ Enhanced camera management accessible via home screen
- **Component Implementation**: ✅ EnhancedCameraCard, EnhancedMultiCameraPage, RecordingSessionWidget complete
- **Router Configuration**: ✅ `/cameras-enhanced` route properly configured
- **Model Compatibility**: ✅ Core camera model integration resolved
- **Navigation Pattern**: ✅ Consistent with app-wide navigation standards

#### **🔬 Testing Status**
- **Compilation Testing**: ✅ Complete - All Flutter compilation errors resolved
- **Functional Testing**: ⏳ **Scheduled for future implementation** - Will be completed in later development cycle
- **Integration Testing**: ⏳ **Scheduled for future implementation** - Backend-frontend integration testing pending
- **User Experience Testing**: ⏳ **Scheduled for future implementation** - UI/UX validation and refinement pending

#### **Core Frontend Services**
- **Recording Profile Service**
  - [ ] Implement `RecordingProfileService` with all CRUD operations
  - [ ] Add profile assignment functionality for cameras
  - [ ] Create profile validation and error handling
  - [ ] Implement real-time profile status updates

- **Profile Template Service**
  - [ ] Create `RecordingProfileTemplateService` for custom templates
  - [ ] Implement template CRUD operations and search
  - [ ] Add template import/export functionality
  - [ ] Create template usage analytics integration

#### **User Interface Components**
- **Recording Profile Management**
  - [ ] Create `RecordingProfilesPage` with profile listing
  - [ ] Implement `RecordingProfileEditPage` for profile creation/editing
  - [ ] Add profile cloning and deletion functionality
  - [ ] Create camera profile assignment interface

- **Profile Template Management**
  - [ ] Implement `ProfileTemplatesPage` with template library
  - [ ] Create template search, filtering, and favorites
  - [ ] Add template import/export dialogs
  - [ ] Implement template-to-profile conversion UI

- **Camera Integration UI**
  - [ ] Create `CameraProfileSelector` for profile assignment
  - [ ] Add profile configuration display in camera settings
  - [ ] Implement real-time recording status with profile context
  - [ ] Create profile-based recording controls

#### **Advanced UI Features**
- [ ] **Profile Wizard**: Guided profile creation for new users
- [ ] **Template Gallery**: Curated templates with previews
- [ ] **Usage Dashboard**: Analytics and usage insights
- [ ] **Bulk Operations**: Multi-camera profile assignment

#### **Testing & Validation**
- [ ] Widget tests for all UI components
- [ ] Integration tests with backend services
- [ ] User experience testing and feedback
- [ ] Performance testing with large template libraries

#### **Success Criteria**
- ✅ Complete profile management UI accessible to users
- ✅ Template library with search, favorites, and sharing
- ✅ Intuitive camera profile assignment interface
- ✅ Real-time recording status with profile context

---

### 7.6 Phase 6: Advanced Features & Optimization ⏳ **FUTURE IMPLEMENTATION** (2-3 weeks)

#### **📋 Implementation Note** *(Updated October 14, 2025)*
**Testing and implementation of Phase 6 and all subsequent phases (7.6, 7.7) will be completed in a future development cycle after Phase 5 functional testing is complete.**

#### **🎯 Objective**: Polish the system and add advanced capabilities

#### **Performance Optimization**
- [ ] **Database Optimization**
  - Query optimization for large template libraries
  - Indexing strategy for fast template searches
  - Connection pooling for concurrent recordings
  - Caching strategy for frequently used profiles

- [ ] **Recording Performance**
  - Concurrent recording limit management
  - Resource allocation optimization
  - Storage cleanup and maintenance
  - Recording queue management

#### **Advanced Features**
- [ ] **Template Analytics Dashboard**
  - Template usage statistics and trends
  - Popular template recommendations
  - User behavior insights
  - Performance metrics visualization

- [ ] **Collaboration Enhancements**
  - Template sharing with permissions
  - Community template marketplace
  - Template rating and review system
  - Collaborative profile development

- [ ] **System Administration**
  - Admin panel for system profile management
  - Bulk template operations for administrators
  - System-wide recording statistics
  - Resource usage monitoring and alerts

#### **Security & Compliance**
- [ ] Template access control and permissions
- [ ] Recording data encryption and security
- [ ] Audit logging for all profile operations
- [ ] Compliance reporting and data retention

#### **Testing & Validation**
- [ ] Performance benchmarking and optimization
- [ ] Security penetration testing
- [ ] Load testing with concurrent users
- [ ] End-to-end system integration testing

#### **Success Criteria**
- ✅ System performs efficiently under high load
- ✅ Advanced analytics provide valuable insights
- ✅ Security and compliance requirements met
- ✅ System ready for production deployment

---

### 7.7 Deployment & Monitoring ⏳ **FUTURE IMPLEMENTATION** (1-2 weeks)

#### **📋 Implementation Note** *(Updated October 14, 2025)*
**Deployment and monitoring implementation will be completed in a future development cycle after all feature development and testing phases are complete.**

#### **🎯 Objective**: Production deployment with comprehensive monitoring

#### **Production Deployment**
- [ ] **Environment Setup**
  - Production database migration and seeding
  - Service configuration and deployment
  - Load balancer and scaling configuration
  - SSL/TLS certificate setup

- [ ] **Monitoring & Alerting**
  - Application performance monitoring (APM)
  - Database performance monitoring
  - Recording service health checks
  - Template service availability monitoring

#### **Documentation & Training**
- [ ] **User Documentation**
  - Complete user guide for recording profiles
  - Template management tutorials
  - Best practices and troubleshooting
  - Video tutorials for key workflows

- [ ] **Technical Documentation**
  - API documentation with examples
  - Database schema documentation
  - Deployment and configuration guides
  - Monitoring and maintenance procedures

#### **Success Criteria**
- ✅ System deployed to production successfully
- ✅ Monitoring and alerting fully operational
- ✅ Complete documentation available
- ✅ Users trained and onboarded successfully

---

## 8. Implementation Timeline Summary

| Phase | Duration | Focus | Key Deliverables |
|-------|----------|--------|------------------|
| **Phase 1** | 2-3 weeks | Core Recording | Basic recording endpoints, video storage |
| **Phase 2** | 2-3 weeks | Recording Profiles | Profile system, system defaults |
| **Phase 3** | 3-4 weeks | Custom Templates | User templates, import/export |
| **Phase 4** | 2-3 weeks | Orchestrator Integration | Session tracking, workflows |
| **Phase 5** | 3-4 weeks | Flutter Frontend | Complete UI implementation |
| **Phase 6** | 2-3 weeks | Advanced Features | Optimization, analytics |
| **Phase 7** | 1-2 weeks | Deployment | Production deployment, monitoring |

**Total Estimated Timeline: 15-22 weeks (3.5-5.5 months)**

## 9. Risk Mitigation & Considerations

### 9.1 Technical Risks
- **Performance Impact**: Implement recording limits and resource monitoring
- **Storage Growth**: Plan for automated cleanup and retention policies  
- **Concurrent Access**: Design for thread-safe template operations
- **Database Scalability**: Plan for horizontal scaling of template storage

### 9.2 User Experience Risks
- **Complexity Overload**: Provide guided onboarding and default templates
- **Template Management**: Implement search and organization features early
- **Migration Path**: Ensure smooth transition from existing configurations
- **Performance Expectations**: Set clear expectations for recording capabilities

### 9.3 Success Metrics
- **User Adoption**: Template creation and usage rates
- **System Performance**: Recording success rates and response times
- **User Satisfaction**: Feedback scores and support ticket volume
- **Technical Metrics**: API response times and system reliability

This roadmap provides a structured approach to implementing the complete camera segment recording system with custom profile templates, ensuring each phase builds upon the previous foundation while maintaining system stability and user experience throughout the development process.

---

## 10. Future Development: Database Infrastructure Requirements

*Added October 14, 2025 - Post Phase 1 Implementation Analysis*

As we progress with the recording infrastructure implementation, the following database changes represent critical requirements for completing Phase 1 and enabling future phases. This section provides detailed specifications for implementing the database foundation that will support the entire recording system.

### 10.1 Database Changes Overview

The Phase 1 database implementation requires four core enhancements to support comprehensive recording session management:

#### **10.1.1 Recording Session Tracking Tables**

**Purpose**: Track every recording session with unique identifiers and metadata

**Primary Implementation**:
```sql
-- Core recording sessions table
CREATE TABLE recording_sessions (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) UNIQUE NOT NULL,
    camera_id INTEGER REFERENCES cameras(id),
    user_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'completed', 'failed', 'stopped')),
    started_at TIMESTAMP DEFAULT NOW(),
    stopped_at TIMESTAMP NULL,
    recording_quality VARCHAR(20) DEFAULT 'high' CHECK (recording_quality IN ('low', 'medium', 'high')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_recording_sessions_uuid (session_uuid),
    INDEX idx_recording_sessions_camera (camera_id),
    INDEX idx_recording_sessions_user (user_id),
    INDEX idx_recording_sessions_status (status),
    INDEX idx_recording_sessions_started (started_at)
);
```

**Why This is Critical**:
- **Prevents Recording Conflicts**: Only one active recording per camera
- **Session History**: Complete audit trail for debugging and analytics
- **User Tracking**: Links recordings to specific users for permissions
- **Status Management**: Real-time tracking of recording lifecycle
- **Performance**: Proper indexing for fast queries on active sessions

**Business Logic Integration**:
- Before starting new recording: `SELECT COUNT(*) FROM recording_sessions WHERE camera_id = ? AND status = 'active'`
- Session cleanup: Automatic status updates when recordings end
- Historical analysis: Query patterns for user behavior and system usage

#### **10.1.2 Camera Recording Metadata Storage**

**Purpose**: Store comprehensive configuration and technical details for each recording

**Implementation**:
```sql
-- Recording configuration and metadata
CREATE TABLE recording_metadata (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    recording_profile_id INTEGER NULL, -- Future: link to recording profiles
    
    -- Configuration parameters
    segment_interval_seconds INTEGER NULL,
    segment_duration_seconds INTEGER DEFAULT 30,
    auto_face_detection_enabled BOOLEAN DEFAULT TRUE,
    video_codec VARCHAR(20) DEFAULT 'h264',
    audio_enabled BOOLEAN DEFAULT FALSE,
    
    -- Technical specifications
    resolution_width INTEGER,
    resolution_height INTEGER,
    fps INTEGER,
    bitrate INTEGER,
    
    -- Processing settings
    face_detection_method VARCHAR(20) DEFAULT 'two_stage',
    quality_preset VARCHAR(20) DEFAULT 'balanced',
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_recording_metadata_session (session_uuid),
    INDEX idx_recording_metadata_profile (recording_profile_id)
);
```

**Why This is Essential**:
- **Reproducible Settings**: Exact recording parameters for debugging
- **Profile Integration**: Foundation for future recording profiles
- **Performance Optimization**: Track which settings work best
- **Compliance**: Detailed audit trail for regulatory requirements
- **Quality Control**: Monitor recording quality vs. storage consumption

**Advanced Features**:
- **Dynamic Configuration**: Settings can be updated mid-recording
- **A/B Testing**: Compare different encoding settings
- **Resource Planning**: Predict storage needs based on configuration

#### **10.1.3 Recording File Path Management**

**Purpose**: Comprehensive tracking of video file storage, organization, and lifecycle

**Implementation**:
```sql
-- File storage and organization
CREATE TABLE recording_files (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    file_uuid VARCHAR(36) UNIQUE NOT NULL,
    
    -- File location and organization
    file_path VARCHAR(500) NOT NULL,
    relative_path VARCHAR(500) NOT NULL, -- Path relative to storage root
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT DEFAULT 0,
    
    -- File type and format
    mime_type VARCHAR(100) DEFAULT 'video/mp4',
    video_codec VARCHAR(20),
    audio_codec VARCHAR(20) NULL,
    duration_seconds REAL DEFAULT 0,
    
    -- Storage backend information
    storage_type VARCHAR(20) DEFAULT 'local' CHECK (storage_type IN ('local', 's3', 'gcs', 'azure')),
    storage_bucket VARCHAR(100) NULL,
    storage_region VARCHAR(50) NULL,
    
    -- File integrity and verification
    checksum_md5 VARCHAR(32) NULL,
    checksum_sha256 VARCHAR(64) NULL,
    file_verified_at TIMESTAMP NULL,
    
    -- Media service integration
    is_uploaded_to_media BOOLEAN DEFAULT FALSE,
    media_collection_id VARCHAR(36) NULL,
    media_upload_attempted_at TIMESTAMP NULL,
    media_upload_completed_at TIMESTAMP NULL,
    
    -- Lifecycle management
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP NULL,
    retention_until TIMESTAMP NULL,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_recording_files_session (session_uuid),
    INDEX idx_recording_files_uuid (file_uuid),
    INDEX idx_recording_files_path (file_path),
    INDEX idx_recording_files_upload_status (is_uploaded_to_media),
    INDEX idx_recording_files_storage_type (storage_type),
    INDEX idx_recording_files_lifecycle (is_archived, is_deleted)
);
```

**Critical Capabilities**:
- **Multi-Storage Support**: Local, AWS S3, Google Cloud, Azure
- **File Integrity**: MD5 and SHA256 verification
- **Lifecycle Management**: Automated archival and deletion
- **Media Service Integration**: Track upload status and collection assignment
- **Compliance**: Retention policies and audit trails

**Operational Benefits**:
- **Storage Optimization**: Move old files to cheaper storage tiers
- **Disaster Recovery**: Checksum verification for data integrity
- **Scalability**: Easy migration between storage backends
- **Cost Management**: Track storage usage per camera/user

#### **10.1.4 Recording Status and Duration Tracking**

**Purpose**: Real-time monitoring and performance tracking for active recordings

**Implementation**:
```sql
-- Real-time recording status and metrics
CREATE TABLE recording_status (
    id SERIAL PRIMARY KEY,
    session_uuid VARCHAR(36) REFERENCES recording_sessions(session_uuid) ON DELETE CASCADE,
    status_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Recording progress
    current_duration_seconds REAL NOT NULL,
    current_file_size_bytes BIGINT DEFAULT 0,
    frames_recorded INTEGER DEFAULT 0,
    expected_final_duration REAL NULL,
    
    -- Performance metrics
    recording_fps REAL NULL, -- Actual recording FPS
    cpu_usage_percent REAL NULL,
    memory_usage_mb INTEGER NULL,
    disk_write_speed_mbps REAL NULL,
    
    -- System health
    disk_space_available_gb REAL NULL,
    temp_directory_size_mb INTEGER NULL,
    
    -- Error tracking
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    last_error TEXT NULL,
    last_warning TEXT NULL,
    
    -- Quality metrics
    video_bitrate_kbps INTEGER NULL,
    audio_bitrate_kbps INTEGER NULL,
    frame_drop_count INTEGER DEFAULT 0,
    encoding_lag_seconds REAL DEFAULT 0,
    
    -- Indexes
    INDEX idx_recording_status_session (session_uuid),
    INDEX idx_recording_status_timestamp (status_timestamp),
    INDEX idx_recording_status_duration (current_duration_seconds)
);

-- Enhanced session tracking (add columns to existing recording_sessions)
ALTER TABLE recording_sessions ADD COLUMN current_duration_seconds REAL DEFAULT 0;
ALTER TABLE recording_sessions ADD COLUMN estimated_file_size_bytes BIGINT DEFAULT 0;
ALTER TABLE recording_sessions ADD COLUMN last_heartbeat TIMESTAMP DEFAULT NOW();
ALTER TABLE recording_sessions ADD COLUMN error_message TEXT NULL;
ALTER TABLE recording_sessions ADD COLUMN frames_recorded INTEGER DEFAULT 0;
ALTER TABLE recording_sessions ADD COLUMN average_fps REAL NULL;
```

**Real-Time Capabilities**:
- **Live Progress Tracking**: Duration, file size, frame count
- **Performance Monitoring**: CPU, memory, disk usage
- **Error Detection**: Immediate notification of recording issues
- **Quality Assurance**: Frame drops, encoding lag, bitrate monitoring
- **Resource Planning**: Disk space monitoring and alerts

### 10.2 Database Schema Relationships

**Entity Relationship Overview**:
```
cameras (existing)
    ↓ (1:many)
recording_sessions ←→ recording_metadata (1:1)
    ↓ (1:many)         ↓ (1:many)
recording_files    recording_status
    ↓ (many:1)
media_collections (existing, via media_collection_id)
```

**Key Relationships**:
- **Camera → Sessions**: One camera can have multiple recording sessions
- **Session → Metadata**: One-to-one relationship for configuration
- **Session → Files**: One-to-many for video segments/files
- **Session → Status**: One-to-many for time-series monitoring
- **Files → Media Collections**: Integration with existing media service

### 10.3 Implementation Priority and Dependencies

#### **Phase 1A: Core Session Tracking (Week 1)**
1. `recording_sessions` table - Foundation for all recording operations
2. Basic session management API integration
3. Session conflict prevention logic

#### **Phase 1B: File Management (Week 2)**
1. `recording_files` table - File storage and organization
2. Storage backend abstraction layer
3. File integrity verification

#### **Phase 1C: Metadata and Monitoring (Week 3)**
1. `recording_metadata` table - Configuration storage
2. `recording_status` table - Real-time monitoring
3. Performance metrics collection

#### **Phase 1D: Integration and Testing (Week 4)**
1. Media service integration endpoints
2. End-to-end recording workflow testing
3. Performance optimization and indexing

### 10.4 Operational Benefits

#### **Immediate Phase 1 Benefits**:
- **Reliability**: No lost recordings, proper session management
- **Debuggability**: Complete audit trail for troubleshooting
- **Performance**: Real-time monitoring and alerting
- **Scalability**: Multi-storage backend support

#### **Future Phase Enablers**:
- **Recording Profiles**: Metadata table ready for profile integration
- **Analytics**: Rich data for usage patterns and optimization
- **Compliance**: Complete audit trail and retention management
- **Multi-tenancy**: User-based recording quotas and permissions

### 10.5 Migration Strategy

#### **Database Migration Plan**:
```sql
-- Migration script template
BEGIN;

-- Create new tables with proper constraints
CREATE TABLE recording_sessions (...);
CREATE TABLE recording_metadata (...);
CREATE TABLE recording_files (...);
CREATE TABLE recording_status (...);

-- Add foreign key constraints
ALTER TABLE recording_metadata ADD CONSTRAINT fk_metadata_session 
    FOREIGN KEY (session_uuid) REFERENCES recording_sessions(session_uuid);

-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_recording_sessions_uuid ON recording_sessions(session_uuid);
-- ... additional indexes

-- Verify schema integrity
SELECT COUNT(*) FROM recording_sessions WHERE session_uuid IS NULL; -- Should be 0

COMMIT;
```

#### **Data Population Strategy**:
- **New Installations**: Tables created empty, populated as recordings start
- **Existing Systems**: Backfill historical data from logs where available
- **Testing**: Synthetic data generation for load testing

### 10.6 Performance Considerations

#### **Query Optimization**:
- **Active Sessions**: Fast lookup by camera_id and status
- **File Retrieval**: Efficient path-based and UUID-based queries
- **Status Monitoring**: Time-series queries with proper indexing
- **Cleanup Operations**: Bulk operations for archival and deletion

#### **Storage Optimization**:
- **Partitioning**: Time-based partitioning for recording_status table
- **Archival**: Automated movement of old records to archive tables
- **Indexing Strategy**: Composite indexes for common query patterns

#### **Scalability Planning**:
- **Read Replicas**: Separate analytics queries from operational queries
- **Horizontal Scaling**: Shard by camera_id or user_id for large installations
- **Caching**: Redis cache for frequently accessed session data

### 10.7 Security and Compliance

#### **Data Protection**:
- **Encryption**: File paths and metadata encryption at rest
- **Access Control**: User-based permissions for recording access
- **Audit Logging**: Complete trail of all database operations
- **Data Retention**: Automated compliance with data retention policies

#### **Privacy Considerations**:
- **User Consent**: Track consent for recording and processing
- **Data Minimization**: Only store necessary metadata
- **Right to Deletion**: Efficient deletion of user's recording data
- **Geographic Compliance**: Storage location tracking for GDPR/regional requirements

This comprehensive database infrastructure forms the foundation for the entire recording system, enabling not just Phase 1 functionality but also providing the scalable, reliable, and secure foundation needed for all future development phases.

---

### 10.8 Performance Testing Strategy for Concurrent Recordings

*Critical Testing Requirements for Post-Stable Platform Implementation*

Once the PPL Meta platform reaches a stable version, comprehensive performance testing with concurrent recordings becomes essential to validate system reliability and scalability. This section outlines the complete testing strategy that must be executed before production deployment.

#### **🎯 Testing Objectives**

The performance testing suite validates that the camera recording system maintains stability, performance, and data integrity when multiple cameras are recording simultaneously under various load conditions, ensuring the system can handle real-world enterprise workloads.

#### **📊 Comprehensive Test Scenarios**

##### **1. Concurrent Recording Load Tests**

**Low Load Validation (2-5 concurrent recordings)**
- Start 2-5 cameras recording simultaneously across different device types
- Validate all recordings complete successfully without data loss
- Measure baseline system resource utilization (CPU, memory, disk I/O)
- Verify recording quality remains consistent across all streams
- Test database performance with multiple concurrent session inserts

**Medium Load Stress Testing (6-15 concurrent recordings)**
- Simulate typical enterprise environment with mixed camera types
- Test varying recording durations (30s, 60s, 120s segments)
- Monitor database performance for session tracking and metadata storage
- Validate face detection triggers work correctly for all concurrent recordings
- Test storage I/O performance with multiple simultaneous file writes

**High Load Capacity Testing (16-50+ concurrent recordings)**
- Stress test maximum system capacity and identify breaking points
- Test system behavior at resource limits with graceful degradation
- Validate proper error handling and user notifications during overload
- Test system recovery mechanisms after resource exhaustion
- Monitor inter-service communication performance under extreme load

##### **2. Resource Contention and Performance Validation**

**Storage I/O Performance Testing**
```bash
# Example automated test command
for i in {1..20}; do
  curl -X POST "http://localhost:8080/api/v1/cameras/camera_$i/record/start" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"duration": 60, "quality": "high"}' &
done
wait

# Monitor disk I/O and file system performance
iostat -x 1 60 > concurrent_recording_io_stats.log
```

**Database Connection Pool Testing**
- Verify `recording_sessions` table handles concurrent INSERT operations without conflicts
- Test for deadlocks during simultaneous session status updates
- Validate proper connection cleanup after recording completion
- Monitor connection pool utilization and query performance
- Test database isolation levels with concurrent metadata updates

**Memory Usage Pattern Analysis**
- Monitor memory consumption scaling with concurrent recording count
- Test for memory leaks during extended recording sessions
- Validate garbage collection efficiency under recording load
- Track memory allocation patterns for video encoding processes
- Test system behavior with memory pressure scenarios

##### **3. Critical Performance Metrics to Measure**

**Response Time Benchmarks**
- **Recording Start Latency**: < 2 seconds for 95% of requests
- **Recording Stop Latency**: < 1 second for session termination
- **Status Query Response**: < 500ms for real-time status updates
- **File Availability Time**: < 5 seconds from recording completion to file access

**System Throughput Metrics**
- **Maximum Concurrent Recordings**: Target minimum 20 simultaneous streams
- **Video Encoding Throughput**: Measure MB/s per recording stream
- **Database Transaction Rate**: Sessions/second for concurrent operations
- **Storage Write Performance**: Aggregate throughput across all recordings

**Resource Utilization Targets**
- **CPU Utilization**: < 80% under normal concurrent load (15 streams)
- **Memory Usage**: < 75% with safety margin for peak loads
- **Disk I/O**: < 70% of available bandwidth for sustainable operation
- **Network Bandwidth**: Monitor inter-service communication overhead

**Quality and Reliability Metrics**
- **Recording Success Rate**: > 99% completion rate under normal conditions
- **Video Quality Consistency**: No degradation across concurrent streams
- **Frame Drop Rate**: < 0.1% dropped frames under load
- **Audio/Video Synchronization**: < 40ms drift tolerance

##### **4. Failure Scenario and Recovery Testing**

**Graceful Degradation Validation**
- Test system behavior when approaching resource limits
- Validate recording queue management and prioritization systems
- Test automatic load balancing between available resources
- Verify proper user notifications when system reaches capacity

**Cascade Failure Prevention**
- Ensure single recording failure doesn't affect other active recordings
- Test session isolation during database or storage failures
- Validate proper cleanup of failed recording resources
- Test recovery mechanisms for partial system failures

**Data Integrity Under Stress**
- Verify no corruption in video files during concurrent operations
- Test database consistency during high concurrent session loads
- Validate proper session state management during failures
- Test file system integrity with rapid concurrent writes

##### **5. Real-World Enterprise Simulation**

**24-Hour Continuous Operation Test**
```python
# Example test scenario configuration
recording_profiles = [
    {"interval": 300, "duration": 60, "cameras": 5},   # Security monitoring
    {"interval": 30, "duration": 15, "cameras": 8},    # Activity logging  
    {"interval": 60, "duration": 30, "cameras": 12},   # Event detection
    {"interval": 15, "duration": 10, "cameras": 3},    # High-traffic areas
]

# Simulate realistic usage patterns
for hour in range(24):
    active_cameras = calculate_active_cameras_for_hour(hour)
    concurrent_recordings = start_concurrent_recordings(
        active_cameras, 
        recording_profiles, 
        business_hours=(9 <= hour <= 17)
    )
    monitor_system_performance(duration_minutes=60)
    validate_recording_integrity()
```

**Peak Usage Burst Testing**
- Simulate sudden activity spikes (events, alerts, manual triggers)
- Test system behavior during business hours vs. off-hours
- Validate performance during scheduled recording profile activations
- Test resource allocation during face detection processing peaks

##### **6. Integration Performance Testing**

**End-to-End Workflow Performance**
- **Complete Pipeline**: Recording start → Video capture → Storage → Face detection → Completion
- **Workflow Duration**: Measure total time from trigger to available processed video
- **Orchestrator Performance**: Test session tracking with multiple active workflows
- **Cross-Service Impact**: Monitor performance impact on other PPL Meta services

**API Gateway and Service Mesh Performance**
- Test API gateway performance with concurrent recording requests
- Monitor request routing latency under load
- Validate load balancing effectiveness across camera service instances
- Test authentication and authorization performance at scale

##### **7. Automated Performance Test Framework**

**Continuous Performance Monitoring**
```python
class ConcurrentRecordingPerformanceTestSuite:
    def test_concurrent_recording_scaling(self):
        """Test performance scaling with increasing concurrent recordings"""
        baseline_metrics = self.measure_single_recording_performance()
        
        for concurrent_count in [2, 5, 10, 15, 20, 30, 50]:
            with self.subTest(concurrent=concurrent_count):
                metrics = self.start_concurrent_recordings(concurrent_count)
                
                # Performance assertions
                self.assertLessEqual(metrics.avg_start_latency, 2.0)
                self.assertGreaterEqual(metrics.success_rate, 0.95)
                self.assertLessEqual(metrics.cpu_utilization, 0.85)
                self.assertLessEqual(metrics.memory_utilization, 0.80)
                
                # Quality assertions
                self.assert_video_quality_maintained(baseline_metrics, metrics)
                self.assert_no_frame_drops_above_threshold(metrics, 0.001)
    
    def test_database_performance_under_load(self):
        """Validate database performance with concurrent session management"""
        concurrent_sessions = 50
        
        start_time = time.time()
        session_ids = self.create_concurrent_sessions(concurrent_sessions)
        creation_time = time.time() - start_time
        
        # Database performance assertions
        self.assertLess(creation_time, 5.0)  # All sessions created within 5s
        self.assert_no_database_deadlocks()
        self.assert_session_data_integrity(session_ids)
    
    def test_storage_performance_scaling(self):
        """Test file storage performance with concurrent recordings"""
        for concurrent_count in [5, 10, 20, 30]:
            storage_metrics = self.measure_storage_performance(concurrent_count)
            
            # Storage performance requirements
            self.assertGreater(storage_metrics.aggregate_throughput, 50)  # MB/s
            self.assertLess(storage_metrics.avg_write_latency, 100)  # ms
            self.assert_no_file_corruption(storage_metrics.file_list)
```

##### **8. Performance Monitoring and Alerting**

**Real-Time Performance Dashboard**
- Live concurrent recording count and success rates
- Resource utilization graphs (CPU, memory, disk, network)
- Recording quality metrics and frame rate monitoring
- Database performance metrics and query response times

**Automated Alerting Thresholds**
- **Critical**: Recording success rate < 95%
- **Warning**: CPU utilization > 75% for > 5 minutes
- **Warning**: Disk I/O > 80% sustained for > 2 minutes
- **Critical**: Database query response time > 1 second
- **Critical**: Recording start latency > 5 seconds

##### **9. Performance Benchmarks and SLAs**

**Production Performance Targets**
- **Concurrent Recording Capacity**: Minimum 20 simultaneous high-quality recordings
- **Recording Start Latency**: 95th percentile < 2 seconds
- **System Resource Utilization**: < 80% CPU and memory under normal load
- **Recording Success Rate**: > 99% completion rate under normal conditions
- **Storage Throughput**: Minimum 50 MB/s aggregate write performance
- **Database Performance**: < 500ms average query response time

**Scalability Requirements**
- **Linear Performance Scaling**: Up to 20 concurrent recordings with < 10% performance degradation
- **Graceful Degradation**: System remains operational beyond capacity with proper user feedback
- **Auto-Recovery**: System automatically recovers within 30 seconds after resource availability
- **Quality Maintenance**: No video quality degradation under normal concurrent load

##### **10. Testing Timeline and Execution Plan**

**Pre-Stable Platform Testing (Current)**
- Basic concurrent recording validation (2-5 streams)
- Database schema performance testing
- Initial resource utilization baseline measurement

**Post-Stable Platform Testing (Phase 1 Implementation)**
- **Week 1**: Concurrent load testing (up to 20 streams)
- **Week 2**: Failure scenario and recovery testing
- **Week 3**: 24-hour continuous operation validation
- **Week 4**: Performance optimization and re-testing

**Production Readiness Validation**
- Final stress testing with production-like data
- Performance regression testing after any system changes
- Continuous monitoring setup and alert validation
- User acceptance testing with realistic concurrent usage

This comprehensive performance testing strategy ensures the camera recording system can handle enterprise-scale concurrent recording loads while maintaining high quality, reliability, and user experience. The testing must be executed systematically after platform stabilization to validate production readiness and identify any performance bottlenecks before deployment.
