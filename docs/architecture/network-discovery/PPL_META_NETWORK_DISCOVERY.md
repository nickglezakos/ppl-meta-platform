# PPL Meta Network Discovery Documentation

## Overview

This document outlines all network discovery scenarios for the PPL Meta platform, covering automatic service discovery between mobile cameras and backend services across different network configurations.

## Current Architecture

### Backend Services
- **Node Service**: Port 8001 (Authentication, User Management)
- **Gateway Service**: Port 8080 (API Gateway)
- **Media Service**: Port 8000 (Media Processing)
- **Orchestrator Service**: Port 8002 (Workflow Orchestration)
- **Vision Service**: Port 8003 (Computer Vision)
- **Cameras Service**: Port 8005 (Camera Management)
- **Nginx Proxy**: Port 80 (Reverse Proxy)

## Port Conflict Considerations

### Common Port Conflicts

**High Risk Ports:**
- **Port 80**: Apache, IIS, existing web servers, router admin interfaces
- **Port 8080**: Tomcat, Jenkins, Spring Boot, corporate proxies

**Medium Risk Ports:**
- **Port 8000**: Django dev server, Python HTTP server
- **Port 8001**: Alternative web servers, microservices

**Solutions Implemented:**
- Environment variable port configuration (`PPL_*_PORT`)
- Auto-detection of available ports during startup
- Multi-port scanning in mobile discovery algorithm
- Alternative port ranges for different environments:
  - Development: 3000-3010
  - Enterprise: 9080-9090  
  - High Security: 18080-18090

### Enhanced Discovery Algorithm

**Port-Aware Service Discovery:**
```dart
class FlexiblePortDiscovery {
  static const standardPorts = [80, 8080, 8001, 8000, 8002, 8003, 8005];
  static const developmentPorts = [3000, 3001, 3002, 3003, 3004, 3005, 3006];
  static const enterprisePorts = [9080, 9081, 9082, 9083, 9084, 9085, 9086];
  static const highSecurityPorts = [18080, 18081, 18082, 18083, 18084, 18085, 18086];
  
  Future<String?> discoverPPLMetaService(String baseUrl) async {
    final allPortSets = [standardPorts, developmentPorts, enterprisePorts, highSecurityPorts];
    
    for (final portSet in allPortSets) {
      for (final port in portSet) {
        final serviceUrl = '$baseUrl:$port';
        if (await testPPLMetaService(serviceUrl)) {
          return serviceUrl;
        }
      }
    }
    return null;
  }
}
```

### Mobile App Discovery Methods
1. **Multicast Discovery** (224.1.1.1:12345)
2. **Tailscale Device Name Resolution** (ppl-meta-server.tailnet-name.ts.net)
3. **Tailscale Network Scanning** (100.x.x.x/10)
4. **OpenVPN Network Scanning** (10.8.x.x, 192.168.255.x, custom ranges)
5. **Local Network Scanning** (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
6. **OpenCV Service Discovery** (Computer Vision endpoints)
7. **Localhost Fallback** (127.0.0.1, localhost)

## Network Discovery Scenarios

### Scenario 1: Same Local WiFi Network
**Configuration:**
- Phone: WiFi IP (e.g., 192.168.1.10)
- Services: WiFi IP (e.g., 192.168.1.5)
- Services bound to: `0.0.0.0`

**Discovery Process:**
```
1. Multicast Discovery → ✅ Should work (if multicast enabled)
2. Local Network Scan → ✅ Discovers 192.168.1.5:8001
3. Service Test → ✅ http://192.168.1.5:8001/api/v1/health
```

**Status:** ✅ **SHOULD WORK** (requires services bound to 0.0.0.0)

### Scenario 2: Phone Hotspot Network
**Configuration:**
- Phone: Hotspot gateway (e.g., 192.168.83.1)
- Mac: Hotspot client (e.g., 192.168.83.100)
- Services bound to: `0.0.0.0`

**Discovery Process:**
```
1. Multicast Discovery → ❌ May not work across hotspot
2. Local Network Scan → ✅ Discovers 192.168.83.100:8001
3. Service Test → ✅ http://192.168.83.100:8001/api/v1/health
```

**Status:** ✅ **SHOULD WORK** (requires services bound to 0.0.0.0)

### Scenario 3: Both on Tailscale (Same Local Network)
**Configuration:**
- Phone: WiFi IP (192.168.1.10) + Tailscale IP (100.64.0.15)
- Services: WiFi IP (192.168.1.5) + Tailscale IP (100.64.0.20)
- Services bound to: `0.0.0.0`

**Discovery Process:**
```
1. Multicast Discovery → ✅ Works on local network
2. Tailscale Network Scan → ✅ Discovers 100.64.0.20:8001
3. Local Network Scan → ✅ Discovers 192.168.1.5:8001 (as fallback)
```

**Status:** ✅ **WORKS PERFECTLY** (multiple discovery paths)

### Scenario 4: Both on Tailscale (Different Networks)
**Configuration:**
- Phone: Cellular/Remote WiFi + Tailscale IP (100.64.0.15)
- Services: Home WiFi + Tailscale IP (100.64.0.20)
- Services bound to: `0.0.0.0`

**Discovery Process:**
```
1. Multicast Discovery → ❌ Different networks
2. Tailscale Network Scan → ✅ Discovers 100.64.0.20:8001
3. Local Network Scan → ❌ Different local networks
```

**Status:** ✅ **WORKS VIA TAILSCALE**

### Scenario 5: Phone on Tailscale, Services Not
**Configuration:**
- Phone: WiFi + Tailscale IP (100.64.0.15)
- Services: WiFi IP (192.168.1.5), no Tailscale
- Services bound to: `0.0.0.0`

**Discovery Process:**
```
1. Multicast Discovery → ✅ Works on same local WiFi
2. Tailscale Network Scan → ❌ Services not on Tailscale
3. Local Network Scan → ✅ Discovers 192.168.1.5:8001
```

**Status:** ✅ **WORKS ON SAME WIFI**

### Scenario 6: Services on Tailscale, Phone Not
**Configuration:**
- Phone: WiFi IP (192.168.1.10), no Tailscale
- Services: WiFi IP (192.168.1.5) + Tailscale IP (100.64.0.20)
- Services bound to: `0.0.0.0`

**Discovery Process:**
```
1. Multicast Discovery → ✅ Works on local network
2. Tailscale Network Scan → ❌ Phone not on Tailscale
3. Local Network Scan → ✅ Discovers 192.168.1.5:8001
```

**Status:** ✅ **WORKS ON SAME WIFI**

### Scenario 7: Services Behind Nginx Proxy
**Configuration:**
- Phone: Any network configuration
- Services: Behind nginx proxy on port 80
- Nginx bound to: `0.0.0.0:80`

**Discovery Process:**
```
1. Standard discovery finds nginx IP
2. Health check: http://nginx-ip/health/node
3. Service URLs: http://nginx-ip/api/v1/... (routed by nginx)
```

**Status:** ✅ **WORKS** (requires nginx proxy discovery)

### Scenario 8: Docker Containerized Services
**Configuration:**
- Services: Running in Docker containers
- Exposed ports: Host network or port mapping
- Services bound to: `0.0.0.0` in containers

**Discovery Process:**
```
1. Discovery finds host IP
2. Services accessible via host:port mapping
3. Health checks work normally
```

**Status:** ✅ **WORKS** (with proper port mapping)

### Scenario 9: Services on Localhost Only
**Configuration:**
- Services bound to: `localhost` or `127.0.0.1`
- Phone: Any network (WiFi, hotspot, etc.)

**Discovery Process:**
```
1. All network discovery methods → ❌ FAIL
2. Localhost fallback → ❌ FAIL (phone can't reach localhost)
```

**Status:** ❌ **BROKEN** (services not accessible externally)

### Scenario 10: Corporate Network with Firewalls
**Configuration:**
- Phone: Corporate WiFi with restricted ports
- Services: Corporate network with firewall rules
- Multicast: Often blocked

**Discovery Process:**
```
1. Multicast Discovery → ❌ Blocked by firewall
2. Network Scanning → ❌ May be blocked
3. Manual Configuration → ✅ Required
```

**Status:** ⚠️ **REQUIRES MANUAL CONFIG**

### Scenario 11: Tailscale Device Name Discovery
**Configuration:**
- Phone: On Tailscale with device name (e.g., iphone-nick)
- Services: On Tailscale with device name (e.g., macbook-air)
- Tailscale DNS: Enabled

**Discovery Process:**
```
1. Query Tailscale device names: tailscale status --json
2. Resolve service device: macbook-air.tailnet-name.ts.net
3. Test services: http://macbook-air.tailnet-name.ts.net:8001
4. Fallback to IP discovery if DNS fails
```

**Status:** ✅ **OPTIMAL** (most reliable Tailscale method)

### Scenario 12: OpenCV Computer Vision Integration
**Configuration:**
- Phone: Mobile camera with OpenCV processing requests
- Services: PPL Meta platform + OpenCV vision service
- Vision processing: Real-time or batch processing

**Discovery Process:**
```
1. Standard service discovery (any method above)
2. Detect Vision Service: http://service-ip:8003/health
3. Verify OpenCV capabilities: GET /api/v1/vision/capabilities
4. Test vision endpoints: POST /api/v1/vision/process
```

**OpenCV-Specific Requirements:**
- Vision service with OpenCV integration
- Image upload/processing endpoints
- Real-time processing capabilities
- Result streaming or polling

**Status:** ✅ **WORKS** (with vision service discovery)

### Scenario 13: Both on OpenVPN (Same Network)
**Configuration:**
- Phone: OpenVPN client with VPN IP (e.g., 10.8.0.15)
- Services: OpenVPN server network with VPN IP (e.g., 10.8.0.5)
- OpenVPN: Traditional VPN with server/client architecture

**Discovery Process:**
```
1. Detect OpenVPN interface: tun0, tap0
2. Extract VPN network range: 10.8.0.0/24
3. Scan VPN network: 10.8.0.1 to 10.8.0.254
4. Test services: http://10.8.0.5:8001/api/v1/health
```

**Status:** ✅ **WORKS** (OpenVPN network discovery)

### Scenario 14: Both on OpenVPN (Remote Networks)
**Configuration:**
- Phone: OpenVPN client from cellular/remote WiFi
- Services: OpenVPN server at fixed location
- OpenVPN: Site-to-site or road warrior configuration

**Discovery Process:**
```
1. Connect to OpenVPN server
2. Receive assigned VPN IP range
3. Scan OpenVPN network for services
4. Access services via VPN tunnel
```

**Status:** ✅ **WORKS VIA OPENVPN**

### Scenario 15: Mixed OpenVPN/Local Network
**Configuration:**
- Phone: Local WiFi + OpenVPN client (dual connectivity)
- Services: Local network + OpenVPN server
- Mixed: Services accessible via both local and VPN

**Discovery Process:**
```
1. Try local network discovery first (faster)
2. Fallback to OpenVPN network scanning
3. Prefer local connections for better performance
4. Use VPN for remote access scenarios
```

**Status:** ✅ **OPTIMAL** (dual connectivity with local preference)

### Scenario 16: OpenVPN with Custom Network Ranges
**Configuration:**
- Phone: OpenVPN with custom subnet (e.g., 192.168.255.x)
- Services: Corporate OpenVPN with non-standard ranges
- Custom: Configured network ranges (172.20.x.x, etc.)

**Discovery Process:**
```
1. Parse OpenVPN configuration for custom ranges
2. Detect VPN interfaces and their assigned IPs
3. Calculate network ranges from VPN configuration
4. Scan custom ranges for PPL Meta services
```

**Status:** ✅ **WORKS** (with configuration parsing)

## Current Issues Identified

### Platform Issues
1. **Services bound to localhost**: Many services default to localhost binding
2. **Nginx configuration**: May not be configured for external access
3. **Multicast service**: May not be implemented or enabled
4. **Port firewall**: Services may not be accessible across networks

### Mobile App Issues
1. **Limited localhost discovery**: Current localhost fallback insufficient
2. **No manual configuration option**: No UI for manual server entry
3. **Nginx proxy detection**: App doesn't know how to discover nginx-proxied services
4. **Service health check endpoints**: Different services have different health endpoints

## Required Improvements

### Backend Platform Changes
1. **Default to 0.0.0.0 binding** for all services
2. **Implement multicast announcements** for automatic discovery
3. **Standardize health check endpoints** across all services
4. **Update nginx configuration** for external access
5. **Add service discovery API** endpoint

### Mobile App Changes
1. **Add manual server configuration** UI option
2. **Improve nginx proxy detection** and routing
3. **Add network diagnostics** and troubleshooting tools
4. **Implement service-specific health checks**
5. **Add connectivity status indicators**

## Testing Matrix

### Network Discovery Testing

| Scenario | Multicast | Tailscale DNS | Tailscale IP | OpenVPN | Local | Nginx | OpenCV | Port Flexibility | Status |
|----------|-----------|---------------|--------------|---------|-------|-------|--------|------------------|--------|
| Same WiFi (Standard) | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ | 80,8080,8001 | PASS |
| Same WiFi (Dev Mode) | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ | 3000,3001,3002 | TEST |
| Same WiFi (Enterprise) | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ | 9080,9081,9082 | TEST |
| Hotspot | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ | Standard ports | PASS |
| Tailscale Same | ✅ | ✅ | ✅ | N/A | ✅ | ✅ | ✅ | Standard ports | PASS |
| Tailscale Remote | N/A | ✅ | ✅ | N/A | N/A | ✅ | ✅ | Standard ports | PASS |
| Mixed Tailscale | ✅ | ✅ | ✅ | N/A | ✅ | ✅ | ✅ | Standard ports | PASS |
| Tailscale Corporate | N/A | ✅ | ✅ | N/A | N/A | ✅ | ✅ | Enterprise ports | PASS |
| Docker Local | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ | Mapped ports | PASS |
| Docker + Nginx | N/A | N/A | N/A | N/A | N/A | ✅ | ✅ | 80 only | PASS |
| Docker Multi | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ | Multiple ranges | TEST |
| Docker Production | N/A | N/A | N/A | N/A | N/A | ✅ | ✅ | Load balancer | TEST |
| OpenVPN Same | ✅ | N/A | N/A | ✅ | ✅ | ✅ | ✅ | Standard ports | TEST |
| OpenVPN Remote | N/A | N/A | N/A | ✅ | N/A | ✅ | ✅ | Standard ports | TEST |
| Mixed OpenVPN | ✅ | N/A | N/A | ✅ | ✅ | ✅ | ✅ | Standard ports | TEST |
| OpenVPN Custom | N/A | N/A | N/A | ✅ | N/A | ✅ | ✅ | Custom range | TEST |

### Port Conflict Testing

| Environment | Standard Ports | Conflict Scenario | Alternative Ports | Test Status |
|-------------|----------------|-------------------|-------------------|-------------|
| Development | 3000, 8080, 8000 | React dev server | 3001, 8081, 8001 | ⏳ TODO |
| Corporate | 80, 8080 | Apache/Tomcat running | 9080, 9081 | ⏳ TODO |
| Enterprise | 8000-8010 | Django/microservices | 18080-18090 | ⏳ TODO |
| High Security | Standard range | Port scanning restrictions | 20000+ range | ⏳ TODO |
| Docker | Host mapping | Port already bound | Dynamic allocation | ⏳ TODO |

### Discovery Method Priority Testing

**Test Each Port Range with Each Discovery Method:**

1. **Multicast Discovery** + Port Scanning
   - Standard ports (80, 8080, 8001, 8000, 8002, 8003, 8005)
   - Development ports (3000-3006)
   - Enterprise ports (9080-9086)
   - High security ports (18080-18086)

2. **Tailscale Integration** + Port Flexibility
   - Device name resolution across all port ranges
   - IP scanning with configurable port lists
   - Fallback port detection

3. **OpenVPN Support** + Port Discovery
   - Interface detection with port scanning
   - Custom range + custom ports
   - Mixed network port detection

4. **Manual Configuration** + Port Validation
   - Custom port entry and validation
   - Port availability checking
   - Service type detection by port
| Phone Hotspot (0.0.0.0) | ❌ | N/A | N/A | N/A | ✅ | ✅ | ✅ | PASS |
| Both Tailscale (Same) | ✅ | ✅ | ✅ | N/A | ✅ | ✅ | ✅ | OPTIMAL |
| Both Tailscale (Remote) | ❌ | ✅ | ✅ | N/A | ❌ | ✅ | ✅ | OPTIMAL |
| Phone Tailscale Only | ✅ | ❌ | ❌ | N/A | ✅ | ✅ | ✅ | PASS |
| Services Tailscale Only | ✅ | ❌ | ❌ | N/A | ✅ | ✅ | ✅ | PASS |
| Nginx Proxy | Varies | Varies | Varies | Varies | Varies | ✅ | ✅ | PASS |
| Docker Services | Varies | Varies | Varies | Varies | ✅ | ✅ | ✅ | PASS |
| Localhost Only | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **FAIL** |
| Corporate Network | ❌ | Varies | Varies | ✅ | ❌ | Manual | ✅ | **MANUAL** |
| Tailscale Device Names | N/A | ✅ | Fallback | N/A | N/A | ✅ | ✅ | **OPTIMAL** |
| OpenCV Integration | Varies | Varies | Varies | Varies | Varies | ✅ | ✅ | **PASS** |
| Both OpenVPN (Same) | ❌ | N/A | N/A | ✅ | ❌ | ✅ | ✅ | **PASS** |
| Both OpenVPN (Remote) | ❌ | N/A | N/A | ✅ | ❌ | ✅ | ✅ | **PASS** |
| Mixed OpenVPN/Local | ✅ | N/A | N/A | ✅ | ✅ | ✅ | ✅ | **OPTIMAL** |
| OpenVPN Custom Ranges | ❌ | N/A | N/A | ✅ | ❌ | ✅ | ✅ | **PASS** |

## Implementation Priority

### High Priority (Critical for basic functionality)
1. Change all services to bind to `0.0.0.0`
2. Add manual server configuration in mobile app
3. Fix nginx proxy discovery

### Medium Priority (Enhanced reliability)
1. Implement multicast service announcements
2. Standardize health check endpoints
3. Add network diagnostics tools

### Low Priority (Advanced features)
1. Corporate network support
2. Advanced firewall traversal
3. Service mesh integration

## Success Criteria

A successful network discovery implementation should:
1. **Automatically discover services** in 80% of common scenarios
2. **Provide manual configuration** for remaining 20%
3. **Show clear error messages** when discovery fails
4. **Work across all supported network types** (WiFi, hotspot, Tailscale)
5. **Be resilient to network changes** during operation

---

*Last Updated: August 21, 2025*
*Author: PPL Meta Development Team*
