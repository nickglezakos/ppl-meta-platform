import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:network_info_plus/network_info_plus.dart';

/// Service for automatic IP detection and Node service discovery
class NetworkAutoDiscoveryService {
  final NetworkInfo _networkInfo = NetworkInfo();
  
  /// Auto-discover Node service URL using device IP detection
  /// 
  /// Algorithm:
  /// 1. Get device IP (e.g., 192.168.21.66)
  /// 2. Extract network prefix (192.168.21.)
  /// 3. Try .253 (Mac standard) with hardcoded port 8001
  /// 4. Fallback to .1 (router) then .254 if needed
  Future<String> autoDiscoverNodeService() async {
    print('🔍 Starting Node service auto-discovery...');
    
    final deviceIP = await _getDeviceIP();
    print('📱 Device IP detected: $deviceIP');
    
    final networkPrefix = _extractNetworkPrefix(deviceIP);
    print('🌐 Network prefix: ${networkPrefix}xxx');
    
    // Primary: Try .253 (Mac standard)
    String nodeURL = '${networkPrefix}253:8001';
    print('🎯 Trying primary: http://$nodeURL');
    if (await _testConnection(nodeURL)) {
      print('✅ Node service found at: http://$nodeURL');
      return nodeURL;
    }
    
    // Fallback 1: Try .1 (router)
    nodeURL = '${networkPrefix}1:8001';
    print('🎯 Trying fallback 1: http://$nodeURL');
    if (await _testConnection(nodeURL)) {
      print('✅ Node service found at: http://$nodeURL');
      return nodeURL;
    }
    
    // Fallback 2: Try .254 (router alternative)
    nodeURL = '${networkPrefix}254:8001';
    print('🎯 Trying fallback 2: http://$nodeURL');
    if (await _testConnection(nodeURL)) {
      print('✅ Node service found at: http://$nodeURL');
      return nodeURL;
    }
    
    throw NetworkDiscoveryException(
      'Node service not found on network. Tried: '
      '${networkPrefix}253:8001, ${networkPrefix}1:8001, ${networkPrefix}254:8001'
    );
  }
  
  /// Get device's current WiFi IP address
  Future<String> _getDeviceIP() async {
    try {
      final wifiIP = await _networkInfo.getWifiIP();
      if (wifiIP == null || wifiIP.isEmpty) {
        throw NetworkException('No WiFi connection detected');
      }
      return wifiIP;
    } catch (e) {
      throw NetworkException('Failed to get device IP: $e');
    }
  }
  
  /// Extract network prefix from IP address
  /// Example: 192.168.21.66 → 192.168.21.
  String _extractNetworkPrefix(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) {
      throw NetworkException('Invalid IP address format: $ip');
    }
    return '${parts[0]}.${parts[1]}.${parts[2]}.';
  }
  
  /// Test connection to a Node service URL
  Future<bool> _testConnection(String nodeURL) async {
    try {
      final response = await http.get(
        Uri.parse('http://$nodeURL/api/v1/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 3));
      
      final isHealthy = response.statusCode == 200;
      print('🏥 Health check http://$nodeURL/api/v1/health: ${response.statusCode} ${isHealthy ? "✅" : "❌"}');
      return isHealthy;
      
    } catch (e) {
      print('❌ Connection failed to http://$nodeURL: $e');
      return false;
    }
  }
  
  /// Get current device IP for camera registration
  Future<String> getDeviceIPForRegistration() async {
    return await _getDeviceIP();
  }
}

/// Exception thrown when network discovery fails
class NetworkDiscoveryException implements Exception {
  final String message;
  NetworkDiscoveryException(this.message);
  
  @override
  String toString() => 'NetworkDiscoveryException: $message';
}

/// Exception thrown for general network errors
class NetworkException implements Exception {
  final String message;
  NetworkException(this.message);
  
  @override
  String toString() => 'NetworkException: $message';
}
