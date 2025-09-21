# Video Playback Debugging Notes

## Issue Summary
Frontend Flutter video player fails to play videos from Gateway streaming endpoint despite backend returning valid video data.

## ❌ False Lead: File Cleanup Theory (Debunked)
**Initial Hypothesis**: Camera service file cleanup (path_obj.unlink()) was causing missing local files for Gateway streaming.

**Attempted Fix**: Disabled file cleanup in camera_detection.py lines 1375-1390.

**Result**: ❌ **FAILED** - Problem persists with identical symptoms:
- Flutter shows: `MEDIA_ERR_SRC_NOT_SUPPORTED`
- Error: "video unsuitable (missing or in a format not supported by your browser)"
- Backend confirms: HTTP 200, 2.6MB video/mp4, proper content-type

## ✅ Confirmed Working: Backend Streaming
```bash
curl -I -X GET "http://localhost:8080/api/v1/stream/video/3dce7d1e-a539-47bc-b2d0-a4ba3b391e3f?face_detection=true"
# HTTP/1.1 200 OK
# content-length: 2654277
# content-type: video/mp4
# accept-ranges: bytes
```

## 🔍 Real Issue: Frontend Video Player Compatibility

**Symptoms**:
- Gateway streaming responds correctly (HTTP 200, video/mp4)
- Flutter video player rejects stream with codec/format error
- Same issue affects SmartVideoPlayerWidget in media-preview
- Gallery VideoPlayerWidget works (different streaming endpoint)

**Key Differences**:
- **Gallery (Working)**: `/api/v1/media/stream/{uuid}` - Media Service direct
- **Media Preview (Broken)**: `/api/v1/stream/video/{uuid}?face_detection=true` - Gateway embedded

## 🎯 Next Investigation Areas

1. **HTTP Headers**: Compare response headers between working vs broken endpoints
2. **Video Codec**: Check if Gateway modifies video encoding for face detection
3. **Streaming Protocol**: Verify if Gateway uses chunked transfer vs direct stream
4. **Flutter Video Player**: Test with different video player implementations
5. **Content-Type**: Verify MIME type and codec parameters

## 📅 Timeline
- **Sept 21, 2025**: Identified file cleanup was not root cause
- **Sept 21, 2025**: Confirmed backend streaming works, frontend player fails

## 🔄 Status
**ACTIVE INVESTIGATION**: Frontend video player compatibility with Gateway streaming response format.