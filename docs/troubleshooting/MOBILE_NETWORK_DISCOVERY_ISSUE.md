# Issue: Implement Comprehensive Network Discovery for Mobile Camera App

## Summary
The mobile camera app currently fails to discover PPL Meta services in most real-world network scenarios. This issue implements robust network discovery with fallback mechanisms and manual configuration options to ensure reliable service discovery across all documented network configurations.

## Problem Statement
Testing shows the mobile app fails service discovery in critical scenarios:

### Current Failures
1. **Phone Hotspot Networks**: Services not discoverable when phone provides hotspot
2. **No Manual Configuration**: No UI option when auto-discovery fails  
3. **Localhost-Only Discovery**: Inadequate fallback for localhost-bound services
4. **Nginx Proxy Discovery**: App doesn't properly detect nginx-proxied services
5. **Poor Error Messages**: Generic failures without helpful troubleshooting

### User Impact
- Zero-input camera registration fails in most scenarios
- Users cannot manually configure server when auto-discovery fails
- Poor user experience requiring technical intervention

## Required Enhancements

### 1. Enhanced Network Discovery Algorithm (HIGH PRIORITY)

**Current Discovery Order:**
```dart
1. Multicast Discovery (224.1.1.1:12345)
2. Tailscale Network Scan (100.x.x.x/10) 
3. Local Network Scan (192.168.x.x, 10.x.x.x, 172.x.x.x)
4. Localhost Fallback (localhost, 127.0.0.1)
```

**Enhanced Discovery Algorithm:**
```dart
1. Multicast Discovery (224.1.1.1:12345)
2. Tailscale Device Name Resolution (device-name.tailnet.ts.net)
3. Tailscale Network Scan (100.x.x.x/10) 
4. OpenVPN Network Scan (10.8.x.x, 192.168.255.x, custom ranges)
5. Local Network Scan (192.168.x.x, 10.x.x.x, 172.x.x.x)
6. OpenCV Vision Service Discovery (port 8003)
7. Localhost Fallback (localhost, 127.0.0.1)
```

**Implementation:**
```dart
// Enhanced OpenVPN network discovery
Future<List<String>> discoverOpenVPNNetworks() async {
  try {
    final networks = <String>[];
    
    // Common OpenVPN network ranges
    final commonRanges = [
      '10.8.0.0/24',      // Default OpenVPN range
      '10.8.1.0/24',      // Alternative range
      '192.168.255.0/24', // Custom range
      '172.20.0.0/24',    // Corporate range
    ];
    
    // Detect VPN interfaces (tun0, tap0, etc.)
    final interfaces = await NetworkInterface.list();
    for (final interface in interfaces) {
      if (interface.name.startsWith('tun') || 
          interface.name.startsWith('tap') ||
          interface.name.startsWith('ovpn')) {
        
        for (final address in interface.addresses) {
          if (address.type == InternetAddressType.IPv4) {
            final network = _calculateNetworkRange(address.address);
            if (network != null) networks.add(network);
          }
        }
      }
    }
    
    // Add common ranges if no VPN interfaces detected
    if (networks.isEmpty) {
      networks.addAll(commonRanges);
    }
    
    return networks;
  } catch (e) {
    return ['10.8.0.0/24']; // Fallback to common range
  }
}

// Enhanced Tailscale device name discovery
Future<List<String>> discoverTailscaleDevices() async {
  try {
    // Query Tailscale status for device names
    final result = await Process.run('tailscale', ['status', '--json']);
    final data = json.decode(result.stdout);
    
    final devices = <String>[];
    for (final peer in data['Peer']) {
      final deviceName = peer['DNSName']; // e.g., "macbook-air.tailnet.ts.net"
      if (deviceName != null) devices.add(deviceName);
    }
    return devices;
  } catch (e) {
    return []; // Fallback to IP scanning
  }
}

// OpenCV vision service discovery
Future<bool> discoverVisionService(String baseUrl) async {
  try {
    // Test vision service health
    final healthResponse = await http.get('$baseUrl:8003/health');
    if (healthResponse.statusCode != 200) return false;
    
    // Verify OpenCV capabilities
    final capResponse = await http.get('$baseUrl:8003/api/v1/vision/capabilities');
    final capabilities = json.decode(capResponse.body);
    
    return capabilities['opencv_enabled'] == true;
  } catch (e) {
    return false;
  }
}

// Enhanced localhost discovery variants
final localhostVariants = [
  'http://localhost',
  'http://127.0.0.1', 
  'http://localhost:8001',
  'http://127.0.0.1:8001',
  'http://localhost:8080',
  'http://127.0.0.1:8080',
  'http://localhost:8003', // Vision service
];

// Calculate network range from IP address
String? _calculateNetworkRange(String ipAddress) {
  try {
    final parts = ipAddress.split('.');
    if (parts.length == 4) {
      // Assume /24 subnet
      return '${parts[0]}.${parts[1]}.${parts[2]}.0/24';
    }
  } catch (e) {
    // Ignore parsing errors
  }
  return null;
}
```

### 2. Manual Server Configuration UI (HIGH PRIORITY)

**Requirements:**
- [ ] Add "Manual Setup" button on discovery failure
- [ ] Server URL input field with validation
- [ ] Connection test before proceeding  
- [ ] Save successful configurations for future use
- [ ] Clear error messages and troubleshooting tips

**UI Flow:**
```
Discovery Failed Screen
├── "Retry Discovery" button
├── "Manual Setup" button  
└── "Troubleshooting Tips" expandable section

Manual Setup Screen  
├── Server URL input (http://192.168.1.5:8001)
├── "Test Connection" button
├── Connection status indicator
└── "Save & Continue" button
```

**Implementation Files:**
- [ ] `lib/screens/manual_server_setup_screen.dart`
- [ ] `lib/services/manual_server_configuration_service.dart`
- [ ] Update `lib/screens/discovery_screen.dart`

### 3. Network Diagnostics and Troubleshooting (MEDIUM PRIORITY)

**Features:**
- [ ] Network interface detection and display
- [ ] Current IP address and network info
- [ ] Connectivity test results with detailed errors
- [ ] Network type detection (WiFi, cellular, hotspot, Tailscale)
- [ ] Service reachability matrix

**Diagnostics Display:**
```dart
Network Information:
├── Interface: wlan0 (WiFi)
├── IP Address: 192.168.83.154  
├── Network: 192.168.83.0/24
├── Gateway: 192.168.83.1
└── Tailscale: Not connected

Discovery Results:
├── Multicast: ❌ No responses (8s timeout)
├── Local Scan: ❌ No services found
├── Localhost: ❌ Connection refused  
└── Manual: ⏳ Not tested
```

### 4. Improved Service Health Checks (HIGH PRIORITY)

**Current Issues:**
- Different services use different health endpoints
- App assumes `/api/v1/health` for all services
- No nginx proxy health check support

**Enhancements:**
- [ ] Support multiple health endpoint formats
- [ ] Implement nginx proxy health checks
- [ ] Add service-specific validation
- [ ] Retry logic with exponential backoff

**Health Check Strategy:**
```dart
// Service-specific health checks
final healthEndpoints = {
  'node': ['/api/v1/health', '/health'],
  'gateway': ['/health'],
  'media': ['/health'],
  'cameras': ['/health'],
  'nginx': ['/health/node', '/health/gateway'],
};

// Test multiple endpoints per service
for (String endpoint in healthEndpoints[serviceType]) {
  try {
    final response = await testEndpoint(endpoint);
    if (response.statusCode == 200) return true;
  } catch (e) {
    continue; // Try next endpoint
  }
}
```

### 5. Service Discovery Caching and Persistence (MEDIUM PRIORITY)

**Requirements:**
- [ ] Cache successful discovery results
- [ ] Persist manual configurations
- [ ] Implement discovery result expiration
- [ ] Add discovery history for debugging

**Implementation:**
```dart
class ServiceDiscoveryCache {
  // Cache successful discoveries for 1 hour
  Map<String, CachedDiscovery> _cache = {};
  
  Future<void> cacheDiscovery(String networkId, DiscoveryResult result);
  Future<DiscoveryResult?> getCachedDiscovery(String networkId);
  void clearExpiredCache();
}
```

### 6. Enhanced Error Handling and User Feedback (HIGH PRIORITY)

**Current Issues:**
- Generic "discovery failed" messages
- No guidance for troubleshooting
- Users don't understand next steps

**Improvements:**
- [ ] Specific error messages for each failure type
- [ ] Contextual troubleshooting suggestions  
- [ ] Progress indicators during discovery
- [ ] Success/failure notifications with details

**Error Message Examples:**
```dart
// Network-specific error messages
final errorMessages = {
  'hotspot_no_services': 'No services found on hotspot network. Ensure services are running and accessible.',
  'localhost_refused': 'Services may be running only on localhost. Try manual configuration with your computer\'s IP address.',
  'tailscale_not_found': 'No Tailscale services found. Ensure both devices are connected to Tailscale.',
  'firewall_blocked': 'Connection blocked. Check firewall settings on your computer.',
};
```

## Testing Requirements

### Network Scenario Testing
Test all scenarios from `PPL_META_NETWORK_DISCOVERY.md`:

- [ ] Same WiFi Network (services on 0.0.0.0)
- [ ] Phone Hotspot Network  
- [ ] Both devices on Tailscale (same network)
- [ ] Both devices on Tailscale (different networks)
- [ ] **Tailscale Device Name Discovery** (device-name.tailnet.ts.net)
- [ ] Mixed Tailscale/local configurations
- [ ] Services behind nginx proxy
- [ ] Docker containerized services
- [ ] **OpenCV Vision Service Integration** (port 8003 discovery)
- [ ] Manual configuration scenarios

### UI/UX Testing
- [ ] Discovery timeout handling
- [ ] Manual setup flow completion
- [ ] Error message clarity and helpfulness
- [ ] Network diagnostics accuracy
- [ ] Caching and persistence behavior

### Performance Testing  
- [ ] Discovery speed optimization
- [ ] Network scanning efficiency
- [ ] Memory usage during discovery
- [ ] Battery impact assessment

## Implementation Plan

### Phase 1: Core Discovery Enhancement (Week 1)

- [ ] Implement enhanced 7-step discovery algorithm
- [ ] Add Tailscale device name resolution
- [ ] Add OpenVPN network detection and scanning  
- [ ] Implement network interface detection
- [ ] Add OpenCV vision service discovery
- [ ] Professional logging system integration

### Phase 2: Manual Configuration & UI (Week 2)

- [ ] Manual server setup screen with network detection
- [ ] Enhanced error handling and specific messages
- [ ] Network diagnostics and troubleshooting UI
- [ ] Discovery result caching and persistence
- [ ] Configuration validation and testing

### Phase 3: Testing & Optimization (Week 3)

- [ ] Comprehensive testing across all 16 network scenarios
- [ ] VPN-specific testing (Tailscale device names, OpenVPN ranges)
- [ ] Performance optimization for discovery speed
- [ ] Edge case handling and graceful fallbacks
- [ ] User experience refinement and documentation

### Testing Matrix

Test all combinations of discovery methods across network scenarios:

| Network Scenario | Multicast | Tailscale DNS | Tailscale IP | OpenVPN | Local | OpenCV | Localhost |
|------------------|-----------|---------------|--------------|---------|-------|---------|-----------|
| Same WiFi | ✓ | - | - | - | ✓ | ✓ | ✓ |
| Hotspot | ✓ | - | - | - | ✓ | ✓ | ✓ |
| Tailscale Same | ✓ | ✓ | ✓ | - | ✓ | ✓ | - |
| Tailscale Remote | - | ✓ | ✓ | - | - | ✓ | - |
| Mixed Tailscale | ✓ | ✓ | ✓ | - | ✓ | ✓ | ✓ |
| OpenVPN Same | ✓ | - | - | ✓ | ✓ | ✓ | ✓ |
| OpenVPN Remote | - | - | - | ✓ | - | ✓ | - |
| Mixed OpenVPN | ✓ | - | - | ✓ | ✓ | ✓ | ✓ |

### Success Metrics

- **Zero Input Required**: 90% automatic discovery success
- **Cross-Platform**: Works on iOS/Android/Web/Desktop
- **Network Agnostic**: Supports all 16 documented scenarios
- **Performance**: Discovery completes within 10 seconds
- **Reliability**: Graceful handling of edge cases and errors

## Files to Modify/Create

### New Files
- `lib/screens/manual_server_setup_screen.dart`
- `lib/services/manual_server_configuration_service.dart`
- `lib/services/network_diagnostics_service.dart`
- `lib/services/service_discovery_cache.dart`
- `lib/widgets/network_diagnostics_widget.dart`
- `lib/widgets/discovery_progress_widget.dart`

### Existing Files to Update
- `lib/services/enhanced_network_discovery_service.dart`
- `lib/services/auto_camera_registration_service.dart`
- `lib/screens/discovery_screen.dart`
- `lib/main.dart`

## Acceptance Criteria
1. ✅ App successfully discovers services in 8/10 documented scenarios
2. ✅ Manual configuration option available when auto-discovery fails
3. ✅ Clear, actionable error messages for each failure type
4. ✅ Network diagnostics help users troubleshoot issues
5. ✅ Discovery results cached and persisted appropriately
6. ✅ Zero-input registration workflow completes successfully in supported scenarios

## Dependencies
- Related platform issue: "Implement Robust Network Service Discovery for All Network Scenarios"
- Requires platform services to bind to 0.0.0.0
- Requires standardized health check endpoints

## Priority  
**HIGH** - Critical for mobile camera zero-configuration setup

## Estimated Effort
- Enhanced discovery algorithm: 12 hours
- Manual configuration UI: 8 hours  
- Network diagnostics: 10 hours
- Improved health checks: 6 hours
- Caching and persistence: 8 hours
- Error handling and UX: 10 hours
- Testing and validation: 12 hours

**Total: ~66 hours**
