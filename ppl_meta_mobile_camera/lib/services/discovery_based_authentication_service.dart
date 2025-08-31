import 'dart:convert';
import 'package:http/http.dart' as http;
import 'simplified_discovery_client.dart';

/// Pure Discovery Service-based authentication service
/// 
/// This service ONLY discovers the Discovery Service, then uses its API
/// to get all other service information. No complex client-side discovery.
class DiscoveryBasedAuthenticationService {
  final SimplifiedDiscoveryClient _discoveryClient = SimplifiedDiscoveryClient();
  
  List<ServiceInfo>? _cachedServices;
  
  /// Main authentication method using Discovery Service
  Future<AuthResult> authenticateViaDiscovery(String username, String password) async {
    try {
      print('🔐 Starting Discovery Service-based authentication...');
      print('👤 Username: $username');
      
      // Step 1: Get all services from Discovery Service
      print('🔍 Step 1: Getting services from Discovery Service...');
      final services = await _getServicesFromDiscovery();
      
      if (services.isEmpty) {
        throw AuthException('No services available from Discovery Service');
      }
      
      print('✅ Found ${services.length} services from Discovery Service');
      for (final service in services) {
        print('  📱 ${service.name} at ${service.baseUrl}');
      }
      
      // Step 2: Find Node service for authentication
      print('🔍 Step 2: Locating Node service for authentication...');
      final nodeService = services.where((s) => s.name == 'ppl-meta-node').firstOrNull;
      
      if (nodeService == null) {
        throw AuthException('Node service not found in Discovery Service registry');
      }
      
      print('🎯 Found Node service: ${nodeService.baseUrl}');
      
      // Step 3: Authenticate with Node service
      print('📤 Step 3: Authenticating with Node service...');
      final token = await _authenticateWithNodeService(nodeService, username, password);
      
      // Step 4: Return complete service discovery result
      print('✅ Authentication successful! Building service map...');
      final serviceMap = _buildServiceMap(services);
      
      return AuthResult.success(
        token: token,
        nodeURL: nodeService.baseUrl,
        services: PlatformServices(
          nodeService: nodeService.baseUrl,
          gatewayService: await getServiceUrl('ppl-meta-gateway'),
          mediaService: await getServiceUrl('ppl-meta-media'),
          cameraService: await getServiceUrl('ppl-meta-cameras'),
          visionService: await getServiceUrl('ppl-meta-vision'),
          discoveryService: await _discoveryClient.findDiscoveryService(),
        ),
      );
      
    } catch (e) {
      print('💥 Discovery-based authentication failed: $e');
      if (e is AuthException) rethrow;
      throw AuthException('Discovery authentication failed: $e');
    }
  }
  
    /// Get all services from Discovery Service with caching
  Future<List<ServiceInfo>> _getServicesFromDiscovery() async {
    try {
      print('📋 Fetching services from Discovery Service...');
      
      final services = await _discoveryClient.getAllServices();
      _cachedServices = services;
      
      print('✅ Retrieved ${services.length} services from Discovery Service:');
      for (final service in services) {
        print('  📱 ${service.name} (${service.serviceType}) - ${service.baseUrl}');
      }
      
      return services;
      
    } catch (e) {
      print('❌ Failed to get services from Discovery Service: $e');
      
      // Return cached services if available
      if (_cachedServices != null && _cachedServices!.isNotEmpty) {
        print('� Using cached services (${_cachedServices!.length} services)');
        return _cachedServices!;
      }
      
      throw AuthException('Discovery Service not available and no cached services');
    }
  }
  
  /// Authenticate with a specific Node service
  Future<String> _authenticateWithNodeService(ServiceInfo nodeService, String username, String password) async {
    final loginURL = '${nodeService.baseUrl}/api/v1/users/login';
    print('🎯 Authentication endpoint: $loginURL');
    
    try {
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
        final token = data['access_token'] as String?;
        
        if (token == null || token.isEmpty) {
          print('❌ Login response data: $data');
          throw AuthException('No access token received from login response');
        }
        
        print('✅ Authentication successful! JWT token obtained.');
        print('🎫 Token preview: ${token.substring(0, 20)}...');
        
        return token;
      } else {
        final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
        throw AuthException('Login failed with status ${response.statusCode}: $errorBody');
      }
    } catch (e) {
      print('❌ Node service authentication failed: $e');
      rethrow;
    }
  }
  
  /// Build service map from Discovery Service data
  Map<String, String> _buildServiceMap(List<ServiceInfo> services) {
    final serviceMap = <String, String>{};
    
    for (final service in services) {
      serviceMap[service.name] = service.baseUrl;
      print('🗺️ ${service.name} → ${service.baseUrl}');
    }
    
    return serviceMap;
  }
  
  /// Get specific service URL by name
  Future<String?> getServiceUrl(String serviceName) async {
    try {
      final services = await _getServicesFromDiscovery();
      final service = services.where((s) => s.name == serviceName).firstOrNull;
      
      if (service != null) {
        print('🎯 Found $serviceName at ${service.baseUrl}');
        return service.baseUrl;
      } else {
        print('❌ Service $serviceName not found in Discovery Service');
        return null;
      }
    } catch (e) {
      print('❌ Failed to get service URL for $serviceName: $e');
      return null;
    }
  }
  
  /// Test connectivity to a specific service
  Future<bool> testServiceConnectivity(String serviceName) async {
    try {
      final services = await _getServicesFromDiscovery();
      final service = services.where((s) => s.name == serviceName).firstOrNull;
      
      if (service == null) {
        print('❌ Service $serviceName not found for connectivity test');
        return false;
      }
      
      final response = await http.get(
        Uri.parse(service.fullHealthUrl),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      final connected = response.statusCode == 200;
      print('🩺 $serviceName connectivity: ${connected ? "✅ OK" : "❌ Failed"} (${response.statusCode})');
      
      return connected;
    } catch (e) {
      print('🩺 $serviceName connectivity: ❌ Failed ($e)');
      return false;
    }
  }
  
  /// Refresh service cache from Discovery Service
  Future<void> refreshServiceCache() async {
    print('🔄 Refreshing service cache from Discovery Service...');
    _cachedServices = null;
    await _getServicesFromDiscovery();
    print('✅ Service cache refreshed');
  }
  
  /// Get all available services
  Future<List<ServiceInfo>> getAllServices() async {
    return await _getServicesFromDiscovery();
  }
}

/// Authentication result with Discovery Service integration
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
  }) {
    return AuthResult._(
      success: true,
      token: token,
      nodeURL: nodeURL,
      services: services,
    );
  }
  
  factory AuthResult.failure(String error) {
    return AuthResult._(
      success: false,
      error: error,
    );
  }
}

/// Platform services from Discovery Service
class PlatformServices {
  final String? nodeService;
  final String? mediaService;
  final String? gatewayService;
  final String? cameraService;
  final String? visionService;
  final String? orchestratorService;
  final String? discoveryService;
  
  PlatformServices({
    this.nodeService,
    this.mediaService,
    this.gatewayService,
    this.cameraService,
    this.visionService,
    this.orchestratorService,
    this.discoveryService,
  });
  
  factory PlatformServices.fromJson(Map<String, dynamic> json) {
    return PlatformServices(
      nodeService: json['nodeService'],
      mediaService: json['mediaService'],
      gatewayService: json['gatewayService'],
      cameraService: json['cameraService'],
      visionService: json['visionService'],
      orchestratorService: json['orchestratorService'],
      discoveryService: json['discoveryService'],
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'nodeService': nodeService,
      'mediaService': mediaService,
      'gatewayService': gatewayService,
      'cameraService': cameraService,
      'visionService': visionService,
      'orchestratorService': orchestratorService,
      'discoveryService': discoveryService,
    };
  }
  
  @override
  String toString() {
    return 'PlatformServices(${[
      if (nodeService != null) 'node: $nodeService',
      if (mediaService != null) 'media: $mediaService',
      if (gatewayService != null) 'gateway: $gatewayService',
      if (cameraService != null) 'camera: $cameraService',
      if (visionService != null) 'vision: $visionService',
      if (orchestratorService != null) 'orchestrator: $orchestratorService',
      if (discoveryService != null) 'discovery: $discoveryService',
    ].join(', ')})';
  }
}

/// Authentication exception
class AuthException implements Exception {
  final String message;
  AuthException(this.message);
  
  @override
  String toString() => 'AuthException: $message';
}
