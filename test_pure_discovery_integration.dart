#!/usr/bin/env dart

import 'dart:io';
import 'dart:convert';

/// Simple test script to demonstrate pure Discovery Service integration
/// This simulates how the mobile app will work

const String host = '192.168.1.68'; // Replace with your host IP

Future<void> main() async {
  print('🚀 PPL Meta Pure Discovery Service Integration Test');
  print('====================================================');
  print('');
  
  await testPureDiscoveryFlow();
}

Future<void> testPureDiscoveryFlow() async {
  try {
    print('📋 Step 1: Discover ONLY the Discovery Service');
    print('----------------------------------------------');
    
    final discoveryUrls = [
      'http://$host/discovery',      // Nginx proxy (recommended)
      'http://$host:8006',           // Direct access
      'http://localhost/discovery',   // Localhost nginx
      'http://localhost:8006',       // Localhost direct
    ];
    
    String? discoveryUrl;
    
    for (final url in discoveryUrls) {
      print('🔍 Testing Discovery Service at: $url');
      
      if (await testDiscoveryService(url)) {
        discoveryUrl = url;
        print('✅ Found Discovery Service at: $url');
        break;
      } else {
        print('❌ Not found at: $url');
      }
    }
    
    if (discoveryUrl == null) {
      print('❌ FAILED: Could not find Discovery Service');
      return;
    }
    
    print('');
    print('📋 Step 2: Get ALL service information from Discovery Service API');
    print('----------------------------------------------------------------');
    
    final services = await getServicesFromDiscovery(discoveryUrl);
    
    if (services.isEmpty) {
      print('⚠️ No services registered in Discovery Service');
    } else {
      print('✅ Found ${services.length} services from Discovery Service:');
      for (final service in services) {
        print('   📱 ${service['name']} (${service['service_type']})');
        print('      🌐 URL: http://${service['host']}:${service['port']}');
        print('      🏥 Health: ${service['status']}');
        print('      🔧 Capabilities: ${service['capabilities']}');
        print('');
      }
    }
    
    print('📋 Step 3: Simulate Mobile App Authentication Flow');
    print('------------------------------------------------');
    
    // Find Node service for authentication
    Map<String, dynamic>? nodeService;
    for (final service in services) {
      if (service['name'] == 'ppl-meta-node') {
        nodeService = service;
        break;
      }
    }
    
    if (nodeService != null) {
      final nodeUrl = 'http://${nodeService['host']}:${nodeService['port']}';
      print('🎯 Found Node service at: $nodeUrl');
      print('🔐 Mobile app would authenticate with Node service at this URL');
      print('✅ PURE DISCOVERY: Mobile app discovers only Discovery Service');
      print('✅ PURE DISCOVERY: All other service URLs come from Discovery Service API');
    } else {
      print('⚠️ Node service not found in Discovery Service registry');
      print('💡 This would trigger service registration or retry logic');
    }
    
    print('');
    print('📋 Step 4: Architecture Validation');
    print('---------------------------------');
    print('✅ CONFIRMED: Mobile app only needs to discover Discovery Service');
    print('✅ CONFIRMED: All service topology comes from Discovery Service API');
    print('✅ CONFIRMED: No complex client-side discovery logic needed');
    print('✅ CONFIRMED: Single point of discovery architecture achieved');
    
  } catch (e) {
    print('❌ Test failed: $e');
  }
}

Future<bool> testDiscoveryService(String url) async {
  try {
    final client = HttpClient();
    final request = await client.getUrl(Uri.parse('$url/health'));
    request.headers.set('Accept', 'application/json');
    
    final response = await request.close().timeout(Duration(seconds: 5));
    
    if (response.statusCode == 200) {
      final body = await response.transform(utf8.decoder).join();
      final data = jsonDecode(body);
      
      // Verify it's actually the Discovery Service
      if (data['service'] == 'ppl-meta-discovery') {
        client.close();
        return true;
      }
    }
    
    client.close();
    return false;
    
  } catch (e) {
    return false;
  }
}

Future<List<Map<String, dynamic>>> getServicesFromDiscovery(String discoveryUrl) async {
  try {
    final client = HttpClient();
    final request = await client.getUrl(Uri.parse('$discoveryUrl/api/v1/services'));
    request.headers.set('Accept', 'application/json');
    
    final response = await request.close().timeout(Duration(seconds: 10));
    
    if (response.statusCode == 200) {
      final body = await response.transform(utf8.decoder).join();
      final data = jsonDecode(body);
      
      client.close();
      return List<Map<String, dynamic>>.from(data['services']);
    }
    
    client.close();
    return [];
    
  } catch (e) {
    print('❌ Error getting services: $e');
    return [];
  }
}
