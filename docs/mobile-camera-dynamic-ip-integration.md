# Mobile Camera Dynamic IP Integration Guide

## Overview

The PPL Meta Platform now supports dynamic IP address detection and updating for mobile cameras. This allows mobile devices to automatically update their network location when connecting to different WiFi networks or when their IP address changes.

## Problem Solved

Previously, mobile cameras were registered with a static IP address, leading to connection failures when:
- The mobile device connects to a different WiFi network
- The router assigns a new IP address via DHCP
- The device moves between network environments

## Mobile App Integration

### 1. IP Detection (Already Implemented)

The mobile app already includes robust IP detection in `simplified_discovery_client.dart`:

```dart
Future<String?> getMyIPAddress() async {
  try {
    // Use socket connection to detect actual local IP
    final socket = await Socket.connect('8.8.8.8', 80);
    final localIP = socket.address.address;
    socket.destroy();
    
    if (_isLocalNetworkIP(localIP)) {
      return localIP;
    }
  } catch (e) {
    // Fallback to network interface detection
    final interfaces = await NetworkInterface.list();
    // ... implementation details
  }
}
```

### 2. Registration with Dynamic IP

When registering a mobile camera, the app should always send the current detected IP:

```dart
final deviceIP = await getMyIPAddress();
final requestBody = {
  'name': cameraName,
  'device_id': deviceId,
  'ip_address': deviceIP,  // Dynamically detected IP
  'port': 8554,
  // ... other fields
};
```

### 3. Backend Response Handling

The backend now handles existing cameras gracefully:

**Previous Response (Confusing):**
```json
{
  "message": "Mobile camera already registered",
  "camera": { ... }
}
```

**New Response (Clear Update):**
```json
{
  "message": "Mobile camera updated with new IP address",
  "camera": {
    "connection_string": "mobile://192.168.1.200:8554",
    "ip_address": "192.168.1.200"
  }
}
```

### 4. Dynamic IP Update Endpoint

New endpoint for mobile apps to update their IP when network changes are detected:

```dart
// Call this when the app detects network change
Future<void> updateMobileIP() async {
  final newIP = await getMyIPAddress();
  
  final response = await http.post(
    Uri.parse('$baseUrl/api/v1/cameras/mobile/$deviceId/update-ip'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
    body: json.encode({
      'ip_address': newIP,
      'port': 8554,
    }),
  );
}
```

## Backend Implementation

### 1. Mobile Camera Registration

**Endpoint:** `POST /api/v1/cameras/mobile`

**Behavior:**
- If camera doesn't exist: Creates new camera with provided IP
- If camera exists: Updates IP address and connection string
- Always returns success with current camera info

### 2. Mobile Camera Update

**Endpoint:** `PUT /api/v1/cameras/mobile/{device_id}`

**New fields:**
```json
{
  "ip_address": "192.168.1.200",
  "port": 8554
}
```

### 3. Quick IP Update

**Endpoint:** `POST /api/v1/cameras/mobile/{device_id}/update-ip`

**Optimized for frequent IP changes:**
```json
{
  "ip_address": "192.168.1.200",
  "port": 8554
}
```

**Response:**
```json
{
  "message": "Mobile camera IP updated successfully",
  "old_connection": "mobile://192.168.1.175:8554",
  "new_connection": "mobile://192.168.1.200:8554"
}
```

## Connection String Format

The backend dynamically constructs connection strings:
- **Format:** `mobile://{ip_address}:{port}`
- **Example:** `mobile://192.168.1.200:8554`

This allows the streaming service to know exactly where to connect to the mobile camera.

## Mobile App Recommendations

### 1. Network Change Detection

Monitor network state changes and update IP when detected:

```dart
connectivity.onConnectivityChanged.listen((result) async {
  if (result == ConnectivityResult.wifi) {
    // WiFi connected - update IP
    await updateMobileIP();
  }
});
```

### 2. Periodic IP Verification

Periodically check if IP has changed:

```dart
Timer.periodic(Duration(minutes: 5), (timer) async {
  final currentIP = await getMyIPAddress();
  if (currentIP != lastKnownIP) {
    await updateMobileIP();
    lastKnownIP = currentIP;
  }
});
```

### 3. Error Handling

Handle registration errors gracefully:

```dart
try {
  final response = await registerMobileCamera();
  if (response['message'].contains('updated with new IP')) {
    // IP was updated successfully
    showSuccess('Camera reconnected with new network');
  }
} catch (e) {
  // Handle actual errors
}
```

## Testing

### 1. Registration Test

```bash
curl -H 'Authorization: Bearer TOKEN' \
  -H 'Content-Type: application/json' \
  -X POST 'http://localhost:8005/api/v1/cameras/mobile' \
  -d '{
    "device_id": "mobile_TEST_001",
    "name": "Test Mobile Camera",
    "ip_address": "192.168.1.100",
    "port": 8554
  }'
```

### 2. IP Update Test

```bash
curl -H 'Authorization: Bearer TOKEN' \
  -H 'Content-Type: application/json' \
  -X POST 'http://localhost:8005/api/v1/cameras/mobile/mobile_TEST_001/update-ip' \
  -d '{
    "ip_address": "192.168.1.200",
    "port": 8554
  }'
```

### 3. Connection Verification

```bash
curl -H 'Authorization: Bearer TOKEN' \
  'http://localhost:8005/api/v1/cameras/mobile_TEST_001/info'
```

## Benefits

1. **Seamless Network Transitions:** Mobile cameras work across different WiFi networks
2. **Automatic IP Updates:** No manual reconfiguration needed
3. **Robust Connection:** Backend always has current mobile device location
4. **Better User Experience:** "Camera registration error" messages eliminated
5. **Scalable Architecture:** Supports multiple mobile cameras with changing IPs

## Migration for Existing Mobile Apps

Existing mobile apps will automatically benefit from this update:
1. Next registration attempt will update the IP address
2. Backend handles the transition transparently
3. No breaking changes to existing API calls
4. Frontend error handling becomes simpler

This resolves the three mobile app issues:
- ✅ "Camera registration throwing an error" → Now updates IP successfully
- ✅ "Mobile camera connection failures" → Backend uses current IP
- ✅ "Not connected to streaming server" → Proper connection strings generated
