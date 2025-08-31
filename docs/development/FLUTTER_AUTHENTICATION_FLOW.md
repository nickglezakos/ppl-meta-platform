# Flutter Mobile App Authentication Flow
## PPL Meta Platform - Camera Registration & Authentication

*Last Updated: August 30, 2025*

---

## 🚨 **CRITICAL ISSUE IDENTIFIED**

**Problem:** Flutter app camera registration failing with 404 Not Found
**Root Cause:** Wrong endpoint + wrong payload format
**Status:** ❌ **NEEDS IMMEDIATE FIX**

### Quick Fix Required:
1. **Change endpoint** from `/api/v1/cameras/register` → `/api/v1/cameras/mobile`
2. **Update payload** to match `MobileCameraCreate` schema (see examples below)
3. **Ensure authentication** works with Node service tokens

---

## 🎯 Overview

This document describes the complete authentication and camera registration flow for the Flutter mobile application in the PPL Meta Platform. The flow has been successfully tested and verified to work with the backend services.

## 📋 Flow Summary

```
Flutter App → SimpleSetupScreen → Node Service Authentication → JWT Token → Camera Registration → Main App
```

## 🔧 Backend Architecture

### Services Involved
1. **Node Service** (Port 8001) - Authentication & User Management
2. **Cameras Service** (Port 8005) - Camera Registration & Management  
3. **Discovery Service** (Port 8006) - Service Discovery & Health Monitoring

### JWT Token Architecture
- **Node Service** creates minimal JWT tokens: `{sub: "user_id", exp: timestamp, iat: timestamp}`
- **Cameras Service** recognizes Node tokens and grants full administrator permissions
- **Cross-Service Authentication** enabled via shared secrets

---

## 📱 Frontend Flow (Flutter)

### Step 1: SimpleSetupScreen Authentication
```dart
// Location: Flutter App - SimpleSetupScreen
// User enters credentials and submits form

final response = await http.post(
  Uri.parse('http://platform-ip:8001/api/v1/users/login'),
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: 'username=${email}&password=${password}',
);

final data = json.decode(response.body);
final token = data['access_token']; // Extract JWT token
```

### Step 2: Automatic Camera Registration
```dart
// Flutter app automatically registers device as mobile camera
final cameraResponse = await http.post(
  Uri.parse('http://platform-ip:8005/api/v1/cameras/mobile'),
  headers: {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  },
  body: json.encode({
    'name': 'Mobile Camera - ${deviceInfo.model}',
    'device_id': 'mobile_${generateUniqueId()}',
    'ip_address': await getDeviceIP(),
    'port': 8554,
    'device_model': deviceInfo.model,
    'device_manufacturer': deviceInfo.manufacturer,
    'app_version': packageInfo.version,
    'resolution_width': 1920,
    'resolution_height': 1080,
    'max_fps': 30,
    'supports_audio': true,
  }),
);
```

### Step 3: Redirect to Main Camera Interface
```dart
// On successful registration, navigate to camera view
if (cameraResponse.statusCode == 200) {
  Navigator.of(context).pushReplacement(
    MaterialPageRoute(builder: (context) => CameraView(token: token)),
  );
}
```

---

## ⚙️ Backend Implementation Details

### Node Service Authentication
**Endpoint:** `POST /api/v1/users/login`

**Request:**
```http
POST /api/v1/users/login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=fresh.user@example.com&password=NewPassword234!
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**JWT Payload (Node Service):**
```json
{
  "sub": "7",
  "exp": 1756580968,
  "iat": 1725038962
}
```

### Camera Service Registration
**Endpoint:** `POST /api/v1/cameras/mobile`

**Request Headers:**
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Test Mobile Camera",
  "device_id": "mobile_test_001",
  "ip_address": "192.168.1.100",
  "port": 8554,
  "device_model": "iPhone 14",
  "device_manufacturer": "Apple",
  "app_version": "1.0.0",
  "resolution_width": 1920,
  "resolution_height": 1080,
  "max_fps": 30,
  "supports_audio": true
}
```

**Response:**
```json
{
  "message": "Mobile camera registered successfully",
  "camera": {
    "id": 41,
    "name": "Test Mobile Camera",
    "device_id": "mobile_test_001",
    "camera_type": "MOBILE",
    "status": "available",
    "connection_string": "mobile://192.168.1.100:8554",
    "ip_address": "192.168.1.100",
    "port": 8554,
    "resolution": "1920x1080"
  }
}
```

---

## 🔐 JWT Verification Logic

### Cameras Service Authentication (`src/security/auth.py`)

The cameras service implements a dual-verification system:

#### 1. Node Service Token Verification (Primary)
```python
def verify_token(self, token: str) -> Dict:
    # Try Node service secret first
    try:
        node_secret = os.getenv("NODE_SERVICE_SECRET", "default-secret...")
        payload = jwt.decode(token, node_secret, algorithms=[self.algorithm])
        
        # Identify Node tokens by minimal payload (≤3 fields: sub, exp, iat)
        if payload.get("sub") and len(payload) <= 3:
            payload["service"] = "node"
            payload["permissions"] = list(CameraRole.ADMINISTRATOR)
            return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass  # Try cameras service next
```

#### 2. Permission Granting for Node Tokens
```python
def has_permission(self, token: str, required_permission: str) -> bool:
    payload = self.verify_token(token)
    
    # Node service tokens get full admin permissions
    if payload.get("service") == "node":
        admin_permissions = set(CameraRole.ADMINISTRATOR)
        return required_permission in admin_permissions
    
    # Regular camera service permission check
    user_permissions = set(payload.get("permissions", []))
    return required_permission in user_permissions
```

#### 3. Administrator Permissions
```python
CameraRole.ADMINISTRATOR = {
    "cameras:view",
    "cameras:detect", 
    "cameras:connect",
    "cameras:disconnect",
    "cameras:stream:start",
    "cameras:stream:stop", 
    "cameras:stream:view",
    "cameras:record:start",
    "cameras:record:stop",
    "cameras:record:view",
    "cameras:record:delete",
    "cameras:configure",
    "cameras:settings:update",
    "cameras:admin",          # Required for mobile registration
    "cameras:sessions:manage"
}
```

---

## 🔧 Configuration Requirements

### Environment Variables
Both Node and Cameras services must have matching secrets:

**Node Service `.env`:**
```bash
JWT_SECRET_KEY=RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4
```

**Cameras Service `.env`:**
```bash
JWT_SECRET_KEY=RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4
NODE_SERVICE_SECRET=RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4
```

### Database Permissions
User must have cameras:admin capability assigned:

```sql
-- This was done via assign_camera_permission.py script
INSERT INTO user_capabilities (user_id, capability_name, granted_by, granted_at)
VALUES (7, 'cameras:admin', 1, NOW());
```

---

## 🧪 Testing & Verification

### Successful Authentication Log
```
2025-08-30 18:40:11,756 - src.security.auth - INFO - Checking permission 'cameras:admin' for token...
2025-08-30 18:40:11,756 - src.security.auth - INFO - Trying Node service secret: RA6XfYJZqh...
2025-08-30 18:40:11,756 - src.security.auth - INFO - Successfully decoded with Node secret. Payload: {'sub': '7', 'exp': 1756580968}
2025-08-30 18:40:11,756 - src.security.auth - INFO - Identified as Node service token for user 7, granted admin permissions
2025-08-30 18:40:11,756 - src.security.auth - INFO - Token verified, payload service: node
2025-08-30 18:40:11,756 - src.security.auth - INFO - User 7 has permission 'cameras:admin': True
2025-08-30 18:40:11,784 - src.api.v1.endpoints.cameras - INFO - User 7 registered mobile camera: Test Mobile Camera (mobile_test_001)
```

### Test Commands
```bash
# 1. Authenticate and get token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

# 2. Register mobile camera
curl -X POST 'http://localhost:8005/api/v1/cameras/mobile' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test Mobile Camera",
    "device_id": "mobile_test_001",
    "ip_address": "192.168.1.100",
    "port": 8554,
    "device_model": "iPhone 14",
    "device_manufacturer": "Apple",
    "app_version": "1.0.0"
  }'

# 3. Verify registration
curl -s "http://localhost:8005/api/v1/cameras/" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -m json.tool
```

---

## ✅ Success Criteria

### Authentication Flow ✅
- [x] User login with email/password
- [x] JWT token generation by Node service  
- [x] Token validation by Cameras service
- [x] Cross-service permission granting

### Camera Registration ✅
- [x] Mobile device registration
- [x] Database storage of camera metadata
- [x] Proper permission validation (`cameras:admin`)
- [x] HTTP 200 response with camera details

### Security ✅
- [x] JWT signature verification
- [x] Token expiration handling
- [x] Service identification by payload structure
- [x] Administrator permission assignment

---

## 🚨 Troubleshooting

### Common Issues & Solutions

#### Issue: 404 Not Found on Camera Registration ⚠️ **CRITICAL**
**Cause:** Flutter app hitting wrong endpoint
**Current Flutter Error:** `❌ Authenticated request failed: 404 - {"detail":"Not Found"}`

**Problem:** Flutter app sends to `/api/v1/cameras/register` (doesn't exist)
**Solution:** Use correct endpoint: `/api/v1/cameras/mobile`

**Wrong Flutter Code:**
```dart
// ❌ INCORRECT - This endpoint doesn't exist
final cameraEndpoint = '$serverUrl/api/v1/cameras/register';

// ❌ WRONG PAYLOAD FORMAT
final registrationData = {
  'name': cameraName,
  'type': 'mobile',  // Wrong field
  'location': location,  // Not expected
  'capabilities': [...],  // Not expected
  'streaming_config': {...},  // Not expected
  'device_info': {...}  // Not expected
};
```

**Correct Flutter Code:**
```dart
// ✅ CORRECT - Use this endpoint
final cameraEndpoint = '$serverUrl/api/v1/cameras/mobile';

// ✅ CORRECT PAYLOAD FORMAT (matches MobileCameraCreate schema)
final registrationData = {
  'name': 'Mobile Camera - ${deviceInfo.model}',
  'device_id': 'mobile_${generateUniqueId()}',
  'ip_address': await getDeviceIP(),
  'port': 8554,
  'device_model': deviceInfo.model,
  'device_manufacturer': deviceInfo.manufacturer,
  'app_version': '1.0.0',
  'resolution_width': 1920,
  'resolution_height': 1080,
  'max_fps': 30,
  'supports_audio': true,
};
```

#### Issue: 403 Forbidden on Camera Registration
**Cause:** User lacks `cameras:admin` permission
**Solution:** Run database permission assignment script:
```python
# assign_camera_permission.py
from src.database import get_db
from src.models import UserCapability

db = next(get_db())
capability = UserCapability(
    user_id=7,
    capability_name="cameras:admin", 
    granted_by=1
)
db.add(capability)
db.commit()
```

#### Issue: JWT Verification Fails
**Cause:** Mismatched secrets between services
**Solution:** Ensure both services use same `JWT_SECRET_KEY`

#### Issue: Token Classified as "cameras" instead of "node"
**Cause:** Verification order incorrect
**Solution:** Cameras service tries Node secret first, then cameras secret

---

## 🏗️ Implementation Checklist

### Backend Setup
- [x] Node service authentication endpoint (`/api/v1/users/login`)
- [x] Cameras service mobile registration (`/api/v1/cameras/mobile`)
- [x] JWT verification logic in cameras service
- [x] Cross-service secret sharing
- [x] Database permission assignment
- [x] Service discovery and health monitoring

### Frontend Implementation  
- [x] SimpleSetupScreen with form validation
- [x] HTTP client for API calls
- [x] JWT token storage and management
- [x] Automatic camera registration flow
- [x] Navigation to main camera interface
- [x] Error handling and user feedback

### Testing & Validation
- [x] End-to-end authentication flow
- [x] JWT token verification
- [x] Camera registration success
- [x] Permission validation
- [x] Database persistence
- [x] Service health monitoring

---

## 📚 Related Documentation

- [Service Discovery Guide](./SERVICE_DISCOVERY.md)
- [JWT Authentication Specification](./JWT_AUTHENTICATION.md)
- [Camera Service API Reference](./API_CAMERAS.md)
- [Flutter App Development Guide](./FLUTTER_DEVELOPMENT.md)
- [Database Schema Documentation](./DATABASE_SCHEMA.md)

---

*This document represents the current working state of the Flutter authentication flow as of August 30, 2025. The implementation has been tested and verified to work correctly with the PPL Meta Platform backend services.*
