# Collections Screen API Fix
## Version 2.19.84 - Compilation Error Resolution

### Issue
**Error:** `No named parameter with the name 'body'`  
**Location:** `collections_screen.dart:926`  
**Cause:** Used incorrect parameter name `body` instead of `data` for `ApiClient.post()` method

### Root Cause Analysis
The `ApiClient.post()` method signature is:
```dart
Future<Response<T>> post<T>(
  String path, {
  dynamic data,  // ← Correct parameter name
  Map<String, dynamic>? queryParameters,
  Options? options,
}) async
```

The code incorrectly used:
```dart
await apiClient.post(
  '/api/v1/mvr-people/merge/hierarchical',
  body: {  // ❌ WRONG - No such parameter
    'mvr_uuids': mvrPersonUuids,
    ...
  },
);
```

### Solution
Changed `body:` to `data:` to match the `ApiClient.post()` method signature:

```dart
await apiClient.post(
  '/api/v1/mvr-people/merge/hierarchical',
  data: {  // ✅ CORRECT
    'mvr_uuids': mvrPersonUuids,
    'similarity_threshold': 0.70,
    'min_similarity_check': 0.50,
  },
);
```

### Changes Made

**File:** `collections_screen.dart`  
**Lines:** 920-935  

**Before:**
```dart
final apiClient = ref.read(apiClientProvider);

final mergeResponse = await apiClient.post(
  '/api/v1/mvr-people/merge/hierarchical',
  body: {  // ❌ Error: No named parameter 'body'
    'mvr_uuids': mvrPersonUuids,
    'similarity_threshold': 0.70,
    'min_similarity_check': 0.50,
  },
);

if (!mergeResponse.success) {  // ❌ Response doesn't have .success
  throw Exception('Hierarchical merge failed: ${mergeResponse.error}');
}
```

**After:**
```dart
final apiClient = ref.read(apiClientProvider);

final mergeResponse = await apiClient.post(
  '/api/v1/mvr-people/merge/hierarchical',
  data: {  // ✅ Correct parameter name
    'mvr_uuids': mvrPersonUuids,
    'similarity_threshold': 0.70,
    'min_similarity_check': 0.50,
  },
);

if (mergeResponse.statusCode != 200) {  // ✅ Correct status check
  throw Exception('Hierarchical merge failed: ${mergeResponse.statusMessage}');
}
```

### Additional Corrections

**Response Handling:**
- Changed from `mergeResponse.success` (doesn't exist) to `mergeResponse.statusCode != 200`
- Changed from `mergeResponse.error` to `mergeResponse.statusMessage`

**API Client Usage:**
- Correctly use `ref.read(apiClientProvider)` to get ApiClient instance
- No need for MediaApiClient wrapper for simple POST requests
- ApiClient.post() returns Dio Response<T> object

### API Client Reference

**Class:** `ApiClient` (`lib/core/api/api_client.dart`)  
**Provider:** `apiClientProvider`  

**Available Methods:**
```dart
// GET request
Future<Response<T>> get<T>(String path, {
  Map<String, dynamic>? queryParameters,
  Options? options,
})

// POST request
Future<Response<T>> post<T>(String path, {
  dynamic data,  // ← Use this parameter
  Map<String, dynamic>? queryParameters,
  Options? options,
})

// PUT request
Future<Response<T>> put<T>(String path, {
  dynamic data,
  Map<String, dynamic>? queryParameters,
  Options? options,
})

// DELETE request
Future<Response<T>> delete<T>(String path, {
  dynamic data,
  Map<String, dynamic>? queryParameters,
  Options? options,
})
```

### Response Object Structure

**Type:** `dio.Response<T>`

**Key Properties:**
- `statusCode` - HTTP status code (200, 404, 500, etc.)
- `statusMessage` - HTTP status message ("OK", "Not Found", etc.)
- `data` - Response body (parsed JSON or raw data)
- `headers` - Response headers
- `requestOptions` - Original request options

**Example Usage:**
```dart
final response = await apiClient.post('/api/endpoint', data: {...});

if (response.statusCode == 200) {
  final data = response.data as Map<String, dynamic>;
  print('Success: ${data['message']}');
} else {
  print('Error: ${response.statusMessage}');
}
```

### Testing Status

✅ **Compilation:** No errors  
⏳ **Runtime:** Pending end-to-end test  
⏳ **Integration:** Pending with backend API  

### Verification Checklist

- [x] Compilation errors resolved
- [x] Parameter name corrected (`body` → `data`)
- [x] Response handling corrected (`.success` → `.statusCode`)
- [x] Error message extraction corrected (`.error` → `.statusMessage`)
- [ ] Test with real backend API endpoint
- [ ] Verify merge response format matches expectations
- [ ] Validate hierarchical merge workflow end-to-end

### Related Files

**Modified:**
- `lib/screens/collections_screen.dart` (Lines 920-935)

**Referenced:**
- `lib/core/api/api_client.dart` (ApiClient class definition)
- `lib/providers/api_providers.dart` (apiClientProvider definition)

### Notes

1. **ApiClient vs MediaApiClient:**
   - `ApiClient` - Low-level HTTP client wrapper (Dio)
   - `MediaApiClient` - High-level media-specific operations
   - For custom endpoints like MVR merge, use `ApiClient` directly

2. **Dio Response vs ApiResponse:**
   - `dio.Response<T>` - Raw Dio response with statusCode, data, etc.
   - `ApiResponse<T>` - Wrapper class with .success, .error properties
   - MediaApiClient methods return `ApiResponse<T>`
   - ApiClient methods return `dio.Response<T>`

3. **Future Enhancement:**
   - Could add `hierarchicalMergeMVR()` method to MediaApiClient
   - Would wrap the POST call and return ApiResponse<T>
   - Would provide cleaner interface: `if (response.success) { ... }`

---

**Fixed By:** GitHub Copilot  
**Date:** December 15, 2025  
**Status:** ✅ Resolved
