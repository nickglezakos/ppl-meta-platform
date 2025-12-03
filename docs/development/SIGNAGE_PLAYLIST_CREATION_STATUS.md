# Signage Playlist Creation - Development Status

**Date:** December 2, 2025  
**Session:** Phase 7 Signage Management UI - Playlist Creation Fix

---

## 🎯 Objective

Enable users to create video playlists (signage video lists) from user collections in the Flutter frontend, excluding camera collections.

---

## ✅ Completed Work

### 1. Provider Namespace Conflict Resolution
- **Issue:** Conflict between `provider` and `flutter_riverpod` packages causing compilation errors
- **Solution:** 
  - Added package alias: `import 'package:provider/provider.dart' as provider;`
  - Created helper method `_getSignageProvider()` in `SignageManagementScreen`
  - Replaced all `context.read<SignageProvider>()` calls
  - Fixed `VideoListBuilder` to use package-aliased Provider access

**Files Modified:**
- `ppl-meta-frontend/lib/screens/signage_management_screen.dart`
- `ppl-meta-frontend/lib/widgets/signage/video_list_builder.dart`

### 2. Dialog Context Provider Access
- **Issue:** `VideoListBuilder` shown in dialog couldn't access `SignageProvider`
- **Solution:** Wrapped dialog with `provider.ChangeNotifierProvider.value()` to pass provider to dialog context

**Code:**
```dart
showDialog(
  context: context,
  builder: (dialogContext) => provider.ChangeNotifierProvider<SignageProvider>.value(
    value: _getSignageProvider(listen: false),
    child: const VideoListBuilder(),
  ),
);
```

### 3. Backend API Schema Update (UUID Support)
- **Issue:** Backend expected integer collection IDs, frontend sends UUID strings
- **Solution:** Updated backend schemas and service to accept UUID strings

**Files Modified:**
- `ppl-meta-media/src/schemas/signage.py` - Changed `collection_ids: List[int]` → `List[str]`
- `ppl-meta-media/src/services/signage_service.py` - Added UUID to ID conversion logic

**Key Changes:**
```python
# Convert string UUIDs to UUID objects for query
from uuid import UUID as UUIDType
collection_uuids = [UUIDType(uuid_str) for uuid_str in data.collection_ids]

# Query with UUIDs
collections = (
    self.db.query(MediaCollection)
    .filter(MediaCollection.uuid.in_(collection_uuids))
    .all()
)

# Map UUIDs to internal IDs
collection_id_map = {str(c.uuid): c.id for c in collections}
```

### 4. Gateway Routing Configuration
- **Issue:** Gateway didn't have routes for signage endpoints (404 errors)
- **Solution:** Added comprehensive signage endpoint proxying to gateway

**File Modified:** `ppl-meta-gateway/src/api/v1/router.py`

**Routes Added:**
- `POST /api/v1/signage/video-lists` - Create playlist
- `GET /api/v1/signage/video-lists` - List playlists
- `GET /api/v1/signage/video-lists/{list_uuid}` - Get playlist details
- `PUT /api/v1/signage/video-lists/{list_uuid}` - Update playlist
- `DELETE /api/v1/signage/video-lists/{list_uuid}` - Delete playlist
- `POST /api/v1/signage/video-lists/{list_uuid}/sync` - Sync to devices
- Plus device management and sync history endpoints

### 5. Authentication Integration
- **Issue:** Signage endpoints used stub authentication returning null UUID (`00000000-0000-0000-0000-000000000000`)
- **Solution:** Integrated proper JWT authentication using `get_current_user` dependency

**File Modified:** `ppl-meta-media/src/api/v1/signage.py`

**Changes:**
```python
# Added import
from ...auth import AuthUser, get_current_user

# Removed stub function
# def get_user_id_from_token() -> UUID:
#     return UUID("00000000-0000-0000-0000-000000000000")

# Updated all endpoints
async def create_video_list(
    data: VideoListCreate,
    current_user: AuthUser = Depends(get_current_user),  # ✅ Added
    db: Session = Depends(get_db),
):
    user_id = current_user.user_id  # ✅ Changed from get_user_id_from_token()
```

### 6. Debug Logging
- Added comprehensive logging to trace collection ownership validation
- Logs show user ID, collection UUIDs, query results, and ownership mismatches

---

## 🐛 Current Issue

### 500 Internal Server Error

**Status:** Service returns HTTP 500 when creating playlist  
**Last Known State:** Authentication working, collections found, but server error during creation

**Evidence:**
```
Gateway Log: POST /api/v1/signage/video-lists - 500 Internal Server Error
Process Time: 0.0537s
```

**Frontend Error:**
```
Failed to create video list: DioException [bad response]
Status code: 500 (Server error - the server failed to fulfil an apparently valid request)
```

**What We Know:**
- ✅ Provider accessible in dialog context
- ✅ Gateway routing working (no more 404)
- ✅ Authentication working (user ID extracted correctly)
- ✅ Collections found with correct ownership
- ❌ Something fails during video list creation in service layer

---

## 🔍 Next Steps

### Immediate Actions

1. **Check Media Service Logs**
   - Look for Python traceback in media service console output
   - Should show: `Traceback (most recent call last):` followed by error details
   - This will reveal the exact failure point

2. **Likely Issues to Investigate:**
   
   **A. Video Order Processing**
   - Frontend sends `videoOrder` but backend might have issues with empty list
   - Check line in `signage_service.py` where `internal_video_order` is created
   
   **B. Database Schema Mismatch**
   - `VideoList` model might expect fields we're not providing
   - Check required fields in `src/models/signage.py`
   
   **C. Video Items Creation**
   - `_add_videos_from_collections()` might fail if collection has no videos
   - Check if test collection has videos in it

3. **Quick Debug Test**
   ```bash
   # Test with minimal payload
   TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'username=fresh.user@example.com&password=NewPassword234!' | \
     python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
   
   curl -v -X POST "http://localhost:8080/api/v1/signage/video-lists" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Playlist",
       "collection_ids": ["0394b2a2-7b30-451c-b6a1-86afea83c28f"],
       "loop_mode": "continuous"
     }' | python3 -m json.tool
   ```

4. **Add Try-Catch in Service**
   - Wrap internal operations in try-catch blocks
   - Log each step: video list creation, video items addition, stats update

### Files to Review Tomorrow

1. **`ppl-meta-media/src/services/signage_service.py`**
   - Lines 60-120: `create_video_list()` method
   - Lines 280-350: `_add_videos_from_collections()` method
   - Check error handling, required fields, database commits

2. **`ppl-meta-media/src/models/signage.py`**
   - `VideoList` model definition
   - Check required fields, defaults, relationships

3. **`ppl-meta-frontend/lib/models/signage_models.dart`**
   - `CreateVideoListRequest` model
   - Compare field names with backend schema

---

## 📋 Testing Checklist (When Fixed)

- [ ] Create playlist with 1 collection
- [ ] Create playlist with multiple collections
- [ ] Create playlist with custom name and description
- [ ] Verify playlist appears in list
- [ ] Edit existing playlist
- [ ] Delete playlist
- [ ] Test with different loop modes
- [ ] Test with transition durations

---

## 📝 Summary

**Problem:** Users couldn't create video playlists due to multiple frontend/backend integration issues  
**Progress:** Fixed Provider conflicts, dialog context, UUID support, gateway routing, and authentication  
**Current Block:** 500 error during playlist creation - need media service error traceback  
**Next Session:** Debug the 500 error using server logs, likely in video list creation or video items addition logic

---

## 🔧 Quick Reference

### Key Files Modified This Session
```
ppl-meta-frontend/
├── lib/screens/signage_management_screen.dart
├── lib/widgets/signage/video_list_builder.dart

ppl-meta-media/
├── src/api/v1/signage.py
├── src/schemas/signage.py
├── src/services/signage_service.py

ppl-meta-gateway/
└── src/api/v1/router.py
```

### Test User Credentials
```
Email: fresh.user@example.com
Password: NewPassword234!
User ID: 7
User UUID: 4cf362b1-3e05-4e85-81c7-c08a98c7e41b
```

### Test Collection
```
Name: marketing 01
UUID: 0394b2a2-7b30-451c-b6a1-86afea83c28f
Owner: 4cf362b1-3e05-4e85-81c7-c08a98c7e41b (user 7)
```

### Service Ports
- Gateway: 8080
- Node (Auth): 8001
- Media: 8000
- Orchestrator: 8002
- Vision: 8003
- Cameras: 8005

---

**Status:** 🟡 In Progress - Blocked on 500 error investigation  
**Confidence:** High - All integration points working except final service layer execution  
**Estimated Time to Complete:** 30-60 minutes once error traceback is obtained
