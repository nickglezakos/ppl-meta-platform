# Camera Collections Discovery Report
**Date:** October 20, 2025  
**Version:** 1.0.0  
**Author:** System Analysis  

## Executive Summary

This document provides a comprehensive technical analysis of the camera collections discovery process completed on October 20, 2025. The analysis reveals the actual camera collections and device configurations available in the PPL Meta platform, replacing previously used mock data with real system information.

## Authentication Setup

### Successful Authentication
- **Endpoint:** `POST http://localhost:8001/api/v1/users/login`
- **Credentials:** 
  - Username: `fresh.user@example.com`
  - Password: `NewPassword234!`
- **Token Generated:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzYwOTg3MTI3fQ.hFI-H6tQObeO0E6bkcmFeXcwlQ_ohzZHvqPxqRFMVbI`
- **Token Type:** Bearer
- **User ID:** 7 (extracted from JWT payload)

## OpenAPI Specifications Analysis

### Camera Service API (Port 8005)
**Key Endpoints Discovered:**
- `GET /api/v1/cameras/` - List all cameras
- `POST /api/v1/cameras/detect` - Detect new cameras
- `POST /api/v1/cameras/{device_id}/connect` - Connect specific camera
- `GET /api/v1/cameras/{device_id}/info` - Get camera information
- `GET /api/v1/cameras/active` - List active connections
- `POST /api/v1/cameras/rtsp` - Add RTSP camera
- `GET /api/v1/cameras/mobile` - List mobile cameras
- `POST /api/v1/cameras/mobile` - Register mobile camera

**Important Finding:** The camera service does NOT have collection endpoints - it manages individual camera devices only.

### Media Service API (Port 8000)
**Collection Management Endpoints:**
- `GET /api/v1/media/collections` - List all collections ✅
- `POST /api/v1/media/collections` - Create new collection
- `GET /api/v1/media/collections/by-camera/{camera_device_id}` - Get collection by camera ✅
- `GET /api/v1/media/collections/{collection_id}` - Get specific collection
- `GET /api/v1/media/collections/{collection_id}/items` - Get collection items
- `GET /api/v1/media/collections/{collection_id}/stats` - Get collection statistics

**Key Insight:** Collections are managed by the Media Service, not the Camera Service. Each camera device can have associated collections for storing recorded media.

## Real Camera Collections Discovered

### Active Camera Devices (from Camera Service)
```json
[
    {
        "id": 1,
        "name": "USB Camera 0",
        "device_id": "usb_camera_0",
        "camera_type": "USB",
        "status": "available",
        "resolution": "1280x720",
        "max_fps": 30,
        "supports_streaming": true,
        "supports_recording": true
    },
    {
        "id": 3,
        "name": "Nick desk",
        "device_id": "rtsp_192.168.1.76_554",
        "camera_type": "RTSP",
        "status": "available",
        "resolution": "1920x1080",
        "max_fps": 30,
        "supports_streaming": true,
        "supports_recording": true
    },
    {
        "id": 68,
        "name": "mcam-201117ty-2d7ee4",
        "device_id": "mobile_TKQ1.221114.001",
        "camera_type": "MOBILE",
        "status": "available",
        "resolution": "1920x1080",
        "max_fps": 30,
        "supports_streaming": true,
        "supports_recording": true
    }
]
```

### Associated Media Collections
```json
[
    {
        "name": "USB Camera 0 Collection",
        "description": "Auto-generated collection for USB Camera 0",
        "camera_device_id": "usb_camera_0",
        "uuid": "c984dbd1-6598-44db-aa99-87ac955de25a"
    },
    {
        "name": "usb_camera_0 Collection",
        "description": "Collection for camera: usb_camera_0",
        "camera_device_id": "usb_camera_0",
        "uuid": "76241fb0-fc86-4859-b442-f7f2979a5c53"
    },
    {
        "name": "rtsp_192.168.1.76_554 Collection",
        "description": "Collection for camera: rtsp_192.168.1.76_554",
        "camera_device_id": "rtsp_192.168.1.76_554",
        "uuid": "c8fccf88-9dcf-4899-b008-0701b81eab97"
    },
    {
        "name": "Nick desk Collection",
        "description": "Collection for camera: Nick desk",
        "camera_device_id": "nick_desk",
        "uuid": "153c03d9-4c63-4488-a634-b165e4b84c74"
    },
    {
        "name": "mcam-201117ty-2d7ee4 Collection",
        "description": "Collection for camera: mcam-201117ty-2d7ee4",
        "camera_device_id": "mobile_TKQ1.221114.001",
        "uuid": "4fe59481-c5f9-4b32-89aa-237897077220"
    }
]
```

## Technical Findings

### Mock vs Real Data Comparison

#### Previous Mock Collections (used in testing):
- `warehouse_cameras`
- `entrance_cameras` 
- `parking_cameras`
- `office_cameras`

#### Actual Real Collections (discovered):
- `USB Camera 0 Collection` (device_id: `usb_camera_0`)
- `rtsp_192.168.1.76_554 Collection` (device_id: `rtsp_192.168.1.76_554`)
- `mcam-201117ty-2d7ee4 Collection` (device_id: `mobile_TKQ1.221114.001`)

### Device ID Mapping
| Camera Name | Device ID | Camera Type | Collection UUID |
|-------------|-----------|-------------|-----------------|
| USB Camera 0 | `usb_camera_0` | USB | `c984dbd1-6598-44db-aa99-87ac955de25a` |
| Nick desk | `rtsp_192.168.1.76_554` | RTSP | `c8fccf88-9dcf-4899-b008-0701b81eab97` |
| mcam-201117ty-2d7ee4 | `mobile_TKQ1.221114.001` | MOBILE | `4fe59481-c5f9-4b32-89aa-237897077220` |

## Integration Architecture

### Service Communication Flow
1. **Camera Service** (Port 8005) - Manages physical camera devices and connections
2. **Media Service** (Port 8000) - Manages collections and recorded media associated with cameras
3. **Cross-Video Tracking** (vmeta service) - Requires collection names for processing

### API Integration Pattern
```
Client Authentication → Node Service (8001)
↓
Camera Discovery → Camera Service (8005) 
↓ 
Collection Query → Media Service (8000)
↓
Cross-Video Processing → vmeta Service (8008)
```

## Recommendations for Testing Infrastructure

### 1. Update Individual Headless Testing Script
The `tools/individual_headless_testing.py` script should be updated to use real collection names:

**Replace:**
```python
collections = ["warehouse_cameras", "entrance_cameras", "parking_cameras", "office_cameras"]
```

**With:**
```python
real_collections = [
    "USB Camera 0 Collection",  # USB camera
    "rtsp_192.168.1.76_554 Collection",  # RTSP camera
    "mcam-201117ty-2d7ee4 Collection"  # Mobile camera
]
```

### 2. Dynamic Collection Discovery
Implement dynamic collection fetching from Media Service:
```python
def fetch_available_collections(auth_token):
    response = requests.get(
        "http://localhost:8000/api/v1/media/collections",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    return [col["name"] for col in response.json()]
```

### 3. Camera-Specific Testing Options
Provide testing options based on camera type:
- **USB Camera Option:** `usb_camera_0` collection
- **RTSP Camera Option:** `rtsp_192.168.1.76_554` collection  
- **Mobile Camera Option:** `mobile_TKQ1.221114.001` collection

## Service Health Status

All services confirmed healthy during discovery:
- ✅ Node Service (8001) - Authentication working
- ✅ Media Service (8000) - Collections accessible
- ✅ Camera Service (8005) - Camera listings available
- ✅ vmeta Service (8008) - Cross-video tracking endpoints ready
- ✅ Gateway Service (8080) - Proxy routing functional
- ✅ Nginx Proxy - All services accessible via unified interface

## Next Steps

1. **Update Testing Scripts:** Replace mock collections with real collection names
2. **Implement Dynamic Discovery:** Add real-time collection fetching capability
3. **Test Real Data Pipeline:** Validate cross-video tracking with actual camera collections
4. **Document Collection Management:** Create procedures for adding/managing new camera collections

## Conclusion

The discovery process successfully identified the real camera infrastructure and collection architecture. The platform has 3 active cameras (USB, RTSP, Mobile) with corresponding media collections. The separation between camera device management (Camera Service) and media collection management (Media Service) is now clearly understood, enabling proper integration for cross-video tracking functionality.

**Key Success:** Authentication working, OpenAPI specs analyzed, real collections discovered, mock data identified for replacement.