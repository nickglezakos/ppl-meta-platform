import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:network_info_plus/network_info_plus.dart';

/// Modern Network Discovery Service with simplified device IP approach
/// 
/// This service implements the simplified discovery logic:
/// 1. Get device IP using NetworkInfo().getWifiIP()
/// 2. Use device IP directly with hardcoded port 8001
/// 3. No complex scanning - direct connection approach
class ModernNetworkDiscoveryService {
  static const int NODE_PORT = 8001;
  
  final NetworkInfo _networkInfo = NetworkInfo();
  
  /// Discover PPL Meta Node service using device IP directly
  Future<String> autoDiscoverNodeService() async {
    print('🔍 🚀 SIMPLE NETWORK DISCOVERY STARTING...');
    print('🔍 Using device IP to locate Node service');
    
    try {
      // Get device IP directly
      final deviceIP = await _networkInfo.getWifiIP();
      if (deviceIP == null) {
        throw NetworkDiscoveryException('No WiFi IP detected - device not connected to WiFi');
      }
      
      print('📱 Device IP detected: $deviceIP');
      
      // Construct Node service URL using same IP
      final nodeServiceURL = 'http://$deviceIP:$NODE_PORT';
      print('🎯 Testing Node service at: $nodeServiceURL');
      
      // Test connection to Node service
      if (await _testConnection(nodeServiceURL)) {
        print('✅ Node service found at device IP: $nodeServiceURL');
        return nodeServiceURL;
      }
      
      throw NetworkDiscoveryException('Node service not responding at $nodeServiceURL');
      
    } catch (e) {
      print('❌ Network discovery failed: $e');
      rethrow;
    }
  }
  
  /// Test connection to a service URL
  Future<bool> _testConnection(String url) async {
    try {
      print('🔍 Testing connection to: $url');
      final response = await http
          .get(Uri.parse('$url/api/v1/health'))
          .timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final isNodeService = data['service'] == 'ppl-meta-node';
        print('✅ Connection successful - Node service: $isNodeService');
        return isNodeService;
      } else {
        print('❌ Connection failed - Status: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('❌ Connection error: $e');
      return false;
    }
  }
}

/// Network discovery exception
class NetworkDiscoveryException implements Exception {
  final String message;
  NetworkDiscoveryException(this.message);
  
  @override
  String toString() => 'NetworkDiscoveryException: $message';
}
