import 'dart:convert';
import 'package:http/http.dart' as http;
import 'discovery_config_service.dart';

/// Enhanced discovery service client for PPL Meta mobile applications
class PPLMetaDiscoveryClient {
  static const String defaultDiscoveryUrl = 'http://localhost:8006';
  static const Duration _discoveryTimeout = Duration(seconds: 10);
  
  final String discoveryServiceUrl;
  final DiscoveryConfigService _configService = DiscoveryConfigService.instance;
  
  PPLMetaDiscoveryClient({
    this.discoveryServiceUrl = defaultDiscoveryUrl,
  });

  /// Get discovery URL from user configuration or auto-detect
  Future<String> _getDiscoveryUrl() async {
    // Try configured discovery client first
    try {
      final configuredClient = await _configService.getConfiguredDiscoveryClient();
      if (configuredClient != null) {
        final discoveryUrl = await configuredClient.findDiscoveryService();
        if (discoveryUrl != null) {
          // Test that it's actually working
          final services = await configuredClient.discoverServicesAtAddress(discoveryUrl.replaceFirst('http://', ''));
          if (services.isNotEmpty) {
            print('✅ Using configured discovery service at: $discoveryUrl');
            return discoveryUrl;
          }
        }
      }
    } catch (e) {
      print('⚠️ Configured discovery service not available: $e');
    }
    
    // PRIORITY 1: Try Discovery Service through nginx proxy (via host machine)
    final hostIPs = await _getHostMachineIPs();
    
    for (final hostIP in hostIPs) {
      final nginxUrl = 'http://$hostIP/discovery';
      print('🔍 Testing discovery service via nginx at: $nginxUrl');
      if (await _testDiscoveryUrl(nginxUrl)) {
        print('✅ Found discovery service via nginx at: $nginxUrl');
        return nginxUrl;
      }
    }
    
    // PRIORITY 2: Try direct Discovery Service access
    for (final hostIP in hostIPs) {
      final directUrl = 'http://$hostIP:8006';
      print('🔍 Testing discovery service directly at: $directUrl');
      if (await _testUrl(directUrl)) {
        print('✅ Found discovery service directly at: $directUrl');
        return directUrl;
      }
    }
    
    // PRIORITY 3: Try default localhost (development fallback)
    if (await _testUrl(discoveryServiceUrl)) {
      print('✅ Using default discovery service: $discoveryServiceUrl');
      return discoveryServiceUrl;
    }
    
    print('⚠️ No discovery service found, using default: $discoveryServiceUrl');
    return discoveryServiceUrl; // Fallback to default
  }

  /// Get potential host machine IP addresses
  Future<List<String>> _getHostMachineIPs() async {
    final List<String> hostIPs = [];
    
    // Check if user has configured a specific discovery service
    try {
      final configuredClient = await _configService.getConfiguredDiscoveryClient();
      if (configuredClient != null) {
        final discoveryUrl = await configuredClient.findDiscoveryService();
        if (discoveryUrl != null) {
          // Extract IP from configured discovery URL
          final uri = Uri.parse(discoveryUrl);
          if (uri.host != 'localhost' && uri.host != '127.0.0.1') {
            hostIPs.add(uri.host);
          }
        }
      }
    } catch (e) {
      print('Could not get configured IPs: $e');
    }
    
    // REMOVED: No fallback IPs - user must explicitly configure network
    print('🔧 No hardcoded fallback IPs - explicit user configuration required');
    
    return hostIPs;
  }

  /// Test if a URL is accessible
  Future<bool> _testUrl(String url) async {
    try {
      final response = await http.get(
        Uri.parse('$url/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 3));
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Test if a Discovery Service URL is accessible (for nginx-proxied endpoints)
  Future<bool> _testDiscoveryUrl(String baseUrl) async {
    try {
      // For nginx-proxied discovery service, test the API endpoint directly
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/services'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 3));
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Discover all registered services
  Future<List<ServiceInfo>> discoverServices() async {
    try {
      // Auto-detect correct discovery service URL
      final discoveryUrl = await _getDiscoveryUrl();
      print('🔍 Discovering services from PPL Meta Discovery Service...');
      print('🌐 Discovery URL: $discoveryUrl/api/v1/services');
      
      final response = await http.get(
        Uri.parse('$discoveryUrl/api/v1/services'),
        headers: {'Accept': 'application/json'},
      ).timeout(_discoveryTimeout);
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final services = (data['services'] as List)
            .map((service) => ServiceInfo.fromJson(service))
            .where((service) => service.status == 'healthy')
            .toList();
        
        print('✅ Discovered ${services.length} healthy services');
        for (final service in services) {
          print('  📱 ${service.name} (${service.serviceType}) - ${service.host}:${service.port}');
        }
        
        return services;
      } else {
        throw DiscoveryException('Discovery service returned ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      print('❌ Discovery failed: $e');
      throw DiscoveryException('Failed to discover services: $e');
    }
  }

  /// Find a specific service by name
  Future<ServiceInfo?> findService(String serviceName) async {
    final services = await discoverServices();
    
    // Try exact match first
    var service = services.where((s) => s.name == serviceName).firstOrNull;
    
    // If no exact match, try partial match
    service ??= services.where((s) => s.name.contains(serviceName)).firstOrNull;
    
    if (service != null) {
      print('🎯 Found service: ${service.name} at ${service.baseUrl}');
    } else {
      print('❌ Service not found: $serviceName');
    }
    
    return service;
  }

  /// Find the gateway service (main entry point)
  Future<ServiceInfo?> findGateway() async {
    return await findService('ppl-meta-gateway');
  }

  /// Find the node service
  Future<ServiceInfo?> findNodeService() async {
    return await findService('ppl-meta-node');
  }

  /// Find the media service
  Future<ServiceInfo?> findMediaService() async {
    return await findService('ppl-meta-media');
  }

  /// Find the cameras service
  Future<ServiceInfo?> findCamerasService() async {
    return await findService('ppl-meta-cameras');
  }

  /// Test if discovery service is accessible
  Future<bool> testDiscoveryService() async {
    try {
      // Auto-detect correct discovery service URL
      final discoveryUrl = await _getDiscoveryUrl();
      print('🩺 Testing discovery service health at: $discoveryUrl');
      
      final response = await http.get(
        Uri.parse('$discoveryUrl/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      final healthy = response.statusCode == 200;
      print('🩺 Discovery service health: ${healthy ? "✅ OK" : "❌ Failed"}');
      return healthy;
    } catch (e) {
      print('🩺 Discovery service health: ❌ Failed ($e)');
      return false;
    }
  }
}

/// Enhanced network discovery service with PPL Meta Discovery Service integration
class EnhancedNetworkDiscoveryService {
  final PPLMetaDiscoveryClient _discoveryClient = PPLMetaDiscoveryClient();
  
  /// Auto-discover Node service using PPL Meta Discovery Service with fallbacks
  Future<String?> autoDiscoverNodeService() async {
    print('🎯 Starting enhanced network discovery...');
    
    try {
      // Primary: Use PPL Meta Discovery Service
      print('📡 Primary method: PPL Meta Discovery Service...');
      if (await _discoveryClient.testDiscoveryService()) {
        final nodeService = await _discoveryClient.findNodeService();
        
        if (nodeService != null) {
          final baseUrl = nodeService.baseUrl;
          print('✅ Discovery service successful: $baseUrl');
          
          // Verify the service is accessible
          if (await _testConnection(baseUrl)) {
            print('✅ Node service verified via discovery: $baseUrl');
            return baseUrl;
          } else {
            print('⚠️ Node service not accessible, trying fallback');
          }
        }
      } else {
        print('⚠️ Discovery service not accessible, trying fallback');
      }
      
      // Fallback 1: Try localhost/nginx proxy
      print('🔄 Fallback 1: Testing localhost/nginx proxy...');
      final localhostUrl = await _testLocalhostProxy();
      
      if (localhostUrl != null && await _testConnection(localhostUrl)) {
        print('✅ Localhost/nginx proxy successful: $localhostUrl');
        return localhostUrl;
      }
      
      // Fallback 2: Try direct node service
      print('🔄 Fallback 2: Testing direct node service...');
      const directNodeUrl = 'http://localhost:8001';
      
      if (await _testConnection(directNodeUrl)) {
        print('✅ Direct node service successful: $directNodeUrl');
        return directNodeUrl;
      }
      
      // Fallback 3: Network scan (from original implementation)
      print('🔄 Fallback 3: Network scan...');
      final networkUrl = await _scanLocalNetwork();
      
      if (networkUrl != null && await _testConnection(networkUrl)) {
        print('✅ Network scan successful: $networkUrl');
        return networkUrl;
      }
      
      print('❌ All discovery methods failed');
      return null;
      
    } catch (e) {
      print('❌ Enhanced discovery error: $e');
      return null;
    }
  }

  /// Test localhost nginx proxy for development
  Future<String?> _testLocalhostProxy() async {
    try {
      print('🏠 Testing localhost nginx proxy...');
      
      final localhostUrls = [
        'http://localhost',      // nginx proxy root
        'http://127.0.0.1',     // localhost IP
      ];
      
      for (final url in localhostUrls) {
        print('🔍 Testing localhost URL: $url');
        if (await _testConnection(url)) {
          print('🎯 Found PPL Meta via localhost: $url');
          return url;
        }
      }
      
      print('⚠️ No localhost services found');
      return null;
      
    } catch (e) {
      print('❌ Error testing localhost: $e');
      return null;
    }
  }

  /// Scan local network for PPL Meta Node service (simplified version)
  Future<String?> _scanLocalNetwork() async {
    try {
      print('🔍 Scanning local network for PPL Meta services...');
      
      // REMOVED: No hardcoded common IPs - explicit user configuration required
      print('� No hardcoded network IPs available - user must explicitly configure');
      return null;
      
      print('⚠️ No network services found');
      return null;
      
    } catch (e) {
      print('❌ Error scanning network: $e');
      return null;
    }
  }

  /// Test if a service URL is accessible
  Future<bool> _testConnection(String baseUrl) async {
    try {
      print('🩺 Testing connection to: $baseUrl');
      
      final client = http.Client();
      
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
      
      print('🌐 Making request to: $uri');
      
      final response = await client.get(uri).timeout(const Duration(seconds: 5));
      client.close();
      
      final success = response.statusCode == 200;
      if (success) {
        print('🩺 Health check $baseUrl: ✅ OK (${response.statusCode})');
      } else {
        print('🩺 Health check $baseUrl: ❌ Failed (HTTP ${response.statusCode})');
      }
      
      return success;
      
    } catch (e) {
      print('🩺 Health check $baseUrl: ❌ Failed ($e)');
      return false;
    }
  }
}

/// Service information from discovery service
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
