# Issue: Implement Robust Network Service Discovery for All Network Scenarios

## Summary
The PPL Meta platform currently has limited network discovery capabilities that fail in common real-world scenarios, particularly when services are bound to localhost or when using phone hotspots. This issue tracks implementing comprehensive automatic service discovery across all network configurations.

## Problem Statement
Based on comprehensive testing documented in `PPL_META_NETWORK_DISCOVERY.md`, the current platform has these critical issues:

### Blocking Issues
1. **Services bound to localhost**: Most services default to `localhost`/`127.0.0.1` binding, making them inaccessible from external devices
2. **No multicast announcements**: Services don't broadcast their availability for automatic discovery
3. **Inconsistent health endpoints**: Different services use different health check URLs
4. **Nginx not externally accessible**: Proxy configuration may not support external access

### Impact
- Mobile cameras cannot automatically discover services on different networks
- Manual configuration required in most real-world scenarios
- Poor user experience for zero-configuration setup

## Required Changes

### 1. Service Binding Configuration (HIGH PRIORITY)
**Affected Services:**
- Node Service (port 8001)
- Media Service (port 8000) 
- Vision Service (port 8003)

**Changes Required:**
```bash
# Current (problematic)
python src/main.py  # defaults to localhost

# Required
python src/main.py --host 0.0.0.0  # accessible externally
```

**Implementation:**
- [ ] Update Node Service main.py to bind to 0.0.0.0
- [ ] Update Media Service main.py to bind to 0.0.0.0  
- [ ] Update Vision Service main.py to bind to 0.0.0.0
- [ ] Add environment variable `HOST` support (default: 0.0.0.0)
- [ ] Update Docker configurations for external access
- [ ] Update tasks.json to use --host 0.0.0.0

### 2. Standardize Health Check Endpoints (HIGH PRIORITY)
**Current State:**
- Node Service: `/api/v1/health`
- Gateway Service: `/health` 
- Media Service: `/health`
- Others: Various inconsistent endpoints

**Required:**
- [ ] Standardize all services to use `/health` endpoint
- [ ] Ensure health checks return consistent JSON format
- [ ] Add service identification in health response:
```json
{
  "status": "healthy",
  "service": "ppl-meta-node",
  "version": "1.0.0",
  "timestamp": "2025-08-21T11:32:14.189Z"
}
```

### 3. Implement Multicast Service Announcements (MEDIUM PRIORITY)
**Requirements:**
- [ ] Create multicast announcement service
- [ ] Broadcast service availability on 224.1.1.1:12345
- [ ] Include service type, IP, port, and health endpoint
- [ ] Implement graceful shutdown announcements

**Message Format:**
```json
{
  "service_type": "ppl-meta-node",
  "ip": "192.168.1.5",
  "port": 8001,
  "health_endpoint": "/health",
  "discovery_timestamp": "2025-08-21T11:32:14.189Z"
}
```

### 4. Update Nginx Configuration (HIGH PRIORITY)
**Current Issues:**
- May not bind to external interfaces
- Health endpoint routing needs verification

**Required Changes:**
- [ ] Update nginx-local-dev.conf to bind to 0.0.0.0:80
- [ ] Verify health endpoint routing (/health/node, /health/media, etc.)
- [ ] Add service discovery endpoint: `/api/discovery/services`
- [ ] Test external accessibility

### 5. Add OpenCV Vision Service Integration (MEDIUM PRIORITY)
Create dedicated endpoints for OpenCV computer vision functionality:

**Vision Service Requirements:**
- [ ] Standardize Vision Service health endpoint: `/health`
- [ ] Add OpenCV capabilities endpoint: `/api/v1/vision/capabilities`
- [ ] Implement image processing endpoints: `/api/v1/vision/process`
- [ ] Add real-time processing support
- [ ] Include OpenCV version and feature information in health response

**Capabilities Endpoint Response:**
```json
{
  "opencv_enabled": true,
  "opencv_version": "4.8.1",
  "supported_formats": ["jpg", "png", "mp4", "rtsp"],
  "features": [
    "object_detection",
    "face_recognition", 
    "motion_detection",
    "image_enhancement"
  ],
  "real_time_processing": true
}
```

### 6. Add Service Discovery API Endpoint (MEDIUM PRIORITY)
Create centralized service discovery endpoint accessible via Gateway/Nginx:

**Endpoint:** `GET /api/discovery/services`
**Response:**
```json
{
  "services": [
    {
      "name": "ppl-meta-node",
      "url": "http://192.168.1.5:8001",
      "health_url": "http://192.168.1.5:8001/health",
      "status": "healthy"
    },
    {
      "name": "ppl-meta-cameras", 
      "url": "http://192.168.1.5:8005",
      "health_url": "http://192.168.1.5:8005/health",
      "status": "healthy"
    }
  ],
  "discovery_timestamp": "2025-08-21T11:32:14.189Z"
}
```

## Testing Requirements

### Network Scenarios to Test
1. **Same WiFi Network** - Services and mobile on same WiFi
2. **Phone Hotspot** - Mobile as hotspot, services connected to hotspot  
3. **Tailscale Networks** - Both devices on Tailscale VPN
4. **Mixed Networks** - One device on Tailscale, other on local WiFi
5. **Docker Deployment** - Services running in containers
6. **Nginx Proxy** - Services behind reverse proxy

### Test Cases
- [ ] Services discoverable via multicast on local network
- [ ] Health checks accessible from external devices
- [ ] Service discovery API returns correct information
- [ ] All network scenarios in testing matrix pass

## Acceptance Criteria
1. ✅ All services bind to 0.0.0.0 by default
2. ✅ Multicast announcements work on local networks  
3. ✅ Health endpoints standardized and accessible
4. ✅ Service discovery API provides accurate service information
5. ✅ Mobile app can discover services in 8/10 documented scenarios
6. ✅ Manual configuration available for remaining scenarios

## Dependencies
- Related mobile app issue: "Implement Comprehensive Network Discovery for Mobile Camera App"
- Documentation: `PPL_META_NETWORK_DISCOVERY.md`

## Priority
**HIGH** - Blocking mobile camera automatic setup functionality

## Estimated Effort
- Service binding updates: 4 hours
- Health endpoint standardization: 6 hours
- Multicast implementation: 8 hours  
- Nginx configuration: 2 hours
- Service discovery API: 6 hours
- Testing and validation: 8 hours

**Total: ~34 hours**
