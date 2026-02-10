# Camera UUID Migration Guide

## Overview

This migration updates the PPL Meta Platform to use proper UUID v4 identifiers for all cameras instead of legacy device-specific IDs. The migration is **backward compatible** and supports a graceful transition period.

## Changes Summary

### Phase 1: Backend UUID Validation & Auto-Naming ✅

**New Services:**
- `device_id_service.py` - UUID validation and conversion utilities
- `auto_naming_service.py` - Auto-numbered camera name generation

**Updated Endpoints:**
- USB Camera Detection - Generates UUIDs for new cameras
- RTSP Camera Registration - Uses UUID + auto-naming
- Edge Camera Registration - Validates/converts device_id to UUID  
- Mobile Camera Registration - Validates/converts device_id to UUID

**Key Features:**
- Legacy device IDs converted to UUIDs automatically
- Auto-numbered names: "USB Camera 1", "RTSP Camera 2", etc.
- Names can be customized via existing rename endpoint
- Fully backward compatible with existing cameras

### Phase 2: Edge Camera UUID Generation ✅

**Updated Files:**
- `ppl-meta-edge-camera/src/config_manager.py` - New persistent config storage
- `ppl-meta-edge-camera/src/landing_page.py` - UUID generation logic

**Behavior:**
- Generates UUID v4 on first boot
- Persists to `runtime_config.json`
- Respects `DEVICE_ID` environment variable override
- Backward compatible with existing edge cameras

### Phase 3: Mobile App UUID Generation ✅

**Updated Files:**
- `ppl_meta_mobile_camera/pubspec.yaml` - Added uuid package
- `ppl_meta_mobile_camera/lib/services/device_identifier_service.dart` - UUID generation

**Behavior:**
- Generates UUID v4 on first app launch
- Persists via SharedPreferences
- Survives app reinstalls (if device storage intact)
- Backward compatible with existing mobile cameras

---

## Migration Timeline

### Immediate (Phase 1)
- Backend now accepts both UUIDs and legacy IDs
- New cameras automatically get UUIDs
- Existing cameras continue working with legacy IDs

### Short-term (Phases 2-3)
- Update edge cameras → next deployment generates UUID
- Release mobile app update → users' devices generate UUIDs
- All new registrations use proper UUIDs

### Long-term (Optional)
- After 6+ months, optionally deprecate legacy ID support
- Run migration script to convert remaining legacy IDs

---

## Testing Instructions

### 1. Test USB Camera Detection

```bash
# Start cameras service
cd ppl-meta-cameras
source venv/bin/activate
cd src
python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload

# In another terminal, trigger detection
curl -X POST "http://localhost:8005/api/v1/cameras/detect?save_to_db=true" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Result:**
- New USB cameras get UUID format: `550e8400-e29b-41d4-a716-446655440000`
- Camera names auto-numbered: "USB Camera 1", "USB Camera 2", etc.
- Existing cameras keep their legacy IDs

### 2. Test RTSP Camera Registration

```bash
# Register new RTSP camera
curl -X POST "http://localhost:8005/api/v1/cameras/rtsp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.1.100",
    "port": 554,
    "path": "/stream1",
    "username": "admin",
    "password": "password"
  }'
```

**Expected Result:**
- device_id is UUID format
- Auto-generated name: "RTSP Camera 1" (or next available number)
- Name can be changed via existing rename endpoint

### 3. Test Edge Camera UUID Generation

```bash
# SSH into edge camera (Raspberry Pi)
ssh pi@<edge-camera-ip>

# Check runtime config
cat /path/to/ppl-meta-edge-camera/runtime_config.json

# Should see:
# {
#   "device_id": "550e8400-e29b-41d4-a716-446655440000"
# }

# Register with platform
curl -X POST "http://localhost:8005/api/v1/cameras/edge/register-edge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "<uuid-from-config>",
    "name": "Kitchen Camera",
    "ip_address": "192.168.1.77",
    "management_port": 9001,
    "stream_port": 8554
  }'
```

**Expected Result:**
- Edge camera generates and stores UUID
- Backend accepts UUID as-is (no conversion)
- Legacy edge-camera-XXXXX IDs converted to UUIDs

### 4. Test Mobile App UUID Generation

```bash
# Install dependencies
cd ppl_meta_mobile_camera
flutter pub get

# Run on Android device
flutter run

# Check device logs
flutter logs | grep "device UUID"

# Should see:
# ✅ Generated new UUID for mobile camera: 550e8400-...
# OR
# 📱 Using persisted device UUID: 550e8400-...
```

**Expected Result:**
- First launch generates UUID
- UUID persists across app restarts
- Legacy Android IDs converted to UUIDs by backend

### 5. Test Camera Rename

```bash
# Rename camera (existing functionality still works)
curl -X PATCH "http://localhost:8005/api/v1/cameras/<device-id>/name" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Name"
  }'
```

**Expected Result:**
- Camera name updated
- Collection name synced automatically
- Continuous pipeline continues working (uses UUID)

---

## Code Examples

### Backend: Check if ID is UUID

```python
from src.services.device_id_service import is_valid_uuid, ensure_valid_uuid

# Check format
if is_valid_uuid(device_id):
    print(f"Already UUID: {device_id}")
else:
    print(f"Legacy format, will convert: {device_id}")

# Convert to UUID if needed
validated_id = ensure_valid_uuid(device_id)  # Returns UUID
```

### Backend: Generate Auto-numbered Name

```python
from src.services.auto_naming_service import generate_auto_camera_name

# Generate unique name
name = generate_auto_camera_name(
    db=db_session,
    camera_type=CameraType.USB,
    index=0  # Optional: starting index for USB cameras
)
# Result: "USB Camera 1" (or next available number)
```

### Edge Camera: Get Device ID

```python
from src.landing_page import get_device_id

# Returns persisted UUID or generates new one
device_id = get_device_id()
# Result: "550e8400-e29b-41d4-a716-446655440000"
```

### Mobile App: Get Device ID

```dart
import 'package:ppl_meta_mobile_camera/services/device_identifier_service.dart';

final deviceService = DeviceIdentifierService();
final deviceId = await deviceService.getDeviceId();
// Result: "550e8400-e29b-41d4-a716-446655440000"
```

---

## Troubleshooting

### Issue: Legacy camera not working after migration

**Solution:** Backend supports both legacy and UUID formats. No action needed unless you forcibly migrated database IDs.

### Issue: Edge camera generates new ID after reboot

**Cause:** `runtime_config.json` not persisting (file permissions?)

**Solution:**
```bash
# Check file exists and is writable
ls -la /path/to/ppl-meta-edge-camera/runtime_config.json

# If missing, will be created on next boot
# If exists but wrong permissions:
chmod 644 runtime_config.json
```

### Issue: Mobile app generates new UUID after reinstall

**Expected Behavior:** SharedPreferences cleared on app uninstall. This is by design for privacy.

**Workaround:** Implement cloud-based device identity recovery (future enhancement).

### Issue: Duplicate camera names after migration

**Solution:** Auto-naming service increments until unique name found. Should not happen unless database inconsistency exists.

```bash
# Check for duplicate names
psql -d media_db -c "SELECT name, COUNT(*) FROM cameras GROUP BY name HAVING COUNT(*) > 1;"

# Fix manually or re-run migration
```

---

## Database Schema

### Before Migration
```
cameras.device_id = "usb_camera_0" | "rtsp_192.168.1.76_554" | "edge-camera-12ab34cd"
cameras.name = "USB Camera 0" | "Kitchen RTSP" | "Office Edge Cam"
```

### After Migration
```
cameras.device_id = "550e8400-e29b-41d4-a716-446655440000" (UUID v4)
cameras.name = "USB Camera 1" | "RTSP Camera 2" | "Edge Camera 3" (auto-numbered, user-customizable)
```

---

## Backward Compatibility

### Legacy ID Handling

**Backend automatically converts:**
- `usb_camera_0` → generates UUID, logs warning
- `rtsp_192.168.1.76_554` → generates UUID, logs warning  
- `edge-camera-12ab34cd` → generates UUID, logs mapping
- Android IDs → generates UUID, logs mapping

**Workers/Collections:**
- Existing workers with legacy IDs continue functioning
- New workers use UUIDs
- Collections already use UUIDs (no change)

### Mixed Environment Support

Platform supports:
- Old edge cameras (legacy ID) + new edge cameras (UUID)
- Old mobile apps (Android ID) + new mobile apps (UUID)
- Old USB detection (legacy) + new USB detection (UUID)

All work together seamlessly during transition period.

---

## Future Enhancements (Phase 4+)

### Optional: Full Database Migration

```python
# Script to convert all legacy IDs to UUIDs
# UPDATE cameras SET device_id = <new-uuid> WHERE device_id LIKE 'usb_camera_%'
# UPDATE collections SET camera_uuid = <new-uuid> WHERE camera_uuid = <old-id>
# UPDATE recording_sessions... etc
```

### Optional: Legacy ID Deprecation

After sufficient transition period:
1. Log warnings for legacy ID usage
2. Add deprecation notices in API responses
3. Eventually reject legacy IDs (breaking change - major version bump)

---

## Support

For issues or questions:
1. Check logs: `ppl-meta-cameras/logs/ppl-meta-cameras.log`
2. Enable debug logging: Set `LOG_LEVEL=DEBUG`
3. Verify UUID format: Use `device_id_service.is_valid_uuid()`

## Version History

- **v1.0.0** - Initial UUID migration implementation
- **Date:** 2026-02-10
- **Author:** GitHub Copilot + User
