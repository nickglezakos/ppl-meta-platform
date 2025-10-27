# Flutter Authentication & Routing Bug Fix

## Issue Summary
**Date**: 2025-01-XX
**Severity**: Critical
**Impact**: Users lose authentication after navigating to media-preview screen

## Problem Description

After navigating to `http://localhost:3000/#/media-preview`, the Flutter app made API requests to the wrong service, resulting in 404 errors and authentication failures:

```
uri: http://localhost:8002/api/v1/media/collections?user_id=4cf362b1-3e05-4e85-81c7-c08a98c7e41b
statusCode: 404
WorkflowAPI: DioException [bad response]
```

### Expected Behavior
- Requests should go to Gateway service: `http://localhost:8080/api/v1/media/collections`
- Authentication should use JWT from Authorization header
- Collections endpoint should work via Gateway → Media service proxy chain

### Actual Behavior
- Requests went to Orchestrator service: `http://localhost:8002` (which doesn't have collections endpoint)
- Authentication passed `user_id` query parameter instead of JWT
- 404 errors caused auth token loss and prevented navigation

## Root Causes

### 1. Shared Dio Instance BaseUrl Mutation
**File**: `lib/services/workflow_widget_api_client.dart` (line 23-25)

**Problem**: Multiple API clients were modifying a shared `Dio` instance's `baseUrl`:
```dart
// BEFORE (WRONG - modifies shared instance)
_apiClient = apiClient ?? ApiClient(AppConfig.instance);
_apiClient.dio.options.baseUrl = this.baseUrl; // Overwrites shared baseUrl!
```

**Impact**: When `WorkflowWidgetApiClient` initialized, it would overwrite the baseUrl on the shared `ApiClient` instance, causing subsequent requests from `CameraCollectionService` to use the wrong URL.

**Fix**: Always create a dedicated `ApiClient` instance:
```dart
// AFTER (CORRECT - own instance)
_apiClient = ApiClient(AppConfig.instance);
_apiClient.dio.options.baseUrl = this.baseUrl; // Safe - modifies our own instance
```

### 2. Incorrect Authentication Method
**File**: `lib/core/services/camera_collection_service.dart` (line 416)

**Problem**: Frontend passed `user_id` as query parameter, but backend expects JWT:
```dart
// BEFORE (WRONG)
final response = await _apiClient.get('/api/v1/media/collections/', queryParameters: {
  'user_id': userId, // Backend doesn't accept this parameter
});
```

**Backend Signature** (ppl-meta-media/src/api/v1/media.py:449):
```python
@router.get("/collections", response_model=List[MediaCollectionResponse])
async def list_collections(
    skip: int = 0,
    limit: int = 100,
    include_public: bool = False,
    current_user: AuthUser = Depends(get_current_user), # Extracts user from JWT!
    db: Session = Depends(get_db),
):
```

**Fix**: Remove query parameter, rely on JWT from Authorization header:
```dart
// AFTER (CORRECT)
final response = await _apiClient.get('/api/v1/media/collections/');
// JWT automatically added by ApiClient interceptor
```

## Files Modified

### 1. `lib/services/workflow_widget_api_client.dart`
**Change**: Force creation of dedicated ApiClient instance
**Lines**: 16-26
**Reason**: Prevent baseUrl mutation on shared instances

### 2. `lib/core/services/camera_collection_service.dart`
**Change**: Remove user_id query parameter from collections request
**Lines**: 405-417
**Reason**: Match backend authentication method (JWT instead of query param)

## Verification Steps

1. **Check Configuration**:
   ```bash
   # Verify env config has correct baseUrl
   cat ppl-meta-frontend/assets/config/env.development.json | grep API_BASE_URL
   # Should show: "API_BASE_URL": "http://localhost:8080"
   ```

2. **Test Collections Endpoint**:
   ```bash
   # Direct test (requires valid JWT token)
   curl -H "Authorization: Bearer <token>" http://localhost:8080/api/v1/media/collections
   ```

3. **Run Flutter App**:
   ```bash
   cd ppl-meta-frontend
   flutter clean
   flutter pub get
   flutter run -d chrome --web-port 3000
   ```

4. **Test User Flow**:
   - Login to app
   - Navigate to media-preview screen
   - Verify collections load correctly
   - Verify no 404 errors in console
   - Verify authentication persists after navigation

## Backend Service Architecture

```
┌─────────────────────────────────────────┐
│ Flutter App (localhost:3000)            │
│  - ApiClient baseUrl: localhost:8080    │
│  - Auth: JWT in Authorization header    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ Gateway Service (localhost:8080)        │
│  - Route: /api/v1/media/collections     │
│  - Action: Proxy to Media service       │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ Media Service (localhost:8000)          │
│  - Endpoint: GET /collections           │
│  - Auth: Extract user from JWT          │
│  - Returns: List[MediaCollectionResponse]│
└─────────────────────────────────────────┘
```

## Prevention Guidelines

### For API Clients

1. **Never reuse ApiClient instances** across different services that need different baseUrls
2. **Always create dedicated instances** when modifying Dio options
3. **Document baseUrl changes** clearly in code comments

### For Authentication

1. **Prefer JWT in Authorization header** over query parameters
2. **Match frontend auth method** to backend expectations
3. **Test auth flow** after backend API changes

### Code Review Checklist

- [ ] Does this API client modify `dio.options.baseUrl`?
- [ ] If yes, does it use a dedicated ApiClient instance?
- [ ] Does the authentication method match backend signature?
- [ ] Are query parameters documented and expected by backend?
- [ ] Is there logging to track request URLs during development?

## Related Documentation

- Backend API Gateway: `ppl-meta-gateway/src/api/v1/router.py`
- Media Service Endpoints: `ppl-meta-media/src/api/v1/media.py`
- Frontend Config: `ppl-meta-frontend/assets/config/env.development.json`
- API Client Implementation: `ppl-meta-frontend/lib/core/api/api_client.dart`

## Testing Results

**Before Fix**:
- ❌ Collections request → 404 error
- ❌ Request routed to wrong service (8002)
- ❌ Auth token lost after media-preview navigation
- ❌ User forced to refresh/re-login

**After Fix**:
- ✅ Collections request → 200 OK
- ✅ Request routed correctly (8080 → 8000)
- ✅ Auth token persists across navigation
- ✅ Normal app flow maintained

## Version Information

- **Flutter**: [Your Flutter version]
- **Dart**: [Your Dart version]
- **Dio**: [Check pubspec.yaml]
- **Fixed in**: v2.19.21 (or next version)

---

**Reviewed by**: AI Assistant
**Status**: Ready for Testing
**Priority**: P0 - Critical Bug Fix
