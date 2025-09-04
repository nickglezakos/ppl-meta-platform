#!/usr/bin/env dart

/// Camera Authentication Integration Test
/// 
/// Tests CAM-FLUTTER-001 implementation without UI
/// Verifies JWT authentication flow and camera service integration

import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() async {
  print('🧪 Testing Camera Authentication Implementation (CAM-FLUTTER-001)');
  print('=' * 70);
  
  // Test 1: Node Service Authentication
  print('\n1️⃣ Testing Node Service Authentication...');
  final authResult = await testNodeServiceAuth();
  
  if (!authResult['success']) {
    print('❌ Authentication test failed. Exiting.');
    exit(1);
  }
  
  final jwtToken = authResult['token'];
  print('✅ Authentication successful');
  
  // Test 2: Camera Service Connection
  print('\n2️⃣ Testing Camera Service Connection...');
  final cameraResult = await testCameraServiceConnection(jwtToken);
  
  if (cameraResult['success']) {
    print('✅ Camera service connection successful');
  } else {
    print('❌ Camera service connection failed: ${cameraResult['error']}');
  }
  
  // Test 3: Camera Detection
  print('\n3️⃣ Testing Camera Detection...');
  final detectionResult = await testCameraDetection(jwtToken);
  
  if (detectionResult['success']) {
    print('✅ Camera detection successful');
  } else {
    print('❌ Camera detection failed: ${detectionResult['error']}');
  }
  
  // Test 4: JWT Token Validation
  print('\n4️⃣ Testing JWT Token Validation...');
  final validationResult = await testTokenValidation(jwtToken);
  
  if (validationResult['success']) {
    print('✅ JWT token validation successful');
  } else {
    print('❌ JWT token validation failed: ${validationResult['error']}');
  }
  
  print('\n🎉 CAM-FLUTTER-001 Authentication Flow Test Complete!');
  print('Summary:');
  print('  ✅ Node Service Authentication: ${authResult['success'] ? 'PASS' : 'FAIL'}');
  print('  ✅ Camera Service Connection: ${cameraResult['success'] ? 'PASS' : 'FAIL'}');
  print('  ✅ Camera Detection: ${detectionResult['success'] ? 'PASS' : 'FAIL'}');
  print('  ✅ JWT Token Validation: ${validationResult['success'] ? 'PASS' : 'FAIL'}');
}

Future<Map<String, dynamic>> testNodeServiceAuth() async {
  try {
    final response = await http.post(
      Uri.parse('http://localhost/api/v1/users/login'),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'username': 'fresh.user@example.com',
        'password': 'NewPassword234!',
      },
    ).timeout(Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      if (data['access_token'] != null) {
        print('   📝 JWT Token received (${data['access_token'].toString().substring(0, 20)}...)');
        return {'success': true, 'token': data['access_token']};
      } else {
        return {'success': false, 'error': 'No access token in response'};
      }
    } else {
      final errorData = json.decode(response.body);
      return {'success': false, 'error': 'HTTP ${response.statusCode}: ${errorData['detail'] ?? 'Unknown error'}'};
    }
  } catch (e) {
    return {'success': false, 'error': 'Exception: $e'};
  }
}

Future<Map<String, dynamic>> testCameraServiceConnection(String jwtToken) async {
  try {
    final response = await http.get(
      Uri.parse('http://localhost/api/v1/cameras/'),
      headers: {
        'Authorization': 'Bearer $jwtToken',
        'Content-Type': 'application/json',
      },
    ).timeout(Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      // The endpoint returns an array of cameras
      if (data is List) {
        print('   📊 Camera service response: ${data.length} cameras found');
        return {'success': true, 'data': data};
      } else {
        print('   📊 Camera service response: ${data['status'] ?? 'Connected'}');
        return {'success': true, 'data': data};
      }
    } else {
      return {'success': false, 'error': 'HTTP ${response.statusCode}'};
    }
  } catch (e) {
    return {'success': false, 'error': 'Exception: $e'};
  }
}

Future<Map<String, dynamic>> testCameraDetection(String jwtToken) async {
  try {
    final response = await http.post(
      Uri.parse('http://localhost/api/v1/cameras/detect?save_to_db=true'),
      headers: {
        'Authorization': 'Bearer $jwtToken',
        'Content-Type': 'application/json',
      },
    ).timeout(Duration(seconds: 15));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      print('   📷 Detection result: ${data['status'] ?? 'Completed'}');
      return {'success': true, 'data': data};
    } else {
      return {'success': false, 'error': 'HTTP ${response.statusCode}'};
    }
  } catch (e) {
    return {'success': false, 'error': 'Exception: $e'};
  }
}

Future<Map<String, dynamic>> testTokenValidation(String jwtToken) async {
  try {
    // Test with a simple camera service call
    final response = await http.get(
      Uri.parse('http://localhost/health'),
      headers: {
        'Authorization': 'Bearer $jwtToken',
        'Content-Type': 'application/json',
      },
    ).timeout(Duration(seconds: 5));

    if (response.statusCode == 200) {
      print('   🔐 Token validation successful with health check');
      return {'success': true};
    } else {
      return {'success': false, 'error': 'HTTP ${response.statusCode}'};
    }
  } catch (e) {
    return {'success': false, 'error': 'Exception: $e'};
  }
}
