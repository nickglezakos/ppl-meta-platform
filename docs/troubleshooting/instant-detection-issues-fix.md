# Instant Detection Issues - Diagnosis & Fix

**Date**: December 12, 2025, 8:00 PM  
**Version**: 2.19.77  
**Issues**: Stop recording polling continues, Demographics showing "unknown"

---

## Issue 1: Instant Detection Polling Continues After Stop

### Problem
When you click "Stop" on the camera stream, the instant detection **continues polling** in the background, causing:
- Terminal logs continue showing polling requests
- Backend resources wasted
- Stream appears stopped but detection runs indefinitely

### Root Cause
Flutter frontend stops the video stream but does NOT call the instant detection stop endpoint:
```
POST /api/v1/instant-detection/stop
```

### Current Flow (BROKEN):
1. User clicks "Stop Stream" in Flutter
2. ✅ Flutter stops video display
3. ❌ Flutter does NOT call instant-detection/stop
4. ❌ Backend instant detection keeps running
5. ❌ Polling continues forever

### Required Flow (CORRECT):
1. User clicks "Stop Stream" in Flutter
2. ✅ Flutter stops video display  
3. ✅ **Flutter calls `/api/v1/instant-detection/stop`**
4. ✅ Backend stops instant detection
5. ✅ Polling stops immediately

### Fix Location
The fix needs to be added wherever the stream stop button is handled. Based on Flutter logs:
```dart
🛑 Stopping stream for camera: usb_camera_0 (before setState)
```

**File to Find**: Search for "Stopping stream for camera" in Flutter codebase
**Required Addition**:
```dart
// BEFORE stopping stream, stop instant detection first
await cameraService.stopInstantDetection(widget.cameraId);

// THEN stop stream
setState(() {
  _isStreaming = false;
});
```

### Backend Endpoint (Already Exists)
```python
# ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py:168
@router.post("/stop")
async def stop_instant_detection(
    manager: InstantDetectionSampler = Depends(get_instant_detection_manager)
) -> Dict:
    """Stop instant detection sampling"""
    manager.stop_sampling()
    return {"success": True, "message": "Instant detection stopped"}
```

### Frontend Implementation Needed
Add to camera service (e.g., `camera_service.dart` or `enhanced_camera_service.dart`):

```dart
Future<Map<String, dynamic>?> stopInstantDetection(String cameraId) async {
  try {
    final response = await _gatewayClient.post(
      '/api/v1/instant-detection/stop',
      options: Options(headers: _buildHeaders()),
    );
    
    print('✅ Instant detection stopped for camera: $cameraId');
    return response.data as Map<String, dynamic>?;
  } catch (e) {
    print('⚠️ Failed to stop instant detection: $e');
    return null;
  }
}
```

Then call it in the stop stream handler:
```dart
Future<void> _stopStream() async {
  print('🛑 Stopping stream for camera: ${widget.cameraId} (before setState)');
  
  // CRITICAL: Stop instant detection BEFORE stopping stream
  await _cameraService.stopInstantDetection(widget.cameraId);
  
  setState(() {
    _isStreaming = false;
  });
  
  print('✅ Stream and instant detection stopped');
}
```

---

## Issue 2: Demographics Showing "Unknown"

### Problem
Instant detection shows person count correctly but demographics display:
```dart
demographics={
  total_male: 0, total_female: 0, total_unknown_gender: 1,
  total_young: 0, total_adult: 0, total_unknown_age: 1
}
```

All attributes show "unknown" instead of actual age/gender.

### Root Cause Analysis

#### Backend Data Flow:
1. Vision Service detects faces ✅
2. Vision Service extracts face embeddings ✅
3. Vision Service analyzes age/gender ❌ **FAILING HERE**
4. Cameras Service aggregates demographics ✅
5. Frontend displays demographics ✅

The problem is in **step 3** - Vision Service is not extracting or is failing to extract age/gender attributes.

### Possible Causes

#### 1. DeepFace Not Analyzing Attributes
```python
# Check if analyze=True is set in face detection call
result = DeepFace.analyze(
    img_path=frame,
    actions=['age', 'gender', 'emotion'],  # Must include age and gender
    enforce_detection=False,
    detector_backend='opencv'
)
```

#### 2. Face Quality Too Low
- If face is too small, blurry, or at bad angle
- DeepFace may detect face but fail attribute analysis
- Returns face_object with no age/gender

#### 3. Model Loading Issue
- Age/gender models not loaded
- Check Vision Service startup logs for errors:
  ```
  ❌ Failed to load age detector model
  ❌ Failed to load gender detector model
  ```

### Investigation Steps

#### 1. Check Vision Service Logs
```bash
tail -f /path/to/ppl-meta-vision.log | grep -E "age|gender|attribute"
```

Look for:
- ✅ "Age detector model loaded successfully"
- ✅ "Gender detector model loaded successfully"  
- ❌ "Failed to analyze attributes"
- ❌ "Face quality too low for attributes"

#### 2. Test Direct Face Analysis
```python
from deepface import DeepFace

result = DeepFace.analyze(
    img_path="test_face.jpg",
    actions=['age', 'gender'],
    enforce_detection=False
)

print(f"Age: {result[0]['age']}")
print(f"Gender: {result[0]['dominant_gender']}")
```

#### 3. Check Instant Detection Response Structure
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8005/api/v1/instant-detection/results/usb_camera_0" | python3 -m json.tool
```

Look for:
```json
{
  "person_objects": [
    {
      "face_object": {
        "age": null,  // ❌ Should be number
        "gender": null,  // ❌ Should be "Man" or "Woman"
        "dominant_emotion": "happy"
      }
    }
  ]
}
```

### Fix Options

#### Option 1: Verify DeepFace Actions
**File**: `ppl-meta-vision/src/services/face_detection_service.py` or equivalent

Ensure face analysis includes age/gender:
```python
result = DeepFace.analyze(
    img_path=frame,
    actions=['age', 'gender', 'emotion', 'race'],  # ALL actions
    enforce_detection=False,
    detector_backend='opencv'
)

# Extract attributes
age = result[0].get('age', None)
gender = result[0].get('dominant_gender', 'Unknown')

# Store in face_object
face_object = {
    "age": age,
    "gender": gender,
    "emotion": result[0].get('dominant_emotion', 'Unknown')
}
```

#### Option 2: Lower Quality Threshold
If faces are detected but attributes fail due to quality:
```python
# Allow attribute extraction even for lower quality faces
try:
    result = DeepFace.analyze(
        img_path=face_region,
        actions=['age', 'gender'],
        enforce_detection=False,  # Don't fail if face not detected
        detector_backend='skip'    # Skip re-detection, use existing face
    )
except Exception as e:
    # Fallback: Return face with "unknown" attributes
    logger.warning(f"Failed to extract attributes: {e}")
    result = [{'age': None, 'dominant_gender': 'Unknown'}]
```

#### Option 3: Enable Attribute Analysis in Instant Detection
**File**: `ppl-meta-cameras/src/services/instant_detection_sampler.py`

Ensure instant detection requests attribute analysis:
```python
vision_request = {
    "frame": base64_frame,
    "analyze_attributes": True,  # CRITICAL FLAG
    "include_demographics": True
}

response = await vision_service.detect_faces(vision_request)
```

### Verification Steps

After implementing fix:

1. **Restart Vision Service**:
   ```bash
   pkill -f "ppl-meta-vision"
   cd ppl-meta-vision && python src/main.py
   ```

2. **Restart Cameras Service**:
   ```bash
   pkill -f "ppl-meta-cameras.*uvicorn"
   cd ppl-meta-cameras && uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload
   ```

3. **Test Instant Detection**:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8005/api/v1/instant-detection/results/usb_camera_0" | \
     python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Age: {d['person_objects'][0]['face_object'].get('age', 'MISSING')}, Gender: {d['person_objects'][0]['face_object'].get('gender', 'MISSING')}\")"
   ```

4. **Check Flutter UI**:
   - Should show age badges (👶 Young / 👨 Adult)
   - Should show gender badges (♂️ Male / ♀️ Female)

---

## Quick Fix Summary

### Issue 1 Fix (Polling Continues):
```dart
// Add to camera stop handler:
await cameraService.stopInstantDetection(widget.cameraId);
```

### Issue 2 Fix (Demographics Unknown):
```python
# Verify in Vision Service face detection:
result = DeepFace.analyze(
    img_path=frame,
    actions=['age', 'gender', 'emotion'],  # Include age and gender
    enforce_detection=False
)

# Ensure attributes are extracted and stored in response
face_object = {
    "age": result[0].get('age'),
    "gender": result[0].get('dominant_gender'),
    "confidence": result[0].get('gender', {}).get('Man', 0)
}
```

---

## Testing Checklist

After fixes:

- [ ] Start stream → instant detection starts automatically
- [ ] Click stop stream → **instant detection stops immediately**
- [ ] Terminal logs → **no more polling after stop**
- [ ] Demographics → **shows actual age/gender, not "unknown"**
- [ ] UI badges → **👨 Adult ♂️ Male** appear correctly
- [ ] Multiple people → **demographics aggregate correctly**

---

## Related Files

### Frontend:
- `ppl-meta-frontend/lib/widgets/camera/instant_detection_widget.dart` - Display widget
- `ppl-meta-frontend/lib/services/camera_service.dart` - API calls
- Camera card/stream widget (need to find exact file with stop handler)

### Backend:
- `ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py:168` - Stop endpoint
- `ppl-meta-cameras/src/services/instant_detection_sampler.py` - Detection manager
- `ppl-meta-vision/src/services/face_detection_service.py` - Age/gender analysis
- `ppl-meta-gateway/src/api/v1/router.py:915` - Proxy logging

---

## Next Steps

1. ✅ Find Flutter camera stop handler (search for "Stopping stream for camera")
2. ✅ Add `stopInstantDetection()` call before stopping stream
3. ✅ Check Vision Service face analysis includes age/gender actions
4. ✅ Test demographics return actual values instead of "unknown"
5. ✅ Verify terminal logs stop when clicking stop button
6. ✅ Commit as version 2.19.77
