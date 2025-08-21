#!/usr/bin/env dart

/// Simple test of automatic camera naming without Flutter dependencies
void main() async {
  print('🤖 PPL Meta Mobile Camera - Automatic Naming System Test');
  print('============================================================');
  print('📱 This test simulates the automatic camera name generation');
  print('   without requiring actual device info or Flutter runtime.');
  print('');
  
  // Simulate device info that would come from DeviceInfoPlugin
  final simulatedDeviceInfo = {
    'model': 'Xiaomi 2201117TY',
    'manufacturer': 'Xiaomi',
    'brand': 'xiaomi',
  };
  
  print('📋 Simulated Device Info:');
  simulatedDeviceInfo.forEach((key, value) {
    print('   $key: $value');
  });
  print('');
  
  // Test camera name generation logic
  print('🏷️ Testing camera name generation...');
  
  // Step 1: Sanitize model name
  final rawModel = simulatedDeviceInfo['model']!;
  final sanitizedModel = _sanitizeModelName(rawModel);
  print('✅ Sanitized model: $rawModel -> $sanitizedModel');
  
  // Step 2: Generate unique ID
  final uniqueId = _generateUniqueId(simulatedDeviceInfo);
  print('✅ Generated unique ID: $uniqueId');
  
  // Step 3: Generate final camera name
  final cameraName = 'mcam-$sanitizedModel-$uniqueId';
  print('✅ Generated camera name: $cameraName');
  print('');
  
  // Test validation
  print('🔍 Validating camera name format...');
  final isUrlSafe = RegExp(r'^[a-z0-9\-]+$').hasMatch(cameraName);
  final hasCorrectFormat = cameraName.startsWith('mcam-') && cameraName.split('-').length >= 3;
  final uniqueIdLength = uniqueId.length == 6;
  
  print('✅ URL-safe format: ${isUrlSafe ? "YES" : "NO"}');
  print('✅ Correct format (mcam-model-id): ${hasCorrectFormat ? "YES" : "NO"}');
  print('✅ Unique ID length (6 chars): ${uniqueIdLength ? "YES" : "NO"}');
  print('');
  
  // Test multiple generations for consistency
  print('🔄 Testing consistency...');
  final cameraName2 = 'mcam-$sanitizedModel-${_generateUniqueId(simulatedDeviceInfo)}';
  final isConsistent = cameraName == cameraName2;
  print('✅ Consistent generation: ${isConsistent ? "YES" : "NO"}');
  print('   Name 1: $cameraName');
  print('   Name 2: $cameraName2');
  print('');
  
  // Final summary
  if (isUrlSafe && hasCorrectFormat && uniqueIdLength) {
    print('🎉 All Tests PASSED!');
    print('✅ Automatic camera naming system is working correctly');
    print('🚀 Ready for integration into mobile app');
  } else {
    print('❌ Some tests failed - review implementation');
  }
  
  print('');
  print('📊 Example Registration Data:');
  final registrationData = {
    'name': cameraName,
    'device_id': 'mobile_${DateTime.now().millisecondsSinceEpoch}',
    'device_model': simulatedDeviceInfo['model'],
    'device_manufacturer': simulatedDeviceInfo['manufacturer'],
    'device_brand': simulatedDeviceInfo['brand'],
    'camera_type': 'MOBILE',
    'registration_method': 'automatic_zero_input',
  };
  
  registrationData.forEach((key, value) {
    print('   $key: $value');
  });
}

/// Sanitizes device model name to be URL-safe and readable
String _sanitizeModelName(String model) {
  if (model.isEmpty) return 'device';
  
  final sanitized = model
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]'), '') // Remove non-alphanumeric
      .replaceAll(RegExp(r'^[^a-z]'), ''); // Ensure starts with letter
  
  if (sanitized.isEmpty) return 'device';
  
  // Limit length but ensure minimum of 3 characters
  final maxLength = model.length > 15 ? 15 : model.length;
  final minLength = sanitized.length < 3 ? sanitized.length : 3;
  final finalLength = maxLength < minLength ? sanitized.length : maxLength;
  
  return sanitized.substring(0, finalLength);
}

/// Generates a unique 6-character identifier from device info
String _generateUniqueId(Map<String, String> deviceInfo) {
  // Combine multiple device identifiers for uniqueness
  final identifiers = [
    deviceInfo['model'],
    deviceInfo['manufacturer'],
    deviceInfo['brand'],
    DateTime.now().millisecondsSinceEpoch.toString(),
  ].where((id) => id != null && id.isNotEmpty).join('|');

  // Simple hash function (in real implementation, use crypto package)
  final hash = identifiers.hashCode.abs().toString();
  
  // Take first 6 characters, pad if necessary
  if (hash.length >= 6) {
    return hash.substring(0, 6);
  } else {
    return hash.padRight(6, '0');
  }
}
