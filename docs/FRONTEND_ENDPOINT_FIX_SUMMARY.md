# Frontend Endpoint Fix Summary

**Date:** June 30, 2026  
**Task:** Update hardcoded frontend endpoints to work with Matrix and VPN backend architecture  
**Approach:** Gateway routing - all services accessed through port 8080

---

## Overview

The frontend previously had hardcoded direct connections to various backend services (ports 8002, 8003, 8005, 8006, 8009, etc.). With the new Matrix and VPN architecture, all backend services should be accessed through the API Gateway on port 8080, which handles routing to services over both local network and VPN mesh.

---

## Files Modified

### ✅ 1. `lib/services/orchestrator_api_client.dart`
**Change:** Removed hardcoded port 8002 for orchestrator service  
**Before:**
```dart
final orchestratorBaseUrl = '${gatewayUri.scheme}://${gatewayUri.host}:8002';
```
**After:**
```dart
// Route through gateway instead of direct orchestrator connection
final orchestratorBaseUrl = apiClient.baseUrl;
```

### ✅ 2. `lib/services/vision_api_client.dart`
**Change:** Changed default baseUrl from port 8003 to port 8080 (gateway)  
**Before:**
```dart
baseUrl = baseUrl ?? 'http://localhost:8003'
```
**After:**
```dart
baseUrl = baseUrl ?? 'http://localhost:8080'
```

### ✅ 3. `lib/services/discovery_service_client.dart`
**Change:** Changed default discovery service URL from port 8006 to port 8080  
**Before:**
```dart
static String _defaultDiscoveryServiceUrl = 'http://localhost:8006';
```
**After:**
```dart
static String _defaultDiscoveryServiceUrl = 'http://localhost:8080';
```

### ✅ 4. `lib/core/config.dart`
**Change:** Updated all service URLs to use gateway (baseUrl) instead of specific ports  
**Before:**
```dart
static String get camerasServiceUrl => 'http://${_resolvedBackendHost()}:8005';
static String get discoveryServiceUrl => 'http://${_resolvedBackendHost()}:8006';
```
**After:**
```dart
static String get camerasServiceUrl => baseUrl;
static String get discoveryServiceUrl => baseUrl;
```

### ✅ 5. `lib/services/communications_api_client.dart`
**Change:** Updated to use AppConfig instead of deprecated Config class  
**Before:**
```dart
import '../core/config.dart';
...
baseUrl = baseUrl ?? Config.communicationsServiceUrl;
```
**After:**
```dart
import '../core/config/app_config.dart';
...
baseUrl = baseUrl ?? AppConfig.instance.apiBaseUrl;
```

### ✅ 6. `lib/services/orchestrator_api_client.dart` (Import Fix)
**Change:** Added explicit import for authServiceProvider  
**Added:**
```dart
import '../core/services/auth_service.dart' show AuthService, authServiceProvider;
```

---

## Architecture Impact

### Before (Direct Service Connections)
```
Frontend → Orchestrator (8002)
Frontend → Vision (8003)
Frontend → Cameras (8005)
Frontend → Discovery (8006)
Frontend → Communications (8009)
```

### After (Gateway Routing)
```
Frontend → Gateway (8080) → Orchestrator (via service registry/VPN)
Frontend → Gateway (8080) → Vision (via service registry/VPN)
Frontend → Gateway (8080) → Cameras (via service registry/VPN)
Frontend → Gateway (8080) → Discovery (via service registry/VPN)
Frontend → Gateway (8080) → Communications (via service registry/VPN)
```

---

## Gateway Routing Requirements

The API Gateway at port 8080 must have routing rules for the following services:
- `/api/v1/orchestrator/*` → Orchestrator service
- `/api/v1/vision/*` → Vision service
- `/api/v1/cameras/*` → Cameras service
- `/api/v1/discovery/*` → Discovery service
- `/api/v1/communications/*` → Communications service
- `/api/v1/media/*` → Media service
- `/api/v1/users/*` → Node/User service
- `/api/v1/presence/*` → Presence service

---

## Benefits

1. **VPN Compatibility:** Gateway can route to services over VPN mesh network
2. **Matrix Integration:** Services can communicate via Matrix protocol when available
3. **Single Entry Point:** Simplified frontend configuration with one URL
4. **Service Discovery:** Gateway uses service registry to find services dynamically
5. **Failover:** Gateway can handle service failover and load balancing
6. **Security:** Centralized authentication and authorization at gateway
7. **Development:** Simpler local development with one port to manage

---

## Testing Checklist

- [ ] Verify orchestrator endpoints work through gateway
- [ ] Test vision service face detection through gateway
- [ ] Check camera operations and streaming
- [ ] Test discovery service queries
- [ ] Verify communications/audit logs access
- [ ] Test authentication flows
- [ ] Check cross-service workflows

---

## Rollback

If issues arise, previous configurations were:
- Orchestrator: Port 8002
- Vision: Port 8003  
- Cameras: Port 8005
- Discovery: Port 8006
- Communications: Port 8009

To rollback, revert the 6 files listed above to use direct port connections.

---

## Notes

- All services already using `ApiClient` class were already correctly configured
- The `app_config.dart` file was already properly set up for gateway routing
- Most API clients (analytics, media, presence, signage, etc.) didn't need changes
- The main issue was legacy code using old `Config` class or hardcoded ports

---

## Related Documentation

- Backend Matrix Integration: `docs/matrix-integration.md`
- VPN Mesh Setup: `docs/vpn-setup.md`
- Gateway Configuration: `docs/gateway-routing.md`
- Service Discovery: `ppl-meta-discovery/README.md`
