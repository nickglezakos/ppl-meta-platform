# Mobile Camera Connection & Management Enhancement Proposal

**Date**: 2026-02-11  
**Status**: Draft  
**Target**: PPL Meta Mobile Camera (Flutter App)

---

## Executive Summary

This proposal outlines enhancements to the PPL Meta Mobile Camera to apply the same robust connection and management logic successfully implemented in the Signage Simple Player and USB/RTSP cameras. The key improvements include:

1. **Discovery Service Integration** - Auto-registration with heartbeat mechanism
2. **Unified Naming Logic** - Consistent auto-naming and rename capabilities
3. **Pending Settings Queue** - Apply settings updates immediately if connected, or on next connection
4. **Connection Resilience** - Auto-reconnect and state synchronization

---

## 1. Discovery Service Integration (Like Signage Player)

### Current State
- Mobile camera manually registers via `/api/v1/cameras/mobile` endpoint
- Has heartbeat endpoint but **no automatic heartbeat mechanism in the app**
- No auto-reconnect on connection loss
- No Discovery Service registration

### Proposed Enhancement

#### 1.1 Auto-Registration on App Launch

**Implementation in Flutter App:**

```dart
class MobileCameraDiscoveryService {
  final Dio _dio;
  final Logger _logger;
  Timer? _heartbeatTimer;
  bool _isRegistered = false;
  String? _deviceId;
  String? _registrationId;
  
  static const Duration heartbeatInterval = Duration(seconds: 30);
  static const Duration registrationRetryDelay = Duration(seconds: 10);
  
  /// Initialize and register with platform
  Future<bool> initialize() async {
    try {
      _logger.i('Initializing Mobile Camera Discovery Service...');
      
      // Get device information (already implemented)
      _deviceId = await DeviceIdentifierService.generateDeviceId();
      
      // Register with Discovery Service
      final registered = await _registerWithDiscovery();
      
      if (registered) {
        _startHeartbeat();
        _logger.i('Discovery Service initialized successfully');
      } else {
        _logger.w('Failed to register - will retry');
        _scheduleRetry();
        
        // ⚠️ FALLBACK: If automatic registration fails after retries,
        // the app should show UI for manual platform connection input
        // (IP address, port, credentials if needed)
      }
      
      return registered;
    } catch (e, stackTrace) {
      _logger.e('Discovery initialization failed', error: e, stackTrace: stackTrace);
      _scheduleRetry();
      return false;
    }
  }
  
  /// Register mobile camera with Discovery Service
  Future<bool> _registerWithDiscovery() async {
    try {
      final authService = AuthenticationService.instance;
      final discoveryUrl = '${authService.discoveryServiceUrl}/api/v1/services/register';
      
      final localIp = await _getLocalIpAddress();
      final deviceInfo = await _getDeviceInfo();
      
      final registration = {
        'name': 'mobile-camera-$_deviceId',
        'service_type': 'mobile_camera',
        'host': localIp,
        'port': 8554, // Mobile camera streaming port
        'metadata': {
          'device_id': _deviceId,
          'camera_name': await _getCameraName(),
          'platform': deviceInfo['platform'],
          'manufacturer': deviceInfo['manufacturer'],
          'model': deviceInfo['model'],
          'app_version': deviceInfo['app_version'],
          'capabilities': ['video_streaming', 'photo_capture', 'remote_control'],
        },
        'health_check_endpoint': '/health',
        'version': '2.0.0',
      };
      
      final response = await _dio.post(
        discoveryUrl,
        data: registration,
        options: Options(
          headers: {'Content-Type': 'application/json'},
          validateStatus: (status) => status != null && status < 500,
        ),
      );
      
      if (response.statusCode == 200 || response.statusCode == 201) {
        _isRegistered = true;
        _registrationId = response.data['service_id'] as String?;
        _logger.i('Registered with Discovery Service: $_registrationId');
        return true;
      }
      
      return false;
    } catch (e) {
      _logger.e('Discovery registration failed', error: e);
      return false;
    }
  }
  
  /// Send heartbeat to Discovery Service
  Future<void> _sendHeartbeat() async {
    if (!_isRegistered || _registrationId == null) {
      await _registerWithDiscovery();
      return;
    }
    
    try {
      final authService = AuthenticationService.instance;
      final heartbeatUrl = '${authService.discoveryServiceUrl}/api/v1/services/heartbeat';
      
      await _dio.post(
        heartbeatUrl,
        data: {
          'service_id': _registrationId,
          'status': 'healthy',
          'metadata': {
            'is_streaming': await _isCurrentlyStreaming(),
            'last_frame_time': DateTime.now().toIso8601String(),
          },
        },
        options: Options(
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );
      
      _logger.d('Heartbeat sent successfully');
    } catch (e) {
      _logger.w('Heartbeat failed - will retry: $e');
    }
  }
  
  /// Start heartbeat timer
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(
      heartbeatInterval,
      (_) => _sendHeartbeat(),
    );
    _logger.d('Heartbeat timer started (${heartbeatInterval.inSeconds}s interval)');
  }
  
  /// Schedule retry registration
  void _scheduleRetry() {
    Timer(registrationRetryDelay, () => initialize());
  }
  
  /// Cleanup on app termination
  Future<void> dispose() async {
    _heartbeatTimer?.cancel();
    if (_isRegistered && _registrationId != null) {
      await _deregisterFromDiscovery();
    }
  }
}
```

#### 1.2 Integration with Existing Mobile Camera Provider

```dart
class PlatformStreamingProvider extends ChangeNotifier {
  // Add discovery service
  MobileCameraDiscoveryService? _discoveryService;
  
  Future<bool> initializeWithPlatform() async {
    // ... existing initialization ...
    
    // Initialize Discovery Service
    _discoveryService = MobileCameraDiscoveryService();
    await _discoveryService!.initialize();
    
    // ... continue with camera registration ...
  }
  
  @override
  void dispose() {
    _discoveryService?.dispose();
    super.dispose();
  }
}
```

---

## 2. Unified Camera Naming Logic (Like USB/RTSP Cameras)

### Current State
- Mobile camera uses device-based name generation
- Name is set during registration
- **No dedicated rename endpoint for mobile cameras**
- Collection name updates not synchronized

### Proposed Enhancement

**Apply the same naming and collection sync logic used for USB/RTSP cameras to mobile cameras:**

1. **Auto-naming** - Generate `Mobile Camera 1`, `Mobile Camera 2` if name not provided
2. **Rename endpoint** - `PATCH /api/v1/cameras/mobile/{uuid}/name` 
3. **Collection sync** - Automatically update collection name when camera renamed
4. **Name validation** - Enforce uniqueness and sanitization
5. **UUID-based** - Use server-generated UUID v4 for camera identification

#### 2.1 Backend: Apply Auto-Naming Logic

**Update `/api/v1/cameras/mobile` registration endpoint:**

```python
@router.post("/mobile", dependencies=[Depends(require_connect_camera)])
async def register_mobile_camera(
    mobile_data: MobileCameraCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Register a mobile device as a camera in the PPL Meta Platform."""
    
    try:
        from src.services.device_id_service import generate_uuid
        
        # Auto-detect IP from request if not provided
        client_ip = request.client.host
        actual_ip = mobile_data.ip_address or client_ip
        
        # Generate unique UUID for device_id (server-side generation)
        # This replaces client-provided device_id for security and consistency
        device_uuid = generate_uuid()
        
        # Check for existing camera by unique hardware identifier
        # Use a combination of manufacturer + model + serial as stable identifier
        hardware_id = f"{mobile_data.device_manufacturer}_{mobile_data.device_model}_{mobile_data.device_serial}"
        
        existing_camera = (
            db.query(Camera)
            .filter(
                Camera.hardware_identifier == hardware_id,
                Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )
        
        # Handle camera name with auto-naming logic
        from src.services.name_validation import validate_camera_name_unique, sanitize_camera_name
        from src.services.auto_naming_service import generate_auto_camera_name
        
        if mobile_data.name:
            # User provided a name - validate and sanitize
            camera_name = sanitize_camera_name(mobile_data.name)
            is_valid, error_msg = validate_camera_name_unique(
                db, 
                camera_name,
                exclude_device_id=existing_camera.device_id if existing_camera else None
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg,
                )
        else:
            # Auto-generate unique name
            camera_name = generate_auto_camera_name(db, CameraType.MOBILE)
        
        if existing_camera:
            # Update existing camera (keep UUID, update other fields)
            existing_camera.name = camera_name
            existing_camera.connection_string = f"mobile://{actual_ip}:{mobile_data.port}"
            existing_camera.ip_address = actual_ip
            existing_camera.port = mobile_data.port
            existing_camera.resolution_width = mobile_data.resolution_width
            existing_camera.resolution_height = mobile_data.resolution_height
            existing_camera.max_fps = mobile_data.max_fps
            existing_camera.status = CameraStatus.AVAILABLE
            existing_camera.last_seen = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_camera)
            
            logger.info(f"Updated existing mobile camera: {camera_name} (UUID: {existing_camera.device_id})")
            
            return {
                "message": "Mobile camera updated successfully",
                "camera": {
                    "id": existing_camera.id,
                    "name": existing_camera.name,
                    "device_id": existing_camera.device_id,  # UUID
                    "hardware_id": hardware_id,
                    "status": existing_camera.status.value,
                    "resolution": f"{existing_camera.resolution_width}x{existing_camera.resolution_height}",
                },
            }
        
        # Create new camera with server-generated UUID
        connection_string = f"mobile://{actual_ip}:{mobile_data.port}"
        
        new_camera = Camera(
            name=camera_name,
            device_id=device_uuid,  # Server-generated UUID v4
            hardware_identifier=hardware_id,  # Stable hardware identifier
            camera_type=CameraType.MOBILE,
            status=CameraStatus.AVAILABLE,
            connection_string=connection_string,
            port=mobile_data.port,
            resolution_width=mobile_data.resolution_width,
            resolution_height=mobile_data.resolution_height,
            max_fps=mobile_data.max_fps,
            supports_streaming=True,
            supports_recording=True,
            supports_audio=mobile_data.supports_audio,
            device_model=mobile_data.device_model,
            device_manufacturer=mobile_data.device_manufacturer,
            app_version=mobile_data.app_version,
        )
        
        db.add(new_camera)
        db.commit()
        db.refresh(new_camera)
        
        logger.info(f"Mobile camera registered: {camera_name} (UUID: {device_uuid}, HW: {hardware_id})")
        
        return {
            "message": "Mobile camera registered successfully",
            "camera": {
                "id": new_camera.id,
                "name": new_camera.name,
                "device_id": new_camera.device_id,  # UUID - mobile app MUST store this
                "hardware_id": hardware_id,
                "camera_type": new_camera.camera_type.value,
                "status": new_camera.status.value,
                "resolution": f"{new_camera.resolution_width}x{new_camera.resolution_height}",
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering mobile camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register mobile camera",
        )
```

#### 2.2 Backend: Add Mobile Camera Rename Endpoint

**Add to `/api/v1/endpoints/cameras.py`:**

```python
@router.patch("/mobile/{device_id}/name", dependencies=[Depends(require_connect_camera)])
async def rename_mobile_camera(
    device_id: str,  # UUID v4 format
    camera_update: CameraNameUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """
    Rename a mobile camera via UUID.
    
    - device_id parameter is UUID v4 (e.g., '550e8400-e29b-41d4-a716-446655440000')
    - Updates camera name in database
    - Synchronizes collection name
    - Can be called when camera is offline (settings queued)
    - Applied on next connection if offline
    """
    try:
        # Find the mobile camera by UUID
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id,  # UUID lookup
                Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )
        
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mobile camera {device_id} not found",
            )
        
        # Validate camera name uniqueness
        from src.services.name_validation import validate_camera_name_unique, sanitize_camera_name
        new_name = sanitize_camera_name(camera_update.name)
        
        if new_name == camera.name:
            return {
                "message": "Camera name unchanged",
                "camera": {
                    "device_id": camera.device_id,
                    "name": camera.name,
                }
            }
        
        is_valid, error_msg = validate_camera_name_unique(db, new_name, exclude_device_id=device_id)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        
        old_name = camera.name
        camera.name = new_name
        
        # If camera is offline, queue the name update
        is_online = camera.status in [CameraStatus.CONNECTED, CameraStatus.STREAMING]
        
        if not is_online:
            # Queue setting for next connection
            from src.models.pending_settings import PendingCameraSettings
            
            pending = PendingCameraSettings(
                camera_device_id=device_id,
                setting_type='name_update',
                setting_value={'new_name': new_name, 'old_name': old_name},
                created_at=datetime.utcnow(),
                user_id=current_user.get('sub')
            )
            db.add(pending)
        
        db.commit()
        db.refresh(camera)
        
        logger.info(
            f"User {current_user.get('sub')} renamed mobile camera: "
            f"{old_name} -> {new_name} (device_id: {device_id}, "
            f"{'queued for next connection' if not is_online else 'applied immediately'})"
        )
        
        # Update associated collection name (same as USB/RTSP cameras)
        await _update_collection_name_for_camera(device_id, new_name, current_user)
        
        return {
            "message": f"Camera name updated successfully ({'queued' if not is_online else 'applied'})",
            "camera": {
                "device_id": camera.device_id,
                "name": camera.name,
                "old_name": old_name,
                "status": camera.status.value,
                "update_queued": not is_online,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming mobile camera: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename mobile camera: {str(e)}",
        )
```

#### 2.3 Automatic Collection Renaming

**Mobile camera collections are automatically renamed when the camera is renamed, matching USB/RTSP camera behavior.**

When a mobile camera is renamed via `PATCH /api/v1/cameras/mobile/{uuid}/name`, the system automatically updates the associated collection name in the Media Service. This ensures:

- **Consistent naming** across camera and collection records
- **User experience** matches USB/RTSP cameras (no manual collection updates needed)
- **Collection persistence** even when camera is offline

##### Collection Rename Flow

```python
async def _update_collection_name_for_camera(
    device_id: str, 
    new_name: str, 
    current_user: Dict
) -> None:
    """
    Update collection name when camera is renamed.
    Uses service-to-service authentication to Media Service.
    """
    try:
        import httpx
        import os
        import jwt
        from datetime import datetime, timedelta
        
        # Create service token for camera->media service auth
        node_secret = os.getenv("NODE_SERVICE_SECRET")
        service_token_payload = {
            'sub': str(current_user.get('sub')),
            'exp': datetime.utcnow() + timedelta(minutes=5)
        }
        service_token = jwt.encode(service_token_payload, node_secret, algorithm='HS256')
        
        headers = {
            'Authorization': f'Bearer {service_token}',
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            # 1. Find collection by camera_device_id (UUID)
            response = await client.get(
                f"http://localhost:8000/api/v1/media/collections/by-camera/{device_id}",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                collection = response.json()
                collection_uuid = collection.get("uuid")
                
                # 2. Update collection name
                update_response = await client.patch(
                    f"http://localhost:8000/api/v1/media/collections/{collection_uuid}/name",
                    params={"name": new_name},
                    headers=headers,
                    timeout=10.0
                )
                
                if update_response.status_code == 200:
                    logger.info(f"✅ Collection renamed for mobile camera {device_id}: {new_name}")
                else:
                    logger.warning(
                        f"⚠️ Failed to rename collection for mobile camera {device_id}: "
                        f"{update_response.status_code}"
                    )
            else:
                logger.info(f"ℹ️ No collection found for mobile camera {device_id}")
                
    except Exception as e:
        logger.error(f"❌ Error renaming collection for mobile camera {device_id}: {e}")
        # Don't fail the camera rename if collection update fails
```

##### Key Points

- **Automatic synchronization**: No user intervention required
- **Service-to-service call**: Camera Service → Media Service
- **UUID-based lookup**: Uses camera's UUID to find collection
- **Non-blocking**: Collection rename failure doesn't fail camera rename
- **Works offline**: Collection renamed immediately even if camera disconnected
- **Consistent with platform**: Same logic used for USB/RTSP cameras

##### Media Service Endpoints Used

```
GET  /api/v1/media/collections/by-camera/{device_id}
  - Returns collection associated with camera UUID
  - Returns 404 if no collection exists (camera hasn't recorded yet)

PATCH /api/v1/media/collections/{collection_uuid}/name?name={new_name}
  - Updates collection name
  - Validates name uniqueness
  - Returns updated collection metadata
```

---

## 3. Pending Settings Queue (Apply on Next Connection)

### Problem Statement
When a user updates camera settings (name, detection modes, etc.) while the mobile camera is **offline/disconnected**, those changes are lost. USB/RTSP cameras don't have this issue because they're typically always available.

### Proposed Solution: Pending Settings Table

#### 3.1 Database Schema

**Add new model: `src/models/pending_settings.py`:**

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class PendingCameraSettings(Base):
    """Queue of pending settings updates for cameras that are offline."""
    
    __tablename__ = "pending_camera_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_device_id = Column(String(255), nullable=False, index=True)
    setting_type = Column(String(100), nullable=False)  # 'name_update', 'workflow_settings', 'resolution', etc.
    setting_value = Column(JSON, nullable=False)  # The actual setting data
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)
    user_id = Column(String(255), nullable=True)
    status = Column(String(50), default='pending')  # 'pending', 'applied', 'failed'
    error_message = Column(String(500), nullable=True)
```

**Migration script:**

```python
"""Add pending_camera_settings table

Revision ID: add_pending_settings
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'pending_camera_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('camera_device_id', sa.String(255), nullable=False, index=True),
        sa.Column('setting_type', sa.String(100), nullable=False),
        sa.Column('setting_value', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('error_message', sa.String(500), nullable=True),
    )
    
    op.create_index('idx_pending_settings_device', 'pending_camera_settings', ['camera_device_id', 'status'])

def downgrade():
    op.drop_table('pending_camera_settings')
```

#### 3.2 Backend Service: Pending Settings Manager

**Create `src/services/pending_settings_service.py`:**

```python
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.models.pending_settings import PendingCameraSettings
from src.models.camera import Camera

logger = logging.getLogger(__name__)

class PendingSettingsService:
    """Service for managing pending camera settings."""
    
    @staticmethod
    def queue_setting(
        db: Session,
        camera_device_id: str,
        setting_type: str,
        setting_value: Dict[str, Any],
        user_id: str
    ) -> PendingCameraSettings:
        """Queue a setting update for a camera."""
        pending = PendingCameraSettings(
            camera_device_id=camera_device_id,
            setting_type=setting_type,
            setting_value=setting_value,
            created_at=datetime.utcnow(),
            user_id=user_id,
            status='pending'
        )
        
        db.add(pending)
        db.commit()
        db.refresh(pending)
        
        logger.info(f"Queued {setting_type} for camera {camera_device_id}")
        return pending
    
    @staticmethod
    async def apply_pending_settings(
        db: Session,
        camera_device_id: str
    ) -> Dict[str, Any]:
        """
        Apply all pending settings for a camera when it connects.
        Called from heartbeat or connection endpoint.
        """
        pending_settings = (
            db.query(PendingCameraSettings)
            .filter(
                PendingCameraSettings.camera_device_id == camera_device_id,
                PendingCameraSettings.status == 'pending'
            )
            .order_by(PendingCameraSettings.created_at)
            .all()
        )
        
        if not pending_settings:
            return {"applied": 0, "failed": 0}
        
        applied_count = 0
        failed_count = 0
        
        for setting in pending_settings:
            try:
                # Apply the setting based on type
                if setting.setting_type == 'name_update':
                    await PendingSettingsService._apply_name_update(db, camera_device_id, setting.setting_value)
                elif setting.setting_type == 'workflow_settings':
                    await PendingSettingsService._apply_workflow_settings(db, camera_device_id, setting.setting_value)
                elif setting.setting_type == 'resolution_update':
                    await PendingSettingsService._apply_resolution_update(db, camera_device_id, setting.setting_value)
                # Add more setting types as needed
                
                # Mark as applied
                setting.status = 'applied'
                setting.applied_at = datetime.utcnow()
                applied_count += 1
                
                logger.info(f"Applied {setting.setting_type} for camera {camera_device_id}")
                
            except Exception as e:
                setting.status = 'failed'
                setting.error_message = str(e)
                failed_count += 1
                logger.error(f"Failed to apply {setting.setting_type} for camera {camera_device_id}: {e}")
        
        db.commit()
        
        return {
            "applied": applied_count,
            "failed": failed_count,
            "total": len(pending_settings)
        }
    
    @staticmethod
    async def _apply_name_update(db: Session, device_id: str, value: Dict) -> None:
        """Apply pending name update."""
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if camera:
            camera.name = value['new_name']
            # Collection name sync happens automatically via existing logic
    
    @staticmethod
    async def _apply_workflow_settings(db: Session, device_id: str, value: Dict) -> None:
        """Apply pending workflow settings."""
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if camera:
            for key, val in value.items():
                if hasattr(camera, key):
                    setattr(camera, key, val)
    
    @staticmethod
    async def _apply_resolution_update(db: Session, device_id: str, value: Dict) -> None:
        """Apply pending resolution update."""
        camera = db.query(Camera).filter(Camera.device_id == device_id).first()
        if camera:
            camera.resolution_width = value.get('width', camera.resolution_width)
            camera.resolution_height = value.get('height', camera.resolution_height)
    
    @staticmethod
    def get_pending_settings(
        db: Session,
        camera_device_id: str
    ) -> List[PendingCameraSettings]:
        """Get all pending settings for a camera."""
        return (
            db.query(PendingCameraSettings)
            .filter(
                PendingCameraSettings.camera_device_id == camera_device_id,
                PendingCameraSettings.status == 'pending'
            )
            .order_by(PendingCameraSettings.created_at)
            .all()
        )
    
    @staticmethod
    def clear_old_settings(db: Session, days: int = 30) -> int:
        """Clear applied/failed settings older than specified days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        count = (
            db.query(PendingCameraSettings)
            .filter(
                PendingCameraSettings.status.in_(['applied', 'failed']),
                PendingCameraSettings.created_at < cutoff_date
            )
            .delete()
        )
        
        db.commit()
        logger.info(f"Cleared {count} old pending settings")
        return count
```

#### 3.3 Apply Pending Settings on Connection

**Update mobile camera heartbeat endpoint:**

```python
@router.post("/mobile/{device_id}/heartbeat", dependencies=[Depends(require_connect_camera)])
async def mobile_camera_heartbeat(
    device_id: str,
    heartbeat_data: Optional[Dict] = None,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Receive heartbeat from mobile camera to update last_seen timestamp."""
    
    try:
        camera = (
            db.query(Camera)
            .filter(
                Camera.device_id == device_id,
                Camera.camera_type == CameraType.MOBILE
            )
            .first()
        )
        
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mobile camera {device_id} not found",
            )
        
        # Track previous status
        was_offline = camera.status == CameraStatus.AVAILABLE
        
        # Update last_seen and status
        camera.last_seen = datetime.utcnow()
        if camera.status == CameraStatus.AVAILABLE:
            camera.status = CameraStatus.CONNECTED
        
        db.commit()
        
        # If camera just came online, apply pending settings
        pending_applied = None
        if was_offline:
            from src.services.pending_settings_service import PendingSettingsService
            pending_applied = await PendingSettingsService.apply_pending_settings(db, device_id)
            logger.info(f"Applied {pending_applied['applied']} pending settings for {device_id}")
        
        return {
            "message": "Heartbeat received",
            "device_id": device_id,
            "status": camera.status.value,
            "timestamp": camera.last_seen.isoformat(),
            "pending_settings_applied": pending_applied,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing heartbeat for mobile camera {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process mobile camera heartbeat",
        )
```

#### 3.4 Update All Settings Endpoints

**Modify existing endpoints to queue settings if camera is offline:**

```python
@router.patch("/{device_id}/workflow-settings", dependencies=[Depends(require_connect_camera)])
async def update_workflow_settings(
    device_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Update workflow settings for a camera."""
    
    camera = db.query(Camera).filter(Camera.device_id == device_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    body = await request.json()
    
    # Check if camera is online
    is_online = camera.status in [CameraStatus.CONNECTED, CameraStatus.STREAMING]
    
    if not is_online and camera.camera_type == CameraType.MOBILE:
        # Queue settings for mobile cameras when offline
        from src.services.pending_settings_service import PendingSettingsService
        
        PendingSettingsService.queue_setting(
            db=db,
            camera_device_id=device_id,
            setting_type='workflow_settings',
            setting_value=body,
            user_id=current_user.get('sub')
        )
        
        return {
            "message": "Settings queued for next connection",
            "device_id": device_id,
            "settings_queued": True,
            "settings": body,
        }
    
    # Apply immediately if online (existing logic)
    # ... rest of existing implementation ...
```

---

## 4. Mobile App Changes

### 4.1 Flutter App: Connection Initialization Flow

```dart
// In main app initialization
Future<void> _initializeMobileCameraServices() async {
  // 1. Initialize authentication
  final authProvider = context.read<AuthenticationProvider>();
  await authProvider.initialize();
  
  // 2. If authenticated, initialize discovery service
  if (authProvider.isAuthenticated) {
    final discoveryService = MobileCameraDiscoveryService();
    final registered = await discoveryService.initialize();
    
    // 2a. Fallback to manual input if auto-registration fails
    if (!registered) {
      // Show UI for manual platform connection
      await _showManualConnectionDialog();
      return;
    }
    
    // 3. Register camera with platform (existing logic)
    await _registerCameraWithPlatform();
    
    // 4. Check for pending settings and apply
    await _checkPendingSettings();
  }
}

Future<void> _showManualConnectionDialog() async {
  // Show dialog/screen for user to manually enter:
  // - Platform IP address
  // - Discovery Service port
  // - Camera Service port
  // - Optional: credentials if authentication failed
  await Navigator.push(
    context,
    MaterialPageRoute(
      builder: (context) => ManualPlatformConnectionScreen(),
    ),
  );
}

Future<void> _checkPendingSettings() async {
  try {
    final authService = AuthenticationService.instance;
    final prefs = await SharedPreferences.getInstance();
    final deviceUuid = prefs.getString('camera_device_uuid');
    
    if (deviceUuid == null) return;
    
    final response = await http.get(
      Uri.parse('${authService.cameraServiceUrl}/api/v1/cameras/$deviceUuid/pending-settings'),
      headers: await authService.getAuthHeaders(),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['pending_count'] > 0) {
        print('📋 Found ${data['pending_count']} pending settings');
        // Settings will be applied automatically by backend on heartbeat
      }
    }
  } catch (e) {
    print('⚠️ Error checking pending settings: $e');
  }
}
```

### 4.2 Flutter App: Handle Name Updates

```dart
class CameraSettingsProvider extends ChangeNotifier {
  Future<bool> updateCameraName(String newName) async {
    try {
      final authService = AuthenticationService.instance;
      
      // Get stored UUID from registration response
      final prefs = await SharedPreferences.getInstance();
      final deviceUuid = prefs.getString('camera_device_uuid');
      
      if (deviceUuid == null) {
        print('❌ No camera UUID found - camera not registered');
        return false;
      }
      
      final response = await http.patch(
        Uri.parse('${authService.cameraServiceUrl}/api/v1/cameras/mobile/$deviceUuid/name'),
        headers: await authService.getAuthHeaders(),
        body: jsonEncode({'name': newName}),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Store updated name locally
        await _prefs.setString('camera_name', newName);
        
        if (data['update_queued'] == true) {
          // Show user that update is queued
          _showSnackbar('Camera name will be updated on next connection');
        } else {
          _showSnackbar('Camera name updated successfully');
        }
        
        notifyListeners();
        return true;
      }
      
      return false;
    } catch (e) {
      print('Error updating camera name: $e');
      return false;
    }
  }
}
```

---

## 5. Mobile App: UUID Storage & Usage

### Store UUID After Registration

```dart
class PlatformStreamingProvider extends ChangeNotifier {
  String? _cameraDeviceUuid;  // Server-generated UUID
  
  /// Register mobile camera and store UUID
  Future<RegistrationResult> registerCamera({String? customName}) async {
    try {
      final authService = AuthenticationService.instance;
      final deviceInfo = await _getDeviceInfo();
      
      // Prepare registration data (NO device_id sent)
      final registrationData = {
        'name': customName,  // Optional
        'device_manufacturer': deviceInfo['manufacturer'],
        'device_model': deviceInfo['model'],
        'device_serial': deviceInfo['serialNumber'],
        'port': 8554,
        'resolution_width': 1920,
        'resolution_height': 1080,
        'max_fps': 30,
      };
      
      final response = await http.post(
        Uri.parse('${authService.cameraServiceUrl}/api/v1/cameras/mobile'),
        headers: await authService.getAuthHeaders(),
        body: jsonEncode(registrationData),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // CRITICAL: Store server-generated UUID
        _cameraDeviceUuid = data['camera']['device_id'];
        
        // Save UUID to SharedPreferences for persistence
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('camera_device_uuid', _cameraDeviceUuid!);
        await prefs.setString('camera_name', data['camera']['name']);
        
        print('✅ Camera registered with UUID: $_cameraDeviceUuid');
        
        _isRegistered = true;
        notifyListeners();
        return RegistrationResult.success(_cameraDeviceUuid!);
      }
      
      return RegistrationResult.failure('Registration failed');
    } catch (e) {
      return RegistrationResult.failure('Error: $e');
    }
  }
  
  /// Get stored UUID (for all API calls)
  Future<String?> getStoredUuid() async {
    if (_cameraDeviceUuid != null) return _cameraDeviceUuid;
    
    final prefs = await SharedPreferences.getInstance();
    _cameraDeviceUuid = prefs.getString('camera_device_uuid');
    return _cameraDeviceUuid;
  }
  
  /// Send heartbeat using UUID
  Future<void> sendHeartbeat() async {
    final uuid = await getStoredUuid();
    if (uuid == null) {
      print('⚠️ No UUID stored - camera not registered');
      return;
    }
    
    final authService = AuthenticationService.instance;
    await http.post(
      Uri.parse('${authService.cameraServiceUrl}/api/v1/cameras/mobile/$uuid/heartbeat'),
      headers: await authService.getAuthHeaders(),
    );
  }
}
```

---

## 6. Implementation Plan

### Phase 1: Backend Foundation (Week 1)
- ✅ Add `hardware_identifier` column to camera table
- ✅ Update mobile registration endpoint to use UUID v4
- ✅ Create `pending_camera_settings` table migration
- ✅ Implement `PendingSettingsService`
- ✅ Update mobile camera registration endpoint with auto-naming
- ✅ Add mobile camera rename endpoint (UUID-based)
- ✅ Update heartbeat endpoint to apply pending settings
- ✅ Create migration script for existing mobile cameras

### Phase 2: Mobile App Discovery Integration (Week 1-2)
- ✅ Implement `MobileCameraDiscoveryService`
- ✅ Update registration to NOT send device_id
- ✅ Add UUID storage in SharedPreferences
- ✅ Update all API calls to use stored UUID
- ✅ Add heartbeat mechanism using UUID
- ✅ Add manual connection fallback UI
- ✅ Integrate with existing streaming provider
- ✅ Test auto-reconnect scenarios

### Phase 3: Settings Queue Integration (Week 2)
- ✅ Update all settings endpoints to queue when offline
- ✅ Add pending settings check on app launch
- ✅ Add UI indicators for queued settings
- ✅ Test offline/online state transitions

### Phase 4: Testing & Validation (Week 3)
- ✅ Test name updates (online vs offline)
- ✅ Test workflow settings (online vs offline)
- ✅ Test heartbeat resilience and auto-reconnect
- ✅ Test Discovery Service integration
- ✅ Test manual connection fallback flow
- ✅ Load testing with multiple mobile cameras

### Phase 5: Documentation & Rollout (Week 3)
- ✅ Update API documentation
- ✅ Create user guide for mobile cameras
- ✅ Deploy to staging environment
- ✅ Production rollout

---

## 7. UUID Benefits for Mobile Cameras

### Security
1. **Server-Generated UUIDs** - Prevents client-side ID spoofing
2. **Unpredictable IDs** - Cannot guess other camera UUIDs
3. **Consistent Format** - Same UUID format across all camera types

### Reliability
1. **Stable Identifiers** - UUID persists across app reinstalls (via hardware_id)
2. **Collision-Free** - UUID v4 guarantees global uniqueness
3. **Migration Path** - Easy to migrate existing cameras

### Consistency
1. **Platform Uniformity** - USB, RTSP, Edge, Mobile all use UUIDs
2. **Collection Linking** - Collections reference cameras by UUID
3. **API Simplification** - All endpoints use same UUID pattern

---

## 8. Benefits

### For Users
1. **Seamless Experience** - Mobile cameras automatically connect and register
2. **Fallback to Manual** - If auto-registration fails, UI prompts for manual input
3. **Reliable Updates** - Settings applied even when phone temporarily offline
4. **Consistent Naming** - Same naming logic across all camera types
5. **Automatic Collection Sync** - Collections automatically renamed when camera renamed
6. **Better Visibility** - See mobile cameras in Discovery Service dashboard
7. **Secure Identifiers** - Server-generated UUIDs prevent ID conflicts

### For Platform
1. **Unified Management** - All cameras follow same patterns (UUID-based)
2. **Improved Reliability** - Heartbeat mechanism ensures connection health
3. **Better Fault Tolerance** - Auto-reconnect and pending settings queue
4. **Easier Maintenance** - Consistent codebase across camera types
5. **Security** - Server controls camera IDs, preventing spoofing

---

## 9. Migration & Backward Compatibility

### UUID Migration Strategy

**For Existing Mobile Cameras:**
1. Existing cameras using old device_id format will be migrated on next registration
2. Backend detects cameras by `hardware_identifier` (manufacturer+model+serial)
3. If existing camera found, keeps its UUID; otherwise generates new UUID
4. Mobile app receives UUID in registration response and stores it
5. All subsequent API calls use stored UUID

**Migration Script:**
```python
# One-time migration script
def migrate_mobile_cameras_to_uuid():
    """Migrate existing mobile cameras to UUID format."""
    from src.services.device_id_service import generate_uuid
    
    cameras = db.query(Camera).filter(
        Camera.camera_type == CameraType.MOBILE,
        ~Camera.device_id.op('~')('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
    ).all()
    
    for camera in cameras:
        old_device_id = camera.device_id
        camera.device_id = generate_uuid()
        # Keep hardware_identifier if exists, or create from other fields
        if not camera.hardware_identifier:
            camera.hardware_identifier = f"{camera.device_manufacturer}_{camera.device_model}_{old_device_id}"
        
        logger.info(f"Migrated mobile camera: {old_device_id} -> {camera.device_id}")
    
    db.commit()
```

### Backward Compatibility Notes

- Discovery Service integration is **additive** - doesn't break existing functionality
- Pending settings only apply to mobile cameras (USB/RTSP don't need it)
- Name migration can happen gradually as cameras reconnect
- **Breaking Change**: Mobile apps MUST update to store and use server-generated UUID
- Old mobile app versions will fail to register (need app update)

---

## 10. API Changes Summary

### New Endpoints

```
PATCH /api/v1/cameras/mobile/{uuid}/name
  - Rename mobile camera via UUID (queued if offline)
  - uuid is server-generated UUID v4 format

GET /api/v1/cameras/{uuid}/pending-settings
  - Get list of pending settings for camera
  - uuid is server-generated UUID v4 format

POST /api/v1/cameras/{uuid}/apply-pending-settings
  - Manually trigger application of pending settings
  - uuid is server-generated UUID v4 format
```

### Modified Endpoints

```
POST /api/v1/cameras/mobile
  - Server generates UUID v4 (not client-provided)
  - Uses hardware_identifier (manufacturer+model+serial) to detect existing cameras
  - Now uses auto-naming logic if name not provided
  - Returns UUID in response as device_id - mobile app MUST store this

POST /api/v1/cameras/mobile/{uuid}/heartbeat
  - uuid is server-generated UUID (mobile app must use stored UUID)
  - Now applies pending settings on first heartbeat after offline
  - Returns pending_settings_applied in response

PATCH /api/v1/cameras/{uuid}/workflow-settings
  - uuid is server-generated UUID v4 format
  - Queues settings if mobile camera is offline
  - Returns settings_queued: true in response
```

---

## 11. Testing Checklist

### UUID Implementation
- [ ] Server generates valid UUID v4 for new mobile cameras
- [ ] Registration returns UUID in response
- [ ] Mobile app stores UUID in SharedPreferences
- [ ] All API calls use stored UUID (not hardware device_id)
- [ ] Existing camera detection via hardware_identifier works
- [ ] Migration script converts old device_ids to UUIDs
- [ ] UUID format validation on all endpoints

### Discovery & Connection
- [ ] Mobile camera auto-registers with Discovery Service
- [ ] Heartbeat sent every 30 seconds using UUID
- [ ] Auto-reconnect after network loss
- [ ] Fallback to manual input if auto-registration fails

### Settings Management
- [ ] Name update applied immediately when online (via UUID)
- [ ] Name update queued when offline, applied on reconnection
- [ ] Workflow settings queued when offline
- [ ] Multiple pending settings applied in correct order
- [ ] **Collection name automatically syncs when camera renamed** (same as USB/RTSP)
- [ ] Collection rename works when camera is offline
- [ ] Collection rename service-to-service call succeeds
- [ ] Old pending settings cleaned up after 30 days
- [ ] Discovery Service shows mobile camera as "healthy"

### Edge Cases
- [ ] Same physical device re-registering gets same UUID
- [ ] Different devices get unique UUIDs
- [ ] Lost UUID recovery (re-registration flow)
- [ ] Concurrent registration attempts handled correctly

---

## 12. Security Considerations

1. **Authentication** - All Discovery Service calls use JWT tokens
2. **Authorization** - Only camera owner can rename or update settings
3. **Validation** - Camera names sanitized and validated for uniqueness
4. **Rate Limiting** - Heartbeat endpoint rate limited to prevent abuse
5. **Data Privacy** - Pending settings don't store sensitive data

---

## 13. Monitoring & Observability

### Metrics to Track
- Mobile camera discovery registration success rate
- Heartbeat success/failure rate
- Pending settings queue length per camera
- Pending settings application success rate
- Average time from settings change to application

### Logs to Monitor
- Discovery registration failures
- Heartbeat timeout patterns
- Pending settings application errors
- Name collision conflicts

---

## 14. Future Enhancements

1. **Push Notifications** - Notify mobile app when settings updated
2. **WebSocket for Real-time Updates** - Replace heartbeat with WebSocket
3. **Batch Settings Updates** - Apply multiple settings atomically
4. **Settings Rollback** - Undo failed settings updates
5. **Mobile Camera Clustering** - Group mobile cameras by location/user

---

## Conclusion

This proposal brings the mobile camera app in line with the robust, production-ready patterns already proven in the Signage Simple Player and USB/RTSP camera implementations. By implementing Discovery Service integration, unified naming logic, and pending settings queue, we ensure a consistent, reliable experience across all camera types in the PPL Meta platform.

The phased implementation plan allows for gradual rollout with minimal risk, while maintaining backward compatibility with existing deployments.

---

**Next Steps:**
1. Review and approve proposal
2. Create implementation tickets
3. Begin Phase 1 backend development
4. Schedule mobile app development sprint
