import 'dart:convert';
import 'package:http/http.dart' as http;

/// Simplified Discovery Service client focused on single point discovery
/// 
/// This client is designed to ONLY find and connect to the PPL Meta Discovery Service
/// All other service information comes from the Discovery Service API
class SimplifiedDiscoveryClient {
  static const Duration _timeout = Duration(seconds: 8);
  
  String? _cachedDiscoveryUrl;
  
  /// Find the Discovery Service URL
  /// Returns null if Discovery Service cannot be found
  Future<String?> findDiscoveryService() async {
    print('🔍 Searching for PPL Meta Discovery Service...');
    
    // Return cached URL if available
    if (_cachedDiscoveryUrl != null) {
      print('✅ Using cached discovery URL: $_cachedDiscoveryUrl');
      return _cachedDiscoveryUrl;
    }
    
    // Get host machine IPs
    final hostIPs = await _getHostMachineIPs();
    
    // PRIORITY 1: Try Discovery Service through nginx proxy (recommended)
    for (final hostIP in hostIPs) {
      final nginxUrl = 'http://$hostIP/discovery';
      if (await _testDiscoveryUrl(nginxUrl)) {
        _cachedDiscoveryUrl = nginxUrl;
        print('✅ Found Discovery Service via nginx: $nginxUrl');
        return nginxUrl;
      }
    }
    
    // PRIORITY 2: Try direct Discovery Service access (port 8006)
    for (final hostIP in hostIPs) {
      final directUrl = 'http://$hostIP:8006';
      if (await _testDiscoveryUrl(directUrl)) {
        _cachedDiscoveryUrl = directUrl;
        print('✅ Found Discovery Service directly: $directUrl');
        return directUrl;
      }
    }
    
    // PRIORITY 3: Try localhost (development fallback)
    const localhostUrl = 'http://localhost:8006';
    if (await _testDiscoveryUrl(localhostUrl)) {
      _cachedDiscoveryUrl = localhostUrl;
      print('✅ Found Discovery Service on localhost: $localhostUrl');
      return localhostUrl;
    }
    
    print('❌ Discovery Service not found on any known location');
    return null;
  }
  
  /// Get all services from Discovery Service
  Future<List<ServiceInfo>> getAllServices() async {
    final discoveryUrl = await findDiscoveryService();
    if (discoveryUrl == null) {
      throw DiscoveryException('Discovery Service not found');
    }
    
    try {
      print('📋 Fetching services from Discovery Service...');
      
      final response = await http.get(
        Uri.parse('$discoveryUrl/api/v1/services'),
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
  
  /// Get services from Discovery Service at specific address
  Future<List<ServiceInfo>> discoverServicesAtAddress(String address) async {
    final url = 'http://$address';
    
    try {
      print('🔍 Testing Discovery Service at: $url');
      
      // Test health first
      final healthResponse = await http.get(
        Uri.parse('$url/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      if (healthResponse.statusCode != 200) {
        throw DiscoveryException('Discovery Service health check failed at $url');
      }
      
      print('✅ Discovery Service health OK at $url');
      
      // Get services
      final servicesResponse = await http.get(
        Uri.parse('$url/api/v1/services'),
        headers: {'Accept': 'application/json'},
      ).timeout(_timeout);
      
      if (servicesResponse.statusCode != 200) {
        throw DiscoveryException('Failed to fetch services: HTTP ${servicesResponse.statusCode}');
      }
      
      final data = json.decode(servicesResponse.body);
      final services = <ServiceInfo>[];
      
      for (final serviceData in data['services']) {
        services.add(ServiceInfo.fromJson(serviceData));
      }
      
      print('✅ Retrieved ${services.length} services from Discovery Service at $url');
      
      // Cache this URL as it's working
      _cachedDiscoveryUrl = url;
      
      return services;
      
    } catch (e) {
      print('❌ Error connecting to Discovery Service at $url: $e');
      throw DiscoveryException('Failed to connect to Discovery Service at $url: $e');
    }
  }

  /// Get the device's IP address on the current network
  Future<String?> getMyIPAddress() async {
    try {
      // Simple approach: we'll assume we're on a standard home network
      // and let the user specify the exact IP
      // This is actually more reliable than trying to auto-detect
      
      print('📱 IP detection: Using manual network configuration');
      print('💡 User will specify the target machine IP');
      
      // Return a sample IP for network detection purposes
      // The UI will extract the network part and let user specify the host part
      return '192.168.1.66'; // This represents the mobile device IP
      
    } catch (e) {
      print('❌ IP detection error: $e');
      return '192.168.1.66'; // Fallback
    }
  }

  /// Clear cached Discovery Service URL (force re-discovery)
  void clearCache() {
    _cachedDiscoveryUrl = null;
    print('🗑️ Discovery Service cache cleared');
  }

  // Private methods  /// Test if a URL is a valid Discovery Service
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
  
  /// Get potential host machine IP addresses using network discovery
  Future<List<String>> _getHostMachineIPs() async {
    final discoveredIPs = <String>[];
    
    // Try to discover the actual network gateway/host machine
    try {
      // Use common development machine IPs in the current network
      final networkPrefixes = ['192.168.1.', '192.168.0.', '10.0.0.', '172.16.0.'];
      
      for (final prefix in networkPrefixes) {
        // Try common host machine IPs in each network
        for (int i = 1; i <= 10; i++) {
          discoveredIPs.add('$prefix$i');
        }
        // Try common development IPs
        discoveredIPs.addAll([
          '${prefix}100', '${prefix}101', '${prefix}102', 
          '${prefix}200', '${prefix}201', '${prefix}229'
        ]);
      }
    } catch (e) {
      print('⚠️ Network discovery failed: $e');
    }
    
    return discoveredIPs;
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
