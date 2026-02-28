# PPL Meta Authentication Processes

## Document Overview
**Created:** December 12, 2025  
**Purpose:** Document authentication flow, issues encountered, and fixes applied across the PPL Meta platform

## Table of Contents
1. [Authentication Architecture](#authentication-architecture)
2. [Gateway Proxy Authentication](#gateway-proxy-authentication)
3. [Issues Encountered](#issues-encountered)
4. [Fixes Applied](#fixes-applied)
5. [Testing & Verification](#testing--verification)

---

## Authentication Architecture

### System Components
```
Frontend (Flutter) → Gateway (8080) → Backend Services
                                    ├─ Media (8000)
                                    ├─ Node (8001)
                                    ├─ Orchestrator (8002)
                                    ├─ Vision (8003)
                                    ├─ Cameras (8005)
                                    ├─ Discovery (8006)
                                    ├─ Bootcore (8007)
                                    └─ VMeta (8008)
```

### Token Flow
1. **User Login** → Node Service validates credentials
2. **JWT Token Generated** → Node Service returns token
3. **Frontend Stores Token** → Secure storage
4. **All Requests** → Frontend includes `Authorization: Bearer <token>`
5. **Gateway Proxies** → Forwards request + auth header to backend
6. **Backend Validates** → Each service validates JWT independently

### JWT Token Structure
```json
{
  "sub": "7",           // User ID
  "exp": 1765486565    // Expiration timestamp
}
```

---

## Gateway Proxy Authentication

### Current Implementation
**Location:** `ppl-meta-gateway/src/api/v1/router.py`

The gateway uses proxy functions to forward requests to backend services:
- `_proxy_to_media_service()` - Media service proxy
- `_proxy_to_cameras_service()` - Cameras service proxy  
- `_proxy_to_vmeta_service()` - VMeta service proxy
- `_proxy_to_node_service()` - Node service proxy
- `_proxy_to_vision_service()` - Vision service proxy
- `_proxy_to_orchestrator_service()` - Orchestrator service proxy

### Header Forwarding Logic
```python
# Get headers (exclude host to avoid conflicts)
headers = dict(request.headers)
headers.pop("host", None)

# Forward headers to backend service
response = await client.request(
    method=method,
    url=target_url,
    headers=headers,  # All headers including Authorization
    content=body,
    params=dict(request.query_params),
)
```

**Expected Behavior:** All headers, including `Authorization`, should be forwarded to backend services.

---

## Issues Encountered

### Issue #1: 401 Unauthorized Errors After Navigation
**Date:** December 12, 2025  
**Reported By:** User  
**Symptoms:**
- User successfully logged in
- Face detection working correctly
- Upon navigation to different screens, received 401 errors
- Unable to view recording results despite successful detection

**Affected Endpoints:**
```
GET /api/v1/cameras/ → 401
GET /api/v1/cameras/{device_id}/mvr-count → 401
GET /api/v1/media/search → 401
```

**Error Logs:**
```
Gateway Log:
2025-12-12 12:27:37,254 - status_code: 401, path: /api/v1/cameras/rtsp_192.168.1.76_554/mvr-count

2025-12-12 12:27:30,975 - HTTP Request: GET http://localhost:8000/api/v1/media/search → 401 Unauthorized
```

**Initial Hypothesis:**
1. Token expiration (ruled out - user just logged in)
2. Gateway not forwarding Authorization header
3. Backend services rejecting valid tokens

---

## Fixes Applied

### Investigation Steps

#### Step 1: Verify Token Validity
**Command:**
```bash
# Check if frontend is sending Authorization header
grep "Authorization" ppl-meta-gateway/logs/ppl-meta-gateway.log
```

**Finding:** Need to add logging to see if Authorization header is present in incoming requests.

#### Step 2: Add Debug Logging
**File:** `ppl-meta-gateway/src/api/v1/router.py`

Added logging to all proxy functions to track auth header flow:

```python
# 🔍 DEBUG: Log authorization header status
auth_header = headers.get("authorization", "MISSING")
logger.info(f"🔐 [SERVICE-PROXY] {method} {path} - Auth header: {'Present' if auth_header != 'MISSING' else 'MISSING'}")
```

**Applied to:**
- `_proxy_to_media_service()` - Line ~353
- `_proxy_to_cameras_service()` - Line ~902
- `_proxy_to_vmeta_service()` - Line ~1562

**Testing Command:**
```bash
# Monitor auth header presence in gateway logs
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-gateway/logs/ppl-meta-gateway.log | grep "🔐"
```

**Expected Output:**
```
🔐 [MEDIA-PROXY] GET /api/v1/media/search - Auth header: Present
🔐 [CAMERAS-PROXY] GET /api/v1/cameras/ - Auth header: Present
🔐 [VMETA-PROXY] GET /api/v1/cameras/{id}/mvr-count - Auth header: Present
```

If "MISSING" appears, the frontend is not sending the Authorization header.

---

### Fix #1: Verify Authorization Header Forwarding

**Status:** IN PROGRESS - Debugging

**Next Steps:**
1. Wait for uvicorn auto-reload
2. Navigate app to trigger 401 errors
3. Check logs for auth header presence
4. Determine root cause based on findings

---

## Testing & Verification

### Test Scenarios

#### Test 1: Login and Token Storage
```bash
# Check if token is stored after login
flutter run
# Login via UI
# Check browser console for token storage confirmation
```

#### Test 2: Header Forwarding
```bash
# Start all services
# Navigate to cameras page
# Check gateway logs
tail -50 ppl-meta-gateway/logs/ppl-meta-gateway.log | grep "🔐"
```

#### Test 3: Direct Backend Auth Test
```bash
# Test if backend accepts token directly (bypass gateway)
TOKEN="<your-jwt-token>"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/media/search
```

---

## Common Auth Issues & Solutions

### Issue: Token Expiration
**Symptoms:** 401 errors after some time  
**Solution:** Check token expiration time, implement token refresh

### Issue: Missing Authorization Header
**Symptoms:** 401 on all requests  
**Solution:** Verify frontend is including Authorization header

### Issue: Gateway Not Forwarding Header
**Symptoms:** Direct backend calls work, gateway calls fail  
**Solution:** Check gateway proxy header forwarding logic

### Issue: Backend Token Validation Failure
**Symptoms:** Token present but still 401  
**Solution:** Check JWT secret consistency across services

---

## Service Authentication Configuration

### Media Service (Port 8000)
- **Auth Method:** JWT Bearer Token
- **Validation:** Checks JWT signature and expiration
- **Config Location:** `ppl-meta-media/src/core/auth.py`

### Cameras Service (Port 8005)
- **Auth Method:** JWT Bearer Token
- **Validation:** Checks JWT signature and expiration
- **Config Location:** `ppl-meta-cameras/src/core/auth.py`

### VMeta Service (Port 8008)
- **Auth Method:** JWT Bearer Token
- **Validation:** Checks JWT signature and expiration
- **Config Location:** `ppl-meta-vmeta/src/core/auth.py`

---

## Status

**Last Updated:** December 12, 2025  
**Current Status:** Investigating 401 errors  
**Debug Logging:** ✅ Added  
**Issue Identified:** 🔄 In Progress  
**Fix Applied:** ⏸️ Pending  

---

## Notes

- All backend services use the same JWT secret for token validation
- Token format: `Bearer <jwt-token>`
- Default token expiration: Set in Node service configuration
- Gateway timeout: 30s for most services, 60s for vmeta

