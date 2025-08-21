import 'package:flutter_test/flutter_test.dart';
import 'package:ppl_meta_mobile_camera/services/device_identifier_service.dart';

void main() {
  group('DeviceIdentifierService Tests', () {
    late DeviceIdentifierService service;

    setUp(() {
      service = DeviceIdentifierService();
      service.clearCache(); // Ensure clean state for each test
    });

    test('generateCameraName should create consistent name format', () async {
      final cameraName = await service.generateCameraName();
      
      // Verify format: mcam-<device-model>-<unique-id>
      expect(cameraName, startsWith('mcam-'));
      
      final parts = cameraName.split('-');
      expect(parts.length, greaterThanOrEqualTo(3)); // mcam, model, id (and potentially more)
      expect(parts[0], equals('mcam'));
      
      // Verify unique ID part is 6 characters
      final uniqueId = parts.last;
      expect(uniqueId.length, equals(6));
      expect(RegExp(r'^[a-z0-9]+$').hasMatch(uniqueId), isTrue);
      
      print('✅ Generated camera name: $cameraName');
    });

    test('generateCameraName should be consistent on multiple calls', () async {
      final name1 = await service.generateCameraName();
      final name2 = await service.generateCameraName();
      
      expect(name1, equals(name2));
      print('✅ Consistent naming: $name1');
    });

    test('getDeviceRegistrationInfo should return device details', () async {
      final info = await service.getDeviceRegistrationInfo();
      
      expect(info, isA<Map<String, dynamic>>());
      expect(info.containsKey('device_model'), isTrue);
      expect(info.containsKey('device_manufacturer'), isTrue);
      expect(info.containsKey('device_brand'), isTrue);
      
      print('✅ Device registration info:');
      info.forEach((key, value) {
        print('   $key: $value');
      });
    });

    test('getDeviceDescription should return readable description', () async {
      final description = await service.getDeviceDescription();
      
      expect(description, isNotEmpty);
      expect(description, isNot(equals('Unknown Mobile Device')));
      
      print('✅ Device description: $description');
    });

    test('clearCache should allow name regeneration', () async {
      final name1 = await service.generateCameraName();
      service.clearCache();
      
      // Note: The name should still be the same since it's based on device info
      // This test mainly verifies the cache clearing mechanism works
      final name2 = await service.generateCameraName();
      expect(name2, isNotEmpty);
      expect(name2, startsWith('mcam-'));
      
      print('✅ Cache clearing works, names: $name1, $name2');
    });

    test('camera name should be URL-safe', () async {
      final cameraName = await service.generateCameraName();
      
      // Verify no special characters that could cause URL issues
      expect(RegExp(r'^[a-z0-9\-]+$').hasMatch(cameraName), isTrue);
      expect(cameraName.contains(' '), isFalse);
      expect(cameraName.contains('_'), isFalse);
      expect(cameraName.contains('.'), isFalse);
      
      print('✅ URL-safe camera name: $cameraName');
    });
  });

  group('Integration Tests', () {
    test('Complete automatic workflow simulation', () async {
      final service = DeviceIdentifierService();
      
      print('\n🚀 Simulating complete automatic camera registration workflow...');
      
      // Step 1: Generate camera name
      print('🏷️ Step 1: Generating automatic camera name...');
      final cameraName = await service.generateCameraName();
      print('✅ Generated: $cameraName');
      
      // Step 2: Get device info
      print('📱 Step 2: Getting device registration info...');
      final deviceInfo = await service.getDeviceRegistrationInfo();
      print('✅ Device info collected');
      
      // Step 3: Get description
      print('📋 Step 3: Getting device description...');
      final description = await service.getDeviceDescription();
      print('✅ Description: $description');
      
      // Verify all components work together
      expect(cameraName, isNotEmpty);
      expect(deviceInfo, isNotEmpty);
      expect(description, isNotEmpty);
      
      print('\n🎉 Automatic workflow simulation completed successfully!');
      print('📊 Results:');
      print('   Camera Name: $cameraName');
      print('   Device: $description');
      print('   Registration Fields: ${deviceInfo.keys.length}');
    });
  });
}
