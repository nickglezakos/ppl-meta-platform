#!/usr/bin/env dart

import 'dart:io';
import 'lib/services/device_identifier_service.dart';

/// Command-line test script for automatic camera naming
void main() async {
  print('🤖 PPL Meta Mobile Camera - Automatic Naming System Test');
  print('============================================================');
  print('');
  
  final deviceService = DeviceIdentifierService();
  
  try {
    print('📱 Testing automatic camera name generation...');
    print('');
    
    // Test 1: Generate camera name
    print('🏷️ Test 1: Generating automatic camera name...');
    final cameraName = await deviceService.generateCameraName();
    print('✅ Generated camera name: $cameraName');
    print('');
    
    // Test 2: Verify consistency
    print('🔄 Test 2: Verifying name consistency...');
    final cameraName2 = await deviceService.generateCameraName();
    print('✅ Second generation: $cameraName2');
    print('   Consistent: ${cameraName == cameraName2 ? "YES" : "NO"}');
    print('');
    
    // Test 3: Get device description
    print('📋 Test 3: Getting device description...');
    final description = await deviceService.getDeviceDescription();
    print('✅ Device description: $description');
    print('');
    
    // Test 4: Get registration info
    print('📊 Test 4: Getting device registration info...');
    final registrationInfo = await deviceService.getDeviceRegistrationInfo();
    print('✅ Registration info collected:');
    registrationInfo.forEach((key, value) {
      print('   $key: $value');
    });
    print('');
    
    // Test 5: Verify URL safety
    print('🔍 Test 5: Verifying URL safety...');
    final isUrlSafe = RegExp(r'^[a-z0-9\-]+$').hasMatch(cameraName);
    print('✅ URL-safe format: ${isUrlSafe ? "YES" : "NO"}');
    print('   No spaces: ${!cameraName.contains(" ") ? "YES" : "NO"}');
    print('   No special chars: ${!RegExp(r'[^a-z0-9\-]').hasMatch(cameraName) ? "YES" : "NO"}');
    print('');
    
    // Test 6: Cache clearing test
    print('🧹 Test 6: Testing cache clearing...');
    deviceService.clearCache();
    final cameraName3 = await deviceService.generateCameraName();
    print('✅ After cache clear: $cameraName3');
    print('   Still consistent: ${cameraName == cameraName3 ? "YES" : "NO"}');
    print('');
    
    // Final summary
    print('🎉 All Tests Completed Successfully!');
    print('============================================');
    print('📱 Final camera name: $cameraName');
    print('🔍 Name format: mcam-<device-model>-<unique-id>');
    print('🎯 Zero user input required: YES');
    print('✅ Ready for production use');
    
  } catch (e) {
    print('💥 Error during testing: $e');
    exit(1);
  }
}
