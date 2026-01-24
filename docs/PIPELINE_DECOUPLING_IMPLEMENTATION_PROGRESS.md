# Pipeline Decoupling Implementation - Progress Report

**Date**: January 24, 2026  
**Status**: Phase 1-2 Complete ✅ | Phase 3 (Frontend) Pending  

## ✅ Completed Tasks

### Phase 1: Database Migration

1. **Migration Scripts Created**
   - `migrations/add_pipeline_settings.sql` - Forward migration
   - `migrations/rollback_pipeline_settings.sql` - Rollback script
   
2. **Database Changes**
   - Added `instant_detection_enabled` column (BOOLEAN, default TRUE)
   - Added `recording_pipeline_enabled` column (BOOLEAN, default TRUE)
   - Added `instant_detection_interval_seconds` column (INTEGER, default 5)
   - Added `segment_duration_seconds` column (INTEGER, default 30)
   - Added constraint to ensure at least one pipeline is enabled
   - Created performance index on pipeline settings columns

### Phase 2: Backend Implementation ✅

1. **Data Model Updates**
   - ✅ Updated `Camera` model in `src/models/camera.py` with pipeline fields
   
2. **API Schemas Created**
   - ✅ `src/schemas/pipeline_settings.py` with:
     - `PipelineSettingsUpdate` - Request schema for updates
     - `PipelineSettingsResponse` - Response schema
     - `RecordingStartRequest` - Enhanced recording start with pipeline overrides
   
3. **API Endpoints Implemented**
   - ✅ `GET /api/v1/cameras/{device_id}/pipeline-settings` - Get current settings
   - ✅ `PATCH /api/v1/cameras/{device_id}/pipeline-settings` - Update settings
   
4. **Endpoint Features**
   - Validation: At least one pipeline must be enabled
   - Validation: Instant detection interval (1-60 seconds)
   - Validation: Segment duration (5-300 seconds)

5. **Recording Logic Integration**
   - ✅ Modified `start_recording_with_session()` in `camera_detection.py`:
     - Reads pipeline settings from database on every recording start
     - Conditionally enables instant detection based on `instant_detection_enabled`
     - Conditionally enables recording pipeline based on `recording_pipeline_enabled`
     - Supports instant-detection-only mode (no video files created)
     - Validates at least one pipeline is enabled
   - ✅ Modified `stop_recording()` in `camera_detection.py`:
     - Handles instant-detection-only sessions
     - Pipeline-aware cleanup (only stops detection if disabled in settings)
     - Returns appropriate response for each mode

6. **Supported Recording Modes**
   - **Both Pipelines** (default): Instant detection + video recording
   - **Instant Detection Only**: Triggers without video files
   - **Recording Only**: Video segments without instant detection
   - Proper error handling and HTTP status codes
   - Logging with pipeline status indicators

### Testing Infrastructure

1. **Test Script Created**
   - `test_pipeline_settings_endpoints.sh` - Comprehensive API tests
   - Tests all valid configurations
   - Tests validation edge cases
   - Tests error conditions

---

## 🚧 Next Steps

### Phase 2: Backend Implementation (Remaining)

1. **Modify Recording Logic**
   - [x] Update `start_recording_with_session()` in `camera_detection.py`
     - Read pipeline settings from database
     - Conditionally start instant detection
     - Conditionally start recording pipeline
     - Handle instant-detection-only mode
   
   - [x] Update `stop_recording()` in `camera_detection.py`
     - Handle instant-detection-only sessions
     - Proper cleanup for each mode
   
2. **Integration Points**
   - [x] Update instant detection manager integration
   - [x] Update recording session service integration
   - [x] Add logging for pipeline mode transitions

**Status:** ✅ **COMPLETED** (2025-01-24)

### Phase 3: Frontend Implementation ✅

1. **Flutter Data Models**
   - [x] Create `CameraPipelineSettings` model
   - [x] Update `Camera` model with pipeline fields
   
2. **UI Screens**
   - [x] Create `camera_pipeline_settings_screen.dart`
   - [x] Update camera card with:
     - Pipeline status indicators (⚡ 🔴)
     - Settings button per camera
     - Navigation to settings screen
   
3. **API Service Layer**
   - [x] Add `getPipelineSettings()` method
   - [x] Add `updatePipelineSettings()` method

**Status:** ✅ **COMPLETED** (2025-01-24)

**Files Created/Modified:**
- `lib/core/models/camera_pipeline_settings.dart` - Pipeline settings model
- `lib/core/models/camera.dart` - Added pipeline fields and helper methods
- `lib/core/services/camera_service.dart` - Added API methods
- `lib/presentation/screens/cameras/camera_pipeline_settings_screen.dart` - Settings UI
- `lib/presentation/widgets/camera/camera_card.dart` - Added status indicators and settings button

### Phase 4: Testing & Validation

1. **Unit Tests**
   - [ ] Test pipeline settings validation logic
   - [ ] Test conditional pipeline startup
   - [ ] Test edge cases (both enabled, instant only, recording only)
   
2. **Integration Tests**
   - [ ] End-to-end test: instant detection only mode
   - [ ] End-to-end test: recording only mode
   - [ ] End-to-end test: both pipelines mode
   - [ ] Test resource usage in each mode

---

## 📝 Migration Instructions

### Step 1: Apply Database Migration

```bash
# Connect to your PostgreSQL database
psql -U your_user -d cameras_db

# Run the migration
\i /path/to/ppl-meta-cameras/migrations/add_pipeline_settings.sql

# Verify the changes
SELECT device_id, instant_detection_enabled, recording_pipeline_enabled 
FROM cameras LIMIT 5;
```

### Step 2: Restart Cameras Service

```bash
# Stop the cameras service
# (Stop method depends on your deployment)

# The service will load the updated Camera model with new fields

# Start the cameras service
cd ppl-meta-cameras
source venv/bin/activate
cd src
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

### Step 3: Test the New Endpoints

```bash
# Update the token in the test script
vim test_pipeline_settings_endpoints.sh
# Replace "your-token-here" with a valid JWT token

# Run the tests
./test_pipeline_settings_endpoints.sh
```

### Step 4: Verify Default Behavior

```bash
# Check that all existing cameras have both pipelines enabled (default)
curl -X GET "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Expected response:
# {
#   "device_id": "usb_camera_0",
#   "camera_name": "...",
#   "instant_detection_enabled": true,
#   "recording_pipeline_enabled": true,
#   "instant_detection_interval_seconds": 5,
#   "segment_duration_seconds": 30,
#   ...
# }
```

---

## 🔧 Configuration Examples

### Example 1: Set Camera to Instant Detection Only

```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=false&instant_detection_interval_seconds=5" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Use Case**: Real-time triggers without storage overhead

### Example 2: Set Camera to Recording Only

```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=false&recording_pipeline_enabled=true&segment_duration_seconds=60" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Use Case**: Forensic recording without real-time analysis

### Example 3: Custom Intervals (Both Pipelines)

```bash
curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/pipeline-settings?instant_detection_enabled=true&recording_pipeline_enabled=true&instant_detection_interval_seconds=10&segment_duration_seconds=45" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Use Case**: Balanced mode with custom timings

---

## 📊 Database Schema

```sql
-- New columns in cameras table
ALTER TABLE cameras 
  ADD COLUMN instant_detection_enabled BOOLEAN DEFAULT TRUE,
  ADD COLUMN recording_pipeline_enabled BOOLEAN DEFAULT TRUE,
  ADD COLUMN instant_detection_interval_seconds INTEGER DEFAULT 5,
  ADD COLUMN segment_duration_seconds INTEGER DEFAULT 30;

-- Constraint
ALTER TABLE cameras
  ADD CONSTRAINT at_least_one_pipeline_enabled
  CHECK (instant_detection_enabled OR recording_pipeline_enabled);

-- Index
CREATE INDEX idx_cameras_pipeline_settings 
  ON cameras(instant_detection_enabled, recording_pipeline_enabled);
```

---

## 🎯 API Endpoints

### GET /api/v1/cameras/{device_id}/pipeline-settings

**Description**: Retrieve current pipeline settings for a camera

**Response Example**:
```json
{
  "device_id": "usb_camera_0",
  "camera_name": "Main Entrance Camera",
  "instant_detection_enabled": true,
  "recording_pipeline_enabled": true,
  "instant_detection_interval_seconds": 5,
  "segment_duration_seconds": 30,
  "created_at": "2026-01-20T08:00:00Z",
  "updated_at": "2026-01-24T10:30:00Z"
}
```

### PATCH /api/v1/cameras/{device_id}/pipeline-settings

**Description**: Update pipeline settings for a camera

**Query Parameters**:
- `instant_detection_enabled` (required): boolean
- `recording_pipeline_enabled` (required): boolean
- `instant_detection_interval_seconds` (optional): integer (1-60)
- `segment_duration_seconds` (optional): integer (5-300)

**Validation**:
- At least one pipeline must be enabled (400 error if both false)
- Interval must be 1-60 seconds (400 error if outside range)
- Segment duration must be 5-300 seconds (400 error if outside range)

---

## 🔐 Security & Permissions

- **GET endpoint**: Requires `view_cameras` permission
- **PATCH endpoint**: Requires `connect_camera` permission
- Both endpoints require valid JWT authentication
- Settings are per-camera, not per-user
- All updates are logged for audit trail

---

## 📈 Next Implementation Priority

1. **HIGH**: Modify `start_recording_with_session()` to respect pipeline settings
2. **HIGH**: Modify `stop_recording()` to handle instant-detection-only mode
3. **MEDIUM**: Create Flutter pipeline settings screen
4. **MEDIUM**: Update cameras list UI with pipeline indicators
5. **LOW**: Write comprehensive unit tests
6. **LOW**: Write integration tests

---

## 🐛 Known Issues / TODOs

- [ ] Recording logic doesn't yet read pipeline settings from database
- [ ] Instant detection startup is still hardcoded
- [ ] No frontend UI for changing settings yet
- [ ] No unit tests for new endpoints
- [ ] No integration tests for different pipeline modes
- [ ] Need to update API documentation
- [ ] Need to update user guide with new features

---

## 📚 References

- Proposal Document: `docs/INSTANT_DETECTION_RECORDING_DECOUPLING_PROPOSAL.md`
- Camera Model: `ppl-meta-cameras/src/models/camera.py`
- Endpoints: `ppl-meta-cameras/src/api/v1/endpoints/cameras.py`
- Schemas: `ppl-meta-cameras/src/schemas/pipeline_settings.py`
- Migration: `ppl-meta-cameras/migrations/add_pipeline_settings.sql`

---

**Last Updated**: January 24, 2026  
**Next Review**: After Phase 2 completion
