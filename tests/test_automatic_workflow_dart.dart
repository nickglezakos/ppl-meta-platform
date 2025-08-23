#!/usr/bin/env dart

/// Test script for automatic streaming workflow
/// This simulates the Flutter app workflow using Dart HTTP client
import 'dart:convert';
import 'dart:io';

Future<void> main() async {
  print('🚀 ========================================');
  print('🚀 TESTING AUTOMATIC STREAMING WORKFLOW');
  print('🚀 ========================================');
  print('📱 Simulating Flutter app automatic workflow');
  print('🎯 Goal: Test complete auto-discovery and registration');
  print('🚀 ========================================');
  
  await testAutomaticWorkflow();
}

Future<void> testAutomaticWorkflow() async {
  final httpClient = HttpClient();
  
  try {
    // Phase 1: Auto-discovery and login
    print('\n🔐 PHASE 1: Auto-Discovery & Login');
    print('🔍 Step 1: Auto-discovering Node service...');
    
    // Simulate device IP detection (we know it's localhost for testing)
    final deviceIP = '192.168.21.66'; // Simulated device IP
    final networkPrefix = '192.168.21.';
    print('📱 Detected device IP: $deviceIP');
    print('🌐 Network prefix: $networkPrefix');
    
    // Try Node service discovery sequence (.253, .1, .254)
    String? nodeURL;
    final candidateIPs = ['${networkPrefix}253', '${networkPrefix}1', '${networkPrefix}254', 'localhost']; // Added localhost for testing
    
    for (final ip in candidateIPs) {
      final testURL = 'http://$ip:8001';
      print('🔍 Testing Node service at: $testURL');
      
      try {
        final request = await httpClient.getUrl(Uri.parse('$testURL/api/v1/health'));
        request.headers.set('Connection', 'close');
        final response = await request.close();
        
        if (response.statusCode == 200) {
          nodeURL = testURL;
          print('✅ Found Node service at: $nodeURL');
          break;
        }
      } catch (e) {
        print('❌ No service at $testURL');
      }
    }
    
    if (nodeURL == null) {
      throw Exception('Node service not found on network');
    }
    
    // Login with auto-discovered Node service
    print('🔐 Step 2: Logging in to discovered Node service...');
    final loginRequest = await httpClient.postUrl(Uri.parse('$nodeURL/api/v1/users/login'));
    loginRequest.headers.set('Content-Type', 'application/x-www-form-urlencoded');
    loginRequest.headers.set('Connection', 'close');
    
    const username = 'fresh.user@example.com';
    const password = 'NewPassword234!';
    const loginBody = 'username=$username&password=$password';
    loginRequest.write(loginBody);
    
    final loginResponse = await loginRequest.close();
    final loginData = await loginResponse.transform(utf8.decoder).join();
    
    if (loginResponse.statusCode != 200) {
      throw Exception('Login failed: ${loginResponse.statusCode} - $loginData');
    }
    
    final loginJson = jsonDecode(loginData);
    final jwtToken = loginJson['token'];
    print('✅ Login successful! JWT token obtained.');
    
    // Phase 2: Dynamic service discovery
    print('\n🔍 PHASE 2: Dynamic Service Discovery');
    print('🔍 Step 3: Discovering platform services...');
    
    final servicesRequest = await httpClient.getUrl(Uri.parse('$nodeURL/api/v1/users/platform/services'));
    servicesRequest.headers.set('Authorization', 'Bearer $jwtToken');
    servicesRequest.headers.set('Connection', 'close');
    
    final servicesResponse = await servicesRequest.close();
    final servicesData = await servicesResponse.transform(utf8.decoder).join();
    
    if (servicesResponse.statusCode != 200) {
      throw Exception('Platform services discovery failed: ${servicesResponse.statusCode} - $servicesData');
    }
    
    final servicesJson = jsonDecode(servicesData);
    print('✅ Platform services discovered:');
    print('📹 Camera Service: ${servicesJson['camera_service']?['endpoint'] ?? 'Not found'}');
    print('🎬 Media Service: ${servicesJson['media_service']?['endpoint'] ?? 'Not found'}');
    print('🌐 Gateway Service: ${servicesJson['gateway_service']?['endpoint'] ?? 'Not found'}');
    print('🎼 Orchestrator Service: ${servicesJson['orchestrator_service']?['endpoint'] ?? 'Not found'}');
    
    final cameraServiceURL = servicesJson['camera_service']?['endpoint'];
    if (cameraServiceURL == null) {
      throw Exception('Camera service endpoint not found');
    }
    
    // Phase 3: Automatic camera registration
    print('\n📱 PHASE 3: Automatic Camera Registration');
    print('📱 Step 4: Auto-registering mobile camera...');
    
    final cameraName = 'Test Mobile Camera (Dart)';
    final registrationData = {
      'name': cameraName,
      'ip_address': deviceIP,
      'port': 8554,
      'device_model': 'Test Device Model',
      'device_manufacturer': 'PPL Meta Mobile (Dart Test)',
      'app_version': '2.13.1-test',
      'resolution_width': 1920,
      'resolution_height': 1080,
      'max_fps': 30,
      'supports_audio': false,
    };
    
    final registrationRequest = await httpClient.postUrl(Uri.parse('$cameraServiceURL/api/v1/cameras/mobile'));
    registrationRequest.headers.set('Authorization', 'Bearer $jwtToken');
    registrationRequest.headers.set('Content-Type', 'application/json');
    registrationRequest.headers.set('Connection', 'close');
    registrationRequest.write(jsonEncode(registrationData));
    
    final registrationResponse = await registrationRequest.close();
    final registrationResponseData = await registrationResponse.transform(utf8.decoder).join();
    
    if (registrationResponse.statusCode == 200 || registrationResponse.statusCode == 201) {
      final registrationJson = jsonDecode(registrationResponseData);
      print('✅ Camera registered successfully!');
      print('📊 Camera ID: ${registrationJson['camera']?['id'] ?? 'Unknown'}');
      print('🆔 Device ID: ${registrationJson['camera']?['device_id'] ?? 'Unknown'}');
      print('📡 Status: ${registrationJson['camera']?['status'] ?? 'Unknown'}');
    } else {
      print('⚠️ Camera registration response: ${registrationResponse.statusCode}');
      print('📄 Response: $registrationResponseData');
    }
    
    // Workflow completion
    print('\n🎉 ========================================');
    print('🎉 AUTOMATIC WORKFLOW COMPLETED!');
    print('🎉 ========================================');
    print('📱 Camera "$cameraName" workflow executed');
    print('🔗 Node Service: $nodeURL');
    print('📹 Camera Service: $cameraServiceURL');
    print('🎉 ========================================');
    
  } catch (e) {
    print('\n❌ ========================================');
    print('❌ AUTOMATIC WORKFLOW FAILED');
    print('❌ ========================================');
    print('💥 Error: $e');
    print('❌ ========================================');
  } finally {
    httpClient.close();
  }
}
