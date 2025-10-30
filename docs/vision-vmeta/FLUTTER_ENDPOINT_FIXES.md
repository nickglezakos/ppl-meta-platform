# Flutter Endpoint Fixes for Phase 5 & 6
**Date:** October 29, 2025  
**Status:** ✅ FIXED

## Overview
Fixed Flutter frontend API calls to match the Phase 5 & 6 backend endpoint implementations. The Flutter app had incorrect URL paths that would have caused 404 errors.

## Issues Found & Fixed

### **Phase 5: Get Session Individuals List**

#### ❌ **Before (INCORRECT)**
```dart
final response = await _apiClient.get(
  '/api/v1/vmeta/cross-video/individuals/tracking/sessions/$sessionUuid/individuals',
);
```

**Problems:**
- Had `/vmeta/` in the path which doesn't exist in Gateway routes
- Would result in 404 error

#### ✅ **After (CORRECT)**
```dart
final response = await _apiClient.get(
  '/api/v1/cross-video/individuals/tracking/sessions/$sessionUuid/individuals',
);
```

**Fixed:**
- Removed `/vmeta/` segment
- Now matches Gateway route exactly
- Will successfully proxy to vmeta service

---

### **Phase 6: Get Aggregated Individual Analysis**

#### ❌ **Before (INCORRECT)**
```dart
Future<ApiResponse<Map<String, dynamic>>> getIndividualAggregatedAnalysis({
  required String individualUuid,
}) async {
  try {
    final response = await _apiClient.get(
      '/api/v1/vmeta/cross-video/individuals/$individualUuid/aggregated-analysis',
    );
```

**Problems:**
1. Had `/vmeta/` in the path which doesn't exist
2. Missing `/tracking/individuals/` segment in the path
3. Missing required `session_uuid` query parameter
4. Would result in 404 error

#### ✅ **After (CORRECT)**
```dart
Future<ApiResponse<Map<String, dynamic>>> getIndividualAggregatedAnalysis({
  required String individualUuid,
  required String sessionUuid,
}) async {
  try {
    final response = await _apiClient.get(
      '/api/v1/cross-video/individuals/tracking/individuals/$individualUuid/aggregated-analysis?session_uuid=$sessionUuid',
    );
```

**Fixed:**
1. Removed `/vmeta/` segment
2. Added `/tracking/individuals/` segment to match Gateway route
3. Added `sessionUuid` parameter (required for session filtering)
4. Added `session_uuid` query parameter to URL
5. Now matches Gateway route exactly

---

## Calling Code Updates

### **Phase 6 Call Site Fixed**

#### ❌ **Before (INCORRECT)**
```dart
// In person_objects_detail_screen.dart
final response = await mediaApiClient.getIndividualAggregatedAnalysis(
  individualUuid: individualUuid,
  // Missing sessionUuid parameter!
);
```

#### ✅ **After (CORRECT)**
```dart
// In person_objects_detail_screen.dart
final response = await mediaApiClient.getIndividualAggregatedAnalysis(
  individualUuid: individualUuid,
  sessionUuid: context.sessionUuid,  // ✅ Now passes session UUID
);
```

---

## Backend Endpoint Reference

For reference, here are the correct Gateway routes that Flutter now matches:

### Gateway Routes (`ppl-meta-gateway/src/api/v1/router.py`)

```python
# Phase 5: Get individuals list from tracking session
@api_router.get("/cross-video/individuals/tracking/sessions/{session_uuid}/individuals")
async def get_session_individuals(request: Request):
    """Proxy request to get individuals list from tracking session to vmeta service."""
    return await _proxy_to_vmeta_service(request)

# Phase 6: Get aggregated analysis for individual
@api_router.get("/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis")
async def get_individual_aggregated_analysis(request: Request):
    """Proxy request to get aggregated individual analysis to vmeta service."""
    return await _proxy_to_vmeta_service(request)
```

### vmeta Service Routes (`ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`)

```python
# Router prefix: /individuals/tracking
# App prefix: /api/v1/cross-video

# Phase 5 (line ~858)
@router.get("/sessions/{session_uuid}/individuals")
async def get_session_individuals(session_uuid, http_request):
    # Full path: /api/v1/cross-video/individuals/tracking/sessions/{uuid}/individuals
    ...

# Phase 6 (line ~952)
@router.get("/individuals/{individual_uuid}/aggregated-analysis")
async def get_individual_aggregated_analysis(individual_uuid, session_uuid, http_request):
    # Full path: /api/v1/cross-video/individuals/tracking/individuals/{uuid}/aggregated-analysis
    # Requires session_uuid as query parameter
    ...
```

---

## Complete URL Structure

### **Phase 5 URL Breakdown**
```
/api/v1/cross-video/individuals/tracking/sessions/{session_uuid}/individuals
│       │                                        │
│       │                                        └─ vmeta router path
│       └─ App prefix (cross-video)
└─ API version
```

### **Phase 6 URL Breakdown**
```
/api/v1/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis?session_uuid={session_uuid}
│       │                                                                                   │
│       │                                                                                   └─ Query param (required!)
│       └─ App prefix + vmeta router path
└─ API version
```

---

## Testing Instructions

### **Test Phase 5:**
```dart
// Create a tracking session first
final sessionResponse = await mediaApiClient.createCrossVideoTrackingSession(
  collectionName: 'usb_camera_0',
  startTime: DateTime(2025, 10, 13, 8, 6),
  endTime: DateTime(2025, 10, 29, 8, 6),
);

final sessionUuid = sessionResponse.data!['session_uuid'];

// Wait for completion, then get individuals
final individualsResponse = await mediaApiClient.getCrossVideoIndividuals(
  sessionUuid: sessionUuid,
);

// Should return list of individuals with metadata
print('Total individuals: ${individualsResponse.data!['total_individuals']}');
```

### **Test Phase 6:**
```dart
// Use individual UUID from Phase 5 response
final individualUuid = individualsResponse.data!['individuals'][0]['individual_uuid'];

final analysisResponse = await mediaApiClient.getIndividualAggregatedAnalysis(
  individualUuid: individualUuid,
  sessionUuid: sessionUuid,  // ✅ Required parameter
);

// Should return detailed analysis with appearances
print('Total appearances: ${analysisResponse.data!['total_appearances']}');
print('Unique videos: ${analysisResponse.data!['unique_videos']}');
```

---

## Files Modified

### Flutter Frontend
1. **`ppl-meta-frontend/lib/services/media_api_client.dart`**
   - Fixed Phase 5 URL (removed `/vmeta/`)
   - Fixed Phase 6 URL (removed `/vmeta/`, added `/tracking/individuals/`)
   - Added `sessionUuid` parameter to Phase 6 function
   - Added `session_uuid` query parameter to Phase 6 request

2. **`ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`**
   - Updated Phase 6 call to pass `sessionUuid` from context
   - Now properly filters individual data by session

---

## Expected Responses

### **Phase 5 Response:**
```json
{
  "session_uuid": "7ca4b041-b795-461e-89b9-c9be8a7b1945",
  "total_individuals": 7,
  "individuals": [
    {
      "individual_uuid": "2a7b51e5-3a30-4da3-984e-ac4fde008bc3",
      "individual_id": "ind_2a7b51e5",
      "total_appearances": 2,
      "total_videos": 2,
      "first_seen": "2025-10-13T08:06:00",
      "last_seen": "2025-10-29T08:06:30",
      "confidence_score": 0.85
    }
    // ... more individuals
  ]
}
```

### **Phase 6 Response:**
```json
{
  "individual_uuid": "2a7b51e5-3a30-4da3-984e-ac4fde008bc3",
  "individual_id": "ind_2a7b51e5",
  "session_uuid": "7ca4b041-b795-461e-89b9-c9be8a7b1945",
  "total_appearances": 2,
  "unique_videos": 2,
  "first_seen": "2025-10-13T08:06:00",
  "last_seen": "2025-10-29T08:06:30",
  "total_duration_seconds": 1382430.0,
  "average_confidence": 0.85,
  "appearances": [
    {
      "individual_uuid": "2a7b51e5-3a30-4da3-984e-ac4fde008bc3",
      "video_uuid": "7b462847-cd1f-441a-8bd9-aaed6643b7cb",
      "person_object_uuid": "dfaa2f0d-9071-485a-ae68-daf1481f7ef3",
      "start_timestamp": "2025-10-13T08:06:00",
      "end_timestamp": "2025-10-13T08:06:30",
      "entry_bbox": [100.0, 200.0, 150.0, 300.0],
      "exit_bbox": [110.0, 210.0, 160.0, 310.0],
      "confidence_score": 0.85
    }
    // ... more appearances
  ],
  "person_object_uuids": [
    "dfaa2f0d-9071-485a-ae68-daf1481f7ef3",
    "e68da561-d778-4969-b3af-b90a51d47699"
  ],
  "analysis_timestamp": "2025-10-29T10:43:21.273731+00:00"
}
```

---

## Summary

✅ **All Flutter endpoint URLs now match backend implementation**
✅ **Phase 5 endpoint will work correctly**
✅ **Phase 6 endpoint will work correctly with proper session filtering**
✅ **Ready for Flutter testing with cached session `7ca4b041-b795-461e-89b9-c9be8a7b1945`**

The Flutter app is now fully aligned with the backend Phase 5 & 6 implementation and ready for testing! 🎉
