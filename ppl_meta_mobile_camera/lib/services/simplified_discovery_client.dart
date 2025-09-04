import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'discovery_config_service.dart';

/// Simplified Discovery Service client focused on single point discovery
/// 
/// This client is designed to ONLY find and connect to the PPL Meta Discovery Service
/// All other service information comes from the Discovery Service API
class SimplifiedDiscoveryClient {
  static const Duration _timeout = Duration(seconds: 8);
  
  String? _cachedDiscoveryUrl;
  
  /// Find the Discovery Service URL
  /// Construct Discovery Service URL from user input
  /// Uses device's network prefix + user's host IP + port
  Future<String?> constructDiscoveryUrl(String userHostIP, String userPort) async {
    print('🔍 Constructing Discovery Service URL from user input...');
    
    // Get the device's actual IP address
    final deviceIP = await getMyIPAddress();
    if (deviceIP == null) {
      print('❌ Cannot detect device IP address - URL construction failed');
      return null;
    }
    
    // Extract network prefix from device IP (first 3 parts)
    final parts = deviceIP.split('.');
    if (parts.length != 4) {
      print('❌ Invalid device IP address format: $deviceIP');
      return null;
    }
    
    final networkPrefix = '${parts[0]}.${parts[1]}.${parts[2]}';
    final discoveryUrl = 'http://$networkPrefix.$userHostIP:$userPort/api/v1/services';
    
    print('📱 Device IP: $deviceIP');
    print('🌐 Network prefix: $networkPrefix');
    print('🎯 Constructed URL: $discoveryUrl');
    
    return discoveryUrl;
  }

  /// Test and cache a Discovery Service URL constructed from user input
  Future<bool> testAndCacheDiscoveryUrl(String userHostIP, String userPort) async {
    final url = await constructDiscoveryUrl(userHostIP, userPort);
    if (url == null) {
      return false;
    }
    
    if (await _testDiscoveryServicesEndpoint(url)) {
      _cachedDiscoveryUrl = url;
      print('✅ Discovery Service validated and cached: $url');
      return true;
    } else {
      print('❌ Discovery Service validation failed: $url');
      return false;
    }
  }

  /// Returns null if Discovery Service cannot be found
  Future<String?> findDiscoveryService() async {
    print('🔍 Searching for PPL Meta Discovery Service...');
    
    // Return cached URL if available
    if (_cachedDiscoveryUrl != null) {
      print('✅ Using cached discovery URL: $_cachedDiscoveryUrl');
      return _cachedDiscoveryUrl;
    }
    
    // Try to get discovery URL from discovery config service
    try {
      final configService = DiscoveryConfigService.instance;
      final configUrl = await configService.getDiscoveryUrl();
      
      if (configUrl != null) {
        print('✅ Found discovery URL from config service: $configUrl');
        _cachedDiscoveryUrl = configUrl;
        return configUrl;
      }
    } catch (e) {
      print('⚠️ Could not get discovery URL from config service: $e');
    }
    
    print('❌ No cached Discovery Service URL - user input required');
    return null;
  }
  
  /// Discover services at a specific IP:port address
  Future<List<ServiceInfo>> discoverServicesAtAddress(String ipPort) async {
    final url = 'http://$ipPort/api/v1/services';
    
    try {
      print('🔍 Connecting to Discovery Service at: $url');
      
      final response = await http.get(
        Uri.parse(url),
        headers: {'Accept': 'application/json'},
      ).timeout(_timeout);
      
      if (response.statusCode != 200) {
        throw DiscoveryException('Discovery Service returned HTTP ${response.statusCode}');
      }
      
      final data = json.decode(response.body);
      final services = <ServiceInfo>[];
      
      for (final serviceData in data['services']) {
        services.add(ServiceInfo.fromJson(serviceData));
      }
      
      print('✅ Retrieved ${services.length} services from Discovery Service at $ipPort');
      
      // Cache this URL as it's working
      _cachedDiscoveryUrl = 'http://$ipPort';
      
      return services;
      
    } catch (e) {
      print('❌ Error connecting to Discovery Service at $ipPort: $e');
      throw DiscoveryException('Failed to connect to Discovery Service at $ipPort: $e');
    }
  }

  /// Get all services from Discovery Service
  Future<List<ServiceInfo>> getAllServices() async {
    final discoveryBaseUrl = await findDiscoveryService();
    if (discoveryBaseUrl == null) {
      throw DiscoveryException('Discovery Service not configured - user input required');
    }
    
    try {
      print('📋 Fetching services from Discovery Service...');
      
      // Construct the full services endpoint URL
      String servicesUrl;
      if (discoveryBaseUrl.endsWith('/api/v1/services')) {
        // URL already includes the endpoint
        servicesUrl = discoveryBaseUrl;
      } else {
        // Add the endpoint to the base URL
        final baseUrl = discoveryBaseUrl.endsWith('/') ? discoveryBaseUrl.substring(0, discoveryBaseUrl.length - 1) : discoveryBaseUrl;
        servicesUrl = '$baseUrl/api/v1/services';
      }
      
      print('🔗 Using services URL: $servicesUrl');
      
      final response = await http.get(
        Uri.parse(servicesUrl),
        headers: {'Accept': 'application/json'},
      ).timeout(_timeout);
      
      if (response.statusCode != 200) {
        throw DiscoveryException('Failed to fetch services: HTTP ${response.statusCode}');
      }
      
      final data = json.decode(response.body);
      final services = <ServiceInfo>[];
      
      for (final serviceData in data['services']) {
        services.add(ServiceInfo.fromJson(serviceData));
      }
      
      print('✅ Retrieved ${services.length} services from Discovery Service');
      return services;
      
    } catch (e) {
      print('❌ Error fetching services: $e');
      throw DiscoveryException('Failed to fetch services: $e');
    }
  }
  
  /// Find a specific service by name
  Future<ServiceInfo?> findService(String serviceName) async {
    try {
      final services = await getAllServices();
      
      // Look for exact name match first
      for (final service in services) {
        if (service.name == serviceName) {
          print('✅ Found service $serviceName: ${service.baseUrl}');
          return service;
        }
      }
      
      // Look for partial name match (case insensitive)
      for (final service in services) {
        if (service.name.toLowerCase().contains(serviceName.toLowerCase())) {
          print('✅ Found service $serviceName (partial match): ${service.baseUrl}');
          return service;
        }
      }
      
      print('❌ Service $serviceName not found in Discovery Service registry');
      return null;
      
    } catch (e) {
      print('❌ Error finding service $serviceName: $e');
      return null;
    }
  }
  
  /// Test Discovery Service health
  Future<bool> testDiscoveryHealth() async {
    final discoveryUrl = await findDiscoveryService();
    if (discoveryUrl == null) return false;
    
    return await _testDiscoveryUrl(discoveryUrl);
  }

  /// Get the device's IP address on the current network

  /// Get the device's network prefix (first 3 parts of IP)
  /// Returns something like "192.168.200" for display in UI
  Future<String?> getNetworkPrefix() async {
    final deviceIP = await getMyIPAddress();
    if (deviceIP == null) return null;
    
    final parts = deviceIP.split('.');
    if (parts.length != 4) return null;
    
    return '${parts[0]}.${parts[1]}.${parts[2]}';
  }

  /// Get the device's IP address on the current network
  Future<String?> getMyIPAddress() async {
    try {
      // Use socket connection to detect actual local IP
      // Connect to a remote address to determine local IP
      final socket = await Socket.connect('8.8.8.8', 80);
      final localIP = socket.address.address;
      socket.destroy();
      
      // Validate that this is not a VPN/Tailscale IP
      if (_isLocalNetworkIP(localIP)) {
        print('📱 IP detection: Detected device IP: $localIP');
        return localIP;
      } else {
        print('⚠️ Socket IP is VPN/Tailscale ($localIP), trying network interfaces...');
      }
      
    } catch (e) {
      print('❌ IP detection error: $e');
    }
    
    // Fallback: try to detect network interface, prioritizing local networks
    try {
      final interfaces = await NetworkInterface.list();
      
      // First pass: Look for common local network ranges
      for (final interface in interfaces) {
        for (final addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && 
              !addr.isLoopback && 
              !addr.address.startsWith('169.254') &&
              _isLocalNetworkIP(addr.address)) {
            print('📱 IP detection: Using local network interface IP: ${addr.address}');
            return addr.address;
          }
        }
      }
      
      // Second pass: If no local network found, use any non-loopback IPv4
      for (final interface in interfaces) {
        for (final addr in interface.addresses) {
          if (addr.type == InternetAddressType.IPv4 && 
              !addr.isLoopback && 
              !addr.address.startsWith('169.254')) {
            print('⚠️ IP detection: Using non-local network IP: ${addr.address}');
            return addr.address;
          }
        }
      }
    } catch (e2) {
      print('❌ Interface detection error: $e2');
    }
    
    // No fallback IP - return null if detection fails
    print('❌ Could not detect device IP address');
    return null;
  }
  
  /// Check if an IP address is in a local network range
  bool _isLocalNetworkIP(String ip) {
    // Common local network ranges
    return ip.startsWith('192.168.') ||  // Class C private
           ip.startsWith('10.0.') ||     // Class A private (but not Tailscale 10.x.x.x)
           ip.startsWith('172.16.') ||   // Class B private
           ip.startsWith('172.17.') ||
           ip.startsWith('172.18.') ||
           ip.startsWith('172.19.') ||
           ip.startsWith('172.20.') ||
           ip.startsWith('172.21.') ||
           ip.startsWith('172.22.') ||
           ip.startsWith('172.23.') ||
           ip.startsWith('172.24.') ||
           ip.startsWith('172.25.') ||
           ip.startsWith('172.26.') ||
           ip.startsWith('172.27.') ||
           ip.startsWith('172.28.') ||
           ip.startsWith('172.29.') ||
           ip.startsWith('172.30.') ||
           ip.startsWith('172.31.');
  }

  /// Clear cached Discovery Service URL (force re-discovery)
  void clearCache() {
    _cachedDiscoveryUrl = null;
    print('🗑️ Discovery Service cache cleared');
  }

  // Private methods
  
  /// Test if a URL is a valid Discovery Service /services endpoint
  Future<bool> _testDiscoveryServicesEndpoint(String url) async {
    try {
      print('🩺 Testing Discovery Service /services endpoint: $url');
      
      final response = await http.get(
        Uri.parse(url),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        // Verify it's the services endpoint by checking response structure
        final data = json.decode(response.body);
        if (data.containsKey('services') && data['services'] is List) {
          print('✅ Verified Discovery Service /services endpoint: $url');
          return true;
        }
      }
      
      print('❌ Not a valid Discovery Service /services endpoint: $url');
      return false;
      
    } catch (e) {
      print('❌ Failed to test Discovery Service /services endpoint at $url: $e');
      return false;
    }
  }

  /// Test if a URL is a valid Discovery Service (legacy method for health checks)
  Future<bool> _testDiscoveryUrl(String url) async {
    try {
      print('🩺 Testing Discovery Service at: $url');
      
      final response = await http.get(
        Uri.parse('$url/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        // Verify it's actually the Discovery Service by checking response
        final data = json.decode(response.body);
        if (data['service'] == 'ppl-meta-discovery') {
          print('✅ Verified Discovery Service at: $url');
          return true;
        }
      }
      
      print('❌ Not a Discovery Service at: $url');
      return false;
      
    } catch (e) {
      print('❌ Failed to test Discovery Service at $url: $e');
      return false;
    }
  }
}

/// Service information from Discovery Service registry
class ServiceInfo {
  final String serviceId;
  final String name;
  final String serviceType;
  final String version;
  final String host;
  final int port;
  final String healthEndpoint;
  final String status;
  final List<String> capabilities;
  final Map<String, dynamic> metadata;

  ServiceInfo({
    required this.serviceId,
    required this.name,
    required this.serviceType,
    required this.version,
    required this.host,
    required this.port,
    required this.healthEndpoint,
    required this.status,
    required this.capabilities,
    required this.metadata,
  });

  factory ServiceInfo.fromJson(Map<String, dynamic> json) {
    return ServiceInfo(
      serviceId: json['service_id'] ?? '',
      name: json['name'] ?? '',
      serviceType: json['service_type'] ?? '',
      version: json['version'] ?? '',
      host: json['host'] ?? '',
      port: json['port'] ?? 0,
      healthEndpoint: json['health_endpoint'] ?? '/health',
      status: json['status'] ?? '',
      capabilities: List<String>.from(json['capabilities'] ?? []),
      metadata: Map<String, dynamic>.from(json['metadata'] ?? {}),
    );
  }

  /// Get the base URL for the service
  String get baseUrl => 'http://$host:$port';

  /// Get the full health check URL
  String get fullHealthUrl => '$baseUrl$healthEndpoint';

  @override
  String toString() {
    return 'ServiceInfo(name: $name, host: $host:$port, status: $status)';
  }
}

/// Discovery exception
class DiscoveryException implements Exception {
  final String message;
  DiscoveryException(this.message);
  
  @override
  String toString() => 'DiscoveryException: $message';
}
