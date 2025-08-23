# Known Issues and Solutions

This document tracks known issues encountered in the PPL Meta Platform and their resolutions for future reference.

## Authentication Issues in Flutter Frontend

### Issue Description

**Date Identified:** August 13, 2025  
**Severity:** High  
**Components Affected:** Flutter Frontend, Authentication Flow  

**Problem Summary:**

- User authentication was successful (login returning valid JWT tokens)
- Tokens were being stored correctly in secure storage
- However, user profile data was not displaying on home and profile screens after login
- Users appeared to be logged in but with no visible profile information

**Symptoms:**

1. Login API calls returned successful responses with valid JWT tokens
2. Token storage was working correctly
3. User profile data was not being fetched after successful login
4. Home and profile screens showed authenticated state but no user details
5. Manual API calls to profile endpoints worked correctly

### Root Cause Analysis

The issue was traced to multiple configuration and implementation problems:

1. **API Configuration Mismatch**
   - Frontend was configured to call backend services directly
   - Should have been routing through the Gateway service for proper load balancing and routing

2. **Incomplete Authentication Flow**
   - Login process was only storing the JWT token
   - Missing step to fetch user profile data after successful authentication

3. **Model Import Conflicts**
   - Duplicate `AuthResponse` models created compilation issues
   - Flutter cache retained references to deleted files

### Resolution Steps

#### 1. Fix API Configuration

**File:** `ppl-meta-frontend/assets/config/env.development.json`

**Before:**

```json
{
  "API_BASE_URL": "http://localhost",
  "NODE_SERVICE_URL": "http://localhost:8001",
  "MEDIA_SERVICE_URL": "http://localhost:8000",
  "GATEWAY_SERVICE_URL": "http://localhost:8080",
  "ORCHESTRATOR_SERVICE_URL": "http://localhost:8002"
}
```

**After:**

```json
{
  "API_BASE_URL": "http://localhost:8080",
  "NODE_SERVICE_URL": "http://localhost:8080",
  "MEDIA_SERVICE_URL": "http://localhost:8080",
  "GATEWAY_SERVICE_URL": "http://localhost:8080",
  "ORCHESTRATOR_SERVICE_URL": "http://localhost:8080"
}
```

**Rationale:** All API calls should route through the Gateway service (port 8080) rather than calling individual services directly.

#### 2. Enhanced Authentication Flow

**File:** `ppl-meta-frontend/lib/core/providers/auth_provider.dart`

**Added user profile fetching after successful login:**

```dart
Future<void> login(String email, String password) async {
  try {
    state = state.copyWith(isLoading: true, error: null);
    
    final authResponse = await _authService.login(email, password);
    
    // Store the token
    await _authService.setToken(authResponse.accessToken);
    
    // Fetch user profile after successful login
    final user = await _authService.getCurrentUser();
    
    state = state.copyWith(
      isLoading: false,
      user: user,
      isAuthenticated: true,
    );
  } catch (e) {
    state = state.copyWith(
      isLoading: false,
      error: e.toString(),
      isAuthenticated: false,
    );
    rethrow;
  }
}
```

**Key Changes:**

- Added `getCurrentUser()` call after token storage
- Ensures user profile data is loaded immediately after login
- Updates authentication state with complete user information

#### 3. Model Cleanup

**Issue:** Duplicate `AuthResponse` models caused import conflicts

**Resolution:**

- Removed duplicate `auth_response.dart` file
- Used existing `AuthResponse` model from `user.dart`
- Updated imports to reference the correct model location
- Cleared Flutter cache to resolve compilation issues

### Verification Steps

1. **Backend Health Check:**

   ```bash
   curl -X POST "http://localhost:8080/api/v1/auth/login" \
   -H "Content-Type: application/json" \
   -d '{"email":"fresh.user@example.com","password":"NewPassword234!"}'
   ```

2. **Profile Endpoint Test:**

   ```bash
   curl -X GET "http://localhost:8080/api/v1/auth/me" \
   -H "Authorization: Bearer <jwt_token>"
   ```

3. **Flutter Frontend Test:**
   - Login with test credentials
   - Verify user profile displays on home screen
   - Check profile screen shows complete user information
   - Confirm authentication persists across app sessions

### Prevention Measures

1. **Configuration Management:**
   - Always route API calls through the Gateway service
   - Maintain consistent environment configurations
   - Document API routing architecture

2. **Authentication Flow:**
   - Implement complete authentication workflows that fetch all required user data
   - Test authentication state management thoroughly
   - Verify token storage and retrieval mechanisms

3. **Development Practices:**
   - Clear Flutter cache when removing files (`flutter clean`)
   - Avoid duplicate model definitions
   - Use centralized model exports from single source files

4. **Testing Protocol:**
   - Test authentication flow end-to-end in development
   - Verify both backend API endpoints and frontend integration
   - Validate user data persistence and display

### Related Files Modified

- `ppl-meta-frontend/assets/config/env.development.json`
- `ppl-meta-frontend/lib/core/providers/auth_provider.dart`
- `ppl-meta-frontend/lib/core/services/auth_service.dart`
- `ppl-meta-frontend/lib/core/models/user.dart`

### Test Credentials Used

- **Email:** `fresh.user@example.com`
- **Password:** `NewPassword234!`

---

## Future Issue Tracking

When adding new issues to this document:

1. Include date identified and severity level
2. Provide clear problem description and symptoms
3. Document root cause analysis
4. List all resolution steps with code examples
5. Include verification procedures
6. Add prevention measures for similar issues

---

## Multi-Select Media Organization Missing Features

### Problem Description

**Date Identified:** August 13, 2025  
**Severity:** Medium  
**Components Affected:** Flutter Frontend, Collections Management, Media Gallery  

**Problem Summary:**

The CAM-FLUTTER-004D (Collection Organization) implementation is missing key user experience features for multi-selecting media and organizing them into collections. While the technical foundation exists, the user journey and UI components are incomplete.

**Missing Features:**

1. **Multi-Select UI in Gallery**: No visual way to enter selection mode and select multiple media items
2. **Collection Creation from Media**: Missing user interface to create new collections from selected camera media  
3. **Professional Workflows**: No "Security Events" collection creation from multiple cameras
4. **Bulk Organization Actions**: Limited bulk operation UI and confirmation dialogs

### Current Implementation Status

**✅ Existing Infrastructure:**

- `ResponsiveMediaGallery` has `enableSelection` parameter
- `CollectionOrganizationWidget` exists for moving media between collections
- `MediaOrganizationService` supports bulk operations
- Selection state management is implemented

**❌ Missing User Experience:**

- No way to enter multi-select mode from the gallery UI
- No "Select" button or long-press to start selection
- No action bar when items are selected
- No workflow for creating collections from selected media
- No "Security Events" or professional workflow templates

### Implementation Plan

#### 1. Enhanced Gallery Selection UI

**Required Changes to `ResponsiveMediaGallery`:**

```dart
// Add to ResponsiveMediaGallery widget
final bool showSelectionToggle;
final Function()? onEnterSelectionMode;
final Function(List<MediaItem>)? onOrganizeSelected;

// Add selection mode toggle button
Widget _buildSelectionToggleButton() {
  return FloatingActionButton.extended(
    onPressed: () {
      setState(() {
        _isSelectionMode = !_isSelectionMode;
        if (!_isSelectionMode) {
          _clearSelection();
        }
      });
      widget.onEnterSelectionMode?.call();
    },
    label: Text(_isSelectionMode ? 'Cancel' : 'Select'),
    icon: Icon(_isSelectionMode ? Icons.close : Icons.check_box),
  );
}

// Enhanced selection bar with organization actions
Widget _buildEnhancedSelectionBar() {
  return Container(
    padding: const EdgeInsets.all(AppSpacing.md),
    child: Row(
      children: [
        Text('${_selectedItems.length} selected'),
        const Spacer(),
        ElevatedButton.icon(
          onPressed: () => widget.onOrganizeSelected?.call(selectedItems),
          icon: const Icon(Icons.folder_open),
          label: const Text('Organize'),
        ),
        // Add to collection, Create collection, etc.
      ],
    ),
  );
}
```

#### 2. Collection Creation Workflow

**New Widget: `CreateCollectionFromMediaDialog`:**

```dart
class CreateCollectionFromMediaDialog extends StatefulWidget {
  final List<MediaItem> selectedMedia;
  final Function(String name, String description) onCreateCollection;
  
  // Professional workflow templates
  static const List<CollectionTemplate> templates = [
    CollectionTemplate(
      name: 'Security Events',
      description: 'Important security footage and snapshots',
      icon: Icons.security,
      color: Colors.red,
    ),
    CollectionTemplate(
      name: 'Daily Monitoring',
      description: 'Regular monitoring snapshots',
      icon: Icons.schedule,
      color: Colors.blue,
    ),
    CollectionTemplate(
      name: 'Motion Alerts',
      description: 'Motion detection triggers',
      icon: Icons.motion_photos_on,
      color: Colors.orange,
    ),
  ];
}
```

#### 3. Professional Workflow Templates

**Security Events Workflow:**

1. User selects media from multiple cameras
2. Clicks "Organize" → "Create Collection"
3. Template selector shows "Security Events" option
4. Auto-populates name and description
5. Creates collection and moves all selected media

**Multi-Camera Workflow:**

1. Filter gallery to show multiple camera collections
2. Select media from different cameras (cross-collection selection)
3. Create unified collection from diverse sources
4. Professional naming conventions and metadata

#### 4. User Journey Implementation

**Gallery → Selection Mode:**

```text
1. User views gallery (camera or regular collection)
2. Long-press on media item OR tap "Select" button
3. Gallery enters selection mode with checkboxes
4. User selects multiple items
5. Action bar appears with "Organize" button
6. Organize → Options: "Move to Collection", "Create New Collection"
```

**Create Collection from Media:**

```text
1. User selects media items
2. Taps "Organize" → "Create New Collection"  
3. Dialog shows templates (Security Events, Daily Monitoring, etc.)
4. User picks template or creates custom
5. Collection created and media moved automatically
6. Success confirmation with navigation to new collection
```

### Implementation Steps

#### Phase 1: Enhanced Selection UI

- [ ] Add selection mode toggle to gallery screens
- [ ] Implement long-press to enter selection mode
- [ ] Enhanced selection bar with organization actions
- [ ] Visual feedback for selected items

#### Phase 2: Collection Creation Workflow

- [ ] Create `CreateCollectionFromMediaDialog` widget
- [ ] Professional workflow templates implementation
- [ ] Integration with existing `MediaOrganizationService`
- [ ] Success/error handling and user feedback

#### Phase 3: Multi-Camera Professional Workflows

- [ ] Cross-collection media selection
- [ ] "Security Events" collection template
- [ ] Metadata enhancement for professional collections
- [ ] Batch operation progress indicators

### Success Criteria

- [ ] **Gallery Selection**: Long-press or button to enter selection mode
- [ ] **Multi-Select UI**: Checkboxes and selection counter
- [ ] **Organization Actions**: "Move to Collection" and "Create Collection" buttons
- [ ] **Collection Templates**: Pre-defined templates for professional workflows
- [ ] **Security Events**: Template specifically for multi-camera security footage
- [ ] **Progress Feedback**: Loading indicators for bulk operations
- [ ] **Success Navigation**: Auto-navigate to newly created collections

### Priority Justification

This completes the camera-owned collections architecture by providing the missing user experience layer for professional media organization workflows.

---

**Last Updated:** August 13, 2025
