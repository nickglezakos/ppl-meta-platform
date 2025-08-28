import 'dart:convert';
import 'package:http/http.dart' as http;

/// Network connectivity testing for mobile app
void main() async {
  print('🌐 Testing Network Connectivity from Mobile App');
  print('='.repeat(50));
  
  final hostIP = '192.168.1.68'; // Host machine IP
  
  final testCases = [
    // Discovery Service
    {'name': 'Discovery Service', 'url': 'http://$hostIP:8006/health'},
    
    // Direct service endpoints
    {'name': 'Gateway Service', 'url': 'http://$hostIP:8080/health'},
    {'name': 'Node Service', 'url': 'http://$hostIP:8001/api/v1/health'},
    {'name': 'Media Service', 'url': 'http://$hostIP:8000/health'},
    {'name': 'Orchestrator Service', 'url': 'http://$hostIP:8002/health'},
    {'name': 'Cameras Service', 'url': 'http://$hostIP:8005/health'},
    {'name': 'Vision Service', 'url': 'http://$hostIP:8003/health'},
  ];
  
  print('🎯 Host Machine IP: $hostIP');
  print('📱 Testing from mobile device...\n');
  
  for (final test in testCases) {
    await testService(test['name']!, test['url']!);
  }
  
  print('\n🔍 Testing Discovery Service Integration...');
  await testDiscoveryService(hostIP);
}

Future<void> testService(String name, String url) async {
  try {
    print('🔍 Testing $name: $url');
    
    final response = await http.get(
      Uri.parse(url),
      headers: {'Accept': 'application/json'},
    ).timeout(const Duration(seconds: 5));
    
    if (response.statusCode == 200) {
      try {
        final data = json.decode(response.body);
        print('✅ $name: HEALTHY - ${data['status'] ?? 'OK'}');
      } catch (e) {
        print('✅ $name: RESPONDING (${response.statusCode})');
      }
    } else {
      print('⚠️ $name: HTTP ${response.statusCode}');
    }
  } catch (e) {
    print('❌ $name: FAILED - $e');
  }
}

Future<void> testDiscoveryService(String hostIP) async {
  try {
    print('🔍 Discovery Service: http://$hostIP:8006/api/v1/services');
    
    final response = await http.get(
      Uri.parse('http://$hostIP:8006/api/v1/services'),
      headers: {'Accept': 'application/json'},
    ).timeout(const Duration(seconds: 5));
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final services = data['services'] as List;
      
      print('✅ Discovery Service: Found ${services.length} registered services');
      
      for (final service in services) {
        final name = service['name'];
        final host = service['host'];
        final port = service['port'];
        final status = service['status'];
        
        print('  📡 $name: $host:$port [$status]');
        
        // Test if service is accessible via registered address
        if (host != '0.0.0.0') {
          final serviceUrl = 'http://$host:$port/health';
          await testService('  → $name (via discovery)', serviceUrl);
        } else {
          print('  ⚠️ $name: Host 0.0.0.0 not accessible from mobile');
        }
      }
    } else {
      print('❌ Discovery Service: HTTP ${response.statusCode}');
    }
  } catch (e) {
    print('❌ Discovery Service: FAILED - $e');
  }
}
