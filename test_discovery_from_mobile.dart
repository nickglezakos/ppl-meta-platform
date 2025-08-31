#!/usr/bin/env dart

/// Test Discovery Service connectivity from mobile perspective

import 'dart:convert';
import 'dart:io';

Future<void> main() async {
  print('🔍 Testing Discovery Service from mobile perspective...');
  
  // Get machine IP
  final String? machineIP = await getMachineIP();
  if (machineIP == null) {
    print('❌ Could not determine machine IP');
    return;
  }
  
  print('📱 Machine IP: $machineIP');
  
  // Test Discovery Service URLs that mobile app would try
  final testUrls = [
    'http://$machineIP/discovery/api/v1/services',  // Via nginx
    'http://$machineIP:8006/api/v1/services',       // Direct port
  ];
  
  for (final url in testUrls) {
    await testDiscoveryUrl(url);
  }
}

Future<String?> getMachineIP() async {
  try {
    final result = await Process.run('ifconfig', []);
    final lines = result.stdout.toString().split('\n');
    
    for (final line in lines) {
      if (line.contains('inet ') && line.contains('broadcast')) {
        final parts = line.trim().split(' ');
        for (int i = 0; i < parts.length; i++) {
          if (parts[i] == 'inet' && i + 1 < parts.length) {
            return parts[i + 1];
          }
        }
      }
    }
  } catch (e) {
    print('⚠️ Failed to get machine IP: $e');
  }
  return null;
}

Future<void> testDiscoveryUrl(String url) async {
  print('\n🌐 Testing: $url');
  
  try {
    final client = HttpClient();
    client.connectionTimeout = Duration(seconds: 5);
    
    final request = await client.getUrl(Uri.parse(url));
    request.headers.add('Accept', 'application/json');
    
    final response = await request.close();
    
    if (response.statusCode == 200) {
      final responseBody = await response.transform(utf8.decoder).join();
      final data = json.decode(responseBody);
      
      print('✅ SUCCESS (${response.statusCode})');
      if (data['services'] != null) {
        print('   📋 Found ${data['services'].length} services');
        for (final service in data['services']) {
          print('   - ${service['name']} (${service['service_type']}) at ${service['host']}:${service['port']}');
        }
      }
    } else {
      print('❌ FAILED (${response.statusCode})');
    }
    
    client.close();
  } catch (e) {
    print('❌ ERROR: $e');
  }
}
