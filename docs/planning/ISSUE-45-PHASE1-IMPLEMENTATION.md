# ISSUE-45 Phase 1: Backend Streaming Infrastructure - Implementation Plan

## Current Infrastructure Analysis

### ✅ Existing Streaming Infrastructure
- **Streaming Endpoints**: `/api/v1/streaming/{device_id}/start`, `/video`, `/stop`
- **Quality Controls**: Low/Medium/High/Ultra with configurable resolution and FPS
- **Session Management**: Authentication and streaming session tracking
- **MJPEG Streaming**: Proven video streaming over HTTP with browser compatibility
- **Camera Types Supported**: USB, RTSP cameras

### 🔧 Mobile Camera Integration Points
- **Mobile Registration**: Mobile cameras register via `/api/v1/cameras/mobile` 
- **Camera Type**: CameraType.MOBILE enum exists
- **Connection String**: Currently uses `mobile://{ip}:{port}` format
- **Database Support**: Mobile cameras stored with `supports_streaming=True`

## Phase 1 Implementation Tasks

### Task 1: Extend Camera Detection Service for Mobile Cameras ✅ Ready
- [x] CameraType.MOBILE already exists in models
- [x] Mobile cameras stored in database with streaming support
- **Implementation**: Extend connect_camera() method to handle mobile:// connection strings

### Task 2: Implement Mobile Camera Stream Ingestion 🚧 In Progress
- [ ] Add WebRTC/RTMP protocol handlers for mobile streaming
- [ ] Extend streaming endpoints to detect mobile camera types
- [ ] Implement mobile camera stream connection logic
- **Target**: Mobile cameras can send video streams to backend

### Task 3: Mobile Camera Session Management 🚧 In Progress  
- [ ] Extend StreamingSessionManager for mobile cameras
- [ ] Add mobile-specific authentication flow
- [ ] Implement mobile camera streaming session tracking
- **Target**: Mobile cameras have authenticated streaming sessions

### Task 4: Stream Relay and Transcoding ⏳ Planned
- [ ] Convert mobile streams (WebRTC/RTMP) to MJPEG for frontend compatibility
- [ ] Implement stream buffering and relay for mobile connections
- [ ] Add mobile stream quality adaptation
- **Target**: Mobile camera streams work with existing frontend components

### Task 5: Quality Controls for Mobile Cameras ⏳ Planned
- [ ] Extend quality settings to work with mobile cameras
- [ ] Implement mobile-specific resolution and FPS controls
- [ ] Add mobile camera streaming configuration
- **Target**: Mobile cameras support same quality controls as USB/RTSP cameras

## Implementation Strategy

### 1. Leverage Existing Architecture
- **Reuse**: Existing `/streaming/{device_id}/video` endpoint works for all camera types
- **Extend**: camera_detection.py connect_camera() method to handle mobile:// URLs
- **Maintain**: Same MJPEG output format for frontend compatibility

### 2. Mobile-Specific Adaptations
- **Input Protocols**: Accept RTMP/WebRTC streams from mobile apps
- **Transcoding**: Convert to MJPEG for existing frontend compatibility
- **Authentication**: Use existing session-based auth with mobile extensions

### 3. Quality Control Integration
- **Existing Settings**: Low (320x240), Medium (640x480), High (1280x720), Ultra (1920x1080)
- **Mobile Adaptation**: Send quality parameters to mobile app via streaming session
- **Transcoding**: Apply quality settings during stream conversion

## Next Steps for Implementation

1. **Start with Task 1**: Extend connect_camera() for mobile cameras
2. **Implement Task 2**: Add mobile stream ingestion protocols  
3. **Validate Integration**: Test with existing streaming endpoints
4. **Quality Controls**: Extend quality management for mobile cameras
5. **Session Management**: Enhance authentication for mobile streaming

## Expected Outcome

After Phase 1 completion:
- ✅ Mobile cameras connect to streaming infrastructure
- ✅ Mobile apps can send video streams via RTMP/WebRTC
- ✅ Backend converts mobile streams to MJPEG format
- ✅ Existing `/api/v1/streaming/{device_id}/video` works for mobile cameras
- ✅ Mobile cameras support same quality controls as other camera types
- ✅ Frontend CameraStreamPlayer works with mobile cameras without changes

This maintains UI consistency while extending backend capabilities for mobile cameras.
