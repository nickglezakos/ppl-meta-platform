# Camera Archive Feature - Implementation Complete

## 📋 Overview
Added camera archive functionality that allows users to hide cameras from the default camera list without deleting them. Archived cameras can be restored at any time.

## ✅ Completed Tasks

### Backend (Python/FastAPI)
1. **Database Schema** (`ppl-meta-cameras/src/models/camera.py`)
   - Added `archived` column (Boolean, default=False, indexed)
   - Database migration created and applied successfully

2. **API Endpoints** (`ppl-meta-cameras/src/api/v1/endpoints/cameras.py`)
   - Modified `GET /api/v1/cameras/` to support `include_archived` query parameter (default=false)
   - Added `POST /api/v1/cameras/{device_id}/archive` endpoint (requires admin_cameras permission)
   - Added `POST /api/v1/cameras/{device_id}/unarchive` endpoint (requires admin_cameras permission)
   - All endpoints include proper error handling and logging

### Frontend (Flutter/Dart)
3. **Camera Model** (`ppl-meta-frontend/lib/core/models/camera.dart`)
   - Added `archived` field (bool, default=false)
   - Updated `fromJson()` to parse archived field
   - Updated `toJson()` to include archived field
   - Updated `copyWith()` to include archived parameter

4. **Camera Service** (`ppl-meta-frontend/lib/core/services/camera_service.dart`)
   - Modified `getCameras()` to accept `includeArchived` parameter (default=false)
   - Added `archiveCamera(String deviceId)` method
   - Added `unarchiveCamera(String deviceId)` method

5. **Camera Providers** 
   - Updated `CameraListNotifier.loadCameras()` to accept `includeArchived` parameter (`ppl-meta-frontend/lib/core/providers/camera_providers.dart`)
   - Added `archiveCamera()` and `unarchiveCamera()` methods to `CameraActions` class (`ppl-meta-frontend/lib/core/providers/multi_camera_providers.dart`)

6. **Cameras Screen** (`ppl-meta-frontend/lib/presentation/screens/cameras/cameras_screen.dart`)
   - Added `_showArchivedCameras` state variable
   - Added archive/unarchive toggle button in app bar
   - Icon changes based on state: unarchive (orange) when showing archived, archive (gray) when hidden
   - Updated all `loadCameras()` calls to pass `includeArchived` parameter
   - Pull-to-refresh and error retry respect current archive filter state

7. **Camera Card** (`ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`)
   - Added archive/unarchive button for each camera
   - Icon shows current state: unarchive (orange) for archived cameras, archive (gray) for active cameras
   - Clicking button archives/unarchives camera with snackbar feedback
   - Automatically refreshes camera list after archive action

### Database
8. **Migration Files** (`ppl-meta-cameras/migrations/`)
   - Created `add_camera_archive.sql` migration
   - Created `rollback_camera_archive.sql` rollback migration
   - Created `run_migration.py` utility script for running migrations
   - Migration successfully applied to PostgreSQL database

## 🔧 Technical Details

### API Behavior
- **Default behavior**: `GET /api/v1/cameras/` returns only non-archived cameras
- **Show archived**: `GET /api/v1/cameras/?include_archived=true` returns all cameras
- **Archive camera**: `POST /api/v1/cameras/{device_id}/archive` sets archived=True
- **Unarchive camera**: `POST /api/v1/cameras/{device_id}/unarchive` sets archived=False

### UI Behavior
- **Toggle button** (app bar): Shows/hides archived cameras in the list
- **Archive button** (camera card): Archives/unarchives individual camera
- **Visual feedback**: Orange color for archived state, gray for active state
- **Snackbar notifications**: Confirms archive/unarchive actions
- **Automatic refresh**: Camera list updates after any archive action

### Database Schema
```sql
ALTER TABLE cameras 
  ADD COLUMN archived BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_cameras_archived ON cameras(archived);
```

### Permissions
- Archive and unarchive operations require `admin_cameras` permission
- Regular users can view archived cameras if the toggle is enabled

## 📝 Usage Examples

### Backend API
```bash
# Get only active (non-archived) cameras
GET /api/v1/cameras/

# Get all cameras including archived
GET /api/v1/cameras/?include_archived=true

# Archive a camera
POST /api/v1/cameras/edge-camera-123/archive

# Unarchive a camera
POST /api/v1/cameras/edge-camera-123/unarchive
```

### Frontend Usage
1. **View archived cameras**: Click the archive toggle button in the cameras screen app bar
2. **Archive a camera**: Click the archive icon on any camera card
3. **Unarchive a camera**: Enable archived view, then click the unarchive icon on archived camera

## 🎯 Benefits
- **No data loss**: Cameras are hidden, not deleted
- **Easy restoration**: One-click unarchive to restore cameras
- **Clean UI**: Default view shows only active cameras
- **Flexible filtering**: Users can toggle archived camera visibility
- **Performance**: Indexed archived column for efficient filtering
- **User-friendly**: Clear visual indicators and feedback

## 📊 Database Migration
```bash
# To apply the migration
cd ppl-meta-cameras
source venv/bin/activate
python run_migration.py migrations/add_camera_archive.sql

# To rollback (if needed)
python run_migration.py migrations/rollback_camera_archive.sql
```

## ✅ Testing Checklist
- [ ] Archive camera from camera card - ✅ UI implemented
- [ ] Unarchive camera from camera card - ✅ UI implemented
- [ ] Toggle archived visibility in cameras screen - ✅ UI implemented
- [ ] Verify archived cameras don't appear in default list - ⏳ Requires testing
- [ ] Verify archived cameras appear when toggle is enabled - ⏳ Requires testing
- [ ] Verify archive/unarchive API endpoints - ⏳ Requires testing
- [ ] Verify permissions (admin_cameras) - ⏳ Requires testing
- [ ] Test database migration on clean install - ✅ Migration applied successfully
- [ ] Test rollback migration - ⏳ Requires testing

## 📌 Related Files
**Backend:**
- `ppl-meta-cameras/src/models/camera.py`
- `ppl-meta-cameras/src/api/v1/endpoints/cameras.py`
- `ppl-meta-cameras/migrations/add_camera_archive.sql`
- `ppl-meta-cameras/migrations/rollback_camera_archive.sql`
- `ppl-meta-cameras/run_migration.py`

**Frontend:**
- `ppl-meta-frontend/lib/core/models/camera.dart`
- `ppl-meta-frontend/lib/core/services/camera_service.dart`
- `ppl-meta-frontend/lib/core/providers/camera_providers.dart`
- `ppl-meta-frontend/lib/core/providers/multi_camera_providers.dart`
- `ppl-meta-frontend/lib/presentation/screens/cameras/cameras_screen.dart`
- `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`

## 🚀 Next Steps
1. Test the complete workflow with running services
2. Verify archived cameras are properly filtered in default view
3. Verify toggle button correctly shows/hides archived cameras
4. Test archive/unarchive API endpoints directly
5. Verify admin_cameras permission enforcement
6. Add archived camera count to cameras screen header (optional enhancement)
7. Consider adding "Last Archived" timestamp field (optional enhancement)
