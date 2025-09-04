import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../lib/core/models/camera.dart';
import '../lib/core/models/rtsp_camera.dart';
import '../lib/core/services/multi_camera_service.dart';

/// Demo and test for CAM-FLUTTER-006 Multi-Camera Management
void main() {
  group('CAM-FLUTTER-006 Multi-Camera System Tests', () {
    late MultiCameraService cameraService;
    
    setUp(() {
      cameraService = MultiCameraService();
    });

    test('Should create RTSP camera configuration', () async {
      // Example with your RTSP camera setup
      final camera = await cameraService.addRTSPCamera(
        name: 'Living Room Camera',
        host: '192.168.1.100', // Replace with your camera's IP
        port: 554,
        username: 'admin', // Replace with your username
        password: 'your_password', // Replace with your password
        streamPath: '/stream', // Check your camera documentation
        transport: RTSPTransport.tcp,
        profile: RTSPProfile.main,
      );

      expect(camera.name, equals('Living Room Camera'));
      expect(camera.type, equals(CameraType.rtsp));
      expect(camera.deviceId, contains('rtsp_192_168_1_100'));
    });

    test('Should generate correct RTSP URL', () {
      final rtspCamera = RTSPCamera(
        id: 'test_cam',
        name: 'Test Camera',
        host: '192.168.1.100',
        port: 554,
        username: 'admin',
        password: 'password123',
        streamPath: '/live/main',
        transport: RTSPTransport.tcp,
        profile: RTSPProfile.main,
      );

      final expectedUrl = 'rtsp://admin:password123@192.168.1.100:554/live/main';
      expect(rtspCamera.rtspUrl, equals(expectedUrl));
    });

    test('Should handle multiple camera types', () async {
      // Add RTSP camera
      final rtspCamera = await cameraService.addRTSPCamera(
        name: 'Network Camera 1',
        host: '192.168.1.100',
        username: 'admin',
        password: 'pass123',
      );

      // Get all cameras (would include USB cameras if detected)
      final allCameras = await cameraService.getAllCameras();
      
      // Should have at least the RTSP camera we added
      expect(allCameras.isNotEmpty, isTrue);
      
      final rtspCameras = allCameras.where((c) => c.type == CameraType.rtsp).toList();
      expect(rtspCameras.length, equals(1));
      expect(rtspCameras.first.name, equals('Network Camera 1'));
    });

    test('Should validate RTSP camera configurations', () {
      // Test with default port
      final camera1 = RTSPCamera(
        id: '1',
        name: 'Camera 1',
        host: '192.168.1.100',
        username: 'admin',
        password: 'pass',
      );
      expect(camera1.port, equals(554));
      expect(camera1.streamPath, equals('/stream'));

      // Test with custom settings
      final camera2 = RTSPCamera(
        id: '2',
        name: 'Camera 2',
        host: '10.0.0.50',
        port: 8554,
        username: 'user',
        password: 'secret',
        streamPath: '/live/main',
        transport: RTSPTransport.udp,
        profile: RTSPProfile.sub,
      );
      
      expect(camera2.port, equals(8554));
      expect(camera2.streamPath, equals('/live/main'));
      expect(camera2.transport, equals(RTSPTransport.udp));
      expect(camera2.profile, equals(RTSPProfile.sub));
    });

    test('Should convert RTSP camera to Camera model', () {
      final rtspCamera = RTSPCamera(
        id: 'rtsp_001',
        name: 'Front Door Camera',
        host: '192.168.1.200',
        port: 554,
        username: 'viewer',
        password: 'view123',
        streamPath: '/camera1',
        isActive: true,
      );

      final camera = rtspCamera.toCamera();

      expect(camera.id, equals('rtsp_001'));
      expect(camera.name, equals('Front Door Camera'));
      expect(camera.type, equals(CameraType.rtsp));
      expect(camera.isActive, isTrue);
      expect(camera.manufacturer, equals('Network Camera'));
      expect(camera.model, equals('RTSP'));
      expect(camera.metadata?['type'], equals('rtsp'));
      expect(camera.metadata?['host'], equals('192.168.1.200'));
      expect(camera.metadata?['port'], equals(554));
    });

    tearDown(() {
      cameraService.dispose();
    });
  });

  group('Camera Type Tests', () {
    test('Should handle all camera types', () {
      for (final type in CameraType.values) {
        final camera = Camera(
          id: 'test_${type.name}',
          deviceId: 'device_${type.name}',
          name: 'Test ${type.displayName}',
          status: 'connected',
          type: type,
        );

        expect(camera.type, equals(type));
        expect(camera.name, contains(type.displayName));
      }
    });

    test('Should serialize camera types correctly', () {
      final camera = Camera(
        id: 'test_rtsp',
        deviceId: 'rtsp_cam_001',
        name: 'RTSP Test Camera',
        status: 'connected',
        type: CameraType.rtsp,
      );

      final json = camera.toJson();
      expect(json['type'], equals('rtsp'));

      final restored = Camera.fromJson(json);
      expect(restored.type, equals(CameraType.rtsp));
    });
  });
}

/// Example integration demo for your specific RTSP camera
class RTSPCameraDemo {
  static void demonstrateSetup() {
    print('🎥 CAM-FLUTTER-006 RTSP Camera Demo');
    print('=====================================');
    
    // Example configuration for a typical RTSP camera
    final exampleCamera = RTSPCamera(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: 'Your RTSP Camera', // Replace with your camera name
      host: '192.168.1.XXX', // Replace with your camera's IP
      port: 554, // Standard RTSP port
      username: 'your_username', // Replace with your username
      password: 'your_password', // Replace with your password
      streamPath: '/stream', // Common paths: /stream, /live/main, /h264
      transport: RTSPTransport.tcp, // TCP is more reliable
      profile: RTSPProfile.main, // Main profile for best quality
    );

    print('📋 Your camera configuration:');
    print('   Name: ${exampleCamera.name}');
    print('   Host: ${exampleCamera.host}:${exampleCamera.port}');
    print('   Stream Path: ${exampleCamera.streamPath}');
    print('   Transport: ${exampleCamera.transport.displayName}');
    print('   Profile: ${exampleCamera.profile.displayName}');
    print('   RTSP URL: ${exampleCamera.rtspUrl}');
    print('   Device ID: ${exampleCamera.deviceId}');
    
    print('\n🚀 To add your camera:');
    print('1. Open the PPL Meta app');
    print('2. Navigate to Cameras');
    print('3. Click "Add RTSP Camera"');
    print('4. Fill in your camera details');
    print('5. The system will test the connection');
    print('6. Start streaming and take snapshots!');
    
    print('\n💡 Common RTSP stream paths:');
    print('   Hikvision: /h264/ch1/main/av_stream');
    print('   Dahua: /cam/realmonitor?channel=1&subtype=0');
    print('   Generic: /stream, /live/main, /video1');
    print('   
: /live, /stream1');
    
    print('\n🔧 Troubleshooting:');
    print('   - Ensure camera is on same network');
    print('   - Check firewall settings (port 554)');
    print('   - Verify username/password');
    print('   - Try different transport (TCP/UDP)');
    print('   - Check camera manual for stream path');
  }
}

/// Example provider usage for testing
class MultiCameraProviderDemo {
  static void demonstrateProviders() {
    print('\n🔄 Riverpod Provider Usage:');
    print('============================');
    
    print('''
// In your Flutter widget:
class CameraManagementWidget extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch all cameras
    final allCameras = ref.watch(allCamerasProvider);
    
    // Watch just RTSP cameras
    final rtspCameras = ref.watch(rtspCamerasProvider);
    
    // Get camera counts
    final counts = ref.watch(cameraCountProvider);
    
    // Get camera actions
    final actions = ref.read(cameraActionsProvider);
    
    return allCameras.when(
      loading: () => CircularProgressIndicator(),
      error: (error, stack) => Text('Error: \$error'),
      data: (cameras) => ListView.builder(
        itemCount: cameras.length,
        itemBuilder: (context, index) {
          return CameraCard(
            camera: cameras[index],
            showTypeIndicator: true,
          );
        },
      ),
    );
  }
  
  // Add RTSP camera
  Future<void> addMyCamera(WidgetRef ref) async {
    final actions = ref.read(cameraActionsProvider);
    
    try {
      final camera = await actions.addRTSPCamera(
        name: 'My Security Camera',
        host: '192.168.1.100',
        username: 'admin',
        password: 'mypassword',
      );
      
      print('Camera added: \${camera.name}');
    } catch (e) {
      print('Error adding camera: \$e');
    }
  }
}
''');
  }
}
