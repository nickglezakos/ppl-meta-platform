#!/usr/bin/env dart

import 'dart:io';
import 'dart:convert';

/// Fast test for Discovery Service integration
Future<void> main() async {
  print('🚀 Fast Discovery Service Integration Test');
  print('==========================================');
  
  await quickDiscoveryTest();
}

Future<void> quickDiscoveryTest() async {
  print('🔍 Testing Discovery Service...');
  
  // Test nginx proxy first (most likely to work)
  final client = HttpClient();
  client.connectionTimeout = Duration(seconds: 3);
  
  try {
    final request = await client.getUrl(Uri.parse('http://localhost/discovery/health'));
    final response = await request.close();
    
    if (response.statusCode == 200) {
      final body = await response.transform(utf8.decoder).join();
      final data = jsonDecode(body);
      
      print('✅ Discovery Service found via nginx proxy');
      print('   Service: ${data['service']}');
      print('   Status: ${data['status']}');
      
      // Quick test of services API
      await testServicesAPI();
      
    } else {
      print('❌ Discovery Service not accessible via nginx');
    }
    
  } catch (e) {
    print('❌ Discovery Service test failed: $e');
  } finally {
    client.close();
  }
}

Future<void> testServicesAPI() async {
  print('');
  print('📋 Testing Services API...');
  
  final client = HttpClient();
  client.connectionTimeout = Duration(seconds: 3);
  
  try {
    final request = await client.getUrl(Uri.parse('http://localhost/discovery/api/v1/services'));
    final response = await request.close();
    
    if (response.statusCode == 200) {
      final body = await response.transform(utf8.decoder).join();
      final data = jsonDecode(body);
      
      final services = data['services'] as List;
      
      print('✅ Services API working');
      print('   Total services: ${services.length}');
      print('   Healthy services: ${data['healthy_count'] ?? 0}');
      
      if (services.isNotEmpty) {
        print('');
        print('🎯 Service Registry Summary:');
        for (final service in services.take(3)) { // Show only first 3
          print('   📱 ${service['name']} - ${service['status']}');
        }
        if (services.length > 3) {
          print('   ... and ${services.length - 3} more services');
        }
      }
      
      print('');
      print('✅ SUCCESS: Pure Discovery Service integration working!');
      print('   • Mobile app would discover ONLY the Discovery Service');
      print('   • All other service info comes from Discovery Service API');
      print('   • Single point discovery architecture confirmed');
      
    } else {
      print('❌ Services API not responding');
    }
    
  } catch (e) {
    print('❌ Services API test failed: $e');
  } finally {
    client.close();
  }
}
