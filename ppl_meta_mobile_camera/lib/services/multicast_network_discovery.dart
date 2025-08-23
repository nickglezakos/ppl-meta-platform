import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';

/// Service announcement data received via multicast
class ServiceAnnouncement {
  final String service;
  final String version;
  final String ip;
  final int port;
  final String protocol;
  final Map<String, String> endpoints;
  final List<String> capabilities;
  final int timestamp;
  final String discoveryMethod;

  ServiceAnnouncement({
    required this.service,
    required this.version,
    required this.ip,
    required this.port,
    required this.protocol,
    required this.endpoints,
    required this.capabilities,
    required this.timestamp,
    required this.discoveryMethod,
  });

  factory ServiceAnnouncement.fromJson(Map<String, dynamic> json) {
    return ServiceAnnouncement(
      service: json['service'] ?? '',
      version: json['version'] ?? '',
      ip: json['ip'] ?? '',
      port: json['port'] ?? 0,
      protocol: json['protocol'] ?? 'http',
      endpoints: Map<String, String>.from(json['endpoints'] ?? {}),
      capabilities: List<String>.from(json['capabilities'] ?? []),
      timestamp: json['timestamp'] ?? 0,
      discoveryMethod: json['discovery_method'] ?? 'unknown',
    );
  }

  /// Get the base URL for the service
  String get baseUrl => '$protocol://$ip:$port';

  /// Get the health check URL
  String? get healthUrl => endpoints['health'];

  /// Get the login URL
  String? get loginUrl => endpoints['login'];

  /// Get the platform services URL
  String? get servicesUrl => endpoints['services'];

  /// Check if the announcement is recent (within 30 seconds)
  bool get isRecent {
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    return (now - timestamp) <= 30;
  }

  @override
  String toString() {
    return 'ServiceAnnouncement(service: $service, ip: $ip:$port, version: $version, method: $discoveryMethod)';
  }
}

/// Multicast discovery client for finding PPL Meta services
class MulticastServiceDiscovery {
  static const String _multicastGroup = '224.1.1.1';
  static const int _multicastPort = 12345;
  static const Duration _discoveryTimeout = Duration(seconds: 10);
  static const Duration _cleanupInterval = Duration(seconds: 60);

  RawDatagramSocket? _socket;
  Timer? _cleanupTimer;
  final Map<String, ServiceAnnouncement> _discoveredServices = {};
  final StreamController<List<ServiceAnnouncement>> _servicesController =
      StreamController<List<ServiceAnnouncement>>.broadcast();

  /// Stream of discovered services
  Stream<List<ServiceAnnouncement>> get servicesStream =>
      _servicesController.stream;

  /// Get the current list of discovered services
  List<ServiceAnnouncement> get currentServices =>
      _discoveredServices.values.where((s) => s.isRecent).toList();

  /// Start multicast discovery
  Future<bool> start() async {
    try {
      debugPrint('🎯 Starting multicast service discovery...');
      
      // Create UDP socket bound to multicast port
      _socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, _multicastPort);
      
      // Join multicast group
      final multicastAddress = InternetAddress(_multicastGroup);
      _socket!.joinMulticast(multicastAddress);
      
      debugPrint('📡 Listening for multicast announcements on $_multicastGroup:$_multicastPort');
      
      // Listen for incoming packets
      _socket!.listen(_handleIncomingPacket);
      
      // Start cleanup timer to remove stale services
      _cleanupTimer = Timer.periodic(_cleanupInterval, _cleanupStaleServices);
      
      debugPrint('✅ Multicast discovery started successfully');
      return true;
      
    } catch (e) {
      debugPrint('❌ Failed to start multicast discovery: $e');
      return false;
    }
  }

  /// Stop multicast discovery
  void stop() {
    debugPrint('🛑 Stopping multicast service discovery...');
    
    _cleanupTimer?.cancel();
    _cleanupTimer = null;
    
    if (_socket != null) {
      try {
        _socket!.leaveMulticast(InternetAddress(_multicastGroup));
        _socket!.close();
      } catch (e) {
        debugPrint('⚠️ Error closing multicast socket: $e');
      }
      _socket = null;
    }
    
    _discoveredServices.clear();
    _servicesController.add([]);
    
    debugPrint('✅ Multicast discovery stopped');
  }

  /// Handle incoming multicast packets
  void _handleIncomingPacket(RawSocketEvent event) {
    if (event == RawSocketEvent.read) {
      try {
        final datagram = _socket!.receive();
        if (datagram != null) {
          final message = utf8.decode(datagram.data);
          debugPrint('📨 Received multicast packet: ${message.substring(0, 100)}...');
          
          _processServiceAnnouncement(message);
        }
      } catch (e) {
        debugPrint('⚠️ Error processing multicast packet: $e');
      }
    }
  }

  /// Process a service announcement
  void _processServiceAnnouncement(String message) {
    try {
      final json = jsonDecode(message) as Map<String, dynamic>;
      final announcement = ServiceAnnouncement.fromJson(json);
      
      // Only process PPL Meta Node service announcements
      if (announcement.service == 'ppl-meta-node') {
        final serviceKey = '${announcement.ip}:${announcement.port}';
        
        debugPrint('🎯 Discovered PPL Meta Node: ${announcement.ip}:${announcement.port}');
        debugPrint('   Version: ${announcement.version}');
        debugPrint('   Capabilities: ${announcement.capabilities.join(', ')}');
        debugPrint('   Endpoints: ${announcement.endpoints.keys.join(', ')}');
        
        _discoveredServices[serviceKey] = announcement;
        _notifyServicesUpdated();
      }
    } catch (e) {
      debugPrint('⚠️ Error parsing service announcement: $e');
    }
  }

  /// Clean up stale service announcements
  void _cleanupStaleServices(Timer timer) {
    final beforeCount = _discoveredServices.length;
    _discoveredServices.removeWhere((key, service) => !service.isRecent);
    
    if (_discoveredServices.length != beforeCount) {
      debugPrint('🧹 Cleaned up stale services (${beforeCount} → ${_discoveredServices.length})');
      _notifyServicesUpdated();
    }
  }

  /// Notify listeners of service updates
  void _notifyServicesUpdated() {
    final recentServices = currentServices;
    _servicesController.add(recentServices);
    
    debugPrint('📋 Active services: ${recentServices.length}');
    for (final service in recentServices) {
      debugPrint('   - ${service.service} at ${service.baseUrl}');
    }
  }

  /// Discover services with timeout
  Future<List<ServiceAnnouncement>> discoverServices({
    Duration? timeout,
  }) async {
    timeout ??= _discoveryTimeout;
    
    debugPrint('🔍 Starting service discovery (timeout: ${timeout.inSeconds}s)...');
    
    if (!await start()) {
      debugPrint('❌ Failed to start discovery');
      return [];
    }
    
    // Wait for discoveries or timeout
    final completer = Completer<List<ServiceAnnouncement>>();
    Timer? timeoutTimer;
    StreamSubscription? subscription;
    
    void complete(List<ServiceAnnouncement> services) {
      if (!completer.isCompleted) {
        timeoutTimer?.cancel();
        subscription?.cancel();
        completer.complete(services);
      }
    }
    
    // Set up timeout
    timeoutTimer = Timer(timeout, () {
      debugPrint('⏰ Discovery timeout reached');
      complete(currentServices);
    });
    
    // Listen for first discovery
    subscription = servicesStream.listen((services) {
      if (services.isNotEmpty) {
        debugPrint('🎯 Found ${services.length} services via multicast');
        complete(services);
      }
    });
    
    final result = await completer.future;
    stop(); // Clean up
    
    debugPrint('✅ Discovery completed: ${result.length} services found');
    return result;
  }

  /// Find the best PPL Meta Node service
  Future<ServiceAnnouncement?> findNodeService({
    Duration? timeout,
  }) async {
    final services = await discoverServices(timeout: timeout);
    
    // Find the most recent Node service
    final nodeServices = services.where((s) => s.service == 'ppl-meta-node').toList();
    
    if (nodeServices.isEmpty) {
      debugPrint('❌ No PPL Meta Node services found via multicast');
      return null;
    }
    
    // Sort by timestamp (most recent first)
    nodeServices.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    final best = nodeServices.first;
    
    debugPrint('🎯 Selected Node service: ${best.baseUrl}');
    debugPrint('   Capabilities: ${best.capabilities.join(', ')}');
    
    return best;
  }

  /// Dispose resources
  void dispose() {
    stop();
    _servicesController.close();
  }
}

/// Enhanced network discovery service that combines multicast with fallback
class EnhancedNetworkDiscoveryService {
  final MulticastServiceDiscovery _multicastDiscovery = MulticastServiceDiscovery();
  
  /// Auto-discover Node service using multicast with Tailscale and device IP fallback
  Future<String?> autoDiscoverNodeService() async {
    debugPrint('🎯 Starting enhanced network discovery...');
    
    try {
      // First, try multicast discovery (works on local networks)
      debugPrint('📡 Attempting multicast discovery...');
      final nodeService = await _multicastDiscovery.findNodeService(
        timeout: const Duration(seconds: 8),
      );
      
      if (nodeService != null) {
        final baseUrl = nodeService.baseUrl;
        debugPrint('✅ Multicast discovery successful: $baseUrl');
        debugPrint('🔍 Discovered service details:');
        debugPrint('   IP: ${nodeService.ip}');
        debugPrint('   Port: ${nodeService.port}');
        debugPrint('   Version: ${nodeService.version}');
        debugPrint('   Health URL: ${nodeService.healthUrl}');
        
        // Verify the service is accessible
        if (await _testConnection(baseUrl)) {
          debugPrint('✅ Service verified via multicast: $baseUrl');
          return baseUrl;
        } else {
          debugPrint('⚠️ Multicast service not accessible, trying fallback');
          debugPrint('💡 This might be a network connectivity issue between devices');
        }
      } else {
        debugPrint('⚠️ No services found via multicast, trying fallback');
      }
      
      // Fallback 1: Try Tailscale network scan
      debugPrint('🔄 Fallback 1: Scanning Tailscale network...');
      final tailscaleUrl = await _scanTailscaleNetwork();
      
      if (tailscaleUrl != null && await _testConnection(tailscaleUrl)) {
        debugPrint('✅ Tailscale network scan successful: $tailscaleUrl');
        return tailscaleUrl;
      }
      
      // Fallback 2: Try local network scan
      debugPrint('🔄 Fallback 2: Scanning local network...');
      final localNetworkUrl = await _scanLocalNetwork();
      
      if (localNetworkUrl != null && await _testConnection(localNetworkUrl)) {
        debugPrint('✅ Local network scan successful: $localNetworkUrl');
        return localNetworkUrl;
      }
      
      // Fallback 3: Try localhost (for nginx proxy development)
      debugPrint('🔄 Fallback 3: Testing localhost nginx proxy...');
      final localhostUrl = await _testLocalhostProxy();
      
      if (localhostUrl != null && await _testConnection(localhostUrl)) {
        debugPrint('✅ Localhost nginx proxy successful: $localhostUrl');
        return localhostUrl;
      }
      
      debugPrint('❌ All discovery methods failed');
      return null;
      
    } catch (e) {
      debugPrint('❌ Enhanced discovery error: $e');
      return null;
    } finally {
      _multicastDiscovery.dispose();
    }
  }

  /// Scan Tailscale network for PPL Meta Node service
  Future<String?> _scanTailscaleNetwork() async {
    try {
      debugPrint('🔍 Detecting Tailscale network...');
      final interfaces = await NetworkInterface.list();
      
      // Look for Tailscale interface
      for (final interface in interfaces) {
        if (interface.name.startsWith('tailscale') || interface.name.startsWith('tun')) {
          for (final addr in interface.addresses) {
            if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
              final deviceIp = addr.address;
              debugPrint('📱 Found Tailscale device IP: $deviceIp (interface: ${interface.name})');
              
              // Extract network prefix for scanning
              if (deviceIp.startsWith('100.')) {
                debugPrint('🌐 Scanning Tailscale network range...');
                
                // Common Tailscale IP patterns to try
                final baseIp = deviceIp.substring(0, deviceIp.lastIndexOf('.'));
                final commonTailscaleIPs = [
                  // Try common Tailscale server IPs
                  '$baseIp.67',  // Common pattern for first device
                  '$baseIp.68',  // Common pattern for second device
                  '$baseIp.1',   // Gateway
                  '$baseIp.100', // High range
                  '$baseIp.101',
                  '$baseIp.102',
                ];
                
                // Try each IP in parallel for faster scanning
                final futures = commonTailscaleIPs.map((ip) async {
                  final url = 'http://$ip:8001';
                  debugPrint('🔍 Testing Tailscale IP: $ip');
                  if (await _testConnection(url)) {
                    debugPrint('🎯 Found PPL Meta Node on Tailscale: $url');
                    return url;
                  }
                  return null;
                }).toList();
                
                final results = await Future.wait(futures);
                final found = results.where((url) => url != null).firstOrNull;
                
                if (found != null) {
                  return found;
                }
              }
            }
          }
        }
      }
      
      debugPrint('⚠️ No Tailscale network found or no services discovered');
      return null;
      
    } catch (e) {
      debugPrint('❌ Error scanning Tailscale network: $e');
      return null;
    }
  }

  /// Scan local network for PPL Meta Node service
  Future<String?> _scanLocalNetwork() async {
    try {
      debugPrint('🔍 Detecting local network...');
      final interfaces = await NetworkInterface.list();
      
      // Priority order for interface types
      final preferredPrefixes = [
        'en0',       // Primary WiFi on macOS/iOS
        'wlan',      // WiFi on Android/Linux
        'eth',       // Ethernet
        'en1',       // Secondary network
      ];
      
      // Try each preferred interface type
      for (final prefix in preferredPrefixes) {
        for (final interface in interfaces) {
          if (interface.name.startsWith(prefix)) {
            for (final addr in interface.addresses) {
              if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
                final deviceIp = addr.address;
                debugPrint('� Found local device IP: $deviceIp (interface: ${interface.name})');
                
                // Common local network ranges
                if (deviceIp.startsWith('192.168.') || deviceIp.startsWith('10.') || deviceIp.startsWith('172.')) {
                  final baseIp = deviceIp.substring(0, deviceIp.lastIndexOf('.'));
                  final commonLocalIPs = [
                    '$baseIp.1',   // Router/Gateway
                    '$baseIp.68',  // Common laptop IP
                    '$baseIp.100', // High range
                    '$baseIp.101',
                    '$baseIp.253', // High range
                  ];
                  
                  // Try each IP
                  for (final ip in commonLocalIPs) {
                    final url = 'http://$ip:8001';
                    debugPrint('🔍 Testing local IP: $ip');
                    if (await _testConnection(url)) {
                      debugPrint('🎯 Found PPL Meta Node on local network: $url');
                      return url;
                    }
                  }
                }
              }
            }
          }
        }
      }
      
      debugPrint('⚠️ No local network services found');
      return null;
      
    } catch (e) {
      debugPrint('❌ Error scanning local network: $e');
      return null;
    }
  }

  /// Test localhost nginx proxy for development
  Future<String?> _testLocalhostProxy() async {
    try {
      debugPrint('🏠 Testing localhost nginx proxy...');
      
      // When using nginx proxy, the Node service is accessible via localhost
      final localhostUrls = [
        'http://localhost',      // nginx proxy root
        'http://127.0.0.1',     // localhost IP
        'http://localhost:8001', // direct node service (fallback)
      ];
      
      for (final url in localhostUrls) {
        debugPrint('🔍 Testing localhost URL: $url');
        if (await _testConnection(url)) {
          debugPrint('🎯 Found PPL Meta via localhost: $url');
          return url;
        }
      }
      
      debugPrint('⚠️ No localhost services found');
      return null;
      
    } catch (e) {
      debugPrint('❌ Error testing localhost: $e');
      return null;
    }
  }

  /// Test if a service URL is accessible
  Future<bool> _testConnection(String baseUrl) async {
    try {
      debugPrint('🩺 Testing connection to: $baseUrl');
      
      final client = HttpClient();
      client.connectionTimeout = const Duration(seconds: 5); // Increased timeout for VPN
      
      // Determine the correct health endpoint based on URL
      late Uri uri;
      if (baseUrl.contains('localhost') || baseUrl.contains('127.0.0.1')) {
        // For localhost/nginx proxy, test the node health endpoint
        if (baseUrl == 'http://localhost' || baseUrl == 'http://127.0.0.1') {
          uri = Uri.parse('$baseUrl/health/node');
        } else {
          // For direct localhost:8001, use the API health endpoint
          uri = Uri.parse('$baseUrl/api/v1/health');
        }
      } else {
        // For network IPs, use the standard API health endpoint
        uri = Uri.parse('$baseUrl/api/v1/health');
      }
      
      debugPrint('🌐 Making request to: $uri');
      
      final request = await client.getUrl(uri);
      final response = await request.close();
      
      client.close();
      
      final success = response.statusCode == 200;
      if (success) {
        debugPrint('🩺 Health check $baseUrl: ✅ OK (${response.statusCode})');
      } else {
        debugPrint('🩺 Health check $baseUrl: ❌ Failed (HTTP ${response.statusCode})');
      }
      
      return success;
      
    } catch (e) {
      debugPrint('🩺 Health check $baseUrl: ❌ Failed ($e)');
      if (e.toString().contains('SocketException')) {
        debugPrint('💡 Network connectivity issue - check VPN/network configuration');
      }
      return false;
    }
  }
}
