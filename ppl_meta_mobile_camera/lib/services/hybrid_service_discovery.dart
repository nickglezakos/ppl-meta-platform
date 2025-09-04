import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../core/models/auth_result.dart';
import 'multicast_network_discovery.dart';

/// Enhanced service discovery that combines multicast with PPL Meta Discovery Service
class HybridServiceDiscoveryService {
  final EnhancedNetworkDiscoveryService _multicastService = EnhancedNetworkDiscoveryService();
  
  /// Discover Node service using hybrid approach:
  /// 1. Try multicast discovery (local network)
  /// 2. Try PPL Meta Discovery Service (centralized)
  /// 3. Fallback to network scanning
  Future<String?> discoverNodeService() async {
    debugPrint('🌐 Starting hybrid service discovery...');
    
    try {
      // Method 1: Try multicast discovery first (fastest for local networks)
      debugPrint('📡 Method 1: Multicast discovery...');
      final multicastResult = await _multicastService.autoDiscoverNodeService();
      
      if (multicastResult != null) {
        debugPrint('✅ Multicast discovery successful: $multicastResult');
        return multicastResult;
      }
      
      // Method 2: Try PPL Meta Discovery Service (centralized service registry)
      debugPrint('🔍 Method 2: PPL Meta Discovery Service...');
      final discoveryResult = await _tryPPLMetaDiscoveryService();
      
      if (discoveryResult != null) {
        debugPrint('✅ PPL Meta Discovery Service successful: $discoveryResult');
        return discoveryResult;
      }
      
      // Method 3: Fallback methods already implemented in EnhancedNetworkDiscoveryService
      debugPrint('⚠️ Centralized discovery failed, using existing fallback methods');
      return null;
      
    } catch (e) {
      debugPrint('❌ Hybrid discovery error: $e');
      return null;
    }
  }
  
  /// Try to discover services using PPL Meta Discovery Service
  Future<String?> _tryPPLMetaDiscoveryService() async {
    try {
      // Common discovery service endpoints to try
      final discoveryUrls = [
        'http://localhost:8006',           // Local development
        'http://127.0.0.1:8006',          // Localhost IP
        'http://192.168.129.107:8006',    // Current network - main service
        'http://192.168.129.100:8006',    // Current network - common IP
        'http://192.168.129.1:8006',      // Current network router
        'http://192.168.1.100:8006',      // Common local network
        'http://192.168.1.1:8006',        // Router IP
        'http://10.0.0.1:8006',           // Alternative local network
      ];
      
      for (final discoveryUrl in discoveryUrls) {
        debugPrint('🔍 Trying discovery service: $discoveryUrl');
        
        final nodeUrl = await _queryDiscoveryService(discoveryUrl);
        if (nodeUrl != null) {
          debugPrint('✅ Found Node service via discovery: $nodeUrl');
          return nodeUrl;
        }
      }
      
      debugPrint('⚠️ No discovery services responded');
      return null;
      
    } catch (e) {
      debugPrint('❌ PPL Meta Discovery Service error: $e');
      return null;
    }
  }
  
  /// Query a specific discovery service for Node service
  Future<String?> _queryDiscoveryService(String discoveryUrl) async {
    try {
      final response = await http.get(
        Uri.parse('$discoveryUrl/api/v1/services'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final services = data['services'] as List?;
        
        if (services != null) {
          // Look for Node service
          for (final service in services) {
            if (service['name'] == 'ppl-meta-node' && service['status'] == 'healthy') {
              final host = service['host'];
              final port = service['port'];
              
              // Convert 0.0.0.0 to localhost for mobile access
              final finalHost = (host == '0.0.0.0') ? 'localhost' : host;
              final nodeUrl = 'http://$finalHost:$port';
              
              debugPrint('🎯 Found Node service in discovery: $nodeUrl');
              debugPrint('   Service ID: ${service['service_id']}');
              debugPrint('   Version: ${service['version']}');
              debugPrint('   Capabilities: ${service['capabilities']}');
              
              // Verify the service is accessible
              if (await _testNodeConnection(nodeUrl)) {
                return nodeUrl;
              } else {
                debugPrint('⚠️ Node service not accessible: $nodeUrl');
              }
            }
          }
        }
      }
      
      return null;
      
    } catch (e) {
      debugPrint('⚠️ Error querying $discoveryUrl: $e');
      return null;
    }
  }
  
  /// Test if Node service is accessible
  Future<bool> _testNodeConnection(String nodeUrl) async {
    try {
      final response = await http.get(
        Uri.parse('$nodeUrl/api/v1/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 3));
      
      final success = response.statusCode == 200;
      debugPrint('🩺 Node health check $nodeUrl: ${success ? "✅" : "❌"} (${response.statusCode})');
      
      return success;
      
    } catch (e) {
      debugPrint('🩺 Node health check $nodeUrl: ❌ ($e)');
      return false;
    }
  }
  
  /// Get all available services from discovery service (for debugging)
  Future<List<Map<String, dynamic>>> getAvailableServices() async {
    try {
      final discoveryUrls = [
        'http://localhost:8006',
        'http://127.0.0.1:8006',
      ];
      
      for (final discoveryUrl in discoveryUrls) {
        try {
          final response = await http.get(
            Uri.parse('$discoveryUrl/api/v1/services'),
            headers: {'Accept': 'application/json'},
          ).timeout(const Duration(seconds: 5));
          
          if (response.statusCode == 200) {
            final data = jsonDecode(response.body);
            final services = List<Map<String, dynamic>>.from(data['services'] ?? []);
            
            debugPrint('📋 Discovery service $discoveryUrl found ${services.length} services:');
            for (final service in services) {
              debugPrint('   - ${service['name']} (${service['status']}) at ${service['host']}:${service['port']}');
            }
            
            return services;
          }
        } catch (e) {
          debugPrint('⚠️ Error getting services from $discoveryUrl: $e');
        }
      }
      
      return [];
      
    } catch (e) {
      debugPrint('❌ Error getting available services: $e');
      return [];
    }
  }
}

/// Enhanced authentication service that uses hybrid discovery
class EnhancedAutoAuthenticationService {
  final HybridServiceDiscoveryService _discoveryService = HybridServiceDiscoveryService();
  
  /// Automatic login with hybrid service discovery
  Future<AuthResult> autoLogin(String username, String password) async {
    try {
      debugPrint('🔐 Starting enhanced automatic login...');
      debugPrint('👤 Username: $username');
      
      // Step 1: Discover Node service using hybrid approach
      debugPrint('🔍 Step 1: Discovering Node service...');
      final nodeURL = await _discoveryService.discoverNodeService();
      
      if (nodeURL == null) {
        // Show available services for debugging
        final availableServices = await _discoveryService.getAvailableServices();
        debugPrint('📋 Available services from discovery: ${availableServices.length}');
        for (final service in availableServices) {
          debugPrint('   - ${service['name']}: ${service['host']}:${service['port']} (${service['status']})');
        }
        
        throw AuthException('Failed to discover Node service using all methods');
      }
      
      debugPrint('🎯 Node service discovered: $nodeURL');
      
      // Step 2: Login with discovered endpoint
      debugPrint('📤 Step 2: Authenticating...');
      final loginURL = '$nodeURL/api/v1/users/login';
      
      final response = await http.post(
        Uri.parse(loginURL),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: 'username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}',
      ).timeout(const Duration(seconds: 10));
      
      debugPrint('📥 Login response: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        
        if (token == null || token.isEmpty) {
          throw AuthException('No access token received');
        }
        
        debugPrint('✅ Authentication successful!');
        
        // Step 3: Get platform services
        debugPrint('🔍 Step 3: Getting platform services...');
        final services = await _getPlatformServices(nodeURL, token);
        
        return AuthResult.success(token);
      } else {
        final errorBody = response.body.isNotEmpty ? response.body : 'No error details';
        throw AuthException('Login failed: HTTP ${response.statusCode} - $errorBody');
      }
      
    } catch (e) {
      debugPrint('💥 Enhanced login error: $e');
      if (e is AuthException) rethrow;
      throw AuthException('Enhanced login failed: $e');
    }
  }
  
  /// Get platform services configuration
  Future<PlatformServices> _getPlatformServices(String nodeURL, String token) async {
    final servicesURL = '$nodeURL/api/v1/users/platform/services';
    
    final response = await http.get(
      Uri.parse(servicesURL),
      headers: {
        'Authorization': 'Bearer $token',
        'Accept': 'application/json',
      },
    ).timeout(const Duration(seconds: 10));
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return PlatformServices.fromJson(data);
    } else {
      throw AuthException('Failed to get platform services: ${response.statusCode}');
    }
  }
}

/// Simple platform services model  
class PlatformServices {
  final Map<String, ServiceEndpoint> services;
  
  const PlatformServices({required this.services});
  
  factory PlatformServices.fromJson(Map<String, dynamic> json) {
    final services = <String, ServiceEndpoint>{};
    if (json['services'] is Map) {
      final servicesMap = json['services'] as Map<String, dynamic>;
      for (final entry in servicesMap.entries) {
        if (entry.value is Map) {
          services[entry.key] = ServiceEndpoint.fromJson(entry.value as Map<String, dynamic>);
        }
      }
    }
    return PlatformServices(services: services);
  }
}

/// Service endpoint model
class ServiceEndpoint {
  final String host;
  final int port;
  final String protocol;
  
  const ServiceEndpoint({
    required this.host,
    required this.port,
    this.protocol = 'http',
  });
  
  factory ServiceEndpoint.fromJson(Map<String, dynamic> json) {
    return ServiceEndpoint(
      host: json['host'] as String? ?? 'localhost',
      port: json['port'] as int? ?? 8000,
      protocol: json['protocol'] as String? ?? 'http',
    );
  }
  
  String get baseUrl => '$protocol://$host:$port';
}

/// Authentication exception
class AuthException implements Exception {
  final String message;
  final int? statusCode;
  
  const AuthException(this.message, {this.statusCode});
  
  @override
  String toString() => 'AuthException: $message${statusCode != null ? ' (${statusCode})' : ''}';
}
