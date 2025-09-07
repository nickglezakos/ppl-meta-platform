#!/usr/bin/env dart

/// Test the actual mobile camera streaming integration with the current logs

import 'dart:convert';

// Simulate the actual camera data from the backend based on logs
final actualCameraData = {
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

// Frontend Camera model logic (exact copy from camera.dart)
enum CameraType {
  ip,
  usb,
  rtsp,
  mjpeg,
  mobile,
  virtual;
}

class Camera {
  final String id;
  final String deviceId;
  final String name;
  final String? manufacturer;
  final String? model;
  final String? resolution;
  final String status;
  final bool isActive;
  final DateTime? lastSeen;
  final String? streamUrl;
  final CameraType type;
  final Map<String, dynamic>? metadata;

  const Camera({
    required this.id,
    required this.deviceId,
    required this.name,
    this.manufacturer,
    this.model,
    this.resolution,
    required this.status,
    this.isActive = false,
    this.lastSeen,
    this.streamUrl,
    this.type = CameraType.usb,
    this.metadata,
  });

  factory Camera.fromJson(Map<String, dynamic> json) {
    // Extract connection string and other metadata for mobile camera detection
    final connectionString = json['connection_string']?.toString();
    final cameraTypeStr = json['camera_type']?.toString() ?? json['type']?.toString();
    
    // Build metadata including connection info
    final metadata = Map<String, dynamic>.from(json['metadata'] as Map<String, dynamic>? ?? {});
    if (connectionString != null) {
      metadata['connection_string'] = connectionString;
    }
    if (json['ip_address'] != null) {
      metadata['ip_address'] = json['ip_address'];
    }
    if (json['port'] != null) {
      metadata['port'] = json['port'];
    }
    
    // Determine camera type with mobile detection
    CameraType cameraType;
    if (cameraTypeStr?.toLowerCase() == 'mobile' || connectionString?.startsWith('mobile://') == true) {
      cameraType = CameraType.mobile;
    } else {
      cameraType = CameraType.values.firstWhere(
        (t) => t.name.toLowerCase() == cameraTypeStr?.toLowerCase(),
        orElse: () => CameraType.usb,
      );
    }
    
    return Camera(
      id: json['id']?.toString() ?? '',
      deviceId: json['device_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      manufacturer: json['manufacturer']?.toString(),
      model: json['model']?.toString(),
      resolution: json['resolution']?.toString(),
      status: json['status']?.toString() ?? 'offline',
      isActive: json['is_active'] == true || json['isActive'] == true,
      lastSeen: json['last_seen'] != null 
          ? DateTime.tryParse(json['last_seen'].toString())
          : null,
      streamUrl: json['stream_url']?.toString(),
      type: cameraType,
      metadata: metadata,
    );
  }

  /// Check if this is a mobile camera
  bool get isMobileCamera => type == CameraType.mobile || 
      (metadata != null && metadata!['connection_string']?.toString().startsWith('mobile://') == true);

  /// Get the direct MJPEG stream URL for mobile cameras
  /// Returns null if this is not a mobile camera or if connection info is not available
  String? get directStreamUrl {
    if (!isMobileCamera) return null;
    
    // Try to extract from metadata connection_string first
    final connectionString = metadata?['connection_string']?.toString();
    if (connectionString != null && connectionString.startsWith('mobile://')) {
      // Parse mobile://ip:port format
      final address = connectionString.substring(9); // Remove 'mobile://'
      return 'http://$address/stream';
    }
    
    // Fallback: try to construct from metadata ip_address and port
    final ip = metadata?['ip_address']?.toString();
    final port = metadata?['port']?.toString();
    if (ip != null && port != null) {
      return 'http://$ip:$port/stream';
    }
    
    return null;
  }
}

// Simulate the streaming URL preparation logic
Future<String?> prepareAuthenticatedUrl(Camera? camera, String cameraId) async {
  try {
    print('📱 prepareAuthenticatedUrl called for camera: $cameraId');
    print('📱 Camera data: ${camera?.deviceId}');
    
    // Check if this is a mobile camera
    if (camera != null && camera.isMobileCamera) {
      final directUrl = camera.directStreamUrl;
      if (directUrl != null) {
        print('✅ Using direct MJPEG stream for mobile camera ${camera.name}: $directUrl');
        return directUrl;
      } else {
        print('❌ Mobile camera detected but no direct stream URL available');
        return null;
      }
    }
    
    // For non-mobile cameras, use the traditional backend approach
    print('📡 Creating backend streaming session for non-mobile camera...');
    // This is where the backend session would be created
    return 'http://localhost:8080/api/v1/streaming/$cameraId/video-session/some-session-id';
  } catch (e) {
    print('❌ Error preparing authenticated URL: $e');
    return null;
  }
}

void main() async {
  print('🧪 Mobile Camera Streaming Integration Test');
  print('=' * 50);
  print('');
  
  // Create camera from JSON (simulating backend response)
  print('1️⃣ Creating Camera from backend JSON data...');
  final camera = Camera.fromJson(actualCameraData);
  
  print('   Camera ID: ${camera.id}');
  print('   Device ID: ${camera.deviceId}');
  print('   Type: ${camera.type}');
  print('   Is Mobile: ${camera.isMobileCamera}');
  print('   Direct Stream URL: ${camera.directStreamUrl}');
  print('');
  
  // Test streaming URL preparation
  print('2️⃣ Testing streaming URL preparation...');
  final streamUrl = await prepareAuthenticatedUrl(camera, camera.id);
  print('   Result URL: $streamUrl');
  print('');
  
  // Analyze what should happen
  print('3️⃣ Analysis:');
  if (camera.isMobileCamera && camera.directStreamUrl != null) {
    if (streamUrl == camera.directStreamUrl) {
      print('   ✅ SUCCESS: Mobile camera should bypass backend');
      print('   ✅ Direct MJPEG URL will be used: $streamUrl');
      print('   ✅ No backend streaming session should be created');
    } else {
      print('   ❌ FAIL: Expected direct URL but got: $streamUrl');
    }
  } else {
    print('   📡 Non-mobile camera: backend streaming session required');
  }
  print('');
  
  // Test what happens if camera is null (loading state)
  print('4️⃣ Testing with null camera (loading state)...');
  final nullStreamUrl = await prepareAuthenticatedUrl(null, camera.id);
  print('   Result with null camera: $nullStreamUrl');
  if (nullStreamUrl != null && nullStreamUrl.contains('video-session')) {
    print('   ⚠️  WARNING: Null camera creates backend session - this could be the bug!');
    print('   💡 Frontend should wait for camera data before calling prepareAuthenticatedUrl');
  } else {
    print('   ✅ Null camera correctly returns null');
  }
}
