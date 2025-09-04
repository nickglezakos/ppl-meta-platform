# Mobile Camera Discovery Configuration Fix

## Problem Analysis

The mobile app is experiencing two main issues:

1. **Discovery Configuration Loss**: The mobile app shows "❌ No discovery configuration found" because the configuration isn't persisting between app sessions
2. **Duplicate Camera Registrations**: The backend has 5 duplicate cameras with the same name but different device IDs with timestamp suffixes

## Root Cause

### Discovery Service Configuration
The cameras service is properly registered at:
- **Host**: 192.168.185.107
- **Port**: 8005
- **Status**: healthy
- **URL**: http://192.168.185.107:8005

### Mobile App Configuration Issue
The mobile app's `DiscoveryConfigService` loses the configuration stored in `SharedPreferences` when:
- App restarts
- User navigates between screens  
- Authentication state changes

## Solutions

### Fix 1: Update Mobile App Discovery Configuration

The mobile app needs to be configured with the correct discovery service URL:

```dart
// In discovery_config_service.dart
static const String defaultDiscoveryUrl = 'http://192.168.185.107:8006';
```

### Fix 2: Improve Configuration Persistence

Update the mobile app to better persist discovery configuration:

```dart
// Enhanced configuration storage
Future<void> saveDiscoveryConfig(DiscoveryConfig config) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('discovery_config', jsonEncode(config.toJson()));
  await prefs.setString('discovery_last_update', DateTime.now().toIso8601String());
}
```

### Fix 3: Clean Up Duplicate Cameras

Current duplicate cameras in backend:
- ID 56: mcam-201117ty-2d7ee4 (mobile_TKQ1.221114.001_1756843629006)
- ID 57: mcam-201117ty-2d7ee4 (mobile_TKQ1.221114.001_1756843629299) 
- ID 58: mcam-201117ty-2d7ee4 (mobile_TKQ1.221114.001_1756843629567)
- ID 59: mcam-201117ty-2d7ee4 (mobile_TKQ1.221114.001_1756843629825)
- ID 60: mcam-201117ty-2d7ee4 (mobile_TKQ1.221114.001_1756843630084)

### Fix 4: Improve Mobile Camera Registration Logic

Update the mobile app to check for existing cameras before creating new ones:

```dart
// Before registering, check if camera already exists
Future<bool> checkExistingCamera(String deviceId) async {
  final response = await http.get(
    Uri.parse('$baseUrl/cameras/mobile?device_id=$deviceId'),
    headers: await _getAuthHeaders(),
  );
  return response.statusCode == 200;
}
```

## Implementation Steps

### Step 1: Update Mobile App Discovery URL
```bash
# Update the mobile app configuration
cd ppl_meta_mobile_camera
# Edit lib/services/discovery_config_service.dart
# Change defaultDiscoveryUrl to 'http://192.168.185.107:8006'
```

### Step 2: Test Discovery Connection
```bash
# Test from mobile device network (Tailscale)
curl -s 'http://192.168.185.107:8006/api/v1/services' | grep cameras
```

### Step 3: Clean Up Duplicate Cameras
```bash
# Use authenticated request to delete duplicates
# Keep only the latest registration
```

### Step 4: Test Mobile Camera Registration
```bash
# Test the full workflow:
# 1. Mobile app discovers services
# 2. Authenticates with node service  
# 3. Registers camera with cameras service
# 4. Verifies registration
```

## Expected Results

After implementing these fixes:

1. ✅ Mobile app will find discovery configuration
2. ✅ Cameras service will be discovered at correct URL
3. ✅ Mobile camera registration will succeed without duplicates
4. ✅ Camera streaming will work end-to-end

## Network Configuration

Current setup:
- **Platform Services**: 192.168.185.107 (all services)
- **Mobile Device**: 100.73.145.39 (via Tailscale)  
- **Discovery Service**: http://192.168.185.107:8006
- **Cameras Service**: http://192.168.185.107:8005
- **Gateway Service**: http://192.168.185.107:8080

## Verification Commands

```bash
# Check service discovery
curl -s 'http://192.168.185.107:8006/api/v1/services' | grep cameras

# Test cameras service health  
curl -s 'http://192.168.185.107:8005/health'

# Test mobile cameras endpoint (requires auth)
curl -H 'Authorization: Bearer <token>' 'http://192.168.185.107:8005/api/v1/cameras/mobile'
```
