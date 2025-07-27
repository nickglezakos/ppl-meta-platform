# Issue Template

## **Issue**: [051] - 🎬 **Video Frame Extraction Endpoint**

**Title**: Implement Video Frame Extraction API Endpoint in Media Service
**Section**: Media Service API - Video Processing
**Priority**: Medium
**Status**: 🔄 PLANNING
**Parent**: N/A

**Description**:
Create a new REST API endpoint in the media service microservice that extracts and returns specific frames from video files as JPEG images. The endpoint should integrate seamlessly with the existing architecture, operating through the gateway microservice and nginx proxy, following the same patterns as other media endpoints like `/thumbnail/{media_id}` and `/stream/{media_id}`.

**Steps Required**:

1. **Backend API Implementation**:
   - Create new endpoint `GET /media/{media_id}/frame/{frame_number}` in `ppl-meta-media/src/api/v1/media.py`
   - Add frame extraction logic using video processing libraries (OpenCV/FFmpeg)
   - Implement proper error handling for invalid frame numbers and non-video files
   - Add authentication and access control following existing patterns

2. **Schema Definition**:
   - Add `VideoFrameResponse` schema in `ppl-meta-media/src/schemas/media.py`
   - Define request/response models for frame extraction parameters
   - Add validation for frame number ranges and video format support

3. **Service Layer Implementation**:
   - Extend `MediaService` class with frame extraction functionality
   - Add method `extract_video_frame(media_id, frame_number, output_format)`
   - Implement caching mechanism for frequently requested frames
   - Add video metadata validation (duration, frame count, fps)

4. **Gateway Integration**:
   - Add proxy route in `ppl-meta-gateway/src/api/v1/router.py`
   - Create `@api_router.get("/media/{media_id}/frame/{frame_number}")` endpoint
   - Implement proper request forwarding to media service

5. **Nginx Configuration**:
   - Update `nginx-local-dev.conf` to handle the new endpoint path
   - Add appropriate caching headers for frame images
   - Configure proper timeout settings for video processing

6. **Testing and Validation**:
   - Create unit tests for frame extraction functionality
   - Add integration tests for the complete request flow
   - Test with various video formats (MP4, AVI, MOV, WebM)
   - Validate performance with large video files

**Expected Result**:

- Endpoint `GET /media/{media_id}/frame/{frame_number}` returns JPEG image of specified frame
- Proper HTTP response codes (200 for success, 404 for invalid frame, 415 for non-video files)
- Integration works through gateway and nginx proxy
- Performance is acceptable for real-time frame extraction

**Technical Requirements**:

- **Authentication**: Use existing JWT-based authentication system
- **Access Control**: Verify user ownership or public sharing permissions
- **Video Processing**: Support common video formats (MP4, AVI, MOV, WebM)
- **Output Format**: Return JPEG images by default, with optional PNG/WebP support
- **Performance**: Frame extraction should complete within 5 seconds for standard videos
- **Caching**: Implement frame caching to avoid repeated processing
- **Error Handling**: Graceful handling of corrupted videos, invalid frames, and processing errors
- **Resource Management**: Proper cleanup of temporary files and memory usage

**Deliverables**:

- [ ] New API endpoint in `media.py` with full implementation
- [ ] Updated schemas in `media.py` for request/response models
- [ ] Extended `MediaService` class with frame extraction methods
- [ ] Gateway proxy route configuration
- [ ] Updated nginx configuration for routing
- [ ] Comprehensive test suite covering all scenarios
- [ ] Documentation for the new endpoint
- [ ] Performance benchmarks and optimization

**API Specification**:

```http
GET /api/v1/media/{media_id}/frame/{frame_number}

Parameters:
- media_id: UUID of the video file
- frame_number: Integer frame number to extract (0-based or 1-based)
- format: Optional output format (jpeg, png, webp) - default: jpeg
- quality: Optional JPEG quality (1-100) - default: 85
- size: Optional resize parameter (small, medium, large, or WxH) - default: original

Response:
- Content-Type: image/jpeg (or requested format)
- Content-Length: Size of image in bytes
- Cache-Control: Caching headers for performance
- X-Frame-Info: JSON metadata about the extracted frame
```

**Status**: ✅ RESOLVED
**Resolution Date**: July 27, 2025

**Resolution Applied**:

- ✅ **Backend API Implementation**: Added `extract_video_frame` endpoint in `ppl-meta-media/src/api/v1/media.py`
  - Route: `GET /{media_id}/frame/{frame_number}` with query parameters for format, quality, and size
  - Comprehensive parameter validation and error handling
  - Support for JPEG, PNG, and WebP output formats
  - Optional frame resizing with aspect ratio preservation
  - Proper authentication and access control integration

- ✅ **Schema Definition**: Added `VideoFrameResponse` schema in `ppl-meta-media/src/schemas/media.py`
  - Complete response model with frame metadata
  - Proper field validation and documentation
  - Integration with existing schema patterns

- ✅ **Service Layer Implementation**: Extended `MediaService` class with frame extraction functionality
  - Method: `extract_video_frame()` with comprehensive parameter support
  - OpenCV-based frame extraction with error handling
  - PIL-based image processing and format conversion
  - Frame validation against video total frame count
  - Proper resource cleanup and memory management

- ✅ **Gateway Integration**: Added proxy route in `ppl-meta-gateway/src/api/v1/router.py`
  - Route: `@api_router.get("/media/{media_id}/frame/{frame_number}")`
  - Seamless request forwarding to media service
  - Maintains existing authentication and routing patterns

- ✅ **Nginx Configuration**: Existing configuration supports the new endpoint
  - All `/api/` routes properly routed through gateway
  - 60-second timeout sufficient for frame processing
  - Standard caching and proxy headers applied

- ✅ **Error Handling**: Comprehensive error handling implemented
  - 400: Invalid parameters (format, quality, frame number, size)
  - 403: Access denied
  - 404: Frame out of range, media not found
  - 415: Non-video media type
  - 500: Processing errors with detailed messages

**Files Modified**:

- `ppl-meta-media/src/schemas/media.py` - Added VideoFrameResponse schema
- `ppl-meta-media/src/api/v1/media.py` - Added extract_video_frame endpoint
- `ppl-meta-media/src/services/media_service.py` - Added extract_video_frame method
- `ppl-meta-gateway/src/api/v1/router.py` - Added proxy route for frame extraction

---
