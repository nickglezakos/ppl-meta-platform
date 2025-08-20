import 'dart:convert';
import 'package:http/http.dart' as http;
import 'multicast_network_discovery.dart';

/// Enhanced authentication service with multicast auto-discovery
class AutoAuthenticationService {
  final EnhancedNetworkDiscoveryService _networkService = EnhancedNetworkDiscoveryService();
  
  /// Automatic login with Node service auto-discovery
  /// 
  /// Process:
  /// 1. Auto-discover Node service using multicast + fallback
  /// 2. Login with discovered endpoint
  /// 3. Get platform services with JWT token
  Future<AuthResult> autoLogin(String username, String password) async {
    try {
      print('🔐 Starting automatic login process...');
      print('👤 Username: $username');
      
      // Step 1: Auto-discover Node service
      print('🔍 Step 1: Auto-discovering Node service...');
      final nodeURL = await _networkService.autoDiscoverNodeService();
      if (nodeURL == null) {
        throw AuthException('Failed to discover Node service');
      }
      
      print('🎯 Auto-discovered Node service: $nodeURL');
      
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
        
        return AuthResult.success(
          token: token,
          nodeURL: nodeURL,
          services: services,
        );
      } else {
        final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
        throw AuthException('Login failed with status ${response.statusCode}: $errorBody');
      }
      
    } catch (e) {
      print('💥 Login exception: $e');
      if (e is AuthException) rethrow;
      throw AuthException('Login process failed: $e');
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
}

/// Authentication result container
class AuthResult {
  final bool success;
  final String? token;
  final String? nodeURL;
  final PlatformServices? services;
  final String? error;
  
  AuthResult._({
    required this.success,
    this.token,
    this.nodeURL, 
    this.services,
    this.error,
  });
  
  factory AuthResult.success({
    required String token,
    required String nodeURL,
    required PlatformServices services,
  }) => AuthResult._(
    success: true,
    token: token,
    nodeURL: nodeURL,
    services: services,
  );
  
  factory AuthResult.failure(String error) => AuthResult._(
    success: false,
    error: error,
  );
}

/// Platform services configuration
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

/// Service endpoint configuration
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

/// Authentication exception
class AuthException implements Exception {
  final String message;
  AuthException(this.message);
  
  @override
  String toString() => 'AuthException: $message';
}
