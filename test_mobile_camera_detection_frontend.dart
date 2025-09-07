#!/usr/bin/env dart

/// Debug script to test mobile camera detection in frontend Camera model

import 'dart:convert';

// Test data that should match what we see in the logs
final testMobileCameraData = {
  'id': 123,
  'device_id': 'mobile_TKQ1.221114.001',
  'name': 'Mobile Camera',
  'camera_type': 'mobile',
  'status': 'active',
  'connection_string': 'mobile://10.228.129.0:8554',
  'ip_address': '10.228.129.0',
  'port': 8554,
  'metadata': {
    'connection_string': 'mobile://10.228.129.0:8554',
    'ip_address': '10.228.129.0',
    'port': 8554,
    'camera_type': 'mobile'
  }
};

// Simulate the mobile camera detection logic from frontend
String _parseCameraType(Map<String, dynamic> json) {
  final typeStr = json['camera_type']?.toString().toLowerCase() ?? 'ip';
  final connectionString = json['connection_string']?.toString() ?? '';
  
  // Check for mobile camera by type or connection string
  if (typeStr == 'mobile' || connectionString.startsWith('mobile://')) {
    return 'mobile';
  }
  
  return typeStr;
}

bool _isMobileCamera(Map<String, dynamic> json) {
  final type = _parseCameraType(json);
  return type == 'mobile';
}

String? _getDirectStreamUrl(Map<String, dynamic> json) {
  if (!_isMobileCamera(json)) return null;
  
  // Try to extract from metadata connection_string first
  final metadata = json['metadata'] as Map<String, dynamic>?;
  final connectionString = metadata?['connection_string']?.toString() ?? json['connection_string']?.toString();
  
  if (connectionString != null && connectionString.startsWith('mobile://')) {
    // Parse mobile://ip:port format
    final address = connectionString.substring(9); // Remove 'mobile://'
    return 'http://$address/stream';
  }
  
  // Fallback: try to construct from metadata ip_address and port
  final ip = metadata?['ip_address']?.toString() ?? json['ip_address']?.toString();
  final port = metadata?['port']?.toString() ?? json['port']?.toString();
  if (ip != null && port != null) {
    return 'http://$ip:$port/stream';
  }
  
  return null;
}

void main() {
  print('🔍 Mobile Camera Detection Test');
  print('=' * 40);
  print('');
  
  print('Test Data:');
  print('  Device ID: ${testMobileCameraData['device_id']}');
  print('  Camera Type: ${testMobileCameraData['camera_type']}');
  print('  Connection String: ${testMobileCameraData['connection_string']}');
  print('  IP Address: ${testMobileCameraData['ip_address']}');
  print('  Port: ${testMobileCameraData['port']}');
  print('');
  
  // Test detection
  final parsedType = _parseCameraType(testMobileCameraData);
  final isMobile = _isMobileCamera(testMobileCameraData);
  final directUrl = _getDirectStreamUrl(testMobileCameraData);
  
  print('Detection Results:');
  print('  Parsed Type: $parsedType');
  print('  Is Mobile: $isMobile');
  print('  Direct Stream URL: $directUrl');
  print('');
  
  // Test expected behavior
  print('Expected Behavior:');
  print('  Should be detected as mobile: ✅ ${isMobile ? 'PASS' : 'FAIL'}');
  print('  Should have direct URL: ✅ ${directUrl != null ? 'PASS' : 'FAIL'}');
  print('  Expected URL: http://10.228.129.0:8554/stream');
  print('  Actual URL: $directUrl');
  print('  URL Match: ✅ ${directUrl == 'http://10.228.129.0:8554/stream' ? 'PASS' : 'FAIL'}');
  print('');
  
  if (isMobile && directUrl != null) {
    print('✅ Mobile camera detection is working correctly!');
    print('📱 Frontend should use direct MJPEG streaming: $directUrl');
  } else {
    print('❌ Mobile camera detection failed!');
    print('💡 Frontend will incorrectly use backend streaming session');
  }
}
