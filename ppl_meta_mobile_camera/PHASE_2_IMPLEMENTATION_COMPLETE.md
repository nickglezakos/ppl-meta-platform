# Phase 2 Implementation Complete ✅

## Mobile App UUID v4 Migration

Successfully implemented server-generated UUID system for mobile cameras, replacing client-provided device IDs. This brings mobile cameras in line with USB/RTSP camera patterns.

---

## Files Modified

### 1. Device Identifier Service
**File:** `lib/services/device_identifier_service.dart`

**Changes:**
- ✅ Added `storeCameraUuid(String uuid)` - Stores server-generated UUID
- ✅ Added `getStoredCameraUuid()` - Retrieves stored UUID for API calls
- ✅ Added `getDeviceSerial()` - Gets device serial for hardware identification
- ✅ Updated storage key system (camera UUID separate from legacy device ID)

**Usage:**
```dart
final deviceService = DeviceIdentifierService();

// After registration, store UUID
await deviceService.storeCameraUuid(serverUuid);

// For API calls, retrieve UUID
final uuid = await deviceService.getStoredCameraUuid();
if (uuid != null) {
  // Make API call with UUID
}
```

---

### 2. Auto Camera Registration Service
**File:** `lib/services/auto_camera_registration_service.dart`

**Major Changes:**

#### Registration Payload (Before → After)
```dart
// ❌ OLD - Client-provided device_id
final requestBody = {
  'name': cameraName,
  'device_id': 'mobile_android123', // Client ID
  'device_model': 'Pixel 6',
  'device_manufacturer': 'Google',
};

// ✅ NEW - Server generates UUID
final requestBody = {
  'name': cameraName, // Optional
  'device_model': 'Pixel 6',
  'device_manufacturer': 'Google',
  'device_serial': serialNumber, // For hardware_identifier
  'ip_address': deviceIP,
  'port': 8554,
};
```

#### Response Handling
```dart
// Step 7: Store server-generated UUID
final deviceUuid = responseData['camera']['device_id'];
await _deviceService.storeCameraUuid(deviceUuid);
```

#### Existing Camera Detection
- Changed from device_id lookup to stored UUID check
- Verifies camera exists on server before re-registering
- Handles UUID migration gracefully

---

### 3. Mobile Camera Heartbeat Service (NEW)
**File:** `lib/services/mobile_camera_heartbeat_service.dart`

**Features:**
- 💓 Periodic heartbeat (default 30s interval)
- 📝 Automatic pending settings application
- 🔄 Auto-recovery from network issues
- ⚙️ Configurable interval

**Usage:**
```dart
final heartbeatService = MobileCameraHeartbeatService();

// Start heartbeat after successful registration
await heartbeatService.startHeartbeat();

// Stop when app goes to background
heartbeatService.stopHeartbeat();

// Send immediate heartbeat after network reconnect
await heartbeatService.sendImmediateHeartbeat();
```

**Heartbeat Response Handling:**
```dart
// Server response includes pending settings
{
  "message": "Heartbeat received",
  "device_id": "uuid",
  "status": "connected",
  "timestamp": "2026-02-11T...",
  "pending_settings_applied": [
    {"type": "name_update", "value": "New Camera Name"}
  ]
}
```

---

## Integration Guide

### App Lifecycle Integration

```dart
// main.dart or app initialization
import 'package:ppl_meta_mobile_camera/services/mobile_camera_heartbeat_service.dart';

class MobileCameraApp extends StatefulWidget {
  @override
  _MobileCameraAppState createState() => _MobileCameraAppState();
}

class _MobileCameraAppState extends State<MobileCameraApp> 
    with WidgetsBindingObserver {
  
  final _heartbeatService = MobileCameraHeartbeatService();
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeHeartbeat();
  }
  
  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _heartbeatService.stopHeartbeat();
    super.dispose();
  }
  
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // App came to foreground - restart heartbeat
      _heartbeatService.startHeartbeat();
    } else if (state == AppLifecycleState.paused) {
      // App went to background - stop heartbeat to save battery
      _heartbeatService.stopHeartbeat();
    }
  }
  
  Future<void> _initializeHeartbeat() async {
    // Check if camera is registered
    final deviceService = DeviceIdentifierService();
    final uuid = await deviceService.getStoredCameraUuid();
    
    if (uuid != null) {
      // Camera already registered, start heartbeat
      await _heartbeatService.startHeartbeat();
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: HomeScreen(),
    );
  }
}
```

---

## API Changes Summary

### Endpoints Now Using UUID

All mobile camera API calls must use stored UUID:

```dart
// Get stored UUID first
final uuid = await deviceService.getStoredCameraUuid();
if (uuid == null) {
  // Camera not registered - show registration flow
  return;
}

// ✅ Heartbeat
POST /api/v1/cameras/mobile/{uuid}/heartbeat

// ✅ Update camera (if needed in future)
PUT /api/v1/cameras/mobile/{uuid}

// ✅ Rename camera (via rename endpoint)
PATCH /api/v1/cameras/mobile/{uuid}/name

// ✅ Any other camera-specific endpoint
GET /api/v1/cameras/{uuid}
```

---

## Migration Path

### For Existing Installations

1. **Backend Migration** (Run first)
   ```bash
   cd ppl-meta-cameras
   python migrations/migrate_mobile_cameras_to_uuid.py
   ```

2. **Mobile App Update** (Deploy to users)
   - Old apps will fail registration (device_id field no longer accepted)
   - Users must update to new app version
   - On first launch after update:
     - App detects no stored UUID
     - Triggers re-registration
     - Server detects existing camera via hardware_identifier
     - Returns existing camera with new UUID
     - App stores UUID for future use

### Backward Compatibility

- ✅ Server detects existing cameras via `hardware_identifier`
- ✅ Same device gets same camera record (not duplicate)
- ✅ Collections remain linked (by camera UUID)
- ✅ No data loss during migration

---

## Testing Checklist

### Registration Flow
- [ ] New camera registration generates server UUID
- [ ] UUID stored in SharedPreferences
- [ ] Re-registration returns same camera (not duplicate)
- [ ] Hardware identifier detection works across app reinstalls

### Heartbeat Mechanism
- [ ] Heartbeat starts after successful registration
- [ ] Heartbeat sends every 30 seconds
- [ ] Heartbeat stops when app backgrounded
- [ ] Heartbeat resumes when app foregrounded
- [ ] Pending settings applied on heartbeat

### UUID Storage & Retrieval
- [ ] UUID persists across app restarts
- [ ] UUID cleared on app uninstall
- [ ] API calls use stored UUID
- [ ] Invalid UUID handled gracefully (re-registration)

### Edge Cases
- [ ] App reinstall - re-registers with same camera
- [ ] Network loss - heartbeat recovers
- [ ] Server restart - heartbeat reconnects
- [ ] Multiple devices - each gets unique UUID

---

## Next Steps

### Pending: Manual Connection Fallback UI

When auto-registration fails, provide manual input form:

```dart
// TODO: Implement fallback UI
class ManualRegistrationForm extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Form(
      child: Column(
        children: [
          TextFormField(
            decoration: InputDecoration(labelText: 'Server URL'),
          ),
          TextFormField(
            decoration: InputDecoration(labelText: 'Username'),
          ),
          TextFormField(
            decoration: InputDecoration(labelText: 'Password'),
            obscureText: true,
          ),
          ElevatedButton(
            onPressed: () {
              // Attempt manual registration
            },
            child: Text('Register Camera'),
          ),
        ],
      ),
    );
  }
}
```

---

## Summary

**Phase 2 Complete! ✅**

- ✅ Mobile app no longer sends device_id
- ✅ Server generates UUID v4 for mobile cameras
- ✅ UUID stored in SharedPreferences
- ✅ Heartbeat mechanism implemented
- ✅ Pending settings auto-applied
- ✅ Hardware identifier for device detection
- ⏳ Manual fallback UI (pending)

Mobile cameras now follow the same proven patterns as USB/RTSP cameras with server-controlled identity and reliable UUID-based API access! 🎉
