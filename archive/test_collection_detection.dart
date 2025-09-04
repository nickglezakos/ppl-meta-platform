import 'package:dio/dio.dart';
import 'dart:convert';

// Simple test to verify collection detection
void main() async {
  final dio = Dio(BaseOptions(
    baseUrl: 'http://localhost:8000/api/v1',
    headers: {
      'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU1MDc3Njc2fQ._B2wBdzoUsMhE3o708OoXJIzuppHDJI1sfRo2AD135s',
    },
  ));
  
  try {
    print('🔍 Testing collection detection for USB Camera 0...');
    
    // Get all collections
    final response = await dio.get('/collections/', queryParameters: {
      'user_id': '7',
    });
    
    if (response.statusCode == 200) {
      final collections = response.data as List;
      print('📋 Found ${collections.length} collections');
      
      // Look for camera collections
      for (final collection in collections) {
        print('   • ${collection['name']} (${collection['uuid']})');
        if (collection['description'] != null) {
          print('     Description: ${collection['description']}');
        }
      }
      
      // Check for USB Camera 0 Collection specifically
      final usbCameraCollection = collections.firstWhere(
        (c) => c['name'] == 'USB Camera 0 Collection',
        orElse: () => null,
      );
      
      if (usbCameraCollection != null) {
        print('✅ Found USB Camera 0 Collection!');
        print('   UUID: ${usbCameraCollection['uuid']}');
        print('   Description: ${usbCameraCollection['description']}');
        print('');
        print('🔗 This should be mapped to camera: usb_camera_0');
      } else {
        print('❌ USB Camera 0 Collection not found');
      }
    }
  } catch (e) {
    print('❌ Error: $e');
  }
}
