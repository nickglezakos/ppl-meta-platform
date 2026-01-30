# Bug Fix: Auth Token Lost When Accessing Corrupted Media

## Issue Description

When a user accessed a corrupted or unavailable media file at `http://localhost:3000/#/collections`, and then tapped the "back" button, they would lose their authentication token. This prevented them from accessing other collections and routes, requiring them to log in again.

### Error Symptoms

1. User accesses corrupted media file
2. Video player shows error: `PlatformException(MEDIA_ERR_SRC_NOT_SUPPORTED, No further diagnostic information...)`
3. User taps "back" button
4. User is unable to access other collections
5. Console shows: `⚠️ ApiClient: NO AUTH TOKEN for GET /api/v1/...`

## Root Cause Analysis

The bug was caused by overly aggressive token clearing in the `ApiClient` error interceptor:

### Before (Buggy Code)
```dart
onError: (error, handler) async {
  if (error.response?.statusCode == 401) {
    // Token expired, clear it but don't auto-logout here
    _authToken = null;  // ❌ CLEARS TOKEN ON ANY 401!
    print('🔓 ApiClient: Token cleared due to 401 response');
  }
  handler.next(error);
}
```

### Problem Flow
1. User tries to access corrupted media or makes paginated request
2. Server returns 401 or **403 with "Not authenticated"** message
3. ApiClient interceptor catches error and **clears the auth token**
4. User navigates or continues browsing
5. Router/subsequent requests find **no token**
6. User loses access to protected routes

**Critical Discovery:** The bug occurred with both:
- **401 errors** (Unauthorized)
- **403 errors** with authentication messages like "Not authenticated"

The server sometimes returns 403 instead of 401 for authentication failures, which was not being handled.

## Solution

### Fix 1: Smart Token Clearing & Auto-Restoration in ApiClient

Modified the error interceptor to intelligently clear tokens based on multiple factors, **AND** automatically restore tokens from storage when they're missing:

**Key Innovation:** Auto-restore token from storage on each request if missing

```dart
onRequest: (options, handler) async {
  // If no token, try to restore from storage
  if (_authToken == null && _ref != null) {
    try {
      final authService = _ref!.read(authServiceProvider);
      final storedToken = await authService.getToken();
      if (storedToken != null && !JwtDecoder.isExpired(storedToken)) {
        _authToken = storedToken;
        print('🔄 ApiClient: Restored token from storage');
      }
    } catch (e) {
      print('⚠️ ApiClient: Failed to restore token from storage');
    }
  }
  
  if (_authToken != null) {
    options.headers['Authorization'] = 'Bearer $_authToken';
  }
  handler.next(options);
}
```

And smart token clearing:
- **Handles both 401 AND 403 errors** with authentication messages
- JWT expiration check
- Authentication endpoint detection
- Server error message analysis

**File:** [ppl-meta-frontend/lib/core/api/api_client.dart](ppl-meta-frontend/lib/core/api/api_client.dart#L26-L49)

### Fix 2: Resilient Auth State Management

Improved the `AuthNotifier.checkAuth()` method to not automatically set state to unauthenticated on temporary network errors:

```dart
Future<void> checkAuth() async {
  try {
    final token = await _authService.getToken();
    if (token == null) {
  # Fix 3: Prevent setState After Dispose

Added mounted checks in `SmartVideoPlayerWidget` to prevent setState calls after the widget has been disposed:

```dart
if (mounted) {
  setState(() {
    _storedFaceData = faces;
    _faceDataSource = 'enhanced_logic_v2_api';
    _isLoadingFaces = false;
  });
}
```

This prevents the error: `setState() called after dispose()` when async operations complete after navigation.

**File:** [ppl-meta-frontend/lib/widgets/smart_video_player_widget.dart](ppl-meta-frontend/lib/widgets/smart_video_player_widget.dart#L939-L959)

##    state = const AuthState.unauthenticated();
      return;
    }

    final user = await _authService.getCurrentUser();
    if (user != null) {
      state = AuthState.authenticated(user);
    } else {
      // Check if token still exists - might be temporary network issue
      final tokenAfterCheck = await _authService.getToken();
      if (tokenAfterCheck != null && state.isAuthenticated) {
        // Keep current state - don't lose auth on temporary errors
        return;
      }
      state = const AuthState.unauthenticated();
    }
  } catch (e) {
    // Don't automatically set to unauthenticated on errors
    final token = await _authService.getToken();
    if (token != null && state.isAuthenticated) {
      // Keep authenticated state on network errors
      return;
    }
    state = const AuthState.unauthenticated();
  }
}
```

**File:** [ppl-meta-frontend/lib/core/providers/auth_provider.dart](ppl-meta-frontend/lib/core/providers/auth_provider.dart#L95-L127)

## Testing

### Test Case 1: Corrupted Media
1. Navigate to `/collections`
2. Click on a corrupted/unavailable media item
3. Observe video error: `MEDIA_ERR_SRC_NOT_SUPPORTED`
4. Click "back" button
5. ✅ **Expected:** User can still access collections and other routes
6. ✅ **Expected:** Auth token is preserved

### Test Case 2: Actual Token Expiration
1. Login with valid credentials
2. Wait for token to expire (or manually expire it)
3. Try to access `/users/profile` or paginated media list
4. ✅ **Expected:** 401/403 error clears token and redirects to login
5. ✅ **Expected:** Proper logout behavior

### Test Case 3: 403 "Not Authenticated" Error
1. Login successfully
2. Access paginated collection (e.g., page 2 of media search)
3. Receive 403 with `{"detail":"Not authenticated"}`
4. ✅ **Expected:** Token cleared and user redirected to login
5. ✅ **Expected:** No cascading "NO AUTH TOKEN" errors

### Test Case 4: 403 "Not Authenticated" Error
1. Login successfully
2. Access paginated collection (e.g., page 2 of media search)
3. Receive 403 with `{"detail":"Not authenticated"}`
4. ✅ **Expected:** Token cleared and user redirected to login
5. ✅ **Expected:** No cascading "NO AUTH TOKEN" errors

### Test Case 3: Network Errors
1. Login successfully
2. Disconnect network
3. Navigate between pages
4. ✅ **Expected:** Auth state preserved despite network errors
5. Reconnect network
6. ✅ **Expected:** App continues working with same auth token
mart token clearing with JWT expiration check
2. `ppl-meta-frontend/lib/core/providers/auth_provider.dart` - Resilient auth state management
3. `ppl-meta-frontend/lib/widgets/smart_video_player_widget.dart` - Fixed setState after dispos

### Before Fix
- ❌ Users lost authentication when accessing corrupted media
- ❌ Required re-login after every media error
- ❌ Poor user experience
- ❌ False positive "session expired" behavior

### After Fix
- ✅ Users maintain authentication despite media errors
- ✅ Only logout on actual auth failures
- ✅ Improved user experience
- ✅ Resilient to temporary network issues
- ✅ Proper distinction between resource errors and auth errors

## Files Modified

1. `ppl-meta-frontend/lib/core/api/api_client.dart` - Selective token clearing
2. `ppl-meta-frontend/lib/core/providers/auth_provider.dart` - Resilient auth state

## Related Issues

- Video player errors: See [video_player_widget.dart](ppl-meta-frontend/lib/widgets/video_player_widget.dart)
- Media preview navigation: See [media_preview_screen.dart](ppl-meta-frontend/lib/screens/media_preview_screen.dart)
- Collections routing: See [app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart)

## Deployment Notes

- No database migrations required
- No API changes required
- Frontend-only fix
- Sa**Token automatically restored from storage if cleared temporarily**
- ✅ Only logout on actual auth failures
- ✅ Improved user experience
- ✅ Resilient to temporary network issues
- ✅ Proper distinction between resource errors and auth errors
- ✅ **Handles auth state/ApiClient disconnect gracefully**

**Fixed on:** 30 January 2026  
**Version:** v2.23.2  
**Author:** GitHub Copilot
