import 'dart:convert';
import 'package:http/http.dart' as http;
import 'unified_discovery_service.dart';

/// Enhanced authentication service with unified discovery (multicast + central)
class EnhancedAutoAuthenticationService {
  final UnifiedDiscoveryService _discoveryService = UnifiedDiscoveryService();
  
  /// Automatic login with comprehensive service discovery
  /// 
  /// Process:
  /// 1. Use unified discovery (central + multicast + local scan)
  /// 2. Find best Node service for authentication
  /// 3. Login with discovered endpoint
  /// 4. Get platform services with JWT token
  Future<AuthResult> autoLogin(String username, String password) async {
    try {
      print('🔐 Starting enhanced automatic login process...');
      print('👤 Username: $username');
      
      // Step 1: Unified service discovery
      print('🔍 Step 1: Running unified service discovery...');
      final nodeService = await _discoveryService.findBestNodeService();
      
      if (nodeService == null) {
        throw AuthException('Failed to discover any Node service using all discovery methods');
      }
      
      final nodeURL = nodeService.baseUrl;
      print('🎯 Selected Node service: $nodeURL (via ${nodeService.discoveryMethod})');
      print('📊 Service details:');
      print('   Host: ${nodeService.host}:${nodeService.port}');
      print('   Version: ${nodeService.version}');
      print('   Status: ${nodeService.status}');
      print('   Capabilities: ${nodeService.capabilities.join(', ')}');
      
      // Step 2: Login with discovered endpoint
      print('📤 Step 2: Authenticating with Node service...');
      final loginURL = '$nodeURL/api/v1/users/login';
      print('🎯 Authentication endpoint: $loginURL');
      
      final response = await http.post(
        Uri.parse(loginURL),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: 'username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}',
      ).timeout(const Duration(seconds: 10));
      
      print('📥 Login response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // The server returns 'access_token', not 'token'
        final token = data['access_token'] as String?;
        
        if (token == null || token.isEmpty) {
          print('❌ Login response data: $data');
          throw AuthException('No access token received from login response');
        }
        
        print('✅ Login successful! JWT token obtained.');
        print('🎫 Token preview: ${token.substring(0, 20)}...');
        
        // Step 3: Get platform services with JWT
        print('🔍 Step 3: Discovering platform services...');
        final services = await _getPlatformServices(nodeURL, token);
        print('✅ Platform services discovered successfully!');
        
        // Step 4: Get discovered services for additional context
        print('🔍 Step 4: Getting additional discovered services...');
        final discoveredServices = _discoveryService.currentServices;
        print('📊 Total discovered services: ${discoveredServices.length}');
        for (final service in discoveredServices) {
          print('   - ${service.name} at ${service.baseUrl} (${service.discoveryMethod})');
        }
        
        return AuthResult.success(
          token: token,
          nodeURL: nodeURL,
          services: services,
          discoveredServices: discoveredServices,
          discoveryMethod: nodeService.discoveryMethod,
        );
      } else {
        final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
        throw AuthException('Login failed with status ${response.statusCode}: $errorBody');
      }
      
    } catch (e) {
      print('💥 Login exception: $e');
      if (e is AuthException) rethrow;
      throw AuthException('Login process failed: $e');
    } finally {
      // Don't dispose here as we might need discovery service later
      // _discoveryService.dispose();
    }
  }
  
  /// Get platform services using JWT token
  Future<PlatformServices> _getPlatformServices(String nodeURL, String token) async {
    final servicesURL = '$nodeURL/api/v1/users/platform/services';
    print('🎯 Platform services endpoint: $servicesURL');
    
    final response = await http.get(
      Uri.parse(servicesURL),
      headers: {
        'Authorization': 'Bearer $token',
        'Accept': 'application/json',
      },
    ).timeout(const Duration(seconds: 10));
    
    print('📥 Platform services response status: ${response.statusCode}');
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return PlatformServices.fromJson(data);
    } else {
      throw AuthException('Failed to get platform services: ${response.statusCode} - ${response.body}');
    }
  }

  /// Get current discovery service (for accessing discovered services)
  UnifiedDiscoveryService get discoveryService => _discoveryService;

  /// Refresh service discovery
  Future<List<DiscoveredServiceInfo>> refreshDiscovery() async {
    return await _discoveryService.discoverAllServices();
  }

  /// Dispose resources
  void dispose() {
    _discoveryService.dispose();
  }
}

/// Enhanced authentication result container with discovery information
class AuthResult {
  final bool success;
  final String? token;
  final String? nodeURL;
  final PlatformServices? services;
  final String? error;
  final List<DiscoveredServiceInfo>? discoveredServices;
  final String? discoveryMethod;
  
  AuthResult._({
    required this.success,
    this.token,
    this.nodeURL, 
    this.services,
    this.error,
    this.discoveredServices,
    this.discoveryMethod,
  });
  
  factory AuthResult.success({
    required String token,
    required String nodeURL,
    required PlatformServices services,
    List<DiscoveredServiceInfo>? discoveredServices,
    String? discoveryMethod,
  }) => AuthResult._(
    success: true,
    token: token,
    nodeURL: nodeURL,
    services: services,
    discoveredServices: discoveredServices,
    discoveryMethod: discoveryMethod,
  );
  
  factory AuthResult.failure(String error) => AuthResult._(
    success: false,
    error: error,
  );

  /// Get summary of discovery results
  String get discoveryySummary {
    if (discoveredServices == null) return 'No discovery information';
    
    final groupedServices = <String, int>{};
    for (final service in discoveredServices!) {
      groupedServices[service.discoveryMethod] = 
          (groupedServices[service.discoveryMethod] ?? 0) + 1;
    }
    
    final parts = groupedServices.entries
        .map((e) => '${e.value} via ${e.key}')
        .toList();
    
    return 'Found ${discoveredServices!.length} services: ${parts.join(', ')}';
  }
}

/// Platform services configuration (unchanged from original)
class PlatformServices {
  final ServiceEndpoint cameraService;
  final ServiceEndpoint mediaService;
  final ServiceEndpoint gatewayService;
  final ServiceEndpoint orchestratorService;
  final ServiceEndpoint? visionService;
  
  PlatformServices({
    required this.cameraService,
    required this.mediaService,
    required this.gatewayService,
    required this.orchestratorService,
    this.visionService,
  });
  
  factory PlatformServices.fromJson(Map<String, dynamic> json) {
    print('📊 Parsing platform services data:');
    print('   Available services: ${json.keys.join(", ")}');
    
    // Extract microservices from nested structure
    final microservices = json['microservices'] as Map<String, dynamic>?;
    if (microservices == null) {
      throw Exception('No microservices found in platform response');
    }
    
    print('   📱 Microservices found: ${microservices.keys.join(", ")}');
    
    return PlatformServices(
      cameraService: ServiceEndpoint.fromJson('cameras', microservices['cameras']),
      mediaService: ServiceEndpoint.fromJson('media', microservices['media']),
      gatewayService: ServiceEndpoint.fromJson('gateway', microservices['gateway']),
      orchestratorService: ServiceEndpoint.fromJson('orchestrator', microservices['orchestrator']),
      visionService: microservices['vision'] != null 
        ? ServiceEndpoint.fromJson('vision', microservices['vision'])
        : null,
    );
  }
}

/// Service endpoint configuration (unchanged from original)
class ServiceEndpoint {
  final String name;
  final String endpoint;
  final int port;
  final String healthEndpoint;
  
  ServiceEndpoint({
    required this.name,
    required this.endpoint,
    required this.port,
    required this.healthEndpoint,
  });
  
  factory ServiceEndpoint.fromJson(String serviceName, Map<String, dynamic> json) {
    // The new structure has nested endpoints with local/tailscale options
    final endpoints = json['endpoints'] as Map<String, dynamic>;
    final port = json['port'] as int;
    final healthEndpoint = json['health'] as String;
    
    // Prefer local endpoint, fallback to tailscale if available
    final endpoint = endpoints['local'] as String? ?? endpoints['tailscale'] as String;
    if (endpoint == null) {
      throw Exception('No valid endpoint found for $serviceName service');
    }
    
    print('   📹 $serviceName Service: $endpoint (port $port)');
    
    return ServiceEndpoint(
      name: serviceName,
      endpoint: endpoint,
      port: port,
      healthEndpoint: healthEndpoint,
    );
  }
}

/// Authentication exception (unchanged from original)
class AuthException implements Exception {
  final String message;
  AuthException(this.message);
  
  @override
  String toString() => 'AuthException: $message';
}
