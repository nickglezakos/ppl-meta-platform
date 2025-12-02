import 'package:flutter_test/flutter_test.dart';
import 'package:signage_simple_player/services/discovery_service.dart';
import 'package:signage_simple_player/utils/device_info_helper.dart';

void main() {
  group('DeviceInfoHelper', () {
    test('getDeviceId returns non-empty string', () async {
      final deviceId = await DeviceInfoHelper.getDeviceId();
      expect(deviceId, isNotEmpty);
    });

    test('getDeviceId returns consistent value', () async {
      final id1 = await DeviceInfoHelper.getDeviceId();
      final id2 = await DeviceInfoHelper.getDeviceId();
      expect(id1, equals(id2));
    });

    test('getDeviceInfo returns valid model', () async {
      final deviceInfo = await DeviceInfoHelper.getDeviceInfo();
      expect(deviceInfo.deviceId, isNotEmpty);
      expect(deviceInfo.deviceName, isNotEmpty);
      expect(deviceInfo.platform, isNotEmpty);
      expect(deviceInfo.appVersion, isNotEmpty);
    });

    test('getLocalIpAddress returns valid IP', () async {
      final ip = await DeviceInfoHelper.getLocalIpAddress();
      expect(ip, isNotEmpty);
      expect(ip, matches(RegExp(r'^(\d{1,3}\.){3}\d{1,3}$|^localhost$')));
    });
  });

  group('SignageDiscoveryService', () {
    late SignageDiscoveryService service;

    setUp(() {
      service = SignageDiscoveryService();
    });

    tearDown(() async {
      await service.dispose();
    });

    test('initialize sets device info', () async {
      await service.initialize();
      expect(service.deviceInfo, isNotNull);
      expect(service.deviceInfo!.deviceId, isNotEmpty);
    });

    test('service starts unregistered', () {
      expect(service.isRegistered, isFalse);
      expect(service.serviceId, isNull);
    });

    test('dispose cleans up resources', () async {
      await service.initialize();
      await service.dispose();
      expect(service.isRegistered, isFalse);
    });
  });
}
